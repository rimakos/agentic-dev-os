---
name: address-pr-comments
description: Work through the open review comments on a PR (Azure DevOps or GitHub): fetch the active threads, show them grouped by file, ask how to handle them, plan and make the fixes, draft the replies, and turn any comment that will come up again into a knowledge entry. Usage /address-pr-comments <PR URL or id> [reviewer]. Triggers on /address-pr-comments, "address the PR comments", "work through the review", "fix what the reviewer said". Never posts replies, resolves threads or commits.
---

# address-pr-comments

## 1. Fetch the open threads

From the PR URL or id, read the threads with the host's own tool:

- **Azure DevOps:** `az repos pr show --id <id>` for the branches, and the threads with
  `az devops invoke --area git --resource pullRequestThreads --route-parameters
  project=<project> repositoryId=<repo> pullRequestId=<id> --api-version 7.1`. If `az` is not signed
  in to that organisation, ask the user to sign in (`az login` or a PAT in `AZURE_DEVOPS_EXT_PAT`).
  Never print or copy a token.
- **GitHub:** `gh pr view <id> --json headRefName,baseRefName` and
  `gh api repos/{owner}/{repo}/pulls/<id>/comments` plus the review bodies.
- If neither works, ask the user to paste the comments.

Save large responses to a temp file before parsing. Keep threads that are active (not fixed, closed
or resolved) and comments written by people (Azure DevOps `commentType` `text`). With a reviewer
argument, keep threads whose first comment is theirs.

## 2. Show them and ask

Group by file, in order, with the whole conversation per thread:

```
### <file>:<line>  (<author>)
<comment>
```

Ask how to handle them: all of them, per comment, or specific instructions. Wait for the answer.

## 3. Plan, then fix

1. Check out the PR's source branch only if the user is on it already or asks; otherwise say which
   branch the fixes belong on and stop.
2. For each comment to address: read the code it points at, state the reviewer's intent in one line,
   and the change that meets it. Show the plan and wait for a yes.
3. Make the changes in the style of the surrounding code, following the repo's rules (`CLAUDE.md`,
   `AGENTS.md`). Run what proves each fix: the test, the build or the script the comment was about.
   A comment about a clean build is fixed when the clean build passes, not when the file looks right.

## 4. Replies and lessons

- **Replies:** one draft per thread, in the user's voice: what changed and where, or why not. The
  user posts them.
- **Lessons:** for each comment, ask whether the next person would hit it again. If yes, it is a
  candidate for the knowledge base (`memory.root` in `os-config.yaml`): name the page to add or fix
  and the one-line fact with its evidence, for `/wrap` to file. A pattern about reviewing rather than
  about the system goes to `review.lessons` as one line with the PR number.

## Report

```
Addressed: <n> of <m> threads      Branch: <branch>
<file:line>  <what changed>  proof: <command and result>
Skipped:     <thread> because <reason>
Replies:     drafted below, not posted
Lessons:     <page or line to add>, or none
Ready to commit: <files>
```
