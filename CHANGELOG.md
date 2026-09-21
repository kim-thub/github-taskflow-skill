# Changelog

## v0.4.0

- `start --adopt` 추가: dev/main에서 이미 수정한 미커밋 작업을 새로운 이슈 브랜치로 이동
- 기존 Stage·unstaged·untracked 상태 유지, dirty worktree에서 `git switch dev` 및 `git pull` 생략
- 현재 HEAD가 원격 PR 기준 브랜치의 조상이 아닌 경우 Issue 생성 전에 중단해 다른 커밋이 PR에 섞이는 사고 방지
- 프로젝트 설정/템플릿은 유지하고 runtime만 갱신하는 `install.py --update-runtime` 지원
- 전역 Codex/Claude Skill의 adopt/update 지침과 실제 Git 통합 회귀 테스트 추가

## v0.3.0

- 사용자 전역 Codex/Claude Skill 등록 구조 유지
- 공식 사용 흐름을 VS Code 확장 중심에서 터미널 Codex CLI / Claude Code CLI 중심으로 변경
- 일반 터미널의 `gh auth status`를 GitHub 인증 검증 기준으로 명시
- IDE 확장에서만 발생하는 Keychain/sandbox 인증 차이를 제한사항으로 문서화
- `bootstrap.py` 설치 완료 안내를 터미널 CLI 기준으로 변경

## v0.2.0

- 사용자 전역 Codex/Claude Skill 등록용 `bootstrap.py` 추가
- VS Code 확장에서 프로젝트마다 Skill을 복사하지 않고 사용할 수 있는 전역 설치 흐름 추가
- `install.py --agents none`으로 프로젝트 런타임만 설치하는 모드 추가
- `github-taskflow install` Agent mode 추가
- clone 위치를 `~/.config/github-taskflow/source-path`에 기록해 전역 Skill이 distribution을 찾도록 변경

## v0.1.0

- 최초 공개
- GitHub Issue → branch → checks → staged commit → origin push → PR 자동화
- Claude Code/Codex 프로젝트 Skill 설치 지원
