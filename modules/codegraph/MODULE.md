# codegraph

## What it does

CodeGraph builds a semantic knowledge graph of the codebase so the agent gets
instant symbol lookups (search, callers, callees, impact) instead of scanning
files. Two hooks keep the graph in sync as files change.

## Prerequisites

- `codegraph` binary on PATH: `which codegraph`. The binary is distributed
  privately; there is nothing to download here. There is NO Homebrew formula,
  and the npm package named `codegraph` is an unrelated name-squat with no
  `bin` entry: do NOT `npm install` it.
- If the binary is not already on PATH, answer no to this module and have the
  wizard record the skip in the manifest's `modules_skipped` with the reason.
  Installing later is small (a `codegraph init`, two hooks, seven permission
  entries) once someone hands you the real binary.

## Install

1. In the workspace root: `codegraph init -i` (builds `.codegraph/`).
2. Merge into `~/.claude/settings.json` hooks (never drop existing entries).

   `hooks.PostToolUse`:
   ```json
   {"matcher": "Edit|Write", "hooks": [{"type": "command", "command": "codegraph mark-dirty", "async": true}]}
   ```
   `hooks.Stop`:
   ```json
   {"matcher": ".*", "hooks": [{"type": "command", "command": "codegraph sync-if-dirty"}]}
   ```
3. Add to `permissions.allow` in `~/.claude/settings.json`:
   ```json
   "mcp__codegraph__codegraph_search",
   "mcp__codegraph__codegraph_context",
   "mcp__codegraph__codegraph_callers",
   "mcp__codegraph__codegraph_callees",
   "mcp__codegraph__codegraph_impact",
   "mcp__codegraph__codegraph_node",
   "mcp__codegraph__codegraph_status"
   ```
4. Append to `~/.claude/CLAUDE.md`:

   ```markdown
   <!-- AGENTIC-DEV-OS:BEGIN codegraph -->
   ## CodeGraph

   CodeGraph builds a semantic knowledge graph of codebases for faster code
   exploration. If `.codegraph/` exists in the project, use these tools for
   instant lookups instead of scanning files:

   | Tool | Use For |
   |------|---------|
   | `codegraph_search` | Find symbols by name (functions, classes, types) |
   | `codegraph_context` | Get relevant code context for a task |
   | `codegraph_callers` | Find what calls a function |
   | `codegraph_callees` | Find what a function calls |
   | `codegraph_impact` | See what's affected by changing a symbol |
   | `codegraph_node` | Get details + source code for a symbol |

   - Use `codegraph_search` instead of grep for finding symbols.
   - Use `codegraph_callers`/`codegraph_callees` to trace code flow.
   - Use `codegraph_impact` before making changes to see what's affected.
   - When spawning Explore agents in a codegraph-enabled project, tell them
     to use codegraph tools too.

   If `.codegraph/` does NOT exist, fall back to normal grep/glob exploration.
   <!-- AGENTIC-DEV-OS:END codegraph -->
   ```

## Verify

- `.codegraph/` exists in the workspace root.
- In a session, the `codegraph_status` MCP tool
  (`mcp__codegraph__codegraph_status`) responds with graph status.

## Remove

1. Remove the `codegraph mark-dirty` (PostToolUse) and `codegraph
   sync-if-dirty` (Stop) hook entries from `~/.claude/settings.json`.
2. Remove the seven `mcp__codegraph__*` entries from `permissions.allow`.
3. Strip the `AGENTIC-DEV-OS:BEGIN codegraph` / `END codegraph` block from
   `~/.claude/CLAUDE.md`.
4. Optionally delete `.codegraph/` in the workspace (ask first; it is cheap
   to rebuild with `codegraph init -i`).
