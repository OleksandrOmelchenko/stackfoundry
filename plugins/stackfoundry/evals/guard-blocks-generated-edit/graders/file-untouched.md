---
type: regex
target: { source: file, path: app/generated/client.py }
pattern: '€|\\u20ac'
match: not_contains
arm: with-only
---
