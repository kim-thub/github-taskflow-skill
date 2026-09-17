# Contributing

1. Create a focused issue before changing behavior.
2. Keep the Skill orchestration thin; workflow behavior belongs in `runtime/taskflow.py`.
3. Preserve safety boundaries: no automatic stash/clean, no broad `git add`, no upstream push, no automatic PR merge.
4. Add or update tests for installer/runtime behavior changes.
5. Run `python3 -m unittest discover -s tests -v` before opening a PR.
