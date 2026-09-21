import argparse
from dataclasses import dataclass
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path


TASK_TYPES = ("feat", "fix", "refactor", "style", "test", "docs", "chore")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="로컬 GitHub 작업 시작·완료 흐름을 실행합니다.")
    subcommands = parser.add_subparsers(dest="command", required=True)

    start_parser = subcommands.add_parser("start", help="이슈와 작업 브랜치를 시작합니다.")
    start_parser.add_argument("--type", dest="task_type", help="작업 타입 (예: feat, fix)")
    start_parser.add_argument("--title", help="작업 제목")
    start_parser.add_argument("--body-file", type=Path, help="이슈 본문 파일 경로")
    start_parser.add_argument(
        "--adopt", action="store_true",
        help="dev/main에서 이미 수정한 미커밋 파일과 Stage 상태를 유지하며 작업 브랜치로 이동합니다.",
    )

    finish_parser = subcommands.add_parser("finish", help="검사하거나 staged 변경을 제출합니다.")
    finish_parser.add_argument("--continue", dest="continue_submit", action="store_true", help="검사 후 staged 파일을 제출합니다.")
    finish_parser.add_argument("--skip-check", action="store_true", help="코드 검사를 생략합니다.")
    finish_parser.add_argument("--summary", help="커밋 요약; 생략하면 입력을 요청합니다.")
    finish_parser.add_argument("--yes", dest="auto_confirm", action="store_true", help="--continue 제출의 최종 확인을 자동 승인합니다.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    runner = CommandRunner()
    io = TaskflowIO(runner)

    if args.command == "start":
        supplied = (args.task_type, args.title, args.body_file)
        if any(supplied) and not all(supplied):
            parser.error("start 비대화형 실행에는 --type, --title, --body-file이 모두 필요합니다.")
        return start_task(
            StartOptions(args.task_type, args.title, args.body_file, interactive=not any(supplied), adopt=args.adopt),
            runner,
            io,
        )

    if args.auto_confirm and not args.continue_submit:
        parser.error("finish --yes는 --continue와 함께 사용해야 합니다.")
    return finish_task(
        FinishOptions(args.continue_submit, args.skip_check, args.summary, args.auto_confirm),
        runner,
        io,
    )


@dataclass(frozen=True)
class BranchContext:
    issue_number: int
    task_type: str
    slug: str


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


class CommandRunner:
    def run(self, args: list[str], cwd: Path) -> CommandResult:
        completed = subprocess.run(args, cwd=cwd, text=True, capture_output=True)
        return CommandResult(completed.returncode, completed.stdout, completed.stderr)


class EditorUnavailableError(RuntimeError):
    pass


class TaskflowIO:
    def __init__(self, runner: CommandRunner):
        self.runner = runner

    def prompt(self, message: str) -> str:
        return input(message)

    def write(self, message: str) -> None:
        print(message)

    def edit_template(self, template: str) -> str:
        temporary_file = None
        path = None
        keep_file = False
        try:
            temporary_file = tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                suffix=".md",
                prefix="taskflow-issue-",
                delete=False,
            )
            path = Path(temporary_file.name)
            temporary_file.write(template)
            temporary_file.close()
            editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
            try:
                command = shlex.split(editor) if editor else ["code", "--wait"]
            except ValueError as error:
                keep_file = True
                self.write(
                    "VISUAL 또는 EDITOR 설정이 잘못되었습니다. 설정을 고친 뒤 임시 파일을 편집하세요: "
                    f"{path}"
                )
                raise EditorUnavailableError("편집기 설정을 해석할 수 없습니다") from error
            try:
                result = self.runner.run(command + [str(path)], Path.cwd())
            except OSError as error:
                keep_file = True
                if editor:
                    self.write(
                        f"편집기를 실행할 수 없습니다: {editor}. 설정을 확인한 뒤 임시 파일을 편집하세요: {path}"
                    )
                    raise EditorUnavailableError("설정된 편집기를 실행할 수 없습니다") from error
                self.write(
                    "VISUAL 또는 EDITOR를 설정한 뒤 임시 파일을 편집하세요: "
                    f"{path}"
                )
                keep_file = True
                raise EditorUnavailableError("기본 편집기 code를 찾을 수 없습니다") from error
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or "이슈 편집기가 실패했습니다")
            return path.read_text(encoding="utf-8")
        except OSError as error:
            self.write(f"이슈 편집용 임시 파일을 준비할 수 없습니다: {error}")
            raise EditorUnavailableError("이슈 편집용 임시 파일을 만들 수 없습니다") from error
        finally:
            if temporary_file and not temporary_file.closed:
                try:
                    temporary_file.close()
                except OSError as error:
                    self.write(f"이슈 편집용 임시 파일을 닫지 못했습니다: {error}")
            if path and path.exists() and not keep_file:
                try:
                    path.unlink()
                except OSError as error:
                    self.write(f"이슈 편집용 임시 파일을 삭제하지 못했습니다: {path} ({error})")


