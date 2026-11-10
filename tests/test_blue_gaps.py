"""Threat-model gaps T10 and T18, and the CLI hardening the sixth self-run's researchers proposed."""
import json
import os
import shutil
import stat
import subprocess
import unittest
import uuid
from pathlib import Path
from unittest import mock

from tests._support import TempRepo, run_cli, write
from stackfoundry import cited, extensions, gitutil, pack, product

LAUNCHER = Path(__file__).resolve().parents[1] / "plugins" / "stackfoundry" / "scripts" / "stackfoundry.sh"


def event(tool, session, **tool_input):
    return json.dumps({"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": tool_input,
                       "session_id": session})


@unittest.skipUnless(shutil.which("sh"), "sh not available")
class LauncherPathTests(unittest.TestCase):
    """T10: a python3 planted in the repo the hook runs in must never run, whatever relative PATH entry finds it."""

    def test_a_relative_path_entry_is_skipped(self):
        with TempRepo() as root:
            for name in ("python3", "python"):
                planted = root / name
                planted.write_text("#!/bin/sh\necho PLANTED\nexit 0\n", encoding="utf-8", newline="\n")
                planted.chmod(planted.stat().st_mode | stat.S_IEXEC)
            for prefix in (".", ""):
                env = {**os.environ, "PATH": prefix + os.pathsep + os.environ.get("PATH", "")}
                proc = subprocess.run(["sh", str(LAUNCHER), "today"], cwd=root, env=env, capture_output=True,
                                      text=True, encoding="utf-8", timeout=60)
                self.assertNotIn("PLANTED", proc.stdout + proc.stderr, f"PATH entry {prefix!r}")
                self.assertRegex(proc.stdout, r"^\d{4}-\d{2}-\d{2}")


class UnreadableGuardsWarningTests(unittest.TestCase):
    """T18: a guards.json the hook cannot read turns its rules off; Claude Code users are told once a session."""

    def run_guard(self, root, session):
        proc = run_cli(["guard"], stdin=event("Bash", session, command="git push"),
                       env={"CLAUDE_PROJECT_DIR": str(root)})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout) if proc.stdout.strip() else None

    def test_a_broken_file_warns_once_per_session_and_still_decides_nothing(self):
        with TempRepo() as root:
            write(root, {".stackfoundry/guards.json": "{not json"})
            session = str(uuid.uuid4())
            first = self.run_guard(root, session)
            self.assertNotIn("hookSpecificOutput", first)
            self.assertIn("guards.json cannot be read, so its rules are off", first["systemMessage"])
            self.assertIn("stackfoundry guard --check", first["systemMessage"])
            self.assertIsNone(self.run_guard(root, session))
            self.assertIn("systemMessage", self.run_guard(root, str(uuid.uuid4())))

    def test_a_broken_nested_file_warns_beside_the_roots_decision(self):
        with TempRepo() as root:
            write(root, {".stackfoundry/guards.json": json.dumps({"schemaVersion": 1, "git": {"writes": "ask"}}),
                         "sub/.stackfoundry/guards.json": "[1, 2"})
            proc = run_cli(["guard"], stdin=json.dumps({
                "hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "git push"},
                "session_id": str(uuid.uuid4()), "cwd": str(root / "sub")}), env={"CLAUDE_PROJECT_DIR": str(root)})
            out = json.loads(proc.stdout)
            self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "ask")
            self.assertIn(str(Path("sub") / ".stackfoundry" / "guards.json"), out["systemMessage"])

    def test_readable_files_say_nothing(self):
        with TempRepo() as root:
            write(root, {".stackfoundry/guards.json": json.dumps({"schemaVersion": 1})})
            self.assertIsNone(self.run_guard(root, str(uuid.uuid4())))

    def test_other_assistants_get_no_warning_field(self):
        with TempRepo() as root:
            write(root, {".stackfoundry/guards.json": "{not json"})
            payload = json.dumps({"toolName": "bash", "toolArgs": json.dumps({"command": "git push"}),
                                  "cwd": str(root), "sessionId": str(uuid.uuid4())})
            proc = run_cli(["guard", "--client", "copilot"], stdin=payload, env={"CLAUDE_PROJECT_DIR": str(root)})
            self.assertEqual(proc.stdout.strip(), "")


