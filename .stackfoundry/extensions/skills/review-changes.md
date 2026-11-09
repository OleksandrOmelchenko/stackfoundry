---
extends: review-changes
mode: extend
---
stackfoundry reviewing itself: the generated client files and the plugin plumbing are part of every plugin change.

## After: Verify every finding before relaying it
When the change touches `plugins/stackfoundry/` or `scripts/build_clients.py`, also run
`python scripts/build_clients.py --check` and `stackfoundry verify-plumbing plugins/stackfoundry`. A failure of
either is a 🔴 finding naming the file it reports, with the fix (regenerate with `python scripts/build_clients.py`,
or the plumbing error's own fix).
