# agentic-dev-os

A portable agentic operating system for a multi-repo dev team, packaged as a Claude
Code plugin.

Every ticket runs the same loop: **scope the blast radius before planning, implement,
verify across repo boundaries, then feed what you learned into a shared knowledge
wiki** so the next ticket is cheaper. Config-driven and domain-agnostic. Point it at
your repos and go.

> New here? Open `docs/visualiser.html` in a browser for a one-page, clickable map of
> the whole flow. `docs/flow.md` is the written version.

## What's in the box

**The lifecycle skills** (the loop):

| Skill | Fires | Does |
|---|---|---|
| `ticket-impact` | before any plan or code | impact-aware pre-plan + Implementation Handoff; surfaces hidden scope and likely reviewer comments; Cross-repo mini-spec when a seam is touched |
| `cross-repo-review` | on a diff/PR | checks the diff against the stated invariant and system touch map |
| `pr-ticket-review` | on a PR | maps each ticket requirement to the diff (satisfied / partial / missing) + cross-repo ripple |
| `ticket-testing` | to verify behavior | drives the real app and reconciles every UI value against the read-only DB |
| `wrap` | end of every session | fixed closing checklist; files learnings to the wiki |
| `goal` | end of a ticket | compact ADR, only when a decision would surprise a future reader |

**Knowledge-wiki ops:**

| Skill | Does |
|---|---|
| `wiki-ingest` | file a new source into the wiki; update pages + index + log |
| `wiki-lint` | health check: contradictions, stale claims, orphans, missing evidence tags |
| `seed-test-data` | seed precondition rows in SQL so a tester lands at the test point |

**Extend the OS:**

| Skill | Does |
|---|---|
| `skill-workshop` | design + build a new skill (proposal first, then SKILL.md) |

**The OS itself:**

| Skill | Does |
|---|---|
| `os-init` | onboarding wizard: module choice, workspace scaffold, repo analysis, ticket source, smoke test |
| `os-doctor` | read-only health check: scaffold, modules, hooks, marker blocks, manifest integrity |
| `os-remove` | manifest-driven uninstall: one module, glue only, or everything |

**The knowledge wiki** (`template/`): an LLM-maintained knowledge base. index, log,
system-map, per-repo and per-seam pages, known-issues (working rules by topic),
decisions (ADRs), features. Every claim carries an evidence tag (✅ confirmed / 🟡
inferred / ⬜ unknown).

