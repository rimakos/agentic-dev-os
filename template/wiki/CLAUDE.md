# wiki: the work knowledge base

A knowledge base Claude maintains for this workspace, so each ticket costs less than the last.
Work only: personal content lives elsewhere. Start from `index.md` (one line per page) and follow
links; don't scan the tree.

## Layout

- `raw/`: sources as captured (ticket exports, payloads, PR feedback, meeting notes). Never edited.
- `system-map.md`: repo and seam topology. The only place topology lives.
- `repos/<repo>.md`, `seams/<seam>.md`: working knowledge per repo and integration boundary.
- `features/<ticket>-*.md`, `decisions/NNNN-*.md` (ADRs via `/goal`), `workflows/*.md`.
- `known-issues/`: working rules by topic. Read the one that matches the work.
- `log.md`: append-only, `## [YYYY-MM-DD] <op> | <title>`, op is ingest, query, lint, decision,
  feature or restructure.

## Conventions

- Frontmatter: `tags`, `date`, `status` (seed, active, stale).
- `[[wikilinks]]` inside the wiki; code spans for anything outside it.
- Tag factual claims ✅ confirmed (with file:line, row or payload), 🟡 inferred, ⬜ unknown. Keep ⬜
  for what the repos cannot answer (product calls, production-only behavior). These tags stay in
  the wiki and don't reach repo code, comments or commits.
- Evidence order: production data and payloads, then code, then docs. A grep that finds nothing
  only covers the paths and refs it searched.

## Operations

- Ingest (`/wiki-ingest`): source into `raw/`, update the pages it touches, `index.md`, then
  `log.md`. Flag contradictions with existing pages instead of overwriting them.
- Query: read `index.md`, follow links, answer with citations. File answers worth keeping.
- Lint (`/wiki-lint`): contradictions, stale claims, orphans. Propose fixes before applying.
- End of session: `/wrap`, which writes `log.md` last.
- Roll-off: when `log.md` passes about 600 lines or a month closes, move the oldest entries to
  `archives/log-YYYY-MM.md`. Archives are moved, never deleted.

## Adding a rule

A check a script can do belongs in a hook or gate, not here. A rule that will apply again goes
once, in the one known-issues page that owns the topic, with its reason and without the incident
story. Strengthen an existing rule before adding a near-duplicate.

## Precedence

`system-map.md` wins on topology; production evidence wins over the map (then fix the map). A
repo's own rules directory (`repo_local_os` in `os-config.yaml`) wins on that repo's conventions.
