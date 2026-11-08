# Stack layers

A **stack** is the list of packs a target is built from, one or more per layer. Two targets in the same language can
have entirely different stacks: C# in an ASP.NET Core API and C# in a WPF desktop app share a language pack and
nothing else that matters to a code writer, bug hunter or tester.

## The four layers

| Layer | Owns | Pack id | Rulebook `paths:` |
|---|---|---|---|
| **language** | syntax and idioms, style and formatter, analyzers/linters and their severity policy, typing and nullability, error-handling idioms, the package-ecosystem *mechanics* (manifest, lock file, central versions, exact pins), the SDK/runtime pin | `language-<id>` | every file of that language in every target that uses it (`**/*.cs`) |
| **app-model** | lifecycle and startup, threading and async model, hosting, DI and configuration, the request or UI model, state management, typical bug classes, performance profile, security surface, the end-to-end test approach, packaging and deployment | `app-model-<id>` | the folders of the targets that use it (`src/Api/**`) |
| **capability** | one concern that crosses app models: an ORM, an auth server, generated API clients, i18n, an outbox, a search engine, a payment provider, a regulated domain (GDPR, e-invoicing) | `capability-<id>` | the folders where it is used, or the files that touch it |
| **tooling** | test frameworks and runners, mutation and property-testing tools, linters that are not part of a language pack, CI, containers, infrastructure-as-code, provisioning | `tooling-<id>` | the test folders, config files or infra folders it governs |

Ids are short, lower-case and kebab-case, named after the thing people search for: `csharp`, `typescript`,
`aspnet-core`, `wpf`, `nuxt-ssr`, `vue-spa`, `efcore`, `oidc-server`, `xunit`, `vitest`, `github-actions`.

## Telling app models apart

One language, several app models, decided by strong signals and never by the language alone:

| Signal kind | Examples |
|---|---|
| SDK or project type | an MSBuild `Sdk="Microsoft.NET.Sdk.Web"`; `<UseWPF>true</UseWPF>`; an Android application plugin; a `manage.py` |
| Framework config file | `nuxt.config.ts`, `angular.json`, `next.config.js`, `svelte.config.js` |
| Entry-point shape | a web host builder; an `Application` subclass with XAML; a CLI argument parser as the entry point; a worker loop |
| Dependency | a web framework package; a UI toolkit; a mobile SDK |

Rules:

- **One folder can hold two app-model targets** when they fail differently. A Nuxt app has a Vue-component layer
  (reactivity, a11y, styling) and a server-rendering layer (cross-request state, hydration, status codes, head).
  Splitting them gives each its own bug categories and test harness; the targets share paths, and
  `change-targets` reports both.
- **A test project is not an app model.** It belongs to the target it tests (`testPaths`), and its framework is a
  tooling pack.
- **A class library** takes the app model of the targets that use it. A library shared by several app models is a
  target of its own (`shared`), whose changes reach every consumer: its gate is theirs.
- **Ambiguity is asked.** Two plausible app models, a library with no clear consumer, or an app model the survey
  hints at only weakly go to the user during `init`, with the evidence.

## How layers combine in a role

Every role agent reads, for its target, in this order:

1. `.claude/stackfoundry/profile.md` (what the product is, who uses it, what is at stake);
2. `.claude/stackfoundry/targets/<target>.md` (stack facts, harness, gate, traps, oracle sources);
3. the rulebook of each pack in the target's stack, language first, then app model, capabilities, tooling;
4. the shared rulebook for its role (`testing.md` for test roles, `dependency-bumps.md` for bumpers…).

When two layers disagree (a language rule and an app-model rule), the more specific layer wins and the rulebook
says so explicitly; an unexplained contradiction is a finding for `research-stack` to resolve.

## What a pack holds

The schema is [`schemas/pack.schema.json`](schemas/pack.schema.json); research produces it as described in
[`pack-research.md`](pack-research.md). In short, per pack:

- identity: layer, id, the versions in use here and where they are pinned;
- **rules**: the conventions and decisions that go wrong most often, each grounded in the repo (path + symbol) and
  cited (URL, version, access date);
- **bugCategories**: what a bug hunter checks for this layer, each with the failure it causes;
- **testing**: which layer of test proves what, the harness, the runner commands, flaky-test traps;
- **performance** and **security** notes;
- **upgrade**: where the version is pinned, lock-step partners, release-note and migration-guide URLs;
- **sources**: every URL read, with the version it describes and the date it was read.
