#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import stat
import sys
from pathlib import Path

AGENTS = ("codex", "claude", "both")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Install GitHub Taskflow runtime and agent skill into a Git repository.")
    p.add_argument("--target", type=Path, default=Path.cwd(), help="Target Git repository (default: current directory)")
    p.add_argument("--agents", choices=AGENTS, default="both", help="Install Codex, Claude, or both skills")
    p.add_argument("--base-branch", default="dev", help="Base branch written to new config (default: dev)")
    p.add_argument("--force", action="store_true", help="Overwrite Taskflow-managed runtime/skill files")
    return p


def copy_file(src: Path, dst: Path, *, force: bool, executable: bool = False) -> str:
    if dst.exists() and not force:
        return f"skip  {dst} (already exists)"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    if executable:
        dst.chmod(dst.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return f"write {dst}"


def copy_tree(src: Path, dst: Path, *, force: bool) -> list[str]:
    messages: list[str] = []
    for path in src.rglob("*"):
        if path.is_dir():
            continue
        rel = path.relative_to(src)
        messages.append(copy_file(path, dst / rel, force=force))
    return messages


def write_config(source: Path, target: Path, base_branch: str, *, force: bool) -> str:
    if target.exists() and not force:
        return f"skip  {target} (already exists; keep team-specific config)"
    data = json.loads(source.read_text(encoding="utf-8"))
    data["base_branch"] = base_branch
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return f"write {target}"


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    package_root = Path(__file__).resolve().parent
    target = args.target.expanduser().resolve()

    if not (target / ".git").exists():
        print(f"error: target is not a Git repository root: {target}", file=sys.stderr)
        return 2

    messages: list[str] = []
    runtime = package_root / "runtime"
    messages.append(copy_file(runtime / "taskflow.py", target / "scripts/taskflow.py", force=args.force))
    messages.append(copy_file(runtime / "start-task", target / "scripts/start-task", force=args.force, executable=True))
    messages.append(copy_file(runtime / "finish-task", target / "scripts/finish-task", force=args.force, executable=True))
    messages.append(
        write_config(
            runtime / "taskflow.config.example.json",
            target / "scripts/taskflow.config.json",
            args.base_branch,
            force=args.force,
        )
    )

    # Templates are defaults only; never overwrite a team's existing templates without --force.
    template_root = package_root / "templates"
    messages.extend(copy_tree(template_root, target, force=args.force))

    skill = package_root / "skill/github-taskflow"
    if args.agents in {"codex", "both"}:
        messages.extend(copy_tree(skill, target / ".agents/skills/github-taskflow", force=args.force))
    if args.agents in {"claude", "both"}:
        messages.extend(copy_tree(skill, target / ".claude/skills/github-taskflow", force=args.force))

    print("GitHub Taskflow install result")
    for message in messages:
        print(message)
    print("\nNext:")
    print(f"  1. Review {target / 'scripts/taskflow.config.json'}")
    print("  2. Configure checks for your project")
    print("  3. Run: gh auth status")
    print("  4. Ask your agent: '작업 시작해줘' / '검사해줘' / '제출하고 PR 만들어줘'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
