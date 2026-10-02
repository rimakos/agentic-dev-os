---
name: operating-flow
description: Master execution loop. Use at the START of any non-trivial task (multi-step work, code change, plan execution, anything touching 2+ files or needing verification) so the task runs with the standard structure - intake, skill check, define done, subagent-driven execution, drift check, verify, capture. Skip for trivial asks (single factual question, one-line fix, pure lookup). Triggers: /operating-flow, "run this the standard way", "execute with structure", "follow the flow".
---

# operating-flow

## Purpose

Encode one execution loop so every model and session works the same way: no silent assumptions, plan before code, delegation over context bloat, verification before "done", memory capture before close. This is a router: each phase is also a standalone skill; this master enforces the order.

## Sizing gate (decide before anything else, silently)

Classify the ask into one of three sizes. Pick the smallest that fits; overhead must stay proportional to the task.

**Trivial → no loop.** Single question, lookup, or obvious one-line change needing no verification beyond reading the diff. Answer directly, say nothing about the skill.

**Small → light path (~200 tokens overhead).** One file, clear ask, but the change has runtime behavior worth checking. Skip subagents, skip the intake block. Inline: state the done-check in one line, make the change, run the check, report with one evidence line. No closing block, just "verified: <command> → <result>".

**Non-trivial → full loop.** Multi-step, 2+ files, plan execution, ambiguity, or anything irreversible-adjacent. Run all phases below.

**User overrides beat the gate, both directions:**
- "quick" / "no flow" / "skip the flow" in the ask → treat as trivial, no loop, no light path.
- "/operating-flow" or "full flow" → run the full loop regardless of size.

If mid-task the size grows (second file appears, hidden ambiguity, a test is needed), upgrade one tier and say so in one line.

## The loop

Run the phases in order. Each phase has a standalone skill; invoke it if available, otherwise follow the inline summary.

### 1. Intake and define done → `task-intake`

Restate the task in one sentence. State assumptions explicitly. If genuinely ambiguous, surface the interpretations and ask ONE question; do not run with a guess. Classify: question / change / plan-execution. Then define the done-criterion BEFORE touching code: a check that can pass or fail ("failing test then green", "build passes", "file X contains Y", "flow Z works end-to-end").

Plan-execution with a spec/plan → run `spec-gate` before any implementation edit: independent critic grades the spec (blocking, iterate to PASS), holdout scenarios written now and hidden from the implementer.

### 2. Skill check

Match the task to existing skills before any action, including clarifying questions:

- Creative/feature work → brainstorming skill first
- Bug/unexpected behavior → systematic-debugging first
- Multi-step with spec → writing-plans first
- Domain skills (docx, pdf, frontend, etc.) after the process skill

If a skill plausibly applies, invoke it. Process skills set the approach; implementation skills carry it out.

### 3. Execute → `subagent-execute`

Main context orchestrates, reviews, tracks state. Implementation goes to subagents:

- Coupled tasks (one required for another) → ONE subagent together
- Independent tasks → separate subagents, dispatched in parallel
- Surgical changes only: every changed line traces to the request. No adjacent refactors, no speculative features. Simplicity first: if 200 lines could be 50, write 50.

### 4. Drift check (after EVERY task or group)

Did the result match the plan? Did completing it change assumptions downstream tasks rely on? If yes: update the plan and downstream tasks before continuing. Never let a later task break on a stale assumption.

### 5. Verify → `verify-done`

Run the done-criterion from step 1. Exercise the real flow, not just typecheck. Report faithfully: failures quoted exact, skipped steps named, no hedging on success ("done and verified" only when it is). If `spec-gate` wrote a holdout file for this task, dispatch a fresh subagent (spec + holdout + built artifact only, none of the build context) to evaluate it — the implementer never self-grades the holdout.

### 6. Capture → `session-capture`

Feedback, preferences, corrections → memory files immediately (team wiki or Claude auto-memory, per `session-capture`). Decisions with a why → the decisions log. Then the final report: lead with the outcome, supporting detail after.

## Hard rules (never relax)

- NEVER `git add` / `git commit` / `git push`. End with "Ready to commit: <files>".
- Stop before any client-facing, irreversible, or external-publishing action.
- Ask one question at a time, multiple-choice when possible.
- Don't re-ask decisions already made in the conversation.
- Targeted context reads only; no repo-wide scans for "thoroughness".

## Closing block (end of every loop run)

```
Done-criterion: <criterion> → PASS/FAIL <evidence>
Drift: <none | what changed and how plan was updated>
Captured: <learnings/decisions written, or "nothing durable">
Ready to commit: <files>
```

## Self-learning (observe always, edit only with approval)

Two roles, never mixed:

**Observe (every model, every session, ~free):** when the loop itself caused friction
(a phase wasted tokens, a rule was ambiguous, auto-fire missed, a split skill proved
useless) or clearly prevented a failure, append ONE line to
`<workspace>/.claude/os-observations.md`: `YYYY-MM-DD | model | phase | what happened`. One line max. Never skip logging a miss.

**Fix (gated):** running sessions NEVER edit these SKILL.md files. When
`os-observations.md` passes ~20 entries or a month elapses, the user triggers a
review ("/flow-review"): a strong model reads the log, proposes concrete skill edits
or deletions (pruning unused splits counts as improvement), applies them ONLY after
user approval, then archives the processed entries below a `## Reviewed YYYY-MM-DD`
marker. If models drift past the flow, the os-init wizard can add a SessionStart
nudge hook; the plugin ships no escalation files.

## Anti-patterns

| Don't | Do |
|---|---|
| Code first, define done later | Done-criterion before first edit |
| Rewrite this skill mid-session because it "could be better" | One line in os-observations.md, fix at review |
| Implement everything in main context | Delegate to subagents, orchestrate |
| Assume silently when ambiguous | Surface interpretations, ask one question |
| "Should work" as verification | Run the criterion, quote the evidence |
| End session without capture | Learnings/decisions written before final report |
| Run the full loop on a one-liner | Use the triviality escape hatch |
| Grade your own spec, verify against scenarios you wrote and read | `spec-gate`: independent critic + holdout evaluated by a fresh agent |
