"""Antigravity CLI as a repo client: where its files go, its rule and agent formats, its size limits, its block
sentence. Formats from reference/clients.md ([ag-rules], [ag-build-plugins]); accessed 2026-11-11."""
import json
import unittest

from tests._support import TempRepo, run_cli, targets_json, write
from stackfoundry import block, clients, sizes

RULE = "---\ndescription: Web rules\npaths:\n  - \"*.ts\"\n  - \"src/**\"\n---\n\n# Web\n\nSee [testing](testing.md).\n"
AGENT = "---\nname: reviewer\ndescription: Reviews.\ntools: Read, Grep, Glob, Bash, WebSearch, Agent\n---\n\nBody.\n"


class OutputsTests(unittest.TestCase):
    def test_antigravity_gets_path_scoped_rules_shared_skills_and_agents_md(self):
        out = clients.outputs(["antigravity"])
        self.assertEqual(out["rules"], [{"client": "antigravity", "folder": ".agents/rules", "suffix": ".md"}])
        self.assertEqual(out["rulesReadFromInstructions"], [])
        self.assertEqual(out["instructions"], ["AGENTS.md"])
        self.assertEqual(out["skills"], [".agents/skills"])
        self.assertEqual(out["agents"], [])  # no documented project agents folder

    def test_agents_md_is_shared_with_codex(self):
        self.assertEqual(clients.outputs(["codex", "antigravity"])["instructions"], ["AGENTS.md"])


class RuleFormatTests(unittest.TestCase):
    def test_a_rule_is_glob_triggered_with_one_quoted_comma_separated_globs_string(self):
        text = clients.render_rule(RULE, "antigravity")
        self.assertTrue(text.startswith('---\ntrigger: glob\nglobs: "*.ts, src/**"\ndescription: "Web rules"\n---\n'),
                        text)
        self.assertIn("See [testing](testing.md).", text)  # same suffix, so sibling links stay

    def test_render_rule_writes_into_agents_rules(self):
        with TempRepo({".stackfoundry/rules/web.md": RULE}) as root:
            targets_json(root, {"targets": []})
            proc = run_cli(["render-rule", ".stackfoundry/rules/web.md", "--client", "antigravity", "--write",
                            "--root", str(root)], cwd=root)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue((root / ".agents/rules/web.md").is_file())


class AgentFormatTests(unittest.TestCase):
    def test_the_grant_maps_to_antigravity_tools(self):
        fields_text = clients.render_agent(AGENT, "antigravity").split("---")[1]
        self.assertIn('tools: ["view_file", "grep_search", "find_by_name", "list_dir", "run_command", "search_web"]',
                      fields_text)

    def test_a_grant_with_no_equivalent_is_refused_rather_than_widened(self):
        with self.assertRaisesRegex(ValueError, "no tool in its grant has an Antigravity equivalent"):
            clients.render_agent(AGENT.replace("Read, Grep, Glob, Bash, WebSearch, Agent", "Agent"), "antigravity")

    def test_there_is_no_project_agent_path(self):
        with self.assertRaisesRegex(ValueError, "no project agents folder"):
            clients.agent_path(clients.Path("x.md"), "antigravity")


class SizeAndBlockTests(unittest.TestCase):
    def setUp(self):
        self.repo = TempRepo()
        self.root = self.repo.__enter__()
        self.addCleanup(self.repo.__exit__, None, None, None)
        targets_json(self.root, {"targets": [{"name": "web", "paths": ["src/**"]}]})
        write(self.root, {".stackfoundry/config.json": json.dumps({"schemaVersion": 1,
                                                                   "clients": ["codex", "antigravity"]})})

    def test_a_rule_copy_past_24000_bytes_is_an_error(self):
        big = RULE + "y" * 24_001
        write(self.root, {".stackfoundry/rules/web.md": big, ".agents/rules/web.md": clients.render_rule(big, "antigravity")})
        rows = {r["path"]: r for r in sizes.check(self.root)}
        self.assertTrue(any("(antigravity, hard limit)" in e for e in rows[".agents/rules/web.md"]["errors"]),
                        rows[".agents/rules/web.md"])

    def test_a_shared_agents_md_says_how_each_reader_loads_the_rulebooks(self):
        write(self.root, {".stackfoundry/rules/web.md": RULE})
        readers = block.instruction_files(self.root, ["codex", "antigravity"])["AGENTS.md"]
        text = block.render(self.root, "AGENTS.md", readers)
        self.assertIn("Antigravity CLI loads each rulebook's copy in `.agents/rules/` when it reads a matching file.",
                      text)
        self.assertIn(block.READ_FIRST, text)  # for Codex, which has no path-scoped rules


if __name__ == "__main__":
    unittest.main()
