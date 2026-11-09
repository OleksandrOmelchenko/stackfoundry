"""Repo extensions: the format check, scaffolding, and the three-way merge that keeps a full copy current."""
import json
import tempfile
import unittest
from pathlib import Path

from tests._support import HAS_GIT, TempRepo, run_cli, targets_json, write
from stackfoundry import extensions as ext

SKILL = """---
name: demo
description: A demo skill. Use for "demo".
---

# Demo

## 1. Survey

Look around.

## 2. Ask

Ask one question.

```text
## Not a heading (inside a fence)
```

## 3. Report

Write the report.
"""
AGENT = "---\nname: hunter\ndescription: Read-only hunter.\ntools: Read\n---\n# Hunter\n\n## Read first\n\nThe profile.\n"


def plugin(root: Path, skill: str = SKILL, version: str = "1.0.0") -> Path:
    p = root / "plugin"
    write(p, {".claude-plugin/plugin.json": json.dumps({"name": "stackfoundry", "version": version}),
              "skills/demo/SKILL.md": skill, "agents/hunter.md": AGENT})
    return p


def extension(body: str, name: str = "demo", mode: str = "extend") -> str:
    return f"---\nextends: {name}\nmode: {mode}\n---\n{body}"


class FormatTests(unittest.TestCase):
    def test_headings_drop_numbers_and_ignore_fences(self):
        self.assertEqual(ext.headings(SKILL), ["Survey", "Ask", "Report"])
        self.assertEqual(ext.norm("3. **Ask**"), ext.norm("ask"))
        self.assertEqual(ext.norm("Step 2: Verify"), "verify")

    def test_every_section_kind_parses(self):
        body = "notes\n## Rules\nr\n## Before: Ask\nb\n## After: 1. Survey\na\n## Replace: report\nx\n## Target: api\nt\n"
        kinds = [(k, a) for k, a, _, _ in ext.sections(body)]
        self.assertEqual(kinds, [("Rules", None), ("Before", "Ask"), ("After", "1. Survey"), ("Replace", "report"),
                                 ("Target", "api")])

    def test_a_valid_extension_passes_and_anchors_survive_renumbering(self):
        with TempRepo() as root:
            p = plugin(root)
            targets_json(root, {"targets": [{"name": "api", "paths": ["src/**"]}]})
            write(root, {".stackfoundry/extensions/skills/demo.md": extension(
                "## Rules\nAlways cite.\n## After: 7. survey\nAlso list the docs.\n## Target: api\nPublic API.\n")})
            rep = ext.check(root, p)
        self.assertEqual(rep.errors, [])
        self.assertEqual(rep.rows[0]["mode"], "extend")

    def test_each_defect_is_reported(self):
        with TempRepo() as root:
            p = plugin(root)
            targets_json(root, {"targets": [{"name": "api", "paths": ["src/**"]}]})
            write(root, {
                ".stackfoundry/extensions/skills/demo.md": extension(
                    "## Before: Surveys of things\nx\n## Target: web\ny\n## Notes\nz\n## Rules: loud\nq\n"),
                ".stackfoundry/extensions/skills/ghost.md": extension("## Rules\nx\n", name="ghost"),
                ".stackfoundry/extensions/agents/hunter.md": extension("## Rules\nx\n", name="other"),
                ".stackfoundry/extensions/skills/copy.md": extension("whole text\n", name="copy", mode="replace"),
            })
            errors = " | ".join(ext.check(root, p).errors)
        for needle in ("anchor 'Surveys of things' matches no heading of demo; nearest: 'Survey'",
                       "unknown target 'web'", "unknown section '## Notes'", "'## Rules' takes no argument",
                       "no skill named 'ghost'", "must equal the file name 'hunter'", "no skill named 'copy'"):
            self.assertIn(needle, errors)

    def test_replace_without_a_base_fails(self):
        with TempRepo() as root:
            p = plugin(root)
            write(root, {".stackfoundry/extensions/skills/demo.md": extension("Mine.\n", mode="replace")})
            self.assertIn("needs a base copy", " ".join(ext.check(root, p).errors))

    def test_new_scaffolds_and_refuses_to_overwrite(self):
        with TempRepo() as root:
            p = plugin(root)
            rel = ext.new(root, "skill", "demo", replace=False, plugin_root=p)
            text = (root / rel).read_text(encoding="utf-8")
            self.assertIn('"Survey", "Ask", "Report"', text)
            with self.assertRaises(ValueError):
                ext.new(root, "skill", "demo", replace=False, plugin_root=p)
            with self.assertRaises(ValueError):
                ext.new(root, "skill", "../demo", replace=False, plugin_root=p)
            self.assertEqual(ext.check(root, p).errors, [])


