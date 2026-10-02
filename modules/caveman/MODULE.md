# caveman

## What it does

Ultra-compressed communication mode (roughly 75% fewer tokens) that keeps full
technical accuracy. Levels: lite, full (default), ultra. Also ships cavecrew
subagents (investigator/builder/reviewer) whose output comes back compressed,
so long sessions burn less context.

## Recommendation

Off by default since 0.3.0. On Opus 5 and later, Anthropic's lever for response length is one
short instruction in CLAUDE.md, and the `core` block already carries one. Caveman's session
injection also compresses text that should read normally (drafts, PR comments). Install it only
if you want the terse mode on top.

## Prerequisites

- `node` on PATH (`node --version`) — the plugin's hooks run via node.

## Install

1. In Claude Code: `/plugin marketplace add JuliusBrussee/caveman`
2. `/plugin install caveman@caveman`
3. The plugin ships its own SessionStart hook (activate) and UserPromptSubmit
   hook (mode tracker). Normally the plugin registers them itself; if a new
   session shows no caveman activity, wire the two hooks into
   `~/.claude/settings.json` per the plugin's docs (both are node scripts).
4. Usage: `/caveman [lite|full|ultra]` to set the level; say "stop caveman"
   to turn it off. `/caveman-help` lists all commands.

## Verify

Immediately after install, the os-init smoke test and `/os-doctor` show a
"pending fresh session" warning for caveman. That is expected, not a fault:
the SessionStart hook has not run yet.

Confirmation is the next session: start one with a mode set and the
SessionStart hook announces `CAVEMAN MODE ACTIVE`. `/caveman-stats` shows real
token usage for the session.

## Remove

1. `/plugin uninstall caveman@caveman`
2. Delete `~/.claude/.caveman-active` if present.
3. If hooks were wired manually in install step 3, remove those entries from
   `~/.claude/settings.json`.
