# GitHub Taskflow Skill v0.4.0

## 이미 시작한 작업을 안전하게 작업 브랜치로 옮기기

- 새 명령 `./scripts/start-task --adopt`: `dev` 또는 `main`에서 **아직 커밋하지 않은** 작업을 Issue 생성 후 새 브랜치로 이동합니다.
- 수정 파일, Stage 상태, 새 파일을 그대로 보존합니다. `stash`, `reset`, 자동 Stage/Commit, dirty worktree에서 `pull`을 수행하지 않습니다.
- 현재 HEAD가 원격 PR 대상 브랜치의 조상인지 검사하며, 다른 커밋이 PR에 섞일 위험이 있으면 Issue 생성 전에 중단합니다.
- 기존 `start`, 검사, Commit, Push, PR 흐름과 전역 Codex/Claude Skill 등록은 유지됩니다.

## 기존 프로젝트 업데이트

```bash
cd ~/tools/github-taskflow-skill
git pull
python3 bootstrap.py --agents both --force   # copy 모드일 때만 필요
```

기존 프로젝트의 작업 루트에서:

```bash
SOURCE="$(cat "$HOME/.config/github-taskflow/source-path")"
ROOT="$(git rev-parse --show-toplevel)"
python3 "$SOURCE/install.py" --target "$ROOT" --update-runtime
```

프로젝트별 `scripts/taskflow.config.json`과 `.github/` 템플릿은 보존됩니다. 이미 공유 기준 브랜치에 커밋된 변경은 v0.4.0에서 자동 이력 수정하지 않습니다.
