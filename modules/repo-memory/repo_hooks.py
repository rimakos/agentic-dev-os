#!/usr/bin/env python3
"""Just-in-time reminders for a repo that keeps its own rules, without writing anything into the repo.

Each mode is a PreToolUse hook. A reminder fires once per session at the moment the rule matters (outbound and commit-msg: each time),
instead of relying on a paragraph read at session start.

  first-edit      Write|Edit|Bash. First source edit of a session: confirm the repo's start skill ran
                  (--start /start-work).
  knowledge-edit  Write|Edit|Bash. First write into the knowledge base (--memory docs/knowledge): check
                  the claim before tagging it confirmed.
  outbound        Bash. Before a PR is created or commented on (az, gh): check every claim in the text,
                  and reread it with the repo's client-safe check, because file-based checks do not see it.
  pre-push        Bash. Before git push: runs the repo's gate (--gate tools/leak-check.sh) on the files
                  the push sends. Blocks the push (exit 2) only when the gate reports a finding.
  commit-msg      Bash. Before git commit -m: names conventions.commit from os-config.yaml when the
                  message's first line does not fit it. Every time, not once. Needs conventions.py
                  (modules/conventions) next to this file. A message from -F or a heredoc is not read.

Every mode except a pre-push finding exits 0, and any error inside it exits 0.
"""
import json, os, re, shlex, subprocess, sys, tempfile

WRITING_BASH = re.compile(r"sed -i|\btee\b|(?<![\d&>=-])>>?\s*(?!&|/dev/null)[\w./~$]")
QUOTED = re.compile(r"'[^']*'|\"[^\"]*\"")  # a quoted string is one word: an arrow inside it is not a redirect
OUTBOUND = re.compile(r"\baz\s+(rest|repos\s+pr\s+(create|update)|devops\s+invoke)\b|\bgh\s+pr\s+(create|comment|review)\b")
PUSH = re.compile(r"(^|[;&|]\s*)(rtk\s+(proxy\s+)?)?git\s+push(\s|$)")
COMMIT = re.compile(r"(^|[;&|\n]\s*)(rtk\s+(proxy\s+)?)?git\s+commit(\s|$)")


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def say(text):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": text}}))


def once(payload, kind):
    """True the first time this kind fires in this session."""
    marker = os.path.join(tempfile.gettempdir(), f"claude-repo-hooks-{kind}-{payload.get('session_id', 'none')}")
    if os.path.exists(marker):
        return False
    open(marker, "w").close()
    return True


def written(payload, repo):
    """The repo-relative file a Write/Edit targets, '(shell)' for a writing Bash command, else None."""
    tool, inp = payload.get("tool_name"), payload.get("tool_input", {})
    if tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        target = os.path.realpath(inp.get("file_path") or inp.get("notebook_path") or "")
        return os.path.relpath(target, repo) if target.startswith(repo + os.sep) else None
    if tool == "Bash" and WRITING_BASH.search(QUOTED.sub("Q", inp.get("command", ""))):
        return "(shell) " + inp["command"]
    return None


def first_edit(payload, repo):
    path = written(payload, repo)
    if not path or re.search(r"(^|\s|/)(docs|\.claude)/", path):
        return
    if once(payload, "first-edit"):
        skill = arg("--start", "/start-work")
        say(f"First source edit this session. Confirm {skill} ran for this work (plan item, requirement, "
            f"whether a spec must be approved first). If it has not, run it before going further.")


def knowledge_edit(payload, repo):
    path = written(payload, repo)
    memory = arg("--memory", "docs/knowledge").strip("/")
    if not path or memory + "/" not in path:
        return
    if once(payload, "knowledge-edit"):
        say(f"Before writing this knowledge claim: check it now (run the command, read the file:line) and only "
            f"then tag it confirmed. A doc saying so is not evidence. Teammates file pages too, so first run "
            f"git fetch and read origin/main:{memory}/index.md: if a page there already covers this, update "
            f"that page instead of adding a new one. Follow {memory}/README.md for the page shape, and add "
            f"the index line.")


def outbound(payload, repo):
    if payload.get("tool_name") != "Bash" or not OUTBOUND.search(payload.get("tool_input", {}).get("command", "")):
        return
    say("Before this goes on the PR: every factual claim in the text (a count, a line number, a mechanism, "
        "'nothing else does this') needs its check run first, or becomes an open question. The repo's leak "
        "check only scans files, so reread this text with the repo's client-safe check if it has one.")


def pre_push(payload, repo):
    command = payload.get("tool_input", {}).get("command", "")
    gate = arg("--gate")
    if payload.get("tool_name") != "Bash" or not gate or not PUSH.search(command):
        return
    def git(*args):
        return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True).stdout.strip()
    base = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if base:
        files = git("diff", "--name-only", "--diff-filter=d", f"{base}...HEAD").splitlines()
    else:  # a new branch: the files of the commits no remote branch has yet
        files = git("log", "--name-only", "--format=", "HEAD", "--not", "--remotes").splitlines()
    files = sorted({f for f in files if f and os.path.exists(os.path.join(repo, f))})
    if not files:
        return
    try:
        result = subprocess.run([os.path.join(repo, gate), *files], cwd=repo, capture_output=True, text=True, timeout=50)
    except (OSError, subprocess.TimeoutExpired) as error:
        say(f"{gate} could not run before this push ({type(error).__name__}), so the push is unchecked. "
            f"Say so to the user.")
        return
    if result.returncode == 1:
        sys.stderr.write(f"BLOCKED before push: {gate} found something in the files this push sends.\n"
                         f"{result.stdout}{result.stderr}\nFix it, then push again. The push was not run.\n")
        sys.exit(2)
    if result.returncode != 0:
        say(f"{gate} could not run before this push (exit {result.returncode}), so the push is unchecked. "
            f"Say so to the user.")


def commit_msg(payload, repo):
    command = payload.get("tool_input", {}).get("command", "")
    if payload.get("tool_name") != "Bash" or not COMMIT.search(command):
        return
    words = shlex.split(command)
    words = words[words.index("commit"):]
    message = next((words[i + 1] for i, w in enumerate(words[:-1]) if w == "--message" or re.fullmatch("-[a-z]*m", w)), "")
    if not message or "$(" in message or "`" in message:
        return
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path[:0] = [here, os.path.join(os.path.dirname(here), "conventions")]
    import conventions
    rules = conventions.read_config(conventions.find_config(repo))[1]
    failed = conventions.mismatch("commit", message.split("\n")[0], rules)
    if failed:
        say(f"This commit message does not fit the team's pattern in os-config.yaml, conventions.commit: "
            f"{rules['commit']} ({failed}). Rewrite the first line to fit before committing.")


MODES = {"first-edit": first_edit, "knowledge-edit": knowledge_edit, "outbound": outbound, "pre-push": pre_push,
         "commit-msg": commit_msg}

if __name__ == "__main__":
    try:
        payload = json.load(sys.stdin)
        repo = os.path.realpath(os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd())
        MODES[sys.argv[1]](payload, repo)
    except SystemExit:
        raise
    except Exception:
        pass
    sys.exit(0)
