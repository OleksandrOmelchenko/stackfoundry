---
description: The surveyor turns one C# solution into two targets with different app models (ASP.NET Core vs WPF).
tags: [init, survey, needs-bash]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Agent, Bash, Write]
---

I'm about to set up stackfoundry here. Before anything gets written, survey this repository with the stackfoundry
surveyor and save the target map it proposes (targets with their paths and packs) as `target-map.json` in the repo
root. Don't create any other file.
