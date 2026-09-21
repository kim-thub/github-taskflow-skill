# GitHub Taskflow Skill

GitHub Issue → 작업 브랜치 → 프로젝트 검사 → 선택적 Stage → Commit → `origin` Push → Pull Request 생성을 하나의 로컬 워크플로우로 연결하는 **Claude Code + Codex 공용 Agent Skill**입니다.

> 상태: v0.4.0 / 사용자 전역 Skill + 터미널 CLI 중심 사용 / 미커밋 작업 브랜치 이동 지원

## 권장 사용 방식: 한 번 clone, 모든 프로젝트에서 사용

Skill 저장소를 작업 프로젝트와 별도의 도구 폴더에 clone합니다.

```bash
git clone https://github.com/kim-thub/github-taskflow-skill.git ~/tools/github-taskflow-skill
cd ~/tools/github-taskflow-skill
```

그다음 사용자 전역 Skill로 등록합니다.

```bash
python3 bootstrap.py --agents both
```

macOS/Linux에서 `git pull`만으로 Skill 내용도 즉시 갱신되게 하고 싶다면 symlink 모드를 사용할 수 있습니다.

```bash
python3 bootstrap.py --agents both --mode link
```

기본 `copy` 모드는 Windows를 포함해 이식성이 더 좋습니다. copy 모드에서 Skill을 업데이트한 뒤에는 `bootstrap.py --force`를 다시 실행합니다.

등록 위치:

```text
Codex   ~/.agents/skills/github-taskflow/
Claude  ~/.claude/skills/github-taskflow/
공통    ~/.config/github-taskflow/source-path
```

## 권장 실행 환경: 터미널 CLI

v0.4.0의 기본 사용 환경은 VS Code 확장이 아니라 **일반 터미널에서 실행한 Codex CLI 또는 Claude Code CLI**입니다.

먼저 일반 터미널에서 GitHub CLI 인증이 정상인지 확인합니다.

```bash
gh auth status
```

그다음 작업할 Git 저장소로 이동해서 Agent CLI를 실행합니다.

### Codex CLI

```bash
cd /path/to/project
codex
```

Codex에서 Skill을 명시적으로 호출할 수 있습니다.

```text
$github-taskflow install dev
$github-taskflow 작업 시작해줘. feat, 로그인 페이지 구현.
$github-taskflow dev에서 이미 수정한 파일을 새 작업 브랜치로 옮겨줘.
$github-taskflow 검사해줘.
$github-taskflow 이 작업 제출하고 PR까지 만들어줘.
```

Codex는 사용자 전역 Skill을 `$HOME/.agents/skills`에서 읽습니다.

### Claude Code CLI

```bash
cd /path/to/project
claude
```

Claude Code에서:

```text
/github-taskflow install dev
/github-taskflow 작업 시작해줘. feat, 로그인 페이지 구현.
/github-taskflow dev에서 이미 수정한 파일을 새 작업 브랜치로 옮겨줘.
/github-taskflow 검사해줘.
/github-taskflow 이 작업 제출하고 PR까지 만들어줘.
```

Skill을 처음 등록했거나 갱신했다면 실행 중인 Agent CLI 세션을 다시 시작하는 것이 가장 확실합니다.

## 프로젝트에 설치되는 파일

`install` 모드는 전역 설정에 기록된 distribution clone 위치를 찾아 현재 프로젝트에 Taskflow runtime만 설치합니다.

```text
your-project/
├── .github/
│   ├── ISSUE_TEMPLATE/taskflow.md
│   └── PULL_REQUEST_TEMPLATE.md
└── scripts/
    ├── taskflow.py
    ├── taskflow.config.json
    ├── start-task
    └── finish-task
```

전역 Skill을 사용하는 경우 프로젝트마다 `.agents/skills`와 `.claude/skills`를 복사할 필요가 없습니다.

## 프로젝트별 설정

`scripts/taskflow.config.json`에서 기준 브랜치와 검사 명령을 관리합니다.

```json
{
  "base_branch": "dev",
  "issue_template": ".github/ISSUE_TEMPLATE/taskflow.md",
  "pull_request_template": ".github/PULL_REQUEST_TEMPLATE.md",
  "checks": {
    "frontend": {
      "paths": ["frontend/"],
      "cwd": "frontend",
      "commands": [["npm", "run", "build"], ["npm", "run", "lint"]]
    },
    "backend": {
      "paths": ["backend/"],
      "cwd": "backend",
      "commands": [["uv", "run", "pytest"]]
    }
  }
}
```

Agent는 프로젝트의 build/lint/test 명령을 임의로 추측하지 않습니다. 기본 설정이 맞지 않으면 프로젝트에 맞게 설정해야 합니다.

## v0.4.0: dev/main에서 이미 시작한 미커밋 작업 옮기기

팀원이 `dev` 또는 `main`에서 이미 파일을 수정했다면, 작업 내용을 임시 저장하거나 커밋하지 않고 **현재 HEAD에 바로 새 작업 브랜치를 만들 수 있습니다.** Issue 생성과 브랜치 생성은 원래 Taskflow 규칙을 따릅니다.

```bash
git status --short                    # 현재 수정·Stage·새 파일 확인
./scripts/start-task --adopt          # 이슈 입력 후 현재 작업을 새 브랜치로 이동
git branch --show-current             # <이슈번호>-<타입>-<제목>
git status --short                    # 수정·Stage·새 파일 상태 유지 확인
```

