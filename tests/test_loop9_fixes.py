"""Regressions for what the ninth self-run (headless init on a history-free copy of this repo) found."""
import unittest

from tests._support import PLUGIN, TempRepo, run_cli, write
from stackfoundry import rulebooks

SKILL = "---\nname: web-code-writer\ndescription: Writes web code. Use when editing web code.\n---\n\n# Web\n"


class TestingGlobsTests(unittest.TestCase):
    def test_a_helper_must_sit_under_a_test_folder_named_in_full(self):
        targets = {"targets": [{"name": "cli", "paths": ["plugins/x/scripts/**"],
                                "testPaths": ["tests/**", "plugins/x/evals/**"]}],
                   "rules": [{"glob": "plugins/x/hooks/**", "targets": ["cli"]},
                             {"glob": "plugins/x/evals/_lib.sh", "targets": ["cli"]},
                             {"glob": "tests/_support.py", "targets": ["cli"]}]}
        globs = rulebooks._globs("test path of every target", targets, {})
        self.assertIn("tests/_support.py", globs)
        self.assertIn("plugins/x/evals/_lib.sh", globs)
        self.assertNotIn("plugins/x/hooks/**", globs)  # shares only `plugins/` with a test path

    def test_a_test_glob_with_no_folder_adds_no_helpers(self):
        targets = {"targets": [{"name": "a", "paths": ["src/**"], "testPaths": ["**/test_*.py"]}],
                   "rules": [{"glob": "src/conftest.py", "targets": ["a"]}]}
        self.assertEqual(rulebooks._globs("test path of every target", targets, {}), ["**/test_*.py"])


class PlumbingSummaryTests(unittest.TestCase):
    def test_the_summary_says_how_many_skill_files_were_checked(self):
        with TempRepo({".claude/skills/web-code-writer/SKILL.md": SKILL,
                       ".agents/skills/web-code-writer/SKILL.md": SKILL}) as root:
            proc = run_cli(["verify-plumbing", str(root)])
        self.assertIn("1 skill(s) in 2 files", proc.stdout)


class InitWordingTests(unittest.TestCase):
    def test_init_strips_template_frontmatter_and_renders_profiles_after_the_rulebooks_and_gates(self):
        text = " ".join((PLUGIN / "skills/init/SKILL.md").read_text(encoding="utf-8").split())
        self.assertIn("A template's own frontmatter (`templateVersion`, `output`) is the plugin's bookkeeping", text)
        self.assertIn("for the prose, after the rulebooks are written", text)
        self.assertIn("and again in step 5 once the gates are recorded", text)


if __name__ == "__main__":
    unittest.main()
