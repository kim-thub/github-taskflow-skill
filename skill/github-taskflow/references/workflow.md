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

For a clean worktree, `start` performs:

```text
git switch <base_branch>
git pull --ff-only origin <base_branch>
gh issue create
git switch -c <issue>-<type>-<slug>
```

For a team member who already modified files on `dev` or `main` but has **not committed** them, explicit `start --adopt` performs:

```text
git status --porcelain
git branch --show-current
git fetch origin <base_branch>
git merge-base --is-ancestor HEAD origin/<base_branch>
gh issue create
git switch -c <issue>-<type>-<slug>  # from the SAME current HEAD
```

This preserves staged edits, unstaged edits and untracked files; `--adopt` never switches to the configured base or pulls while work is dirty. When starting on `main` with `dev` configured as the PR base, `main`'s HEAD must be an ancestor of `origin/dev` to avoid mixing unrelated committed work into the PR. The new branch may be behind the target base; no rebase or merge is performed automatically. If ancestry check fails, it stops before creating the issue. Already-committed changes on `dev`/`main` require a separate reviewed recovery procedure; do not `reset --hard` or force-push a shared branch.

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
| dirty start worktree | If work is already underway on `dev`/`main`, obtain approval for `start --adopt`; never clean or stash automatically. |
| `--adopt` refuses commit ancestry | Existing commits are not solely part of the configured remote base; review history first, never auto-reset or force-push. |
| missing `origin/<base_branch>` | Verify repository setup; do not rewrite remotes. |
| issue created but branch creation failed | Preserve issue URL and use taskflow's printed branch command. |
| check failed | Fix the failing command and rerun `finish`. |
| push failed | Resolve auth/remote/rejection before PR creation. |
| PR create failed after push | Retry with taskflow's printed `gh pr create --base ... --head ...`. |
| `gh` cannot choose repository | Ask for the intended GitHub repo instead of guessing. |

## Updating an already installed project

`python3 <distribution>/install.py --target <repo> --update-runtime` replaces only `scripts/taskflow.py`, `scripts/start-task` and `scripts/finish-task`. It intentionally retains project-specific `scripts/taskflow.config.json`, GitHub templates and existing Skill registrations. Do not use `--force` for a routine runtime update because it also replaces templates/configuration.

## User-level / terminal CLI installation

For a single clone that serves many projects, register the skill at user scope with `bootstrap.py`.

```text
~/tools/github-taskflow-skill/               # distribution clone
~/.agents/skills/github-taskflow/           # Codex user skill
~/.claude/skills/github-taskflow/           # Claude user skill
~/.config/github-taskflow/source-path        # points back to distribution clone
```

The user-level skill can then install only the runtime into any repository where Codex CLI or Claude Code CLI is launched:

```text
<opened project>/scripts/taskflow.py
<opened project>/scripts/taskflow.config.json
<opened project>/scripts/start-task
<opened project>/scripts/finish-task
```

This keeps the agent skill out of every project while keeping project-specific configuration in the project.


## IDE extension note

The primary validation target for v0.3.0 is a normal terminal running Codex CLI or Claude Code CLI. IDE extensions may use a different sandbox or credential environment. If `gh auth status` succeeds in the normal terminal but fails only in an IDE Agent environment, treat that as an environment-specific authentication/access issue rather than automatically replacing the user's GitHub credentials.
