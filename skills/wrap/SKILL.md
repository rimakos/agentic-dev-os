---
name: wrap
description: End-of-session closer for workspace work. Files what the session learned into the wiki, or in repo-memory mode into the repo's own knowledge base, records the health metrics, and appends the log. Triggers on /wrap, "log this", "wrap up", "close the session", "store what we learned".
---

# wrap

Run these in order. `wiki/log.md` is written last because the SessionStart drift check compares
file times against it. The wiki schema is `wiki/CLAUDE.md`.

1. **Corrections.** List the moments the user corrected you, a page or skill misled you, or an
   assumption broke. For each, decide where it belongs:
   - a check a script can do: add it to a hook or gate rather than prose;
   - a rule that will apply again: state it once, in the one `wiki/known-issues/` page that owns
     the topic, with its reason and without the incident story;
   - a one-off that won't recur: note it in the log only.
   Prefer strengthening an existing rule over adding a near-duplicate.
2. **Decision.** If the session made a non-obvious choice ("why this, not the alternative"), run
   `/goal` for an ADR; otherwise skip with a one-line reason. Personal-project decisions don't go
   here.
3. **Facts.** New durable knowledge (a verified command, a gotcha, a ⬜ to ✅ promotion, a
   contradiction) goes on the right `wiki/repos/` or `wiki/seams/` page with its evidence tag. A
   large source (PR feedback, payload, post-mortem) goes to `wiki/raw/`, noted for `/wiki-ingest`.
4. **Index.** Update `wiki/index.md` for new or repurposed pages.
5. **Health row.** Only if `metrics/system-health.tsv` exists: append one row with today's date,
   op `wrap`, corrections the user flagged, mistakes you caught before they did, 1 if an ADR was
   written, skill or memory files patched, and pages touched in steps 3 and 4. Self-caught rising
   relative to user corrections is the signal that the setup is improving.
6. **Fire rate.** Only if `metrics/skill-fire-rate.py` exists, and once per day: if today's date
   is not yet in `metrics/skill-fire-rate.tsv`, run
   `python3 metrics/skill-fire-rate.py 90 | tail -n +2 >> metrics/skill-fire-rate.tsv`.
7. **Log.** Append `## [YYYY-MM-DD] <op> | <session title>` with 2 to 4 bullets (what changed,
   which pages). If nothing changed, one bullet saying why, so the drift check resets.

## Repo-memory mode

Use this section instead of the steps above when the repo's `.claude/settings.local.json` runs
`hooks/wrap_check.py` from a data folder outside the repo (its `os-config.yaml` says
`memory.mode: repo`). If the repo has its own wrap command (`.claude/commands/wrap.md` or
`.claude/skills/wrap/`), run that one and stop here. Otherwise the repo's knowledge base is the
only memory and the repo's own rules decide where a fact goes:

1. **Read the repo's rules for documents.** Its `CLAUDE.md` (which document changes when, where
   facts live, size limits) and the README of `memory.root`. They win over anything here.
2. **Corrections.** As step 1 above, but a rule that will apply again goes into the file the repo
   names for rules, inside its size limit. A reviewer's comment that would apply to other diffs
   becomes one line in `review.lessons` in the data folder, phrased as a question.
3. **Facts.** For each thing the session confirmed by running something, pick the first home the
   repo's rules give it (a runbook, a decision record, a catalog, a rule file). A knowledge page
   only when none fits. Before writing, read the index at `origin/<default branch>` and update a
   teammate's page on the same subject instead of adding one. Add or correct the index line.
   Most sessions produce nothing here: say so and write nothing.
4. **Checks.** Run the repo's own checks for the files you wrote (a size or link test its rules
   name) and fix what they report. Nothing about the session itself goes into the repo: no log,
   no metrics, no mention of this skill.
5. **Health row.** Append to `<data>/metrics/system-health.tsv` (create it with the header
   `date op user_correction self_caught adr skill_patched pages_touched`, tab-separated).

## Output

One short line per step: what was written where, or "skipped: <reason>". If the wiki is
git-tracked, end with "Ready to commit: <files>". No git actions.
