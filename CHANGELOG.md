# Changelog

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
