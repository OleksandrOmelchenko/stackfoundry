"""`stackfoundry render-block`: the instruction-file block is generated from the profile, never written by hand."""
import json
import unittest

from tests._support import TempRepo, run_cli, targets_json, write
from stackfoundry import block, pack

TARGETS = {"docsRoot": "docs", "targets": [
    {"name": "api", "paths": ["src/**"], "testPaths": ["tests/**"], "packs": ["language-python", "tooling-pytest"]},
    {"name": "web", "paths": ["web/**"], "packs": ["language-python", "app-model-vue"]},
]}
PYTHON = ('---\ndescription: "Python 3.12 rulebook (language layer). Researched 2026-11-01; source pack x."\n'
          'covers: encodings, the version floor, subprocess and path handling\npaths:\n  - "**/*.py"\n---\n\n# Python\n')
PYTEST = ('---\ndescription: "pytest 8 rulebook (tooling layer). Researched 2026-11-01; source pack y."\n'
          'paths:\n  - "tests/**"\n  - "conftest.py"\n---\n\n# pytest\n')
TESTING = ('---\ndescription: The testing rulebook for every suite — where an expected value may come from.\n'
           'covers: oracles, the assurance gate, flaky tests\npaths:\n  - "tests/**"\n---\n\n# Testing\n')
EXTRA = '---\ndescription: Local rules; one more sentence.\npaths:\n  - "a|b/**"\n---\n\n# Extra\n'


