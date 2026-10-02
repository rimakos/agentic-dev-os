# Workspace

Entry point Claude loads for every session in this workspace. Copy it to the workspace root (the
folder holding your repo checkouts and `wiki/`), then edit it.

@wiki/CLAUDE.md

## A ticket

1. `/ticket-impact` before a plan or code. It reads the wiki and `os-config.yaml`, surfaces hidden
   scope, and routes to a repo's own rules when `os-config.yaml` declares a `rules_dir`.
2. Do the work in the main session. Delegate only wide, independent tracks (a broad search,
   parallel research).
3. Contract, schema or multi-repo tickets follow `wiki/workflows/spec-driven-cross-repo-ticket.md`.
4. `/wrap` at the end. It files what the session learned and writes `wiki/log.md` last; the
   SessionStart hook warns the next session if that was skipped.

## Boundaries

- The human does the git writes. `git add`, `commit`, `push`, `stash` and branch creation are set
  to ask in `.claude/settings.json`; end code work with "Ready to commit: <files>".
- Nothing is posted to the ticket tracker or a PR unless the human asks in that turn, because a
  post is public and hard to take back.
- Change only the repo the task names, and check its `git status` first.

## Two memory layers

- The wiki (`wiki/`) is the shared team record: topology, gotchas, decisions. If the layers
  disagree, the wiki wins.
- Claude's auto-memory (`~/.claude/projects/<workspace-slug>/memory/`) holds private working notes
  that are not team knowledge.

Each fact has one home; link to it rather than copying it.
