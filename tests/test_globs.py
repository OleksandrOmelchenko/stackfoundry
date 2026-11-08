import unittest

from tests import _support  # noqa: F401  (import path)
from stackfoundry.globs import match, normalize


class GlobTests(unittest.TestCase):
    def test_double_star_spans_directories_under_its_prefix_only(self):
        self.assertTrue(match("src/api/a/b.cs", "src/api/**"))
        self.assertTrue(match("src/api/b.cs", "src/api/**"))
        self.assertFalse(match("src/apix/b.cs", "src/api/**"))

    def test_leading_double_star_includes_the_top_level(self):
        self.assertTrue(match("a.cs", "**/*.cs"))
        self.assertTrue(match("x/y/a.cs", "**/*.cs"))
        self.assertFalse(match("x/y/a.csx", "**/*.cs"))

    def test_single_star_stays_within_one_directory(self):
        self.assertTrue(match("src/a.cs", "src/*.cs"))
        self.assertFalse(match("src/sub/a.cs", "src/*.cs"))

    def test_a_pattern_without_a_slash_matches_the_name_at_any_depth(self):
        self.assertTrue(match("docs/deep/README.md", "*.md"))
        self.assertTrue(match("Dockerfile", "Dockerfile"))
        self.assertTrue(match("svc/Dockerfile", "Dockerfile"))

    def test_braces_question_mark_and_classes(self):
        self.assertTrue(match("web/nuxt.config.ts", "**/nuxt.config.{ts,js}"))
        self.assertFalse(match("web/nuxt.config.py", "**/nuxt.config.{ts,js}"))
        self.assertTrue(match("a1.txt", "a?.txt"))
        self.assertTrue(match("v2/x", "v[0-9]/x"))
        self.assertFalse(match("vA/x", "v[0-9]/x"))

    def test_a_trailing_slash_means_the_whole_directory(self):
        self.assertTrue(match("gen/a/b.ts", "gen/"))

    def test_windows_separators_and_dot_slash_are_normalized(self):
        self.assertEqual(normalize(".\\src\\a.cs"), "src/a.cs")
        self.assertTrue(match("src\\api\\a.cs", "src/api/**"))


if __name__ == "__main__":
    unittest.main()
