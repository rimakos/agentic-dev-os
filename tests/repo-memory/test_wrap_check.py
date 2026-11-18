"""wrap_check.py: which sessions changed repo files, and whether the wrap step ran."""
import datetime
import os
import sys
import unittest
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sandbox import MODULE, Sandbox, context, read, slash, tool, user

WRAP_CHECK = os.path.join(MODULE, "wrap_check.py")
HEADER = "date\tsessions\tsessions_with_edits\twrapped\tknowledge_commits"


class WrapCheck(Sandbox):
    def edit(self, relative="src/app.py"):
        return tool("Edit", file_path=self.path(relative), old_string="a", new_string="b")

    def fixtures(self):
        """The four kinds of session, newest first."""
        return {
            "edited": self.transcript("edited", user("fix the bug"), self.edit(), age_days=1),
            "wrapped": self.transcript("wrapped", self.edit("src/other.py"), slash("agentic-dev-os:wrap"), age_days=2),
            "knowledge": self.transcript("knowledge", tool("Write", file_path=self.path("docs/knowledge/page.md"), content="x"), age_days=3),
            "empty": self.transcript("empty", age_days=4),
        }

    def pre_commit(self, transcript, command="git commit -m done", sid=None):
        payload = {**self.payload("Bash", transcript, command=command), "session_id": sid or self.sid}
        done = self.run_script(WRAP_CHECK, "pre-commit", "--memory", "docs/knowledge", payload=payload)
        self.assertEqual((done.returncode, done.stderr), (0, ""))
        return context(done)

    def session_start(self, current=None, *args):
        payload = {"session_id": self.sid, "cwd": self.repo, "hook_event_name": "SessionStart", "source": "startup"}
        if current:
            payload["transcript_path"] = current
        done = self.run_script(WRAP_CHECK, "session-start", "--memory", "docs/knowledge", *args, payload=payload)
        self.assertEqual((done.returncode, done.stderr), (0, ""))
        return done.stdout

    def report(self, *args, **env):
        done = self.run_script(WRAP_CHECK, "report", "--memory", "docs/knowledge", *args, **env)
        self.assertEqual((done.returncode, done.stderr), (0, ""))
        return done.stdout

    # pre-commit

    def test_commit_in_a_session_that_edited_and_never_wrapped_gets_one_reminder(self):
        path = self.fixtures()["edited"]
        self.assertIn("/wrap", self.pre_commit(path))
        self.assertEqual(self.pre_commit(path), "")
        self.assertEqual(self.pre_commit(path, "git push"), "")
        self.assertEqual(self.git("status", "--short"), "")

    def test_push_and_pr_create_count_like_a_commit(self):
        path = self.fixtures()["edited"]
        for command in ("git push origin main", "rtk git commit -m x", "gh pr create --fill", "az repos pr create --title x"):
            with self.subTest(command):
                self.assertIn("/wrap", self.pre_commit(path, command, sid=uuid.uuid4().hex))

    def test_other_commands_stay_silent_and_do_not_use_up_the_reminder(self):
        path = self.fixtures()["edited"]
        for command in ("git status", "git log --oneline", "ls"):
            self.assertEqual(self.pre_commit(path, command), "")
        self.assertIn("/wrap", self.pre_commit(path))

    def test_a_wrapped_session_gets_no_reminder(self):
        ways = {"plain command": slash("wrap"), "namespaced command": slash("agentic-dev-os:wrap"),
                "Skill tool": tool("Skill", skill="wrap"), "namespaced Skill tool": tool("Skill", skill="agentic-dev-os:wrap")}
        for label, wrap in ways.items():
            with self.subTest(label):
                path = self.transcript(uuid.uuid4().hex, self.edit(), wrap)
                self.assertEqual(self.pre_commit(path, sid=uuid.uuid4().hex), "")

    def test_sessions_without_repo_edits_get_no_reminder(self):
        paths = self.fixtures()
        paths["outside the repo"] = self.transcript("outside", tool("Write", file_path=os.path.join(self.home, "notes.md"), content="x"))
        paths["read only"] = self.transcript("reads", tool("Read", file_path=self.path("src/app.py")),
                                             tool("Bash", command="git status 2>&1 | head -5 > /dev/null"))
        paths["missing file"] = os.path.join(self.base, "nope.jsonl")
        for label in ("knowledge", "empty", "outside the repo", "read only", "missing file"):
            with self.subTest(label):
                self.assertEqual(self.pre_commit(paths[label], sid=uuid.uuid4().hex), "")

    def test_a_shell_write_counts_as_an_edit(self):
        for command in ("echo x > src/app.py", "sed -i '' s/a/b/ src/app.py", "echo x | tee src/app.py"):
            with self.subTest(command):
                path = self.transcript(uuid.uuid4().hex, tool("Bash", command=command))
                self.assertIn("/wrap", self.pre_commit(path, sid=uuid.uuid4().hex))
    def test_an_arrow_inside_a_quoted_string_is_not_an_edit(self):
        path = self.transcript("arrow", tool("Bash", command="grep -rn 'input -> output' src"))
        self.assertEqual(self.pre_commit(path), "")

    def test_broken_input_never_fails_the_hook(self):
        for stdin in ("", "not json", "[]", "{}"):
            with self.subTest(stdin):
                done = self.run_script(WRAP_CHECK, "pre-commit", payload=stdin)
                self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "", ""))

    # session-start

    def test_session_start_names_the_earlier_session_that_never_wrapped(self):
        self.transcript("older-wrapped", self.edit("src/old.py"), slash("wrap"), age_days=3)
        self.transcript("unwrapped", self.edit("src/app.py"), age_days=1)
        current = self.transcript("current", self.edit("src/now.py"))
        out = self.session_start(current)
        self.assertIn("/wrap", out)
        self.assertIn("src/app.py", out)
        self.assertNotIn("src/old.py", out)
        self.assertNotIn("src/now.py", out)
        self.assertEqual(self.git("status", "--short"), "")

    def test_session_start_is_silent_when_there_is_nothing_to_wrap(self):
        cases = {
            "only the current session": lambda: None,
            "wrapped after the unwrapped one": lambda: (self.transcript("a", self.edit(), age_days=2),
                                                        self.transcript("b", slash("wrap"), age_days=1)),
            "older than the window": lambda: self.transcript("a", self.edit(), age_days=20),
            "knowledge only and empty": lambda: (self.transcript("a", tool("Edit", file_path=self.path("docs/knowledge/index.md")), age_days=1),
                                                 self.transcript("b", age_days=2)),
        }
        for label, build in cases.items():
            with self.subTest(label):
                for name in os.listdir(self.projects()) if os.path.isdir(self.projects()) else []:
                    os.remove(os.path.join(self.projects(), name))
                build()
                self.assertEqual(self.session_start(self.transcript("current", self.edit())), "")

    def test_session_start_without_a_transcript_path_finds_the_projects_folder(self):
        self.fixtures()
        self.assertIn("src/app.py", self.session_start())

    def test_session_start_appends_one_row_a_day(self):
        self.fixtures()
        out = os.path.join(self.home, "acme-os", "metrics", "wrap-rate.tsv")
        os.makedirs(os.path.dirname(out))
        self.session_start(None, "--append", out)
        self.session_start(None, "--append", out)
        self.assertEqual(read(out).splitlines(), [HEADER, f"{datetime.date.today().isoformat()}\t4\t2\t1\t1"])

    # report

    def test_report_counts_sessions_edits_wraps_and_knowledge_commits(self):
        self.fixtures()
        self.transcript("too-old", self.edit(), age_days=40)
        self.write("docs/knowledge/page.md", "a page\n")
        self.commit("knowledge page")
        self.write("src/app.py", "code\n")
        self.commit("code only")
        before = self.fingerprint(self.home)
        self.assertEqual(self.report().splitlines(), [HEADER, f"{datetime.date.today().isoformat()}\t4\t2\t1\t2"])
        self.assertEqual(self.report("--days", "60").splitlines()[1].split("\t")[1:3], ["5", "3"])
        self.assertEqual(self.fingerprint(self.home), before)

    def test_report_with_no_sessions_prints_zeros(self):
        self.assertEqual(self.report().splitlines()[1].split("\t")[1:4], ["0", "0", "0"])
    def test_report_follows_claude_config_dir(self):
        config = os.path.join(self.base, "config")
        self.transcript("edited", self.edit(), folder=os.path.join(config, "projects", os.path.basename(self.projects())))
        self.assertEqual(self.report(CLAUDE_CONFIG_DIR=config).splitlines()[1].split("\t")[1], "1")


if __name__ == "__main__":
    unittest.main()
