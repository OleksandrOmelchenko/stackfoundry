"""Portability across assistants: the neutral profile folder, the launchers, and the shared preamble."""
import json
import unittest

from tests._support import HAS_GIT, PLUGIN, TempRepo, run_cli


class ProfileFolderTests(unittest.TestCase):
    @unittest.skipUnless(HAS_GIT, "git not available")
    def test_a_profile_in_the_old_folder_points_to_upgrade(self):
        data = {"schemaVersion": 1, "targets": [{"name": "web", "paths": ["web/**"]}]}
        with TempRepo({".claude/stackfoundry/targets.json": json.dumps(data), "web/a.ts": "x\n"}, git=True) as root:
            proc = run_cli(["change-targets", "--files", "web/a.ts"], cwd=root)
        self.assertEqual(proc.returncode, 2, proc.stdout)
        self.assertIn("/stackfoundry:upgrade", proc.stderr)
        self.assertIn(".stackfoundry/", proc.stderr)

    @unittest.skipUnless(HAS_GIT, "git not available")
    def test_the_new_folder_is_read(self):
        data = {"schemaVersion": 1, "targets": [{"name": "web", "paths": ["web/**"]}]}
        with TempRepo({".stackfoundry/targets.json": json.dumps(data), "web/a.ts": "x\n"}, git=True) as root:
            proc = run_cli(["change-targets", "--files", "web/a.ts", "--json"], cwd=root)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("web", proc.stdout)


class ConfigTests(unittest.TestCase):
    SCHEMA = PLUGIN / "reference" / "schemas" / "config.schema.json"

    def test_defaults_without_a_file(self):
        with TempRepo({".stackfoundry/targets.json": "{}"}) as root:
            proc = run_cli(["config", "--root", str(root)])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout), {"schemaVersion": 1, "clients": ["claude-code"], "docsRoot": "docs",
                                                   "researchRefreshDays": 90, "defaultEffort": "standard"})

    def test_one_key_prints_its_plain_value_and_file_values_win(self):
        files = {".stackfoundry/config.json": json.dumps({"schemaVersion": 1, "defaultEffort": "thorough",
                                                          "clients": ["codex", "cursor"]})}
        with TempRepo(files) as root:
            effort = run_cli(["config", "defaultEffort", "--root", str(root)])
            clients = run_cli(["config", "clients", "--root", str(root)])
        self.assertEqual(effort.stdout.strip(), "thorough")
        self.assertEqual(json.loads(clients.stdout), ["codex", "cursor"])

    def test_invalid_values_and_unknown_keys_are_errors(self):
        for bad in ({"clients": ["vim"]}, {"clients": []}, {"researchRefreshDays": 3}, {"docsRoot": "../x"},
                    {"defaultEffort": "max"}, {"colour": "red"}):
            with self.subTest(bad=bad), TempRepo({".stackfoundry/config.json": json.dumps(bad)}) as root:
                proc = run_cli(["config", "--root", str(root)])
                self.assertEqual(proc.returncode, 2, proc.stdout)

    def test_the_schema_and_the_cli_agree_on_keys_defaults_and_clients(self):
        from stackfoundry import config
        schema = json.loads(self.SCHEMA.read_text(encoding="utf-8"))["properties"]
        self.assertEqual(set(schema), set(config.DEFAULTS))
        for key, value in config.DEFAULTS.items():
            if key != "schemaVersion":
                self.assertEqual(schema[key]["default"], value, key)
        self.assertEqual(tuple(schema["clients"]["items"]["enum"]), config.CLIENTS)
        self.assertEqual(tuple(schema["defaultEffort"]["enum"]), config.EFFORTS)


if __name__ == "__main__":
    unittest.main()
