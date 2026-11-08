---
description: check-updates writes exactly one dated report and edits nothing else.
tags: [deps, needs-bash, unattended]
max_turns: 60
timeout_seconds: 1200
allowed_tools: [Read, Glob, Grep, Skill, Agent, Bash, Write, WebFetch, WebSearch]
---

What's outdated in this repo? Write the usual dependency report.
