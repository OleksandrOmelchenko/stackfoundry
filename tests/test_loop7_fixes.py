"""Regressions for what the seventh self-run (headless init on a history-free copy of this repo) found."""
import json
import unittest
from unittest import mock

from tests._support import TempRepo, write
from stackfoundry import clients, globs, guard, roles

GUARDS = {"schemaVersion": 1, "generated": [{"glob": "app/generated/**", "regenerate": "run make client"}]}


class CaseFoldTests(unittest.TestCase):
    """On Windows and macOS `APP/Generated/x.py` is `app/generated/x.py`: the guard must not let the edit through."""

    def decide(self, root, path, agent=None):
        event = {"hook_event_name": "PreToolUse", "tool_name": "Edit", "tool_input": {"file_path": path},
                 "cwd": str(root), "session_id": "case-fold-test"}
        if agent:
            event["agent_type"] = agent
        out = guard.decide(event, root, "claude-code")
        return json.loads(out)["hookSpecificOutput"] if out else None

    def test_a_generated_file_in_other_case_is_denied_on_a_case_insensitive_file_system(self):
        with TempRepo({"app/generated/client.py": "x = 1\n"}) as root:
            write(root, {".stackfoundry/guards.json": json.dumps(GUARDS)})
            with mock.patch.object(guard, "CASE_INSENSITIVE_FS", True):
                out = self.decide(root, str(root / "APP" / "Generated" / "client.py"))
            self.assertEqual(out["permissionDecision"], "deny")
            self.assertIn("run make client", out["permissionDecisionReason"])

    def test_a_case_sensitive_file_system_keeps_exact_matching(self):
        with TempRepo() as root:
            write(root, {".stackfoundry/guards.json": json.dumps(GUARDS)})
            with mock.patch.object(guard, "CASE_INSENSITIVE_FS", False):
                self.assertIsNone(self.decide(root, str(root / "APP" / "Generated" / "client.py")))

    def test_the_control_plane_in_other_case_still_asks(self):
        with TempRepo() as root:
            with mock.patch.object(roles, "CASE_INSENSITIVE_FS", True):
                out = self.decide(root, str(root / ".STACKFOUNDRY" / "Guards.json"), agent="stackfoundry:bug-hunter")
            self.assertEqual(out["permissionDecision"], "ask")

    def test_a_glob_takes_the_whole_path(self):
        # `^…$` with match() accepted a trailing newline.
        self.assertTrue(globs.match("app/generated/x.py", "app/generated/**"))
        self.assertFalse(globs.match("README.md\n", "/README.md"))
        self.assertTrue(globs.match("App/Generated/X.py", "app/generated/**", ignore_case=True))
        self.assertFalse(globs.match("App/Generated/X.py", "app/generated/**"))


class SiblingLinkTests(unittest.TestCase):
    RULEBOOK = ("---\ndescription: Python rules\npaths:\n  - \"src/**\"\n---\n\n# Python\n\n"
                "See [the tests rulebook](tooling-unittest.md#mocks) and [testing](testing.md); "
                "[design](../../docs/design.md) and [web](https://example.com/a.md) stay as they are.\n")

    def test_copilot_and_cursor_copies_link_to_their_own_sibling_files(self):
        copilot = clients.render_rule(self.RULEBOOK, "copilot")
        self.assertIn("[the tests rulebook](tooling-unittest.instructions.md#mocks)", copilot)
        self.assertIn("[testing](testing.instructions.md)", copilot)
        cursor = clients.render_rule(self.RULEBOOK, "cursor")
        self.assertIn("(tooling-unittest.mdc#mocks)", cursor)
        for text in (copilot, cursor):
            self.assertIn("[design](../../docs/design.md)", text)
            self.assertIn("[web](https://example.com/a.md)", text)

    def test_claude_code_copies_keep_the_body_byte_for_byte(self):
        self.assertTrue(clients.render_rule(self.RULEBOOK, "claude-code").endswith(self.RULEBOOK.split("---\n", 2)[2]))


if __name__ == "__main__":
    unittest.main()
