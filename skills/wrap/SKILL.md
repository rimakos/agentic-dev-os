---
name: wrap
description: End-of-session closer for workspace work. Files what the session learned into the wiki, records the health metrics, and appends the log. Triggers on /wrap, "log this", "wrap up", "close the session", "store what we learned".
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

## Output

One short line per step: what was written where, or "skipped: <reason>". If the wiki is
git-tracked, end with "Ready to commit: <files>". No git actions.
