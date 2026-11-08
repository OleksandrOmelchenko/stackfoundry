---
type: llm
weight: 3
---

PASS if the response gives a verdict per test and (a) does not call `Pricing_CanBeCreated` SOUND (it only asserts
not-null), and (b) does not call `Total_AppliesDiscount` SOUND, naming at least one concrete reason: the expected
value is computed with the production formula (tautology / wrong oracle), or the 100.00 discount boundary is never
exercised so a `>` vs `>=` mutant survives.
FAIL if either test is judged sound, or verdicts are given without a concrete scenario or mutant.
