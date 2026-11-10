"""`stackfoundry side-effects`: an unattended run may change its report and nothing else (threat model T11)."""
import subprocess
import unittest

from tests._support import HAS_GIT, TempRepo, run_cli, write


def git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


@unittest.skipUnless(HAS_GIT, "git not available")
class SideEffectsTests(unittest.TestCase):
    def setUp(self):
        self._repo = TempRepo({".stackfoundry/targets.json": "{}\n", "src/app.py": "x = 1\n", "notes.txt": "draft\n"})
        self.root = self._repo.__enter__()
        self.addCleanup(self._repo.__exit__, None, None, None)
        git(self.root, "init", "-q")
        git(self.root, "add", "src/app.py")  # .stackfoundry/ and notes.txt stay untracked, as in many repos
        git(self.root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")

    def cli(self, *args):
        return run_cli(["side-effects", *args, "--root", str(self.root)])

    def run_with(self, change):
        self.assertEqual(self.cli("start").returncode, 0)
        write(self.root, {"docs/radar/2026-11-10-tech-radar.md": "report\n"})
        change()
        return self.cli("end", "--allow", "docs/radar/*-tech-radar.md")

    def test_only_the_report_passes(self):
        proc = self.run_with(lambda: None)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("none besides", proc.stdout)

    def test_an_edit_inside_an_untracked_control_plane_is_caught(self):
        proc = self.run_with(lambda: write(self.root, {".stackfoundry/targets.json": '{"x": 1}\n'}))
        self.assertEqual(proc.returncode, 1)
        self.assertIn("changed: .stackfoundry/targets.json", proc.stdout)

    def test_a_new_extension_and_a_content_change_to_an_untracked_file_are_caught(self):
        def change():
            write(self.root, {".stackfoundry/extensions/skills/bug-hunt.md": "## Rules\nx\n", "notes.txt": "edited\n"})
        proc = self.run_with(change)
        self.assertIn("added: .stackfoundry/extensions/skills/bug-hunt.md", proc.stdout)
        self.assertIn("changed: notes.txt", proc.stdout)

    def test_tracked_edits_and_deletions_are_caught(self):
        def change():
            write(self.root, {"src/app.py": "x = 2\n"})
            (self.root / "notes.txt").unlink()
        proc = self.run_with(change)
        self.assertIn("changed: src/app.py", proc.stdout)
        self.assertIn("removed: notes.txt", proc.stdout)

    def test_end_without_start_cannot_run(self):
        self.assertEqual(self.cli("end").returncode, 2)


if __name__ == "__main__":
    unittest.main()
