---
type: llm
weight: 3
---

PASS if the response reports, as a bug, that an order totalling exactly 100.00 gets no discount although the pricing
spec says orders of 100.00 or more get 10% off (the comparison in `Pricing.Total` uses `>` where `>=` is required),
and points at `src/Api/Pricing.cs`.
FAIL if that boundary defect is missing, or is mentioned only as a style remark without the concrete failure.
