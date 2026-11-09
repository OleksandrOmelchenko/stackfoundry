"""The guard as each assistant drives it: that assistant's event on stdin, its answer format on stdout.

Event shapes follow each assistant's hook documentation (accessed 2026-11-09):
  Claude Code  https://code.claude.com/docs/en/hooks
  Codex        https://learn.chatgpt.com/docs/hooks             (tool_name Bash | apply_patch, tool_input.command)
  Copilot      https://docs.github.com/en/copilot/reference/hooks-configuration   (toolName, toolArgs)
  Cursor       https://cursor.com/docs/agent/hooks              (preToolUse, beforeShellExecution, workspace_roots)
  Gemini CLI   https://geminicli.com/docs/hooks/reference/      (BeforeTool; write_file, replace, run_shell_command)
"""
import json
import unittest

from tests._support import TempRepo, run_cli, write

GUARDS = {
    "schemaVersion": 1,
    "generated": [{"glob": "web/src/api-client/**", "regenerate": "run the api-client regeneration"}],
    "commands": [{"pattern": r"(?i)\bsqlcmd\b", "decision": "deny", "reason": "no direct SQL"}],
    "git": {"writes": "ask"},
}
GEN = "web/src/api-client/model.ts"
PLAIN = "web/src/app.ts"


def guard(root, event, client=None):
    write(root, {".stackfoundry/guards.json": json.dumps(GUARDS)})
    args = ["guard"] + (["--client", client] if client else [])
    proc = run_cli(args, stdin=json.dumps(event), env={"CLAUDE_PROJECT_DIR": ""})
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout) if proc.stdout.strip() else None


class CodexTests(unittest.TestCase):
    def event(self, root, tool, command):
        return {"session_id": "s", "turn_id": "t", "cwd": str(root), "hook_event_name": "PreToolUse",
                "model": "m", "permission_mode": "default", "tool_name": tool, "tool_use_id": "u",
                "tool_input": {"command": command}}

    def test_apply_patch_of_a_generated_file_is_denied(self):
        patch = f"*** Begin Patch\n*** Update File: {GEN}\n@@\n-a\n+b\n*** End Patch\n"
        with TempRepo() as root:
            out = guard(root, self.event(root, "apply_patch", patch))
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("api-client regeneration", out["hookSpecificOutput"]["permissionDecisionReason"])

    def test_a_patch_moving_a_file_into_generated_code_is_denied(self):
        patch = f"*** Begin Patch\n*** Update File: {PLAIN}\n*** Move to: {GEN}\n*** End Patch\n"
        with TempRepo() as root:
            self.assertEqual(guard(root, self.event(root, "apply_patch", patch))["hookSpecificOutput"]
                             ["permissionDecision"], "deny")

    def test_a_git_write_is_denied_with_a_go_ahead_reason_because_codex_cannot_ask(self):
        with TempRepo() as root:
            out = guard(root, self.event(root, "Bash", "git push"))["hookSpecificOutput"]
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("go-ahead", out["permissionDecisionReason"])

    def test_other_patches_and_reads_get_no_opinion(self):
        patch = f"*** Begin Patch\n*** Add File: {PLAIN}\n+x\n*** End Patch\n"
        with TempRepo() as root:
            self.assertIsNone(guard(root, self.event(root, "apply_patch", patch)))
            self.assertIsNone(guard(root, self.event(root, "Bash", "git status")))


class CopilotTests(unittest.TestCase):
    def event(self, root, tool, args, as_string=False):
        return {"sessionId": "s", "timestamp": 1, "cwd": str(root), "toolName": tool,
                "toolArgs": json.dumps(args) if as_string else args}

    def test_edit_and_create_of_generated_files_are_denied(self):
        with TempRepo() as root:
            for tool in ("edit", "create", "str_replace_editor"):
                with self.subTest(tool=tool):
                    out = guard(root, self.event(root, tool, {"path": str(root / GEN)}))
                    self.assertEqual(out["permissionDecision"], "deny")
                    self.assertIn("generated", out["permissionDecisionReason"])

    def test_tool_args_sent_as_a_json_string_are_read(self):
        with TempRepo() as root:
            out = guard(root, self.event(root, "bash", {"command": "git commit -m x"}, as_string=True))
        self.assertEqual(out["permissionDecision"], "ask")

    def test_powershell_counts_for_commands_filtered_by_tool(self):
        with TempRepo() as root:
            out = guard(root, self.event(root, "powershell", {"command": "sqlcmd -Q x"}))
        self.assertEqual(out["permissionDecision"], "deny")

    def test_no_opinion_is_no_output(self):
        with TempRepo() as root:
            self.assertIsNone(guard(root, self.event(root, "view", {"path": str(root / GEN)})))
            self.assertIsNone(guard(root, self.event(root, "edit", {"path": str(root / PLAIN)})))


