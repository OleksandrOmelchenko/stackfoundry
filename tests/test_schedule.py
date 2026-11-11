"""`stackfoundry schedule`: the permission rules of scheduled, unattended runs: minimal, owned, checked."""
import json
import unittest

from tests._support import TempRepo, run_cli, targets_json, write
from stackfoundry import pack, schedule
from stackfoundry.cited import url_host

PACK = {"schemaVersion": 1, "id": "tooling-x", "layer": "tooling", "title": "X", "researchedAt": "2026-11-01",
        "versions": [], "rulebookPaths": ["src/**"],
        "sources": {"docs": {"url": "https://docs.x.dev/guide", "accessed": "2026-11-01"},
                    "wiki": {"url": "https://en.wikipedia.org/wiki/X", "accessed": "2026-11-01"},
                    "shop": {"url": "https://kobzar.es/", "accessed": "2026-11-01"}},
        "rules": [{"rule": "R.", "why": "W.", "where": ["src/a"], "sources": ["docs", "wiki", "shop"]}],
        "upgrade": {"releaseNotes": ["https://github.com/x/x/releases"],
                    "migrationGuides": ["https://docs.x.dev/migrate"]}}


class RulesTests(unittest.TestCase):
    def setUp(self):
        self.repo = TempRepo()
        self.root = self.repo.__enter__()
        self.addCleanup(self.repo.__exit__, None, None, None)
        targets_json(self.root, {"targets": [{"name": "api", "paths": ["src/**"], "tests": [
            {"name": "unit", "command": "pytest -q", "shuffle": "pytest -q -p random"}]}]})
        write(self.root, {".stackfoundry/config.json": json.dumps({"schemaVersion": 1, "docsRoot": "notes"}),
                          ".stackfoundry/packs/tooling-x/pack.json": json.dumps(PACK),
                          ".stackfoundry/ecosystems.json": json.dumps({"schemaVersion": 1, "ecosystems": [
                              {"id": "npm", "discover": ["npm outdated --json"]},
                              {"id": "formats", "kind": "formats", "discover": ["check-formats --report-only"]}]})})

    def rules(self, skill):
        return [r["rule"] for r in schedule.rules(self.root, skill)]

    def test_the_web_is_only_release_notes_migration_guides_and_github(self):
        web = [r for r in self.rules("tech-radar") if r.startswith("WebFetch")]
        self.assertEqual(web, ["WebFetch(domain:docs.x.dev)", "WebFetch(domain:github.com)",
                               "WebFetch(domain:raw.githubusercontent.com)"])  # never wikipedia or the shop
        self.assertIn("WebSearch", self.rules("tech-radar"))

    def test_each_skill_writes_only_its_report_folder_under_the_docs_root(self):
        self.assertEqual(self.rules("check-updates")[0], "Edit(notes/dependency-reports/**)")
        self.assertEqual(self.rules("flaky-watch")[0], "Edit(notes/reports/**)")

    def test_commands_come_from_the_profile_and_a_skill_pass_is_no_command(self):
        updates = self.rules("check-updates")
        self.assertIn("Bash(npm outdated --json *)", updates)
        self.assertFalse(any("check-formats" in r for r in updates))
        self.assertIn("Bash(pytest -q -p random *)", self.rules("flaky-watch"))
        self.assertEqual([r for r in self.rules("whats-next") if r.startswith(("WebFetch", "WebSearch"))], [])

    def test_every_rule_has_a_reason_and_the_cli_prints_them(self):
        for skill in schedule.SKILLS:
            for r in schedule.rules(self.root, skill):
                self.assertTrue(r["reason"], (skill, r))
        out = run_cli(["schedule", "rules", "tech-radar", "--root", str(self.root)]).stdout
        self.assertIn("WebFetch(domain:docs.x.dev)    # release notes or migration guides of tooling-x", out)


class HostTests(unittest.TestCase):
    def test_a_url_must_name_a_real_host(self):
        for good in ("https://docs.x.dev/a", "http://example.com", "https://raw.githubusercontent.com/a/b"):
            self.assertIsNotNone(url_host(good), good)
        for bad in ("https://api.<host>/x", "https://internal-host:8080/", "https://{host}/a", "ftp://x.dev",
                    "https://localhost/", "not a url"):
            self.assertIsNone(url_host(bad), bad)

    def test_pack_check_rejects_a_placeholder_host_in_sources_and_upgrade(self):
        bad = json.loads(json.dumps(PACK))
        bad["sources"]["docs"]["url"] = "https://api.<host>/guide"
        bad["upgrade"]["releaseNotes"] = ["https://internal-host:8080/notes"]
        errors, _ = pack.check(bad)
        self.assertTrue(any("source [docs]" in e and "no real host" in e for e in errors), errors)
        self.assertTrue(any(e.startswith("upgrade.releaseNotes[0]") for e in errors), errors)
        self.assertEqual(pack.check(PACK)[0], [])


if __name__ == "__main__":
    unittest.main()
