#!/usr/bin/env python3
"""The repo's real gate and the team's branch and commit shapes, read from os-config.yaml and checked
here instead of restated in prose.

    python3 conventions.py verify [--repo <name>]
    python3 conventions.py branch <ticket> --type <type> --slug <slug>
    python3 conventions.py branch --check <name>
    python3 conventions.py commit-msg [--check "<message>"]

verify runs the repo's verify_cmd (the command CI runs) in its path and exits with that command's code.
branch prints a name and never runs git. A check exits 0 on a match and 1 with what failed.
Exit 2 means the config lacks something; the message names the key.

os-config.yaml is --config <path>, else os-config.yaml in $CLAUDE_PROJECT_DIR, the current
folder or a folder above it, else (repo-memory mode) the one in the data folder whose
hooks/wrap_check.py that folder's .claude/settings.local.json runs.
"""
import json, os, re, subprocess, sys

SLUG = "[a-z0-9]+(?:-[a-z0-9]+)*"
SAMPLE = {"A": "ABC", "a": "abc", "0": "123"}


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def find_config(start):
    """Path of the os-config.yaml that governs the folder `start`, or None."""
    folders = [os.path.realpath(start)]
    while os.path.dirname(folders[-1]) != folders[-1]:
        folders.append(os.path.dirname(folders[-1]))
    if os.environ.get("CLAUDE_PROJECT_DIR"):
        folders.insert(0, os.environ["CLAUDE_PROJECT_DIR"])
    for folder in folders:
        config = os.path.join(folder, "os-config.yaml")
        if os.path.exists(config):
            return config
        local = os.path.join(folder, ".claude", "settings.local.json")
        if not os.path.exists(local):
            continue
        hooks = json.load(open(local)).get("hooks", {})
        commands = [hook.get("command", "") for groups in hooks.values() for group in groups for hook in group.get("hooks", [])]
        for command in commands:
            found = re.search(r'(?:"([^"]+)|(\S+))/hooks/wrap_check\.py', command)
            if found:
                return os.path.join(found.group(1) or found.group(2), "os-config.yaml")
    return None


def value(text):
    """A YAML scalar or inline list, as far as os-config.yaml uses them. Quoted text is taken as written."""
    text = text.strip()
    if text[:1] == "[":
        return [value(part) for part in text[1:text.index("]")].split(",") if part.strip()]
    if text[:1] in ("'", '"'):
        return text[1:text.index(text[0], 1)]
    return "" if text.startswith("#") else text.split(" #")[0].strip()


def read_config(path):
    """(repos, conventions) from os-config.yaml: the two sections this script needs, without a YAML library."""
    repos, conventions, section, key = [], {}, None, None
    for line in open(path, encoding="utf-8"):
        item = line.strip()
        if not item or item.startswith("#"):
            continue
        if not line[0].isspace():
            section = item.split(":")[0]
        elif section == "repos":
            if item.startswith("- "):
                repos.append({})
                item = item[2:]
            key, _, rest = item.partition(":")
            repos[-1][key.strip()] = value(rest)
        elif section == "conventions":
            if item.startswith("- "):
                conventions[key].append(value(item[2:]))
            else:
                key, _, rest = item.partition(":")
                key = key.strip()
                conventions[key] = value(rest) or []
    return repos, conventions


def pieces(kind, conventions):
    """conventions.<kind> ("branch" or "commit") as (label, regex) pieces, literals and placeholders in order."""
    pattern = conventions.get(kind)
    if not pattern:
        raise ValueError(f"conventions.{kind} is not set")
    known = {"ticket": conventions.get("ticket_pattern")}
    if kind == "branch":
        known.update(type="|".join(re.escape(t) for t in conventions.get("branch_types") or []), slug=SLUG)
    else:
        known.update(type="[a-z]+", scope="[a-z0-9-]+", message=r"\S.*")
    out = []
    for i, piece in enumerate(re.split(r"<(\w+)>", pattern)):
        if i % 2 == 0:
            if piece:
                out.append((f'"{piece}"', re.escape(piece)))
        elif piece not in known:
            raise ValueError(f"unknown placeholder <{piece}> in conventions.{kind}; it takes {' '.join(f'<{k}>' for k in known)}")
        elif not known[piece]:
            key = "branch_types" if piece == "type" else "ticket_pattern"
            raise ValueError(f"conventions.{key} is not set, and conventions.{kind} uses <{piece}>")
        else:
            out.append((f"<{piece}> ({known[piece]})", f"(?:{known[piece]})"))
    return out


