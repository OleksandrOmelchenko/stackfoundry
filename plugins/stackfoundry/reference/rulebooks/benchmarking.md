---
templateVersion: 1
output: .claude/rules/benchmarking.md
---
---
description: Benchmarking rulebook — pre-register question, hypothesis and decision rule; what makes a micro-benchmark wrong; a quiet machine that the tooling never reconfigures; comparing runs and the verdict vocabulary; reports.
paths:
{{one "  - \"<glob>\"" line per benchmark project folder, plus "  - \"{{docsRoot}}/performance-reports/*-benchmarks.md\""}}
---

# Benchmarking rulebook

The harness for this repo is named in the benchmarking tooling pack (`.claude/rules/tooling-<harness>.md`) and the
target profile. The procedure is `/stackfoundry:write-benchmarks` and `/stackfoundry:run-benchmarks`. This file is
the rules they share.

## 1. Pre-register the question

Every benchmark carries, in its documentation, before it is run:
- **Question**: what decision the numbers feed.
- **Hypothesis**: the expected outcome with its reason (an ABI rule, a data layout, documented runtime
  behaviour), never "it should be faster".
- **Decision rule**: which verdict (§4) leads to which choice, including what happens on **Same**, the most
  common answer.
- **Models**: the production code it stands for (path + symbol).

A result is read against the rule it was registered with. Changing the rule after seeing the numbers is the
benchmark form of the oracle leak (`testing.md` §1): if the rule was wrong, say so and re-register it.

## 2. What makes a micro-benchmark wrong

- **Dead code**: every computed value is returned or consumed; a near-zero result on code that does work means the
  optimizer removed it.
- **Constant folding**: inputs come from setup fields or parameters, never literals the compiler can fold.
- **Measured setup**: building inputs and warm-up stay out of the measured body.
- **Unequal work**: variants differ only in the thing being compared.
- **No baseline**: a comparison marks its reference variant.
- **Leaking state** between iterations, unless that state is what is measured.
- **Flattering inputs**: vary inputs where branch prediction or caches would favour one variant.
- **Drifted copies**: a variant copied from production matches what it models.
- **Unmeasured claims**: a claim about generated code is backed by the harness's disassembly or profiler output.

## 3. Environment

- Optimized build, no debugger.
- **A quiet machine**: check idle CPU, foreign processes, power source and plan, free memory, and that no build or
  test run is in progress, before and during the run. A benchmark whose window saw foreign load is
  **contaminated** and left out.
- **Nothing changes the machine**: the tooling never switches the power plan, kills or reprioritizes a process, or
  stops another session's service. Blockers go to the user, who decides.
- Runtime defaults (GC mode, tiering, PGO) unless the question is about them; the report records the environment.

## 4. Comparing and judging

- Within one run is the primary evidence; across runs (three by default, fresh processes) is reproduction; across
  commits keeps the earlier run as baseline.
- **A difference is real** only when the median ratio passes the threshold, every clean run agrees on the
  direction, and no run was contaminated.
- Allocated bytes are deterministic for synchronous code: a difference across runs of one commit is a harness bug.
- **Verdict vocabulary**, exactly one per comparison: **Faster**, **Slower**, **Same**, **Unstable**,
  **Contaminated**.

## 5. Reports

`{{docsRoot}}/performance-reports/<date>-<topic>-benchmarks.md`: the pre-registration quoted, the environment and
commit, the comparison per run set with exclusions and why, the verdict per decision rule, and the command that
reproduces it. A dated report is a snapshot.
