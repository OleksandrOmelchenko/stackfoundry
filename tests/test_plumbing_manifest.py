"""verify-plumbing and manifest record/diff."""
import json
import unittest

from tests._support import TempRepo, run_cli, write
from stackfoundry import manifest, preamble
from stackfoundry.plumbing import check

GOOD_SKILL = "---\nname: good\ndescription: Does a thing. Use when asked.\n---\n# Good\n\n" + preamble.SKILL + \
             "\nRun `/stackfoundry:good`. See [ref](${CLAUDE_PLUGIN_ROOT}/reference/x.md).\n"
GOOD_AGENT = "---\nname: hunter\ndescription: Read-only hunter.\ntools: Read, Grep, WebSearch\n---\n# Hunter\n\n" + \
             preamble.AGENT + "\n## Tooling\n- `WebSearch` for advisories.\n- Never `Edit` anything.\n"


class PlumbingTests(unittest.TestCase):
    def test_a_clean_plugin_passes(self):
        files = {".claude-plugin/plugin.json": "{}", "skills/good/SKILL.md": GOOD_SKILL,
                 "agents/hunter.md": GOOD_AGENT, "reference/x.md": "x", "reference/clients.md": "x",
                 "reference/extensions.md": "x", "scripts/stackfoundry.sh": "", "scripts/stackfoundry.ps1": ""}
        with TempRepo(files) as root:
            rep = check(root)
        self.assertEqual(rep.errors, [])

    def test_a_repo_resolves_the_plugin_root_to_the_installed_plugin(self):
        """A materialized agent's ${CLAUDE_PLUGIN_ROOT} links point into the plugin, not the repo."""
        agent = GOOD_AGENT.replace("name: hunter", "name: api-hunter")
        files = {".stackfoundry/agents/api-hunter.md": agent + "\nSee ${CLAUDE_PLUGIN_ROOT}/reference/extensions.md "
                                                               "and ${CLAUDE_PLUGIN_ROOT}/reference/nope.md.\n"}
        with TempRepo(files) as root:
            report = check(root)
        errors = " | ".join(report.errors)
        self.assertIn("api-hunter", report.agents)
        self.assertNotIn("reference/extensions.md does not exist", errors)
        self.assertIn("reference/nope.md does not exist", errors)

    def test_each_defect_is_reported(self):
        files = {
            ".claude-plugin/plugin.json": "{}",
            "skills/good/SKILL.md": GOOD_SKILL,  # its reference/x.md is missing here
            "skills/misnamed/SKILL.md": "---\nname: other\ndescription: x\n---\n",
            "skills/long/SKILL.md": "---\nname: long\ndescription: " + "x" * 251 + "\n---\n",
            "skills/dangling/SKILL.md": "---\nname: dangling\ndescription: x\n---\nThen `/stackfoundry:nope`. "
                                        "Dispatch `Agent` with subagent_type: \"ghost\". [a](missing.md)\n",
            "agents/hunter.md": GOOD_AGENT.replace("Read, Grep, WebSearch", "Read, Grep, Edit"),
            # read-only with a shell, but Tooling never says what the shell is for (threat model T3)
            "agents/sheller.md": GOOD_AGENT.replace("name: hunter", "name: sheller").replace(
                "Read, Grep, WebSearch", "Read, Grep, WebSearch, Bash"),
            "skills/No_Caps/SKILL.md": "---\nname: No_Caps\ndescription: x\n---\n# No caps\n",
            "skills/slashonly/SKILL.md": GOOD_SKILL.replace("name: good", "name: slashonly").replace(
                "---\n#", "disable-model-invocation: true\n---\n#", 1),
            "skills/silent/SKILL.md": GOOD_SKILL.replace("name: good", "name: silent").replace(
                "Does a thing. Use when asked.", "Does a thing, used for the release."),
        }
        with TempRepo(files) as root:
            report = check(root)
        errors = " | ".join(report.errors)
        for needle in ("reference/x.md does not exist", "does not match the folder", "251 characters",
                       "/stackfoundry:nope", "'ghost'", "missing.md", "read-only but granted Edit",
                       "lacks it", "single hyphens", "portable-form preamble",
                       "read-only but granted Bash without naming",
                       "grants Bash together with WebSearch"):  # T2: a shell beside the web
            self.assertIn(needle, errors)
        def errors_for(skill):
            return " | ".join(e for e in report.errors if f"{skill}{'/'}SKILL.md" in e.replace("\\", "/"))
        self.assertIn("slash-only", errors_for("slashonly"))
        self.assertNotIn("plain-language trigger", errors_for("slashonly"))
        self.assertIn("plain-language trigger", errors_for("silent"))
        self.assertNotIn("plain-language trigger", errors_for("good"))

    def test_the_walkthrough_names_every_skill(self):
        walkthrough = GOOD_SKILL.replace("name: good", "name: walkthrough") + \
            "\n## The groups\n\n| Group | Skills |\n|---|---|\n| One | `good`, `ghost` |\n\n## 1. State\n\n`other`\n"
        files = {".claude-plugin/plugin.json": "{}", "skills/good/SKILL.md": GOOD_SKILL,
                 "skills/extra/SKILL.md": GOOD_SKILL.replace("name: good", "name: extra"),
                 "skills/walkthrough/SKILL.md": walkthrough, "reference/x.md": "x", "reference/clients.md": "x",
                 "scripts/stackfoundry.sh": "", "scripts/stackfoundry.ps1": ""}
        with TempRepo(files) as root:
            errors = " | ".join(check(root).errors)
        self.assertIn("leaves out extra", errors)  # `other` below the table does not count
        self.assertIn("'ghost', which is not a skill", errors)
        self.assertNotIn("leaves out good", errors)

    def test_a_repo_check_includes_its_extensions(self):
        files = {".stackfoundry/extensions/skills/backlog.md": "---\nextends: backlog\n---\n## After: No such step\nx\n"}
        with TempRepo(files) as root:
            errors = " | ".join(check(root).errors)
        self.assertIn("extension .stackfoundry/extensions/skills/backlog.md", errors)
        self.assertIn("matches no heading of backlog", errors)

    def test_plain_language_rules_apply_only_to_the_plugin(self):
        """A repo's own .claude/skills may stay slash-only; the trigger rule is the plugin's."""
        files = {".claude/skills/own/SKILL.md": "---\nname: own\ndescription: Release it.\n"
                                                "disable-model-invocation: true\n---\n# Own\n"}
        with TempRepo(files) as root:
            errors = " | ".join(check(root).errors)
        self.assertNotIn("slash-only", errors)
        self.assertNotIn("plain-language trigger", errors)

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
            self.assertEqual(rows["d.md"]["action"], "merge via extensions merge (materialized)")

            # Simulate a newer template version: untouched -> replace, edited -> ask.
            data = json.loads((root / ".stackfoundry/manifest.lock.json").read_text(encoding="utf-8"))
            for entry in data["files"].values():
                entry["templateVersion"] = "0"
            (root / ".stackfoundry/manifest.lock.json").write_text(json.dumps(data), encoding="utf-8")
            rows = {r["file"]: r for r in manifest.diff(root)}
            self.assertEqual(rows["a.md"]["action"], "replace")
            self.assertEqual(rows["b.md"]["action"], "three-way merge, ask")
            self.assertEqual(rows["c.md"]["action"], "leave deleted")


if __name__ == "__main__":
    unittest.main()
