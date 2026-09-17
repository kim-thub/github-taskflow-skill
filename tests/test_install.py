import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class InstallTests(unittest.TestCase):
    def run_install(self, target: Path, *args: str):
        return subprocess.run(
            [sys.executable, str(ROOT / "install.py"), "--target", str(target), *args],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_installs_runtime_and_both_skills(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / ".git").mkdir()
            result = self.run_install(target, "--base-branch", "main")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((target / "scripts/taskflow.py").exists())
            self.assertTrue((target / ".agents/skills/github-taskflow/SKILL.md").exists())
            self.assertTrue((target / ".claude/skills/github-taskflow/SKILL.md").exists())
            config = json.loads((target / "scripts/taskflow.config.json").read_text(encoding="utf-8"))
            self.assertEqual(config["base_branch"], "main")

    def test_does_not_overwrite_existing_config_without_force(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / ".git").mkdir()
            (target / "scripts").mkdir()
            config = target / "scripts/taskflow.config.json"
            config.write_text('{"base_branch":"release"}\n', encoding="utf-8")
            result = self.run_install(target)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(config.read_text())["base_branch"], "release")

    def test_rejects_non_git_target(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_install(Path(directory))
            self.assertEqual(result.returncode, 2)
            self.assertIn("not a Git repository", result.stderr)


if __name__ == "__main__":
    unittest.main()
