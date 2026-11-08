"""globs-check and mutation-check."""
import json
import unittest

from tests._support import TempRepo, run_cli
from stackfoundry.checks import mutation_summary


def report(statuses):
    return {"schemaVersion": "1", "files": {"src/a.ts": {"language": "ts", "mutants": [
        {"id": str(i), "mutatorName": "EqualityOperator", "replacement": ">=", "status": s,
         "location": {"start": {"line": 10 + i, "column": 1}, "end": {"line": 10 + i, "column": 5}}}
        for i, s in enumerate(statuses)]}}}


class MutationCheckTests(unittest.TestCase):
    def test_a_healthy_report_scores_and_lists_survivors(self):
        s = mutation_summary(report(["Killed", "Killed", "Survived", "NoCoverage", "CompileError"]))
        self.assertEqual(s["problems"], [])
        self.assertEqual(s["scoreValid"], 50.0)      # 2 detected of 4 valid
        self.assertEqual(s["scoreCovered"], 66.7)    # 2 detected of 3 covered
        self.assertEqual([x["line"] for x in s["survivors"]], [12])

    def test_zero_kills_and_starved_runners_are_not_evidence(self):
        self.assertTrue(any("zero killed" in p for p in mutation_summary(report(["Survived", "Timeout"]))["problems"]))
        starved = mutation_summary(report(["Killed", "Timeout", "Timeout"]))["problems"]
        self.assertTrue(any("timeouts" in p for p in starved))

    def test_cli_exit_code(self):
        with TempRepo({"r.json": json.dumps(report(["Survived"]))}) as root:
            self.assertEqual(run_cli(["mutation-check", str(root / "r.json")]).returncode, 1)
            (root / "r.json").write_text(json.dumps(report(["Killed"])), encoding="utf-8")
            self.assertEqual(run_cli(["mutation-check", str(root / "r.json")]).returncode, 0)


class GlobsCheckTests(unittest.TestCase):
    def test_reports_globs_that_match_nothing(self):
        rule = '---\npaths:\n  - "src/**/*.cs"\n  - "gone/**"\n---\n# Rule\n'
        with TempRepo({"src/a/B.cs": "x", ".claude/rules/csharp.md": rule}) as root:
            proc = run_cli(["globs-check", str(root / ".claude/rules"), "--root", str(root), "--json"])
            self.assertEqual(proc.returncode, 1, proc.stderr)
            by_glob = {r["glob"]: r["matches"] for r in json.loads(proc.stdout)}
        self.assertEqual(by_glob, {"src/**/*.cs": 1, "gone/**": 0})


class TodayTests(unittest.TestCase):
    def test_prints_an_iso_date_with_or_without_a_profile(self):
        import re
        with TempRepo({".claude/stackfoundry/targets.json": json.dumps({"timezone": "Europe/Madrid"})}) as root:
            proc = run_cli(["today", "--root", str(root), "--verbose"])
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertRegex(proc.stdout, r"^\d{4}-\d{2}-\d{2} \(")
        with TempRepo() as root:
            self.assertTrue(re.fullmatch(r"\d{4}-\d{2}-\d{2}\n", run_cli(["today", "--root", str(root)]).stdout))


if __name__ == "__main__":
    unittest.main()
