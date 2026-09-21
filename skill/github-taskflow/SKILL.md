---
name: github-taskflow
description: Install and operate GitHub Taskflow in the current Git repository. Use when the user asks to install/update taskflow, start a GitHub task, move uncommitted work from dev/main into a new issue branch, run checks, or finish/submit a PR. Designed primarily for terminal Codex CLI or Claude Code CLI.
---

# GitHub Taskflow

Use GitHub Taskflow's Python runtime as the source of truth. Do not reimplement its branch naming, checks, commit format, push target, or PR body logic.

The user's explicit request controls the mode. Arguments, when present, are: `$ARGUMENTS`.

## Choose the mode

- **install**: the user asks to install/setup/add GitHub Taskflow to the currently opened repository.
- **update**: the user asks to update a project's existing Taskflow runtime, preserving its configuration and templates.
- **start**: the user explicitly asks to start, create, or open a new task/issue/branch.
- **adopt**: the user asks to move work already started but not committed on `dev`/`main` into a new task branch.
- **check**: the user asks to inspect or run completion checks without submitting.
- **submit**: the user explicitly asks to finish, submit, push, or create the PR for the current task.

If the requested mode is genuinely unclear, ask one short question. Otherwise proceed.

## Global installation contract

This skill may be installed at user scope while the distribution repository is cloned somewhere else.

The bootstrap installer records that clone location in:

```text
~/.config/github-taskflow/source-path
```

Do not assume the distribution clone is inside the current project.

## Install into the current project

1. Find the current Git repository root with `git rev-parse --show-toplevel`.
2. Confirm `~/.config/github-taskflow/source-path` exists. If it does not, tell the user to run `python3 bootstrap.py --agents both` from their cloned `github-taskflow-skill` repository and restart the current Agent CLI session.
3. Determine the project's base branch. Use a base branch explicitly supplied by the user. If none was supplied and it cannot be determined confidently from existing team conventions, ask one short question rather than guessing.
4. Read the distribution root from the source-path file.
5. Run the installer with project-local skill copies disabled:

   ```bash
   SOURCE="$(cat "$HOME/.config/github-taskflow/source-path")"
   ROOT="$(git rev-parse --show-toplevel)"
   python3 "$SOURCE/install.py" --target "$ROOT" --agents none --base-branch <base-branch>
   ```

   On Windows, use the Python executable available to the user and the equivalent user config path when needed.
6. Read `scripts/taskflow.config.json` in the target project and report its path. Do not invent project-specific build/lint/test commands. If the default checks do not match the project, ask the user whether to configure them or handle that as a separate requested task.
7. Verify these files now exist in the project:

   ```text
   scripts/taskflow.py
   scripts/taskflow.config.json
   scripts/start-task
   scripts/finish-task
   ```

Project-local `.agents/skills` or `.claude/skills` copies are not required when this user-level skill is already installed.

## Update existing project runtime

Global Skill registration does not automatically update `scripts/taskflow.py` already copied into a project. When the user requests v0.4.0 support in an existing project, read the source-path file, find the project root and run:

```bash
SOURCE="$(cat "$HOME/.config/github-taskflow/source-path")"
ROOT="$(git rev-parse --show-toplevel)"
python3 "$SOURCE/install.py" --target "$ROOT" --update-runtime
```

This explicitly updates the three managed runtime scripts only; it leaves `scripts/taskflow.config.json`, `.github/` templates and both Skill installations untouched. Before updating, inspect `git status --short` and warn if the three runtime scripts have user edits; never overwrite an ambiguous user customization without consent.

## Runtime environment

The primary supported environment is Codex CLI or Claude Code CLI launched from a normal terminal in the target repository. Before GitHub operations, use the same environment to run `gh auth status`.

If `gh auth status` succeeds in the user's terminal but fails only inside an IDE extension, do not conclude that the stored GitHub token is invalid. Report the environment mismatch and recommend retrying from the terminal Agent CLI. Do not print, request, or expose token values while diagnosing.

## Preconditions for start/check/submit

1. Work from the Git repository root.
2. Confirm `scripts/taskflow.py` and `scripts/taskflow.config.json` exist. If missing, use **install** instead of inventing commands.
3. Use the repository's configured `base_branch` and checks; do not invent replacements.
4. Never change Git remotes as part of this skill.
5. Never use `--skip-check` unless the user explicitly asks to skip checks.