class CursorTests(unittest.TestCase):
    def common(self, root, name):
        return {"conversation_id": "c", "generation_id": "g", "model": "m", "hook_event_name": name,
                "cursor_version": "3.0.0", "workspace_roots": [str(root)], "user_email": None,
                "transcript_path": None}

    def test_shell_git_write_asks(self):
        with TempRepo() as root:
            event = {**self.common(root, "beforeShellExecution"), "command": "git push", "cwd": str(root),
                     "sandbox": False}
            out = guard(root, event)
        self.assertEqual(out["permission"], "ask")
        self.assertIn("stackfoundry guard", out["agent_message"])

    def test_write_of_a_generated_file_is_denied(self):
        with TempRepo() as root:
            event = {**self.common(root, "preToolUse"), "tool_name": "Write", "tool_use_id": "u",
                     "tool_input": {"file_path": str(root / GEN)}, "cwd": str(root)}
            self.assertEqual(guard(root, event)["permission"], "deny")

    def test_no_opinion_is_an_explicit_allow_because_cursor_blocks_on_empty_output(self):
        with TempRepo() as root:
            event = {**self.common(root, "beforeShellExecution"), "command": "ls", "cwd": str(root)}
            self.assertEqual(guard(root, event), {"permission": "allow"})
            self.assertEqual(guard(root, {"garbage": True}, client="cursor"), {"permission": "allow"})


class GeminiTests(unittest.TestCase):
    def event(self, root, tool, args):
        return {"session_id": "s", "transcript_path": "t", "cwd": str(root), "hook_event_name": "BeforeTool",
                "timestamp": "2026-11-09T10:00:00Z", "tool_name": tool, "tool_input": args}

    def test_write_file_and_replace_of_generated_files_are_denied(self):
        with TempRepo() as root:
            for tool in ("write_file", "replace"):
                with self.subTest(tool=tool):
                    out = guard(root, self.event(root, tool, {"file_path": str(root / GEN), "content": "x"}))
                    self.assertEqual(out["decision"], "deny")

    def test_git_write_is_denied_because_gemini_cannot_ask_and_dir_path_is_honoured(self):
        with TempRepo() as root:
            out = guard(root, self.event(root, "run_shell_command", {"command": "git push", "dir_path": "web"}))
        self.assertEqual(out["decision"], "deny")
        self.assertIn("go-ahead", out["reason"])

    def test_no_opinion_is_no_output(self):
        with TempRepo() as root:
            self.assertIsNone(guard(root, self.event(root, "read_file", {"file_path": str(root / GEN)})))


class DetectionTests(unittest.TestCase):
    def test_the_event_shape_names_the_client_and_claude_stays_the_default(self):
        from stackfoundry.guard import detect
        self.assertEqual(detect({"toolName": "bash", "toolArgs": {}}), "copilot")
        self.assertEqual(detect({"hook_event_name": "beforeShellExecution"}), "cursor")
        self.assertEqual(detect({"hook_event_name": "BeforeTool"}), "gemini")
        self.assertEqual(detect({"turn_id": "t", "tool_name": "Bash"}), "codex")
        self.assertEqual(detect({"hook_event_name": "PreToolUse", "tool_name": "Bash"}), "claude-code")

    def test_a_cyrillic_project_path_still_matches_for_every_client(self):
        with TempRepo() as tmp:
            root = tmp / "Проєкт"
            root.mkdir()
            out = guard(root, {"toolName": "edit", "toolArgs": {"path": str(root / GEN)}, "cwd": str(root)})
        self.assertEqual(out["permissionDecision"], "deny")


if __name__ == "__main__":
    unittest.main()
