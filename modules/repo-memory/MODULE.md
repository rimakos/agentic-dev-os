# repo-memory

## What it does

For a repo that already keeps its own knowledge base and `/wrap` (for example `docs/knowledge/` with
an index and a wrap command in `.claude/commands/`). The repo's knowledge base stays the only memory:
the OS adds no wiki. It adds what a written rule cannot do on its own:

- **At session start:** names the earlier sessions that changed files and ended without `/wrap`, so
  Claude offers `/wrap` for them before new work.
- **Before the first commit, push or PR create of a session that needs one:** a once-per-session
  reminder to run `/wrap` first, so knowledge pages go into the same change.
- **The moment a rule matters** (`repo_hooks.py`, once per session each): the first source edit
  asks whether the repo's start skill ran; the first write into the knowledge base asks for the
  check before a claim is tagged confirmed; a PR create or comment through `az` or `gh` asks for
  each claim's check and a reread with the repo's client-safe check; a `git push` runs the repo's
  leak or word check on the files it sends and blocks only on a finding.
- **Once a day:** a row in `wrap-rate.tsv` with sessions, sessions that changed files, how many of
  them ran `/wrap`, and commits to the knowledge base. This is how a trial shows whether it helped.

Everything it reads is local (Claude Code's session transcripts and `git log`). Nothing is written
into the repo except the git-ignored `.claude/settings.local.json`, so it is safe on a client-visible
repo. Claude Code is started from the repo root, so the repo's own settings, deny rules and hooks
keep working.

## Prerequisites

- `python3` on the PATH.
- The repo git-ignores `.claude/settings.local.json` (`git check-ignore -q .claude/settings.local.json`
  succeeds). If it does not, skip the module: the hooks would show up as a change to commit.
- A knowledge base folder in the repo. Record its path as `memory.root`.

## Install

1. Data folder outside the repo: `~/<project>-os/` (create it, record `dir_created`). Copy
   `modules/repo-memory/wrap_check.py` and `repo_hooks.py` to `~/<project>-os/hooks/`. If the data
   folder already exists (an earlier install), refresh the two scripts and keep everything else.
2. Merge into `<repo>/.claude/settings.local.json` (if it exists, back it up to
   `<data>/backups/`, never next to it: a backup in the repo is an untracked file), with
   `<data>` = the data folder and `<memory>` = `memory.root` relative to the repo:

   ```json
   {"hooks": {
     "SessionStart": [{"hooks": [{"type": "command", "timeout": 15,
       "command": "python3 \"<data>/hooks/wrap_check.py\" session-start --memory <memory> --append \"<data>/metrics/wrap-rate.tsv\""}]}],
     "PreToolUse": [
       {"matcher": "Bash", "hooks": [
         {"type": "command", "timeout": 10, "command": "python3 \"<data>/hooks/wrap_check.py\" pre-commit --memory <memory>"},
         {"type": "command", "timeout": 10, "command": "python3 \"<data>/hooks/repo_hooks.py\" outbound"},
         {"type": "command", "timeout": 60, "command": "python3 \"<data>/hooks/repo_hooks.py\" pre-push --gate <gate>"}]},
       {"matcher": "Write|Edit|Bash", "hooks": [
         {"type": "command", "timeout": 10, "command": "python3 \"<data>/hooks/repo_hooks.py\" knowledge-edit --memory <memory>"},
         {"type": "command", "timeout": 10, "command": "python3 \"<data>/hooks/repo_hooks.py\" first-edit --start <start skill>"}]}]
   }}
   ```

   `<gate>` is the repo's own leak or word check that takes file paths (for example
   `tools/leak-check.sh`); leave the pre-push entry out if there is none. `<start skill>` is the
   repo's skill for starting work (for example `/start-work`); leave first-edit out if there is none.
   On an upgrade, first remove every hook entry whose command points into `<data>/hooks/`, so
   nothing is listed twice. Record each as a `settings_entry` action with `path` set to the local
   settings file.
3. `mkdir -p <data>/metrics`.

## Verify

```
cd <repo> && git check-ignore -q .claude/settings.local.json && echo ignored
cd <repo> && python3 <data>/hooks/wrap_check.py report --memory <memory>
cd <repo> && git status --short .claude/
```

The first prints `ignored`, the second a header and one row, the third nothing.

## Remove

1. Remove every hook entry pointing into `<data>/hooks/` from `<repo>/.claude/settings.local.json`, or restore its backup.
   Delete the file if the OS created it and it is now empty.
2. Delete `<data>/hooks/wrap_check.py` and `repo_hooks.py`. `wrap-rate.tsv` holds the trial's data: ask before deleting it.
