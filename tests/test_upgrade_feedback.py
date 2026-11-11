"""Regressions for what the BookStore 0.3.0 upgrade reported: hand-merged files, and previewing a block change."""
import json
import unittest

from tests._support import PLUGIN, TempRepo, run_cli, targets_json, write
from stackfoundry import manifest

TEMPLATE = "reference/templates/target.md"  # any real template; the test records an older version of it


class MergedKindTests(unittest.TestCase):
    """A file the team merged by hand is recorded with its own hash, so it reads `untouched`. Before `merged`,
    `upgrade` then replaced it without asking (BookStore's four hand-merged rulebooks)."""

    def entry(self, root, kind, template=TEMPLATE):
        path = root / ".stackfoundry/targets/api.md"
        data = {"schemaVersion": 1, "pluginVersion": "0.2.0", "files": {".stackfoundry/targets/api.md": {
            "template": template, "templateVersion": "0", "sha256": manifest.sha256(path), "kind": kind}}}
        write(root, {".stackfoundry/manifest.lock.json": json.dumps(data)})
        return next(r for r in manifest.diff(root) if r["file"] == ".stackfoundry/targets/api.md")

    def test_a_merged_file_whose_template_moved_is_asked_about_never_replaced(self):
        with TempRepo({".stackfoundry/targets/api.md": "# api\n\nThe team's own section.\n"}) as root:
            row = self.entry(root, "merged")
        self.assertEqual((row["state"], row["outdated"]), ("untouched", True))
        self.assertEqual(row["action"], "three-way merge, ask")

    def test_a_generated_file_is_still_replaced_when_untouched(self):
        with TempRepo({".stackfoundry/targets/api.md": "# api\n"}) as root:
            self.assertEqual(self.entry(root, "generated")["action"], "replace")

    def test_a_merged_rulebook_is_merged_by_hand_after_a_re_research(self):
        with TempRepo({".stackfoundry/targets/api.md": "# api\n"}) as root:
            self.assertEqual(self.entry(root, "merged", "research")["action"],
                             "re-research via research-stack, then merge by hand (merged)")

    def test_record_accepts_merged_and_the_schema_allows_it(self):
        with TempRepo({".stackfoundry/targets/api.md": "# api\n"}) as root:
            targets_json(root, {"targets": []})
            proc = run_cli(["manifest", "record", ".stackfoundry/targets/api.md", "--template", TEMPLATE,
                            "--kind", "merged", "--root", str(root)], cwd=root)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            data = json.loads((root / ".stackfoundry/manifest.lock.json").read_text(encoding="utf-8"))
        self.assertEqual(data["files"][".stackfoundry/targets/api.md"]["kind"], "merged")
        schema = json.loads((PLUGIN / "reference/schemas/manifest.schema.json").read_text(encoding="utf-8"))
        kinds = schema["properties"]["files"]["additionalProperties"]["properties"]["kind"]["enum"]
        self.assertIn("merged", kinds)

    def test_the_skills_record_hand_merged_files_as_merged(self):
        for rel in ("skills/upgrade/SKILL.md", "skills/init/SKILL.md", "skills/sync/SKILL.md",
                    "skills/research-stack/SKILL.md"):
            with self.subTest(skill=rel):
                self.assertIn("--kind merged", (PLUGIN / rel).read_text(encoding="utf-8"))


RULE = '---\ndescription: "X{i} rulebook (tooling layer). Researched."\npaths:\n  - "src/x{i}/**"\n---\n\n# X\n'
OLD_BLOCK = "# Team\n\n<!-- stackfoundry:begin old -->\nstale\n<!-- stackfoundry:end -->\n"


class BlockDiffTests(unittest.TestCase):
    """`render-block --diff` shows a block change and its size before anything is written."""

    def setUp(self):
        self.repo = TempRepo()
        self.root = self.repo.__enter__()
        self.addCleanup(self.repo.__exit__, None, None, None)
        targets_json(self.root, {"targets": [{"name": "api", "paths": ["src/**"]}]})
        config = {"schemaVersion": 1, "clients": ["claude-code", "codex"]}
        write(self.root, {".stackfoundry/config.json": json.dumps(config),
                          ".stackfoundry/rules/tooling-x0.md": RULE.format(i=0), "CLAUDE.md": OLD_BLOCK})

    def files(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

    def diff(self):
        proc = run_cli(["render-block", "--diff", "--root", str(self.root)])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return proc.stdout

    def test_the_preview_shows_each_change_with_its_size_and_writes_nothing(self):
        before = self.files()
        out = self.diff()
        self.assertIn("--- a/CLAUDE.md\n+++ b/CLAUDE.md\n", out)
        self.assertIn("-stale\n", out)
        self.assertRegex(out, r"size: CLAUDE\.md \d+ bytes -> \d+ bytes")
        self.assertIn("--- /dev/null\n+++ b/AGENTS.md\n", out)
        self.assertIn("size: AGENTS.md absent -> ", out)
        self.assertEqual(self.files(), before)

    def test_a_table_moving_to_the_index_shows_up_in_the_preview(self):
        write(self.root, {f".stackfoundry/rules/tooling-x{i}.md": RULE.format(i=i) for i in range(1, 150)})
        out = self.diff()
        self.assertIn("+++ b/.stackfoundry/rulebooks.md\n", out)
        self.assertIn("size: .stackfoundry/rulebooks.md absent -> ", out)
        self.assertFalse((self.root / ".stackfoundry/rulebooks.md").exists())

    def test_no_change_says_so(self):
        self.assertEqual(run_cli(["render-block", "--write", "--root", str(self.root)]).returncode, 0)
        self.assertEqual(self.diff(), "render-block: no change\n")


if __name__ == "__main__":
    unittest.main()
