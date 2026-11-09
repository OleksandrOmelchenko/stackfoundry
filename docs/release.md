# Releasing

Users stay on a plugin version until `plugin.json`'s `version` changes, and dependency ranges resolve against git
tags named `<plugin>--v<version>`. So a release is: bump the version, record the changes, tag.

1. **Decide the bump** (Semantic Versioning, judged from the user's side):
   - **major**: a repo profile written by the previous version no longer works (a schema field renamed or removed,
     a generated file moved), or a skill or agent was removed or renamed;
   - **minor**: new skills, agents, roles, schema fields with defaults, or template changes that `upgrade` can apply;
   - **patch**: fixes and wording.
2. **Update** `plugins/stackfoundry/.claude-plugin/plugin.json` `version`, and move `plugins/stackfoundry/CHANGELOG.md`'s `Unreleased`
   section under the new version with today's date. A template change that `upgrade` should offer also bumps the
   template version recorded in `reference/` (see `docs/design.md`, "Upgrades").
3. **Check**: the unit tests, `verify-plumbing`, `python scripts/build_clients.py --check`, `claude plugin validate
   --strict` on the root and the plugin, and the eval cases for what changed. Then the smoke test below in each
   assistant you can run.
4. **Commit**, then tag:

   ```sh
   claude plugin tag plugins/stackfoundry --dry-run
   claude plugin tag plugins/stackfoundry -m "stackfoundry %s" --push
   ```

   `claude plugin tag` checks that `plugin.json` and the marketplace entry agree before it creates
   `stackfoundry--v<version>`.
5. **Publish a GitHub release** for the tag. The `Release assets` workflow (`.github/workflows/release.yml`) builds
   the Gemini CLI extension and attaches it as `stackfoundry-gemini.tar.gz`. The other assistants read the
   committed files that `python scripts/build_clients.py` generates, which the checks in step 3 keep current.
6. Users get it with `claude plugin update stackfoundry@stackfoundry` (or automatically when they turned on
   auto-update for the marketplace), then `/reload-plugins` or a new session. Repos then run
   `/stackfoundry:upgrade` to take template changes into their generated files.

## Smoke test per assistant

Each assistant installs from this repository: `.claude-plugin/marketplace.json` (Claude Code),
`.agents/plugins/marketplace.json` (Codex), `.github/plugin/marketplace.json` (Copilot), `.cursor-plugin/marketplace.json`
(Cursor), and the release asset (Gemini CLI). In each one: add the marketplace from a local clone, install
`stackfoundry`, check that its skills and agents are listed, and in a scratch repo whose `.stackfoundry/guards.json`
marks a folder generated, ask it to edit a file there: the guard must refuse, naming how to regenerate. Then say
"walk me through stackfoundry" with no slash command: the `walkthrough` skill must start. The table in
`plugins/stackfoundry/reference/clients.md` lists what is still to *confirm* per assistant.

| Assistant | Install | Lists skills and agents | Guard refuses a generated-file edit | Plain request starts a skill |
|---|---|---|---|---|
| Claude Code | proven | proven | proven: in the fourth self-run the installed guard refused a release tag and asked before a commit | proven: headless "walk me through stackfoundry" and "set up stackfoundry in this repo" started `walkthrough` and `init` |
| Copilot CLI | proven: marketplace add and install from a local path; the skills install | skills proven; agents not checked | not run yet | partly: "Use the walkthrough skill: …" loads it through Copilot's `skill` tool; on the bare "walk me through stackfoundry" the default model (gpt-4.1) answered from Copilot's own docs instead |
| Codex | not run yet | not run yet | not run yet | not run yet |
| Cursor | not run yet | not run yet | not run yet | not run yet |
| Gemini CLI | not run yet | not run yet | not run yet | not run yet |
