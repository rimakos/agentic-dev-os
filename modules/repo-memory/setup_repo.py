#!/usr/bin/env python3
"""Install or upgrade repo-memory for one repo, without writing anything the repo would commit.

Run from the repo root:
    python3 <plugin>/modules/repo-memory/setup_repo.py --name <project> [options]

  --name <project>    data folder ~/<project>-os (required)
  --memory <path>     the repo's knowledge base folder (default docs/knowledge)
  --start <skill>     the repo's skill for starting work, for the first-edit reminder (for example /start-work)
  --gate <path>       the repo's leak or word check that takes file paths, run before each push
  --lessons <file>    review lessons to start from; lines you do not have yet are added
  --rules yes|no      add the core working rules to the global CLAUDE.md (asked when run in a terminal)

Safe to run again: scripts are refreshed, your lessons, metrics, config and own settings are kept, and
the hook entries pointing into the data folder are replaced, never added twice. In the repo it only
touches the git-ignored .claude/settings.local.json, after a backup into the data folder. Another
agentic OS found on this machine is reported and left untouched. Undo with /agentic-dev-os:os-remove.
"""
import datetime
import glob
import json
import os
import shutil
import subprocess
import sys

MODULE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(os.path.dirname(MODULE))
REPO = os.path.realpath(os.getcwd())
HOME = os.path.expanduser("~")
CONFIG_DIR = os.environ.get("CLAUDE_CONFIG_DIR", os.path.join(HOME, ".claude"))
GLOBAL_MD = os.path.join(CONFIG_DIR, "CLAUDE.md")
LOCAL = os.path.join(REPO, ".claude", "settings.local.json")
ASK = [f"Bash({prefix}git {sub}:*)" for prefix in ("", "rtk ")
       for sub in ("add", "commit", "push", "stash", "checkout -b", "switch -c")]
BEGIN, END = "<!-- AGENTIC-DEV-OS:BEGIN core -->", "<!-- AGENTIC-DEV-OS:END core -->"
CORE = BEGIN + """
## Working with Claude (agentic-dev-os)

- Keep answers brief and plain: the outcome first, short caveats, no filler.
- Git writes are mine. Claude asks before git add, commit, push, stash or a new branch, because a
  person owns what goes into the shared history. Code work ends with "Ready to commit: <files>".
- Nothing is posted to the tracker, a PR or anyone else unless I ask for it in that message.
- Stop before anything hard to undo.
- When a request can be read two ways, say which reading you took. Ask only when the readings lead to
  different work.
- Change only what was asked, in the style of the code around it. Mention nearby problems instead of
  fixing them.
- Use a subagent only for large independent tracks.
- The plugin's skills are called /agentic-dev-os:<name>.
""" + END + "\n"


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def stop(message):
    sys.exit("Stopped: " + message)


def git(*args):
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True)


def read_json(path):
    return json.load(open(path)) if os.path.exists(path) else {}


NAME = arg("--name") or stop("--name <project> is required.")
DATA = os.path.join(HOME, f"{NAME}-os")
MEMORY = arg("--memory", "docs/knowledge").strip("/")
START, GATE, LESSONS = arg("--start"), arg("--gate"), arg("--lessons")
VERSION = read_json(os.path.join(PLUGIN, ".claude-plugin", "plugin.json")).get("version", "?")

top = git("rev-parse", "--show-toplevel").stdout.strip()
if not top or os.path.realpath(top) != REPO:
    stop("run this from the root of the repo.")
if not os.path.isdir(os.path.join(REPO, MEMORY)):
    stop(f"{MEMORY}/ not found in this repo.")
if git("check-ignore", "-q", ".claude/settings.local.json").returncode != 0:
    stop(".claude/settings.local.json is not git-ignored here, so the hooks would show up as a change.")
if GATE and not os.path.exists(os.path.join(REPO, GATE)):
    stop(f"--gate {GATE} not found in this repo.")

