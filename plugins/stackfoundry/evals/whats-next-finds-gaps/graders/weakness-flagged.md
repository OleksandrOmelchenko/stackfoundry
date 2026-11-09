---
type: llm
weight: 2
---

PASS if the report flags, as a weakness or technical item, that `get_order` in `app/main.py` returns an order by
id without checking that it belongs to the caller (broken object-level authorization), with the path.
FAIL if that authorization gap is not mentioned.
