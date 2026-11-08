# Changelog

All notable changes to the stackfoundry plugin are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/).
A release tag is `stackfoundry--v<version>` (see `docs/release.md` in the repository).

## [Unreleased]

### Added

- Marketplace and plugin manifests, repository setup (CI, pre-commit hook, issue and PR templates).
- The stack model: four layers (language, app model, capability, tooling); one language can carry several app
  models, each with its own rulebook and bug categories.
- `init`, `research-stack`, `sync`, `upgrade`, `materialize`, `configure-guards`: build and maintain a repo profile
  whose technology rules are researched from current sources, cited and grounded in the repo.
- Generic role agents for every role (survey, research, bug hunting, fix verification, the four test roles,
  performance, security, plumbing, debugging, review, docs, benchmarks), reading the profile at run time.
- Work skills: the test quality loop, bug-hunt and fix-verify, review-changes, quality-sweep, security review and
  threat modelling, debug and fix-ci, the backlog and plan lifecycle, the work modes, benchmarks.
- Dependency and radar skills: check-updates, act-on-updates, bump-all, bump, check-formats, tech-radar,
  act-on-radar, radar-digest, stackfoundry-radar, flaky-watch, schedule; github-prs and cleanup-merged.
- The `stackfoundry` helper CLI (Python standard library only, no network) and the guard hook (generated files,
  forbidden commands, git-write policy).
- Eval cases on three fixture repos with planted defects.