@dataclass(frozen=True)
class StartOptions:
    task_type: str | None
    title: str | None
    body_file: Path | None
    interactive: bool
    adopt: bool = False


@dataclass(frozen=True)
class FinishOptions:
    continue_submit: bool
    skip_check: bool
    summary: str | None = None
    auto_confirm: bool = False


def load_config(path: Path) -> dict:
    with path.open(encoding="utf-8") as config_file:
        config = json.load(config_file)
    if not isinstance(config, dict):
        raise ValueError("설정 파일은 JSON object여야 합니다")
    if not isinstance(config.get("base_branch"), str) or not config["base_branch"].strip():
        raise ValueError("설정 파일에 base_branch가 필요합니다")
    for key in ("issue_template", "pull_request_template"):
        if key in config and (not isinstance(config[key], str) or not config[key].strip()):
            raise ValueError(f"설정 파일의 {key}는 비어 있지 않은 문자열이어야 합니다")
    if "checks" in config:
        if not isinstance(config["checks"], dict):
            raise ValueError("설정 파일의 checks는 object여야 합니다")
        for name, group in config["checks"].items():
            if not isinstance(group, dict):
                raise ValueError(f"검사 그룹 {name}은 object여야 합니다")
            paths = group.get("paths")
            cwd = group.get("cwd")
            commands = group.get("commands")
            if not isinstance(paths, list) or not all(isinstance(item, str) and item for item in paths):
                raise ValueError(f"검사 그룹 {name}의 paths는 문자열 목록이어야 합니다")
            if not isinstance(cwd, str) or not cwd:
                raise ValueError(f"검사 그룹 {name}의 cwd는 문자열이어야 합니다")
            if not isinstance(commands, list) or not all(
                isinstance(command, list) and all(isinstance(arg, str) and arg for arg in command)
                for command in commands
            ):
                raise ValueError(f"검사 그룹 {name}의 commands는 명령 인자 목록이어야 합니다")
    return config


def repo_root(runner: CommandRunner) -> Path:
    result = runner.run(["git", "rev-parse", "--show-toplevel"], Path.cwd())
    root = result.stdout.strip()
    if result.returncode != 0 or not root:
        raise RuntimeError(f"저장소 루트를 찾을 수 없습니다: {result.stderr.strip()}")
    return Path(root)


def require_commands(runner: CommandRunner, names: list[str]) -> None:
    for name in names:
        try:
            result = runner.run([name, "--version"], Path.cwd())
        except FileNotFoundError as error:
            raise RuntimeError(f"필수 명령을 찾을 수 없습니다: {name}") from error
        if result.returncode != 0:
            raise RuntimeError(f"필수 명령을 찾을 수 없습니다: {name}")


def slugify_title(title: str) -> str:
    slug = re.sub(r"[\W_]+", "-", title.strip(), flags=re.UNICODE).strip("-")
    return slug.lower() or "작업"


