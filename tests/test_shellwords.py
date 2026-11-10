"""Reading shell commands for the guard: splitting into argv, and judging git and gh writes (threat model T5)."""
import unittest

from tests import _support  # noqa: F401  (puts the plugin's scripts on the path)
from stackfoundry import shellwords as sw

# Every form docs/security/plugin-threat-model.md T5 lists, plus the old suite's writes.
GIT_GH_WRITES = [
    "git commit -m x", "git push", "cd a && git reset --hard", "git -C x rebase main", "git tag v1", "git stash",
    "git stash pop", "git branch -D old", "git checkout -- a.txt", "gh pr create --fill", "gh pr merge 3",
    'git -C "a b" push', "git -C 'C:\\Program Files\\x' commit -m y", "git -C a -C b push",
    "git -c commit.gpgsign=false commit -m x", "git --no-pager push", "git.exe push", "/usr/bin/git push",
    "git pull", "git pull --rebase", "git branch feature", "git update-ref -d refs/heads/x",
    "git worktree remove ../wt", "git notes add -m x", "git config core.hooksPath /dev/null",
    "git --git-dir=.git push", "sh -c 'git push'", "bash -lc \"git push origin main\"", "echo $(git push)",
    "echo `git push`", "GIT_TRACE=1 git push", "env GIT_DIR=.git git commit -m x", "sudo git push",
    "git status; git push", "git status\ngit push", "git config set core.hooksPath x", "git config --unset a.b",
    "git remote add up https://x", "git symbolic-ref HEAD refs/heads/x", "git clean -fd",
    "gh api repos/o/r/issues/1/comments -f body=x", "gh api -X POST repos/o/r/issues", "gh api --method=PATCH x",
    "gh api -XDELETE repos/o/r", "gh api x --input body.json", "gh pr ready 3", "gh pr reopen 3",
    "gh release upload v1 a.zip", "gh workflow run ci.yml", "gh run rerun 7", "gh issue comment 3 -b x",
    "gh secret set TOKEN", "gh api graphql -f query='mutation { x }'", "gh -R o/r pr merge 3",
]
GIT_GH_READS = [
    "git status", "git diff HEAD", "git log --oneline", "git tag -l", "git tag", "git branch --list", "git branch",
    "git branch -vv", "git branch -a", "git stash list", "git show HEAD", "gh pr view 3", "echo commit",
    "echo 'git push'", 'echo "git push"', "git -c color.ui=never log", "git config --get user.name",
    "git config user.name", "git config --list", "git config get user.name", "git worktree list",
    "git notes show", "git remote -v", "git remote", "git clean -n", "git apply --check p.diff",
    "gh api repos/o/r/pulls", "gh api -X GET search/issues -f q=x", "gh run view 7", "gh pr list",
    "gh api graphql -f query='{ viewer { login } }'", "git checkout main", "git switch main", "grep push x",
    "git merge-base a b", "git rev-parse HEAD", "git fetch",
]


def writes(cmd, shell="Bash"):
    parts = sw.segments(cmd, shell)
    return any(sw.git_write(a) or sw.gh_write(a) for a in parts)


class GitGhWriteTests(unittest.TestCase):
    def test_writes(self):
        for cmd in GIT_GH_WRITES:
            with self.subTest(cmd=cmd):
                self.assertTrue(writes(cmd), cmd)

    def test_reads(self):
        for cmd in GIT_GH_READS:
            with self.subTest(cmd=cmd):
                self.assertFalse(writes(cmd), cmd)

    def test_powershell_paths_and_call_operator(self):
        self.assertTrue(writes('& "C:\\Program Files\\Git\\bin\\git.exe" push', "PowerShell"))
        self.assertTrue(writes("C:\\tools\\git.exe -C C:\\repo commit -m x", "PowerShell"))
        self.assertTrue(writes("pwsh -Command git push"))
        self.assertTrue(writes("cmd /c git push"))
        self.assertFalse(writes("Get-ChildItem C:\\repo; git status", "PowerShell"))


class SegmentTests(unittest.TestCase):
    def test_split_wrappers_and_unbalanced_quotes(self):
        self.assertEqual(sw.segments("a 1 && b | c; (d)"), [["a", "1"], ["b"], ["c"], ["d"]])
        self.assertEqual(sw.segments("FOO=1 nohup timeout 5 git push"), [["git", "push"]])
        self.assertEqual(sw.segments("sh -c 'git push && rm x'"), [["git", "push"], ["rm", "x"]])
        self.assertIsNone(sw.segments("echo 'unclosed"))

    def test_program(self):
        for tok in ("git", "GIT.EXE", "/usr/bin/git", "C:\\Program Files\\Git\\cmd\\git.exe"):
            self.assertEqual(sw.program(tok), "git")


if __name__ == "__main__":
    unittest.main()
