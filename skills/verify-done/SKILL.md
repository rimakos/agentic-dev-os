---
name: verify-done
description: Use when implementation claims to be finished and before telling the user it's done. Runs the pre-defined done-criterion end-to-end against the real flow (not just typecheck), and reports faithfully with evidence. Standalone phase 5 of the operating-flow loop but works on its own. Triggers: /verify-done, "verify this is done", "prove it works", "check the done criterion", "is this actually finished".
---

# verify-done

## Purpose

Stand between "implementation finished" and "told the user it's done". Nothing is done until the criterion passed and the evidence is in the message.

## When to use

- `/verify-done`
- After any implementation, before reporting completion
- Invoked by `operating-flow` as phase 5

## Inputs

**Required**: the done-criterion (from `task-intake` or stated now; if none exists, write one first, then verify against it).
**Optional**: the diff or task list, to derive extra spot-checks.

## Workflow

1. **Recall the criterion.** Quote it. If none was defined, define one now from the original ask before proceeding (never verify against vibes).
2. **Run the real check.** Exercise the affected flow end-to-end: run the test, run the build, hit the endpoint, render the page. Typecheck/lint alone does not count when a runtime surface exists.
3. **Capture evidence.** Exact command + exact relevant output. Failures quoted verbatim, not paraphrased.
4. **On FAIL**: report it plainly with the output. Do not soften ("mostly works"), do not silently fix-and-retry without saying so. Fix, then re-run the full criterion, then report both the failure and the fix.
5. **On PASS**: state it without hedging, with the evidence line.
6. **Emit the verdict block** and stop.

## Output template

```
Criterion: <quoted>
Check run: <command / action>
Result: PASS | FAIL
Evidence: <exact output line(s)>
Skipped: <anything not verified, stated plainly, or "nothing">
```

## Hard rules

- No "should work", "seems fine", "likely passes". Ran it or it isn't verified.
- Failing output quoted exact.
- Skipped checks named, never implied as done.
- Never commit as part of verification.
- Stop after the verdict block when run standalone.
- If this skill itself caused friction or saved a failure, append one line to `<workspace>/.claude/os-observations.md` (`date | model | verify-done | what`). Never edit skill files mid-session.

## Anti-patterns

| Don't | Do |
|---|---|
| Typecheck passes → "done" | Drive the actual flow the change affects |
| Paraphrase the error | Quote it verbatim |
| Retry silently until green | Report the failure AND the fix |
| Verify what's easy instead of the criterion | Verify the criterion; list the rest as skipped |