# What is already here
old = read_json(os.path.join(DATA, "os-manifest.json"))
upgrading = bool(old)
others = []
for manifest in glob.glob(os.path.join(HOME, "*", ".claude", "os-manifest.json")) + \
        glob.glob(os.path.join(HOME, "*", "*", ".claude", "os-manifest.json")) + \
        glob.glob(os.path.join(HOME, "*-os", "os-manifest.json")):
    folder = os.path.dirname(manifest)
    if os.path.realpath(folder) != os.path.realpath(DATA):
        others.append(os.path.dirname(folder) if folder.endswith(".claude") else folder)

actions = list(old.get("actions", [])) or [{"type": "plugin_installed", "name": "agentic-dev-os@agentic-dev-os", "scope": "local"}]


def record(action):
    if action not in actions:
        actions.append(action)


for sub in ("hooks", "metrics", "reviews", "backups"):
    path = os.path.join(DATA, sub)
    if not os.path.isdir(path):
        os.makedirs(path)
        record({"type": "dir_created", "path": path})

# Scripts: always refreshed from the plugin
repo_settings = read_json(os.path.join(REPO, ".claude", "settings.json"))
own_guard = any(g.get("matcher") == "Bash" for g in repo_settings.get("hooks", {}).get("PreToolUse", []))
scripts = [(os.path.join(MODULE, f), "hooks/" + f) for f in ("wrap_check.py", "repo_hooks.py")]
scripts.append((os.path.join(MODULE, "harvest_extract.py"), "harvest_extract.py"))
if not own_guard:
    scripts.append((os.path.join(PLUGIN, "template", ".claude", "hooks", "block-dangerous-git.sh"), "hooks/block-dangerous-git.sh"))
for source, target in scripts:
    shutil.copy(source, os.path.join(DATA, target))
    record({"type": "file_created", "path": os.path.join(DATA, target)})

# Your data: kept; starter lessons only add lines you do not have
kept = []
lessons = os.path.join(DATA, "reviews", "lessons.md")
starter = open(LESSONS).read() if LESSONS else "# Review lessons\n\nPatterns reviewers flagged. Questions /pr-review asks of a diff, not findings.\n"
if os.path.exists(lessons):
    mine = open(lessons).read()
    new = [line for line in starter.splitlines() if line.startswith("- ") and line not in mine]
    if new:
        open(lessons, "a").write(("" if mine.endswith("\n") else "\n") + "\n".join(new) + "\n")
    kept.append(f"reviews/lessons.md (+{len(new)} line(s))")
else:
    open(lessons, "w").write(starter)
    record({"type": "file_created", "path": lessons})

config = os.path.join(DATA, "os-config.yaml")
if os.path.exists(config):
    kept.append("os-config.yaml")
else:
    open(config, "w").write(f"""# agentic-dev-os, {os.path.basename(REPO)} (repo-memory mode). Lives outside the repo.
workspace:
  name: {NAME}
repos:
  - name: {os.path.basename(REPO)}
    path: {REPO}
memory:
  mode: repo
  root: {MEMORY}
  wrap: /wrap
review:
  lessons: {lessons}
""")
    record({"type": "file_created", "path": config})

# settings.local.json: replace our hook entries, keep everything else
backups = dict(old.get("backups", {}))
settings = read_json(LOCAL)
if os.path.exists(LOCAL):
    label = datetime.datetime.now().strftime("%Y%m%d-%H%M%S") if upgrading else "pre-os"
    backup = os.path.join(DATA, "backups", f"settings.local.json.{label}.bak")
    shutil.copy(LOCAL, backup)
    backups.setdefault(LOCAL, backup)

hooks = settings.setdefault("hooks", {})
ours = os.path.join(DATA, "hooks") + os.sep
for event in list(hooks):
    groups = []
    for group in hooks[event]:
        group["hooks"] = [h for h in group.get("hooks", []) if ours not in h.get("command", "")]
        if group["hooks"]:
            groups.append(group)
    hooks[event] = groups

wrap, reminders = f'python3 "{ours}wrap_check.py"', f'python3 "{ours}repo_hooks.py"'
bash = [f"{wrap} pre-commit --memory {MEMORY}", f"{reminders} outbound"]
if not own_guard:
    bash.insert(0, f'sh "{ours}block-dangerous-git.sh"')
if GATE:
    bash.append(f"{reminders} pre-push --gate {GATE}")
edits = [f"{reminders} knowledge-edit --memory {MEMORY}"]
if START:
    edits.append(f"{reminders} first-edit --start {START}")


