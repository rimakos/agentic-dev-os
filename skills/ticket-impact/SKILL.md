---
name: ticket-impact
description: Use BEFORE writing a plan or any code on a new ticket. Produces a compact impact-aware pre-plan and Implementation Handoff so wider-scope concerns (validators, generated client, cloning paths, edge cases, likely reviewer comments) surface upfront instead of as PR comments. When the working repo carries its own repo-local rules directory, also routes to the right rule docs and follow-up skills. Triggers on /ticket-impact, "review this ticket before implementation", "analyze ticket impact", "scope this ticket", "find hidden scope", "pre-plan this ticket", "what could this affect", "before I start this ticket".
---

# ticket-impact

## Purpose

Surface the wider-scope ripple effects of a ticket before planning starts, so they don't come back as PR review comments. The output is a compact pre-plan plus an Implementation Handoff, and the skill stops there: it does not write a plan, write files, or start implementing. The output is the only artifact unless the user says "save it to <path>".

When the working repo is listed under `repo_local_os` in `os-config.yaml` and its `rules_dir` exists at the repo root, the output also carries a routing block: category, risk level, generated-client impact, rule docs to load, and follow-up skills. That block lists paths only, because the user opens the file when they need it and a summary would drift from the source.

## Inputs

The user pastes one or more blocks. Only the main requirement is required.

| Block | Required | Notes |
|---|---|---|
| Main requirement | yes | The core ticket ask |
| Acceptance criteria | optional | Treated as confirmed requirements |
| Ticket comments | optional | Reviewer/product/QA notes |
| Related tickets | optional | Sibling work that may overlap |
| Related requirements | optional | Cross-ticket dependencies |
| PR link | optional | Not fetched by default, see PR rule |
| Business-rule notes | optional | Domain context |

When blocks disagree (a comment overrides AC, a related ticket conflicts with the main requirement), render the disagreement under Conflicts rather than merging it, so the user decides which one wins.

PR rule: prefer the diff or context the user pasted, and don't offer to fetch. Fetch only when the user says "fetch PR" or "use this PR link", with the host's diff command (`gh pr diff <num>` for GitHub, the equivalent for others). Cap intake at about 500 lines and summarize larger hunks.

## Workflow

### Step 0. Spec mode

If the input contains a written spec (a markdown doc, before/after code blocks, or a numbered change list), work in spec mode. The spec is the scope: Step 3 greps verify spec items rather than expand scope, and the Step 4 checklist flags what the spec omits rather than overriding it. The output adds a Spec adherence block listing every spec item as `will-do | needs-clarification | conflicts-with-codebase`. A `conflicts-with-codebase` status needs a named code reference (file:line), since a clean grep is not evidence of a conflict. See `wiki/workflows/spec-driven-cross-repo-ticket.md`.

### Step 1. Parse inputs

Bucket each block: confirmed requirements, AC, comments, related-ticket influence, PR/diff influence, business-rule notes. Omit empty buckets from the output.

When the ticket belongs to an epic, read the epic description, its sibling tickets and any design doc they link before writing Open questions. A question the epic's author already answered there is an assumption with its source, not a question for them.

### Step 2. Extract search terms

Pull domain nouns, entity names, field names, routes/endpoints, UI labels, and business-rule keywords. Dedupe, cap at about 15, and show only the final list as one line.

### Step 3. Targeted search

This is the only step that reads the repo. The budget is 8 greps plus 8 snippet reads, raised to 12 plus 12 only when a Step 7 risk signal has fired. Run greps in priority order, highest-confidence terms first, and stop as soon as the pre-plan is supportable. The checklist guides risk thinking; searches gather evidence and don't need to cover every checklist category.

- `grep -rn -m 5 "<term>" <backend-src> <frontend-src>` (max 5 hits per term). Resolve the source directories from the working repo, and its siblings in `os-config.yaml` when the ticket spans repos.
- For the top 3 hits per term, one snippet read via `grep -n -A 5 -B 5 -m 1`, about 40 lines at most. No full-file reads and no `find -name` sweeps.
- Scope: the working repo's source and test directories. Exclude the generated-client directory, `**/Migrations/`, `**/bin/`, `**/obj/`, `**/node_modules/`, and other build or vendored output.

Pipeline traversal, one level deep, from the same snippet budget: when a hit lands in a handler, check it for downstream dispatch (mediator/command dispatch, message-bus enqueue, job scheduling), and spend one snippet read on each downstream handler. These handlers never appear in ticket text and are only reachable through the dispatch chain. In each one, look for three silent failures, where the handler runs, processes zero records, and raises no error:

