"""template/.claude/hooks/*.sh, run with the workspace layout /os-init creates (wiki/, metrics/, repo symlinks)."""
import os
import shutil
import sys
import time
import unittest
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "repo-memory"))
from sandbox import SHELL_HOOKS, Sandbox, context

DRIFT = os.path.join(SHELL_HOOKS, "drift-check.sh")
TICKET_IMPACT = os.path.join(SHELL_HOOKS, "ticket-impact-reminder.sh")
WIKI_VERIFY = os.path.join(SHELL_HOOKS, "wiki-verify-reminder.sh")


class ShellHooks(Sandbox):
    """self.repo plays the workspace root."""

    def hook(self, script, tool_name, **tool_input):
        done = self.run_script(script, payload=self.payload(tool_name, **tool_input), CLAUDE_PROJECT_DIR=self.repo)
        self.assertEqual((done.returncode, done.stderr), (0, ""))
        return context(done)

    def edit(self, script, path):
        return self.hook(script, "Edit", file_path=path if os.path.isabs(path) else self.path(path))


class DriftCheck(ShellHooks):
    def drift(self):
        done = self.run_script(DRIFT, payload={"session_id": self.sid, "hook_event_name": "SessionStart"},
                               CLAUDE_PROJECT_DIR=self.repo)
        self.assertEqual((done.returncode, done.stderr), (0, ""))
        return done.stdout

    def page(self, relative, age_seconds):
        stamp = time.time() - age_seconds
        os.utime(self.write(relative, "text\n"), (stamp, stamp))

    def test_a_page_newer_than_the_log_is_named(self):
        self.page("wiki/log.md", 600)
        self.page("wiki/older.md", 900)
        self.page("wiki/known-issues/newer.md", 60)
        out = self.drift()
        self.assertIn("MEMORY DRIFT", out)
        self.assertIn("wiki/known-issues/newer.md", out)
        self.assertNotIn("older.md", out)
        self.assertEqual(self.git("status", "--short", "--", ".", ":!wiki"), "")

    def test_silent_when_the_log_is_the_newest_file_or_missing(self):
        self.page("wiki/page.md", 900)
        self.assertEqual(self.drift(), "")
        self.page("wiki/log.md", 600)
        self.page("wiki/.obsidian/workspace.md", 60)
        self.page("wiki/notes.txt", 60)
        self.assertEqual(self.drift(), "")


@unittest.skipUnless(shutil.which("jq"), "the reminder hooks do nothing without jq")
class TicketImpactReminder(ShellHooks):
    def test_first_source_edit_reminds_once_per_session(self):
        self.assertIn("/ticket-impact", self.edit(TICKET_IMPACT, "src/app.ts"))
        self.assertEqual(self.edit(TICKET_IMPACT, "src/other.ts"), "")
        self.sid = uuid.uuid4().hex
        self.assertIn("/ticket-impact", self.hook(TICKET_IMPACT, "Write", file_path=self.path("src/new.ts"), content="x"))

    def test_an_edit_in_a_symlinked_repo_counts(self):
        target = os.path.join(self.base, "checkouts", "product")
        os.makedirs(target)
        os.symlink(target, self.path("product"))
        self.assertIn("/ticket-impact", self.edit(TICKET_IMPACT, os.path.join(target, "src", "app.ts")))

    def test_a_shell_write_into_the_workspace_counts(self):
        self.assertIn("/ticket-impact", self.hook(TICKET_IMPACT, "Bash", command=f"echo x >> {self.path('src/app.ts')}"))

    def test_os_folders_generated_files_reads_and_other_places_stay_silent(self):
        for relative in ("wiki/page.md", ".claude/settings.json", "metrics/system-health.tsv", "src/generated/client.ts",
                         "node_modules/pkg/index.js", "api/Migrations/001.cs", os.path.join(self.home, "notes.md")):
            self.assertEqual(self.edit(TICKET_IMPACT, relative), "", relative)
        self.assertEqual(self.hook(TICKET_IMPACT, "Bash", command=f"cat {self.path('src/app.ts')} | head -5"), "")
        self.assertEqual(self.hook(TICKET_IMPACT, "Read", file_path=self.path("src/app.ts")), "")
        self.assertIn("/ticket-impact", self.edit(TICKET_IMPACT, "src/app.ts"))
    def test_a_shell_write_through_a_relative_path_counts(self):
        self.assertIn("/ticket-impact", self.hook(TICKET_IMPACT, "Bash", command="sed -i '' 's/a/b/' src/app.ts"))


@unittest.skipUnless(shutil.which("jq"), "the reminder hooks do nothing without jq")
class WikiVerifyReminder(ShellHooks):
    def test_first_wiki_page_edit_reminds_once_per_session(self):
        self.assertIn("wiki claim", self.edit(WIKI_VERIFY, "wiki/known-issues/page.md"))
        self.assertEqual(self.edit(WIKI_VERIFY, "wiki/other.md"), "")
        self.sid = uuid.uuid4().hex
        self.assertIn("wiki claim", self.hook(WIKI_VERIFY, "Bash", command=f"echo '- fact' >> {self.path('wiki/page.md')}"))

    def test_a_shell_write_through_a_relative_path_counts(self):
        self.assertIn("wiki claim", self.hook(WIKI_VERIFY, "Bash", command="echo '- fact' >> wiki/page.md"))
        self.sid = uuid.uuid4().hex
        self.assertEqual(self.hook(WIKI_VERIFY, "Bash", command="echo done >> wiki/log.md"), "")
        self.assertEqual(self.hook(WIKI_VERIFY, "Bash", command="echo x > src/app.ts"), "")

    def test_the_log_source_files_and_reads_stay_silent(self):
        self.assertEqual(self.edit(WIKI_VERIFY, "wiki/log.md"), "")
        self.assertEqual(self.edit(WIKI_VERIFY, "src/app.ts"), "")
        self.assertEqual(self.hook(WIKI_VERIFY, "Bash", command=f"cat {self.path('wiki/page.md')}"), "")
        self.assertEqual(self.hook(WIKI_VERIFY, "Read", file_path=self.path("wiki/page.md")), "")
        self.assertIn("wiki claim", self.edit(WIKI_VERIFY, "wiki/page.md"))

    def test_the_two_reminders_do_not_share_a_marker(self):
        self.assertNotEqual(self.edit(TICKET_IMPACT, "src/app.ts"), "")
        self.assertNotEqual(self.edit(WIKI_VERIFY, "wiki/page.md"), "")


if __name__ == "__main__":
    unittest.main()
