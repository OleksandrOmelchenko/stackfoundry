"""The PreToolUse guard, driven exactly as Claude Code drives it: JSON on stdin, decision JSON on stdout."""
import json
import shutil
import subprocess
import unittest

from tests._support import LAUNCHER, LAUNCHER_PS1, TempRepo, run_cli, write

GUARDS = {
    "schemaVersion": 1,
    "generated": [{"glob": "web/src/api-client/**", "regenerate": "run the api-client regeneration"}],
    "commands": [{"pattern": r"(?i)\bsqlcmd\b", "decision": "deny", "reason": "no direct SQL"},
                 {"pattern": r"npm run deploy", "decision": "ask", "reason": "deploys are the owner's"}],
    "git": {"writes": "ask"},
}


def event(tool, **tool_input):
    return json.dumps({"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input})


class GuardTests(unittest.TestCase):
    def run_guard(self, root, payload, guards=GUARDS):
        if guards is not None:
            write(root, {".stackfoundry/guards.json": json.dumps(guards)})
        proc = run_cli(["guard"], stdin=payload, env={"CLAUDE_PROJECT_DIR": str(root)})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)["hookSpecificOutput"] if proc.stdout.strip() else None

    def test_generated_edit_is_denied_with_how_to_regenerate(self):
        with TempRepo() as root:
            out = self.run_guard(root, event("Edit", file_path=str(root / "web/src/api-client/model.ts")))
        self.assertEqual(out["permissionDecision"], "deny")
        self.assertIn("api-client regeneration", out["permissionDecisionReason"])

    def test_other_edits_and_files_outside_the_repo_pass(self):
        with TempRepo() as root:
            self.assertIsNone(self.run_guard(root, event("Write", file_path=str(root / "web/src/app.ts"))))
            self.assertIsNone(self.run_guard(root, event("Write", file_path="/elsewhere/web/src/api-client/x.ts")))

    def test_command_patterns(self):
        with TempRepo() as root:
            self.assertEqual(self.run_guard(root, event("Bash", command="SQLCMD -Q 'drop'"))["permissionDecision"],
                             "deny")
            self.assertEqual(self.run_guard(root, event("PowerShell", command="npm run deploy"))["permissionDecision"],
                             "ask")

    def test_git_writes_ask_and_reads_pass(self):
        writes = ["git commit -m x", "git push", "cd a && git reset --hard", "git -C x rebase main",
                  "git tag v1", "git stash", "git stash pop", "git branch -D old", "git checkout -- a.txt",
                  "gh pr create --fill", "gh pr merge 3"]
        reads = ["git status", "git diff HEAD", "git log --oneline", "git tag -l", "git branch --list",
                 "git stash list", "git show HEAD", "gh pr view 3", "echo commit"]
        with TempRepo() as root:
            for cmd in writes:
                with self.subTest(cmd=cmd):
                    out = self.run_guard(root, event("Bash", command=cmd))
                    self.assertIsNotNone(out, cmd)
                    self.assertEqual(out["permissionDecision"], "ask")
            for cmd in reads:
                with self.subTest(cmd=cmd):
                    self.assertIsNone(self.run_guard(root, event("Bash", command=cmd)), cmd)

    def test_fails_open(self):
        with TempRepo() as root:
            self.assertIsNone(self.run_guard(root, event("Bash", command="git push"), guards=None))
            write(root, {".stackfoundry/guards.json": "{not json"})
            self.assertIsNone(self.run_guard(root, event("Bash", command="git push"), guards=None))
            self.assertIsNone(self.run_guard(root, "garbage", guards=GUARDS))

    def test_check_reports_rules_the_hook_would_silently_skip(self):
        with TempRepo() as root:
            write(root, {".stackfoundry/guards.json": json.dumps(GUARDS)})
            self.assertEqual(run_cli(["guard", "--check", "--root", str(root)]).returncode, 0)
            bad = {"schemaVersion": 1, "commands": [{"pattern": "(unclosed", "decision": "block"}],
                   "git": {"writes": "maybe"}}
            write(root, {".stackfoundry/guards.json": json.dumps(bad)})
            proc = run_cli(["guard", "--check", "--root", str(root)])
        self.assertEqual(proc.returncode, 1)
        for needle in ("does not compile", "deny or ask", "give a reason", "git.writes"):
            self.assertIn(needle, proc.stdout)

    def test_forget_drops_a_manifest_entry(self):
        from stackfoundry import manifest
        with TempRepo({"a.md": "x\n"}) as root:
            manifest.record(root, ["a.md"], "reference/detect-signals.json", "materialized")
            self.assertEqual(manifest.forget(root, ["a.md"])["files"], {})

    @unittest.skipUnless(shutil.which("sh"), "sh not available")
    def test_the_launcher_runs_the_guard(self):
        with TempRepo() as root:
            write(root, {".stackfoundry/guards.json": json.dumps(GUARDS)})
            proc = subprocess.run(["sh", str(LAUNCHER), "guard"], input=event("Bash", command="git push"),
                                  capture_output=True, text=True, encoding="utf-8", env={**__import__("os").environ,
                                                                       "CLAUDE_PROJECT_DIR": str(root)}, timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"], "ask")

    @unittest.skipUnless(shutil.which("pwsh"), "pwsh not available")
    def test_the_powershell_launcher_runs_the_guard(self):
        with TempRepo() as root:
            write(root, {".stackfoundry/guards.json": json.dumps(GUARDS)})
            proc = subprocess.run(["pwsh", "-NoProfile", "-File", str(LAUNCHER_PS1), "guard"],
                                  input=event("Bash", command="git push"), capture_output=True, text=True,
                                  encoding="utf-8", env={**__import__("os").environ, "CLAUDE_PROJECT_DIR": str(root)}, timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"], "ask")


if __name__ == "__main__":
    unittest.main()
