#!/usr/bin/env python3
"""Boil your past Claude Code sessions in this repo down to what you said, for /agentic-dev-os:harvest.

Run from the repo root:
    python3 <data folder>/harvest_extract.py --out <data folder>/harvest/sessions.md
Reads only your own local session files; writes nothing in the repo.
"""
import glob
import json
import os
import re
import sys

REPO = os.path.realpath(os.getcwd())
CONFIG_DIR = os.environ.get("CLAUDE_CONFIG_DIR", os.path.expanduser("~/.claude"))
OUT = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else os.path.expanduser("~/harvest-sessions.md")
NOISE = re.compile(r"<(system-reminder|command-message|command-args|local-command-stdout)>.*?</\1>", re.S)


def project_dirs():
    name = os.path.basename(REPO)
    root = os.path.join(CONFIG_DIR, "projects")
    return sorted(d for d in glob.glob(os.path.join(root, "*")) if name in os.path.basename(d))


def user_text(entry):
    if entry.get("type") != "user" or entry.get("isMeta"):
        return ""
    content = entry.get("message", {}).get("content")
    if isinstance(content, list):
        content = "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    text = NOISE.sub("", content or "").strip()
    command = re.search(r"<command-name>(.*?)</command-name>", text)
    return command.group(1) if command else text


def edits(entry):
    if entry.get("type") != "assistant":
        return []
    blocks = entry.get("message", {}).get("content") or []
    return [b.get("input", {}).get("file_path", "") for b in blocks
            if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") in ("Edit", "Write", "MultiEdit")]


sessions = []
for folder in project_dirs():
    for path in glob.glob(os.path.join(folder, "*.jsonl")):
        said, changed, first, last = [], set(), None, None
        for line in open(path, errors="replace"):
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            stamp = entry.get("timestamp")
            if stamp:
                first, last = first or stamp, stamp
            text = user_text(entry)
            if text:
                said.append(text if len(text) < 800 else text[:800] + " [...]")
            changed.update(p.replace(REPO + "/", "") for p in edits(entry) if p)
        if said:
            sessions.append((first or "", last or "", os.path.basename(path), said, sorted(changed)))

sessions.sort()
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w") as out:
    out.write(f"# Past sessions in {os.path.basename(REPO)}: what you said\n\n{len(sessions)} sessions. "
              "Full transcripts are the .jsonl files named in each heading.\n")
    for first, last, name, said, changed in sessions:
        out.write(f"\n## {first[:16]} to {last[11:16]}  ({name})\n")
        if changed:
            out.write("Files changed: " + ", ".join(changed[:15]) + ("" if len(changed) <= 15 else ", ...") + "\n")
        for number, text in enumerate(said, 1):
            out.write(f"\n{number}. {text}\n")
print(f"{len(sessions)} sessions from {len(project_dirs())} folder(s) written to {OUT}")
