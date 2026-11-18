---
name: verify
description: Runs the repo's real gate, the command its CI runs (`verify_cmd` in os-config.yaml), and reports the exact failures. Use before saying a code change is done, and before a commit or a PR. Triggers on /verify, "run the checks", "does it pass", "is it green", "verify this". Never swaps in a lint or type-check of its own choosing.
---

# verify

The gate is one command per repo, the same one CI runs, stored as `repos[].verify_cmd` in
`os-config.yaml`. The script is `python3 "<plugin>/modules/conventions/conventions.py"`; from this
skill's base directory the plugin root is two levels up (`../../`). It finds `os-config.yaml` in the
workspace's `.claude/`, or in repo-memory mode in the data folder whose `hooks/wrap_check.py` the
repo's `.claude/settings.local.json` runs.

1. **Which repos.** Every repo this work changed (`git -C <repo> status --short`).
2. **Run the gate** for each: `python3 "<plugin>/modules/conventions/conventions.py" verify --repo <name>`.
   Without `--repo` it takes the repo the current folder is in. The exit code is the answer: 0 is a
   pass, anything else is a fail. Exit 2 with a `conventions:` line means the config is incomplete,
   not that the code failed.
3. **On a failure,** quote the failing lines as printed (command, file:line, message). Do not
   paraphrase them. Fix the cause and run the gate again until it exits 0.
4. **Report** one line per repo: `api: pass` or `api: FAIL (exit 1), <first failing line>`.

## When `verify_cmd` is empty

Do not pick a command and call it the gate. Find the repo's CI file (`.github/workflows/*.yml`,
`azure-pipelines.yml`, `.gitlab-ci.yml`, a `Makefile` target CI calls), read the steps that check a
change, and propose the one command that runs them (an existing script such as `npm run check`, or
the steps joined with `&&`). Ask the user once to confirm it, write it to `verify_cmd` for that repo,
then run it. If the user declines or there is no CI file, say the repo has no gate configured and
report the change as unverified.

## Rules

- A lint, a type-check or one test file you chose is not the gate. Run narrower commands while
  debugging if they help, then finish with `verify`. Never call a change done on anything else.
- Do not change the gate to make it pass (configs, thresholds, skipped tests, `verify_cmd` itself)
  unless the user asks for that.
- A failure your change did not cause is still reported, with the evidence that it fails on the
  base branch too.
- Not run is not a pass. If the gate could not run, say why and what remains unverified.
