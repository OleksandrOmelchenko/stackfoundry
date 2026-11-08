# Security policy

## Reporting

Report vulnerabilities privately through
[GitHub security advisories](https://github.com/OleksandrOmelchenko/stackfoundry/security/advisories/new).
Please don't open a public issue for a security problem.

## Scope

In scope:

- the `stackfoundry` helper CLI and the guard hooks (`plugins/stackfoundry/bin`, `scripts`, `hooks`);
- skill or agent instructions that could make Claude act outside the user's request: writing outside the repo,
  running a destructive command, sending repo content to a third party, or following instructions found in web
  pages or repo files;
- the eval fixtures' scaffold scripts.

## Design commitments

- The helper CLI uses only the Python standard library, makes no network calls and writes only where its
  subcommand says (most subcommands are read-only).
- Hooks fail open when no repo profile exists, and fail closed with a reason when a guard matches.
- Web research is done by Claude's own tools under the user's permission settings. Fetched content is data, never
  instructions, and every agent that reads it says so.
