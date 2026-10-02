#!/usr/bin/env python3
"""How often each skill fires, from this workspace's Claude Code transcripts.

A skill that never fires cannot catch anything. /wrap appends the output to
skill-fire-rate.tsv once a day; /wiki-lint lists skills that stay at zero as
candidates to archive. Run from the workspace root:

    python3 metrics/skill-fire-rate.py [days=90]
"""
import os, re, sys, time, collections, datetime

days = int(sys.argv[1]) if len(sys.argv) > 1 else 90
slug = re.sub(r'[^A-Za-z0-9]', '-', os.getcwd())
root = os.path.expanduser('~/.claude/projects/' + slug)
cut = time.time() - days * 86400
skills, sessions = collections.Counter(), 0
for dp, _, fn in os.walk(root):
    if '/subagents' in dp or '/tool-results' in dp:
        continue
    for f in fn:
        p = os.path.join(dp, f)
        if not f.endswith('.jsonl') or os.path.getmtime(p) < cut:
            continue
        sessions += 1
        txt = open(p, encoding='utf-8', errors='ignore').read()
        for m in re.finditer(r'"name":"Skill","input":\{"skill":"([^"]+)"', txt):
            skills[m.group(1)] += 1
today = datetime.date.today().isoformat()
print('date\tdays\tsessions\tskill\tfires')
for k, n in skills.most_common():
    print(f'{today}\t{days}\t{sessions}\t{k}\t{n}')
