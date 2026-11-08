import unittest

from tests import _support  # noqa: F401
from stackfoundry.frontmatter import split


class FrontmatterTests(unittest.TestCase):
    def test_scalars_lists_and_booleans(self):
        text = (
            "---\nname: bug-hunt\ndescription: \"Hunt: bugs, with a colon\"\n"
            "disable-model-invocation: true\ntools: Read, Grep\npaths:\n  - \"src/**\"\n  - docs/**\n"
            "argument-hint: [a, \"b, c\"]\n---\n# Body\n"
        )
        fields, body, errors = split(text)
        self.assertEqual(errors, [])
        self.assertEqual(fields["name"], "bug-hunt")
        self.assertEqual(fields["description"], "Hunt: bugs, with a colon")
        self.assertIs(fields["disable-model-invocation"], True)
        self.assertEqual(fields["tools"], "Read, Grep")
        self.assertEqual(fields["paths"], ["src/**", "docs/**"])
        self.assertEqual(fields["argument-hint"], ["a", "b, c"])
        self.assertEqual(body.strip(), "# Body")

    def test_no_frontmatter_returns_the_whole_text_as_body(self):
        fields, body, errors = split("# Title\n")
        self.assertEqual((fields, errors), ({}, []))
        self.assertEqual(body, "# Title\n")

    def test_unclosed_frontmatter_and_duplicates_are_errors(self):
        _, _, errors = split("---\nname: x\n")
        self.assertTrue(errors)
        _, _, errors = split("---\nname: x\nname: y\n---\n")
        self.assertTrue(any("duplicate" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
