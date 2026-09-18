import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
import bootstrap


class BootstrapTests(unittest.TestCase):
    def test_copy_mode_installs_both_global_skills_and_records_source(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            result = bootstrap.install_global_skills(ROOT, home, agents="both", mode="copy", force=False)

            self.assertEqual(result, 0)
            self.assertTrue((home / ".agents/skills/github-taskflow/SKILL.md").exists())
            self.assertTrue((home / ".claude/skills/github-taskflow/SKILL.md").exists())
            source = (home / ".config/github-taskflow/source-path").read_text(encoding="utf-8").strip()
            self.assertEqual(Path(source), ROOT.resolve())

    def test_link_mode_points_global_skills_to_clone(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            result = bootstrap.install_global_skills(ROOT, home, agents="codex", mode="link", force=False)

            self.assertEqual(result, 0)
            target = home / ".agents/skills/github-taskflow"
            self.assertTrue(target.is_symlink())
            self.assertEqual(target.resolve(), (ROOT / "skill/github-taskflow").resolve())
            self.assertFalse((home / ".claude/skills/github-taskflow").exists())

    def test_existing_global_skill_requires_force(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            destination = home / ".agents/skills/github-taskflow"
            destination.mkdir(parents=True)
            (destination / "keep.txt").write_text("keep", encoding="utf-8")

            result = bootstrap.install_global_skills(ROOT, home, agents="codex", mode="copy", force=False)

            self.assertEqual(result, 2)
            self.assertTrue((destination / "keep.txt").exists())


if __name__ == "__main__":
    unittest.main()
