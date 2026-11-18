# git-guard

## What it does

A PreToolUse hook on the Bash tool that reads the command the way a shell would before it runs. It
splits compound commands (`&&`, `;`, pipes, subshells, `$(...)`, `sh -c`, `eval`, heredocs), strips
wrappers (`env`, `sudo`, `timeout`, `xargs`, `rtk`, `rtk proxy`), skips git's global options
(`-C <path>`, `-c key=value`) and then judges the git subcommand and its flags. Text that only
mentions a blocked phrase (a `grep` pattern, a commit message) is not a command and passes.

Always installed with core. It replaces the regex guard `block-dangerous-git.sh`, which stays as
the fallback.

## Decisions

| Decision | Commands |
|---|---|
| **deny** | `push` with `--force`, `-f`, `--force-with-lease`, `--force-if-includes`, `+refspec`, `--mirror`, `--delete`, `-d`, `:branch`, `--prune`; `reset --hard`; `clean -f`; `branch -D`; `checkout .`, `checkout -f`; `restore .` of the working tree; `switch -f` / `--discard-changes`; `stash drop` / `clear`; `filter-branch`, `filter-repo`, `update-ref -d`; defining a git alias; a `-c` config value that would run any of these |
| **deny** | `curl` / `wget` that sends data (POST, PUT, PATCH, DELETE) to an environment marked `mutations: forbidden` |
| **ask** | `push` (also `subtree push`, `lfs push`), `stash` (except `list` / `show`), creating a branch (`checkout -b`, `switch -c`, `branch <name>`), `rebase`, `commit --amend`, `checkout -- <path>` |
| **ask** | `add` and `commit`, unless the user's last message asked for a commit ("commit it", "can you commit this?"; "don't commit yet" does not count) |
| **ask** | a git command the guard cannot read: `-c` keys or `GIT_*` variables that make git run a program, brace expansion, a command name that comes from a variable, an unknown wrapper around `git push` |
| **allow** | everything else: read-only git, `fetch`, `pull`, `merge`, `checkout <branch>`, non-git commands |

Deny wins over ask, ask over allow, across every command in the line. The guard prints nothing for
allow, so the `permissions.ask` rules in `settings.json` still apply after it. On an internal error
it stays silent, except that a command that visibly holds a force push or `reset --hard` is denied.

## Read-only environments (optional)

Add `mutations: forbidden` to an environment in `os-config.yaml`:

```yaml
environments:
  prod:
    app_url: "https://app.example.com"
    mutations: forbidden
```

The guard reads only `app_url` and `mutations`, by line, at the template's two-space indentation.
It looks for `os-config.yaml` one folder above the hook (repo-memory data folder) and two above
(workspace root).

## Prerequisites

Node 22.18 or newer, because Node runs the TypeScript files directly. No packages. With an older
Node, or none, `guard.sh` runs `block-dangerous-git.sh` instead: it blocks force push,
`reset --hard`, `clean -f`, `branch -D` and `checkout .` / `restore .` by regex, and cannot ask.

## Install steps

Four files live together in one hooks folder: `guard.sh` (launcher), `guard-git.ts`,
`shell-tokens.ts` and `template/.claude/hooks/block-dangerous-git.sh`.

- **Workspace mode:** `/os-init` step 4 copies them to `<workspace>/.claude/hooks/`. The template's
  `settings.json` runs `sh "$CLAUDE_PROJECT_DIR/.claude/hooks/guard.sh"` on `PreToolUse` / `Bash`.
- **Repo-memory mode:** `modules/repo-memory/setup_repo.py` copies them to `<data>/hooks/` and adds
  `sh "<data>/hooks/guard.sh"` to `.claude/settings.local.json`, unless the repo already has its
  own Bash guard hook.

## Verify

Feed the launcher a hook payload; it only reads stdin and prints a decision:

```
echo '{"tool_name":"Bash","tool_input":{"command":"git push --force"}}' | sh .claude/hooks/guard.sh
```

Expect `"permissionDecision":"deny"`. A plain `git push` gives `"ask"`, `git status` prints nothing.

## Tests

From the plugin root:

```
node --test 'tests/guard/*.test.ts'
```

`tests/guard/guard-cases.json` is the decision table: `[command, last user message, expected]`.

## Uninstall

Remove the `guard.sh` hook entry from the settings file and delete the four files.
