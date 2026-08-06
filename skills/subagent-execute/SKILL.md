---
name: subagent-execute
description: Use when executing a written plan or any multi-task implementation. Delegates the actual implementation to subagents, groups coupled tasks into one agent, parallelizes independent ones, keeps the main context clean for orchestration, and drift-checks after every task group. Standalone phase 3 of the operating-flow loop but works on its own. Triggers: /subagent-execute, "execute the plan", "delegate this work", "run these tasks via subagents".
---

# subagent-execute

## Purpose

Execute multi-task work without burning the main context on implementation detail. Main agent = orchestrator, reviewer, state tracker. Subagents = hands.

## When to use

- `/subagent-execute` with a plan or task list
- Executing any written implementation plan (default mode, do not ask which mode)
- Invoked by `operating-flow` as phase 3

## Inputs

**Required**: a plan, spec, or explicit task list.
**Optional**: done-criterion from `task-intake` (passed to the final verification).

## Workflow

1. **Partition by coupling.** Tasks where one is required for another to work, or that touch the same files → ONE subagent, run together. Tasks independent of everything else → one subagent each.
2. **Dispatch.** Independent subagents launch in parallel (single message, multiple Agent calls). Each prompt is self-contained: the task, the relevant file paths, the constraints (surgical changes, match existing style, no commits), and what to return (a diff summary, not file dumps).
3. **Review each result** as it lands. Check the diff against the plan, not just "did it run".
4. **Drift check after every task/group.** Two questions: (a) did the result deviate from the plan? (b) did completing it change assumptions any remaining task relies on? If either yes: update the plan and downstream task prompts BEFORE dispatching the next one.
5. **Track state** in the main context: done / in-flight / blocked per task. Never lose the list.
6. **Hand off to verification** (run the done-criterion, or invoke `verify-done`) once all tasks land.

## Constraints passed to every subagent

- Surgical changes: every changed line traces to its task. No adjacent refactors, no reformatting, no speculative flexibility.
- Simplicity first: minimum code that solves the actual problem.
- Match existing style, comment density, naming.
- NEVER commit or push.
- Report failures exactly; don't paper over.

## Hard rules

- Main context never implements multi-file work itself when subagents are available; it orchestrates.
- No skipped drift checks, even when a task "obviously" succeeded.
- Coupled tasks never split across parallel agents (merge conflicts, broken intermediate states).
- Stop after all tasks reviewed + verification handoff. No auto-commit.
- If this skill itself caused friction or saved a failure, append one line to `<workspace>/.claude/os-observations.md` (`date | model | subagent-execute | what`). Never edit skill files mid-session.

## Anti-patterns

| Don't | Do |
|---|---|
| Implement everything inline "to save time" | Delegate; keep orchestration context clean |
| One giant subagent for the whole plan | Partition by coupling |
| Parallelize tasks touching the same file | Same file = same subagent |
| Dispatch next task without drift check | Check plan assumptions after every group |
| Trust "task complete" claims | Review the actual diff against the plan |
