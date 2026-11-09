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


class ClientOutputsTests(unittest.TestCase):
    RULE = "---\ndescription: Web rulebook.\npaths:\n  - \"web/**/*.ts\"\n  - \"web/**/*.vue\"\n---\n\n# Web\n\n- **Rule.** Why.\n"
    AGENT = ("---\nname: web-bug-hunter\ndescription: Hunts bugs in web. Read-only.\ntools: Read, Grep, Bash, WebSearch\n"
             "---\n\n# Web bug hunter\n\nBody with ''' quotes.\n")

    def test_no_assistant_gets_a_copy_another_one_already_reads_for_it(self):
        from stackfoundry.clients import outputs
        claude_only = outputs(["claude-code"])
        self.assertEqual([r["folder"] for r in claude_only["rules"]], [".claude/rules"])
        self.assertEqual(claude_only["skills"], [".claude/skills"])
        everyone = outputs(["claude-code", "codex", "copilot", "cursor", "gemini"])
        self.assertEqual(everyone["instructions"], ["AGENTS.md", "CLAUDE.md", "GEMINI.md"])
        self.assertEqual(everyone["skills"], [".claude/skills", ".agents/skills"])
        self.assertEqual(sorted(a["client"] for a in everyone["agents"]), ["claude-code", "codex", "gemini"])
        self.assertEqual(everyone["rulesReadFromInstructions"], ["codex", "gemini"])
        copilot_only = outputs(["copilot"])
        self.assertIn(".github/skills", copilot_only["skills"])
        self.assertEqual([a["folder"] for a in copilot_only["agents"]], [".github/agents"])

    def test_rulebooks_keep_their_globs_in_each_format(self):
        from stackfoundry.clients import render_rule
        from stackfoundry.frontmatter import split
        copilot, _, _ = split(render_rule(self.RULE, "copilot"))
        self.assertEqual(copilot["applyTo"], "web/**/*.ts,web/**/*.vue")
        cursor_text = render_rule(self.RULE, "cursor")
        self.assertIn("globs: web/**/*.ts,web/**/*.vue\nalwaysApply: false", cursor_text)
        claude, body, _ = split(render_rule(self.RULE, "claude-code"))
        self.assertEqual(claude["paths"], ["web/**/*.ts", "web/**/*.vue"])
        self.assertIn("- **Rule.** Why.", body)
        with self.assertRaises(ValueError):
            render_rule(self.RULE, "codex")

    def test_agents_convert_with_their_grants(self):
        import tomllib
        from stackfoundry.clients import render_agent
        from stackfoundry.frontmatter import split
        codex = tomllib.loads(render_agent(self.AGENT, "codex"))
        self.assertEqual((codex["name"], codex["sandbox_mode"]), ("web-bug-hunter", "read-only"))
        self.assertIn("Body with ''' quotes.", codex["developer_instructions"])
        copilot, _, _ = split(render_agent(self.AGENT, "copilot"))
        self.assertEqual(copilot["tools"], ["read", "search", "execute", "web"])
        gemini, _, _ = split(render_agent(self.AGENT, "gemini"))
        self.assertEqual(gemini["tools"], ["read_file", "read_many_files", "grep_search", "run_shell_command",
                                           "google_web_search"])
        self.assertEqual(render_agent(self.AGENT, "cursor"), self.AGENT)

    def test_render_rule_writes_to_the_assistants_standard_place(self):
        with TempRepo({".stackfoundry/config.json": "{}", ".stackfoundry/rules/web.md": self.RULE}) as root:
            proc = run_cli(["render-rule", str(root / ".stackfoundry/rules/web.md"), "--client", "copilot", "--write",
                            "--root", str(root)])
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue((root / ".github/instructions/web.instructions.md").is_file())

    def test_the_client_ids_have_one_home(self):
        from stackfoundry import clients, config
        self.assertIs(config.CLIENTS, clients.CLIENTS)
