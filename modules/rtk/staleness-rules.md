### RTK-hooked output can be stale — confirm failures with `rtk proxy`

- The rtk hook rewrites `ls`/`grep`/`git diff`/build/test commands and can
  return a cached result from an EARLIER state of the tree (deleted files
  still listed, pre-refactor call sites at line numbers that no longer exist,
  build errors from stale code while the raw build is clean).
- Never report a build/test failure or a grep finding from hooked output
  alone. Re-run it raw: `rtk proxy "<cmd>" > <scratch-file> 2>&1` and read
  the file.
- `rtk proxy` takes ONE quoted command. Pipes/redirects inside the quotes get
  passed to the underlying tool as switches and blow up; keep the redirect
  outside the quotes.
- One `rtk proxy` per Bash call whenever the output matters. Chaining several
  with `;` re-triggers the compaction the proxy exists to bypass: later
  commands come back summarized or truncated. Symptoms: a redirect target far
  smaller than the file should be, or output reading `N matches in 1 files`
  with `[+N more]`. Re-run it alone before concluding anything from it.
