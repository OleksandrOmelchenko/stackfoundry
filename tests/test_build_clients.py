"""scripts/build_clients.py: the other assistants' plugin files are generated, current and well formed."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests._support import PLUGIN, ROOT, TempRepo

sys.path.insert(0, str(ROOT / "scripts"))
import build_clients  # noqa: E402


class BuildClientsTests(unittest.TestCase):
    def test_the_committed_files_are_current(self):
        self.assertEqual(build_clients.main(["--check"]), 0)

    def test_the_manifest_checker_knows_exactly_the_vendored_schema_keys(self):
        schema = json.loads((ROOT / "scripts/schemas/agent-plugins-1.0.0/plugin.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(set(schema["properties"]), build_clients.AGENT_PLUGINS_KEYS)
        self.assertEqual(schema["properties"]["$schema"]["const"], build_clients.AGENT_PLUGINS_SCHEMA)
        self.assertEqual(schema["properties"]["name"]["pattern"], build_clients.AGENT_PLUGINS_NAME.pattern)

    def test_the_checker_rejects_what_the_closed_schema_rejects(self):
        good = {"$schema": build_clients.AGENT_PLUGINS_SCHEMA, "name": "stackfoundry"}
        self.assertEqual(build_clients.check_agent_plugins_manifest(good), [])
        for bad in ({**good, "skills": "./x"}, {**good, "name": "Bad--Name"}, {"name": "x"},
                    {**good, "author": {"name": "a", "twitter": "b"}}, {**good, "extensions": {"com.x": "str"}}):
            with self.subTest(bad=bad):
                self.assertNotEqual(build_clients.check_agent_plugins_manifest(bad), [])

    def test_copilot_agents_mirror_every_agent_with_mapped_tools(self):
        sources = sorted(p.stem for p in (PLUGIN / "agents").glob("*.md"))
        copies = sorted(p.name.removesuffix(".agent.md") for p in (PLUGIN / "com.github.copilot/agents").glob("*.agent.md"))
        self.assertEqual(sources, copies)
        text = (PLUGIN / "com.github.copilot/agents/stack-researcher.agent.md").read_text(encoding="utf-8")
        self.assertIn('"web"', text.split("---")[1])
        self.assertNotIn("WebSearch", text.split("---")[1])

    def test_every_marketplace_points_at_the_plugin_folder(self):
        codex = json.loads((ROOT / ".agents/plugins/marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual((ROOT / codex["plugins"][0]["source"]["path"]).resolve(), PLUGIN.resolve())
        copilot = json.loads((ROOT / ".github/plugin/marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual((ROOT / copilot["plugins"][0]["source"]).resolve(), PLUGIN.resolve())
        cursor = json.loads((ROOT / ".cursor-plugin/marketplace.json").read_text(encoding="utf-8"))
        folder = ROOT / cursor["metadata"]["pluginRoot"] / cursor["plugins"][0]["source"]
        self.assertTrue((folder / ".cursor-plugin" / "plugin.json").is_file())

    def _copilot_hook(self, field, shell_args, root_env):
        hook = json.loads((PLUGIN / "com.github.copilot/hooks/hooks.json").read_text(encoding="utf-8"))
        command = hook["hooks"]["preToolUse"][0][field]
        env = {k: v for k, v in os.environ.items()
               if k not in ("PLUGIN_ROOT", "COPILOT_PLUGIN_ROOT", "CLAUDE_PLUGIN_ROOT")}
        env.update(root_env)
        with TempRepo({".stackfoundry/guards.json": json.dumps({"schemaVersion": 1, "git": {"writes": "ask"}})}) as r:
            event = json.dumps({"toolName": "bash", "toolArgs": {"command": "git push"}, "cwd": str(r)})
            return subprocess.run([*shell_args, command], input=event, capture_output=True, text=True,
                                  encoding="utf-8", env=env, timeout=60)

    @unittest.skipUnless(shutil.which("sh"), "sh not available")
    def test_the_copilot_bash_hook_asks_with_a_root_and_stays_silent_without_one(self):
        # Copilot denies the tool call when a preToolUse hook errors, so a missing root must mean exit 0, no output.
        found = self._copilot_hook("bash", ["sh", "-c"], {"PLUGIN_ROOT": str(PLUGIN)})
        self.assertEqual((found.returncode, json.loads(found.stdout)["permissionDecision"]), (0, "ask"), found.stderr)
        missing = self._copilot_hook("bash", ["sh", "-c"], {})
        self.assertEqual((missing.returncode, missing.stdout.strip()), (0, ""), missing.stderr)

    @unittest.skipUnless(shutil.which("pwsh"), "pwsh not available")
    def test_the_copilot_powershell_hook_asks_with_a_root_and_stays_silent_without_one(self):
        found = self._copilot_hook("powershell", ["pwsh", "-NoProfile", "-Command"], {"COPILOT_PLUGIN_ROOT": str(PLUGIN)})
        self.assertEqual((found.returncode, json.loads(found.stdout)["permissionDecision"]), (0, "ask"), found.stderr)
        missing = self._copilot_hook("powershell", ["pwsh", "-NoProfile", "-Command"], {})
        self.assertEqual((missing.returncode, missing.stdout.strip()), (0, ""), missing.stderr)

    def test_the_gemini_extension_is_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "stackfoundry"
            build_clients.build_gemini(build_clients.load_claude_manifest(), out)
            manifest = json.loads((out / "gemini-extension.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["name"], "stackfoundry")
            self.assertTrue((out / "scripts" / "stackfoundry.sh").is_file())
            self.assertTrue((out / "skills" / "init" / "SKILL.md").is_file())
            agent = (out / "agents" / "bug-hunter.md").read_text(encoding="utf-8")
            self.assertIn("read_file", agent.split("---")[1])
            hooks = json.loads((out / "hooks" / "hooks.json").read_text(encoding="utf-8"))
            self.assertIn("${extensionPath}", hooks["hooks"]["BeforeTool"][0]["hooks"][0]["command"])


if __name__ == "__main__":
    unittest.main()
