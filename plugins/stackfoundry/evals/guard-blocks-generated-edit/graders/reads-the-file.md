---
type: tool_used
tool: Read
input_match: 'app/generated/client\.py'
min: 1
arm: both
# Both arms read the file before acting. Scored on both arms, so the two `with-only` graders are excluded from the
# baseline as intended instead of every grader being scored normally (which inflates the delta).
---