- Nullable filters (`.Where(x => x.Field != null)`, `.HasValue`) on fields that are null for the variant the ticket introduces.
- Iteration over collections the new variant never populates.
- A missing eager-load (`.Include()` or equivalent) for a navigation property the handler reads, which returns null instead of throwing.

When the ticket adds or changes an operation on an existing entity, spend one snippet read on the entity's flag/enum extension methods (pattern `static bool [Verb](this [EnumType])`). They gate downstream scheduling, so a missing flag means the job never enqueues.

### Step 4. Apply the checklist

Use only what Step 3 found; this step does no repo I/O. Tag each item covered, likely-affected, or not relevant. Only likely-affected items appear in the output, under Likely missed areas.

1. Validators (validation layer, request validators).
2. API contract (endpoint modules, request/response DTOs).
3. Generated client (regeneration needed?).
4. Frontend schemas/types (validation schemas, generated types).
5. UI forms (form components, error rendering).
6. Imports/exports (file parsers, template files, downloads). When ingest behavior changes, grep the entity's create/import entry points and apply the change to every ingress path (manual upload and automatic or integration import), because ticket wording like "upon upload" usually names only one. Reaching the second path means extracting shared logic, per item 20.
7. Calculations / business rules (domain handlers and logic).
8. Cloning / copy paths (clone and duplicate helpers).
9. DTOs / mappers (handoff, cross-repo integration).
10. Tests (does the existing test class for the symbol cover the change?).
11. Background jobs (schedulers, idempotency). If a job chain ends in a cleanup or state-reset continuation, every intermediate continuation needs to run on any finished state; a success-only continuation skips the terminal step on failure and leaves state flags stuck.
12. Authorization (resource authorization, attribute or policy selection).
13. Serialization / nullability / default behavior.
14. Existing records, migration and default impact (backfill, defaulting).
15. Reports / downloads / exports.
16. Cache / background data freshness (cache reads, eviction).
17. Feature flags / config switches.
18. Error handling / user feedback (result shape, message rendering).
19. Manual-test / QA impact (what changes for the testing guide?).
20. Duplication. Will a literal, expression, or guard end up in two or more files? Plan the shared constant, extension, or helper now, backend and frontend, and collapse a guard repeated N times into one predicate. If the query engine can't translate a helper and a copy is unavoidable, plan a drift test pinning the copy to the helper. Mirrored paths: when implementing an existing behavior on a second path (ingress, export, clone, handoff, entity shape, UI component), open the first implementation before writing and name what actually differs, usually collection type, property names, and nullability. Extract the rest (ordering, checks, thresholds, derivation) into one helper, generic with selector lambdas if shapes differ, and have each caller keep only its own field assignment.
21. Cross-repo data dependency. Does a new filter or behavior need a field the endpoint doesn't return, or data only another repo owns? Then flag a paired ticket in the owning repo, and bound filter option-sets to what the source data supports so no choice yields zero results.
22. Copy that describes a number. Wording that claims a direction or comparison ("saves", "decrease", "more/less", "X vs Y") asserts the value's sign, so plan to exercise it positive, negative, and zero. Where the design puts two columns, rows, or callouts side by side, name the input that makes them differ; if none exists, raise the duplicate as a product finding before build.

### Step 5. Repo-local categorization and routing

Skip unless the working repo is listed under `repo_local_os` and its `rules_dir` exists at the repo root. Paths below are relative to that `rules_dir`. Pick one primary category, the dominant one. If several qualify, don't record a secondary; bump the risk level in Step 7 instead.

| Category | Trigger signals |
|---|---|
| `backend-slice` | new handler/spec/validator, no frontend impact |
| `api-contract-change` | backend DTO/endpoint change that regenerates the client |
| `frontend-feature` | UI / form / data-fetching change with no backend contract change |
| `core-domain-logic` | touches the repo's business-critical calculation or workflow area (named in its known-issues) |
| `integration` | cross-service fetches, caching paths, external-source reads |
| `regression-risk-heavy` | broad multi-feature touch, or two or more of the above qualify |

| Category | Rule docs to load, by role (in order) | Follow-up skills |
|---|---|---|
| backend-slice | `workflows/` backend-slice doc, `standards/` backend doc, `workflows/` pre-PR risk check | the repo's unit-test and code-review skills, `/cross-repo-review` if invariant-heavy |
| api-contract-change | `workflows/` contract-change doc, `standards/` backend and frontend docs, `workflows/` pre-PR risk check | unit-test and code-review skills, the repo's manual-test skill (developer and QA hand-off) |
| frontend-feature | `standards/` frontend doc, `workflows/` pre-PR risk check | code-review skill, manual-test (QA hand-off) |
| core-domain-logic | `known-issues/` doc for the business-critical area, `standards/` backend doc, `workflows/` pre-PR risk check | unit-test and code-review skills, manual-test (business-critical hand-off) |
| integration | `standards/` backend doc, `workflows/` pre-PR risk check | unit-test and code-review skills |
| regression-risk-heavy | matched-category docs plus every relevant `known-issues/` doc | unit-test and code-review skills, manual-test (developer and QA hand-off) |