def entry(command, timeout=10):
    return {"type": "command", "timeout": timeout, "command": command}


hooks.setdefault("SessionStart", []).append(
    {"hooks": [entry(f'{wrap} session-start --memory {MEMORY} --append "{DATA}/metrics/wrap-rate.tsv"', 15)]})
hooks.setdefault("PreToolUse", []).append({"matcher": "Bash", "hooks": [entry(c, 60 if "pre-push" in c else 10) for c in bash]})
hooks["PreToolUse"].append({"matcher": "Write|Edit|Bash", "hooks": [entry(c) for c in edits]})
ask = settings.setdefault("permissions", {}).setdefault("ask", [])
ask.extend(rule for rule in ASK if rule not in ask)

os.makedirs(os.path.dirname(LOCAL), exist_ok=True)
json.dump(settings, open(LOCAL, "w"), indent=2)
for pointer in ("hooks.SessionStart", "hooks.PreToolUse", "permissions.ask"):
    record({"type": "settings_entry", "path": LOCAL, "pointer": pointer})

# Core block: the working rules, in the global CLAUDE.md
core = old.get("core_block", "skipped")
text = open(GLOBAL_MD).read() if os.path.exists(GLOBAL_MD) else ""
answer = arg("--rules")
if BEGIN in text and END in text:
    open(GLOBAL_MD, "w").write(text[:text.index(BEGIN)] + CORE.rstrip("\n") + text[text.index(END) + len(END):])
    core = "global"
elif answer or sys.stdin.isatty():
    if not answer:
        answer = input("\nAdd the agentic-dev-os working rules to your global CLAUDE.md "
                       f"({'your own rules there stay' if text.strip() else 'it is empty'})? [Y/n] ")
    if answer.strip().lower() in ("", "y", "yes"):
        if text:
            backup = os.path.join(DATA, "backups", "CLAUDE.md.pre-os.bak")
            shutil.copy(GLOBAL_MD, backup)
            backups.setdefault(GLOBAL_MD, backup)
        os.makedirs(CONFIG_DIR, exist_ok=True)
        open(GLOBAL_MD, "w").write(text + ("\n\n" if text.strip() else "") + CORE)
        record({"type": "block_injected", "path": GLOBAL_MD, "module": "core"})
        core = "global"

skipped = [{"name": "metrics", "reason": "repo mode: repo-memory keeps wrap-rate.tsv instead"}]
if own_guard:
    skipped.append({"name": "block-dangerous-git", "reason": "the repo has its own Bash guard hook"})
modules = sorted(set(old.get("modules", [])) | {"core", "repo-memory"})
manifest = {
    "os_version": VERSION,
    "installed_at": old.get("installed_at", datetime.date.today().isoformat()),
    **({"upgraded_at": datetime.date.today().isoformat(), "upgraded_from": old.get("os_version")} if upgrading else {}),
    "mode": "repo",
    "repo": REPO,
    "modules": modules,
    "modules_skipped": skipped,
    "core_block": core,
    "skill_collisions": old.get("skill_collisions", []),
    "actions": actions,
    "backups": backups,
}
json.dump(manifest, open(os.path.join(DATA, "os-manifest.json"), "w"), indent=2)

report = subprocess.run(["python3", os.path.join(DATA, "hooks", "wrap_check.py"), "report", "--memory", MEMORY],
                        cwd=REPO, capture_output=True, text=True).stdout
status = git("status", "--short").stdout.strip()
names = ["session start"] + [c.split()[2] if c.startswith("python3") else "git guard" for c in bash + edits]
print(f"\n{'Upgraded' if upgrading else 'Set up'} {DATA} to agentic-dev-os {VERSION}"
      + (f" (was {old.get('os_version')})." if upgrading else "."))
if kept:
    print("Kept yours: " + ", ".join(kept))
print(f"Hooks in .claude/settings.local.json: {len(names)} ({', '.join(names)}). Working rules: {core}.")
for other in others:
    print(f"Found an earlier agentic OS at {other}: left untouched. /agentic-dev-os:harvest can read its wiki.")
print("\n" + report)
print("git status:", status or "clean (nothing in the repo changed)")
