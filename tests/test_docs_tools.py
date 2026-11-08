"""volatile-facts, tracker and backlog."""
import json
import unittest

from tests._support import HAS_GIT, TempRepo, run_cli
from stackfoundry.tracker import check
from stackfoundry.volatile import scan_text

BUG_REPORT = """# api deep sweep

**Open:** 🔴 B1 · 🟡 B3

### B1 🔴 ⬜ OPEN — race in order totals
### B2 🟡 ✅ FIXED — stale cache
### B3 🟡 ⚠️ PARTIAL — missing guard
### B4 🔵 🚫 WONT-FIX — style
"""

TEST_DESIGN = """# api orders design

**Open:** TD-1, TD-3 · **Questions:** Q1

| ID | Behaviour | Technique | Layer | Oracle | Status |
|---|---|---|---|---|---|
| TD-1 | a | boundary | unit | spec §2 | ⬜ |
| TD-2 | b | state | integration | spec §3 | ✅ |
| TD-3 | c | pairwise | unit | ❓ | ❓ |
| TD-4 | d | example | unit | spec §4 | 🚫 |
"""


class VolatileTests(unittest.TestCase):
    def test_finds_each_kind_and_skips_fences(self):
        text = ("See src/Api/Orders.cs:42 for it.\nAs of 2026-01-02 it holds.\nFixed in a1b2c3d.\n"
                "The suite takes 40 seconds.\nThere are 120 tests.\n```\nsrc/x.cs:9\n```\n")
        kinds = [h["kind"] for h in scan_text(text, include_counts=False)]
        self.assertEqual(kinds, ["file:line", "date", "sha", "duration"])
        self.assertIn("count", [h["kind"] for h in scan_text(text, include_counts=True)])

    def test_plain_words_and_versions_are_not_shas(self):
        self.assertEqual(scan_text("Use decade and facade; Node 24.1.0; deadbeef.", False), [])


class TrackerTests(unittest.TestCase):
    def test_well_formed_trackers_pass(self):
        self.assertEqual(check(BUG_REPORT), [])
        self.assertEqual(check(TEST_DESIGN), [])

    def test_banner_drift_and_tallies_are_reported(self):
        drift = BUG_REPORT.replace("**Open:** 🔴 B1 · 🟡 B3", "**Open:** 🔴 B1, B2 · 2 open")
        problems = " | ".join(check(drift))
        self.assertIn("tally", problems)
        self.assertIn("B2", problems)       # listed but fixed
        self.assertIn("B3", problems)       # open but missing

    def test_wrong_severity_bucket(self):
        moved = BUG_REPORT.replace("**Open:** 🔴 B1 · 🟡 B3", "**Open:** 🔴 B1, B3")
        self.assertTrue(any("wrong severity" in p for p in check(moved)))

    def test_test_design_open_rows(self):
        stale = TEST_DESIGN.replace("TD-1, TD-3", "TD-1")
        self.assertTrue(any("TD-3" in p for p in check(stale)))


@unittest.skipUnless(HAS_GIT, "git not installed")
class BacklogTests(unittest.TestCase):
    def test_collects_every_section_and_lints_categories(self):
        files = {
            "docs/plans/README.md": "# index",
            "docs/plans/_template.md": "# template",
            "docs/plans/wishlist.md": "# Wishlist\n\n**Category:** web\n",
            "docs/plans/no-cat.md": "# No category\n\nnothing\n",
            "docs/specifications/search.md": "# Search\n\n**Category:** api\n\n## Follow-ups\n- facet counts\n- none of the filters persist\n\n## Other\n- not a follow-up\n",
            "docs/specifications/done.md": "# Done\n\n**Category:** api\n\n## Follow-ups\n- None.\n",
            "docs/bug-reports/2026-01-01-api.md": BUG_REPORT,
            "docs/test-designs/2026-01-01-api.md": TEST_DESIGN,
            "src/a.py": "x = 1  # TODO: tidy\n",
        }
        with TempRepo(files, git=True) as root:
            proc = run_cli(["backlog", "--json", "--root", str(root)])
            self.assertEqual(proc.returncode, 1, "a plan without a category is lint")
            r = json.loads(proc.stdout)
        self.assertEqual([p["title"] for p in r["plans"]], ["No category", "Wishlist"])
        self.assertEqual([f["text"] for f in r["followUps"]], ["facet counts", "none of the filters persist"])
        self.assertEqual({b["id"] for b in r["bugs"]}, {"B1", "B3"})
        self.assertEqual({t["id"] for t in r["testDesigns"]}, {"TD-1", "TD-3"})
        self.assertEqual(len(r["todos"]), 1)
        self.assertTrue(any("no-cat.md" in x for x in r["lint"]))


if __name__ == "__main__":
    unittest.main()
