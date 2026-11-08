# Templates

Skeletons that `init`, `sync`, `research-stack`, `materialize` and `upgrade` fill to write files into a user's repo.
Each template's own frontmatter holds `templateVersion` (bump it when the skeleton changes in a way `upgrade` should
offer) and `output` (where the result goes). Everything after that frontmatter is the skeleton of the output file,
which may begin with its own frontmatter.

Placeholders are `{{name}}`. A placeholder the filler cannot ground in the repo is left out, never invented; a
section with nothing grounded is dropped rather than left empty.

| Template | Output |
|---|---|
| `profile.md` | `.claude/stackfoundry/profile.md` |
| `target.md` | `.claude/stackfoundry/targets/<target>.md` |
| `pack-rulebook.md` | `.claude/rules/<pack-id>.md` |
| `code-writer-skill.md` | `.claude/skills/<app-model>-code-writer/SKILL.md` (`<app-model>` = the bare id: `app-model-wpf` → `wpf`) |
| `claude-md-block.md` | the `<!-- stackfoundry:begin -->` … `<!-- stackfoundry:end -->` block in the root `CLAUDE.md` |
| `materialized-agent.md` | `.claude/agents/<target>-<role>.md` |

The shared rulebooks in [`../rulebooks/`](../rulebooks/) and the tracker files in [`../trackers/`](../trackers/)
are templates too, with the same frontmatter convention. After writing any of them, the skill runs
`stackfoundry manifest record <files> --template <plugin-relative template path>`.
