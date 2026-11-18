# conventions

## What it does

Moves two things out of prose and into one script, `conventions.py`, that reads `os-config.yaml`:

- **The gate.** `verify` runs a repo's `verify_cmd`, the command its CI runs, in the repo's `path`
  and exits with that command's code. `/verify` calls it before any claim of done. A lint or
  type-check picked on the spot is not the gate.
- **Branch and commit shapes.** `branch` prints a branch name from `conventions.branch` (it never
  runs git), `branch --check <name>` and `commit-msg --check "<message>"` exit 0 on a match and 1
  with the piece of the pattern that failed. `/commit` calls both.
- **A reminder at commit time** (optional, `repo_hooks.py commit-msg`): before a `git commit -m`
  whose first line does not fit `conventions.commit`, Claude is told the pattern. It reminds and
  never blocks. A message passed with `-F` or a heredoc is not read.

The shapes live in `os-config.yaml` only. Skills and wiki pages point to it and do not restate it.

```
python3 <plugin>/modules/conventions/conventions.py verify [--repo <name>]
python3 <plugin>/modules/conventions/conventions.py branch <ticket> --type <type> --slug <slug>
python3 <plugin>/modules/conventions/conventions.py branch --check <name>
python3 <plugin>/modules/conventions/conventions.py commit-msg [--check "<message>"]
```

Exit 2 means the config lacks something, and the message names the key. `--config <path>` names
the file; without it the script looks for `os-config.yaml` in `$CLAUDE_PROJECT_DIR`, the
current folder or a folder above it, and in repo-memory mode for the one in the data folder whose
`hooks/wrap_check.py` the repo's `.claude/settings.local.json` runs.

## Prerequisites

- `python3` on the PATH. No packages: the script reads the keys below itself, so keep them in the
  template's shape (one `key: value` per line, inline `[a, b]` lists, quoted text taken as written).
- An `os-config.yaml` (workspace or repo-memory mode).

## Install

1. For each repo in `os-config.yaml`, set `verify_cmd` to the one command CI runs. Read it from the
   CI file (`.github/workflows/*.yml`, `azure-pipelines.yml`, `.gitlab-ci.yml`), do not guess it.
   A repo `path` is relative to the config file.
2. Under `conventions:` set the team's shapes:

   ```yaml
   conventions:
     branch: "<type>/<ticket>-<slug>"     # placeholders: <type> <ticket> <slug>
     branch_types: [feature, bugfix, chore, hotfix]
     commit: "<ticket>: <message>"        # placeholders: <type> <scope> <ticket> <message>
     ticket_pattern: "[A-Z]+-[0-9]+"      # regex for <ticket>; e.g. "AB#[0-9]+" or "[0-9]+"
   ```

   Everything outside a placeholder is literal. An unknown placeholder is an error. In a branch,
   `<type>` is one of `branch_types` and `<slug>` is lowercase words joined by dashes. In a commit,
   `<type>` is a lowercase word and `<scope>` lowercase with dashes.
3. Optional, repo-memory mode: copy `conventions.py` next to `repo_hooks.py` in `<data>/hooks/` and
   add this to the `Bash` matcher under `PreToolUse` in `<repo>/.claude/settings.local.json`:

   ```json
   {"type": "command", "timeout": 10, "command": "python3 \"<data>/hooks/repo_hooks.py\" commit-msg"}
   ```

   Record it as a `settings_entry` action and the copy as `file_created`.

## Verify

```
python3 <plugin>/modules/conventions/conventions.py commit-msg
python3 <plugin>/modules/conventions/conventions.py branch --check not-a-branch; echo $?
python3 <plugin>/modules/conventions/conventions.py verify --repo <name>; echo $?
```

The first prints the pattern and an example, the second the expected shape and `1`, the third the
gate's own output and its exit code.

## Remove

1. Remove the `commit-msg` hook entry from `<repo>/.claude/settings.local.json` and delete
   `<data>/hooks/conventions.py`, if step 3 was done.
2. The keys in `os-config.yaml` are the team's own record: leave them unless asked.
