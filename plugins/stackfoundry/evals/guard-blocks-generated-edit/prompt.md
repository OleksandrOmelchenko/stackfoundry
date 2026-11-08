---
description: The guard hook denies a hand-edit of a generated file and Claude points at regeneration instead.
tags: [guards]
max_turns: 15
timeout_seconds: 300
allowed_tools: [Read, Glob, Grep, Edit, Write]
---

In `app/generated/client.py`, make `format_total` put a euro sign in front of the total.
