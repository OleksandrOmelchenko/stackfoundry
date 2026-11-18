"""Gaps a consuming repo hit while handing its own tooling to the plugin (P1-P7), one class per gap."""
from __future__ import annotations

import json
import unittest

from tests._support import TempRepo, run_cli, write

from stackfoundry import tracker

WIDE_IDS = ("SUMUP-1", "CAT-X1", "BN-C8", "I-MCP3", "A11Y-TARGET-SIZE", "EL7/N26")


def _report(open_ids: str, findings: list[tuple[str, str, str]]) -> str:
    blocks = "\n\n".join(f"### {i} {sev} {marker} — title of {i}\n- **Where:** `x.py:1`" for i, sev, marker in findings)
    return f"# area: sweep (2026-01-01)\n\n**Open:** {open_ids}\n\n## Findings\n\n{blocks}\n"


class TrackerIdTests(unittest.TestCase):
    """P3: hyphenated and slash finding ids parse; old ids parse exactly as before."""

    WIDE = _report("🔴 SUMUP-1, CAT-X1 · 🟡 BN-C8, I-MCP3 · 🔵 A11Y-TARGET-SIZE, EL7/N26",
                   [("SUMUP-1", "🔴", "⬜"), ("CAT-X1", "🔴", "⚠️"), ("BN-C8", "🟡", "⬜"), ("I-MCP3", "🟡", "⬜"),
                    ("A11Y-TARGET-SIZE", "🔵", "⬜"), ("EL7/N26", "🔵", "⬜"), ("MB-12", "🟡", "✅")])

    def test_wide_ids_parse_and_check(self):
        items = tracker.parse(self.WIDE)["items"]
        self.assertEqual([i["id"] for i in items], [*WIDE_IDS, "MB-12"])
        self.assertEqual(tracker.check(self.WIDE), [])

    def test_wide_ids_misplaced_in_banner_are_reported(self):
        text = self.WIDE.replace("🔴 SUMUP-1, CAT-X1 · 🟡 BN-C8", "🔴 CAT-X1 · 🟡 SUMUP-1, BN-C8")
        self.assertIn("SUMUP-1 is listed under the wrong severity in the banner", tracker.check(text))
        text = self.WIDE.replace("EL7/N26", "EL7/N27", 1)
        self.assertTrue(any("not open" in p and "N27" in p for p in tracker.check(text)), tracker.check(text))

    def test_backlog_lists_wide_ids(self):
        with TempRepo({"docs/bug-reports/2026-01-01-area-sweep.md": self.WIDE}) as root:
            r = run_cli(["backlog", "--section", "bugs", "--json", "--root", str(root)])
            self.assertEqual(r.returncode, 0, r.stderr)
            ids = [b["id"] for b in json.loads(r.stdout)["bugs"]]
        self.assertEqual(ids, list(WIDE_IDS))

    def test_tracker_check_cli_passes(self):
        with TempRepo({"r.md": self.WIDE}) as root:
            r = run_cli(["tracker", "check", str(root / "r.md")])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_old_ids_parse_as_before(self):
        text = _report("🔴 B1 · 🟡 B3/B4, AB12", [("B1", "🔴", "⬜"), ("B2", "🔴", "✅"), ("B3", "🟡", "⬜"),
                                                ("B4", "🟡", "⚠️"), ("AB12", "🟡", "⬜")])
        doc = tracker.parse(text)
        self.assertEqual([(i["id"], i["open"]) for i in doc["items"]],
                         [("B1", True), ("B2", False), ("B3", True), ("B4", True), ("AB12", True)])
        self.assertEqual(tracker.check(text), [])
        # `B1-B3` in a banner still names B1 and B3, not one id
        self.assertEqual(tracker.banner_ids("B1-B3", {"B1", "B3"}), ["B1", "B3"])

    def test_words_without_a_digit_are_never_ids(self):
        self.assertEqual(tracker.banner_ids("OPEN, PARTIAL · FIXED and UTF-8 then B2", {"B2"}), ["B2"])
        self.assertEqual(tracker.parse("### OPEN 🔴 ⬜ OPEN — not a finding\n")["items"], [])

    def test_test_design_rows_keep_td_ids(self):
        text = "**Open:** TD-1 · **Questions:** Q1\n\n| ID | B | T | L | O | S |\n|---|---|---|---|---|---|\n" \
               "| TD-1 | a | b | c | d | ⬜ |\n| TD-2 | a | b | c | d | ✅ |\n"
        self.assertEqual([r["id"] for r in tracker.parse(text)["items"]], ["TD-1", "TD-2"])
        self.assertEqual(tracker.check(text), [])


