---
type: llm
weight: 3
---

PASS if the response reports that `GET /orders/{order_id}` (`get_order` in `app/main.py`) returns any customer's order
without checking it belongs to the caller in `X-Customer-Id` (an IDOR / broken object-level authorization), ranks it
as the most severe or a blocker, and says the fix must answer 404 (not 403) for someone else's order, as the spec
requires.
FAIL if the missing ownership check is not reported, or the suggested fix returns 403.