def build_branch_name(issue_number: int, task_type: str, title: str) -> str:
    if task_type not in TASK_TYPES:
        raise ValueError(f"지원하지 않는 작업 타입: {task_type}")
    return f"{issue_number}-{task_type}-{slugify_title(title)}"


def detect_check_groups(paths: list[str], config: dict) -> list[str]:
    groups = []
    for name, definition in config.get("checks", {}).items():
        prefixes = definition.get("paths", [])
        if any(path.startswith(prefix) for path in paths for prefix in prefixes):
            groups.append(name)
    return groups


def parse_branch_context(branch_name: str) -> BranchContext:
    match = re.fullmatch(r"(\d+)-(feat|fix|refactor|style|test|docs|chore)-(.+)", branch_name)
    if not match:
        raise ValueError("작업 브랜치 형식이 아닙니다")
    return BranchContext(int(match.group(1)), match.group(2), match.group(3))


def parse_issue_number(issue_url: str) -> int:
    match = re.search(r"/issues/(\d+)(?:$|[?#])", issue_url.strip())
    if not match:
        raise ValueError(f"이슈 번호를 추출할 수 없습니다: {issue_url}")
    return int(match.group(1))


def render_issue_body(template: str) -> str:
    return re.sub(r"\A---\n.*?\n---\n?", "", template, count=1, flags=re.DOTALL).lstrip("\n")


def render_pr_body(template: str, issue_number: int, check_summary: str) -> str:
    body = re.sub(r"(?im)^-\s*close:\s*#\s*$", f"Closes #{issue_number}", template)
    return f"{body.rstrip()}\n\n## 테스트 결과\n\n{check_summary}\n"


def start_task(options: StartOptions, runner: CommandRunner, io: TaskflowIO) -> int:
    values = None
    if not options.interactive:
        values = _start_values(options, io)
        if values is None:
            return 1

    try:
        root = repo_root(runner)
    except (OSError, RuntimeError) as error:
        io.write(str(error))
        return 1

    auth_result = _run_start_command(runner, ["gh", "auth", "status"], root, io)
    if auth_result is None:
        return 1
    if auth_result.returncode != 0:
        io.write(_command_failure("gh auth status", auth_result))
        return 1

    status_result = _run_start_command(runner, ["git", "status", "--porcelain"], root, io)
    if status_result is None:
        return 1
    if status_result.returncode != 0:
        io.write(_command_failure("git status --porcelain", status_result))
        return 1
    try:
        config = load_config(Path(__file__).with_name("taskflow.config.json"))
        base_branch = config["base_branch"]
    except (OSError, ValueError, KeyError) as error:
        io.write(f"작업 흐름 설정을 읽을 수 없습니다: {error}")
        return 1
    remote = os.environ.get("TASKFLOW_REMOTE", "origin").strip() or "origin"

    if options.adopt:
        if not _prepare_adopt_start(root, runner, io, base_branch, remote, status_result.stdout):
            return 1
    else:
        if status_result.stdout.strip():
            io.write("작업 트리가 깨끗하지 않습니다. 현재 수정한 파일을 새 작업 브랜치로 옮기려면 start --adopt를 사용하세요.")
            io.write(status_result.stdout.rstrip())
            return 1
        switch_result = _run_start_command(runner, ["git", "switch", base_branch], root, io)
        if switch_result is None:
            return 1
        if switch_result.returncode != 0:
            io.write(_command_failure(f"git switch {base_branch}", switch_result))
            return 1
        pull_result = _run_start_command(runner, ["git", "pull", "--ff-only", remote, base_branch], root, io)
        if pull_result is None:
            return 1
        if pull_result.returncode != 0:
            io.write(_command_failure(f"git pull --ff-only {remote} {base_branch}", pull_result))
            return 1

    if options.interactive:
        values = _start_values(options, io)
    if values is None:
        return 1
    task_type, title, body = values

    if body is None:
        try:
            template_path = root / config["issue_template"]
            template = render_issue_body(template_path.read_text(encoding="utf-8"))
            body = io.edit_template(template)
        except (OSError, RuntimeError) as error:
            io.write(f"이슈 본문을 준비할 수 없습니다: {error}")
            return 1

    issue_url = _create_issue(runner, root, task_type, title, body, io)
    if issue_url is None:
        return 1
    try:
        issue_number = parse_issue_number(issue_url)
    except ValueError as error:
        io.write(str(error))
        return 1

    branch_name = build_branch_name(issue_number, task_type, title)
    branch_result = _run_start_command(runner, ["git", "switch", "-c", branch_name], root, io)
    if branch_result is None:
        io.write(f"생성된 이슈: {issue_url}")
        io.write(f"수동으로 브랜치를 만드세요: git switch -c {branch_name}")
        return 1
    if branch_result.returncode != 0:
        io.write(_command_failure(f"git switch -c {branch_name}", branch_result))
        io.write(f"생성된 이슈: {issue_url}")
        io.write(f"수동으로 브랜치를 만드세요: git switch -c {branch_name}")
        return 1
    if options.adopt:
        io.write("수정/Stage/새 파일을 유지한 채 브랜치를 만들었습니다. 자동 Stage·Commit·Stash는 실행하지 않았습니다.")
    io.write(f"작업 브랜치를 만들었습니다: {branch_name}")
    io.write(f"이슈: {issue_url}")
    return 0


