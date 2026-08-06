# metrics

## What it does

Self-measurement layer: two TSVs tracking session health (corrections vs
self-caught issues) and PR cycle time, plus a wiki workflow page explaining
the columns and the trend to watch. The wrap skill appends one health row per
session when this module is installed.

## Prerequisites

- The workspace has a `wiki/workflows/` directory (created by the base
  install).

## Install

1. `mkdir -p <workspace>/metrics`
2. Copy `modules/metrics/templates/system-health.tsv` and
   `modules/metrics/templates/pr-metrics.tsv` to `<workspace>/metrics/`.
   If a target TSV already exists, leave it (it holds accumulated data).
3. Copy `modules/metrics/templates/system-health.md` to
   `<workspace>/wiki/workflows/system-health.md` and set `date:` in its
   frontmatter to today's date.

## Verify

```
head -1 <workspace>/metrics/system-health.tsv
head -1 <workspace>/metrics/pr-metrics.tsv
```
Each prints its tab-separated header row, and
`<workspace>/wiki/workflows/system-health.md` exists.

## Remove

1. Delete `<workspace>/wiki/workflows/system-health.md`.
2. The TSVs contain accumulated data: ASK the user before deleting
   `<workspace>/metrics/system-health.tsv` and
   `<workspace>/metrics/pr-metrics.tsv`. If they decline, leave them; wrap
   step 6 keys off the file's existence, so keeping the TSV keeps the row
   appends.
