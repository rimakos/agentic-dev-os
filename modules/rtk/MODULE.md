# rtk

## What it does

RTK ("Rust Token Killer") is a token-optimized CLI proxy. A PreToolUse hook
rewrites common Bash commands (`git status` becomes `rtk git status`) so their
output is compacted before it reaches the model, saving 60-90% of tokens on
routine dev operations.

## Prerequisites

- Homebrew, then install the binary (source: github.com/rtk-ai/rtk). Check
  which formula brew resolves first:
  ```
  brew info rtk
  ```
  The description must read as a CLI proxy that minimizes LLM token
  consumption (homepage rtk-ai.app, from homebrew-core). If it describes
  anything else, brew resolved a different `rtk`; follow the install
  instructions in the rtk-ai/rtk README instead. Then:
  ```
  brew install rtk
  ```
- Name-collision check: crates.io and npm both carry an unrelated `rtk`
  (Rust Type Kit). Verify you have the right binary:
  ```
  rtk gain
  ```
  Must print token-savings analytics, not "command not found" or an unknown
  subcommand. `which rtk` shows which binary you got.

## Install

1. Merge this entry into the `hooks.PreToolUse` array of
   `~/.claude/settings.json` (create the file or array if missing; never drop
   existing entries):
   ```json
   {"matcher": "Bash", "hooks": [{"type": "command", "command": "rtk hook claude"}]}
   ```
2. Copy `modules/rtk/RTK.md` to `~/.claude/RTK.md`. If a `~/.claude/RTK.md`
   already exists, leave it in place and record `"rtk_md_created": false` for
   this module in `<workspace>/.claude/os-manifest.json`; otherwise record
   `true`.
3. Append to `~/.claude/CLAUDE.md`:
   ```
   <!-- AGENTIC-DEV-OS:BEGIN rtk -->
   @RTK.md
   <!-- AGENTIC-DEV-OS:END rtk -->
   ```
4. Add to `permissions.allow` in `<workspace>/.claude/settings.json`:
   ```json
   "Bash(rtk git *)",
   "Bash(rtk ls *)",
   "Bash(rtk find *)",
   "Bash(rtk grep *)"
   ```
5. Append the content of `modules/rtk/staleness-rules.md` to the verification
   section of the workspace wiki `CLAUDE.md`, wrapped in the same markers:
   ```
   <!-- AGENTIC-DEV-OS:BEGIN rtk -->
   ...staleness-rules.md content...
   <!-- AGENTIC-DEV-OS:END rtk -->
   ```

## Verify

```
rtk hook check "git status"
```
Expected output: `rtk git status`.

## Remove

1. Remove the `rtk hook claude` entry from `hooks.PreToolUse` in
   `~/.claude/settings.json`.
2. Remove the four `Bash(rtk ...)` entries from `permissions.allow` in
   `<workspace>/.claude/settings.json`.
3. Strip the `AGENTIC-DEV-OS:BEGIN rtk` / `END rtk` blocks from
   `~/.claude/CLAUDE.md` and from the workspace wiki `CLAUDE.md`.
4. Delete `~/.claude/RTK.md` only if the manifest records `rtk_md_created: true`.
