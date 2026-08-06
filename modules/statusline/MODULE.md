# statusline

## What it does

Installs ctxline-claude (github.com/MithunWijayasiri/ctxline-claude), a status
line for Claude Code that shows model, context usage, and session info at the
bottom of the terminal.

## Prerequisites

- `node` on PATH (`node --version`).
- `~/.claude/settings.json` must NOT already contain a `statusLine` key. If it
  does, skip this module — never overwrite an existing status line.

## Install

1. Download the script:
   ```
   mkdir -p ~/.claude/hooks
   curl -fsSL https://raw.githubusercontent.com/MithunWijayasiri/ctxline-claude/main/statusline.js -o ~/.claude/hooks/statusline.js
   ```
2. Add to `~/.claude/settings.json` (top level):
   ```json
   "statusLine": {"type": "command", "command": "node ~/.claude/hooks/statusline.js"}
   ```

## Verify

Start a new Claude Code session: a status line renders at the bottom of the
terminal. If it stays blank, run
`node ~/.claude/hooks/statusline.js` manually to see the error.

## Remove

1. Delete the `statusLine` key from `~/.claude/settings.json`.
2. Delete `~/.claude/hooks/statusline.js`.
