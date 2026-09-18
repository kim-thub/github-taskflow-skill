#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

AGENTS = ("codex", "claude", "both")
MODES = ("copy", "link")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Register GitHub Taskflow as a user-level Codex/Claude skill for VS Code and CLI use."
    )
    p.add_argument("--agents", choices=AGENTS, default="both")
    p.add_argument(
        "--mode",
        choices=MODES,
        default="copy",
        help="copy is cross-platform; link keeps the skill live with git pull updates",
    )
    p.add_argument("--force", action="store_true", help="Replace an existing global github-taskflow skill")
    return p


def _destination_map(home: Path, agents: str) -> list[Path]:
    destinations: list[Path] = []
    if agents in {"codex", "both"}:
        destinations.append(home / ".agents/skills/github-taskflow")
    if agents in {"claude", "both"}:
        destinations.append(home / ".claude/skills/github-taskflow")
    return destinations


def _remove_existing(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path)


def install_global_skills(source_root: Path, home: Path, *, agents: str, mode: str, force: bool) -> int:
    source_root = source_root.resolve()
    skill_source = source_root / "skill/github-taskflow"
    if not (skill_source / "SKILL.md").exists():
        print(f"error: skill source not found: {skill_source}", file=sys.stderr)
        return 2

    destinations = _destination_map(home, agents)
    conflicts = [path for path in destinations if path.exists() or path.is_symlink()]
    if conflicts and not force:
        for path in conflicts:
            print(f"error: global skill already exists: {path} (use --force to replace)", file=sys.stderr)
        return 2

    for destination in destinations:
        if destination.exists() or destination.is_symlink():
            _remove_existing(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if mode == "link":
            destination.symlink_to(skill_source, target_is_directory=True)
        else:
            shutil.copytree(skill_source, destination)
        print(f"write {destination}")

    config_dir = home / ".config/github-taskflow"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "source-path").write_text(str(source_root) + "\n", encoding="utf-8")
    print(f"write {config_dir / 'source-path'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    source_root = Path(__file__).resolve().parent
    result = install_global_skills(
        source_root,
        Path.home(),
        agents=args.agents,
        mode=args.mode,
        force=args.force,
    )
    if result == 0:
        print("\nNext:")
        print("  1. Reload VS Code (Developer: Reload Window) or restart the agent extension")
        print("  2. Open any Git project")
        print("  3. Ask: '이 프로젝트에 github-taskflow 설치해줘. base branch는 dev야.'")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
