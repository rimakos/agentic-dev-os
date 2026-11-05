---
name: pr-review
description: Code review of a branch or PR against the repo's own rules, its knowledge base and what its reviewers have flagged before, with every finding validated (precedent, feasibility, significance, proof) before it is reported. Routes to the repo's specialist reviewers instead of repeating them. Usage /pr-review (current branch against the default branch), /pr-review <PR id or URL>, or /pr-review <base-sha> <head-sha>. Triggers on /pr-review, "review my branch", "review this PR", "code review before I open the PR". Read-only: never edits, posts or commits.
---

# pr-review

A reviewer that knows this repo: its written rules, what the team has already learned, and the kinds
of things its reviewers catch. It reports few findings, each one checked, and says which of the repo's
own reviewers still has to run.

## Inputs

- Nothing: the current branch against the default branch (`origin/main` or what `git remote show
  origin` names).
- A PR id or URL: fetch the PR's head and target commits (`git fetch origin <sha>`, or the host's
  CLI). Review by commit, never the working tree.
- Two commits: review `<base>...<head>`.

## 1. Load what this repo expects

Read these before the diff. Skip any that does not exist.

- **Rules:** the repo's `CLAUDE.md` and what it imports (`AGENTS.md`), `CONTRIBUTING.md` (its pre-PR
  checklist and review section), and any doc those point to for an area the diff touches (module
  boundaries, threat model, style guide). Each hard rule is a checklist row in step 4.
- **Knowledge:** the memory index (`memory.root` in `os-config.yaml`, for example `docs/knowledge/`,
  or the workspace `wiki/index.md`). Open the pages for the areas the diff touches.
- **Reviewer history:** `review.lessons` in `os-config.yaml`, the patterns from past review threads.
  Treat each as a question to ask of this diff, not a finding.
- **Specialist reviewers:** list `.claude/agents/*.md` and the review skills in `.claude/skills/`
  with their descriptions. Note which ones this diff triggers (a signing reviewer, a spec benchmark).
  Do not do their job; name them in the report.

## 2. The diff

`git diff <base>...<head> --name-only`, then the diff itself. Leave out generated files the repo marks
as generated. Lockfiles and checksum files stay in: review them for completeness, not line by line.
Find defects from the diff. Read a whole file only to settle a contract the diff cannot show, or to
compare shape with its closest sibling (lens 7).

## 3. The repo's own checks

Run the cheap checks the repo's pre-PR checklist names (a docs check, a leak check, format and lint
tasks) on the head commit, in a throwaway worktree (`git worktree add <scratch> --detach <head>`,
removed at the end). Report each as passed, failed (with the output line) or not run (why). A failed
check is a finding without further proof.

## 4. Review lenses

1. **Logic.** Wrong conditions, unhandled edge cases, a counter or total that includes the wrong
   thing, state updated on one path and not its twin.
2. **Hard rules.** Each rule from step 1 the diff touches: pass, or the line that breaks it.
3. **Clean state.** Would this work from a fresh clone, an empty cache or build home, the other
   supported OS, and only the committed files? Generated outputs (lockfiles, checksums, tables,
   reports) must be reproducible from what is committed.
4. **Claims against sources.** Every number, count, quoted contract and "X is still complete" in a
   doc, ADR, README, docstring or PR text matches what it cites. Recount and re-read the source.
5. **Docs the change makes wrong.** READMEs, docstrings, the knowledge base and the repo's own
   instructions that describe the old behaviour.
6. **Tests with the behaviour.** New behaviour arrives with tests that assert the outcome.
7. **Same rule, every sibling.** A setting, guard or block added in one place (one convention plugin,
   one handler, one list) and missing from the sibling that needs it. Compare with the closest
   existing file that does the same job.
8. **Reviewer history.** Each lesson from step 1 that applies.

## 5. Keep only what survives

Every candidate passes all four, or is dropped. Never report a finding and then retract it.

1. **Precedent.** If the same pattern is accepted in analogous code, drop it.
2. **Feasibility.** A suggested fix must work with the real types, configs and tools. Find one that
   does or drop the finding.
3. **Significance.** Would this team's reviewer comment on it? Drop pure style with no rule behind it
   and risks that need several unlikely things at once.
4. **Proof.** Run the cheapest thing that settles it, in the worktree: an exhaustive grep for an
   absence claim, a recount for a number, the script on the committed files, one test, or the build
   from an empty cache. A finding you could only read is `suspected`; say so. Never install tools or
   change tracked files to make a run work; say what could not run.

## 6. Report

```
Review: <branch or PR> at <head sha, short>   Verdict: approve | approve with suggestions | changes needed

Checks:     <check>: passed | failed (<line>) | not run (<why>)
Blocker:    <file:line> what is wrong, the proof (rung and result), the fix
Should-fix: ...
Minor:      ...
Still to run: <specialist reviewer or skill> because <trigger>, or none
For the knowledge base: <a fact this review confirmed that the next person would rediscover>, or none
```

At most a handful of findings, most important first. The `For the knowledge base` line is for
`/wrap` to file; this skill writes nothing.
