# Setup: read me first

This is a portable agentic dev OS: a Claude Code plugin (20 skills) plus a
workspace scaffold (the wiki + rules) that turns Claude into a disciplined,
memory-keeping teammate across your repos. Every ticket runs the same loop:
scope before planning, implement, review across repo boundaries, then write what
you learned into a shared wiki so the next ticket is cheaper.

You do not hand-fill anything. One wizard (`/os-init`) scans your actual repo
checkouts, proposes everything personalized to your stack, and writes nothing
until you approve.

## Quickstart

The whole happy path:

1. Accept the GitHub invite to `rimakos/agentic-dev-os` (private repo).
2. In Claude Code: `/plugin marketplace add rimakos/agentic-dev-os`, then
   `/plugin install agentic-dev-os@agentic-dev-os`.
3. `mkdir -p ~/myproject-os && cd ~/myproject-os && claude`
4. Run `/os-init` and answer the wizard.

The workspace folder can be empty. The wizard asks where your repo checkout
lives and symlinks it in. Details below if anything is unclear or breaks.

---

## Prerequisites

Required: git and Claude Code (`claude` works in your terminal). Strongly
recommended: `jq` (without it the git guard hook over-blocks). Module-specific:
Homebrew only if you pick the rtk module, node only for caveman or statusline,
`gh` authenticated only if GitHub Issues is your ticket source.

---

## Part 1: install (about 2 minutes)

Normal route: accept the GitHub invite to `rimakos/agentic-dev-os`, then in
Claude Code:

```
/plugin marketplace add rimakos/agentic-dev-os
/plugin install agentic-dev-os@agentic-dev-os
```

Claude Code clones and manages the plugin itself. Updates later:
`/plugin marketplace update agentic-dev-os`.

**Got this as a zip instead?** Unzip it and move the folder to a permanent
path BEFORE registering it:

```
mv agentic-dev-os ~/agentic-dev-os        # in your terminal, from where you unzipped
```

The marketplace stores the path you give it and reads it live. Registering a
temporary or wrong path reports success, but no skills appear. Then use the
path in place of the repo:

```
/plugin marketplace add ~/agentic-dev-os
/plugin install agentic-dev-os@agentic-dev-os
```

The 20 skills work immediately, current session included. No restart needed.

---

## Part 2: run the wizard

Make a workspace folder for your project, named like `~/myproject-os`. It can
be empty. Launch `claude` from it and run `/os-init`.

The wizard asks where your product repo checkout lives and symlinks it into the
workspace. Zero OS files are written inside the repo. One workspace per
project: a second project gets its own.

It also asks which optional modules you want, y/n each:

- `rtk`: compacts shell output before Claude reads it, the biggest single token
  win (60-90% on git/ls/grep/build logs, needs Homebrew). Gotcha: two unrelated
  packages named rtk exist. After install, `rtk gain` must print token-savings
  analytics; otherwise you got the wrong one.
- `caveman`: terse reply mode plus compressed subagents, cuts output tokens
  roughly 75%. Skip it if terse replies annoy you.
- `codegraph`: instant symbol/caller lookups instead of file scans. Skip unless
  you already have the binary: it is privately distributed, there is no brew
  formula, and the npm `codegraph` package is an unrelated name-squat.
- `statusline`: model and context usage at the bottom of the terminal. Costs
  nothing, purely cosmetic.
- plugin pack: superpowers (process discipline), context7 (live library docs),
  playwright (browser automation for ticket testing).
- `metrics`: two small TSVs on session health and PR cycle time, a few lines
  per `/wrap`.

Then it analyzes the symlinked repos (tech and role from real signals like
package.json, *.csproj, go.mod, git remotes, plus the seams between them) and
asks for your ticket source. It presents a draft of the config and wiki starter
pages and writes nothing until you approve. Everything it installs is recorded
in `.claude/os-manifest.json`, so removal is clean.

---

## Part 3: what you run each ticket

Read `wiki/index.md`, then `/ticket-impact` before any plan, implement (Claude
delegates to subagents, main context stays clean), `/cross-repo-review` the
diff, `/wrap` to close (files learnings, writes `log.md` last). The drift-check
hook nags you next session if you skipped `/wrap`. Claude never commits. You do.

Gotcha: always launch `claude` from the workspace root, never from inside the
repo. The hooks resolve via `$CLAUDE_PROJECT_DIR`; run from inside the repo
they silently do nothing.

Full methodology: `docs/flow.md`. Clickable map + cost estimator:
`docs/visualiser.html` (open in a browser).

---

## Part 4: changed your mind

`/os-doctor` reports the health of the install any time (scaffold, modules,
hooks, manifest). `/os-remove` uninstalls cleanly: one module (`--module rtk`),
just the hooks and global glue (`--glue-only`), or everything (`--all`). Your
wiki, metrics, and os-config are knowledge, not install state; they are never
auto-deleted.
