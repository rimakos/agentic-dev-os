---
name: os-doctor
description: Read-only health check of the agentic dev OS install in this workspace - verifies core scaffold, installed modules, hooks, marker blocks, and manifest integrity, then reports a status table with fix hints. Triggers on /os-doctor, "check the os install", "is the os wired up", "os health check".
allowed-tools: Read, Grep, Glob, Bash
---

# os-doctor

Diagnose, never treat. This skill READS ONLY - it writes nothing, fixes
nothing, and runs no mutating command. Output is a status table with fix
hints; the user (or `/os-init` / `/os-remove`) applies fixes.

## Shared contracts (identical across os-init / os-doctor / os-remove)

**Modules.** `core` always installed; optional: `rtk`, `caveman`, `codegraph`,
`statusline`, `plugins`, `metrics`. Each module's instructions (incl. its
Verify section) live at `<plugin-root>/modules/<name>/MODULE.md`; from this
skill's base directory the plugin root is two levels up (`../../`).

**Markers.** OS-injected content in shared files is wrapped
`<!-- AGENTIC-DEV-OS:BEGIN <module> -->` ... `<!-- AGENTIC-DEV-OS:END <module> -->`.

**Manifest** at `<workspace>/.claude/os-manifest.json`: `os_version`,
`installed_at`, `modules` (list), `modules_skipped` (list of
`{"name": "<module>", "reason": "<why>"}` entries), `actions` (list of
`file_created` / `dir_created` / `block_injected` / `settings_entry` /
`plugin_installed` / `symlink_created` entries), `backups` (original-path to
backup-path map). A `symlink_created` entry carries
`"path": "<workspace>/<name>"` and `"target": "<absolute repo path>"`.

## Procedure

1. **Manifest.** Read `<workspace>/.claude/os-manifest.json`. Absent: report
   "OS not installed here", suggest `/os-init`, stop. Present but unparseable:
   report ❌ with the parse error, continue with what file checks are possible.
2. **Core scaffold integrity.** Check: wiki dirs present
   (`wiki/`, `wiki/repos/`, `wiki/seams/`, plus `wiki/index.md`,
   `wiki/log.md`, `wiki/system-map.md`, `wiki/CLAUDE.md`), `os-config.yaml`
   present and not still full of template examples (match exact whole
   template placeholder tokens only, the literal example values from
   `template/os-config.yaml`, never bare substrings: substring matches hit
   real user filenames), hooks registered in `.claude/settings.json`
   (drift-check, block-dangerous-git, ticket-impact-reminder,
   wiki-verify-reminder), hook scripts present and executable,
   `permissions.ask` in `.claude/settings.json` holding the git write rules
   (`git add`, `commit`, `push`, `stash`, branch creation, plain and `rtk`),
   `wiki/known-issues/` present, and global `~/.claude/CLAUDE.md` containing
   the `core` marker block. A `core` block that still names `operating-flow`
   or subagent-driven execution is a pre-0.3.0 install: report ⚠️ and point to
   the "Upgrading from 0.2.x" steps in the plugin README.
3. **Per-module Verify.** For each module listed in `modules`, read
   `../../modules/<name>/MODULE.md` and run its Verify section (read-only
   commands only - version checks, file existence, grep). Also confirm any
   marker blocks / settings entries the manifest attributes to that module
   are actually present where recorded. Report each module in
   `modules_skipped` as ⚠️ with "skipped by decision: <reason>", never ❌.
   Note: caveman right after install legitimately shows ⚠️
   "pending fresh session" until a new session prints CAVEMAN MODE ACTIVE.
4. **Manifest drift.** Flag every manifest action whose target no longer
   exists (file deleted, settings entry gone, marker block stripped), and
   any backup path in `backups` that is missing. For every `symlink_created`
   action, verify the path is still a symlink AND its target resolves.
5. **Wiki drift.** Flag wiki files with mtime newer than `wiki/log.md`
   (edits not closed out by a log entry - suggest `/wrap`).

## Output

One table, then nothing else:

```
component            | status | fix hint
core: wiki scaffold  | ✅     | -
core: hooks          | ⚠️     | drift-check.sh not executable: chmod +x .claude/hooks/drift-check.sh
rtk                  | ❌     | rtk binary not found: reinstall via /os-init or remove via /os-remove --module rtk
```

✅ healthy, ⚠️ degraded/drifted, ❌ broken/missing. One row per component
(core split into scaffold / hooks / global block; one row per module; one row
each for manifest drift and wiki drift). Fix hints are commands or skill
pointers only - this skill never applies them.