Agent CLI에서도 “이미 `dev`에서 작업한 파일을 새 브랜치로 옮겨줘”라고 요청하면 `start --adopt`를 사용합니다. 단, 변경 파일이 해당 작업과 무관하거나 포함 범위가 모호하면 먼저 사용자 확인을 받습니다.

**안전 조건:** 미커밋 수정이 있어야 하고, 시작 브랜치는 `dev`/`main` 또는 프로젝트의 설정된 기준 브랜치여야 합니다. 현재 `HEAD`가 `origin/<base_branch>`의 조상인지 원격을 fetch한 뒤 확인합니다. `main`에서 작업했지만 PR 기준이 `dev`인 경우에도 이 조건이 충족되면 이동합니다. 조건을 통과하지 못하면 Issue를 만들기 전에 중단합니다. **작업 중인 브랜치에서 `git pull`, `git switch dev`, `stash`, `reset`, 자동 Stage/Commit을 하지 않습니다.**

이미 `dev`/`main`에 **커밋까지 한 작업**은 단순 브랜치 이동만으로 원래 브랜치에서 커밋이 사라지지 않습니다. v0.4.0은 그 이력을 자동으로 수정하지 않으며, 별도 Git 이력 검토가 필요하다고 알립니다.

## 기존 프로젝트-local 설치도 지원

전역 Skill 대신 각 프로젝트에 Skill을 같이 복사하고 싶다면 기존 방식도 사용할 수 있습니다.

```bash
python3 install.py --target /path/to/project --agents both --base-branch dev
```

전역 Skill을 이미 사용하는 프로젝트에는 runtime만 설치할 수 있습니다.

```bash
python3 install.py --target /path/to/project --agents none --base-branch dev
```

## 업데이트

v0.3.0에서 v0.4.0으로 갱신할 때는 **전역 Skill과 프로젝트에 복사한 runtime을 각각 업데이트**해야 합니다.

### link 모드

```bash
cd ~/tools/github-taskflow-skill
git pull
```

전역 Skill이 clone을 직접 가리키므로 추가 등록이 필요 없습니다.

### copy 모드

```bash
cd ~/tools/github-taskflow-skill
git pull
python3 bootstrap.py --agents both --force
```

프로젝트에 복사된 `scripts/taskflow.py` runtime은 자동으로 덮어쓰지 않습니다. 기존 프로젝트에서 v0.4.0의 `--adopt`를 사용하려면 다음을 실행하세요. 팀 전용 설정과 Issue/PR 템플릿은 그대로 유지됩니다.

```bash
SOURCE="$(cat "$HOME/.config/github-taskflow/source-path")"
ROOT="$(git rev-parse --show-toplevel)"
python3 "$SOURCE/install.py" --target "$ROOT" --update-runtime
```

`--update-runtime`은 프로젝트의 `scripts/taskflow.py`, `start-task`, `finish-task` 세 파일을 교체합니다. 이 파일을 팀에서 직접 수정했다면 먼저 해당 수정 내용을 확인하세요. `--force`는 팀의 설정·템플릿까지 덮어쓸 수 있으므로 일반 업데이트에 사용하지 않습니다.

**팀 프로젝트에서 위 스크립트가 Git 추적 대상이라면:** `--update-runtime`으로 생긴 변경은 기능 개발과 분리된 Taskflow 업그레이드 PR로 먼저 반영하세요. 이미 `dev`/`main`에 기능 수정이 있는 경우 그 파일들과 업그레이드 파일을 한 PR에 자동으로 합치지 마세요.

## VS Code 확장 사용에 대한 안내

Codex/Claude의 IDE 확장에서도 Skill 자체는 인식될 수 있습니다. 다만 확장 실행 환경이 일반 터미널과 다른 sandbox, Keychain 또는 credential 접근 정책을 사용할 수 있습니다.

예를 들어 일반 터미널에서 `gh auth status`가 성공하지만 IDE Agent 내부에서만 인증이 실패한다면, 토큰을 다시 발급하기 전에 동일 명령을 일반 터미널에서 비교하세요. v0.4.0의 검증 기준은 **일반 터미널에서 실행한 Agent CLI**입니다.

## 안전장치

- 일반 `start`는 dirty worktree 차단, 명시적인 `start --adopt`는 dev/main의 미커밋 작업만 보존하며 이동
- `--adopt`는 기준 원격 브랜치의 커밋 조상을 검사해 무관한 커밋이 PR에 섞이는 상황 차단
- `git stash`, `git clean`, 자동 삭제를 사용하지 않음
- 검사를 통과하지 않으면 기본적으로 제출 중단
- Agent는 `git add .`, `git add -A`를 사용하지 않음
- 현재 작업과 관련된 명시적 경로만 Stage
- commit은 staged 파일만 포함
- push 대상은 `origin`만 허용
- PR merge와 branch 삭제는 자동화하지 않음
- `--skip-check`는 사용자가 명시적으로 요청한 경우만 사용

## 요구 사항

- Python 3.10+
- Git
- GitHub CLI (`gh`)
- 일반 터미널에서 `gh auth status` 성공
- Codex CLI 또는 Claude Code CLI
- 팀원이 직접 clone한 저장소에서 `origin`이 제출 대상 GitHub 저장소를 가리키는 구조

## 테스트

```bash
python3 -m unittest discover -s tests -v
```

## License

MIT
