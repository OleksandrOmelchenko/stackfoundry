# stackfoundry plugin

Studies your repository, researches each language, app model, capability and tool it uses from current official
sources, and writes repo-grounded rulebooks and target profiles. Generic role agents (bug hunter, test writer, fix
verifier, security and performance reviewers…) and orchestrator skills then work from those facts, so every
specialist knows your real paths, harnesses and gate commands.

## Install and start

```text
/plugin marketplace add OleksandrOmelchenko/stackfoundry
/plugin install stackfoundry@stackfoundry
/stackfoundry:init
```

`init` surveys the repo, proposes a target map (each deployable or testable unit with its stack of layers), asks you
to confirm it, researches every technology in parallel, grounds the results in your code, proves each gate command
once, and reports what it wrote. It never overwrites existing `.claude/` content without asking.

Later:

| Want | Run |
|---|---|
| Find bugs in one target | `/stackfoundry:bug-hunt <target>` |
| Write tests the right way | `/stackfoundry:design-tests <target>` then `/stackfoundry:write-tests <target> --design <doc>` |
| Review uncommitted work | `/stackfoundry:review-changes` |
| Investigate a failure | `/stackfoundry:debug` |
| See what is outdated | `/stackfoundry:check-updates`, then `/stackfoundry:act-on-updates` |
| Keep the research fresh | `/stackfoundry:tech-radar`, then `/stackfoundry:act-on-radar` |
| Pick up a new project or framework | `/stackfoundry:sync` |
| Take a new plugin version's templates | `/stackfoundry:upgrade` |

## Settings

`/plugin configure stackfoundry` sets the docs root, the research refresh window and the default fan-out effort.
Values recorded in the repo profile win.

## Requirements

Claude Code, git, Python 3.10 or newer on `PATH` as `python3`, `python` or `py -3`.
