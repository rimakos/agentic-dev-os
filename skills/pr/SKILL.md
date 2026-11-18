---
name: pr
description: Opens a pull request for the current branch, or updates the title and description of an existing one, on Azure DevOps or GitHub. Always shows the preview first and sends only after the user approves it. Triggers on /pr, "open a PR", "create the PR", "update the PR description". Never pushes, comments or votes.
---

# pr

The script is `../../modules/pr/pr.py` from this skill's folder. Run it from the repo the pull
request is for. It previews by default and sends only with `--yes`.

1. **Title and body.** Read the commits and the diff against the target branch. Write the title in
   the repo's convention. Write the body to a file outside the repo, in the repo's PR template if
   it has one, otherwise in four short parts: what changed, why, how it was verified (the command
   or test and its result), and the ticket. Only claims you checked in this session.
2. **Check.** `python3 <script> describe --title "<title>" --body-file <file> [--ticket <id>]`.
   Fix what it rejects (a title that breaks the convention, an empty body) and run it again.
3. **Preview.** New pull request: `python3 <script> create --title "<title>" --body-file <file>
   [--target <branch>] [--ticket <id>] [--draft]`. Existing one: `python3 <script> update <pr id>
   [--title "<title>"] [--body-file <file>]`. Show the user the whole preview, including the
   command line.
4. **Exit 3.** The branch is not on the remote. Show the push command it printed and stop. The
   user pushes. Start again from step 3 when they say it is done.
5. **Send.** Only when the user approves that preview in their reply, run the same command with
   `--yes` and report what the host printed. If they ask for a change, edit the file and go back
   to step 2. An approval given earlier, or for a different preview, does not count.

## Rules

- Never pass `--yes` on a preview the user has not seen.
- Never push, and never post comments, votes or reviews.
- Exit 2 means the host is unknown or its CLI is missing. Say which and stop.