Always append the repo's repeated-PR-mistakes known-issues doc, if it has one. List only files that exist under the `rules_dir`, and don't load the whole tree. Manual-test developer mode is for backend and contract validation, QA hand-off mode for business validation; emit both for full-stack tickets.

When the workspace wiki has a product-rules page, load it and list under Business-rule notes every row that touches the ticket's domain nouns. Those rules live in neither the code nor the ticket.

### Step 6. Cross-repo mini-spec

Trigger on any cross-repo touch, handoff DTO, precision/serialization/persistence/data-flow change, migration, schema change, integration boundary, or ticket text naming another repo in `os-config.yaml`. When triggered, emit the Cross-repo mini-spec block from the output template with sections in this order: Invariant, System touch map, Evidence used, What changes, What not to change, Open questions. It supplements Affected surfaces, Edge cases, Tests, and the Implementation Handoff; it doesn't replace them. Risk level becomes at least Medium.

- Invariant: one or two sentences naming the end-to-end property that must hold (precision across the wire, idempotency on a stated key, identity stable across days). If you can't state it, ask before continuing, since there is no spec yet.
- System touch map: tag every repo in `os-config.yaml` `repos` and every seam in `seams` (the message bus especially) as touched, not-touched, or unknown, with a one-line reason. A surface grep didn't hit is unknown, not not-touched, and also goes into Open questions.
- Evidence: specs, DB rows, stored JSON, logs, and captured payloads outrank code search; code outranks docs; a negative grep is never conclusive. Cite the highest-ranked evidence available. Each What not to change line cites a named artifact (file:line, DB row, payload, log line) showing the invariant holds without touching that surface.
- Tests: each entry names the invariant it asserts, with exact (not tolerant) assertions for precision and serialization.
- Artifacts: before finalizing, ask once whether the user can paste the two or three most relevant of: a DB column/schema row, stored JSON, a captured request/response payload, a log line, a generated-client signature, or a migration filename/tail. Don't block if they paste nothing, and don't fetch production data. If an artifact already in the conversation contradicts the invariant (a column `decimal(18,4)` vs a DTO assuming `decimal(18,2)`, a null payload field, `DateOnly` vs `DateTime`), record it under Conflicts or Open questions.
- Durable storage: for cross-repo or high-risk tickets only, and only when running from the workspace root, offer once to save `wiki/features/<ticket>-<short-name>.md`. Write it only on an explicit yes, containing just ticket id and short name, invariant, touch map, evidence, open questions, created date, and last reviewed date.

Load whichever of these exist, both sets if both are present: from the workspace root, `wiki/system-map.md` and `wiki/workflows/spec-driven-cross-repo-ticket.md`; from inside a repo with a `rules_dir`, `<rules_dir>/system-map.md` and `<rules_dir>/workflows/spec-driven-cross-repo-ticket.md`.

### Step 7. Score risk and emit

Risk signals (any one unlocks the 12+12 budget): DB/schema change, API contract change, generated client impact, business-rule/calculation change, import/export change, validation change, background job impact, broad frontend/backend change, multi-domain touch, unclear requirements.

For the routing block:

- Risk level. Low: no signal, single contained surface. Medium: one signal or two or more surfaces. High: two or more signals, generated-client impact likely, the repo's business-critical area touched, or two or more categories qualified.
- Generated-client impact. Unlikely: frontend-only, or backend with no DTO/endpoint change. Possible: backend touches a DTO or handler but it's ambiguous. Likely: confirmed DTO/endpoint signature change.
- Regression hotspots: at most 2, taken from the repo's own known-issues catalog, or "none".

Tag every affected surface with confidence: confirmed (exact symbol/string match), likely (adjacent pattern or strong domain-noun overlap), or possible (the checklist suggests it but no grep hit). No grep hit means possible, not safe; absence of a hit never justifies excluding a surface. Each Non-goals line names the artifact or code reference behind it, or is tagged `unverified-exclusion` and moved to Open questions.

Limits: at most 8 affected surfaces, 10 edge cases, 12 likely-missed items, and 5 open questions. Keep edge cases to what the inputs and checklist flag. No generic advice, full file dumps, or large tables. Omit sections with no content, except the Implementation Handoff, which is always present. Replace "looks fine" summaries with the specific likely-affected items and their reasons.

The output template and a worked example are in `references/output-template.md`; read it when you reach this step. End the turn after the output, without offering to write the plan.
