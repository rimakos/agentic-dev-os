"""repo_hooks.py: the just-in-time reminders and the pre-push gate (commit-msg is tested elsewhere)."""
import os
import subprocess
import sys
import unittest
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sandbox import MODULE, Sandbox, context

REPO_HOOKS = os.path.join(MODULE, "repo_hooks.py")
GATE = "#!/bin/sh\n# exit 1 with the file names when a file holds the word SECRET\ngrep -l SECRET \"$@\" && exit 1\nexit 0\n"


class RepoHooks(Sandbox):
    def hook(self, mode, payload, *args, **env):
        done = self.run_script(REPO_HOOKS, mode, *args, payload=payload, **env)
        self.assertEqual((done.returncode, done.stderr), (0, ""))
        return context(done)

    def edit(self, relative):
        return self.payload("Edit", file_path=self.path(relative), old_string="a", new_string="b")

    def bash(self, command):
        return self.payload("Bash", command=command)

    # first-edit

    def test_first_source_edit_reminds_once_and_names_the_start_skill(self):
        self.assertIn("/begin", self.hook("first-edit", self.edit("src/app.py"), "--start", "/begin"))
        self.assertEqual(self.hook("first-edit", self.edit("src/other.py"), "--start", "/begin"), "")
        self.assertEqual(self.hook("first-edit", self.bash("echo x > src/app.py"), "--start", "/begin"), "")
        self.sid = uuid.uuid4().hex
        self.assertIn("/start-work", self.hook("first-edit", self.bash("echo x > src/app.py")))
        self.assertEqual(self.git("status", "--short"), "")

    def test_first_edit_ignores_docs_reads_and_files_outside_the_repo(self):
        quiet = [self.edit("docs/knowledge/page.md"), self.edit(".claude/settings.local.json"),
                 self.payload("Write", file_path=os.path.join(self.home, "notes.md"), content="x"),
                 self.payload("Read", file_path=self.path("src/app.py")), self.bash("git status 2>&1 | head -3")]
        for payload in quiet:
            self.assertEqual(self.hook("first-edit", payload), "", payload["tool_input"])
        self.assertNotEqual(self.hook("first-edit", self.edit("src/app.py")), "")
    def test_first_edit_still_fires_after_the_session_moved_into_a_sub_folder(self):
        os.makedirs(self.path("src"))
        payload = {**self.edit("README.md"), "cwd": self.path("src")}
        self.assertNotEqual(self.hook("first-edit", payload, CLAUDE_PROJECT_DIR=self.repo), "")

    # knowledge-edit

    def test_first_knowledge_write_reminds_once(self):
        self.assertEqual(self.hook("knowledge-edit", self.edit("src/app.py"), "--memory", "docs/knowledge"), "")
        self.assertIn("docs/knowledge", self.hook("knowledge-edit", self.edit("docs/knowledge/page.md"), "--memory", "docs/knowledge"))
        self.assertEqual(self.hook("knowledge-edit", self.edit("docs/knowledge/index.md"), "--memory", "docs/knowledge"), "")
        self.sid = uuid.uuid4().hex
        self.assertNotEqual(self.hook("knowledge-edit", self.bash("echo '- fact' >> docs/knowledge/page.md")), "")

    def test_knowledge_edit_follows_the_memory_option(self):
        self.assertEqual(self.hook("knowledge-edit", self.edit("docs/knowledge/page.md"), "--memory", "wiki"), "")
        self.assertIn("wiki/index.md", self.hook("knowledge-edit", self.edit("wiki/page.md"), "--memory", "wiki/"))

    def test_the_two_reminders_do_not_share_a_marker(self):
        self.assertNotEqual(self.hook("first-edit", self.edit("src/app.py")), "")
        self.assertNotEqual(self.hook("knowledge-edit", self.edit("docs/knowledge/page.md")), "")

    # outbound

    def test_outbound_fires_for_pr_text_only(self):
        for command in ("gh pr create --title x --body y", "gh pr comment 12 --body y", "az repos pr create --title x",
                        "az repos pr update --id 3 --description y", "az devops invoke --area git"):
            self.assertIn("claim", self.hook("outbound", self.bash(command)), command)
        for payload in (self.bash("gh pr view 12"), self.bash("git push"), self.edit("src/app.py"),
                        self.payload("Write", file_path=self.path("notes.md"), content="gh pr create")):
            self.assertEqual(self.hook("outbound", payload), "", payload["tool_input"])

    # pre-push

    def pushed_repo(self, gate=GATE, mode=0o755):
        """The sandbox repo with a gate, an upstream, and one commit the next push would send."""
        self.write("tools/check.sh", gate, mode)
        self.commit("gate")
        remote = os.path.join(self.base, "remote.git")
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", remote], env=self.env, check=True)
        self.git("remote", "add", "origin", remote)
        self.git("push", "-q", "-u", "origin", "main")
        self.write("src/config.py", "KEY = 'SECRET'\n")
        self.write("src/clean.py", "x = 1\n")
        self.commit("unpushed")

    def pre_push(self, command="git push", *args):
        args = args or ("--gate", "tools/check.sh")
        return self.run_script(REPO_HOOKS, "pre-push", *args, payload=self.bash(command))

    def test_a_gate_finding_blocks_the_push_and_names_the_file(self):
        self.pushed_repo()
        for command in ("git push", "rtk git push origin main", "git add -A && git commit -m x && git push"):
            done = self.pre_push(command)
            self.assertEqual(done.returncode, 2, command)
            self.assertIn("BLOCKED", done.stderr)
            self.assertIn("src/config.py", done.stderr)
            self.assertNotIn("src/clean.py", done.stderr)
        self.assertEqual(self.git("status", "--short"), "")

    def test_a_clean_push_passes_in_silence(self):
        self.pushed_repo()
        self.write("src/config.py", "KEY = 'from the environment'\n")
        self.commit("fixed")
        done = self.pre_push()
        self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "", ""))

    def test_the_gate_only_runs_for_a_push_with_something_to_send(self):
        self.pushed_repo()
        for command in ("git status", "git commit -m 'before git push'", "echo git pushed"):
            self.assertEqual(self.pre_push(command).returncode, 0, command)
        self.assertEqual(self.pre_push("git push", "--memory", "docs/knowledge").returncode, 0)
        self.git("push", "-q")
        done = self.pre_push()
        self.assertEqual((done.returncode, done.stdout), (0, ""))

    def test_a_gate_that_fails_to_run_is_reported_and_does_not_block(self):
        self.pushed_repo(gate="#!/bin/sh\nexit 3\n")
        done = self.pre_push()
        self.assertEqual(done.returncode, 0)
        self.assertIn("unchecked", context(done))
    def test_a_gate_that_is_not_executable_is_reported(self):
        self.pushed_repo(mode=0o644)
        self.assertIn("unchecked", context(self.pre_push()))
    def test_a_new_branch_on_a_remote_without_main_is_still_checked(self):
        self.write("tools/check.sh", GATE, 0o755)
        self.commit("gate")
        self.git("branch", "-m", "develop")
        remote = os.path.join(self.base, "remote.git")
        subprocess.run(["git", "init", "-q", "--bare", "-b", "develop", remote], env=self.env, check=True)
        self.git("remote", "add", "origin", remote)
        self.git("push", "-q", "-u", "origin", "develop")
        self.git("checkout", "-q", "-b", "feature/secret")
        self.write("src/config.py", "KEY = 'SECRET'\n")
        self.commit("unpushed")
        done = self.pre_push("git push -u origin feature/secret")
        self.assertTrue(done.returncode == 2 or "unchecked" in context(done))

    # all modes

    def test_broken_input_never_fails_a_hook(self):
        for mode in ("first-edit", "knowledge-edit", "outbound", "pre-push", "no-such-mode"):
            for stdin in ("", "not json", "[]", "{}"):
                done = self.run_script(REPO_HOOKS, mode, payload=stdin)
                self.assertEqual((done.returncode, done.stdout, done.stderr), (0, "", ""), (mode, stdin))


if __name__ == "__main__":
    unittest.main()
