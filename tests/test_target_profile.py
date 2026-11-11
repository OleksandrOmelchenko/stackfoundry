"""`stackfoundry gate` and `render-target`: a target profile's Stack and Gate come from the profile, not by hand."""
import json
import unittest

from tests._support import PLUGIN, TempRepo, run_cli, targets_json, write
from stackfoundry import target_profile

TARGETS = {"targets": [{
    "name": "api", "paths": ["src/**"], "packs": ["language-python", "tooling-pytest"],
    "gate": {"build": ["python -m build"], "test": ["pytest -q"], "lint": ["ruff check ."],
             "preconditions": ["Docker running"]},
    "tests": [{"name": "unit", "kind": "unit", "command": "pytest -q tests/unit", "shuffle": "pytest -q -p random"}],
    "localUrl": "http://localhost:8000",
}, {"name": "docs", "paths": ["docs/**"], "packs": ["language-markdown"]}]}


class GateTests(unittest.TestCase):
    def setUp(self):
        self.repo = TempRepo()
        self.root = self.repo.__enter__()
        self.addCleanup(self.repo.__exit__, None, None, None)
        targets_json(self.root, TARGETS)

    def cli(self, *args):
        return run_cli(["gate", *args, "--root", str(self.root)])

    def gates(self):
        return json.loads((self.root / ".stackfoundry/gates.json").read_text(encoding="utf-8"))

    def test_record_then_list(self):
        self.assertEqual(self.cli("record", "api", "--command", "pytest -q", "--status", "proven").returncode, 0)
        self.assertEqual(self.cli("record", "api", "--command", "ruff check .", "--status", "failed").returncode, 0)
        self.assertEqual(self.gates(), {"schemaVersion": 1, "targets": {"api": {"pytest -q": "proven",
                                                                                "ruff check .": "failed"}}})
        rows = json.loads(self.cli("list", "--json").stdout)
        self.assertIn({"target": "api", "command": "python -m build", "status": "unproven"}, rows)
        self.assertIn({"target": "api", "command": "pytest -q -p random", "status": "unproven"}, rows)  # a suite's
        self.assertIn({"target": "api", "command": "pytest -q", "status": "proven"}, rows)

    def test_unproven_removes_the_entry_and_an_emptied_target(self):
        self.cli("record", "api", "--command", "pytest -q", "--status", "proven")
        self.cli("record", "api", "--command", "pytest -q", "--status", "unproven")
        self.assertEqual(self.gates(), {"schemaVersion": 1, "targets": {}})

    def test_an_edited_command_reads_unproven_by_itself(self):
        self.cli("record", "api", "--command", "pytest -q", "--status", "proven")
        edited = json.loads(json.dumps(TARGETS))
        edited["targets"][0]["gate"]["test"] = ["pytest -q -x"]
        targets_json(self.root, edited)
        rows = {(r["target"], r["command"]): r["status"] for r in target_profile.listing(self.root)}
        self.assertEqual(rows[("api", "pytest -q -x")], "unproven")
        self.assertNotIn(("api", "pytest -q"), rows)

    def test_an_unknown_target_or_command_is_refused(self):
        bad_target = self.cli("record", "web", "--command", "pytest -q", "--status", "proven")
        self.assertEqual(bad_target.returncode, 2)
        self.assertIn("no target named 'web'", bad_target.stderr)
        bad_command = self.cli("record", "api", "--command", "rm -rf /", "--status", "proven")
        self.assertEqual(bad_command.returncode, 2)
        self.assertIn("is not a gate or suite command of 'api'", bad_command.stderr)
        self.assertFalse((self.root / ".stackfoundry/gates.json").exists())

    def test_the_file_is_lf_and_matches_its_schema_shape(self):
        self.cli("record", "api", "--command", "pytest -q", "--status", "proven")
        self.assertNotIn(b"\r\n", (self.root / ".stackfoundry/gates.json").read_bytes())
        schema = json.loads((PLUGIN / "reference/schemas/gates.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["targets"]["additionalProperties"]["additionalProperties"]["enum"],
                         ["proven", "failed"])


if __name__ == "__main__":
    unittest.main()
