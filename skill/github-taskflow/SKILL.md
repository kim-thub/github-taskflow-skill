---
name: github-taskflow
description: Operate this repository's scripts/taskflow.py workflow when the user explicitly asks to start a GitHub task, run task checks, finish/submit a task, push the task branch, or create its PR. Do not use for ordinary coding unless the user asks to operate the task workflow.
---

# GitHub Taskflow

Use the repository's existing `scripts/taskflow.py` as the source of truth. Do not reimplement its branch naming, checks, commit format, push target, or PR body logic.

The user's explicit request controls the mode. Arguments, when present, are: `$ARGUMENTS`.

## Preconditions

1. Work from the Git repository root.
2. Confirm `scripts/taskflow.py` and `scripts/taskflow.config.json` exist.
3. Use the repository's configured `base_branch` and checks; do not invent replacements.
4. Never change Git remotes as part of this skill.
5. Never use `--skip-check` unless the user explicitly asks to skip checks.

Use `python3 scripts/taskflow.py ...` on macOS/Linux. On Windows, use `py scripts\\taskflow.py ...` when `python3` is unavailable.

## Choose the mode

- **start**: the user explicitly asks to start, create, or open a new task/issue/branch.
- **check**: the user asks to inspect or run completion checks without submitting.
- **submit**: the user explicitly asks to finish, submit, push, or create the PR for the current task.

If the requested mode is genuinely unclear, ask one short question. Otherwise proceed.

## Start

1. Run `git status --short`. `start` requires a clean worktree; if it is dirty, stop and show the files that block the workflow.
2. Determine the task type from `feat`, `fix`, `refactor`, `style`, `test`, `docs`, `chore`. If the user's request does not make the type clear, ask for it.
3. Derive a concise Korean or project-language title from the user's requested work.
4. Read the configured issue template. Fill its existing sections from the user's task. Do not invent unrelated scope.
5. Write the issue body to `.git/taskflow-agent-issue.md`. This keeps the temporary file outside Git status.
6. Run non-interactively:
   `python3 scripts/taskflow.py start --type <type> --title <title> --body-file .git/taskflow-agent-issue.md`
7. Remove only `.git/taskflow-agent-issue.md` after the command finishes.
8. Verify `git branch --show-current`. Report the created issue URL and branch from command output.

Do not call the interactive `start` form from an agent.

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

- Dirty worktree on start: do not stash, clean, delete, or auto-commit existing work.
- No staged files on submit: stage only files clearly belonging to the current task as described above.
- Check failure: do not commit/push/PR until resolved, unless the user explicitly chose `--skip-check`.
- Push failure: do not create a PR manually until the push problem is resolved.
- PR creation failure after push: preserve the commit/branch and use the manual retry command printed by taskflow if the user asked you to complete submission.
- Multiple GitHub remotes with no `gh` default: do not guess the repository. Ask the user which repository should receive the issue/PR, or use the repository they explicitly named.

## More detail

Read `references/workflow.md` only when troubleshooting, adapting this skill to another repository, or explaining the workflow.
