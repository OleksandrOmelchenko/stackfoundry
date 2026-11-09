"""Regressions for what the fifth self-run (headless init on a clone of this repo) found."""
import json
import unittest

from tests._support import TempRepo, run_cli, targets_json, write
from stackfoundry import clients, rulebooks
from stackfoundry.frontmatter import split
from stackfoundry.survey import parse_package_json, survey
from stackfoundry.volatile import scan

TARGETS = {"docsRoot": "docs", "targets": [
    {"name": "cli", "paths": ["src/**"], "testPaths": ["tests/**", "tests/test_cli.py"], "tests": [{"command": "t"}],
     "packs": ["language-python", "tooling-unittest"]},
    {"name": "bench", "paths": ["bench/**"], "packs": ["tooling-pyperf"], "benchmarks": {"kind": "micro"}},
]}
ECOSYSTEMS = {"schemaVersion": 1, "deferredFile": "docs/plans/later.md", "ecosystems": [
    {"id": "actions", "kind": "ci", "pins": [{"file": ".github/workflows/*.yml"}, {"file": ".github/workflows/ci.yml"}],
     "discover": [], "gateTargets": ["cli"]},
    {"id": "pip", "kind": "packages", "pins": [{"file": "requirements.txt"}], "lockFiles": ["requirements.lock"],
     "discover": [], "gateTargets": ["cli"]},
]}


class RenderRulebookTests(unittest.TestCase):
    def setUp(self):
        self.repo = TempRepo()
        self.root = self.repo.__enter__()
        self.addCleanup(self.repo.__exit__, None, None, None)
        targets_json(self.root, TARGETS)
        write(self.root, {".stackfoundry/ecosystems.json": json.dumps(ECOSYSTEMS),
                          ".stackfoundry/config.json": json.dumps({"schemaVersion": 1, "docsRoot": "handbook"})})

    def paths(self, name):
        out, text = rulebooks.render(self.root, name)
        fields, _, errors = split(text)
        self.assertEqual(errors, [])
        return out, fields["paths"], text

    def test_testing_lists_test_paths_without_covered_globs_and_the_docs_root(self):
        out, paths, text = self.paths("testing")
        self.assertEqual(out, ".stackfoundry/rules/testing.md")
        self.assertEqual(paths, ["tests/**", "handbook/test-designs/**"])  # tests/test_cli.py is under tests/**
        self.assertIn("[tooling-unittest](tooling-unittest.md)", text)
        self.assertNotIn("{{", text)

    def test_dependency_bumps_lists_pins_and_lock_files(self):
        _, paths, text = self.paths("dependency-bumps")
        self.assertEqual(paths, [".github/workflows/*.yml", "requirements.txt", "requirements.lock"])
        self.assertIn("docs/plans/later.md", text)

    def test_benchmarking_needs_a_harness(self):
        _, paths, _ = self.paths("benchmarking")
        self.assertEqual(paths, ["bench/**", "handbook/performance-reports/*-benchmarks.md"])
        targets_json(self.root, {"targets": [TARGETS["targets"][0]]})
        proc = run_cli(["render-rulebook", "benchmarking", "--root", str(self.root)])
        self.assertEqual(proc.returncode, 2)
        self.assertIn("no target has a benchmarks harness", proc.stderr)

    def test_write_puts_the_canonical_rulebook_in_place(self):
        proc = run_cli(["render-rulebook", "documentation", "--write", "--root", str(self.root)])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        text = (self.root / ".stackfoundry/rules/documentation.md").read_text(encoding="utf-8")
        self.assertIn('  - "handbook/**"', text)

    def test_every_shipped_rulebook_template_renders(self):
        for name in rulebooks.NAMES:
            with self.subTest(name=name):
                self.paths(name)


class RenderRuleQuotingTests(unittest.TestCase):
    def test_a_description_yaml_would_cut_is_quoted_and_a_plain_one_is_kept(self):
        risky = "---\ndescription: Rules: always cite # sources\npaths:\n  - \"src/**\"\n---\n# Body\n"
        plain = "---\ndescription: Plain words — no traps here.\npaths:\n  - \"src/**\"\n---\n# Body\n"
        for client in ("claude-code", "cursor"):
            with self.subTest(client=client):
                fields, _, _ = split(clients.render_rule(risky, client))
                self.assertEqual(fields["description"], "Rules: always cite # sources")
                self.assertEqual(clients.render_rule(plain, "claude-code"), plain)


class SurveyTests(unittest.TestCase):
    def test_a_package_json_that_is_not_an_object_is_reported_not_a_crash(self):
        deps, facts = parse_package_json("[1, 2]")
        self.assertEqual(deps, [])
        self.assertIn("not an object", facts["error"])

    def test_extensions_and_materialized_agents_are_listed(self):
        files = {".stackfoundry/extensions/skills/bug-hunt.md": "x", ".stackfoundry/extensions/agents/hunter.md": "x",
                 ".stackfoundry/extensions/.base/index.json": "{}", ".stackfoundry/agents/api-bug-hunter.md": "x",
                 "src/app.py": "x"}
        with TempRepo(files, git=True) as root:
            claude = survey(root)["claude"]
        self.assertEqual(claude["extensions"], [".stackfoundry/extensions/agents/hunter.md",
                                                ".stackfoundry/extensions/skills/bug-hunt.md"])
        self.assertEqual(claude["materializedAgents"], [".stackfoundry/agents/api-bug-hunter.md"])

    def test_absurdly_nested_json_is_could_not_run_not_a_traceback(self):
        with TempRepo() as root:
            targets_json(root, {"targets": [{"name": "a", "paths": ["**"]}]})
            write(root, {".stackfoundry/guards.json": "[" * 100000 + "]" * 100000})
            proc = run_cli(["guard", "--check", "--root", str(root)])
        self.assertNotIn("Traceback", proc.stderr)


class VolatileExcludeTests(unittest.TestCase):
    def test_an_exclude_matches_whatever_folder_was_scanned(self):
        files = {"repo/.stackfoundry/rules/language-python.md": "See src/app.py:42 for it.\n",
                 "repo/.stackfoundry/rules/testing.md": "See src/app.py:42 for it.\n"}
        with TempRepo(files) as root:
            hits = scan(root / "repo", False, ["rules/language-*.md"])
        self.assertEqual({h["file"].rsplit("/", 1)[-1] for h in hits}, {"testing.md"})


if __name__ == "__main__":
    unittest.main()
