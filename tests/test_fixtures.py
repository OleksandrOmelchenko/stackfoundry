"""The eval fixtures survey to the stacks their EXPECTED.md promises, and the scaffold hides the answer key."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests._support import HAS_GIT, ROOT
from stackfoundry.survey import survey

FIXTURES = ROOT / "fixtures"


def stacks(result):
    return {u["manifest"]: {h["tech"] for h in u["hints"]} for u in result["units"]}


class FixtureSurveyTests(unittest.TestCase):
    def test_dotnet_web_and_wpf_is_two_app_models_on_one_language(self):
        s = stacks(survey(FIXTURES / "dotnet-web-and-wpf"))
        api, desktop = s["src/Api/Api.csproj"], s["src/Desktop/Desktop.csproj"]
        self.assertTrue({"csharp", "aspnet-core"} <= api)
        self.assertTrue({"csharp", "wpf", "mvvm-toolkit"} <= desktop)
        self.assertNotIn("wpf", api)
        self.assertNotIn("aspnet-core", desktop)
        self.assertIn("xunit", s["tests/Api.Tests/Api.Tests.csproj"])

    def test_vue_spa(self):
        web = stacks(survey(FIXTURES / "vue-spa"))["package.json"]
        self.assertTrue({"typescript", "vue-spa", "vitest", "vite"} <= web)

    def test_python_fastapi(self):
        api = stacks(survey(FIXTURES / "python-fastapi"))["pyproject.toml"]
        self.assertTrue({"python", "fastapi", "pydantic", "pytest"} <= api)


class FixtureProfileTests(unittest.TestCase):
    def test_every_profile_overlay_passes_the_profile_checks(self):
        import json
        from stackfoundry.profile import check_targets

        overlays = sorted(FIXTURES.glob("*.profile"))
        self.assertTrue(overlays)
        for overlay in overlays:
            with self.subTest(overlay=overlay.name):
                data = json.loads((overlay / ".claude/stackfoundry/targets.json").read_text(encoding="utf-8"))
                self.assertEqual(check_targets(data), [])
                for target in data["targets"]:
                    self.assertTrue((overlay / target["profile"]).is_file(), target["profile"])


@unittest.skipUnless(HAS_GIT and shutil.which("sh"), "needs git and sh")
class ScaffoldTests(unittest.TestCase):
    def test_scaffold_copies_the_fixture_without_its_answer_key_and_commits(self):
        with tempfile.TemporaryDirectory() as ws:
            script = f'SCAFFOLD_LIB="{(FIXTURES / "scaffold-lib.sh").as_posix()}"; . "$SCAFFOLD_LIB"; scaffold vue-spa'
            proc = subprocess.run(["sh", "-c", script], cwd=ws, capture_output=True, text=True, encoding="utf-8",
                                  env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1"})
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue((Path(ws) / "src/components/CartBadge.vue").is_file())
            self.assertFalse((Path(ws) / "EXPECTED.md").exists())
            log = subprocess.run(["git", "log", "--oneline"], cwd=ws, capture_output=True, text=True, encoding="utf-8").stdout
            self.assertIn("fixture: vue-spa", log)


if __name__ == "__main__":
    unittest.main()
