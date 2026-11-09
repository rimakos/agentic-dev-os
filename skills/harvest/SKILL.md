---
name: harvest
description: Go back through your past Claude Code sessions in this repo and file what the next person would otherwise rediscover (corrections, gotchas, business rules, decisions, review patterns) into the repo's knowledge base, the way its /wrap does. Shows a list first and writes only the rows you pick. Repo-memory mode. Triggers on /harvest, "fill the knowledge base from my past sessions", "mine my old chats". Never commits.
---

# harvest

Two phases. Write nothing until the user picks rows.

## Sources

- **Sessions:** the data folder is the one whose `hooks/wrap_check.py` the repo's
  `.claude/settings.local.json` runs; `os-config.yaml` there gives `memory.root` and
  `review.lessons`. From the repo root run
  `python3 <data>/harvest_extract.py --out <data>/harvest/sessions.md` and read the result: what the
  user said in each session, with the files changed. For a moment worth keeping, open the `.jsonl`
  named in that session's heading (under `~/.claude/projects/`) and read the turns around it. Many
  sessions: split them across subagents by date range.
- **An earlier agentic OS** on this machine, if setup reported one: its `index.md`, `wiki/`,
  `decisions/` and `known-issues/`. What is about this repo is a source like the sessions. Leave that
  folder as it is.

## Look for

1. Corrections: the user said Claude was wrong, or a doc, skill or rule file said one thing and the
   system did another.
2. Gotchas that cost time: a build, tool or version quirk, a step that failed and why.
3. Business logic and rules the user explained that are in no doc.
4. Decisions someone will later ask "why this?" about.
5. Review patterns: something a reviewer flagged that a diff should be checked for next time.
6. The user's preferences in how they work with Claude.

## Phase 1: the list

Run `git fetch`. One table, newest first:

| # | What (one sentence) | Kind (1-6) | Session date | Where it goes | Still true today? |

Where it goes, following the knowledge base's own README and the repo's `/wrap`: 1 to 3 as a page in
`memory.root` (or a fix to the page or doc that covers it); 4 as the repo's decision record (an ADR,
a decisions file); 5 as one line in `review.lessons` with the PR number; 6 into Claude's auto memory,
never the repo. Check each row against the current code now and mark it ✅ checked, 🟡 inferred or ⬜
cannot check from here. Leave out what is already covered on `origin/main` (say "already covered:
N"), one-off chatter, and anything no longer true. Stop and wait for the pick.

## Phase 2: the rows picked

Write them exactly as the repo's `/wrap` does: page shape, evidence tags, the index line, a fix to any
doc the fact corrects. Never copy chat text, tokens, keys, personal paths or client data into the
repo. Run the repo's leak or client-safe check on every file you changed. Do not commit. End with
`Ready to commit: <files>`.

One person harvests at a time: a teammate's harvest goes after they pull the first one's pages.
