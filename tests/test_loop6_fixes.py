"""Regressions for what the sixth self-run (headless init on a clone of this repo) found."""
import contextlib
import io
import unittest
from unittest import mock

from tests._support import HAS_GIT, TempRepo, git, run_cli, targets_json, write
from stackfoundry import cli, config, guard, rulebooks
from stackfoundry.change_targets import classify
from stackfoundry.frontmatter import split

PROFILE = {"docsRoot": "docs", "targets": [
    {"name": "plugin", "paths": ["pkg/skills/**", "pkg/*.md"], "testPaths": ["tests/test_plugin.py"]},
    {"name": "cli", "paths": ["pkg/scripts/**"], "testPaths": ["tests/test_cli.py"]},
], "rules": [
    {"glob": "tests/_support.py", "targets": ["plugin", "cli"]},
    {"glob": "docs/**", "targets": []},
]}


def profile(root_glob):
    data = {**PROFILE, "rules": PROFILE["rules"] + [{"glob": root_glob, "targets": []}]}
    return data


class ShadowedTests(unittest.TestCase):
    FILES = ["pkg/skills/init/SKILL.md", "pkg/README.md", "README.md", "pkg/scripts/cli.py", "docs/a.md"]

    def test_a_bare_root_glob_hiding_target_files_is_reported(self):
        result = classify(profile("*.md"), self.FILES)
        self.assertEqual([s["file"] for s in result["shadowed"]], ["pkg/skills/init/SKILL.md", "pkg/README.md"])
        self.assertEqual(result["shadowed"][0], {"file": "pkg/skills/init/SKILL.md", "rule": "*.md",
                                                 "targets": ["plugin"]})

    def test_an_anchored_root_glob_hides_nothing(self):
        result = classify(profile("/*.md"), self.FILES)
        self.assertEqual(result["shadowed"], [])
        self.assertEqual(result["targets"]["plugin"]["files"], ["pkg/skills/init/SKILL.md", "pkg/README.md"])
        self.assertIn("README.md", result["ignored"])

    def test_a_deliberate_no_target_folder_is_not_shadowing(self):
        self.assertEqual(classify(profile("/*.md"), ["docs/a.md"])["shadowed"], [])

    @unittest.skipUnless(HAS_GIT, "git not available")
    def test_all_maps_every_tracked_and_untracked_file(self):
        with TempRepo({f: "x\n" for f in self.FILES}) as root:
            targets_json(root, profile("*.md"))
            git(root, "init", "-q")
            git(root, "add", "pkg", "README.md")
            git(root, "commit", "-qm", "init")
            write(root, {"pkg/skills/new/SKILL.md": "x\n"})
            proc = run_cli(["change-targets", "--all", "--root", str(root)])
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("# Change targets (every file)", proc.stdout)
            self.assertIn("## Shadowed", proc.stdout)
            self.assertIn("- pkg/skills/new/SKILL.md: rule `*.md` hides it from plugin", proc.stdout)
            self.assertIn("anchor root files as `/<name>`", proc.stdout)


class TestingRulebookHelperTests(unittest.TestCase):
    def test_routed_test_helpers_are_covered(self):
        with TempRepo() as root:
            targets_json(root, PROFILE)
            _, text = rulebooks.render(root, "testing")
            fields, _, errors = split(text)
            self.assertEqual(errors, [])
            # The template adds the test-design folder under the docs root after the list.
            self.assertEqual(fields["paths"], ["tests/test_plugin.py", "tests/test_cli.py", "tests/_support.py",
                                               "docs/test-designs/**"])


class InternalErrorTests(unittest.TestCase):
    def run_main(self, argv):
        with contextlib.redirect_stderr(io.StringIO()) as err:
            code = cli.main(argv)
        return code, err.getvalue()

    def test_a_crash_in_a_command_exits_2_not_1(self):
        # 1 means "ran and found something": a bug must never read as a verdict.
        with mock.patch.object(config, "main", side_effect=TypeError("boom")):
            code, err = self.run_main(["config"])
        self.assertEqual(code, 2)
        self.assertIn("stackfoundry config: internal error: TypeError: boom", err)

    def test_a_crash_in_the_guard_has_no_opinion(self):
        # As a PreToolUse hook, exit 2 would block every tool call.
        with mock.patch.object(guard, "main", side_effect=KeyError("x")):
            code, _ = self.run_main(["guard"])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
