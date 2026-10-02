### RTK-hooked output

- The rtk hook rewrites `ls`, `grep`, `git diff`, build and test commands and can return output
  from an earlier state of the tree (deleted files still listed, stale line numbers, build errors
  the raw build doesn't have). Before reporting a build or test failure or a grep finding, re-run
  it raw: `rtk proxy "<cmd>" > <scratch-file> 2>&1`, then read the file.
- `rtk proxy` takes one quoted command. Pipes and redirects inside the quotes reach the underlying
  tool as arguments, so keep the redirect outside the quotes.
- Use one `rtk proxy` per Bash call when the output matters; chaining several with `;` brings the
  compaction back (output like `N matches in 1 files` with `[+N more]`).