**The enforcement** (`template/.claude/`): `permissions.ask` rules for git writes
(and, after `/os-init`, your tracker's write tools), a git guard that blocks
force-push and hard resets, a SessionStart drift check, and two once-per-session
reminders: `/ticket-impact` before the first repo edit, verify before the first wiki
claim.

There is no execution-loop skill. Current models plan, delegate and verify on their
own, so 0.3.0 moved that ritual to `archive/` (see "What changed in 0.3.0").

## Optional modules

Six add-ons under `modules/`, each with a `MODULE.md` (Prerequisites / Install /
Verify / Remove). `/os-init` asks y/n for each during onboarding; `/os-doctor`
verifies them; `/os-remove` uninstalls them cleanly via the install manifest
(`.claude/os-manifest.json`). Anything injected into a shared file is wrapped in
`<!-- AGENTIC-DEV-OS:BEGIN <module> -->` markers so removal takes nothing else out.

| Module | One line |
|---|---|
| `rtk` | CLI proxy that compacts shell output before the model reads it (60-90% token savings on routine ops) |
| `caveman` | compressed reply mode; off by default since 0.3.0, the core block already sets response length |
| `codegraph` | semantic code graph: instant symbol/caller/impact lookups instead of file scans (needs the privately distributed binary; skip otherwise, the npm `codegraph` package is unrelated) |
| `statusline` | ctxline-claude status line: model, context usage, session info |
| `plugins` | baseline plugin pack: context7 + playwright |
| `metrics` | self-measurement TSVs (session health, PR cycle time, skill fire rate) appended by `/wrap` |

## Setup

Prerequisites: git and Claude Code, `jq` strongly recommended. Module-specific:
Homebrew for rtk, node for caveman/statusline, `gh` authenticated for GitHub
Issues as ticket source.

1. Make sure your GitHub account has access to the repo (accept the invite if
   it is private).
2. In Claude Code:

   ```
   /plugin marketplace add rimakos/agentic-dev-os
   /plugin install agentic-dev-os@agentic-dev-os
   ```

   Working from a zip or local copy instead? Move the folder to a permanent
   path first (Downloads is not one): the marketplace stores the path you give
   it and reads it live, so a temporary or wrong path reports success but no
   skills appear. Then register the path in place of the repo:
   `/plugin marketplace add ~/agentic-dev-os`.

   The skills become available as `/ticket-impact`, `/wrap`, etc. across your
   sessions.
3. Make an empty workspace folder for your project (like `~/myproject-os`),
   `cd` into it, and run `/os-init`. The wizard does the rest: asks which repos
   to symlink into the workspace, asks which optional modules you want,
   analyzes the repos and their seams, configures your ticket source, and
   writes nothing until you approve its draft.

Fallback without plugin support: copy `skills/*` into `~/.claude/skills/`, copy the
contents of `template/` into your workspace root, and fill in `os-config.yaml` by
hand.

That is the whole "OS": the skills provide the flow, the permission rules and hooks
hold the boundaries, and the wiki is the memory it writes to.

## Upgrading from 0.2.x

`/os-init` stops when a manifest exists, so an existing workspace upgrades by hand:

1. `/plugin marketplace update agentic-dev-os`, then restart Claude Code.
2. In `~/.claude/CLAUDE.md`, replace the content between the
   `AGENTIC-DEV-OS:BEGIN core` and `END core` markers with a block written per
   `/os-init` step 5 (length line, boundaries with reasons, how to work). Drop the
   operating-flow trigger and the subagent-driven execution lines.
3. Merge `permissions.ask` and the two reminder hooks from
   `template/.claude/settings.json` into `<workspace>/.claude/settings.json`, copy
   `template/.claude/hooks/ticket-impact-reminder.sh` and `wiki-verify-reminder.sh`
   into `<workspace>/.claude/hooks/`, and add the entries to the manifest as
   `settings_entry` and `file_created` actions.
4. Copy `template/wiki/known-issues/` into `<workspace>/wiki/`, move the working rules
   from your `wiki/CLAUDE.md` into those pages, and replace `wiki/CLAUDE.md` with the
   new template version.
5. If the plugin pack installed superpowers: `/plugin uninstall
   superpowers@claude-plugins-official`.
6. Run `/os-doctor`.

## What changed in 0.3.0

Rebuilt for Opus 5.x, following Anthropic's prompting guide for Opus 5 and its
prompt-audit guide: keep what runs (hooks, permission rules, metrics), keep what is
known (wiki), cut what is only told.

- Archived the execution ritual (`operating-flow`, `task-intake`, `subagent-execute`,
  `verify-done`, `session-capture`) and two skills with no fires in 90 days
  (`mcp-impact`, `cross-repo-manual-test`). Restore any from `archive/skills/`.
- The no-commit rule is now `permissions.ask` rules instead of prose, and `/os-init`
  sets the tracker's write tools to ask too.
- `CLAUDE.md` and `wiki/CLAUDE.md` rewritten short and calm; working rules moved to
  `wiki/known-issues/`, one home per rule, reasons kept, incident stories dropped.
- `ticket-impact` rewritten calm (364 to 144 lines, output template in
  `references/`), with three new checklist rules: every ingress path, mirrored paths,
  and copy that describes a number.
- `/wrap` routes each correction to a gate, one known-issues page, or the log, and
  records a daily skill fire rate when the metrics module is installed.
- superpowers left the plugin pack; caveman is off by default.

## Uninstall / rollback

`/os-remove` replays the install manifest in reverse. Three modes: `--module <name>`
drops one module, `--glue-only` strips the global CLAUDE.md block and all
hooks/settings entries while keeping everything else, `--all` removes everything the
manifest records. Injected blocks are removed by their marker fences, nothing
outside them. `wiki/`, `metrics/`, and `os-config.yaml` are knowledge, not install
state: never auto-deleted, even under `--all` (a separate explicit confirmation
defaults to keep). Auto-memory is never touched. `/os-doctor` reports install health
any time.

## Rough cost per ticket

The flow spends tokens. `docs/visualiser.html` ships an interactive estimator
(pick difficulty, quick vs deep, path, and model rate); the table below is a
snapshot at Opus 4.8 rates ($5 / $1M input, $25 / $1M output), assuming ~45% of
input is served from prompt cache.

| Ticket | Path | Mode | ~Input | ~Output | ~Cost |
|---|---|---|---|---|---|
| Trivial | quick | quick | 60k | 11k | ~$0.45 |
| Small | quick | quick | 100k | 19k | ~$0.75 |
| Medium | quick | quick | 170k | 31k | ~$1.30 |
| Medium | full | quick | 265k | 44k | ~$1.90 |
| Large | quick | quick | 305k | 56k | ~$2.30 |
| Large | full | deep | 1.0M | 127k | ~$6.20 |
| Cross-repo epic | full | deep | 1.7M | 211k | ~$10 |

**Quick vs deep.** Quick runs each skill as a single agent pass. Deep fans out to
parallel subagents for wide independent tracks, multiplying input ~2.1× and output
~1.6×, for cross-repo and high-blast-radius work.
**Quick path** = ticket-impact, plan, implement, cross-repo-review, wrap.
**Full path** adds pr-ticket-review, ticket-testing, goal.

These are planning heuristics for a real multi-repo team, not a billing guarantee.
Measure your own runs with `count_tokens` and edit the base numbers and model
rates in the estimator (top of the `<script>` block in `visualiser.html`).

## Philosophy

- **Scope before you plan.** Wider-scope ripple should surface as a pre-plan, not as
  PR comments.
- **Evidence over assertion.** Every claim is tagged and rankable: production data >
  code (file:line) > docs. Negative grep is never proof.
- **The wiki is the memory.** Topology and gotchas live in one place, tagged and
  cross-linked, not in ten people's heads.
- **The human commits.** Git writes and tracker posts are permission ask rules, so
  the boundary holds without the model having to remember it.
- **Enforce with hooks, not prose.** A check a script can run belongs in a hook; a
  rule that has a hook loses its prose copies.
- **Cut what the model already does.** Instructions to plan, verify or double-check
  cost quality on current models; the OS carries only what the model cannot know.
- **Deterministic beats judgment.** Anything done the same way twice becomes a skill.

## Layout

```
.claude-plugin/     plugin + marketplace manifests
skills/             the 13 skills (SKILL.md each)
archive/skills/     skills cut in 0.3.0, not loaded
modules/            optional add-ons: rtk, caveman, codegraph, statusline, plugins, metrics (MODULE.md each)
template/           workspace scaffold (/os-init copies its contents to your workspace root)
  CLAUDE.md         entry point: the ticket flow, boundaries, memory layers
  os-config.yaml    repos, seams, ticket source, environments (app URL + DB connections)
  .claude/          settings.json (ask rules) + hooks (drift-check, block-dangerous-git,
                    ticket-impact-reminder, wiki-verify-reminder)
  wiki/             CLAUDE.md schema + index/log/system-map + repo/seam templates
    known-issues/   working rules by topic (verification, pr-review, repo-targeting)
    decisions/      ADRs
    features/       per-ticket feature notes
    raw/            immutable sources (assets/ for attachments)
docs/
  flow.md           the methodology in prose
  visualiser.html   clickable one-page flow map + cost estimator
```