def mismatch(kind, text, conventions):
    """None when text fits conventions.<kind>, else the first piece of the pattern it fails at."""
    built = ""
    for label, regex in pieces(kind, conventions):
        built += regex
        if not re.match(built, text):
            return f"no match at {label}"
    return None if re.fullmatch(built, text) else "extra text after the pattern"


def check(kind, text, conventions):
    failed = mismatch(kind, text, conventions)
    if failed:
        print(f'"{text}" does not match conventions.{kind}: {conventions[kind]}\n  failed: {failed}')
    return 1 if failed else 0


def verify(repos, config):
    name, here = arg("--repo"), os.path.realpath(os.getcwd())
    for repo in repos:
        repo["path"] = os.path.realpath(os.path.join(os.path.dirname(config), repo.get("path", "")))
    if name:
        chosen = [r for r in repos if r.get("name") == name]
    else:
        chosen = [r for r in repos if (here + os.sep).startswith(r["path"] + os.sep)]
    if not chosen:
        listed = ", ".join(f"{r.get('name')} ({r.get('verify_cmd') or 'verify_cmd not set'})" for r in repos)
        why = f"no repo named {name}" if name else "the current folder is in no configured repo"
        raise ValueError(f"{why}; pass --repo <name>. Repos in {config}: {listed or 'none'}")
    repo = max(chosen, key=lambda r: len(r["path"]))
    if not repo.get("verify_cmd"):
        raise ValueError(f"verify_cmd is empty for repo {repo['name']}: set repos[].verify_cmd in {config} "
                         f"to the command CI runs for it")
    print(f"verify {repo['name']}: {repo['verify_cmd']} (in {repo['path']})", flush=True)
    code = subprocess.run(repo["verify_cmd"], shell=True, cwd=repo["path"]).returncode
    print(f"verify {repo['name']}: {'pass' if code == 0 else f'FAIL (exit {code})'}")
    return code


def branch(conventions):
    if "--check" in sys.argv:
        return check("branch", arg("--check"), conventions)
    name = (conventions.get("branch") or "").replace("<type>", arg("--type", "")) \
        .replace("<ticket>", sys.argv[2]).replace("<slug>", arg("--slug", ""))
    if check("branch", name, conventions):
        return 1
    print(name)
    return 0


def commit_msg(conventions):
    if "--check" in sys.argv:
        return check("commit", arg("--check").split("\n")[0], conventions)
    pieces("commit", conventions)
    pattern = conventions["commit"]
    ticket = re.sub(r"\[(.)[^\]]*\]\+?", lambda m: SAMPLE.get(m.group(1), m.group(1)), conventions.get("ticket_pattern") or "")
    example = pattern.replace("<type>", "fix").replace("<scope>", "api").replace("<ticket>", ticket) \
        .replace("<message>", "handle an empty export")
    print(f"pattern: {pattern}")
    if mismatch("commit", example, conventions):
        print(f"<ticket> matches {conventions.get('ticket_pattern')}")
    else:
        print(f"example: {example}")
    return 0


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    if command not in ("verify", "branch", "commit-msg") or (command == "branch" and len(sys.argv) < 3):
        print(__doc__)
        return 2
    config = arg("--config") or find_config(os.getcwd())
    if not config:
        raise ValueError("no os-config.yaml found from this folder; pass --config <path>")
    repos, conventions = read_config(config)
    if command == "verify":
        return verify(repos, config)
    return branch(conventions) if command == "branch" else commit_msg(conventions)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, re.error) as problem:
        sys.stderr.write(f"conventions: {problem}\n")
        sys.exit(2)
