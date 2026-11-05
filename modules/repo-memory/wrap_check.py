#!/usr/bin/env python3
"""Make the repo's own /wrap happen, without writing anything into the repo.

Reads Claude Code's session transcripts for this project (they live under ~/.claude/projects/).
A session "needs a wrap" when it edited repo files outside the knowledge base and never ran /wrap.

  session-start   SessionStart hook. Names the sessions since the last /wrap that changed files.
  pre-commit      PreToolUse hook on Bash. Before the first git commit, git push or PR create of a
                  session that needs a wrap, adds a reminder. Once per session, never blocks.
  report          Prints one TSV row: date, sessions, sessions_with_edits, wrapped, knowledge_commits.
                  With --append FILE, appends it there (once per day).

Options: --memory <path in the repo, default docs/knowledge>  --days <window, default 30>
"""
import json, os, re, subprocess, sys, tempfile, time
from datetime import date

WRAP = re.compile(r'<command-name>/(?:[\w-]+:)?wrap</command-name>|"skill"\s*:\s*"(?:[\w-]+:)?wrap"')
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
WRITING_BASH = re.compile(r"sed -i|\btee\b|(?<![\d&>])>>?\s*(?!&|/dev/null)[\w./~$\"']")


def arg(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def project_dir(cwd):
    return os.path.join(os.path.expanduser("~/.claude/projects"), re.sub(r"[^A-Za-z0-9]", "-", cwd))


def scan(path, repo, memory):
    """(edited repo files outside memory, ran /wrap) for one transcript."""
    edited, wrapped = set(), False
    try:
        lines = open(path, encoding="utf-8", errors="replace")
    except OSError:
        return edited, wrapped
    for line in lines:
        if WRAP.search(line):
            wrapped = True
        if '"tool_use"' not in line:
            continue
        try:
            content = json.loads(line).get("message", {}).get("content", [])
        except ValueError:
            continue
        for item in content if isinstance(content, list) else []:
            if item.get("type") != "tool_use":
                continue
            inp = item.get("input", {})
            if item.get("name") in EDIT_TOOLS:
                target = inp.get("file_path") or inp.get("notebook_path") or ""
            elif item.get("name") == "Bash" and WRITING_BASH.search(inp.get("command", "")):
                target = os.path.join(repo, "(shell edit)")
            else:
                continue
            target = os.path.realpath(target)
            if target.startswith(repo + os.sep) and not target.startswith(memory + os.sep):
                edited.add(os.path.relpath(target, repo))
    return edited, wrapped


def sessions(folder, skip=None, days=30):
    """Transcripts in this project, newest first, within the window."""
    cutoff = time.time() - days * 86400
    try:
        names = [n for n in os.listdir(folder) if n.endswith(".jsonl")]
    except OSError:
        return []
    paths = [os.path.join(folder, n) for n in names]
    paths = [p for p in paths if p != skip and os.path.getmtime(p) >= cutoff]
    return sorted(paths, key=os.path.getmtime, reverse=True)


def session_start(payload, repo, memory):
    current = payload.get("transcript_path")
    folder = os.path.dirname(current) if current else project_dir(repo)
    pending = []
    for path in sessions(folder, skip=current, days=14):
        edited, wrapped = scan(path, repo, memory)
        if wrapped:
            break
        if edited:
            pending.append((path, edited))
    if not pending:
        return
    files = sorted({f for _, e in pending for f in e})
    when = time.strftime("%d %b %H:%M", time.localtime(os.path.getmtime(pending[0][0])))
    print(f"{len(pending)} earlier session(s) here changed files and ended without /wrap "
          f"(latest {when}). Before new work, offer the user /wrap for them, so what they "
          f"learned reaches {os.path.relpath(memory, repo)}/. Files: " + ", ".join(files[:8]))


def pre_commit(payload, repo, memory):
    command = payload.get("tool_input", {}).get("command", "")
    if not re.search(r"\bgit\s+(commit|push)\b|\b(gh|az\s+repos)\s+pr\s+create\b", command):
        return
    sid = payload.get("session_id", "nosession")
    marker = os.path.join(tempfile.gettempdir(), f"claude-hook-wrap-{sid}")
    if os.path.exists(marker):
        return
    edited, wrapped = scan(payload.get("transcript_path", ""), repo, memory)
    if wrapped or not edited:
        return
    open(marker, "w").close()
    note = (f"This session changed {len(edited)} file(s) and /wrap has not run. The repo asks for "
            f"knowledge pages in the same change, so suggest /wrap to the user before this "
            f"{'push' if 'push' in command else 'commit'}, or say why there is nothing to file.")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": note}}))


def report(repo, memory, days):
    rows = [scan(p, repo, memory) for p in sessions(project_dir(repo), days=days)]
    with_edits = [r for r in rows if r[0]]
    log = subprocess.run(["git", "-C", repo, "log", f"--since={days} days ago", "--format=%h", "--",
                          os.path.relpath(memory, repo)], capture_output=True, text=True).stdout
    row = [date.today().isoformat(), len(rows), len(with_edits),
           sum(1 for r in with_edits if r[1]), len(log.split())]
    line = "\t".join(map(str, row))
    out = arg("--append", None)
    if not out:
        print("date\tsessions\tsessions_with_edits\twrapped\tknowledge_commits\n" + line)
        return
    if os.path.exists(out) and open(out).read().find(row[0]) != -1:
        return
    new = not os.path.exists(out)
    with open(out, "a") as f:
        if new:
            f.write("date\tsessions\tsessions_with_edits\twrapped\tknowledge_commits\n")
        f.write(line + "\n")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "report"
    payload = {}
    if mode != "report":
        try:
            payload = json.load(sys.stdin)
        except ValueError:
            return
    repo = os.path.realpath(os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd())
    memory = os.path.join(repo, arg("--memory", "docs/knowledge"))
    if mode == "session-start":
        session_start(payload, repo, memory)
        if arg("--append", None):
            report(repo, memory, int(arg("--days", "30")))
    elif mode == "pre-commit":
        pre_commit(payload, repo, memory)
    else:
        report(repo, memory, int(arg("--days", "30")))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # a reminder hook must never break a session
    sys.exit(0)