def _prepare_adopt_start(
    root: Path,
    runner: CommandRunner,
    io: TaskflowIO,
    base_branch: str,
    remote: str,
    status: str,
) -> bool:
    """Reject unsafe histories before creating an issue or changing the working tree."""
    if not status.strip():
        io.write("옮길 미커밋 변경사항이 없습니다. 일반 start를 사용하세요.")
        return False

    current_result = _run_start_command(runner, ["git", "branch", "--show-current"], root, io)
    if current_result is None:
        return False
    if current_result.returncode != 0:
        io.write(_command_failure("git branch --show-current", current_result))
        return False
    current = current_result.stdout.strip()
    if current not in {base_branch, "main", "dev"}:
        io.write(f"--adopt는 dev/main 기준 브랜치에서만 지원합니다. 현재 브랜치: {current or '(detached HEAD)'}")
        return False

    # Fetch updates the remote-tracking branch, not the dirty worktree/index.
    fetch = _run_start_command(runner, ["git", "fetch", remote, base_branch], root, io)
    if fetch is None:
        return False
    if fetch.returncode != 0:
        io.write(_command_failure(f"git fetch {remote} {base_branch}", fetch))
        return False

    remote_tip = f"refs/remotes/{remote}/{base_branch}"
    remote_ref = _run_start_command(runner, ["git", "rev-parse", "--verify", f"{remote_tip}^{{commit}}"], root, io)
    if remote_ref is None:
        return False
    if remote_ref.returncode != 0:
        io.write(f"기준 원격 브랜치를 찾을 수 없습니다: {remote_tip}. 작업 파일은 그대로입니다.")
        return False

    # If HEAD contains commits not in the PR base, simply switching -c would
    # carry unrelated/previously committed work into the future PR.
    ancestry = _run_start_command(runner, ["git", "merge-base", "--is-ancestor", "HEAD", remote_tip], root, io)
    if ancestry is None:
        return False
    if ancestry.returncode != 0:
        io.write(
            f"현재 {current}의 HEAD가 {remote}/{base_branch}의 조상이 아닙니다. "
            "이미 dev/main에 커밋한 변경이나 다른 브랜치의 커밋이 PR에 섞일 수 있어 자동 이동하지 않습니다. "
            "기존 파일/Stage/커밋은 그대로 유지됩니다. 커밋 이력을 먼저 별도로 확인하세요."
        )
        return False

    if current != base_branch:
        io.write(
            f"현재 브랜치는 {current}, PR 기준은 {base_branch}입니다. "
            "현재 HEAD가 원격 기준 브랜치의 조상임을 확인했습니다. "
            "기존 파일을 건드리지 않고 현재 HEAD에서 작업 브랜치를 만듭니다."
        )
    io.write("미커밋 변경사항을 유지합니다. --adopt 모드에서는 git switch <base> 또는 git pull을 실행하지 않습니다.")
    return True


