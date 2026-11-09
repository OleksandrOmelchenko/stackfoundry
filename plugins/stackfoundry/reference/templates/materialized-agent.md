---
templateVersion: 1
output: .stackfoundry/agents/{{target}}-{{role}}.md (then each assistant's copy via stackfoundry render-agent)
---
---
name: {{target}}-{{role}}
description: {{the role's one-line job}} for {{target}} ({{one line on what the target is}}). {{read-only or what it may write}}. Dispatched by /stackfoundry:{{orchestrator}} {{target}} in place of the generic {{role}}.
tools: {{the generic role agent's tools}}
---

# {{Target}} {{role title}}

<!-- Materialized by /stackfoundry:materialize from the plugin's generic `{{role}}` agent, plugin version
     {{pluginVersion}}. The team owns this file: /stackfoundry:upgrade never touches it. To pick up later
     improvements to the generic role, diff it against the plugin's agents/{{role}}.md by hand. -->

{{the generic role agent's body, with the target profile's facts inlined where the generic body says "read the
target profile", plus the team's tuning (extra categories, different weights, stricter gates)}}
