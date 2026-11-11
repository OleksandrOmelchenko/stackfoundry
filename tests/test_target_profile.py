"""`stackfoundry gate` and `render-target`: a target profile's Stack and Gate come from the profile, not by hand."""
import json
import unittest

from tests._support import PLUGIN, TempRepo, run_cli, targets_json, write
from stackfoundry import manifest, target_profile

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


PROFILE = """# Target `api`

The API. Exposure: public.

## Stack

| Layer | Pack | Rulebook |
|---|---|---|
| language | `language-python` | hand-written row |

## Where things are

- Source: `src/**`. Entry point: `src/app.py` `main`.

## Gate

Hand-written gate notes that the renderer now owns.

## Oracle sources

The team's own oracle notes.

## Traps

- One trap, with its evidence.
"""


class RenderTargetTests(unittest.TestCase):
    def setUp(self):
        self.repo = TempRepo()
        self.root = self.repo.__enter__()
        self.addCleanup(self.repo.__exit__, None, None, None)
        targets_json(self.root, TARGETS)
        write(self.root, {".stackfoundry/rules/language-python.md": "---\ndescription: d\npaths: ['**/*.py']\n---\n",
                          ".stackfoundry/targets/api.md": PROFILE})
        self.path = self.root / ".stackfoundry/targets/api.md"

    def cli(self, *args):
        proc = run_cli(["render-target", "api", *args, "--root", str(self.root)])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return proc.stdout

    def test_stack_and_gate_come_from_the_profile(self):
        run_cli(["gate", "record", "api", "--command", "pytest -q", "--status", "proven", "--root", str(self.root)])
        bodies = target_profile.render(self.root, "api")
        self.assertEqual(bodies["stack"].splitlines(), [
            "| Layer | Pack | Rulebook |", "|---|---|---|",
            "| language | `language-python` | [language-python](../rules/language-python.md) |",
            "| tooling | `tooling-pytest` | not researched yet |"])
        gate = bodies["gate"]
        self.assertIn("```sh\npython -m build\npytest -q\nruff check .\n```", gate)
        self.assertIn("- `pytest -q`: proven\n", gate)
        self.assertIn("- `python -m build`: unproven\n", gate)
        self.assertIn("Preconditions: Docker running.", gate)
        self.assertIn("shuffled `pytest -q -p random` (unproven)", gate)
        self.assertIn("mutation: none yet (/stackfoundry:setup-mutation)", " ".join(gate.split()))
        self.assertIn("Local URL for live repros: `http://localhost:8000`.", gate)

    def test_the_first_write_migrates_an_unmarked_profile_and_keeps_every_other_section(self):
        self.cli("--write")
        text = self.path.read_text(encoding="utf-8")
        self.assertNotIn("hand-written row", text)
        self.assertNotIn("Hand-written gate notes", text)
        for kept in ("The API. Exposure: public.", "- Source: `src/**`. Entry point: `src/app.py` `main`.",
                     "## Oracle sources\n\nThe team's own oracle notes.\n", "## Traps\n\n- One trap, with its evidence.\n"):
            self.assertIn(kept, text)
        self.assertEqual(text.count("<!-- stackfoundry:begin target-"), 2)
        self.assertEqual(self.cli("--diff"), "render-target: no change\n")  # idempotent

    def test_prose_outside_the_markers_survives_a_re_render(self):
        self.cli("--write")
        text = self.path.read_text(encoding="utf-8").replace("The API. Exposure: public.", "The API, edited by the team.")
        self.path.write_text(text, encoding="utf-8")
        edited = json.loads(json.dumps(TARGETS))
        edited["targets"][0]["packs"].append("capability-auth")
        targets_json(self.root, edited)
        self.cli("--write")
        after = self.path.read_text(encoding="utf-8")
        self.assertIn("The API, edited by the team.", after)
        self.assertIn("| capability | `capability-auth` | not researched yet |", after)

    def test_crlf_is_kept_and_diff_writes_nothing(self):
        self.path.write_bytes(PROFILE.replace("\n", "\r\n").encode("utf-8"))
        before = self.path.read_bytes()
        out = self.cli("--diff")
        self.assertIn("+<!-- stackfoundry:begin target-stack", out)
        self.assertRegex(out, r"size: \.stackfoundry/targets/api\.md \d+ bytes -> \d+ bytes")
        self.assertEqual(self.path.read_bytes(), before)
        self.cli("--write")
        data = self.path.read_bytes()
        self.assertEqual(data.count(b"\n"), data.count(b"\r\n"))

    def test_a_profile_without_its_heading_is_an_error(self):
        self.path.write_text("# Target `api`\n\nNo sections.\n", encoding="utf-8")
        proc = run_cli(["render-target", "api", "--write", "--root", str(self.root)])
        self.assertEqual(proc.returncode, 2)
        self.assertIn("no '## Stack' heading", proc.stderr)

    def test_the_manifest_hashes_only_the_rendered_sections_of_a_profile(self):
        self.cli("--write")
        recorded = manifest.sha256(self.path)
        self.path.write_text(self.path.read_text(encoding="utf-8").replace("The team's own oracle notes.", "Changed."),
                             encoding="utf-8")
        self.assertEqual(manifest.sha256(self.path), recorded)  # prose edit: still untouched
        one = "a\n<!-- stackfoundry:begin x -->\nb\n<!-- stackfoundry:end -->\nc\n"
        write(self.root, {"CLAUDE.md": one})
        import hashlib
        block = b"<!-- stackfoundry:begin x -->\nb\n<!-- stackfoundry:end -->"
        self.assertEqual(manifest.sha256(self.root / "CLAUDE.md"), hashlib.sha256(block).hexdigest())  # unchanged


class SkillWiringTests(unittest.TestCase):
    """The skills that write a profile's Stack or Gate call the renderer instead of editing those sections by hand."""

    def test_each_writer_renders_and_records_through_the_cli(self):
        expected = {"skills/init/SKILL.md": ("render-target <target> --write", "gate record"),
                    "skills/sync/SKILL.md": ("render-target <target> --diff", "--status unproven"),
                    "skills/upgrade/SKILL.md": ("render-target --write", "render-target --diff"),
                    "skills/scaffold-test-harness/SKILL.md": ("render-target <target> --write", "gate record"),
                    "skills/setup-mutation/SKILL.md": ("render-target <target> --write", "gate record")}
        for rel, needles in expected.items():
            text = " ".join((PLUGIN / rel).read_text(encoding="utf-8").split())
            for needle in needles:
                with self.subTest(skill=rel, needle=needle):
                    self.assertIn(needle, text)
        mutation = (PLUGIN / "skills/setup-mutation/SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("*Mutation lane* line of the", mutation)


if __name__ == "__main__":
    unittest.main()
