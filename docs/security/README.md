# Security

Living threat models, one per target (`/stackfoundry:threat-model <target>`). Their **gaps** use the bug-report
finding format (`T` ids, 🔴/🟡/🔵, ⬜/⚠️/✅/🚫 markers, an open-ids banner), so `/stackfoundry:backlog` lists the
open ones and `stackfoundry tracker check` verifies each file. Findings of a security review
(`/stackfoundry:security-review-target`) go to `../bug-reports/` with `S` ids.

## Index

| Threat model | State | Open |
|---|---|---|
| [plugin](plugin-threat-model.md) | open | 🔵 T8, T12, T13, T14, T17 |
