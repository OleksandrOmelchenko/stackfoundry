"""Regression tests for the defects the first self-run of /stackfoundry:init found in its own CLI."""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from tests._support import CLI, HAS_GIT, ROOT, TempRepo, git, run_cli, targets_json, write
from stackfoundry import manifest
from stackfoundry.change_targets import specialists
from stackfoundry.pack import check as pack_check
from stackfoundry.pack import render as pack_render
from stackfoundry.plumbing import check as plumbing_check
from stackfoundry.profile import check_targets
from stackfoundry.survey import survey
from stackfoundry.tracker import check as tracker_check

CYRILLIC = "Александр"


def guard_bytes(payload: bytes, project: Path):
    """Feed the guard raw bytes, as Claude Code does, with no text-mode decoding on the way in."""
    return subprocess.run([sys.executable, "-I", str(CLI), "guard"], input=payload, capture_output=True,
                          env={**os.environ, "CLAUDE_PROJECT_DIR": str(project)})


class GuardEncodingTests(unittest.TestCase):
    def test_a_utf8_event_with_a_non_ascii_project_path_is_still_guarded(self):
        with TempRepo() as tmp:
            project = tmp / CYRILLIC / "repo"
            write(project, {".claude/stackfoundry/guards.json": json.dumps(
                {"schemaVersion": 1, "generated": [{"glob": "gen/**", "regenerate": "run codegen"}]})})
            event = {"hook_event_name": "PreToolUse", "tool_name": "Edit",
                     "tool_input": {"file_path": str(project / "gen" / f"{CYRILLIC}.py")}}
            # ensure_ascii=False: the bytes on the wire are real UTF-8, not \u escapes.
            proc = guard_bytes(json.dumps(event, ensure_ascii=False).encode("utf-8"), project)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_a_byte_order_mark_in_guards_json_does_not_switch_guarding_off(self):
        with TempRepo() as project:
            (project / ".claude/stackfoundry").mkdir(parents=True)
            (project / ".claude/stackfoundry/guards.json").write_bytes(
                b"\xef\xbb\xbf" + json.dumps({"schemaVersion": 1, "git": {"writes": "ask"}}).encode())
            event = {"tool_name": "Bash", "tool_input": {"command": "git push"}}
            proc = guard_bytes(json.dumps(event).encode(), project)
        self.assertEqual(json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"], "ask")


@unittest.skipUnless(HAS_GIT, "git not installed")
class GitPathTests(unittest.TestCase):
    def test_non_ascii_file_names_stay_in_the_change_set(self):
        data = {"schemaVersion": 1, "targets": [{"name": "api", "paths": ["src/**"], "packs": []}]}
        with TempRepo({"src/a.py": "x"}, git=True) as root:
            targets_json(root, data)
            write(root, {f"src/{CYRILLIC}.py": "y"})
            proc = run_cli(["change-targets", "--json", "--root", str(root)])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(f"src/{CYRILLIC}.py", json.loads(proc.stdout)["targets"]["api"]["files"])


class ProfileTests(unittest.TestCase):
    def test_a_byte_order_mark_in_targets_json_is_accepted(self):
        data = {"schemaVersion": 1, "targets": [{"name": "api", "paths": ["src/**"], "packs": []}]}
        with TempRepo() as root:
            (root / ".claude/stackfoundry").mkdir(parents=True)
            (root / ".claude/stackfoundry/targets.json").write_bytes(b"\xef\xbb\xbf" + json.dumps(data).encode())
            proc = run_cli(["change-targets", "--json", "--root", str(root), "--files", "src/a.py"])
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_a_broken_specialist_regex_is_reported_not_fatal(self):
        data = {"schemaVersion": 1, "targets": [{"name": "api", "paths": ["src/**"], "packs": []}],
                "specialists": [{"agent": "security-reviewer", "contains": ["(unclosed"]}]}
        self.assertTrue(any("does not compile" in e for e in check_targets(data)))
        with TempRepo({"src/a.py": "x"}) as root:
            self.assertEqual(specialists(data, root, ["src/a.py"]), [])

    def test_malformed_input_exits_2_not_1(self):
        with TempRepo({"r.json": "{not json"}) as root:
            proc = run_cli(["mutation-check", str(root / "r.json")])
        self.assertEqual(proc.returncode, 2)
        self.assertNotIn("Traceback", proc.stderr)

    def test_files_takes_several_values_in_either_form(self):
        data = {"schemaVersion": 1, "targets": [{"name": "a", "paths": ["a/**"], "packs": []},
                                                {"name": "b", "paths": ["b/**"], "packs": []},
                                                {"name": "c", "paths": ["c/**"], "packs": []}]}
        with TempRepo() as root:
            targets_json(root, data)
            proc = run_cli(["change-targets", "--json", "--root", str(root), "--files", "a/x", "b/y,c/z"])
        self.assertEqual(set(json.loads(proc.stdout)["targets"]), {"a", "b", "c"})


class ManifestTests(unittest.TestCase):
    def test_the_claude_md_block_is_hashed_alone_and_writes_are_atomic(self):
        block = "<!-- stackfoundry:begin -->\nrows\n<!-- stackfoundry:end -->\n"
        with TempRepo({"CLAUDE.md": "# Team notes\n\n" + block}) as root:
            manifest.record(root, ["CLAUDE.md"], "reference/templates/claude-md-block.md", "generated")
            write(root, {"CLAUDE.md": "# Team notes, edited by the team\n\nMore.\n\n" + block})
            self.assertEqual(manifest.diff(root)[0]["state"], "untouched")
            write(root, {"CLAUDE.md": "# Team notes\n\n" + block.replace("rows", "changed rows")})
            self.assertEqual(manifest.diff(root)[0]["state"], "edited")
            leftovers = list((root / ".claude/stackfoundry").glob(".manifest-*"))
            self.assertEqual(leftovers, [])
            raw = (root / ".claude/stackfoundry/manifest.lock.json").read_bytes()
            self.assertNotIn(b"\r\n", raw)

    def test_profile_facts_have_no_template_to_upgrade(self):
        with TempRepo({".claude/stackfoundry/targets.json": "{}"}) as root:
            manifest.record(root, [".claude/stackfoundry/targets.json"], "profile", "generated")
            row = manifest.diff(root)[0]
        self.assertFalse(row["outdated"])
        self.assertTrue(row["action"].startswith("none"))


class SurveyTests(unittest.TestCase):
    def test_the_stackfoundry_repo_surveys_as_a_plugin_with_fixtures_flagged(self):
        result = survey(ROOT)
        units = {u["manifest"]: u for u in result["units"]}
        plugin = units["plugins/stackfoundry/.claude-plugin/plugin.json"]
        self.assertEqual(plugin["path"], "plugins/stackfoundry")
        self.assertIn("claude-code-plugin", {h["tech"] for h in plugin["hints"]})
        self.assertFalse(plugin["fixture"])
        self.assertIn("python", plugin["languages"], "the CLI's sources belong to the plugin unit")
        fixtures = [u for m, u in units.items() if m.startswith("fixtures/")]
        self.assertTrue(fixtures)
        self.assertTrue(all(u["fixture"] for u in fixtures))
        self.assertIn("claude-code-marketplace", {h["tech"] for h in result["repoHints"]})
        self.assertIn("tests", {s["dir"] for s in result["looseSources"]})

    def test_a_marker_below_the_header_is_not_a_generated_file(self):
        body = "import os\n\n\nVALUE = 1\n\n" + 'MARKER = "<auto-generated>"\n'
        with TempRepo({"src/a.py": body, "gen/b.py": "# <auto-generated> by codegen\nx = 1\n"}) as root:
            gen = survey(root)["generatedDirs"]
        self.assertEqual(gen, {"gen": 1})

    def test_errors_go_to_stderr(self):
        proc = run_cli(["survey", str(ROOT / "no-such-dir")])
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(proc.stdout, "")


@unittest.skipUnless(HAS_GIT, "git not installed")
class GlobsCheckTests(unittest.TestCase):
    def test_bin_folders_count(self):
        rule = '---\npaths:\n  - "tool/bin/**"\n---\n# Rule\n'
        with TempRepo({"tool/bin/run": "x", ".claude/rules/r.md": rule}, git=True) as root:
            proc = run_cli(["globs-check", "--root", str(root)])
        self.assertEqual(proc.returncode, 0, proc.stdout)


class PlumbingTests(unittest.TestCase):
    def test_marketplace_root_is_a_repo_and_plugin_refs_are_not_checked_there(self):
        skill = "---\nname: mine\ndescription: x\n---\nThen run `/stackfoundry:bug-hunt`.\n"
        files = {".claude-plugin/marketplace.json": "{}", ".claude/skills/mine/SKILL.md": skill}
        with TempRepo(files) as root:
            rep = plumbing_check(root)
        self.assertEqual(rep.skills, ["mine"])
        self.assertEqual(rep.errors, [])

    def test_ignored_agent_fields_and_angle_brackets_warn(self):
        files = {".claude-plugin/plugin.json": "{}",
                 "skills/s/SKILL.md": "---\nname: s\ndescription: Use for /x <target>.\n---\n",
                 "agents/a.md": "---\nname: a\ndescription: d\ntools: Read\npermissionMode: plan\n---\n"}
        with TempRepo(files) as root:
            warnings = " | ".join(plumbing_check(root).warnings)
        self.assertIn("HTML entities", warnings)
        self.assertIn("'permissionMode' is ignored", warnings)


class TrackerTests(unittest.TestCase):
    def test_a_ledger_is_not_a_tracker(self):
        ledger = "# Deferred upgrades\n\n| Item | Why |\n|---|---|\n"
        self.assertEqual(tracker_check(ledger), [])
        with TempRepo({"d.md": ledger}) as root:
            proc = run_cli(["tracker", "check", str(root / "d.md")])
        self.assertEqual(proc.returncode, 0)
        self.assertIn("not a tracker", proc.stdout)


PACK = {
    "schemaVersion": 1, "id": "app-model-sample", "layer": "app-model", "title": "Sample",
    "researchedAt": "2026-11-09", "versions": [{"version": "1.2", "pinnedIn": "pyproject.toml"}],
    "targets": ["api"], "rulebookPaths": ["src/**"],
    "rules": [{"rule": "Do X.", "why": "Y breaks.", "where": ["src/a.py: f"], "sources": ["docs"],
               "repoConvention": "The repo does Z."}],
    "bugCategories": [{"name": "boundary", "lookFor": "a > b | c", "failure": "off by one", "sources": ["docs"]}],
    "sources": {"docs": {"url": "https://example.org/docs", "title": "Docs", "version": "1.2",
                         "accessed": "2026-11-09"}},
}


class PackTests(unittest.TestCase):
    def test_a_valid_pack_renders_its_rulebook_deterministically(self):
        errors, _ = pack_check(PACK)
        self.assertEqual(errors, [])
        text = pack_render(PACK)
        self.assertEqual(text, pack_render(json.loads(json.dumps(PACK))))
        self.assertIn('paths:\n  - "src/**"\n---', text)
        self.assertIn("- **Do X.** Y breaks. Here: src/a.py: f. [docs]", text)
        self.assertIn("This repo: The repo does Z.", text)
        self.assertIn("a > b \\| c", text, "a pipe inside a table cell is escaped")
        self.assertIn("- [docs] Docs: https://example.org/docs (1.2, accessed 2026-11-09)", text)

    def test_broken_packs_are_errors(self):
        bad = json.loads(json.dumps(PACK))
        bad["rules"][0]["sources"] = ["nowhere"]
        bad["bugCategories"][0]["failure"] = "x &gt; y"
        bad["sources"]["docs"]["accessed"] = "yesterday"
        bad["id"] = "tooling-sample"
        errors = " | ".join(pack_check(bad)[0])
        for needle in ("unknown source key(s): nowhere", "HTML-escaped", "accessed date", "does not start with"):
            self.assertIn(needle, errors)

    def test_cli_render_writes_the_file(self):
        with TempRepo({"p.json": json.dumps(PACK)}) as root:
            proc = run_cli(["pack", "render", str(root / "p.json"), "--out", str(root / "out/r.md")])
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue((root / "out/r.md").read_text(encoding="utf-8").startswith("---\ndescription: Sample"))


if __name__ == "__main__":
    unittest.main()
