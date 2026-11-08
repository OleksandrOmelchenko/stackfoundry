---
templateVersion: 1
output: "{{docsRoot}}/security/{{target}}-threat-model.md"
---
# {{target}}: threat model

**Open:** {{open gap ids by severity, e.g. "🔴 T2 · 🟡 T5", or "none"}}

A living document (`/stackfoundry:threat-model {{target}}` refreshes it). Exposure: {{exposure}}. Stakes: {{stakes}}.

## Assets

{{what is worth stealing, corrupting or denying; where it lives (path + symbol, store, secret)}}

## Actors

{{who can reach the target, with what credentials and intent}}

## Entry points

{{each with path + symbol, the actor that reaches it, and the auth it requires}}

## Trust boundaries

{{each crossing: what is validated, authenticated or authorized there (path + symbol)}}

## Threats

| Threat | Category | Entry point | Mitigation (path + symbol) | Gap |
|---|---|---|---|---|

## Gaps

{{one block per gap, in the bug-report finding format:
### T1 🔴 ⬜ OPEN — title
- **Where:** …
- **Threat:** …
- **Failure:** the concrete attack and its outcome
- **Fix:** …}}

## Not covered

{{what the model did not reach and why}}
