"""Regressions for what the eighth self-run (headless init on a history-free copy of this repo) reported."""
import json
import re
import unittest

from tests._support import PLUGIN, TempRepo, write
from stackfoundry.change_targets import classify, stackfoundry_files

DATA = {"schemaVersion": 1, "targets": [{"name": "cli", "paths": ["src/**"]}],
        "fullRunTriggers": [".github/workflows/**", ".githooks/pre-commit"]}


class ChangeTargetsTests(unittest.TestCase):
    def test_a_full_run_trigger_is_reported_as_one_not_as_unmapped(self):
        r = classify(DATA, [".github/workflows/ci.yml", ".githooks/pre-commit", "odd.txt"])
        self.assertEqual(r["fullRun"], [".github/workflows/ci.yml", ".githooks/pre-commit"])
        self.assertEqual(r["unmapped"], ["odd.txt"])

    def test_a_target_path_still_wins_over_a_full_run_trigger(self):
        data = {**DATA, "fullRunTriggers": ["src/shared.py"]}
        r = classify(data, ["src/shared.py"])
        self.assertEqual(r["targets"]["cli"]["files"], ["src/shared.py"])
        self.assertEqual(r["fullRun"], [])

    def test_files_stackfoundry_generated_are_its_own_not_unmapped(self):
        manifest = {"schemaVersion": 1, "pluginVersion": "0.2.0", "files": {
            ".github/instructions/web.instructions.md": {"template": "research", "sha256": "x"},
            ".agents/rules/web.md": {"template": "research", "sha256": "x"},
            ".agents/skills/python-cli-code-writer/SKILL.md": {"template": "t", "sha256": "x"}}}
        with TempRepo({".stackfoundry/manifest.lock.json": json.dumps(manifest)}) as root:
            own = stackfoundry_files(root)
        files = sorted(manifest["files"]) + [".agents/skills/team-skill/SKILL.md"]
        r = classify(DATA, files, own)
        self.assertEqual(r["stackfoundry"], sorted(manifest["files"]))
        self.assertEqual(r["unmapped"], [".agents/skills/team-skill/SKILL.md"])  # the team's own stays judged

    def test_no_manifest_means_no_own_files(self):
        with TempRepo() as root:
            self.assertEqual(stackfoundry_files(root), set())


class DocsRootTests(unittest.TestCase):
    """config.json's docsRoot wins over a legacy targets.json one; every skill and agent reads it from there."""

    def test_no_skill_or_agent_takes_docs_root_from_targets_json(self):
        # The phrasings the skills used, each read with wrapped lines joined.
        stale = re.compile(r"targets\.json` (?:→|for|:) `docsRoot`|`docsRoot` (?:and `timezone` )?from "
                           r"`(?:\.stackfoundry/)?targets\.json`|`<docsRoot>` from `(?:\.stackfoundry/)?targets\.json`")
        offenders = []
        for path in sorted(list(PLUGIN.glob("skills/*/SKILL.md")) + list(PLUGIN.glob("agents/*.md"))):
            text = " ".join(path.read_text(encoding="utf-8").split())
            if stale.search(text):
                offenders.append(path.relative_to(PLUGIN).as_posix())
        self.assertEqual(offenders, [])

    def test_the_surveyor_drafts_docs_root_for_config_json(self):
        text = (PLUGIN / "agents/surveyor.md").read_text(encoding="utf-8")
        report = text[text.index("## Report"):]
        self.assertIn('"config": {"schemaVersion": 1, "docsRoot": "docs"}', report)
        self.assertNotIn('"targets": {"schemaVersion": 1, "docsRoot"', report)


class SurveyorAndInitTests(unittest.TestCase):
    def test_the_surveyor_never_drafts_a_paid_check_as_a_test(self):
        text = (PLUGIN / "agents/surveyor.md").read_text(encoding="utf-8")
        self.assertIn("A check that costs money or needs a person", text)
        self.assertIn("never a `tests` or `gate` entry", text)

    def test_init_learns_the_outputs_before_its_one_confirmation(self):
        text = (PLUGIN / "skills/init/SKILL.md").read_text(encoding="utf-8")
        step4 = text[text.index("## 4. Write"):text.index("| File | From |")]
        self.assertIn("Before anything is written, `stackfoundry outputs --clients", step4)
        self.assertNotIn("(after writing it)", step4)


if __name__ == "__main__":
    unittest.main()