class GitBashWarningTests(unittest.TestCase):
    """Claude Code's guard hook runs through `sh`; on Windows without Git Bash it is off, and --check says so."""

    def check(self, os_name, sh):
        import argparse
        import contextlib
        import io
        from stackfoundry import guard
        with TempRepo() as root:
            write(root, {".stackfoundry/guards.json": json.dumps({"schemaVersion": 1})})
            with mock.patch.object(guard.os, "name", os_name), mock.patch.object(guard.shutil, "which",
                                                                                 return_value=sh), \
                    contextlib.redirect_stdout(io.StringIO()) as out:
                code = guard.main(argparse.Namespace(check=True, root=str(root)))
        return code, out.getvalue()

    def test_windows_without_sh_warns_but_the_file_is_still_ok(self):
        code, out = self.check("nt", None)
        self.assertEqual(code, 0)
        self.assertIn("guards.json: ok", out)
        self.assertIn("no `sh` on PATH, so Claude Code's guard hook cannot run here", out)

    def test_windows_with_sh_says_nothing_more(self):
        # (os.name cannot be faked as "posix" on Windows: pathlib refuses PosixPath there.)
        self.assertNotIn("warning", self.check("nt", "C:/Program Files/Git/usr/bin/sh.exe")[1])


class HardeningTests(unittest.TestCase):
    def test_validators_refuse_a_trailing_newline(self):
        # `re.match` with `$` accepts "value\n"; every id, name, path and date check must take the whole string.
        self.assertIsNone(pack.ID.fullmatch("language-python\n"))
        self.assertIsNone(cited.DATE.fullmatch("2026-11-10\n"))
        self.assertIsNone(product.KEBAB.fullmatch("b2c-shop\n"))
        self.assertIsNone(extensions.NAME.fullmatch("review-changes\n"))
        self.assertIsNone(extensions.FORK_NAME.fullmatch("x.md\n"))
        self.assertIsNone(extensions.PLUGIN_FILE.fullmatch("skills/init/SKILL.md\n"))
        errors, _ = pack.check({"schemaVersion": 1, "id": "language-python\n", "layer": "language",
                                "researchedAt": "2026-11-10\n"})
        self.assertIn("id 'language-python\\n' must look like <layer>-<name>", errors)
        self.assertIn("researchedAt must be a YYYY-MM-DD date", errors)

    def test_git_on_windows_is_only_git_exe(self):
        # A git.cmd or git.bat runs through cmd.exe, which re-parses the arguments. git_exe is cached: clear it on
        # both sides so neither the real git nor this fake leaks between tests.
        gitutil.git_exe.cache_clear()
        self.addCleanup(gitutil.git_exe.cache_clear)
        with TempRepo() as root:
            (root / "git.cmd").write_text("@echo off\n", encoding="utf-8")
            with mock.patch.object(gitutil.os, "name", "nt"), \
                    mock.patch.dict(gitutil.os.environ, {"PATH": str(root), "PATHEXT": ".COM;.EXE;.BAT;.CMD"}), \
                    mock.patch.object(gitutil.os, "pathsep", os.pathsep):
                with self.assertRaises(gitutil.GitError):
                    gitutil.git_exe()
            (root / "git.exe").write_bytes(b"MZ")
            gitutil.git_exe.cache_clear()
            with mock.patch.object(gitutil.os, "name", "nt"), mock.patch.dict(gitutil.os.environ, {"PATH": str(root)}):
                self.assertEqual(gitutil.git_exe(), os.path.join(str(root), "git.exe"))

    def test_options_cannot_be_abbreviated(self):
        with TempRepo() as root:
            proc = run_cli(["config", "--ro", str(root)])
            self.assertEqual(proc.returncode, 2)
            self.assertIn("unrecognized arguments: --ro", proc.stderr)
            self.assertEqual(run_cli(["config", "--root", str(root), "docsRoot"]).stdout.strip(), "docs")


if __name__ == "__main__":
    unittest.main()
