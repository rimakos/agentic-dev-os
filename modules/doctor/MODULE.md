# doctor

## What it does

`kb_health.py` checks a markdown knowledge base against its index and prints one row per check
(`ok|warn|fail  <check>  <detail>  <fix hint>`). It exits 1 if any row fails. It reads only.
`/os-doctor` runs it and reports the rows.

- fail: a page the index does not list, an index link to a file that does not exist, and with
  `--max-row N` or `--max-lines N` an index row or a page over the limit.
- warn: a page nothing links to (orphan), a page whose frontmatter says `status: stale`, and with
  `--log <file>` a log whose newest `## [YYYY-MM-DD]` entry is missing or older than
  `--stale-days` (default 14).

A page is a `.md` file under `--root`. Not counted: the index, the log, `README.md` files, names
starting with `_`, and the `raw/` and `archives/` folders. Links are `[text](file.md)` or
`[[wikilinks]]`, in list items or table rows. Links inside code are ignored. An index line inside
an HTML comment still lists its page.

## Prerequisites

- `python3` on the PATH.

## Install

Nothing to copy. `/os-doctor` runs `<plugin>/modules/doctor/kb_health.py`.

## Verify

```
python3 <plugin>/modules/doctor/kb_health.py --root <workspace>/wiki --log <workspace>/wiki/log.md
```

Prints the rows. Exit 0 means no row failed.

## Remove

Nothing to remove.
