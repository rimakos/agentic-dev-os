#!/bin/sh
# PreToolUse (Write|Edit|Bash). On the first repo source edit of a session, remind
# that /ticket-impact runs before implementation. Once per session (marker keyed on
# session_id), additionalContext only, never blocks.
#
# A repo file is anything under the workspace root outside the OS folders, or under
# the target of a repo symlink in the workspace root (the layout /os-init creates).

payload=$(cat)
command -v jq >/dev/null 2>&1 || exit 0
ws="${CLAUDE_PROJECT_DIR:-$PWD}"

tool=$(printf '%s' "$payload" | jq -r '.tool_name // empty' 2>/dev/null)
case "$tool" in
  Write|Edit)
    subject=$(printf '%s' "$payload" | jq -r '.tool_input.file_path // empty' 2>/dev/null)
    ;;
  Bash)
    # Auto mode edits through Bash (heredoc, sed), so scan the command, but only
    # when it writes; otherwise every grep and test run would match.
    subject=$(printf '%s' "$payload" | jq -r '.tool_input.command // empty' 2>/dev/null)
    case "$subject" in
      *"sed -i"*|*'> '*|*'>>'*|*tee\ *) ;;
      *) exit 0 ;;
    esac
    ;;
  *) exit 0 ;;
esac
[ -n "$subject" ] || exit 0

# Generated, vendored and OS files never count.
case "$subject" in
  *"$ws/wiki/"*|*"$ws/.claude/"*|*"$ws/metrics/"*|*/node_modules/*|*/generated/*|*/Migrations/*) exit 0 ;;
esac

hit=""
case "$subject" in
  *"$ws/"*) hit=1 ;;
esac
if [ -z "$hit" ]; then
  for link in "$ws"/*; do
    [ -L "$link" ] || continue
    target=$(cd "$link" 2>/dev/null && pwd -P) || continue
    case "$subject" in
      *"$target/"*) hit=1; break ;;
    esac
  done
fi
[ -n "$hit" ] || exit 0

sid=$(printf '%s' "$payload" | jq -r '.session_id // empty' 2>/dev/null)
marker="${TMPDIR:-/tmp}/claude-hook-ticket-impact-${sid:-nosession}"
[ -e "$marker" ] && exit 0
touch "$marker"

cat <<'JSON'
{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"First repo source edit this session. If /ticket-impact has not run for this ticket, run it before going further: it routes to the repo's own rules and surfaces the hidden scope."}}
JSON
exit 0
