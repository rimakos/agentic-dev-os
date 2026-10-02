---
name: spec-gate
description: Blocking spec quality gate + holdout scenario authoring, run BEFORE implementing any feature that has a spec or plan. An independent critic grades the spec (PASS/FAIL with an ambiguity list); acceptance scenarios are written now and hidden from the implementer, then evaluated by a fresh agent after the build. Triggers: /spec-gate, "grade this spec", "gate zero", "write the holdout", after writing any plan and before writing code.
---

# spec-gate

## Purpose

Two failure modes this kills: (1) implementing against a vague spec and finding
the ambiguity mid-build, (2) verifying a feature against checks the implementer
wrote and read, so the build overfits to its own test. Mechanism ported from an
enterprise "Dark Factory" pipeline: grade the spec before code (blocking), and
keep acceptance scenarios outside the implementer's context until the end.

## When to use

- After writing a plan/spec for a feature, BEFORE the first implementation edit.
- Invoked by `operating-flow` phase 1 for plan-execution tasks with a spec.
- Skip for bug fixes, refactors, and tasks with no spec (the done-criterion
  from `task-intake` is enough there).

## Part 1 — Critic grade (blocking)

Dispatch ONE subagent as an adversarial spec critic. It gets the spec text and
the referenced architecture/context docs, nothing else. It must return:

- **Verdict: PASS / FAIL.**
- **Rubric** (each pass/fail): behavioral contract stated as "when X, the
  system does Y"; explicit NON-behaviors (what this feature deliberately does
  not do); integration boundaries named (what it touches, what it must not);
  references to real architecture docs/files (a spec citing nothing fails);
  constraints testable, not vibes ("fast" fails, "p95 < 300ms" passes).
- **Ambiguity list**: every point where two reasonable engineers would build
  different things.

FAIL → fix the SPEC (never "interpret around it"), re-grade. Iterate to PASS.
Then show the user the verdict + ambiguity list and get their go-ahead.
**Writing any implementation file before PASS is a process violation, even a
one-liner.**

## Part 2 — Holdout scenarios (write now, hide until the end)

While grading runs, write 3–8 concrete acceptance scenarios: given/when/then,
real inputs, observable outcomes. Include at least one negative scenario
(what must NOT happen).

- Save them OUTSIDE the repo and outside the implementing context:
  `<workspace>/holdouts/<feature-slug>.md` (workspace = the OS/wiki dir, never
  the code repo).
- The implementing session/agents MUST NOT read this file. If you are
  orchestrating and already know the scenarios, delegate implementation to
  subagents that never see them.

## Part 3 — Holdout evaluation (after implementation, from verify-done)

Dispatch a FRESH subagent with ONLY: the spec, the holdout file, and access to
the built artifact (running app, test command, rendered output). It runs each
scenario and returns PASS/FAIL per scenario with evidence. The implementer
never self-grades the holdout. Record the result next to the holdout file
(`<feature-slug>-results.md`) and report failures verbatim.

## Output template

```
Spec grade: PASS/FAIL (round N)
Ambiguities: <list or "none">
Holdout: <path>, <N> scenarios (contents not shown to implementer)
User go-ahead: pending
```

## Hard rules

- No implementation edits before the critic says PASS and the user approves.
- On gate FAIL after implementation exists: fix the spec first, then the code.
- Holdout file is never pasted into the implementing context.
- Friction or a save from this skill → one line in
  `<workspace>/.claude/os-observations.md`. Never edit skill files mid-session.

## Anti-patterns

| Don't | Do |
|---|---|
| Grade your own spec inline | Independent critic subagent, spec + docs only |
| "The spec is short, skip the gate" | Short specs hide the most ambiguity |
| Keep scenarios in the plan file | Separate holdout file outside the repo |
| Evaluate the holdout yourself | Fresh subagent that saw none of the build |
| Patch code to dodge a spec mismatch | Fix the spec, escalate, then the code |
