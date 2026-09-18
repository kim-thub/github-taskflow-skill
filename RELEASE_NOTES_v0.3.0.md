# GitHub Taskflow Skill v0.3.0

v0.3.0 keeps the global Codex/Claude Skill installation introduced in v0.2.0, but makes terminal Agent CLIs the primary supported execution environment.

## Changes

- Keep global Skill registration for Codex and Claude
- Use Codex CLI / Claude Code CLI from a normal terminal as the recommended workflow
- Document `gh auth status` in the normal terminal as the GitHub authentication baseline
- Document IDE extension sandbox/Keychain differences as an environment-specific limitation
- Update bootstrap guidance for terminal-first usage

## Recommended setup

```bash
git clone https://github.com/kim-thub/github-taskflow-skill.git ~/tools/github-taskflow-skill
cd ~/tools/github-taskflow-skill
python3 bootstrap.py --agents both --mode link
```

Then open a project in a normal terminal and run Codex CLI or Claude Code CLI.
