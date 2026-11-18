import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
KB_HEALTH = REPO / "modules" / "doctor" / "kb_health.py"

HEALTHY = {
    "index.md": (
        "# Index\n\n"
        "- [api](repos/api.md): backend\n"
        "- [[api-web]]: the seam\n\n"
        "| page | what |\n|---|---|\n"
        "| [rules](known-issues/rules.md) | working rules |\n\n"
        "<!-- - [example](repos/example.md) -->\n"
    ),
    "repos/api.md": "---\ntags: [repo]\nstatus: active\n---\n# api\n\nSee [[rules]].\n",
    "seams/api-web.md": "# api-web\n",
    "known-issues/rules.md": "# rules\n\nWrite `[[wikilinks]]` inside the wiki.\n",
    "repos/_TEMPLATE.md": "# <repo>\n",
    "decisions/README.md": "# Decisions\n",
    "raw/ticket-1.md": "captured\n",
    "log.md": f"# Log\n\n## [2020-01-01] ingest | old\n\n## [{date.today()}] feature | new\n",
}


class KbHealthTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root)
        for name, text in HEALTHY.items():
            self.write(name, text)

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def run_health(self, *extra):
        result = subprocess.run(
            [sys.executable, str(KB_HEALTH), "--root", str(self.root), "--log", str(self.root / "log.md"), *extra],
            capture_output=True, text=True)
        rows = {}
        for line in result.stdout.splitlines():
            status, check, detail = [part.strip() for part in line.split("  ", 3) if part.strip()][:3]
            rows[check] = (status, detail)
        return result.returncode, rows

    def test_healthy_fixture_passes(self):
        code, rows = self.run_health("--max-row", "80", "--max-lines", "50")
        self.assertEqual(code, 0, rows)
        self.assertEqual({status for status, _ in rows.values()}, {"ok"}, rows)
        self.assertEqual(len(rows), 7)

    def test_template_wiki_has_no_failures(self):
        wiki = REPO / "template" / "wiki"
        result = subprocess.run([sys.executable, str(KB_HEALTH), "--root", str(wiki), "--log", str(wiki / "log.md")],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_page_missing_from_the_index_fails(self):
        self.write("repos/web.md", "# web\n")
        self.write("repos/api.md", "# api\n\nSee [web](web.md).\n")
        code, rows = self.run_health()
        self.assertEqual(code, 1)
        self.assertEqual(rows["index lists every page"], ("fail", "repos/web.md"))
        self.assertEqual(rows["orphan pages"][0], "ok")

    def test_index_link_to_a_missing_file_fails(self):
        self.write("index.md", HEALTHY["index.md"] + "- [gone](repos/gone.md)\n- [[nowhere]]\n")
        code, rows = self.run_health()
        self.assertEqual(code, 1)
        self.assertEqual(rows["index links resolve"], ("fail", "repos/gone.md, [[nowhere]]"))

    def test_orphan_page_warns(self):
        self.write("repos/lonely.md", "# lonely\n")
        code, rows = self.run_health()
        self.assertEqual(rows["orphan pages"], ("warn", "repos/lonely.md"))

    def test_old_log_warns(self):
        old = date.today() - timedelta(days=15)
        self.write("log.md", f"# Log\n\n## [{old}] ingest | old\n")
        code, rows = self.run_health()
        self.assertEqual(code, 0)
        self.assertEqual(rows["log is fresh"], ("warn", f"newest entry {old} is 15 days old"))
        code, rows = self.run_health("--stale-days", "30")
        self.assertEqual(rows["log is fresh"][0], "ok")

    def test_log_without_entries_or_missing_warns(self):
        self.write("log.md", "# Log\n\n<!-- ## [2026-01-15] restructure | example -->\n")
        self.assertEqual(self.run_health()[1]["log is fresh"][0], "warn")
        (self.root / "log.md").unlink()
        code, rows = self.run_health()
        self.assertEqual(code, 0)
        self.assertEqual(rows["log is fresh"][0], "warn")

    def test_stale_page_warns(self):
        self.write("repos/api.md", "---\ntags: [repo]\nstatus: stale\n---\n# api\n\nSee [[rules]].\n")
        self.write("seams/api-web.md", "# api-web\n\nstatus: stale\n")
        code, rows = self.run_health()
        self.assertEqual(code, 0)
        self.assertEqual(rows["stale pages"], ("warn", "repos/api.md"))

    def test_long_index_row_fails(self):
        self.write("index.md", HEALTHY["index.md"] + "- [api](repos/api.md): " + "x" * 80 + "\n")
        code, rows = self.run_health("--max-row", "80")
        self.assertEqual(code, 1)
        self.assertEqual(rows["index rows within 80"], ("fail", "line 11 (103)"))

    def test_long_page_fails(self):
        self.write("seams/api-web.md", "# api-web\n" + "line\n" * 50)
        code, rows = self.run_health("--max-lines", "50")
        self.assertEqual(code, 1)
        self.assertEqual(rows["pages within 50 lines"], ("fail", "seams/api-web.md (51)"))

    def test_missing_index_fails(self):
        (self.root / "index.md").unlink()
        code, rows = self.run_health()
        self.assertEqual(code, 1)
        self.assertEqual(rows["index"][0], "fail")


if __name__ == "__main__":
    unittest.main()
