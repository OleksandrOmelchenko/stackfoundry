---
type: llm
weight: 3
---

PASS if the response identifies the root cause in `list_orders` (`app/main.py`): the slice starts at `page * size`,
but pages start at 1 per the spec, so it should start at `(page - 1) * size`; and proposes a regression test whose
expected value comes from the spec (page 1 holds the first `size` orders).
FAIL if the root cause is wrong or only guessed without pointing at the slice, or no regression test is proposed.