Use `python3 scripts/taskflow.py ...` on macOS/Linux. On Windows, use `py scripts\\taskflow.py ...` when `python3` is unavailable.

## Start

1. Run `git status --short` and `git branch --show-current`. On a clean worktree use the normal `start` flow. When work is already modified on `dev`/`main`, use **adopt** only if the user explicitly asked to move that work into a branch; otherwise show the paths and ask for confirmation before adopting them. If any change is unrelated or ambiguous, do not silently carry it into the task branch.
2. Determine the task type from `feat`, `fix`, `refactor`, `style`, `test`, `docs`, `chore`. If the user's request does not make the type clear, ask for it.
3. Derive a concise Korean or project-language title from the user's requested work.
4. Read the configured issue template. Fill its existing sections from the user's task. Do not invent unrelated scope.
5. Write the issue body to `.git/taskflow-agent-issue.md`. This keeps the temporary file outside Git status.
6. Run non-interactively:
   - Clean worktree: `python3 scripts/taskflow.py start --type <type> --title <title> --body-file .git/taskflow-agent-issue.md`
   - User-approved, uncommitted work on `dev`/`main`: `python3 scripts/taskflow.py start --adopt --type <type> --title <title> --body-file .git/taskflow-agent-issue.md`
7. Remove only `.git/taskflow-agent-issue.md` after the command finishes.
8. Verify `git branch --show-current`. Report the created issue URL and branch from command output.

Do not call the interactive `start` form from an agent.

`--adopt` fetches the configured remote base to check commit ancestry, but does not switch to that branch, pull into the dirty tree, stash, clean, stage, commit, or reset files. The current HEAD must be an ancestor of `origin/<base_branch>` (or the explicitly configured start remote). Existing changes, including Stage state and untracked files, remain intact on the new branch. If already committed work exists on `dev`/`main` outside the remote PR base history, stop **before creating an issue** and explain that moving those commits requires separate user-approved recovery. Do not run `git reset`, `git cherry-pick`, or force-push on a shared base branch automatically.

## Check

1. Run `python3 scripts/taskflow.py finish`.
2. If a configured check fails, stop submission work and fix or report that failure according to the user's request.
3. If the user requested checks only, stop after reporting the check result. Do not stage, commit, push, or create a PR.

## Submit

Treat an explicit request to **finish/submit/push/create the PR** as authorization for the taskflow's commit, `origin` push, and PR creation. Do not treat a generic coding request as that authorization.

1. Run `python3 scripts/taskflow.py finish` first. Continue only if checks pass, unless the user explicitly requested `--skip-check`.
2. Inspect `git status --short`, `git diff`, and any existing staged diff.
3. Determine which changed files belong to the current task from the conversation, current issue/branch, and diff.
4. Stage only explicit task-related paths with `git add -- <path>...`. Never use `git add .` or `git add -A`.
5. If any changed file is unrelated or its inclusion is ambiguous, leave it unstaged. Ask the user only when you cannot determine whether a file must be included for this task.
6. Verify the staged set with `git diff --cached --name-only` and review `git diff --cached`.
7. Derive a short commit summary from the staged change unless the user supplied one.
8. Run:
   `python3 scripts/taskflow.py finish --continue --summary <summary> --yes`
   Add `--skip-check` only when the user explicitly requested it.
9. Verify the result with `git status --short` and, when PR creation succeeded, `gh pr view --json number,url,baseRefName,headRefName`.
10. Report the commit/PR result. Do not merge the PR or delete the branch.

## Failure boundaries

- Dirty worktree on start: preserve it; only use `start --adopt` for confirmed uncommitted work on `dev`/`main`. Never stash, clean, delete, or auto-commit existing work.
- Committed work on the base branch: `--adopt` refuses history that would add unrelated commits to a PR. Do not rewrite shared branch history automatically.
- No staged files on submit: stage only files clearly belonging to the current task as described above.
- Check failure: do not commit/push/PR until resolved, unless the user explicitly chose `--skip-check`.
- Push failure: do not create a PR manually until the push problem is resolved.
- PR creation failure after push: preserve the commit/branch and use the manual retry command printed by taskflow if the user asked you to complete submission.
- Multiple GitHub remotes with no `gh` default: do not guess the repository. Ask the user which repository should receive the issue/PR, or use the repository they explicitly named.

## More detail

Read `references/workflow.md` only when troubleshooting, adapting this skill to another repository, or explaining the workflow.
