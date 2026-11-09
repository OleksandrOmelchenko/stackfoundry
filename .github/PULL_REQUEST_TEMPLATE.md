## What and why

<!-- One paragraph. Link the issue. -->

## Checklist

- [ ] `python -m unittest discover -s tests -t .` passes
- [ ] `sh plugins/stackfoundry/scripts/stackfoundry.sh verify-plumbing plugins/stackfoundry` is clean
- [ ] `claude plugin validate --strict .` and `claude plugin validate --strict plugins/stackfoundry` are clean
- [ ] Skill descriptions stay ≤ 250 characters, agent descriptions ≤ 300 (`.claude/rules/authoring.md`)
- [ ] No technology content shipped in the plugin: facts come from the repo profile or from web research at run time
- [ ] No volatile facts in living text (counts, `file:line`, dates, SHAs)
- [ ] `plugins/stackfoundry/CHANGELOG.md` updated under `Unreleased`
- [ ] Evals run for changed skills, or listed as not run
