# GitHub Taskflow Skill

GitHub Issue → 작업 브랜치 → 프로젝트 검사 → 선택적 Stage → Commit → `origin` Push → Pull Request 생성을 하나의 로컬 워크플로우로 연결하는 **Claude Code + Codex 공용 Agent Skill**입니다.

> 상태: v0.1.0 / 표준 라이브러리 기반 / GitHub Actions 불필요

## 왜 만들었나요?

팀원이 Git 명령과 PR 절차를 매번 기억하지 않아도 같은 규칙으로 작업하도록 하기 위한 도구입니다. 실제 Git/GitHub 동작은 `scripts/taskflow.py`가 담당하고, Agent Skill은 Claude Code 또는 Codex가 그 런타임을 안전하게 호출하도록 안내합니다.

### 기본 흐름

```text
"작업 시작해줘"
    ↓
base branch 최신화
    ↓
GitHub Issue 생성
    ↓
<issue>-<type>-<slug> 작업 브랜치
    ↓
개발
    ↓
"검사해줘"
    ↓
변경 경로에 맞는 build/lint/test
    ↓
"제출하고 PR 만들어줘"
    ↓
관련 파일만 Stage → commit → origin push → PR
```

## 요구 사항

- Python 3.10+
- Git
- GitHub CLI (`gh`)
- `gh auth login` 완료
- 팀원이 직접 clone한 저장소에서 `origin`이 제출 대상 GitHub 저장소를 가리키는 구조

## 설치

### 1. 이 저장소 clone

```bash
git clone https://github.com/kim-thub/github-taskflow-skill.git
```

### 2. 사용할 프로젝트에 설치

```bash
python3 github-taskflow-skill/install.py \
  --target /path/to/your-project \
  --agents both \
  --base-branch dev
```

선택 가능한 Agent:

```text
--agents codex
--agents claude
--agents both
```

설치기는 기존 팀 설정을 기본적으로 덮어쓰지 않습니다. 기존 `taskflow.config.json`이나 GitHub 템플릿이 있으면 유지합니다. 의도적으로 교체할 때만 `--force`를 사용하세요.

## 설치 후 구조

```text
your-project/
├── .agents/skills/github-taskflow/       # Codex
├── .claude/skills/github-taskflow/       # Claude Code
├── .github/
│   ├── ISSUE_TEMPLATE/taskflow.md
│   └── PULL_REQUEST_TEMPLATE.md
└── scripts/
    ├── taskflow.py
    ├── taskflow.config.json
    ├── start-task
    └── finish-task
```

## 프로젝트별 설정

`scripts/taskflow.config.json`만 수정합니다.

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

## 사용법

### Claude Code

자연어로:

```text
작업 시작해줘. feat, 로그인 페이지 구현.
검사해줘.
이 작업 제출하고 PR까지 만들어줘.
```

프로젝트 Skill로 직접 호출할 수도 있습니다.

```text
/github-taskflow start feat 로그인 페이지 구현
/github-taskflow check
/github-taskflow submit 로그인 페이지 구현
```

### Codex

```text
$github-taskflow start feat 로그인 페이지 구현
$github-taskflow check
$github-taskflow submit 로그인 페이지 구현
```

자연어 요청으로 Skill이 선택되도록 사용할 수도 있습니다.

## 안전장치

- 작업 시작 전 dirty worktree 차단
- `git stash`, `git clean`, 자동 삭제를 사용하지 않음
- 검사를 통과하지 않으면 기본적으로 제출 중단
- Agent는 `git add .`, `git add -A`를 사용하지 않음
- 현재 작업과 관련된 명시적 경로만 Stage
- commit은 staged 파일만 포함
- push 대상은 `origin`만 허용
- PR merge와 branch 삭제는 자동화하지 않음
- `--skip-check`는 사용자가 명시적으로 요청한 경우만 사용

## 수동 CLI 사용도 가능

Agent 없이도 같은 런타임을 사용할 수 있습니다.

```bash
./scripts/start-task
./scripts/finish-task
./scripts/finish-task --continue
```

Windows:

```powershell
py scripts\taskflow.py start
py scripts\taskflow.py finish
py scripts\taskflow.py finish --continue
```

## 테스트

이 배포 저장소의 설치기 테스트:

```bash
python3 -m unittest discover -s tests -v
```

설치된 프로젝트의 Taskflow 자체 테스트는 프로젝트가 별도로 보유하는 것을 권장합니다.

## 배포/버전 관리

권장 릴리스 방식:

```text
v0.1.0  최초 공개
v0.1.x  버그 수정
v0.x.0  호환되는 기능 추가
v1.0.0  설치/설정 계약 안정화
```

GitHub Release에는 저장소 소스와 함께 `github-taskflow-skill.zip`을 첨부하면 설치가 더 쉽습니다.

## Claude / Codex 배포 확장

- **Claude Code**: 여러 프로젝트와 사용자에게 재사용할 때 Plugin이 공식 패키징 계층입니다. 이 저장소를 Claude plugin/marketplace 형태로 확장할 수 있습니다.
- **OpenAI**: Skills API는 Skill 디렉터리 또는 ZIP 업로드와 immutable version 생성을 지원합니다. GitHub 릴리스 ZIP을 같은 배포 원본으로 사용할 수 있습니다.

## 제한 사항

- 현재 워크플로우는 팀원이 저장소를 직접 clone하고 `origin`에 push하는 모델을 기본으로 합니다.
- fork 기반 기여 흐름은 자동 추론하지 않습니다.
- CLI 사용자 메시지는 현재 한국어 중심입니다.

## License

MIT
