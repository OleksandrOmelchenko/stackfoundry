"""`stackfoundry size-check`, the plugin's listing budget and the pack size warning (context budgets per assistant)."""
import json
import unittest
from unittest import mock

from tests._support import PLUGIN, TempRepo, run_cli, targets_json, write
from stackfoundry import pack, plumbing, sizes

RULE = "---\ndescription: R\npaths:\n  - \"src/**\"\n---\n\n# R\n"


def lines(n: int, prefix: str = "x") -> str:
    return "".join(f"{prefix} {i}\n" for i in range(n))


class SizeCheckTests(unittest.TestCase):
    def setUp(self):
        self.repo = TempRepo()
        self.root = self.repo.__enter__()
        self.addCleanup(self.repo.__exit__, None, None, None)
        targets_json(self.root, {"targets": [{"name": "api", "paths": ["src/**"]}]})

    def config(self, *clients):
        write(self.root, {".stackfoundry/config.json": json.dumps({"schemaVersion": 1, "clients": list(clients)})})

    def rows(self):
        return {r["path"]: r for r in sizes.check(self.root)}

    def test_every_generated_file_is_measured_and_a_claude_md_past_its_advice_warns(self):
        self.config("claude-code")
        block = "<!-- stackfoundry:begin x -->\n" + lines(3) + "<!-- stackfoundry:end -->\n"
        write(self.root, {"CLAUDE.md": lines(250) + block, ".stackfoundry/rules/web.md": RULE,
                          ".claude/rules/web.md": RULE, ".claude/skills/web-code-writer/SKILL.md": lines(10),
                          ".stackfoundry/agents/api-hunter.md": lines(5)})
        rows = self.rows()
        self.assertEqual(sorted(rows), [".claude/rules/web.md", ".claude/skills/web-code-writer/SKILL.md",
                                        ".stackfoundry/agents/api-hunter.md", ".stackfoundry/rules/web.md", "CLAUDE.md"])
        claude = rows["CLAUDE.md"]
        self.assertEqual((claude["lines"], claude["block_lines"]), (255, 5))  # the block alone is measured too
        self.assertEqual(claude["warnings"], ["255 lines > 200 (claude-code advice)"])
        self.assertEqual(claude["errors"], [])
        self.assertEqual(run_cli(["size-check", "--root", str(self.root)]).returncode, 0)

    def test_codex_stops_reading_agents_md_past_32_kib(self):
        self.config("codex")
        write(self.root, {"AGENTS.md": "y" * (32 * 1024 + 1)})
        self.assertEqual(self.rows()["AGENTS.md"]["errors"], [f"{32 * 1024 + 1} bytes > 32768 (codex, hard limit)"])
        proc = run_cli(["size-check", "--root", str(self.root)])
        self.assertEqual(proc.returncode, 1)
        self.assertIn("error: 32769 bytes > 32768 (codex, hard limit)", proc.stdout)

    def test_a_rule_copy_and_a_skill_are_judged_by_their_own_host(self):
        self.config("claude-code", "cursor")
        long_rule = RULE + lines(600)
        write(self.root, {".stackfoundry/rules/web.md": long_rule, ".claude/rules/web.md": long_rule,
                          ".cursor/rules/web.mdc": long_rule, ".claude/skills/big/SKILL.md": lines(501)})
        rows = self.rows()
        self.assertEqual(rows[".claude/rules/web.md"]["warnings"], [])  # no cited limit for Claude Code rules
        self.assertEqual(rows[".cursor/rules/web.mdc"]["warnings"], ["607 lines > 500 (cursor advice)"])
        self.assertIn("501 lines > 500 (every assistant advice)", rows[".claude/skills/big/SKILL.md"]["warnings"])


class ListingBudgetTests(unittest.TestCase):
    def test_the_shipped_listing_is_within_its_budget(self):
        rep = plumbing.check(PLUGIN)
        self.assertEqual(rep.errors, [])
        self.assertLessEqual(rep.listing, plumbing.LISTING_CAP)

    def test_a_listing_past_the_budget_fails_verify_plumbing(self):
        rep = plumbing.check(PLUGIN)
        with mock.patch.object(plumbing, "LISTING_CAP", rep.listing - 1):
            errors = " | ".join(plumbing.check(PLUGIN).errors)
        self.assertIn(f"descriptions total {rep.listing} characters, over the listing budget", errors)


class PackSizeTests(unittest.TestCase):
    PACK = {"schemaVersion": 1, "id": "language-python", "layer": "language", "title": "Python",
            "researchedAt": "2026-11-01", "versions": [], "sources": {"s": {"url": "https://example.com",
                                                                            "accessed": "2026-11-01"}},
            "rulebookPaths": ["**/*.py"]}

    def rules(self, n):
        return [{"rule": f"Rule {i}.", "why": "Because.", "where": ["src/a.py"], "sources": ["s"]} for i in range(n)]

    def test_a_pack_that_renders_past_the_rule_advice_warns(self):
        _, warnings = pack.check({**self.PACK, "rules": self.rules(600)})
        self.assertTrue(any("past the 500 a path-scoped rule is advised" in w for w in warnings), warnings)
        _, small = pack.check({**self.PACK, "rules": self.rules(3)})
        self.assertFalse(any("path-scoped rule is advised" in w for w in small), small)


if __name__ == "__main__":
    unittest.main()