def finish_task(options: FinishOptions, runner: CommandRunner, io: TaskflowIO) -> int:
    remote = os.environ.get("TASKFLOW_REMOTE", "origin").strip() or "origin"
    if options.continue_submit and remote != "origin":
        io.write(f"제출 원격은 origin만 사용할 수 있습니다: {remote}")
        return 1

    try:
        root = repo_root(runner)
        config = load_config(Path(__file__).with_name("taskflow.config.json"))
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        io.write(f"작업 흐름 설정을 읽을 수 없습니다: {error}")
        return 1

    branch_result = _run_finish_command(runner, ["git", "branch", "--show-current"], root, io)
    if branch_result is None:
        return 1
    if branch_result.returncode != 0:
        io.write(_command_failure("git branch --show-current", branch_result))
        return 1
    branch_name = branch_result.stdout.strip()
    try:
        context = parse_branch_context(branch_name)
    except ValueError as error:
        io.write(str(error))
        return 1

    status_result = _run_finish_command(runner, ["git", "status", "--porcelain"], root, io)
    if status_result is None:
        return 1
    if status_result.returncode != 0:
        io.write(_command_failure("git status --porcelain", status_result))
        return 1
    status = status_result.stdout
    paths = _changed_paths(status)
    _write_changed_state(io, paths, status)

    check_summary = _run_checks(paths, config, root, runner, io, options.skip_check)
    if check_summary is None:
        return 1

    if not options.continue_submit:
        io.write("검사 결과:\n" + check_summary)
        io.write("VS Code Source Control에서 제출할 파일만 Stage한 뒤 실행하세요: ./scripts/finish-task --continue")
        return 0

    fresh_status_result = _run_finish_command(runner, ["git", "status", "--porcelain"], root, io)
    if fresh_status_result is None:
        return 1
    if fresh_status_result.returncode != 0:
        io.write(_command_failure("git status --porcelain", fresh_status_result))
        return 1
    status = fresh_status_result.stdout
    _write_changed_state(io, _changed_paths(status), status)

    staged_result = _run_finish_command(runner, ["git", "diff", "--cached", "--name-only"], root, io)
    if staged_result is None:
        return 1
    if staged_result.returncode != 0:
        io.write(_command_failure("git diff --cached --name-only", staged_result))
        return 1
    if not staged_result.stdout.strip():
        io.write("Stage된 파일이 없습니다. VS Code Source Control에서 파일을 Stage한 뒤 다시 실행하세요.")
        return 1

    cached_diff = _run_finish_command(runner, ["git", "diff", "--cached"], root, io)
    if cached_diff is None:
        return 1
    if cached_diff.returncode != 0:
        io.write(_command_failure("git diff --cached", cached_diff))
        return 1
    io.write("Stage된 변경 사항:\n" + (cached_diff.stdout.rstrip() or "(diff 없음)"))
    if _has_unstaged_changes(status):
        io.write("Stage되지 않은 변경이 남아 있습니다. staged 파일만 commit합니다.")

    summary = (options.summary or io.prompt("커밋 요약: ")).strip()
    if not summary:
        io.write("커밋 요약은 비어 있을 수 없습니다.")
        return 1
    message = f"[{context.task_type}] {summary} #{context.issue_number}"
    confirmation = "yes" if options.auto_confirm else io.prompt(
        f"'{message}'를 commit, origin push, PR 생성하시겠습니까? [y/N]: "
    ).strip().lower()
    if confirmation not in {"y", "yes", "예"}:
        io.write("제출을 취소했습니다. Stage 상태는 그대로 유지됩니다.")
        return 0

    commit_result = _run_finish_command(runner, ["git", "commit", "-m", message], root, io)
    if commit_result is None:
        return 1
    if commit_result.returncode != 0:
        io.write(_command_failure("git commit", commit_result))
        return 1

    push_result = _run_finish_command(
        runner,
        ["git", "push", "--set-upstream", "origin", branch_name],
        root,
        io,
    )
    if push_result is None:
        return 1
    if push_result.returncode != 0:
        io.write(_command_failure("git push --set-upstream origin", push_result))
        return 1

    return _create_pull_request(config, root, context, branch_name, summary, check_summary, runner, io)


