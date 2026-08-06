---
tags: [workflow, metrics]
date:
status: active
---

# system-health metrics

One row per session close (`/wrap` step 6), appended to
`metrics/system-health.tsv`. Answers one question: is the OS learning, or are
you correcting the same mistakes every week?

## Columns

| column | meaning |
|--------|---------|
| `date` | session date, YYYY-MM-DD |
| `op` | what appended the row (`wrap`) |
| `user_correction` | times the user had to correct the agent this session |
| `self_caught` | issues the agent caught itself before the user did |
| `adr` | 0/1: an ADR was written this session |
| `skill_patched` | 0/1: a skill/workflow/schema was patched this session |
| `pages_touched` | wiki pages created or updated this session |

## The metric

`self_caught` rising while `user_correction` falls means the captured rules
are doing their job. Flat `user_correction` with zero `skill_patched` means
corrections are happening but nothing is being patched: the failure-to-patch
rule is being skipped.

## When rows get appended

Wrap step 6, one row per session, just before the final log write. Only when
`metrics/system-health.tsv` exists; sessions without a wrap get no row.

## Monthly eyeball

Once a month, scan the last ~20 rows:

```
tail -20 metrics/system-health.tsv | column -t -s$'\t'
```

Look for the trend, not single rows. Repeated `user_correction` spikes with
`skill_patched` at 0 name the page to fix. `metrics/pr-metrics.tsv` sits
alongside for per-PR cycle tracking (filled manually or by cron).
