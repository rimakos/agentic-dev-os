# Verification rules

What the model cannot see on its own. Checks a script can run belong in a hook instead.

## Reading code and state

- Cite code at `origin/<branch>`; a local or symlinked checkout can be stale. Read another ref with
  `git show` or `git worktree`, not `git checkout <ref> -- <path>`.
- `../` inside a symlinked repo is that repo's real parent, not the workspace. Use absolute paths
  before saying a file is missing.
- A grep that finds nothing only covers the paths and refs it searched. Generated clients, DI and
  message subscriptions hide call sites. An absence claim about a document needs the whole
  document scanned.
- To prove a guard does not exist, search for the invariant it would protect, not one mechanism.
- A repo config file names the local default. If the deployed value is not in the repo, say
  unknown.
- When unsure of a fact (a field exists, a fix shipped), check it before writing it to the wiki.

## Running things

- Exit 0 with no output is not a build: check the artifact.
- A suite total from an aborted run is not a result, even with zero failures. Check the log for an
  abort.
- An end-to-end run on a fixture an earlier run already changed proves nothing.
- A regression test that has never failed proves nothing: break the line it guards once and watch
  it go red.
- Unit tests that construct handlers directly don't prove DI wiring: boot the app and hit the path.
- A test with a mocked external client proves which requests go out, not what the service does with
  them.

## Claims

- A screenshot proves the tree it came from, not the pushed SHA.
- A number belongs to what it was measured on. A test name states intent; the assertion must match
  it.
- A code comment is a factual claim too: check it against the code beside it.
- To prove a change landed, search the merged ref for text only that change introduced. "I pushed"
  is a claim too: check the PR head SHA or `git status -sb`.

## Merges

- A clean auto-merge can still break the build. Build and test every merge result, and look hardest
  at files git merged without a conflict.
- When both branches wrote the same helper, check the bodies are equivalent and say which behaviors
  moved.
