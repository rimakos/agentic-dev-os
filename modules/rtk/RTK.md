# RTK

A hook rewrites shell commands to run through `rtk`, a token-saving proxy (`git status` runs as
`rtk git status`). The output is compressed, and some rewrites differ from the real tool:
`rtk find` refuses compound predicates such as `-o` and `-prune`, and `rtk git diff` prints a
summary without `+++ b/` file headers, so it is not a valid patch. When exact output matters (a
diff saved to a file, a failure that looks wrong), run `rtk proxy <cmd>` or call the tool by
absolute path (`/usr/bin/find`).
