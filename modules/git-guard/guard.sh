#!/bin/sh
# Launcher for the git guard (PreToolUse, Bash). Runs guard-git.ts when Node can run TypeScript
# directly (>= 22.18); otherwise runs the older shell guard. Both read the same hook payload on stdin.
dir=$(cd "$(dirname "$0")" && pwd)
payload=$(cat)

# One Node start: the guard itself never exits non-zero, so a failure means this Node cannot run it.
if out=$(printf '%s' "$payload" | node --disable-warning=ExperimentalWarning "$dir/guard-git.ts" 2>/dev/null); then
  printf '%s' "$out"
  exit 0
fi

# Installed copies keep the shell guard beside this file; in the plugin it lives in the template.
old="$dir/block-dangerous-git.sh"
[ -f "$old" ] || old="$dir/../../template/.claude/hooks/block-dangerous-git.sh"
printf '%s' "$payload" | sh "$old"
