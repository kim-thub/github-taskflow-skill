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

    def test_runtime_only_install_skips_project_skill_copies(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / ".git").mkdir()
            result = self.run_install(target, "--agents", "none")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((target / "scripts/taskflow.py").exists())
            self.assertFalse((target / ".agents").exists())
            self.assertFalse((target / ".claude").exists())

    def test_rejects_non_git_target(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_install(Path(directory))
            self.assertEqual(result.returncode, 2)
            self.assertIn("not a Git repository", result.stderr)

    def test_update_runtime_preserves_team_config_and_existing_templates(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / ".git").mkdir()
            self.assertEqual(self.run_install(target, "--agents", "none").returncode, 0)
            config = target / "scripts/taskflow.config.json"
            custom = '{"base_branch":"release", "checks":{"custom":{"paths":[],"cwd":".","commands":[]}}}\n'
            config.write_text(custom, encoding="utf-8")
            template = target / ".github/PULL_REQUEST_TEMPLATE.md"
            template.write_text("TEAM TEMPLATE\n", encoding="utf-8")
            runtime = target / "scripts/taskflow.py"
            runtime.write_text("OLD RUNTIME\n", encoding="utf-8")
            result = self.run_install(target, "--update-runtime")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("--adopt", runtime.read_text(encoding="utf-8"))
            self.assertEqual(config.read_text(encoding="utf-8"), custom)
            self.assertEqual(template.read_text(encoding="utf-8"), "TEAM TEMPLATE\n")

    def test_update_runtime_rejects_project_without_installed_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / ".git").mkdir()
            result = self.run_install(target, "--update-runtime")
            self.assertEqual(result.returncode, 2)
            self.assertIn("requires an existing", result.stderr)


if __name__ == "__main__":
    unittest.main()
