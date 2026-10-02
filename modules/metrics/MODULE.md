# metrics

## What it does

Self-measurement layer: TSVs tracking session health (corrections vs
self-caught issues), PR cycle time and how often each skill fires, plus a wiki
workflow page explaining the columns and the trend to watch. The wrap skill
appends one health row per session and a fire-rate snapshot once a day when
this module is installed. A skill with zero fires in 90 days is a candidate to
archive.

## Prerequisites

- The workspace has a `wiki/workflows/` directory (created by the base
  install).

## Install

1. `mkdir -p <workspace>/metrics`
2. Copy `modules/metrics/templates/system-health.tsv`,
   `pr-metrics.tsv`, `skill-fire-rate.tsv` and `skill-fire-rate.py` to
   `<workspace>/metrics/`. If a target TSV already exists, leave it (it holds
   accumulated data).
3. Copy `modules/metrics/templates/system-health.md` to
   `<workspace>/wiki/workflows/system-health.md` and set `date:` in its
   frontmatter to today's date.

## Verify

```
head -1 <workspace>/metrics/system-health.tsv
head -1 <workspace>/metrics/pr-metrics.tsv
cd <workspace> && python3 metrics/skill-fire-rate.py 7 | head -1
```
Each prints its tab-separated header row, and
`<workspace>/wiki/workflows/system-health.md` exists.

## Remove

1. Delete `<workspace>/wiki/workflows/system-health.md` and
   `<workspace>/metrics/skill-fire-rate.py`.
2. The TSVs contain accumulated data: ASK the user before deleting
   `<workspace>/metrics/system-health.tsv`, `pr-metrics.tsv` and
   `skill-fire-rate.tsv`. If they decline, leave them; wrap keys off each
   file's existence, so keeping a TSV keeps its appends.
