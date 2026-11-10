# Follow Gemini CLI users to Antigravity CLI

**Category:** plugin

## Context

Google moved Gemini CLI users to Antigravity CLI, and individual-tier Gemini CLI requests stopped on 2026-06-18.
Extensions carried over as Antigravity plugins ([google-antigravity]:
https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/). stackfoundry
still ships only for Gemini CLI:

- the README's install row runs `gemini extensions install` with the release's `stackfoundry-gemini.tar.gz`;
- `scripts/build_clients.py` `build_gemini` builds that extension, and `.github/workflows/release.yml` job `gemini`
  attaches it to every release (0.2.0 included);
- `plugins/stackfoundry/reference/clients.md` describes Gemini CLI only.

The domain brief (`.stackfoundry/domain/ai-coding-assistant-plugin.json`) lists capability `host-migration-support`,
which is **missing** here, and the weakness "Host churn strands users" [google-antigravity, gemini-extensions].
Source: `docs/reports/2026-11-10-whats-next.md`, item 1.

The outcome is that people coming from Gemini CLI get a working install path, or a clear statement that the channel
is retired. Nobody should follow a README row to a client that no longer serves them.

## Scope

- **Decide** between supporting Antigravity CLI as a channel and retiring Gemini CLI (keeping the Gemini extension
  for enterprise tiers only if it is still served there), recorded with its source.
- **If supported:**
  - `build_clients.py` produces what Antigravity reads (an Antigravity plugin, or the Agent Plugins `plugin.json`
    if that suffices), checked by `build_clients.py --check`;
  - the README has an Antigravity install row;
  - the release workflow attaches its asset, if one is needed;
  - `reference/clients.md` has an Antigravity column: manifest, install, hooks and their event shape, agents,
    instruction file, headless command.
- **The guard** recognises Antigravity's pre-tool hook event (`scripts/stackfoundry/guard.py` `detect` and
  `normalize`) and answers in its format, if the hook shape differs from Gemini's `BeforeTool`.
- **Clients and outputs:** `config.json` `clients` accepts the new id, and `stackfoundry outputs` maps its files.
- **The radar:** `stackfoundry-radar` checks every assistant in `clients` for deprecation and successor notices, not
  only Claude Code, so the next move is caught early.

## Design notes

- **Research first.** The brief could not read Antigravity's plugin reference or the Gemini migration guide
  (`notReached`). Research them from current sources: the plugin manifest, hook events, agent and skill folders,
  the instruction file, marketplace or install-by-URL, and the headless flag. Cite each fact in
  `reference/clients.md`'s Sources section, as the other clients are.
- **Retiring instead:** remove `build_gemini` and the release job, drop `gemini` from `clients.CLIENTS` with a
  migration note (`upgrade` step 0 style), and update the README and the CHANGELOG under "Removed". That is a
  breaking change for anyone using it, so it needs a minor or major bump per `docs/release.md`.
- **Reuse** `clients.render_agent` and `render_rule` patterns. A new client id flows through
  `clients.CLIENTS`, `RULE_FORMATS`, `INSTRUCTION_FILES` and `AGENT_FORMATS`.

## Affected areas

- `plugin`: `scripts/build_clients.py`, `plugins/stackfoundry/reference/clients.md`, `README.md`,
  `skills/stackfoundry-radar`, `skills/init` (client list in the interview).
- `cli`: `plugins/stackfoundry/scripts/stackfoundry/clients.py`, `guard.py`, `config.py`.
- `repo`: `.github/workflows/release.yml`, `docs/release.md` smoke table.

## Verification

- `build_clients.py --check` covers the new output, and `tests/test_build_clients.py` gains its cases.
- `tests/test_guard_clients.py` has a recorded Antigravity hook event per kind (edit, shell), denied and allowed.
- The `docs/release.md` smoke row for Antigravity is run on a real install: install, list, guard denial, and a plain
  request.
- The `cli` and `plugin` gates pass.

## Out of scope

- Other hosts' smoke tests (`docs/plans/host-smoke-matrix.md`).
- Any change to the Claude Code layout, which stays the source of truth.