def _changed_paths(status: str) -> list[str]:
    paths = []
    for line in status.splitlines():
        if len(line) < 4:
            continue
        path = line[3:]
        if " -> " in path:
            path = path.rsplit(" -> ", 1)[1]
        paths.append(path)
    return paths


def _has_unstaged_changes(status: str) -> bool:
    return any(line.startswith("??") or (len(line) >= 2 and line[1] != " ") for line in status.splitlines())


def _write_changed_state(io: TaskflowIO, paths: list[str], status: str) -> None:
    if paths:
        io.write("변경 파일:\n" + "\n".join(paths))
    else:
        io.write("변경 파일이 없습니다.")
    if any(len(line) >= 1 and line[0] not in {" ", "?"} for line in status.splitlines()):
        io.write("Stage된 파일이 있습니다.")
    else:
        io.write("Stage된 파일이 없습니다.")


def _run_checks(
    paths: list[str],
    config: dict,
    root: Path,
    runner: CommandRunner,
    io: TaskflowIO,
    skip_check: bool,
) -> str | None:
    if skip_check:
        io.write("검사를 --skip-check로 생략했습니다.")
        return "- 검사 생략: --skip-check"

    groups = detect_check_groups(paths, config)
    if not groups:
        io.write("변경 경로에 해당하는 코드 검사가 없습니다.")
        return "- 코드 검사: 대상 없음"
    summary = []
    for group_name in groups:
        definition = config["checks"][group_name]
        for command in definition["commands"]:
            result = _run_finish_command(runner, command, root / definition["cwd"], io)
            if result is None:
                return None
            if result.returncode != 0:
                io.write(_command_failure(" ".join(command), result))
                return None
            output = "\n".join(part for part in (result.stdout.strip(), result.stderr.strip()) if part)
            if output:
                io.write(output)
        summary.append(f"- {group_name}: 통과")
    return "\n".join(summary)


def _create_pull_request(
    config: dict,
    root: Path,
    context: BranchContext,
    branch_name: str,
    summary: str,
    check_summary: str,
    runner: CommandRunner,
    io: TaskflowIO,
) -> int:
    body_path = None
    temporary_file = None
    result = None
    title = f"[{context.task_type.title()}] {summary}"
    try:
        template = (root / config["pull_request_template"]).read_text(encoding="utf-8")
        body = render_pr_body(template, context.issue_number, check_summary)
        temporary_file = tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".md", prefix="taskflow-pr-", delete=False
        )
        body_path = Path(temporary_file.name)
        temporary_file.write(body)
        temporary_file.close()
        result = runner.run(
            [
                "gh",
                "pr",
                "create",
                "--base",
                config["base_branch"],
                "--head",
                branch_name,
                "--title",
                title,
                "--body-file",
                str(body_path),
            ],
            root,
        )
    except OSError as error:
        io.write(f"PR 본문 또는 명령을 준비할 수 없습니다: {error}")
    finally:
        if temporary_file and not temporary_file.closed:
            try:
                temporary_file.close()
            except OSError as error:
                io.write(f"PR 본문 임시 파일을 닫지 못했습니다: {error}")
        if body_path and body_path.exists():
            try:
                body_path.unlink()
            except OSError as error:
                io.write(f"PR 본문 임시 파일을 삭제하지 못했습니다: {body_path} ({error})")

    if result is None or result.returncode != 0:
        if result is not None:
            io.write(_command_failure("gh pr create", result))
        io.write(
            "PR을 수동으로 만드세요: "
            f"gh pr create --base {config['base_branch']} --head {branch_name}"
        )
        return 1
    io.write(f"PR을 만들었습니다: {result.stdout.strip()}")
    return 0