@unittest.skipUnless(HAS_GIT, "git not available")
class MergeTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="репо-")  # a Cyrillic path, as on the author's machine
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.plugin = plugin(self.root)
        self.rel = ext.new(self.root, "skill", "demo", replace=True, plugin_root=self.plugin)

    def edit_repo(self, old, new, crlf=False):
        f = self.root / self.rel
        text = f.read_text(encoding="utf-8").replace(old, new)
        f.write_bytes(text.replace("\n", "\r\n" if crlf else "\n").encode("utf-8"))

    def update_plugin(self, old, new, version="1.1.0"):
        plugin(self.root, SKILL.replace(old, new), version)

    def test_a_fresh_copy_is_current(self):
        self.assertEqual(ext.merge(self.root, self.rel, plugin_root=self.plugin)["status"], "current")
        self.assertFalse(ext.check(self.root, self.plugin).rows[0]["behind"])

    def test_clean_merge_keeps_both_changes_and_advances_the_base(self):
        self.edit_repo("Ask one question.", "Ask one question, in Ukrainian.", crlf=True)
        self.update_plugin("Write the report.", "Write the report and link it.")
        self.assertTrue(ext.check(self.root, self.plugin).rows[0]["behind"])
        result = ext.merge(self.root, self.rel, plugin_root=self.plugin)
        self.assertEqual(result["status"], "merged")
        raw = (self.root / self.rel).read_bytes()
        self.assertIn(b"\r\n", raw)  # the repo's line endings are kept
        text = raw.decode("utf-8")
        self.assertIn("in Ukrainian", text)
        self.assertIn("and link it", text)
        self.assertTrue(text.startswith("---\r\nextends: demo\r\nmode: replace\r\n---"))
        entry = ext.load_index(self.root)["files"][self.rel]
        self.assertEqual(entry["version"], "1.1.0")
        self.assertFalse(ext.check(self.root, self.plugin).rows[0]["behind"])
        self.assertEqual(ext.merge(self.root, self.rel, plugin_root=self.plugin)["status"], "current")

    def test_conflict_goes_to_a_merge_file_until_resolved(self):
        self.edit_repo("Ask one question.", "Ask two questions.")
        self.update_plugin("Ask one question.", "Ask three questions.")
        result = ext.merge(self.root, self.rel, plugin_root=self.plugin)
        self.assertEqual(result["status"], "conflict")
        pending = self.root / result["file"]
        self.assertIn("<<<<<<< repo", pending.read_text(encoding="utf-8"))
        self.assertIn("Ask two questions.", (self.root / self.rel).read_text(encoding="utf-8"))  # untouched
        with self.assertRaises(ValueError):
            ext.merge(self.root, self.rel, resolved=True, plugin_root=self.plugin)
        settled = pending.read_text(encoding="utf-8")
        settled = settled.split("<<<<<<< repo\n")[0] + "Ask two or three questions.\n" + settled.split(">>>>>>> plugin\n")[1]
        pending.write_text(settled, encoding="utf-8")
        self.assertEqual(ext.merge(self.root, self.rel, resolved=True, plugin_root=self.plugin)["status"], "merged")
        self.assertFalse(pending.exists())
        self.assertIn("two or three", (self.root / self.rel).read_text(encoding="utf-8"))
        self.assertFalse(ext.check(self.root, self.plugin).rows[0]["behind"])

    def test_materialized_agent_base_and_forget(self):
        write(self.root, {".stackfoundry/agents/api-hunter.md": AGENT.replace("name: hunter", "name: api-hunter")})
        self.assertIn("without a base copy", " ".join(ext.check(self.root, self.plugin).warnings))
        ext.record_base(self.root, ".stackfoundry/agents/api-hunter.md", "agents/hunter.md", self.plugin)
        rows = {r["file"]: r for r in ext.check(self.root, self.plugin).rows}
        self.assertEqual(rows[".stackfoundry/agents/api-hunter.md"]["kind"], "materialized")
        self.assertTrue(ext.forget(self.root, ".stackfoundry/agents/api-hunter.md"))
        self.assertFalse((self.root / ".stackfoundry/extensions/.base/materialized/api-hunter.md").exists())


class CliTests(unittest.TestCase):
    def test_check_exit_codes_and_refused_paths(self):
        with TempRepo() as root:
            p = plugin(root)
            ok = run_cli(["extensions", "check", "--root", str(root), "--plugin-root", str(p)])
            self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
            write(root, {".stackfoundry/extensions/skills/demo.md": extension("## After: Nowhere\nx\n")})
            bad = run_cli(["extensions", "check", "--root", str(root), "--plugin-root", str(p)])
            self.assertEqual(bad.returncode, 1)
            self.assertIn("matches no heading", bad.stdout)
            listed = run_cli(["extensions", "list", "--json", "--root", str(root), "--plugin-root", str(p)])
            self.assertEqual(json.loads(listed.stdout)["extensions"][0]["extends"], "demo")
            outside = run_cli(["extensions", "merge", str(root / "README.md"), "--root", str(root)])
            self.assertEqual(outside.returncode, 2)
            self.assertIn("not an extension", outside.stderr)


if __name__ == "__main__":
    unittest.main()
