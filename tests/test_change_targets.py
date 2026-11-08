import json
import unittest

from tests._support import HAS_GIT, TempRepo, git, run_cli, targets_json, write
from stackfoundry.change_targets import classify, specialists
from stackfoundry.select_tests import plan

DATA = {
    "schemaVersion": 1,
    "targets": [
        {"name": "api", "paths": ["src/Api/**"], "testPaths": ["tests/Api.Tests/**"], "packs": [],
         "tests": [{"name": "unit", "command": "dotnet test tests/Api.Tests", "paths": ["tests/Api.Tests/**"],
                    "covers": ["src/Api/Services/**"]}]},
        {"name": "desktop", "paths": ["src/Desktop/**"], "testPaths": ["tests/Desktop.Tests/**"],
         "tests": [{"name": "unit", "command": "dotnet test tests/Desktop.Tests"}]},
        {"name": "web", "paths": ["web/**"], "testPaths": ["web/**/*.spec.ts"],
         "tests": [{"name": "vitest", "command": "npm test --prefix web", "affectedCommand": "npx vitest related"}]},
        {"name": "web-ssr", "paths": ["web/pages/**", "web/server/**"]},
        {"name": "shared", "paths": ["src/Shared/**"], "tests": [{"name": "all", "command": "dotnet test"}]},
    ],
    "rules": [{"glob": "src/Shared/**", "targets": ["shared", "api", "desktop"]}],
    "specialists": [
        {"agent": "security-reviewer", "why": "auth code", "paths": ["src/Api/Auth/**"]},
        {"agent": "compliance-reviewer", "why": "money", "contains": ["(?i)invoice"], "scope": ["src/**"]},
    ],
    "generated": ["web/src/api-client/**"],
    "ignored": ["docs/**"],
    "fullRunTriggers": ["Directory.Packages.props"],
}


class ClassifyTests(unittest.TestCase):
    def test_first_match_order_and_shared_folders(self):
        r = classify(DATA, [
            "web/src/api-client/model.ts",      # generated beats everything
            "docs/x.md",                       # ignored
            "src/Shared/Util.cs",              # explicit rule -> three targets
            "web/pages/index.vue",             # two targets share the folder
            "web/components/a.spec.ts",        # a test file of web
            "README.md",                       # unmapped
        ])
        self.assertEqual(r["generated"], ["web/src/api-client/model.ts"])
        self.assertEqual(r["ignored"], ["docs/x.md"])
        self.assertEqual(r["unmapped"], ["README.md"])
        self.assertEqual(set(r["targets"]), {"shared", "api", "desktop", "web", "web-ssr"})
        self.assertEqual(r["targets"]["web-ssr"]["files"], ["web/pages/index.vue"])
        self.assertIn("web/components/a.spec.ts", r["targets"]["web"]["testFiles"])

    def test_tests_only_flag(self):
        r = classify(DATA, ["tests/Api.Tests/A.cs"])
        self.assertTrue(r["targets"]["api"]["testsOnly"])
        r = classify(DATA, ["tests/Api.Tests/A.cs", "src/Api/B.cs"])
        self.assertFalse(r["targets"]["api"]["testsOnly"])

    def test_specialists_by_path_and_by_content(self):
        with TempRepo({"src/Api/Auth/Login.cs": "class Login {}", "src/Api/Billing.cs": "// Invoice totals",
                       "src/Api/Other.cs": "class Other {}"}) as root:
            specs = {s["agent"]: s["files"] for s in specialists(
                DATA, root, ["src/Api/Auth/Login.cs", "src/Api/Billing.cs", "src/Api/Other.cs"])}
        self.assertEqual(specs["security-reviewer"], ["src/Api/Auth/Login.cs"])
        self.assertEqual(specs["compliance-reviewer"], ["src/Api/Billing.cs"])


class SelectTestsTests(unittest.TestCase):
    def test_affected_selection_and_uncovered(self):
        p = plan(DATA, ["src/Api/Services/Orders.cs", "src/Api/Controllers/X.cs", "web/a.ts"])
        self.assertEqual(p["mode"], "affected")
        runs = {(r["target"], r["test"]): r["command"] for r in p["runs"]}
        self.assertEqual(runs[("api", "unit")], "dotnet test tests/Api.Tests")
        self.assertEqual(runs[("web", "vitest")], "npx vitest related")
        # The api tests cover Services only, so the controller change is reported, not hidden.
        self.assertEqual(p["uncovered"], ["src/Api/Controllers/X.cs"])

    def test_a_trigger_forces_every_target_to_run_its_full_command(self):
        p = plan(DATA, ["Directory.Packages.props"])
        self.assertEqual(p["mode"], "full")
        self.assertIn(("web", "npm test --prefix web"), {(r["target"], r["command"]) for r in p["runs"]})
        self.assertIn("desktop", {r["target"] for r in p["runs"]})


@unittest.skipUnless(HAS_GIT, "git not installed")
class CliTests(unittest.TestCase):
    def test_uncommitted_and_branch_modes(self):
        with TempRepo({"src/Api/A.cs": "a", "web/a.ts": "a"}, git=True) as root:
            targets_json(root, DATA)
            git(root, "add", "-A")
            git(root, "commit", "-q", "-m", "profile")
            git(root, "checkout", "-q", "-b", "feature")
            write(root, {"src/Api/A.cs": "changed"})
            git(root, "commit", "-q", "-am", "change")
            write(root, {"web/b.ts": "untracked"})

            proc = run_cli(["change-targets", "--json", "--root", str(root)])
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(set(json.loads(proc.stdout)["targets"]), {"web"})

            proc = run_cli(["change-targets", "--json", "--root", str(root), "--base", "main"])
            self.assertEqual(set(json.loads(proc.stdout)["targets"]), {"api", "web"})

            proc = run_cli(["select-tests", "--json", "--root", str(root), "--base", "main"])
            self.assertEqual(proc.returncode, 0, proc.stderr)
            p = json.loads(proc.stdout)
            # The api tests declare they cover src/Api/Services/** only, so src/Api/A.cs is not silently
            # "tested": it is reported as Uncovered (the select_tests contract).
            self.assertEqual(p["uncovered"], ["src/Api/A.cs"])
            self.assertEqual({r["target"] for r in p["runs"]}, {"web"})

    def test_missing_profile_is_a_clear_error(self):
        with TempRepo({"a.txt": "x"}, git=True) as root:
            proc = run_cli(["change-targets", "--root", str(root)])
            self.assertEqual(proc.returncode, 2)
            self.assertIn("/stackfoundry:init", proc.stderr)


if __name__ == "__main__":
    unittest.main()
