---
description: debug turns a customer symptom into the pagination root cause, with a regression-test idea.
tags: [debug, read-only]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Agent]
---

Customers with only a few orders say that page 1 of their order list comes back empty. Find out why. You can't run
or edit anything in this session.
