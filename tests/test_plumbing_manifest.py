"""verify-plumbing and manifest record/diff."""
import json
import unittest

from tests._support import TempRepo, run_cli, write
from stackfoundry import manifest
from stackfoundry.plumbing import check

GOOD_SKILL = "---\nname: good\ndescription: Does a thing. Use when asked.\n---\nRun `/stackfoundry:good`. " \
             "See [ref](${CLAUDE_PLUGIN_ROOT}/reference/x.md).\n"
GOOD_AGENT = "---\nname: hunter\ndescription: Read-only hunter.\ntools: Read, Grep, WebSearch\n---\n" \
             "## Tooling\n- `WebSearch` for advisories.\n- Never `Edit` anything.\n"


class PlumbingTests(unittest.TestCase):
    def test_a_clean_plugin_passes(self):
        files = {".claude-plugin/plugin.json": "{}", "skills/good/SKILL.md": GOOD_SKILL,
                 "agents/hunter.md": GOOD_AGENT, "reference/x.md": "x"}
        with TempRepo(files) as root:
            rep = check(root)
        self.assertEqual(rep.errors, [])

    def test_each_defect_is_reported(self):
        files = {
            ".claude-plugin/plugin.json": "{}",
            "skills/good/SKILL.md": GOOD_SKILL,  # its reference/x.md is missing here
            "skills/misnamed/SKILL.md": "---\nname: other\ndescription: x\n---\n",
            "skills/long/SKILL.md": "---\nname: long\ndescription: " + "x" * 251 + "\n---\n",
            "skills/dangling/SKILL.md": "---\nname: dangling\ndescription: x\n---\nThen `/stackfoundry:nope`. "
                                        "Dispatch `Agent` with subagent_type: \"ghost\". [a](missing.md)\n",
            "agents/hunter.md": GOOD_AGENT.replace("Read, Grep, WebSearch", "Read, Grep, Edit"),
        }
        with TempRepo(files) as root:
            errors = " | ".join(check(root).errors)
        for needle in ("reference/x.md does not exist", "does not match the folder", "251 characters",
                       "/stackfoundry:nope", "'ghost'", "missing.md", "read-only but granted Edit",
                       "lacks it"):
            self.assertIn(needle, errors)

    def test_the_shipped_plugin_is_clean(self):
        proc = run_cli(["verify-plumbing", str(manifest.PLUGIN_ROOT)])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


class ManifestTests(unittest.TestCase):
    def test_states_and_actions(self):
        template = "reference/detect-signals.json"  # exists in the plugin; no frontmatter -> version "1"
        with TempRepo({"a.md": "one\n", "b.md": "two\n", "c.md": "three\n", "d.md": "four\n"}) as root:
            manifest.record(root, ["a.md", "b.md", "c.md"], template, "generated")
            manifest.record(root, ["d.md"], template, "materialized")
            write(root, {"b.md": "edited\n"})
            (root / "c.md").unlink()
            # A CRLF checkout of an untouched file is not an edit.
            (root / "a.md").write_bytes(b"one\r\n")
            rows = {r["file"]: r for r in manifest.diff(root)}
            self.assertEqual(rows["a.md"]["state"], "untouched")
            self.assertEqual(rows["b.md"]["state"], "edited")
            self.assertEqual(rows["c.md"]["state"], "deleted")
            self.assertEqual(rows["d.md"]["action"], "skip (materialized)")

            # Simulate a newer template version: untouched -> replace, edited -> ask.
            data = json.loads((root / ".claude/stackfoundry/manifest.lock.json").read_text(encoding="utf-8"))
            for entry in data["files"].values():
                entry["templateVersion"] = "0"
            (root / ".claude/stackfoundry/manifest.lock.json").write_text(json.dumps(data), encoding="utf-8")
            rows = {r["file"]: r for r in manifest.diff(root)}
            self.assertEqual(rows["a.md"]["action"], "replace")
            self.assertEqual(rows["b.md"]["action"], "three-way merge, ask")
            self.assertEqual(rows["c.md"]["action"], "leave deleted")


if __name__ == "__main__":
    unittest.main()
