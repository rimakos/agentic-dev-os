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
| `cross-repo-manual-test` | before QA | invariant-anchored manual test guide |
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
| `mcp-impact` | decide if a branch warrants MCP tooling; reuse-first, safety-gated |

**The execution loop** (how any non-trivial task runs; each phase also standalone):

| Skill | Does |
|---|---|
| `operating-flow` | master loop: sizing gate, intake, skill check, subagent execution, drift check, verify, capture |
| `task-intake` | restate the task, surface ambiguity, define a verifiable done-criterion before code |
| `subagent-execute` | delegate implementation to subagents; couple related tasks, parallelize independent ones |
| `verify-done` | run the done-criterion end-to-end against the real flow before claiming finished |
| `session-capture` | write feedback, decisions, and durable facts to memory at session end |

**The OS itself:**

| Skill | Does |
|---|---|
| `os-init` | onboarding wizard: module choice, workspace scaffold, repo analysis, ticket source, smoke test |
| `os-doctor` | read-only health check: scaffold, modules, hooks, marker blocks, manifest integrity |
| `os-remove` | manifest-driven uninstall: one module, glue only, or everything |

**The knowledge wiki** (`template/`): an LLM-maintained knowledge base. index, log,
system-map, per-repo and per-seam pages, decisions (ADRs), features. Every claim
carries an evidence tag (✅ confirmed / 🟡 inferred / ⬜ unknown).

## Optional modules

Six add-ons under `modules/`, each with a `MODULE.md` (Prerequisites / Install /
Verify / Remove). `/os-init` asks y/n for each during onboarding; `/os-doctor`
verifies them; `/os-remove` uninstalls them cleanly via the install manifest
(`.claude/os-manifest.json`). Anything injected into a shared file is wrapped in
`<!-- AGENTIC-DEV-OS:BEGIN <module> -->` markers so removal takes nothing else out.

| Module | One line |
|---|---|
| `rtk` | CLI proxy that compacts shell output before the model reads it (60-90% token savings on routine ops) |
| `caveman` | compressed reply mode + cavecrew subagents; cuts output tokens roughly 75% |
| `codegraph` | semantic code graph: instant symbol/caller/impact lookups instead of file scans (needs the privately distributed binary; skip otherwise, the npm `codegraph` package is unrelated) |
| `statusline` | ctxline-claude status line: model, context usage, session info |
| `plugins` | baseline plugin pack: superpowers + context7 + playwright |
| `metrics` | self-measurement TSVs (session health, PR cycle time) appended by `/wrap` |

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

That is the whole "OS": the skills provide the flow, `CLAUDE.md` + the hooks make it
run automatically, and the wiki is the memory it writes to.

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
| Medium | full | quick | 290k | 48k | ~$2.10 |
| Large | quick | quick | 305k | 56k | ~$2.30 |
| Large | full | deep | 1.1M | 138k | ~$6.70 |
| Cross-repo epic | full | deep | 1.8M | 230k | ~$11 |

**Quick vs deep.** Quick runs each skill as a single agent pass. Deep fans out to
parallel subagents and adds adversarial verification, multiplying input ~2.1× and
output ~1.6×, for higher confidence on cross-repo and high-blast-radius work.
**Quick path** = ticket-impact, plan, implement, cross-repo-review, wrap.
**Full path** adds pr-ticket-review, cross-repo-manual-test, ticket-testing, goal.

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
- **The agent never commits.** It scopes, implements, reviews, and captures. The
  human integrates.
- **Deterministic beats judgment.** Anything done the same way twice becomes a skill.

## Layout

```
.claude-plugin/     plugin + marketplace manifests
skills/             the 20 skills (SKILL.md each)
modules/            optional add-ons: rtk, caveman, codegraph, statusline, plugins, metrics (MODULE.md each)
template/           workspace scaffold (/os-init copies its contents to your workspace root)
  CLAUDE.md         entry point: wires the wiki + operating rules
  os-config.yaml    repos, seams, ticket source, environments (app URL + DB connections)
  .claude/          settings.json + hooks (drift-check, block-dangerous-git)
  wiki/             CLAUDE.md schema + index/log/system-map + repo/seam templates
    decisions/      ADRs
    features/       per-ticket feature notes
    raw/            immutable sources (assets/ for attachments)
docs/
  flow.md           the methodology in prose
  visualiser.html   clickable one-page flow map + cost estimator
```
