# stackfoundry

A plugin for Claude Code, Codex, GitHub Copilot, Cursor and Gemini CLI. It reads your repository, researches each
technology it finds from current official sources, and sets up specialists grounded in your real paths, harnesses and
gates: code writers, test writers and reviewers, bug hunters, fix verifiers, security and performance reviewers,
dependency bumpers and a tech radar.

## Quick Start

### Installation

**Claude Code**

```text
/plugin marketplace add OleksandrOmelchenko/stackfoundry
/plugin install stackfoundry@stackfoundry
```

**Other assistants**

| Assistant | Install |
|---|---|
| GitHub Copilot CLI | `copilot plugin marketplace add OleksandrOmelchenko/stackfoundry`, then `copilot plugin install stackfoundry@stackfoundry` |
| Codex | `codex plugin marketplace add OleksandrOmelchenko/stackfoundry`, then install `stackfoundry` from its plugin list |
| Cursor | add `OleksandrOmelchenko/stackfoundry` as a team marketplace, or clone it and link `plugins/stackfoundry` into `~/.cursor/plugins/local/` |
| Gemini CLI | `gemini extensions install` with the `stackfoundry-gemini.tar.gz` of a release |
| Any Agent Skills client | copy `plugins/stackfoundry/skills/` into the folder it reads (often `.agents/skills/`); skills only |

Requirements: git, Python 3.11+, and `sh` (Git Bash on Windows) or PowerShell 7.

### Set up your repository

Ask your assistant:

```text
Set up stackfoundry in this repo
```

(In Claude Code, `/stackfoundry:init` does the same.) It surveys the repo, agrees the targets with you, researches
each technology, and writes:

- `.stackfoundry/`: the profile, targets, guards and researched packs;
- path-scoped rulebooks in each assistant's format (`.claude/rules/`, `.github/instructions/`, `.cursor/rules/`);
- code-writer skills per app model, and tracker folders for bug reports, test designs and plans.

### Find your way

Not sure what to ask? Say:

```text
Walk me through stackfoundry
```

It asks what you want to do, explains the matching skill in two lines, and runs it with your yes.

### Make a skill your own

```text
Customize review-changes: also run our contract tests
```

The change is written to `.stackfoundry/extensions/` in your repo, which every run of the skill reads, in every
assistant. Plugin updates never overwrite it: `upgrade` re-checks it, and merges a full replacement with the
plugin's changes. Format: `plugins/stackfoundry/reference/extensions.md`.

### Everyday requests

Every skill starts from a plain request. A few to begin with:

| Say | Runs |
|---|---|
| Write the feature the repo's way | `write-code` |
| Write tests for the API | `write-tests` |
| Run the tests my change needs | `run-tests` |
| Find bugs in the desktop app | `bug-hunt` |
| Did my fix hold? | `fix-verify` |
| Why is CI failing? | `fix-ci` |
| Review my changes | `review-changes` |
| Security review of the API | `security-review-target` |
| What should we build next? | `whats-next` |
| What's left in the backlog? | `backlog` |
| Keep me posted on our stack | `schedule` (next section) |

### Keep watching your stack

Some skills are made to run on their own: each run writes one dated report and never changes code. Ask:

```text
Schedule stackfoundry's background checks
```

`schedule` proposes a cadence for each one, asks once, and registers them as scheduled tasks; outside the Claude
desktop app it prints the cron, Task Scheduler or GitHub Actions setup instead. Each also runs on demand.

| Check | What each report gives you | Then say |
|---|---|---|
| `tech-radar` | news about your stack: new releases, deprecations that hit code you use, security advisories, new tools and practices, each with its source | "act on the radar" |
| `check-updates` | every pinned dependency, SDK, CI action and image that is outdated, majors flagged | "act on the updates" |
| `stackfoundry-radar` | whether the plugin, or the files it generated in your repo, are behind | "update stackfoundry's files in this repo" |
| `flaky-watch` | tests that both passed and failed across shuffled runs, with their seeds | "fix the flaky tests" |
| `docs-reconciler` (report only) | docs that drifted from the code | "fix the stale docs" |
| `whats-next` (report only) | the next product and technical steps: what a product of your kind is expected to have and you lack, present weaknesses, where your domain is moving, each with a source and a path | "what's next" (to plan the ones you pick) |

"Radar summary" digests the last few reports: what was acted on, and what keeps coming back.

## How it works

- **A stack is a language × an app model.** C# in an API and C# in a WPF app get different rulebooks, bug categories
  and test advice.
- **Procedure in the plugin, facts in your repo.** The plugin ships generic skills and role agents; `init` writes
  your repo's facts, and you own them.
- **Nothing from memory.** Every rule cites the source it was researched from, and the radar flags stale ones.
- **Guards.** A pre-tool hook blocks edits to generated files and forbidden commands, and asks before git writes.

Details: [docs/design.md](docs/design.md). What each assistant reads: `plugins/stackfoundry/reference/clients.md`;
how far each one is tested: [docs/release.md](docs/release.md).

## Privacy

Research sends technology names and versions to web search. Your code and profile never leave your machine through
stackfoundry's own scripts, which make no network calls.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
