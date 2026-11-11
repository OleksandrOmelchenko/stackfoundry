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


if __name__ == "__main__":
    unittest.main()
