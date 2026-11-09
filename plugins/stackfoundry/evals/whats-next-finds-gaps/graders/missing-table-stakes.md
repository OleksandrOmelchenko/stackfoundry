---
type: llm
weight: 3
---

PASS if the recommended steps include order status or delivery tracking as missing (the `Order` model in
`app/main.py` has no status, shipment or tracking field and no endpoint exposes one), call it table stakes or rank it
among the first items, and cite a domain source for it.
FAIL if order status is not recommended, is called present, or is recommended without any source or repo path.
