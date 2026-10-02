# output template

Output shape for the emit step of `../SKILL.md`.

## Output template

```markdown
# Ticket Impact Pre-Plan

**Ticket goal**: <one sentence, derived from main requirement>

**Risk flags**: <comma-separated list of fired signals, or "none">

## Repo-local rules routing
_Emitted only when the working repo is listed under `repo_local_os` and its `rules_dir` exists. Paths only. Never inline rule-doc content._

- **Category**: <one primary>
- **Risk level**: Low | Medium | High
- **Generated client impact**: unlikely | possible | likely
- **Regression hotspots**: <up to 2, or "none">
- **Load context (in order)**:
  - `<rules_dir>/<path>`
  - ...
- **Follow-up skills**: /skill-a, /skill-b
- **Targeted exploration** (max 3: one handler/slice, one frontend area, one similar example):
  - <handler/slice hint>
  - <frontend area hint>
  - <similar implementation/example hint>

## Cross-repo mini-spec
_Emitted only when Step 6 triggered. Omit entirely otherwise._

### Invariant
<one or two sentences: the end-to-end property that must hold>

### System touch map
| Surface | Status | Reason |
|---|---|---|
| <repo from os-config.yaml> | touched / not-touched / unknown | <one line> |
| <repo from os-config.yaml> | touched / not-touched / unknown | <one line> |
| <shared-lib repo> | touched / not-touched / unknown | <one line> |
| <migrations repo> | touched / not-touched / unknown | <one line> |
| <message bus / seam from os-config.yaml> | touched / not-touched / unknown | <one line> |

### Evidence used
- <highest-rank artifact for current behaviour: DB row / captured payload / log line / file:line>
- ...

### What changes
- <surface, file:line, one-line change>
- ...

### What not to change
- <surface>: invariant holds because <named artifact: file:line / payload / DB row>
- ...

### Open questions
- <every `unknown` row from the touch map, plus anything the spec doesn't pin down>
- ...

## Inputs received
<list only the buckets that have content: main req / AC / comments / related / PR / business notes>

## Conflicts
<only if conflicts exist between buckets; otherwise omit this section>

## Search terms used
<comma-separated, max 15>

## Affected surfaces (max 8)
- **<file or area>**: <one line> (_confidence: confirmed / likely / possible_)
- ...

## Likely missed areas (likely-affected only, max 12)
- <checklist item>: <one-line why it likely applies here>
- ...

## Edge cases (max 10)
- <case>
- ...

## Tests to add or update
- <test class or scenario>: <one-line reason>
- ...

## Non-goals
- <what this ticket explicitly does NOT cover>

## Assumptions
- <each assumption I'm making, so the user can correct>

## Open questions for PM/product (max 5)
- <only when genuinely useful>

## Implementation Handoff
(Compact-but-complete. A cheaper implementation model should be able to execute the confirmed plan from this section alone, without the full planning conversation.)

- **Goal**: <ticket goal>
- **Affected files/areas**: <bullet list, paths only>
- **Required changes**: <bullet list, one line each>
- **Validation/schema/API impacts**: <bullet list>
- **Edge cases to handle**: <bullet list>
- **Tests required**: <bullet list>
- **Non-goals**: <bullet list>
- **Assumptions**: <bullet list>

---
**Deep pass recommended**: yes/no: <one-sentence reason>
```

## Example trigger

> User: `/ticket-impact`
> PROJ-1234: add new order-line columns (PrevDiscount, VendorName, SkuName, SkuId, ListPrice). AC: users can upload a CSV with these new columns; values persist on `OrderLine.Skus` and `PrevDiscount`.

Skill produces (compact form):

> **Risk flags**: validation change, import/export change, generated client impact
> **Search terms**: PrevDiscount, VendorName, Skus, RawOrderRecord, OrderLineValidator, ...
> **Affected surfaces**: `OrderLineValidator.cs` (likely, needs rules for new fields), `OrderCsvParser.cs` (confirmed), `OrderLine.cs` (confirmed), `OrderCloneExtensions.cs` (possible, verify field copy), ...
> **Likely missed**: validators (new fields lack rules); cloning path (verify copy); generated client (regen the client); manual-test (template-mismatch flow); ...
> **Repo-local rules routing**:
> - Category: api-contract-change
> - Risk level: High
> - Generated client impact: likely
> - Regression hotspots: order-import eager-load, schema nullable parsing
> - Load context: `<rules_dir>/workflows/api-contract-change.md`, `<rules_dir>/standards/backend.md`, `<rules_dir>/standards/frontend.md`, `<rules_dir>/known-issues/repeated-pr-mistakes.md`
> - Follow-up skills: unit-test + code-review skills, the repo's manual-test skill (developer + QA hand-off)
> - Targeted exploration:
>   - Features/Orders/Validators/OrderLineValidator.cs (handler/slice)
>   - web/src/features/orders/ (frontend area)
>   - similar slice: Features/Orders/ existing upload path
> **Implementation Handoff**: ... (compact handoff block)
> **Deep pass recommended**: no, scope is contained to the order-import path.
