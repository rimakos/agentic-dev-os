# PR review

- Read PR content by SHA, not the working tree, since the checked-out branch is usually something
  else. Fetch source and target, then `git diff <target>...<source>`, `git show <source>:<path>`,
  and `git grep -n <pattern> <sha> -- <path>` for call sites. Working-tree reads only for files not
  in the diff.
- A compaction summary is not evidence. Re-derive line numbers and counts at the head SHA after a
  `/compact`.
- Verify each finding against the code before reporting it, and drop it if the same pattern exists
  in analogous code or the fix would not compile. Report only fixes that are needed, with a go or
  no-go verdict.
- Verify a finding by running it where you can: a scratch `git worktree add --detach <sha>`.
- `git fetch` and compare before working a branch someone else can push to.