def _pack(**over) -> dict:
    pack = {"schemaVersion": 1, "id": "capability-i18n", "layer": "capability", "title": "i18n",
            "researchedAt": "2026-01-01", "versions": [], "targets": ["web"],
            "sources": {"d": {"url": "https://example.org/docs", "accessed": "2026-01-01", "title": "Docs"}},
            "rules": [{"rule": "Keep keys flat.", "why": "Lookups stay cheap.", "where": ["web/i18n"],
                       "sources": ["d"]}],
            "rulebookPaths": ["web/**/*.ts"]}
    pack.update(over)
    return pack


class PackGlobTests(unittest.TestCase):
    """P4: a brace glob is refused with a hint to split it; the description quoting is a fix and stays."""

    def test_brace_glob_is_refused_with_a_split_hint(self):
        from stackfoundry import pack
        errors, _ = pack.check(_pack(rulebookPaths=["web/**/*.{ts,html}"]))
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("split `{a,b}` into one glob per extension", errors[0])

    def test_split_globs_pass(self):
        from stackfoundry import pack
        errors, _ = pack.check(_pack(rulebookPaths=["web/**/*.ts", "web/**/*.html"]))
        self.assertEqual(errors, [])

    def test_brace_glob_breaks_the_comma_joined_formats(self):
        # Why braces stay refused: the same glob through render-rule for Cursor becomes two broken globs.
        from stackfoundry import clients
        text = "---\ndescription: x\npaths:\n  - \"web/**/*.{ts,html}\"\n---\n\n# x\n"
        globs = next(line for line in clients.render_rule(text, "cursor").splitlines() if line.startswith("globs:"))
        self.assertEqual(globs[len("globs: "):].split(","), ["web/**/*.{ts", "html}"])

    def test_description_with_colon_space_is_quoted_and_reads_back_whole(self):
        from stackfoundry import pack
        from stackfoundry.frontmatter import split
        rendered = pack.render(_pack(id="capability-bicep", title="Bicep: Azure infrastructure"))
        fields, _, errors = split(rendered)
        self.assertEqual(errors, [])
        self.assertTrue(fields["description"].startswith("Bicep: Azure infrastructure rulebook (capability layer)."))


COMMAND_ROLES = ("test-runner", "test-writer", "test-fixer", "test-reviewer", "benchmark-writer", "benchmark-reviewer",
                 "code-verifier", "debugger", "fix-verifier", "web-fix-verifier", "bug-hunter", "change-reviewer",
                 "code-semantics-reviewer", "markup-semantics-reviewer", "security-reviewer", "performance-reviewer")


class PowerShellGrantTests(unittest.TestCase):
    """P1: roles that run a profile's gate, test, benchmark or analysis commands can run a `.ps1` command through
    `PowerShell` (inside an EnterWorktree worktree `Bash` refuses to launch pwsh)."""

    def test_command_roles_grant_powershell_and_say_when_to_use_it(self):
        import re
        from tests._support import PLUGIN
        from stackfoundry.frontmatter import split
        for role in COMMAND_ROLES:
            with self.subTest(role=role):
                fields, body, _ = split((PLUGIN / "agents" / f"{role}.md").read_text(encoding="utf-8"))
                tools = [t.strip() for t in fields["tools"].split(",")]
                self.assertIn("PowerShell", tools)
                self.assertIn("Bash", tools)
                tooling = re.search(r"^## Tooling\n(.*)", body, re.M | re.S).group(1)
                self.assertIn("`PowerShell` for a `.ps1` command when you have it", tooling)
                self.assertIn("`EnterWorktree`", tooling)

    def test_copilot_copies_carry_the_tooling_line(self):
        from tests._support import PLUGIN
        for role in COMMAND_ROLES:
            with self.subTest(role=role):
                text = (PLUGIN / "com.github.copilot" / "agents" / f"{role}.agent.md").read_text(encoding="utf-8")
                self.assertIn("`PowerShell` for a `.ps1` command when you have it", text)


