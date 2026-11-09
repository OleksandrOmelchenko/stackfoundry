# Reference: the method

Everything here is technology-neutral. Facts about a particular repository are written into that repository by
`/stackfoundry:init`; rules about a particular technology are researched at run time.

| Path | What |
|---|---|
| [`layers.md`](layers.md) | The four layers (language, app model, capability, tooling), how app models are told apart, how roles read them |
| [`pack-research.md`](pack-research.md) | How a technology is researched into a pack: source order, citation and grounding rules, freshness |
| [`detect-signals.json`](detect-signals.json) | Detection hints for `stackfoundry survey` (evidence, never decisions) |
| [`schemas/`](schemas/) | JSON Schemas of every file init writes under `.stackfoundry/` |
| [`examples/`](examples/) | A worked targets/guards/ecosystems set for a repo with an API, a WPF app and a server-rendered web app |
| [`templates/`](templates/) | Skeletons of the repo profile, target profiles, pack rulebooks, code-writer skills, the CLAUDE.md block, materialized agents |
| [`rulebooks/`](rulebooks/) | Shared rulebooks installed into the repo: testing, dependency bumps, documentation, benchmarking |
| [`trackers/`](trackers/) | Tracker READMEs and templates: bug reports, test designs, plans, specifications, reports, deferred upgrades, radar decisions |

Role procedures are the agents in `../agents/`; orchestration is the skills in `../skills/`.
