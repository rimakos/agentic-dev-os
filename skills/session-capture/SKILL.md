---
name: session-capture
description: Use at the end of a working session, after user feedback/corrections, or after any decision worth remembering. Writes feedback, decisions, and durable facts to the project's memory files immediately, then produces a final report that leads with the outcome. Standalone phase 6 of the operating-flow loop but works on its own. Triggers: /session-capture, "capture this session", "log what we learned", "close out", "write that down".
---

# session-capture

## Purpose

Nothing learned in a session evaporates. Feedback, decisions, and durable facts land in files before the final message, so no future session relearns them.

## When to use

- `/session-capture` or end of any working session
- Immediately when the user gives feedback, states a preference, or corrects you (do not wait for session end)
- Invoked by `operating-flow` as phase 6

## Where things go (canonical homes, no duplicates)

Two targets. Team-shareable knowledge goes to the workspace wiki; agent-personal learnings go to Claude auto-memory. If the project has a `/wrap` skill, prefer it for the wiki side.

| What | Where |
|---|---|
| Durable team facts (gotchas, conventions, domain truths, decisions + WHY) | the workspace wiki (`wiki/` pages, per the project's /wrap conventions) |
| Feedback, corrections, preferences, cross-session working notes | Claude auto-memory at `~/.claude/projects/<workspace-slug>/memory/` |

Auto-memory convention: files named `<type>_<snake_case_topic>.md`, type ∈ user | feedback | project | reference. YAML frontmatter with `name`, `description`, `metadata.type`. Feedback bodies follow: what happened / **Why:** / **How to apply:**. Append a one-line index entry to `MEMORY.md` for every new file.

One canonical home per fact. Link, don't copy. If a new learning contradicts an existing page, update that page too.

## Workflow

1. **Sweep the session**: feedback given? decisions made? durable facts surfaced? tasks left open?
2. **Write each item** to its canonical home per the table. Date every entry, newest first. Prefer updating an existing entry over creating a near-duplicate.
3. **Contradiction check**: does anything written contradict an existing wiki or memory page? Fix the older file.
4. **Open threads**: unfinished work worth resuming → note it where the project tracks work (ticket board, TODO file), not buried in a memory entry.
5. **Final report**: lead with the outcome (what happened / what was found), then supporting detail, then what was captured, then "Ready to commit: <files>" if anything changed. Never commit.

## Hard rules

- Capture happens BEFORE the final message, not as a promised follow-up.
- Feedback gets captured the moment it's given, mid-session, not batched to the end.
- Never write the same fact into two homes.
- Never commit or push the captured files.
- Stop after the final report.
- If this skill itself caused friction or saved a failure, append one line to `<workspace>/.claude/os-observations.md` (`date | model | session-capture | what`). Never edit skill files mid-session.

## Anti-patterns

| Don't | Do |
|---|---|
| "I'll remember that" (no file write) | Write it now, then apply it |
| Session summary only in chat | Chat summary + file capture |
| Duplicate a fact into wiki AND memory | One canonical home, link the other |
| Log the decision without the why | What was chosen AND why alternatives lost |
