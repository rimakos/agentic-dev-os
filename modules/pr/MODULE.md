# pr

## What it does

`pr.py` opens or updates a pull request on Azure DevOps or GitHub, and always shows a preview
first. Without `--yes` it prints the title, target, source branch, ticket, body and the exact
command, and sends nothing. With `--yes` it runs that command. The `/pr` skill passes `--yes` only
after the user approved the preview.

- `describe --title T --body-file F [--ticket ID]`: checks the title and body, prints the preview.
- `create --title T --body-file F [--target BRANCH] [--ticket ID] [--draft] [--yes]`
- `update PR_ID [--title T] [--body-file F] [--yes]`

The body goes to the host as a file (`az ... --description=@<file>`, `gh ... --body-file <file>`),
so backticks, `$VAR`, quotes, `@mentions` and blank lines arrive as written. `az` drops the
newlines at the very end of the file. On Azure DevOps `--ticket` links a work item
(`--work-items`) and a body over 4000 characters is refused before anything is sent. On GitHub the
ticket is linked only if the body names it.

It never pushes. When the branch is not on the remote it prints the push command and exits 3.
Exit 2 means the host is unknown or its CLI is missing, exit 1 an invalid title or body. If the
`conventions` module is installed and a title pattern is configured, the title must match it.

## Prerequisites

- `python3` and `git` on the PATH, and a remote named `origin`.
- Azure DevOps (`dev.azure.com`, `visualstudio.com`): `az` with the `azure-devops` extension,
  signed in (`az extension show --name azure-devops`).
- GitHub (`github.com`): `gh`, signed in (`gh auth status`).

## Install

Nothing to copy. The `/pr` skill runs `<plugin>/modules/pr/pr.py` from the repo.

## Verify

On a pushed branch, from the repo:

```
printf 'What changed.\n' > /tmp/pr-body.md
python3 <plugin>/modules/pr/pr.py create --title "<a title>" --body-file /tmp/pr-body.md
```

It prints the preview, a `Command:` line and `Preview only, nothing was sent`, and exits 0.

## Remove

Nothing to remove.