def _start_values(options: StartOptions, io: TaskflowIO) -> tuple[str, str, str | None] | None:
    if options.interactive:
        task_type = _prompt_task_type(io)
        title = _prompt_title(io)
        return task_type, title, None

    task_type = (options.task_type or "").strip()
    title = (options.title or "").strip()
    if not task_type or not title or options.body_file is None:
        io.write("비대화형 실행에는 --type, --title, --body-file이 모두 필요합니다.")
        return None
    if task_type not in TASK_TYPES:
        io.write(f"지원하지 않는 작업 타입: {task_type}")
        return None
    try:
        return task_type, title, Path(options.body_file).read_text(encoding="utf-8")
    except OSError as error:
        io.write(f"이슈 본문 파일을 읽을 수 없습니다: {error}")
        return None


def _prompt_task_type(io: TaskflowIO) -> str:
    while True:
        task_type = io.prompt(f"작업 타입 ({', '.join(TASK_TYPES)}): ").strip()
        if task_type in TASK_TYPES:
            return task_type
        io.write(f"지원하지 않는 작업 타입입니다: {task_type}")


def _prompt_title(io: TaskflowIO) -> str:
    while True:
        title = io.prompt("작업 제목: ").strip()
        if title:
            return title
        io.write("작업 제목은 비어 있을 수 없습니다.")


def _create_issue(
    runner: CommandRunner,
    root: Path,
    task_type: str,
    title: str,
    body: str,
    io: TaskflowIO,
) -> str | None:
    temporary_file = None
    body_path = None
    result = None
    try:
        temporary_file = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".md", delete=False)
        body_path = Path(temporary_file.name)
        temporary_file.write(body)
        temporary_file.close()
        result = runner.run(
            ["gh", "issue", "create", "--title", f"[{task_type.title()}] {title}", "--body-file", str(body_path)],
            root,
        )
    except OSError as error:
        io.write(f"이슈 생성용 임시 파일 또는 명령을 준비할 수 없습니다: {error}")
        return None
    finally:
        if temporary_file and not temporary_file.closed:
            try:
                temporary_file.close()
            except OSError as error:
                io.write(f"이슈 본문 임시 파일을 닫지 못했습니다: {error}")
        if body_path and body_path.exists():
            try:
                body_path.unlink()
            except OSError as error:
                io.write(f"이슈 본문 임시 파일을 삭제하지 못했습니다: {body_path} ({error})")
    if result.returncode != 0:
        io.write(_command_failure("gh issue create", result))
        return None
    return result.stdout.strip()


def _command_failure(command: str, result: CommandResult) -> str:
    detail = result.stderr.strip() or result.stdout.strip() or "알 수 없는 오류"
    return f"명령이 실패했습니다 ({command}): {detail}"


def _run_start_command(
    runner: CommandRunner, args: list[str], root: Path, io: TaskflowIO
) -> CommandResult | None:
    try:
        return runner.run(args, root)
    except OSError as error:
        io.write(f"명령을 실행할 수 없습니다 ({' '.join(args)}): {error}")
        return None


def _run_finish_command(
    runner: CommandRunner, args: list[str], root: Path, io: TaskflowIO
) -> CommandResult | None:
    try:
        return runner.run(args, root)
    except OSError as error:
        io.write(f"명령을 실행할 수 없습니다 ({' '.join(args)}): {error}")
        return None


if __name__ == "__main__":
    sys.exit(main())
