#!/usr/bin/env python3
"""Health checks for a markdown knowledge base with an index. Read-only.

  kb_health.py --root <folder> [--index <file>] [--log <file>] [--stale-days N]
               [--max-row N] [--max-lines N]

Prints one row per check: status, check, detail, fix hint. Exits 1 if any row fails.
"""
import argparse
import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import unquote

# Not pages: sources kept as captured, rolled-off history, folder notes and templates.
SKIPPED_FOLDERS = {"raw", "archives"}

COMMENT = re.compile(r"<!--.*?-->", re.S)
CODE = re.compile(r"```.*?```|`[^`\n]*`", re.S)
MD_LINK = re.compile(r"\[[^\]]*\]\(<?([^)>\s]+)>?[^)]*\)")
WIKILINK = re.compile(r"\[\[([^\]|#]+)[^\]]*\]\]")
INDEX_ROW = re.compile(r"\s*([-*+]|\d+\.)\s|\s*\|")
LOG_ENTRY = re.compile(r"^## \[(\d{4}-\d{2}-\d{2})\]", re.M)


def is_stale(path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return False
    frontmatter = text[4:].split("\n---", 1)[0]
    return re.search(r"^status:\s*stale\s*$", frontmatter, re.M) is not None


def links(path, files, in_comments=False):
    """(text as written, file it points at or None) for each link inside the knowledge base."""
    text = CODE.sub("", path.read_text(encoding="utf-8"))
    if not in_comments:
        text = COMMENT.sub("", text)
    found = []
    for target in MD_LINK.findall(text):
        target = unquote(target.split("#")[0])
        if not target or re.match(r"[a-z][a-z0-9+.-]*:", target, re.I):
            continue
        file = (path.parent / target).resolve()
        found.append((target, file if file.exists() else None))
    for name in WIKILINK.findall(text):
        name = name.strip()
        matches = [f for f in files if f.with_suffix("").as_posix().endswith("/" + name)]
        found.append((f"[[{name}]]", matches[0] if matches else None))
    return found


def check(args):
    root = Path(args.root).resolve()
    index = Path(args.index).resolve() if args.index else root / "index.md"
    log = Path(args.log).resolve() if args.log else None
    if not index.is_file():
        return [("fail", "index", f"{index} not found", "create the index or pass --index")]

    def name(path):
        return str(path.relative_to(root)) if path.is_relative_to(root) else str(path)

    def row(status, check_name, problems, ok, hint):
        if not problems:
            return ("ok", check_name, ok, "-")
        return (status, check_name, ", ".join(problems), hint)

    files = sorted(root.rglob("*.md"))
    pages = [
        f for f in files
        if f not in (index, log)
        and f.name != "README.md" and not f.name.startswith("_")
        and not SKIPPED_FOLDERS & set(f.relative_to(root).parts[:-1])
    ]
    index_links = links(index, files)
    # A commented-out index line still lists its page; a commented-out example that points
    # nowhere is not a broken link.
    listed = {file for _, file in links(index, files, in_comments=True)}
    linked = listed | {file for f in files if f != index for _, file in links(f, files) if file != f}

    rows = [
        row("fail", "index lists every page", [name(p) for p in pages if p not in listed],
            f"{len(pages)} pages", "add a line for each to the index"),
        row("fail", "index links resolve", [text for text, file in index_links if file is None],
            f"{len(index_links)} links", "fix or remove the index line"),
        row("warn", "orphan pages", [name(p) for p in pages if p not in linked],
            "none", "link each from the index or a related page, or delete it"),
        row("warn", "stale pages", [name(p) for p in pages if is_stale(p)],
            "none", "refresh each page or remove it, then update its status"),
    ]

    if log:
        entries = LOG_ENTRY.findall(COMMENT.sub("", log.read_text(encoding="utf-8"))) if log.is_file() else []
        if not entries:
            rows.append(("warn", "log is fresh", f"no dated entry in {name(log)}", "run /wrap at the end of a session"))
        else:
            age = (date.today() - date.fromisoformat(max(entries))).days
            stale = [f"newest entry {max(entries)} is {age} days old"] if age > args.stale_days else []
            rows.append(row("warn", "log is fresh", stale, f"newest entry {max(entries)}",
                            "run /wrap at the end of a session"))

    if args.max_row:
        long_rows = [
            f"line {number} ({len(line)})"
            for number, line in enumerate(index.read_text(encoding="utf-8").splitlines(), 1)
            if INDEX_ROW.match(line) and len(line) > args.max_row
        ]
        rows.append(row("fail", f"index rows within {args.max_row}", long_rows, "all", "shorten the row"))
    if args.max_lines:
        counts = [(p, len(p.read_text(encoding="utf-8").splitlines())) for p in pages]
        long_pages = [f"{name(p)} ({lines})" for p, lines in counts if lines > args.max_lines]
        rows.append(row("fail", f"pages within {args.max_lines} lines", long_pages, "all", "split or trim the page"))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", required=True)
    parser.add_argument("--index")
    parser.add_argument("--log")
    parser.add_argument("--stale-days", type=int, default=14)
    parser.add_argument("--max-row", type=int)
    parser.add_argument("--max-lines", type=int)
    rows = check(parser.parse_args())
    for status, check_name, detail, hint in rows:
        print(f"{status:<4}  {check_name}  {detail}  {hint}")
    return 1 if any(status == "fail" for status, *_ in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
