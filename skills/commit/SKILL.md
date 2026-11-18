---
name: commit
description: Commits staged work in the team's format, only when the user explicitly asks ("commit it", "commit these changes", "make two commits"). Stages the intended files by name, checks the branch name and the message against os-config.yaml with the conventions script, and commits. Never pushes. Do not use on your own initiative.
---

# commit

Only on an explicit request in this turn. Without one, end the work with `Ready to commit: <files>`
and stop. The branch and commit shapes are in `os-config.yaml` under `conventions:` and nowhere
else; do not write a message from memory of the format. The script is
`python3 "<plugin>/modules/conventions/conventions.py"`; from this skill's base directory the plugin
root is two levels up (`../../`).

1. **Branch.** `git -C <repo> branch --show-current`, then `conventions.py branch --check <name>`.
   On exit 1, or on the default or a release branch, stop and show the user the expected shape.
   To propose a name: `conventions.py branch <ticket> --type <type> --slug <slug>` prints one. The
   user creates or renames the branch, or tells you to.
2. **What goes in.** `git -C <repo> status --short` and the diff. One logical change per commit;
   split when the user asked or when unrelated changes are mixed. Leave out scratch files, local
   config and anything that looks like a secret, and say which files you left out.
3. **Gate.** If `/verify` has not passed on this state, run it. Do not commit on a failing gate
   without telling the user first and getting a yes.
4. **For each commit, in order:**
   1. Stage its files by name: `git -C <repo> add <file> <file>`. Never `-A`, `-a` or `.`.
   2. `conventions.py commit-msg` prints the pattern and an example. Fill every placeholder. The
      message says what changed and why.
   3. `conventions.py commit-msg --check "<message>"` must exit 0. Fix the message and check again
      until it does.
   4. `git -C <repo> commit -m "<message>"`. For a body, add a second `-m`.
5. **Report.** `git -C <repo> log --oneline -n <count>` and the list of commits made.

## Rules

- Never push. The user pushes.
- Never amend, rebase or reset unless the user asks for exactly that. Fix a mistake with a new
  commit.
- If a permission prompt or a guard hook stops a git command, say why. Do not work around it.
- If `conventions.py` exits 2, a key is missing from `os-config.yaml`. Name the key, ask the user
  for the team's shape, and do not commit in a format you guessed.
