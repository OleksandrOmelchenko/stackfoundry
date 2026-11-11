---
description: The testing rulebook for every suite — where an expected value may come from, test layers, doubles, design techniques, determinism, assertions, no-gaming rules, the assurance gate, mutation/property/a11y testing, flaky tests, smells, review verdicts and fixer classes.
covers: where expected values come from, test layers, doubles, determinism, the assurance gate, flaky tests, review verdicts
paths:
  - "tests/**"
  - "fixtures/**"
  - "plugins/stackfoundry/evals/**"
  - "docs/test-designs/**"
---

# Testing rulebook

One rulebook for every suite. Per-target facts (harness, base classes, commands, traps) live in
`.stackfoundry/targets/<target>.md`; per-framework notes live in each tooling pack's rulebook
(`.claude/rules/tooling-*.md`, section Testing). Not here.

## 1. Oracles: where an expected value may come from

- **Every expected value cites a source.** In precedence order: the specs under `docs/specifications/` →
  the rulebooks in `.claude/rules/` → a generated contract (an API schema, generated client models, error types,
  enums) → a declared contract in code (documentation comments, an interface's documented behaviour) → a
  bug-report finding → the user's answer. Cite it in the design row, or in a one-line comment when the test name
  does not make it obvious.
- **The implementation is never the oracle.** Read production code to find partitions, branches and seams, never
  to copy the value it currently returns. "The test failed, so I set the expected value to what the code
  returned" pins the bug into the suite (oracle leak).
- **Characterization tests are labelled** (`characterization: <why>`), so a reviewer can tell pinned existing
  behaviour from specified behaviour.
- **Ambiguity becomes a question, never a guess.** An unresolved expected value goes to the design's Questions
  (❓) and is asked.

## 2. Which layer

- Each target profile names its primary test layer. As a default: **services and APIs** are tested mostly at their
  public boundary (HTTP, a message, a CLI invocation) against real managed dependencies (the database), with pure
  unit tests for logic without I/O; **UI apps** mostly as components or screens with real children and the
  network faked at its edge; **libraries** through their public API.
- End-to-end tests are for **critical journeys only**. A behaviour a smaller test can prove does not belong in e2e.
- Server rendering, visual baselines and contract tests each prove one thing only (server output, look, wire
  compatibility); use them for that thing.
- Push each check down to the smallest layer that can express it: flakiness and cost grow with test size.

## 3. Test doubles

- Preference: **real > fake > stub > interaction verification.** Verify an interaction only for a state-changing
  call to something you do not own, and don't over-specify its arguments.
- **Mock only unmanaged dependencies** (a payment provider, email, third-party HTTP, the clock). A database the
  application owns is managed: use the real one and assert its final state.
- **Don't mock types you don't own**: wrap them and fake the wrapper.
- An in-memory substitute for a real database only where the meaning does not depend on the database (constraints,
  transactions, concurrency and query semantics all do).
- A fake must not return shapes the real dependency cannot produce.

## 4. Designing the test list

- Write the **test list** before the tests: every behaviour (given/when/then), not "test method X".
- A **planned** change carries its test list in the plan, with each expected value's source, before code exists;
  the tests are written to that list, never derived from what was built.
- Techniques, per behaviour: **equivalence partitioning**; **boundary values, 3-value** (boundary and both
  neighbours) for money, quantities, lengths, dates and windows; **decision tables** for rule combinations
  (pricing, authorization role × owner × operation, eligibility, validation); **state transitions** for
  lifecycles, covering every valid transition **and every invalid one**; **pairwise** for configuration matrices;
  **property-based** where a statement holds for all inputs (§10).
- **Risk = likelihood × impact.** Money, auth, data loss, privacy and concurrency first.

## 5. How a test reads

- Arrange–Act–Assert, **one behaviour per test** (parameterized rows rather than several Acts).
- The name states the behaviour and the condition, in the framework's convention.
- DAMP over DRY: what the reader needs to understand the assertion is visible in the test.
- **No logic in tests**: no loops, conditionals or string building that recompute the expected value.
- Test through the **public surface**; assert **state and output**, not calls or internals. A test that breaks on
  a pure refactor is a defect (change-detector).
- Name constants whose meaning is not obvious.

## 6. Determinism

- **Time**: an injectable clock or fake timers; never the wall clock in an assertion.
- **Randomness**: seeded; log the seed on failure.
- **Collections**: order-insensitive unless order is the behaviour.
- **Isolation**: fresh state per test, reset *before* each test; never hardcode a database-generated id.
- **Waiting**: await the event, use the framework's retrying assertions. **No sleeps, no raised timeouts.**
- **Environment**: no real network, external provider, fixed port or machine-specific path. Environment-gated
  tests skip with a stated condition, never unconditionally.

## 7. Assertions and snapshots

- Assert the **specific** value the source states. A not-null check on a constructed object is not a test.
- Several assertions about one concept are fine; unrelated facts in one test is assertion roulette.
- Snapshots are narrow (one payload, one rendered fragment) and paired with an explicit assertion of the business
  fact. Never update a snapshot to make a failing test pass unless the diff is the intended change named in the
  task.

## 8. No gaming

A test agent **never**: loosens an assertion, deletes or skips a failing test, focuses a test (`.only`), wraps the
act in `try/catch` to pass, adds retries or sleeps as a fix, sets expected := observed, updates a snapshot to go
green, or edits production code, generated code, migrations or schema. Coverage is a prioritization signal, never
a target. A red test caused by a product defect stays red and is reported in bug-report form (id, `file:line`,
concrete failure, suggested fix); the user decides between fixing the product and quarantine.

## 9. Assurance gate for a new test

A new test is kept only if it (1) compiles and type-checks, (2) **passes 3 times with the order shuffled**, and
(3) covers an uncovered branch **or** kills a mutant the suite didn't. Otherwise it is REDUNDANT and dropped.
Where practical, prove it can fail: break the behaviour in a throwaway copy, or name the mutant it kills.

**Selective runs** prove only the tests they select. A green affected run says nothing about code listed as
**Uncovered**, nor about behaviour reached in ways the selection cannot see (reflection, configuration, a route
named in a string). Run the full suites before declaring a cross-cutting change done. A test that fails only in a
full run is a real finding (order dependence, §11).

## 10. Mutation, property-based and accessibility testing

- **Mutation testing**: report the score over detected and over valid mutants; scope to the diff and to domain
  logic, never DTOs, wiring, logging or generated code. Each survivor is a missing test or a written
  equivalent-mutant justification. **A report with zero killed mutants means the tool is broken**, including an
  "all timed out" report from a starved runner.
- **Property-based testing** for round-trips, invariants, idempotency and model-based checks. Keep readable example
  tests beside properties; a shrunk counterexample becomes a permanent example test.
- **Accessibility**: scan after the interaction that produces the state (dialog open, error shown), not only on
  first render; colour contrast only in a real browser; pair automated scans with keyboard and focus-order
  assertions.

## 11. Flaky tests

Classify before fixing, then fix the cause:

| Category | Fix |
|---|---|
| Async wait | await the event; retrying assertion |
| Concurrency | make the race explicit and deterministic (controlled ordering, a barrier) |
| Order dependence / shared state | fresh fixture per test; reset before |
| Time | fake clock or timers |
| Randomness | seed it |
| Network / external | fake at the edge; contract checked separately |
| Resource leak | dispose; per-test scope; await teardown |
| Unordered collection / float | order-insensitive or tolerance assertion |

Reproduce first (repeat runs, shuffled order, serial vs parallel). **Quarantine** only with the user's approval:
owner, linked issue, expiry date, recorded in the design (⏸). A retry is a diagnostic, never the fix.

## 12. Smell catalogue (cited by reviewers)

Assertion roulette · eager test · mystery guest · general fixture · sleepy test · conditional test logic ·
exception swallowing · empty test · sensitive equality · redundant assertion · magic number · change-detector
(implementation details, call order, private state, CSS classes, query text) · over-mocking (a mocked database
context, a mocked type you don't own, verifying a query) · tautology (expected value computed the way production
computes it).

## 13. Review verdicts (one per test)

| Verdict | Meaning | Severity |
|---|---|---|
| **SOUND** | Pins a sourced behaviour; would fail if it broke | 🟢 |
| **WEAK** | Passes, but a named mutant survives (`file:line` original → mutated): **CONFIRMED** by a mutation run or **PLAUSIBLE** by reasoning | 🟡 |
| **WRONG-ORACLE** | The expected value contradicts its source, or has none and isn't marked characterization | 🔴 |
| **BRITTLE** | Coupled to implementation; name the pure refactor that breaks it | 🟡 |
| **FLAKY-RISK** | A §11 category plus the ordering, interleaving or time that fails it | 🔴 in a gated lane, else 🟡 |
| **MISPLACED** | Wrong layer or harness (§2, §3) | 🟡 |
| **REDUNDANT** | Duplicates a named test and kills no extra mutant | 🔵 |
| **UNCLEAR** | A §12 smell that hides intent | 🔵 |

Every non-SOUND verdict carries its concrete scenario. A WRONG-ORACLE on money, auth, privacy or concurrency gets a
second, skeptical review before it is reported.

## 14. Fixer classification (before any edit)

- **TEST-DEFECT**: setup, wait, fixture or locator is wrong; the expected value matches its source.
- **PRODUCT-DEFECT**: the code contradicts the source. Report it; the test stays red.
- **ENV**: machine or harness state (stale build artifact, a locked output folder, a missing browser, the
  container runtime down). Fix the environment or the instructions, not the test.
- **FLAKY:\<category\>**: a §11 category, proven by reproduction; fix by that row.
- **SPEC-AMBIGUOUS**: the source does not settle the expected value. Ask; don't pick.

An expected value changes only when its **source** changed (a spec edit, an intended behaviour change named in the
task, a bug report's resolution); cite it in the fix.

## 15. Framework notes

Per framework, in its tooling pack's rulebook: [`tooling-unittest`](tooling-unittest.md) (the `unittest` suite under `tests/`), [`tooling-claude-plugin-eval`](tooling-claude-plugin-eval.md) (the eval cases under `plugins/stackfoundry/evals/`).
