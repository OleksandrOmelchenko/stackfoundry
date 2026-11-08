"""The marketplace and plugin manifests agree with each other and with the release rules in docs/release.md."""
import json
import re
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
PLUGIN_DIR = ROOT / "plugins" / "stackfoundry"
PLUGIN = PLUGIN_DIR / ".claude-plugin" / "plugin.json"
ICON = PLUGIN_DIR / ".claude-plugin" / "icon.png"

SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?$")


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.market = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
        self.plugin = json.loads(PLUGIN.read_text(encoding="utf-8"))

    def test_marketplace_lists_the_plugin_by_its_own_name(self):
        entries = {p["name"]: p for p in self.market["plugins"]}
        self.assertIn(self.plugin["name"], entries)
        source = entries[self.plugin["name"]]["source"]
        self.assertEqual((ROOT / source).resolve(), PLUGIN_DIR.resolve())

    def test_plugin_version_is_semver(self):
        # Dependency ranges resolve against tags named <plugin>--v<version> (docs/release.md).
        self.assertRegex(self.plugin["version"], SEMVER)

    def test_marketplace_entry_does_not_pin_a_conflicting_version(self):
        entry = next(p for p in self.market["plugins"] if p["name"] == self.plugin["name"])
        if "version" in entry:
            self.assertEqual(entry["version"], self.plugin["version"])

    def test_user_config_defaults_respect_their_own_bounds(self):
        for key, spec in self.plugin.get("userConfig", {}).items():
            with self.subTest(key=key):
                default = spec.get("default")
                if "options" in spec:
                    self.assertIn(default, spec["options"])
                if spec.get("type") == "number":
                    self.assertGreaterEqual(default, spec.get("min", default))
                    self.assertLessEqual(default, spec.get("max", default))

    def test_icon_is_a_square_png_the_directory_accepts(self):
        # The plugin directory accepts a square PNG of 512 to 2048 px per side, under 2 MB.
        data = ICON.read_bytes()
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        width, height = struct.unpack(">II", data[16:24])
        self.assertEqual(width, height)
        self.assertTrue(512 <= width <= 2048)
        self.assertLess(len(data), 2 * 1024 * 1024)


if __name__ == "__main__":
    unittest.main()
