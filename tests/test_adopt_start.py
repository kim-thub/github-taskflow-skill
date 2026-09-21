"""Real Git integration tests for safe adoption of work started on dev/main."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AdoptStartTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.repo = self.base / "project"
        self.repo.mkdir()
        self.remote = self.base / "remote.git"
        self._git("init", "--bare", "--initial-branch=dev", str(self.remote), cwd=self.base)
        self._git("init", "--initial-branch=dev")
        self._git("config", "user.name", "Taskflow Test")
        self._git("config", "user.email", "taskflow@example.invalid")
        self._git("remote", "add", "origin", str(self.remote))
        (self.repo / "scripts").mkdir()
        shutil.copy2(ROOT / "runtime/taskflow.py", self.repo / "scripts/taskflow.py")
        (self.repo / "scripts/taskflow.config.json").write_text(json.dumps({
            "base_branch": "dev", "issue_template": ".github/ISSUE_TEMPLATE/taskflow.md",
            "pull_request_template": ".github/PULL_REQUEST_TEMPLATE.md", "checks": {},
        }), encoding="utf-8")
        issue_template = self.repo / ".github/ISSUE_TEMPLATE/taskflow.md"
        issue_template.parent.mkdir(parents=True)
        issue_template.write_text("## 목적\n작업\n", encoding="utf-8")
        (self.repo / "tracked.txt").write_text("initial\n", encoding="utf-8")
        (self.repo / "issue.md").write_text("## 목적\n테스트\n", encoding="utf-8")
        self._git("add", "scripts", ".github", "tracked.txt", "issue.md")
        self._git("commit", "-m", "initial")
        self._git("push", "-u", "origin", "dev")
        self.bin = self.base / "bin"
        self.bin.mkdir()
        self.gh_log = self.base / "gh.log"
        fake_gh = self.bin / "gh"
        fake_gh.write_text("""#!/usr/bin/env python3
import os, pathlib, sys
args = sys.argv[1:]
with pathlib.Path(os.environ['FAKE_GH_LOG']).open('a') as f:
    f.write(' '.join(args) + '\\n')
if args[:2] == ['auth', 'status']:
    sys.exit(0)
if args[:2] == ['issue', 'create']:
    print('https://github.com/example/project/issues/42')
    sys.exit(0)
print('unexpected gh command', file=sys.stderr)
sys.exit(1)
""", encoding="utf-8")
        fake_gh.chmod(0o755)

    def _git(self, *args, cwd=None):
        result = subprocess.run(["git", *args], cwd=cwd or self.repo, text=True, capture_output=True)
        if result.returncode:
            raise AssertionError(f"git {' '.join(args)} failed: {result.stderr}")
        return result.stdout.strip()

    def _start(self, *more):
        env = os.environ.copy()
        env["PATH"] = str(self.bin) + os.pathsep + env.get("PATH", "")
        env["FAKE_GH_LOG"] = str(self.gh_log)
        return subprocess.run(
            [sys.executable, "scripts/taskflow.py", "start", *more,
             "--type", "feat", "--title", "기존작업 옮기기", "--body-file", "issue.md"],
            cwd=self.repo, env=env, text=True, capture_output=True,
        )

    def _dirty(self):
        file = self.repo / "tracked.txt"
        file.write_text("initial\nstaged\n", encoding="utf-8")
        self._git("add", "tracked.txt")
        file.write_text("initial\nstaged\nunstaged\n", encoding="utf-8")
        (self.repo / "new.txt").write_text("untracked\n", encoding="utf-8")

    def _snapshot(self):
        return (
            self._git("status", "--porcelain", "-uall"),
            self._git("diff", "--binary"),
            self._git("diff", "--cached", "--binary"),
            (self.repo / "tracked.txt").read_bytes(),
            (self.repo / "new.txt").read_bytes(),
        )

    def _assert_no_issue(self):
        log = self.gh_log.read_text(encoding="utf-8") if self.gh_log.exists() else ""
        self.assertNotIn("issue create", log)

    def test_adopt_preserves_staged_unstaged_untracked_and_base_tip(self):
        base_head = self._git("rev-parse", "HEAD")
        self._dirty()
        before = self._snapshot()
        result = self._start("--adopt")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self._snapshot(), before)
        self.assertEqual(self._git("rev-parse", "HEAD"), base_head)
        self.assertEqual(self._git("rev-parse", "dev"), base_head)
        self.assertTrue(self._git("branch", "--show-current").startswith("42-feat-"))
        self.assertIn("issue create", self.gh_log.read_text(encoding="utf-8"))
        self.assertIn("유지한 채", result.stdout)

    def test_adopt_from_main_when_main_head_is_ancestor_of_dev(self):
        self._git("switch", "-c", "main")
        self._dirty()
        before = self._snapshot()
        result = self._start("--adopt")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self._snapshot(), before)
        self.assertEqual(self._git("rev-parse", "main"), self._git("rev-parse", "dev"))
        self.assertIn("현재 브랜치는 main", result.stdout)

    def test_adopt_from_main_when_dev_has_newer_commits(self):
        self._git("switch", "-c", "main")
        self._git("switch", "dev")
        (self.repo / "dev-only.txt").write_text("dev progress\n", encoding="utf-8")
        self._git("add", "dev-only.txt")
        self._git("commit", "-m", "dev moved ahead")
        self._git("push", "origin", "dev")
        self._git("switch", "main")
        self._dirty()
        before = self._snapshot()
        result = self._start("--adopt")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self._snapshot(), before)
        self.assertNotEqual(self._git("rev-parse", "HEAD"), self._git("rev-parse", "dev"))
        self.assertEqual(self._git("rev-parse", "main"), self._git("rev-parse", "HEAD"))

    def test_reject_committed_local_changes_on_dev_before_issue(self):
        (self.repo / "tracked.txt").write_text("committed\n", encoding="utf-8")
        self._git("add", "tracked.txt")
        self._git("commit", "-m", "unrelated commit on dev")
        self._dirty()
        before = self._snapshot()
        result = self._start("--adopt")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("HEAD가 origin/dev의 조상이 아닙니다", result.stdout)
        self.assertEqual(self._git("branch", "--show-current"), "dev")
        self.assertEqual(self._snapshot(), before)
        self._assert_no_issue()

    def test_reject_main_with_unique_commits(self):
        self._git("switch", "-c", "main")
        (self.repo / "tracked.txt").write_text("committed\n", encoding="utf-8")
        self._git("add", "tracked.txt")
        self._git("commit", "-m", "main-only commit")
        self._dirty()
        result = self._start("--adopt")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self._git("branch", "--show-current"), "main")
        self._assert_no_issue()

    def test_reject_adopt_on_feature_branch_without_issue(self):
        self._git("switch", "-c", "other-feature")
        self._dirty()
        result = self._start("--adopt")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("기준 브랜치에서만", result.stdout)
        self._assert_no_issue()

    def test_reject_dirty_normal_start_and_suggest_adopt(self):
        self._dirty()
        result = self._start()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("start --adopt", result.stdout)
        self.assertEqual(self._git("branch", "--show-current"), "dev")
        self._assert_no_issue()

    def test_reject_adopt_without_uncommitted_changes(self):
        result = self._start("--adopt")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("옮길 미커밋 변경사항이 없습니다", result.stdout)
        self._assert_no_issue()

    def test_normal_clean_start_unchanged(self):
        result = self._start()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(self._git("branch", "--show-current").startswith("42-feat-"))


if __name__ == "__main__":
    unittest.main()
