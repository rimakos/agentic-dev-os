---
name: os-init
description: Onboarding wizard that installs the agentic dev OS into the current workspace - preflight, workspace setup, module selection, scaffold, global glue, repo analysis, ticket source, smoke test. Triggers on /os-init, "set up the agentic os", "onboard this workspace", "install the dev os".
---

# os-init

Install the OS into the current workspace. Interactive wizard: one question
round at a time, present drafts before writing, record everything in the
manifest so `/os-remove` can undo it. Hard rules: NEVER run git commit/push/add;
NEVER modify any repo's code; only OS files get written.

## Shared contracts (identical across os-init / os-doctor / os-remove)

**Modules.** `core` is always installed. Optional, each asked y/n: `rtk`,
`caveman`, `codegraph`, `statusline`, `plugins`, `metrics`. Each module's
install/verify/remove instructions live at `<plugin-root>/modules/<name>/MODULE.md`;
from this skill's base directory the plugin root is two levels up (`../../`).

**Markers.** Any content injected into a shared file (global `~/.claude/CLAUDE.md`,
any settings.json, wiki/CLAUDE.md) is wrapped:

```
<!-- AGENTIC-DEV-OS:BEGIN <module> -->
...content...
<!-- AGENTIC-DEV-OS:END <module> -->
```

NEVER append to a shared file without markers.

**Manifest** at `<workspace>/.claude/os-manifest.json`:

```json
{
  "os_version": "0.3.0",
  "installed_at": "YYYY-MM-DD",
  "modules": ["core", "..."],
  "modules_skipped": [{"name": "<module>", "reason": "<why>"}],
  "actions": [
    {"type": "file_created", "path": "..."},
    {"type": "dir_created", "path": "..."},
    {"type": "block_injected", "path": "...", "module": "..."},
    {"type": "settings_entry", "path": "...", "pointer": "hooks.PreToolUse", "value": {}},
    {"type": "plugin_installed", "name": "..."},
    {"type": "symlink_created", "path": "<workspace>/<name>", "target": "<absolute repo path>"}
  ],
  "backups": {"<original-path>": "<backup-path>"}
}
```

Append to `actions` IMMEDIATELY after every mutating action (crash-safe: a
partial install must still be removable). Before the FIRST edit of any
pre-existing shared file, copy it to `<same-path>.pre-os.bak` and record the
pair in `backups`.

## Workflow

### 1. Preflight

Check and report each: `git --version` (required), `jq --version` (warn-only,
but recommend installing it: without jq the block-dangerous-git hook falls
back to over-blocking and settings merges are harder), workspace layout
(current dir contains repo checkouts as subdirectories or siblings - list
what you detect). If `<workspace>/.claude/os-manifest.json` already exists:
STOP. Report "already installed", point to `/os-doctor` (health check) and
`/os-remove` (uninstall).

Activation note: plugin skills are available in the CURRENT session
immediately after `/plugin install`; only the workspace scaffold's hooks need
a fresh `claude` launched from the workspace root (they resolve via
`$CLAUDE_PROJECT_DIR`). Never attempt to launch a nested `claude` from inside
a session (the `!` prefix runs non-interactively and fails).

### 2. Workspace setup

Detect the layout. Case A: the current dir already contains repo checkouts as
subdirectories. Proceed. Case B: the current dir is empty or holds no repos
(the common fresh-onboarding case). AskUserQuestion for the absolute path(s)
of the product repo checkout(s), then create one symlink per repo in the
workspace root (`ln -s <repo-path> <workspace>/<repo-name>`), verify each
resolves, and record each as a `symlink_created` manifest action.

The pattern, stated explicitly: one workspace per project, recommended name
`~/<project>-os`. The repo itself is NOT the workspace and gets ZERO OS files
written inside it. A second unrelated project gets its own workspace with its
own wiki and os-config. If a repo is not cloned yet, pause and ask the user
to clone it themselves (the wizard never runs git clone), then continue.

### 3. Module selection

ONE AskUserQuestion round, multiSelect, listing the 6 optional modules with a
one-line description and cost/benefit each:

- `rtk` - token-saving CLI proxy for dev commands (saves tokens; adds a hook layer)
- `caveman` - compressed reply mode (terser output; off by default since 0.3.0, the core block already sets response length)
- `codegraph` - semantic code graph for fast symbol lookup (faster exploration; index build cost)
- `statusline` - Claude Code status line setup (visibility; cosmetic)
- `plugins` - recommended plugin installs, incl. playwright + context7 (fewer wrong-API loops; more installed surface)
- `metrics` - PR/ticket cycle-time tracking (trend data; needs periodic upkeep)

Core is not asked; it always installs. If the user intends to use
`ticket-testing` and declines `plugins`, warn that playwright is required for it.

### 4. Scaffold (core)

Copy the CONTENTS of `<plugin-root>/template/` into the workspace root.
Rules:

- Never overwrite an existing file. If `CLAUDE.md` or wiki files already
  exist, merge the template content in marker-wrapped (`core`) where that
  makes sense, otherwise skip the file and report it.
- If a workspace `.claude/settings.json` already exists, back it up first,
  then merge the `permissions.ask` rules and hook entries from
  `template/.claude/settings.json` into it as discrete entries; record EACH as
  a `settings_entry` action (pointer + value). If none exists, copy the template file and record
  `file_created`.
- Record every created file/dir in the manifest as you go.

### 5. Global glue (core)

Into `~/.claude/CLAUDE.md` (create if missing; if pre-existing, back up per
the backup rule) inject ONE marker-wrapped block for module `core`, under
~25 lines, written calm (no MUST/NEVER, no incident history), containing:

1. **Length**: keep responses brief and plain; lead with the outcome, keep
   caveats short, skip filler. One short instruction is the lever for
   length on current models.
2. **Boundaries, each with its reason**: git writes go through the
   permission ask rules and the human runs them, so code work ends with
   "Ready to commit: <files>"; nothing is posted to the tracker or a PR
   unless the user asks in that turn; stop before anything hard to undo.
3. **How to work**: say which reading you took when a request is ambiguous
   and ask only when readings lead to different work; keep changes to what
   was asked, in the style of the surrounding code, and mention adjacent
   problems instead of fixing them; delegate to a subagent only for large
   independent tracks.

Leave out instructions to verify, double-check, plan, or use subagents to
verify: current models do these on their own, and Anthropic's prompting
guide for Opus 5 says such instructions cost quality and tokens.

Record as `block_injected` (path + module `core`).

### 6. Optional modules

For each selected module, in order:

1. Read `../../modules/<name>/MODULE.md`.
2. Run its Prerequisites checks. Unmet: SKIP the module with one clear report
   line ("skipped <name>: <missing prereq>"), never stall or retry-loop.
   Whenever a module is skipped (prereq unmet, or the user declines after
   seeing a prereq problem), append `{name, reason}` to `modules_skipped` in
   the manifest so `/os-doctor` reports a deliberate skip instead of a broken
   install.
3. Execute its Install section.
4. Run its Verify section.
5. Record every action in the manifest (`plugin_installed` for plugin
   installs, `settings_entry` / `block_injected` / `file_created` as
   applicable), and add the module name to `modules`.

Ask the user nothing per-module UNLESS the MODULE.md requires a user-supplied
value (e.g. a DB connection string).

### 7. Repo analysis

Scan workspace subdirectories (plus any repo paths the user declares). For
each repo detect tech + role from real signals: `package.json`, `*.csproj`,
`go.mod`, `pyproject.toml`, `Cargo.toml`, `composer.json`, framework
dependencies, git remotes. Infer seams (integration boundaries) from evidence:
generated API clients, shared package/DTO imports, OpenAPI/proto files, shared
DB migrations, message-bus config.

Draft, but DO NOT write yet:

- filled `os-config.yaml` (workspace name, repos with type/path/role/tech,
  seams with mechanism/contract/notes; all template examples deleted)
- `wiki/system-map.md`: repo-roles table + topology sketch + seams, EVERY
  claim evidence-tagged ✅ (file:line) / 🟡 inferred / ⬜ unknown
- one `wiki/repos/<name>.md` per repo from `wiki/repos/_TEMPLATE.md`
- one `wiki/seams/<name>.md` per inferred seam from `wiki/seams/_TEMPLATE.md`
- updated `wiki/index.md` (one line per page)

When the detected data store is not SQL-reachable (Firestore, DynamoDB, and
similar), leave `environments.dev.db.*` connections EMPTY with the reason
recorded (a config comment plus a wiki note), and report plainly that
`seed-test-data` (SQL-based) and the DB-reconcile half of `ticket-testing`
are inert until adapted for that store. Never fill in plausible-looking fake
values.

**Present the full draft in chat and WAIT for approval.** Only after the user
approves: write the files, record each in the manifest.

### 8. Ticket source

AskUserQuestion: Shortcut / Jira / Azure DevOps / Linear / GitHub Issues /
other. Write `workspace.ticket_source` and `workspace.ticket_prefix` into
`os-config.yaml`. Note which MCP server or CLI serves that source; if one is
configured, verify it responds (one cheap call). If missing or unreachable,
record a ⬜ in the wiki and move on - never stall here. Mention the optional
`workspace.ticket_exclusions` list in `os-config.yaml` for inherited
out-of-scope tickets, so `ticket-impact` never pulls them into a blast
radius.

Then make the tracker's write operations ask: list the MCP server's (or
CLI's) tools that create, update, comment, or delete, add each to
`permissions.ask` in `<workspace>/.claude/settings.json` (MCP tools by full
name, CLI writes as `Bash(<cli> <subcommand>:*)`), show the list before
writing it, and record each as a `settings_entry` action. Read tools stay
unprompted.

### 9. Smoke test

Run and report a pass/fail table:

- `bash .claude/hooks/drift-check.sh` executes without error
- `block-dangerous-git.sh` blocks a fake `git push --force` tool-call payload
  fed on stdin (expect a block), and allows a fake plain `git push` payload
  (non-force pushes pass the hook; they are gated by the `permissions.ask`
  rules instead)
- `jq '.permissions.ask' .claude/settings.json` lists the git write rules
  and the tracker write tools from step 8
- `ticket-impact-reminder.sh` returns its reminder for a fake Edit payload on
  a repo file and nothing for a second payload with the same `session_id`;
  `wiki-verify-reminder.sh` the same for a wiki page. Remove the marker files
  (`$TMPDIR/claude-hook-*-<test-session-id>`) afterwards
- each installed module's Verify section passes

If caveman was installed, its verify shows "pending fresh session" here;
report that as expected, not a failure.

### 10. Close

Write the first `wiki/log.md` entry:
`## [YYYY-MM-DD] restructure | os-init onboarding` + bullets (modules, files).
Print a summary: modules installed, manifest path, the pointer line
"run /os-doctor anytime to health-check, /os-remove to uninstall.", and one
more line: start a fresh session from the workspace root to activate the
scaffold hooks (and caveman if installed).
Never commit or push anything.
