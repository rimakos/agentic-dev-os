---
name: task-intake
description: Use at the start of a task to restate it, state assumptions, surface ambiguity, classify it, and define a verifiable done-criterion before any code is written. Standalone phase 1 of the operating-flow loop but works on its own. Triggers: /task-intake, "scope this task", "define done for this", "intake this task", "what are we actually doing".
---

# task-intake

## Purpose

Turn a raw ask into a scoped task with an explicit, verifiable done-criterion before any implementation starts. Kills silent assumptions and "should work" endings at the source.

## When to use

- `/task-intake`
- Start of any non-trivial task (or invoked by `operating-flow` as phase 1)
- "scope this task", "define done", "intake this"

## Inputs

**Required**: the user's ask, as given.
**Optional**: existing plan or spec (intake then validates instead of scoping from scratch).

## Workflow

1. **Restate** the task in one sentence. If your restatement and the ask could diverge, that's a sign of ambiguity.
2. **State assumptions.** Every interpretation you'd otherwise make silently goes on the table: target files, scope edges, what's explicitly OUT of scope.
3. **Ambiguity gate.** If two reasonable readings lead to different work, surface both and ask ONE question (multiple-choice preferred). Do not proceed on a guess. If unambiguous, proceed without asking.
4. **Classify**: question (deliverable = assessment, no changes) / change (deliverable = working code or file) / plan-execution (deliverable = plan completed with checkpoints).
5. **Define done.** One criterion that can pass or fail, checkable by tool or command, written before the first edit. Good: "test X fails now, passes after", "npm run build exits 0", "page renders the new field". Bad: "code is improved", "should work".
6. **Emit the intake block** (template below) and stop. Execution is a separate step or skill.

## Output template

```
Task: <one sentence>
Type: question | change | plan-execution
Assumptions: <bullets, include out-of-scope>
Done when: <verifiable criterion + the command/check that proves it>
```

## Hard rules

- Done-criterion is mandatory. No criterion, no implementation.
- One question max per ambiguity gate.
- Questions only for genuine forks; obvious defaults get applied and listed as assumptions instead.
- Stop after the intake block when run standalone.
- If this skill itself caused friction or saved a failure, append one line to `<workspace>/.claude/os-observations.md` (`date | model | task-intake | what`). Never edit skill files mid-session.

## Anti-patterns

| Don't | Do |
|---|---|
| "I'll figure out done as I go" | Criterion written before first edit |
| Ask 4 setup questions | Apply defaults, list as assumptions, ask only real forks |
| Restate the ask verbatim as "scope" | Restate in your own words to expose drift |
| Vague criterion ("works well") | Command + expected result |