class RenderBlockTests(unittest.TestCase):
    def setUp(self):
        self.repo = TempRepo()
        self.root = self.repo.__enter__()
        self.addCleanup(self.repo.__exit__, None, None, None)
        targets_json(self.root, TARGETS)
        write(self.root, {".stackfoundry/rules/language-python.md": PYTHON,
                          ".stackfoundry/rules/tooling-pytest.md": PYTEST,
                          ".stackfoundry/rules/testing.md": TESTING,
                          ".stackfoundry/rules/zz-extra.md": EXTRA})

    def config(self, *clients):
        write(self.root, {".stackfoundry/config.json": json.dumps({"schemaVersion": 1, "clients": list(clients)})})

    def test_rows_link_from_the_file_and_take_covers_then_the_title(self):
        text = block.render(self.root, ".claude/CLAUDE.md", ["claude-code"])
        rows = [line for line in text.splitlines() if line.startswith("| [")]
        self.assertEqual(rows, [
            "| [language-python](../.stackfoundry/rules/language-python.md) | `**/*.py` | "
            "encodings, the version floor, subprocess and path handling |",
            "| [tooling-pytest](../.stackfoundry/rules/tooling-pytest.md) | `tests/**`, `conftest.py` | pytest 8 |",
            "| [testing](../.stackfoundry/rules/testing.md) | `tests/**` | oracles, the assurance gate, flaky tests |",
            "| [zz-extra](../.stackfoundry/rules/zz-extra.md) | `a\\|b/**` | Local rules |",
        ])
        self.assertIn("Targets: `api`, `web`.", text)
        self.assertNotIn("{{", text)
        self.assertTrue(text.startswith("<!-- stackfoundry:begin"))
        self.assertTrue(text.endswith("<!-- stackfoundry:end -->\n"))
        root_text = block.render(self.root, "AGENTS.md", ["codex"])
        self.assertIn("| [language-python](.stackfoundry/rules/language-python.md) |", root_text)

    def test_each_assistant_reading_a_file_gets_its_sentence(self):
        self.assertIn("Claude Code loads each rulebook's copy in `.claude/rules/` when it reads a matching file.",
                      block.render(self.root, "CLAUDE.md", ["claude-code"]))
        shared = block.render(self.root, "AGENTS.md", ["codex", "copilot", "gemini"])
        self.assertIn("Copilot loads each rulebook's copy in `.github/instructions/` when it reads a matching file. "
                      "Before editing a file that matches a rulebook's globs, read that rulebook.", shared)
        self.assertEqual(shared.count("Before editing a file"), 1)

    def test_files_follow_init_rule_for_claude_md(self):
        self.assertEqual(block.instruction_files(self.root, ["claude-code", "codex", "copilot"]),
                         {"CLAUDE.md": ["claude-code"], "AGENTS.md": ["codex", "copilot"]})
        write(self.root, {".claude/CLAUDE.md": "# Team notes\n"})
        self.assertEqual(block.instruction_files(self.root, ["claude-code"]), {".claude/CLAUDE.md": ["claude-code"]})
        write(self.root, {"CLAUDE.md": "# Root\n"})
        self.assertEqual(block.instruction_files(self.root, ["claude-code"]), {"CLAUDE.md": ["claude-code"]})

    def test_write_splices_between_markers_and_keeps_the_rest_and_its_line_endings(self):
        self.config("claude-code")
        (self.root / "CLAUDE.md").write_bytes(b"# Team\r\n\r\nKeep me.\r\n\r\n<!-- stackfoundry:begin old -->\r\n"
                                              b"stale\r\n<!-- stackfoundry:end -->\r\n\r\nAfter.\r\n")
        proc = run_cli(["render-block", "--write", "--root", str(self.root)])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = (self.root / "CLAUDE.md").read_bytes()
        self.assertTrue(data.startswith(b"# Team\r\n\r\nKeep me.\r\n\r\n<!-- stackfoundry:begin (managed"))
        self.assertTrue(data.endswith(b"<!-- stackfoundry:end -->\r\n\r\nAfter.\r\n"))
        self.assertNotIn(b"stale", data)
        self.assertEqual(data.count(b"\n"), data.count(b"\r\n"))

    def test_write_appends_to_a_file_without_markers_and_creates_a_missing_one_in_lf(self):
        self.config("claude-code", "codex")
        (self.root / "CLAUDE.md").write_bytes(b"# Team\n")
        self.assertEqual(run_cli(["render-block", "--write", "--root", str(self.root)]).returncode, 0)
        claude = (self.root / "CLAUDE.md").read_bytes()
        self.assertTrue(claude.startswith(b"# Team\n\n<!-- stackfoundry:begin"))
        agents = (self.root / "AGENTS.md").read_bytes()
        self.assertTrue(agents.startswith(b"<!-- stackfoundry:begin"))
        self.assertNotIn(b"\r\n", claude + agents)
        again = run_cli(["render-block", "--write", "--root", str(self.root)])
        self.assertEqual(again.returncode, 0)
        self.assertEqual((self.root / "CLAUDE.md").read_bytes(), claude)  # idempotent

    def test_stdout_is_lf_and_names_one_file(self):
        self.config("claude-code", "codex")
        proc = run_cli(["render-block", "AGENTS.md", "--root", str(self.root)])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Before editing a file", proc.stdout)
        both = run_cli(["render-block", "--root", str(self.root)])
        self.assertEqual(both.returncode, 2)
        self.assertIn("name one instruction file", both.stderr)
        other = run_cli(["render-block", "GEMINI.md", "--root", str(self.root)])
        self.assertEqual(other.returncode, 2)
        self.assertIn("not an instruction file", other.stderr)

    def test_no_rulebooks_is_an_error(self):
        for f in (self.root / ".stackfoundry/rules").glob("*.md"):
            f.unlink()
        self.config("claude-code")
        proc = run_cli(["render-block", "CLAUDE.md", "--root", str(self.root)])
        self.assertEqual(proc.returncode, 2)
        self.assertIn("no rulebooks", proc.stderr)


class PackCoversTests(unittest.TestCase):
    PACK = {"schemaVersion": 1, "id": "language-python", "layer": "language", "title": "Python",
            "researchedAt": "2026-11-01", "versions": [], "rules": [], "sources": {}, "rulebookPaths": ["**/*.py"]}

    def test_covers_reaches_the_rulebook_frontmatter_only_when_set(self):
        self.assertNotIn("covers:", pack.render(self.PACK))
        text = pack.render({**self.PACK, "covers": "encodings, the version floor"})
        self.assertIn("\ncovers: encodings, the version floor\npaths:\n", text)


if __name__ == "__main__":
    unittest.main()
