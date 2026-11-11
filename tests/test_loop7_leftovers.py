"""Regressions for the loop 7 leftovers: findings and researcher questions confirmed against the code afterwards."""
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests._support import HAS_GIT, PLUGIN, TempRepo, git, write
from stackfoundry import clients, guard, sideeffects
from stackfoundry.profile import PROFILE_DIR

GUARDS_PATH = (PROFILE_DIR / "guards.json").as_posix()


class DuplicateKeyTests(unittest.TestCase):
    def test_guard_check_names_a_key_given_twice(self):
        with TempRepo() as root:
            text = ('{"schemaVersion": 1, "commands": [{"pattern": "rm", "reason": "no"}],\n'
                    ' "commands": [{"pattern": "curl", "reason": "no"}]}\n')
            write(root, {GUARDS_PATH: text})
            problems = guard.check_file(root / GUARDS_PATH)
        self.assertIn("key 'commands' appears more than once; only the last one counts", problems)

    def test_the_hook_still_keeps_the_last_value(self):
        # Rejecting the file would switch every rule off, because the hook fails open on an unreadable file.
        with TempRepo() as root:
            write(root, {GUARDS_PATH: '{"schemaVersion": 1, "git": {"writes": "allow"}, "git": {"writes": "deny"}}'})
            self.assertEqual(guard._load(root)["git"], {"writes": "deny"})


@unittest.skipIf(os.name == "nt", "POSIX file modes")
class FileModeTests(unittest.TestCase):
    def test_a_rewritten_file_keeps_its_mode(self):
        with TempRepo({"AGENTS.md": "old\n"}) as root:
            os.chmod(root / "AGENTS.md", 0o644)
            clients._write(root, "AGENTS.md", "new\n")
            self.assertEqual(stat.S_IMODE((root / "AGENTS.md").stat().st_mode), 0o644)

    def test_a_new_file_gets_the_umask_mode_not_0600(self):
        old = os.umask(0o022)
        try:
            with TempRepo() as root:
                clients._write(root, ".claude/rules/web.md", "x\n")
                self.assertEqual(stat.S_IMODE((root / ".claude/rules/web.md").stat().st_mode), 0o644)
        finally:
            os.umask(old)


class SideEffectsStateTests(unittest.TestCase):
    @unittest.skipUnless(HAS_GIT, "git not available")
    def test_the_state_lives_in_the_repos_git_dir(self):
        with TempRepo() as root:
            git(root, "init", "-q")
            state = sideeffects._state_file(root)
            self.assertEqual(state.parent.parent.resolve(), (root / ".git").resolve())

    def test_without_git_the_state_is_under_the_users_home_not_the_shared_temp_folder(self):
        with TempRepo() as root, mock.patch.object(sideeffects, "run", side_effect=sideeffects.GitError("no git")):
            state = sideeffects._state_file(root)
        self.assertTrue(state.is_relative_to(Path.home() / ".stackfoundry"), state)
        self.assertFalse(state.is_relative_to(Path(tempfile.gettempdir())), state)


class WarningMarkerTests(unittest.TestCase):
    def test_a_planted_symlink_at_the_marker_never_creates_its_target(self):
        with TempRepo({GUARDS_PATH: "{ not json"}) as root, tempfile.TemporaryDirectory() as tmp:
            event = {"session_id": "s1"}
            with mock.patch("tempfile.gettempdir", return_value=tmp):
                self.assertIsNotNone(guard._unreadable_warning(event, root, root))
                marker = next(Path(tmp).glob("stackfoundry-guard-warned-*"))
                marker.unlink()
                victim = Path(tmp) / "victim"
                try:
                    marker.symlink_to(victim)
                except OSError:
                    self.skipTest("cannot create symlinks here")
                guard._unreadable_warning(event, root, root)
            self.assertFalse(victim.exists())


class CopilotMatcherTests(unittest.TestCase):
    def test_the_hook_matcher_names_every_tool_the_guard_maps(self):
        hooks = json.loads((PLUGIN / "com.github.copilot/hooks/hooks.json").read_text(encoding="utf-8"))
        matched = set(hooks["hooks"]["preToolUse"][0]["matcher"].split("|"))
        candidates = ("create", "edit", "write", "str_replace_editor", "apply_patch", "bash", "powershell", "view")
        mapped = {t for t in candidates
                  if guard.normalize({"toolName": t, "toolArgs": {}}, "copilot", Path.cwd()) is not None}
        self.assertIn("write", mapped)
        self.assertEqual(mapped - matched, set())


if __name__ == "__main__":
    unittest.main()
