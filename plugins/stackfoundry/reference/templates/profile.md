---
templateVersion: 1
output: .stackfoundry/profile.md
---
# {{product name}}: repo profile

<!-- Written by /stackfoundry:init from the interview and the survey. Owned by the team: edit freely.
     Every role agent reads it first, so keep it short and true. -->

## The product

{{what it does, for whom, in two or three sentences}}

## Users and channels

{{who uses each target: anonymous public, signed-in customers, staff, other services, offline operators}}

## What is at stake

{{money, personal data, auth, data integrity, availability, legal duties; which targets carry which}}

## Constraints that shape the code

{{regulation (e.g. GDPR, e-invoicing), concurrency (several staff editing at once), performance budgets,
supported platforms, anything a reviewer would otherwise call a mistake}}

## Who decides

{{who approves production deploys, live-data changes, majors, money-touching changes}}

## Working agreements

- Git: {{git policy: who commits, branches or single-branch, PRs or not}} (enforced as `guards.json` `git.writes`).
- Generated code: {{the generated folders and how each is regenerated}} (enforced by the guard hook).
- Docs root: `{{docsRoot}}`. Report dates use {{timezone}}.
- {{other agreements the interview surfaced}}

## Targets

`.stackfoundry/targets.json` is the list; each target's facts are in `.stackfoundry/targets/`.
