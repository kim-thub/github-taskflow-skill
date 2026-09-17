# Workflow reference

## Repository contract

The skill expects these repository files:

```text
scripts/taskflow.py
scripts/taskflow.config.json
.github/ISSUE_TEMPLATE/...
.github/PULL_REQUEST_TEMPLATE.md
```

Typical configuration:

```json
{
  "base_branch": "dev",
  "issue_template": ".github/ISSUE_TEMPLATE/issue-template.md",
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

## Start behavior

`start` performs:

```text
git switch <base_branch>
git pull --ff-only origin <base_branch>
gh issue create
git switch -c <issue>-<type>-<slug>
```

The team model assumes `origin` is the repository used by team members. Fork-based workflows need an explicit repository policy and should not be inferred by the skill.

## Finish behavior

The first `finish` run is read/check-only with respect to Git history and remotes. It selects checks from changed paths.

Submission performs:

```text
staged files only -> commit
git push --set-upstream origin <task-branch>
gh pr create --base <base_branch> --head <task-branch>
```

The taskflow itself never auto-stages. This skill may stage explicit paths only after reviewing the diff and only for an explicit submit request.

## Agent-only noninteractive flag

`finish --yes` is intended for an explicitly invoked agent submission flow. It is valid only together with `--continue`. It skips the CLI confirmation prompt; it does not skip checks, staging validation, commit, push, or PR error handling.

## Recovery

| Symptom | Action |
| --- | --- |
| `gh` auth failure | Run/ask user to run `gh auth login`, then retry. |
| dirty start worktree | Show `git status --short`; do not clean or stash automatically. |
| missing `origin/<base_branch>` | Verify repository setup; do not rewrite remotes. |
| issue created but branch creation failed | Preserve issue URL and use taskflow's printed branch command. |
| check failed | Fix the failing command and rerun `finish`. |
| push failed | Resolve auth/remote/rejection before PR creation. |
| PR create failed after push | Retry with taskflow's printed `gh pr create --base ... --head ...`. |
| `gh` cannot choose repository | Ask for the intended GitHub repo instead of guessing. |
