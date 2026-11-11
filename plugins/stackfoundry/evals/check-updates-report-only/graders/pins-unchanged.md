---
type: regex
target: { source: file, path: package.json }
pattern: '"vue": "3\.2\.47"[\s\S]*"vite": "4\.1\.0"[\s\S]*"vitest": "0\.28\.5"'
match: contains
arm: both
# The report-only run leaves the fixture's pins as they were. This reads the file, so a Write overwrite or a Bash
# redirect into package.json fails it (a check on created paths alone would miss both).
---
