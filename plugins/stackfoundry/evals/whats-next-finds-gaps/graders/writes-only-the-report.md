---
type: tool_used
tool: Write
input_match: '"file_path"\s*:\s*"(?![^"]*docs/reports/)'
min: 0
max: 0
arm: both
# No Write outside the report folder, including an overwrite of a file the scaffold created (`target: files` sees
# only new paths).
---
