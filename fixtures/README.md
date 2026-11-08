# Eval fixtures

Small repositories the eval cases in `plugins/stackfoundry/evals/` run against. A case's `scaffold.sh` copies one of
these folders into the empty eval workspace and makes it a git repository (`fixtures/scaffold-lib.sh`).

Each fixture carries **known answers**, listed in its `EXPECTED.md` (excluded from the copy, so the agent never sees
it): a planted bug with the spec that proves it is a bug, a weak test, an outdated or vulnerable pinned package, and
the target map `init` should arrive at.

| Fixture | Proves |
|---|---|
| `dotnet-web-and-wpf` | one language, two app models: an ASP.NET Core API and a WPF app become two targets with different stacks |
| `vue-spa` | a TypeScript UI target with a component harness |
| `python-fastapi` | a Python service with a security-relevant planted bug |

A `<fixture>.profile/` folder beside a fixture holds a ready `.claude/stackfoundry/` profile. Cases that test a skill
on an initialized repo (bug-hunt, review-tests, debug…) call `scaffold <fixture> with-profile`; cases that test
`init` itself use the bare fixture.

The fixtures are not built or tested in CI: they exist to be read, surveyed and reviewed. Keep them small, and keep
each planted defect provable from the fixture's own spec.
