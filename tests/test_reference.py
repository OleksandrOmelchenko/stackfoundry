"""The reference material is well-formed: JSON parses, examples satisfy the profile checks, templates carry their
version and output, and tracker templates use the format `stackfoundry tracker` parses."""
import json
import unittest

from tests._support import PLUGIN
from stackfoundry.frontmatter import split
from stackfoundry.profile import EXPOSURES, check_targets

REF = PLUGIN / "reference"


class ReferenceTests(unittest.TestCase):
    def test_every_json_file_parses(self):
        for path in REF.rglob("*.json"):
            with self.subTest(path=path.name):
                json.loads(path.read_text(encoding="utf-8"))

    def test_the_example_targets_pass_the_profile_checks(self):
        data = json.loads((REF / "examples" / "targets.example.json").read_text(encoding="utf-8"))
        self.assertEqual(check_targets(data), [])

    def test_the_schema_and_the_loader_agree_on_exposure(self):
        schema = json.loads((REF / "schemas" / "targets.schema.json").read_text(encoding="utf-8"))
        enum = schema["properties"]["targets"]["items"]["properties"]["exposure"]["enum"]
        self.assertEqual(set(enum), EXPOSURES)

    def test_every_template_declares_its_version_and_output(self):
        for folder in ("templates", "rulebooks", "trackers"):
            for path in (REF / folder).glob("*.md"):
                if path.name == "README.md":
                    continue
                with self.subTest(path=f"{folder}/{path.name}"):
                    fields, _, errors = split(path.read_text(encoding="utf-8"))
                    self.assertEqual(errors, [])
                    self.assertIsInstance(fields.get("templateVersion"), int)
                    self.assertTrue(fields.get("output"))

    def test_detect_signals_reference_only_known_layers(self):
        signals = json.loads((REF / "detect-signals.json").read_text(encoding="utf-8"))
        layers = {"language", "app-model", "capability", "tooling"}
        for eco, rules in signals["dependencies"].items():
            for rule in rules:
                self.assertIn(rule["layer"], layers, f"{eco}:{rule['name']}")
        for rule in signals["configFiles"] + list(signals["dotnetSdks"].values()) + signals["dotnetProperties"]:
            self.assertIn(rule["layer"], layers)


class UnattendedTests(unittest.TestCase):
    """Threat model T11: unattended runs never auto-accept edits, and each one checks its side effects."""

    UNATTENDED = ("tech-radar", "stackfoundry-radar", "check-updates", "flaky-watch", "docs-reconciler", "whats-next")

    def test_no_scheduling_line_auto_accepts_or_bypasses(self):
        text = (PLUGIN / "skills" / "schedule" / "SKILL.md").read_text(encoding="utf-8")
        for line in text.splitlines():
            if "--permission-mode" in line:
                with self.subTest(line=line.strip()[:80]):
                    self.assertIn("--permission-mode dontAsk", line)
        self.assertNotIn("--permission-mode acceptEdits", text)
        self.assertNotIn("bypassPermissions", text)

    def test_every_unattended_skill_runs_the_side_effects_check(self):
        for skill in self.UNATTENDED:
            with self.subTest(skill=skill):
                text = (PLUGIN / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
                self.assertIn("side-effects start", text)
                self.assertRegex(text, r"end\s+--allow")
                self.assertNotIn("git status --porcelain", text)


class LandingPrsTests(unittest.TestCase):
    """Threat model T13: landing PRs never runs a command a PR branch's own config supplied."""

    def test_config_comes_from_the_default_branch_and_commands_are_confirmed(self):
        text = " ".join((PLUGIN / "skills" / "github-prs" / "SKILL.md").read_text(encoding="utf-8").split())
        self.assertIn("git show origin/<default>:.stackfoundry/<file>", text)
        self.assertIn("never from a PR's branch", text)
        self.assertIn("**control files**", text)
        self.assertIn("lists every command the resolution will run", text)
        self.assertIn("is named in the report, never run", text)


if __name__ == "__main__":
    unittest.main()
