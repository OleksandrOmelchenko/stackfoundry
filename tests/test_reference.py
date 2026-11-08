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


if __name__ == "__main__":
    unittest.main()
