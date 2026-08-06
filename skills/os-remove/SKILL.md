---
name: os-remove
description: Manifest-driven uninstaller for the agentic dev OS - removes one module, the glue only, or everything, by replaying the install manifest in reverse. Knowledge (wiki, metrics, os-config) is kept unless explicitly released. Triggers on /os-remove, "uninstall the agentic os", "remove the os glue", "tear out the dev os".
---

# os-remove

Undo what `/os-init` did, using only the manifest as the source of truth.
Safety rules: never run any git command; never touch any repo's code; never
touch auto-memory content; confirm once before executing `--all`.

## Shared contracts (identical across os-init / os-doctor / os-remove)

**Modules.** `core` plus optional `rtk`, `caveman`, `codegraph`, `statusline`,
`plugins`, `metrics`. Each module's Remove instructions live at
`<plugin-root>/modules/<name>/MODULE.md`; from this skill's base directory the
plugin root is two levels up (`../../`).

**Markers.** OS-injected content in shared files is wrapped
`<!-- AGENTIC-DEV-OS:BEGIN <module> -->` ... `<!-- AGENTIC-DEV-OS:END <module> -->`.
Removal deletes from BEGIN to END inclusive, nothing outside.

**Manifest** at `<workspace>/.claude/os-manifest.json`: `os_version`,
`installed_at`, `modules` (list), `modules_skipped` (list of
`{"name": "<module>", "reason": "<why>"}` entries), `actions` (ordered list of
`file_created` / `dir_created` / `block_injected` / `settings_entry` /
`plugin_installed` / `symlink_created` entries), `backups` (original-path to
backup-path map). A `symlink_created` entry carries
`"path": "<workspace>/<name>"` and `"target": "<absolute repo path>"`.
Partial installs are valid manifests - remove whatever is recorded.

## Modes

Parse from the invocation args:

- `--module <name>` - remove one module's actions only (and drop it from `modules`)
- `--glue-only` - remove the global `~/.claude/CLAUDE.md` block(s) and ALL
  hooks/settings entries; KEEP wiki, metrics, os-config
- `--all` - everything the manifest records

No args: AskUserQuestion which mode (one round, the three options above with
one-line consequences each).

## Procedure

1. Read the manifest. Absent: report "nothing to remove (no manifest)",
   suggest `/os-doctor`, stop.
2. `--all` only: confirm once with the user (list module count + action
   count) before touching anything.
3. Select the relevant actions for the mode, then replay them in REVERSE
   order of the `actions` list:
   - `block_injected` - strip the marker block from the file (BEGIN through
     END inclusive). Block already gone: note and continue.
   - `settings_entry` - remove the entry from the settings file by
     pointer + value match (jq). No exact match: report, do not guess-delete.
   - `file_created` / `dir_created` - delete ONLY if still matching what we
     created (file unmodified since install, dir empty of user content). If
     user-modified: ask keep/delete per item.
   - `plugin_installed` - tell the user to run `/plugin uninstall <name>`,
     or run it if the environment allows.
   - `symlink_created`: confirm the path is actually a symlink, then remove
     the LINK only; NEVER touch the target repo. If the path is no longer a
     symlink (user replaced it), report and skip.
   - `modules_skipped` entries record decisions only; they have no actions
     to replay.
   - Restore from `backups` where sensible (shared file whose only change
     was ours: prefer restoring the `.pre-os.bak`; otherwise strip markers
     surgically and leave the backup in place for the user).
4. **Knowledge is not install state.** `wiki/`, `metrics/`, and
   `os-config.yaml` hold accumulated knowledge. Even under `--all`, their
   deletion is a SEPARATE explicit AskUserQuestion defaulting to KEEP.
   Auto-memory content is never touched, under any mode.
5. Update the manifest: `--module` removes that module's actions + name and
   rewrites it; `--glue-only` removes the replayed actions; `--all` (after a
   clean run) deletes the manifest file itself.
6. Report: exactly what was removed, what was kept (and why), what needs a
   manual step (plugin uninstalls, kept backups). No git actions ever.
