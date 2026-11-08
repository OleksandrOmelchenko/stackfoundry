# stackfoundry

A Claude Code marketplace whose plugin casts a **repo-grounded swarm of specialists** for every stack in your
repository: code writers, plumbing verifiers, test designers, writers, reviewers and fixers, bug hunters, fix
verifiers, security and performance reviewers, dependency bumpers, and a scheduled tech radar that keeps all of it
current.

Generic advice reads as authoritative and is usually wrong for your codebase. stackfoundry generates nothing from
memory. It reads your repo, researches each technology it finds from **current official sources** (release notes,
migration guides, advisories), and writes rulebooks that name your real paths, harnesses and gate commands, each claim
citing its source.

## Install

```text
/plugin marketplace add OleksandrOmelchenko/stackfoundry
/plugin install stackfoundry@stackfoundry
/stackfoundry:init
```

To pin it for everyone who clones your repo, `init` adds `extraKnownMarketplaces` and `enabledPlugins` to the
committed `.claude/settings.json`. Each collaborator still runs the install command once.

Requirements: Claude Code, git, Python 3.11+ (the helper CLI and hooks use only the standard library).

stackfoundry is a **Claude Code** plugin. It ships a command-line helper in `bin/`, and claude.ai and Cowork don't
install plugins that do; its work (git, builds, test suites) needs a development environment anyway.

## How it works

### A stack is a language × an app model

C# in an ASP.NET API and C# in a WPF desktop app share syntax, analyzers and NuGet, and differ in nearly everything a
code writer or bug hunter needs to know: lifecycle, threading, hosting, packages, test harness, how it ships. So each
target's stack is built from layers:

| Layer | Owns | Examples |
|---|---|---|
| Language | style, analyzers, typing, package-ecosystem mechanics, the SDK/runtime pin | C#, TypeScript, Python, Go |
| App model | lifecycle, threading, hosting, request/UI model, bug classes, perf profile, how it ships | ASP.NET Core, WPF, Vue SPA, Nuxt SSR, Django |
| Capability | a concern that crosses app models | EF Core, OIDC server, OpenAPI client generation, i18n |
| Tooling | test frameworks, CI, infra | xUnit, Vitest, Playwright, GitHub Actions, Terraform |

Each layer gets its own path-scoped rulebook, so Claude loads the C# rules plus the WPF rules for a desktop file, and
the C# rules plus the ASP.NET Core rules for an API file.

### Procedure in the plugin, facts in your repo

| The plugin ships (and updates) | `init` writes into your repo (and you own) |
|---|---|
| orchestrator skills: `bug-hunt`, `write-tests`, `check-updates`, `tech-radar`… | `.claude/stackfoundry/`: profile, targets, ecosystems, guards, researched packs, manifest |
| generic role agents: `bug-hunter`, `test-writer`, `fix-verifier`… | `.claude/rules/<layer>-<tech>.md`: grounded, path-scoped rulebooks |
| the method: layer taxonomy, schemas, research procedure, rulebook and tracker templates | `.claude/skills/<app-model>-code-writer/`: the decisions that go wrong most often, per app model |
| the `stackfoundry` helper CLI and guard hooks | tracker scaffolds: bug reports, test designs, plans, specifications, dependency and radar reports |

A role agent is told its **target** and reads that target's profile and rulebooks, so one `bug-hunter` hunts
security bugs in your public API and binding leaks in your desktop app, each with that stack's checklist. When a team
wants a hand-tuned agent for one target, `/stackfoundry:materialize` writes it into the repo.

### The loops

- **Tests**: `design-tests` → `write-tests` → `review-tests` → `fix-tests`. Expected values cite a source, never the code's output; new tests pass three shuffled runs and add coverage or kill a mutant.
- **Bugs**: `bug-hunt` (read-only, per-category fan-out, adversarial verification) ↔ `fix-verify` (one verdict per landed fix). Findings live in trackers with stable ids.
- **Reactive**: `debug` (reproduce → bisect → fix → regression test) and `fix-ci`.
- **Security**: `threat-model` per target from its exposure, `security-review-target`.
- **Review**: `review-changes` dispatches independent reviewers that are never told the author's intent.
- **Dependencies**: `check-updates` (unattended, report-only) → `act-on-updates` (asks once, routes) → `bump-all`.
- **Radar**: `tech-radar` (unattended) researches new versions, tools, practices and advisories per technology → `act-on-radar` routes each item (adopt, bump, migrate, trial, watch, reject).
- **Docs and backlog**: `plan-feature`, `implement-plan`, `retire-plan`, `backlog`, `docs-reconciler`.

Run `/stackfoundry:schedule` to register the unattended ones as Claude desktop scheduled tasks.

## Privacy

Research sends technology names and versions to web search. Your code, file contents and profile never leave your
machine through stackfoundry's own scripts, which make no network calls. Agents run in your Claude Code session under
your permission settings.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). The design rationale is in [docs/design.md](docs/design.md).

## License

[MIT](LICENSE)