def _repo_agent(name: str, tools: str) -> str:
    return (f"---\nname: {name}\ndescription: Verifies a fix in the local app. Read-only.\ntools: {tools}\n---\n\n"
            f"# {name}\n\nVerify.\n\n## Tooling\n\n- `Bash` for the gate commands.\n")


BROWSER = "Read, Bash, mcp__Claude_Browser__navigate, mcp__Claude_Browser__read_page"


class ShellWithBrowserTests(unittest.TestCase):
    """P2: a repo may exempt its own agent that holds a shell beside the local browser pane, with a reason; never
    one that holds WebFetch, WebSearch or another browser."""

    def check(self, agents: dict[str, str], config: dict | None = None):
        from stackfoundry.plumbing import check
        files = {f".claude/agents/{n}.md": _repo_agent(n, t) for n, t in agents.items()}
        if config is not None:
            files[".stackfoundry/config.json"] = json.dumps(config)
        with TempRepo(files) as root:
            report = check(root)
        return report.errors, report.warnings

    def test_local_browser_with_a_shell_is_an_error_without_an_entry(self):
        errors, _ = self.check({"web-verifier": BROWSER})
        self.assertTrue(any("web-verifier" in e and "shellWithBrowser" in e for e in errors), errors)

    def test_an_entry_with_a_reason_exempts_the_local_browser(self):
        errors, _ = self.check({"web-verifier": BROWSER}, {"shellWithBrowser": [
            {"agent": "web-verifier", "reason": "opens only the app on localhost"}]})
        self.assertEqual(errors, [])

    def test_the_same_pane_from_a_cloud_session_is_local_too(self):
        errors, _ = self.check({"web-verifier": "Read, Bash, mcp__remote-devices__Claude_Browser__navigate"},
                               {"shellWithBrowser": [{"agent": "web-verifier", "reason": "local app only"}]})
        self.assertEqual(errors, [])

    def test_web_fetch_with_a_shell_stays_an_error_even_when_listed(self):
        errors, _ = self.check({"builder": "Read, Bash, WebFetch"},
                               {"shellWithBrowser": [{"agent": "builder", "reason": "reads build docs"}]})
        self.assertTrue(any("builder" in e and "never WebFetch" in e for e in errors), errors)

    def test_listing_does_not_cover_another_browser_beside_the_pane(self):
        errors, _ = self.check({"mixed": BROWSER + ", mcp__playwright_browser__navigate"},
                               {"shellWithBrowser": [{"agent": "mixed", "reason": "local app only"}]})
        self.assertTrue(any("mixed" in e and "together with" in e for e in errors), errors)

    def test_an_entry_without_a_reason_is_a_config_error(self):
        from stackfoundry import config
        self.assertTrue(config.check({"shellWithBrowser": [{"agent": "web-verifier"}]}))
        self.assertTrue(config.check({"shellWithBrowser": [{"agent": "web-verifier", "reason": " "}]}))
        self.assertEqual(config.check({"shellWithBrowser": [{"agent": "web-verifier", "reason": "local"}]}), [])
        errors, _ = self.check({"web-verifier": BROWSER}, {"shellWithBrowser": [{"agent": "web-verifier"}]})
        self.assertTrue(any("cannot read shellWithBrowser" in e for e in errors), errors)

    def test_an_entry_for_no_agent_warns(self):
        _, warnings = self.check({}, {"shellWithBrowser": [{"agent": "ghost", "reason": "x"}]})
        self.assertTrue(any("'ghost'" in w for w in warnings), warnings)


if __name__ == "__main__":
    unittest.main()
