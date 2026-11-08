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
3. **Check**: the unit tests, `verify-plumbing`, `claude plugin validate --strict` on the root and the plugin, and
   the eval cases for what changed.
4. **Commit**, then tag:

   ```sh
   claude plugin tag plugins/stackfoundry --dry-run
   claude plugin tag plugins/stackfoundry -m "stackfoundry %s" --push
   ```

   `claude plugin tag` checks that `plugin.json` and the marketplace entry agree before it creates
   `stackfoundry--v<version>`.
5. Users get it with `claude plugin update stackfoundry@stackfoundry` (or automatically when they turned on
   auto-update for the marketplace), then `/reload-plugins` or a new session. Repos then run
   `/stackfoundry:upgrade` to take template changes into their generated files.
