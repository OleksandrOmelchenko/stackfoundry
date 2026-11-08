# stackfoundry evals

Cases for `claude plugin eval`. Each one scaffolds a fixture repo from `fixtures/` at the repository root (so run
them from a clone of the repository, not from an installed copy of the plugin) and grades the result with and
without the plugin.

| Case | Needs | Proves |
|---|---|---|
| `surveyor-splits-app-models` | Bash, Write | the surveyor turns one C# solution into two targets: ASP.NET Core and WPF |
| `bug-hunt-finds-planted` | read-only | bug-hunt finds the discount boundary that contradicts the spec |
| `review-tests-flags-weak` | read-only | review-tests calls the not-null and tautological tests what they are |
| `security-review-finds-idor` | read-only | security-review-target finds the missing ownership check (and keeps 404) |
| `debug-reaches-root-cause` | read-only | debug goes from a customer symptom to the pagination slice |
| `guard-blocks-generated-edit` | Edit, Write | the guard hook denies a hand-edit of a generated file |
| `check-updates-report-only` | Bash, Write, WebFetch, WebSearch | check-updates writes one report and nothing else (`--allow-tools Bash Write WebFetch WebSearch`) |

## Running

```sh
cd plugins/stackfoundry
claude plugin eval . --scaffold --runs 1 --no-publish --tag read-only
claude plugin eval . --scaffold --runs 1 --no-publish --case guard-blocks-generated-edit --allow-tools Edit Write
claude plugin eval . --scaffold --runs 1 --no-publish --case surveyor-splits-app-models --allow-tools Bash Write
```

- **Authentication.** Each run is a `claude -p` child with a temporary home, so a sign-in stored for the desktop app
  or your shell does not reach it. Provide a token in the environment (for example from `claude setup-token`).
- **Bash cases need Claude Code's OS sandbox**: Linux with `bubblewrap` and `socat`, macOS, or WSL2 on Windows.
  Native Windows has no sandbox backend, so run the `needs-bash` cases there or in CI.
- `--scaffold` runs the case's `scaffold.sh` as you; the scripts only copy a fixture and `git init` it.
- Every case costs real tokens (two arms × runs). Start with `--runs 1`; use the default three before a release.
- Results go to `evals/results/` (git-ignored).
