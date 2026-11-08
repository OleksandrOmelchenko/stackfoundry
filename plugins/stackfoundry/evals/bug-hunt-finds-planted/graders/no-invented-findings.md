---
type: llm
---

PASS if every finding the response marks as a blocker (🔴 or "blocker") is real in the code it cites: no claim about
a file, method or behaviour that does not exist in the repository.
FAIL if a blocker-level finding is invented or contradicts the cited code.
