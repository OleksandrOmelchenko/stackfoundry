"""The guard's role rules (threat model T3, T11): Claude Code names the calling subagent as `agent_type`, and the
guard asks before a read-only role changes files or any subagent changes the control plane it does not own."""
import json
import unittest

from tests._support import TempRepo, run_cli, write

MATERIALIZED = "---\nname: api-bug-hunter\ndescription: Hunts bugs in api. Read-only.\ntools: Read, Bash\n---\nBody.\n"


def guard(root, tool, agent=None, **tool_input):
    event = {"hook_event_name": "PreToolUse", "tool_name": tool, "cwd": str(root), "tool_input": tool_input}
    if agent:
        event["agent_type"] = agent
    proc = run_cli(["guard"], stdin=json.dumps(event), env={"CLAUDE_PROJECT_DIR": str(root)})
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"] if proc.stdout.strip() else None


class ReadOnlyRoleTests(unittest.TestCase):
    """R1: a read-only role's command that changes project files asks; its reads pass."""

    def test_file_changing_commands_ask(self):
        with TempRepo() as root:
            for cmd in ("rm -rf src", "sed -i s/a/b/ app.py", "mv a.py b.py", "pytest -q > out.txt", "git stash",
                        "cd src && touch x", "echo x | tee notes.md", "bash -c 'cp a b'", "git checkout -- a.py"):
                with self.subTest(cmd=cmd):
                    self.assertEqual(guard(root, "Bash", "stackfoundry:bug-hunter", command=cmd), "ask")
            self.assertEqual(guard(root, "PowerShell", "stackfoundry:bug-hunter",
                                   command="Remove-Item -Recurse src"), "ask")

    def test_reads_and_writes_outside_the_project_pass(self):
        with TempRepo() as root:
            for cmd in ("git diff HEAD", "pytest -q", "pytest -q 2>&1 | tail -5", "npm test > /dev/null",
                        "grep -rn x src", "mkdir -p /tmp/sf-scratch", "git log --oneline > $TMPDIR/log.txt"):
                with self.subTest(cmd=cmd):
                    self.assertIsNone(guard(root, "Bash", "stackfoundry:bug-hunter", command=cmd))

    def test_only_read_only_subagents_are_judged(self):
        with TempRepo() as root:
            self.assertIsNone(guard(root, "Bash", None, command="rm -rf src"))  # the main session
            self.assertIsNone(guard(root, "Bash", "stackfoundry:test-writer", command="rm tests/old_test.py"))
            self.assertIsNone(guard(root, "Bash", "general-purpose", command="rm -rf src"))
            self.assertIsNone(guard(root, "Bash", "stackfoundry:no-such-role", command="rm -rf src"))
            self.assertIsNone(guard(root, "Bash", "stackfoundry:../x", command="rm -rf src"))

    def test_a_materialized_agent_is_judged_by_its_own_definition(self):
        with TempRepo() as root:
            write(root, {".stackfoundry/agents/api-bug-hunter.md": MATERIALIZED})
            self.assertEqual(guard(root, "Bash", "api-bug-hunter", command="rm x.py"), "ask")
            self.assertIsNone(guard(root, "Bash", "api-bug-hunter", command="git diff"))


class ControlPlaneTests(unittest.TestCase):
    """R2-R4: control-plane files are changed only by the role that owns them, or by the main session."""

    def test_edits_of_the_control_plane_ask(self):
        with TempRepo() as root:
            for rel in (".stackfoundry/guards.json", ".stackfoundry/extensions/skills/bug-hunt.md", "CLAUDE.md",
                        "src/AGENTS.md", ".cursor/rules/x.mdc"):
                with self.subTest(rel=rel):
                    self.assertEqual(guard(root, "Write", "stackfoundry:test-writer", file_path=str(root / rel)),
                                     "ask")
            self.assertIsNone(guard(root, "Write", "stackfoundry:test-writer", file_path=str(root / "tests/t.py")))
            self.assertIsNone(guard(root, "Write", None, file_path=str(root / ".stackfoundry/guards.json")))

    def test_a_role_writes_its_own_output(self):
        with TempRepo() as root:
            pack = root / ".stackfoundry/packs/language-python/pack.json"
            self.assertIsNone(guard(root, "Write", "stackfoundry:stack-researcher", file_path=str(pack)))
            self.assertIsNone(guard(root, "Edit", "stackfoundry:docs-reconciler", file_path=str(root / "CLAUDE.md")))
            self.assertEqual(guard(root, "Edit", "stackfoundry:docs-reconciler",
                                   file_path=str(root / ".stackfoundry/guards.json")), "ask")

    def test_web_roles_write_nothing_but_their_output(self):
        with TempRepo() as root:
            for agent, rel in (("stackfoundry:stack-researcher", "src/app.py"),
                               ("stackfoundry:domain-researcher", "scripts/setup.sh"),
                               ("stackfoundry:stack-researcher", ".stackfoundry/guards.json")):
                with self.subTest(agent=agent, rel=rel):
                    self.assertEqual(guard(root, "Write", agent, file_path=str(root / rel)), "ask")

    def test_commands_that_change_the_control_plane_ask(self):
        with TempRepo() as root:
            for cmd in ("echo {} > .stackfoundry/guards.json", "cp x.md .stackfoundry/extensions/skills/x.md",
                        "sed -i 's/ask/allow/' .stackfoundry/guards.json"):
                with self.subTest(cmd=cmd):
                    self.assertEqual(guard(root, "Bash", "stackfoundry:test-writer", command=cmd), "ask")
            self.assertIsNone(guard(root, "Bash", "stackfoundry:test-writer", command="cp a.py tests/b.py"))


if __name__ == "__main__":
    unittest.main()
