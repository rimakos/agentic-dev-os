#!/bin/sh
# PreToolUse (Write|Edit|Bash). On the first wiki page edit of a session, remind
# that a claim is checked before it is written. Once per session (marker keyed on
# session_id), additionalContext only, never blocks. log.md is exempt.

payload=$(cat)
command -v jq >/dev/null 2>&1 || exit 0
ws="${CLAUDE_PROJECT_DIR:-$PWD}"

tool=$(printf '%s' "$payload" | jq -r '.tool_name // empty' 2>/dev/null)
case "$tool" in
  Write|Edit)
    subject=$(printf '%s' "$payload" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
    ;;
  Bash)
    subject=$(printf '%s' "$payload" | jq -r '.tool_input.command // empty' 2>/dev/null)
    case "$subject" in
      *"sed -i"*|*'> '*|*'>>'*|*tee\ *) ;;
      *) exit 0 ;;
    esac
    ;;
  *) exit 0 ;;
esac
[ -n "$subject" ] || exit 0

case "$subject" in
  *"$ws/wiki/log.md"*) exit 0 ;;
  *"$ws/wiki/"*) ;;
  *) exit 0 ;;
esac

sid=$(printf '%s' "$payload" | jq -r '.session_id // empty' 2>/dev/null)
marker="${TMPDIR:-/tmp}/claude-hook-wiki-verify-${sid:-nosession}"
[ -e "$marker" ] && exit 0
touch "$marker"

cat <<'JSON'
{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"Before writing a wiki claim: check it against origin/<branch> or a live query rather than the local checkout, and tag it. Use unknown only for what the repos cannot answer. Rules: wiki/known-issues/verification.md."}}
JSON
exit 0
