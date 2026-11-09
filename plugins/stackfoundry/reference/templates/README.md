# Templates

Skeletons that `init`, `sync`, `research-stack`, `materialize` and `upgrade` fill to write files into a user's repo.
Each template's own frontmatter holds `templateVersion` (bump it when the skeleton changes in a way `upgrade` should
offer) and `output` (where the result goes). Everything after that frontmatter is the skeleton of the output file,
which may begin with its own frontmatter.

Placeholders are `{{name}}`. A placeholder the filler cannot ground in the repo is left out, never invented; a
table row or a section with nothing grounded is dropped rather than left empty. The template's own frontmatter
(`templateVersion`, `output`) is stripped: the output starts at the skeleton.

| Template | Output |
|---|---|
| `profile.md` | `.stackfoundry/profile.md` |
| `target.md` | `.stackfoundry/targets/<target>.md` |
| `pack-rulebook.md` | `.stackfoundry/rules/<pack-id>.md`: the layout `stackfoundry pack render` implements (never filled by hand) |
| `code-writer-skill.md` | `.claude/skills/<app-model>-code-writer/SKILL.md` (`<app-model>` = the bare id: `app-model-wpf` → `wpf`) |
| `instructions-block.md` | the `<!-- stackfoundry:begin -->` block in each instruction file the repo's assistants read (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`) |
| `materialized-agent.md` | `.stackfoundry/agents/<target>-<role>.md`, then each assistant's copy (`stackfoundry render-agent`); its base is recorded with `stackfoundry extensions base` |

The shared rulebooks in [`../rulebooks/`](../rulebooks/) and the tracker files in [`../trackers/`](../trackers/)
are templates too, with the same frontmatter convention. After writing any of them, the skill runs
`stackfoundry manifest record <files> --template <plugin-relative template path>`.
