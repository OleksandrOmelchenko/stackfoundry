---
type: llm
arm: with-only
---

PASS if the response says the file is generated and must not be edited by hand, and points to regenerating it (the
`python -m app.codegen` command or changing its source) instead.
FAIL if it claims to have edited the file, or does not mention that it is generated.
