---
type: tool_used
tool: Bash
input_match: '(^|[^0-9&>])>>?\s*(?!/dev/null|&)[^\s|&]|\btee\b|\bsed\s+-i|\bmv\s|\bcp\s'
min: 0
max: 0
arm: both
# No shell command that writes a file: a redirect (other than to /dev/null or another stream), tee, sed -i, mv or cp.
---
