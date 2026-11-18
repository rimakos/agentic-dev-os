"""Run from the repo root: python3 -m unittest discover -s tests -p 'test_*.py'"""
import json, os, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPT = os.path.join(ROOT, "modules", "conventions", "conventions.py")
HOOKS = os.path.join(ROOT, "modules", "repo-memory", "repo_hooks.py")
ENV = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}

CONFIG = """# a comment
workspace:
  name: sample
repos:
  - name: api
    type: backend                  # backend | frontend
    path: api
    verify_cmd: "echo gate ran && exit 3"   # the command CI runs
  - name: web
    path: web
    verify_cmd: 'echo ok'
  - name: lib
    path: lib
    verify_cmd: ""
conventions:
  evidence_tags: true
  evidence_ranking:                # a block list
    - "production data"
    - "code (file:line)"
  branch: "<type>/<ticket>-<slug>"     # placeholders
  branch_types: [feature, bugfix, chore, hotfix]
  commit: "<ticket>: <message>"
  ticket_pattern: "[A-Z]+-[0-9]+"
"""


class Sandbox(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = os.path.realpath(self.tmp.name)
        for repo in ("api/src", "web", "lib"):
            os.makedirs(os.path.join(self.root, repo))
        self.config = self.write("os-config.yaml", CONFIG)

    def write(self, name, text):
        path = os.path.join(self.root, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as file:
            file.write(text)
        return path

    def edit(self, old, new):
        self.assertIn(old, CONFIG)
        self.write("os-config.yaml", CONFIG.replace(old, new))

    def run_cli(self, *args, cwd=None, config=True, env=ENV):
        args = [*args, "--config", self.config] if config else list(args)
        done = subprocess.run([sys.executable, SCRIPT, *args], cwd=cwd or self.root, env=env, capture_output=True, text=True)
        return done.returncode, done.stdout + done.stderr


    def workspace(self):
        """The config at the workspace root, where os-init puts it; found without --config."""
        os.rename(self.config, os.path.join(self.root, "os-config.yaml"))

    def repo_memory(self):
        """A repo whose settings.local.json runs wrap_check.py from a data folder outside it."""
        repo = os.path.join(self.root, "api")
        data = os.path.join(self.root, "data folder-os")
        self.write("data folder-os/os-config.yaml", CONFIG.replace("path: api", f"path: {repo}"))
        os.remove(self.config)
        hooks = {"SessionStart": [{"hooks": [{"type": "command", "command": f'python3 "{data}/hooks/wrap_check.py" session-start'}]}]}
        self.write("api/.claude/settings.local.json", json.dumps({"permissions": {}, "hooks": hooks}))
        return repo


class Verify(Sandbox):
    def test_named_repo_runs_its_command_and_returns_its_code(self):
        code, out = self.run_cli("verify", "--repo", "api")
        self.assertEqual(code, 3)
        self.assertIn("gate ran", out)
        self.assertIn("FAIL (exit 3)", out)

    def test_pass(self):
        code, out = self.run_cli("verify", "--repo", "web")
        self.assertEqual(code, 0)
        self.assertIn("verify web: pass", out)

    def test_runs_in_the_repo_path(self):
        self.edit("'echo ok'", "'pwd'")
        self.assertIn(os.path.join(self.root, "web") + "\n", self.run_cli("verify", "--repo", "web")[1])

    def test_picks_the_repo_containing_the_current_folder(self):
        code, out = self.run_cli("verify", cwd=os.path.join(self.root, "api", "src"))
        self.assertEqual(code, 3)
        self.assertIn("verify api:", out)

    def test_outside_every_repo_lists_them(self):
        code, out = self.run_cli("verify")
        self.assertEqual(code, 2)
        for text in ("api (echo gate ran && exit 3)", "web (echo ok)", "lib (verify_cmd not set)"):
            self.assertIn(text, out)

    def test_unknown_repo(self):
        code, out = self.run_cli("verify", "--repo", "nope")
        self.assertEqual(code, 2)
        self.assertIn("no repo named nope", out)

    def test_empty_command_names_the_key(self):
        code, out = self.run_cli("verify", "--repo", "lib")
        self.assertEqual(code, 2)
        self.assertEqual(len(out.strip().splitlines()), 1)
        self.assertIn("repos[].verify_cmd", out)


class Branch(Sandbox):
    def test_prints_the_name(self):
        self.assertEqual(self.run_cli("branch", "ABC-12", "--type", "feature", "--slug", "add-export"),
                         (0, "feature/ABC-12-add-export\n"))

    def test_rejects_bad_type_ticket_and_slug(self):
        for args, where in ((("ABC-12", "--type", "feat", "--slug", "x"), "<type>"),
                            (("abc-12", "--type", "feature", "--slug", "x"), "<ticket>"),
                            (("ABC-12", "--type", "feature", "--slug", "Add_Export"), "<slug>"),
                            (("ABC-12", "--type", "feature", "--slug", "add-"), "extra text")):
            code, out = self.run_cli("branch", *args)
            self.assertEqual(code, 1, args)
            self.assertIn(where, out)
            self.assertNotIn("\nfeature/", out)

    def test_check(self):
        self.assertEqual(self.run_cli("branch", "--check", "bugfix/ABC-7-fix-login"), (0, ""))
        code, out = self.run_cli("branch", "--check", "fix-login")
        self.assertEqual(code, 1)
        self.assertIn("<type>/<ticket>-<slug>", out)
        self.assertIn("feature|bugfix|chore|hotfix", out)

    def test_hash_ticket(self):
        self.edit('"[A-Z]+-[0-9]+"', '"AB#[0-9]+"')
        self.assertEqual(self.run_cli("branch", "AB#123", "--type", "chore", "--slug", "bump-deps"),
                         (0, "chore/AB#123-bump-deps\n"))
        self.assertEqual(self.run_cli("branch", "--check", "chore/AB#123-bump-deps")[0], 0)
        self.assertEqual(self.run_cli("branch", "--check", "chore/AB-123-bump-deps")[0], 1)

    def test_numeric_ticket(self):
        self.edit('"[A-Z]+-[0-9]+"', '"[0-9]+"')
        self.assertEqual(self.run_cli("branch", "54741", "--type", "hotfix", "--slug", "age-labels"),
                         (0, "hotfix/54741-age-labels\n"))
        self.assertEqual(self.run_cli("branch", "--check", "hotfix/54741-2fa-login")[0], 0)
        self.assertEqual(self.run_cli("branch", "--check", "hotfix/ABC-1-x")[0], 1)

    def test_unknown_placeholder_is_an_error(self):
        self.edit("<type>/<ticket>-<slug>", "<kind>/<ticket>-<slug>")
        code, out = self.run_cli("branch", "--check", "feature/ABC-1-x")
        self.assertEqual(code, 2)
        self.assertIn("unknown placeholder <kind>", out)

    def test_missing_pattern_names_the_key(self):
        self.edit('branch: "<type>/<ticket>-<slug>"', 'branch: ""')
        code, out = self.run_cli("branch", "--check", "feature/ABC-1-x")
        self.assertEqual(code, 2)
        self.assertIn("conventions.branch is not set", out)


class CommitMsg(Sandbox):
    def test_check_pass_reads_the_first_line_only(self):
        self.assertEqual(self.run_cli("commit-msg", "--check", "ABC-12: add export\n\nbody that fits nothing"), (0, ""))

    def test_check_fail_shows_pattern_and_what_failed(self):
        code, out = self.run_cli("commit-msg", "--check", "add export")
        self.assertEqual(code, 1)
        self.assertIn("<ticket>: <message>", out)
        self.assertIn("no match at <ticket> ([A-Z]+-[0-9]+)", out)
        code, out = self.run_cli("commit-msg", "--check", "ABC-12 add export")
        self.assertEqual(code, 1)
        self.assertIn('no match at ": "', out)

    def test_no_check_prints_pattern_and_example(self):
        self.assertEqual(self.run_cli("commit-msg"),
                         (0, "pattern: <ticket>: <message>\nexample: ABC-123: handle an empty export\n"))

    def test_type_scope_and_hash_ticket(self):
        self.write("os-config.yaml", CONFIG.replace('"<ticket>: <message>"', '"<type>(<scope>): <message> [<ticket>]"')
                   .replace('"[A-Z]+-[0-9]+"', '"AB#[0-9]+"'))
        self.assertEqual(self.run_cli("commit-msg", "--check", "fix(api): handle nulls [AB#42]")[0], 0)
        self.assertEqual(self.run_cli("commit-msg", "--check", "fix(api): handle nulls [AB-42]")[0], 1)
        self.assertIn("example: fix(api): handle an empty export [AB#123]", self.run_cli("commit-msg")[1])

    def test_numeric_ticket(self):
        self.edit('"[A-Z]+-[0-9]+"', '"[0-9]+"')
        self.assertEqual(self.run_cli("commit-msg", "--check", "54741: keep the label order")[0], 0)
        self.assertEqual(self.run_cli("commit-msg", "--check", "ABC-1: keep the label order")[0], 1)

    def test_unknown_placeholder_is_an_error(self):
        self.edit("<ticket>: <message>", "<ticket>: <subject>")
        for args in (("commit-msg",), ("commit-msg", "--check", "ABC-1: x")):
            code, out = self.run_cli(*args)
            self.assertEqual(code, 2)
            self.assertIn("unknown placeholder <subject>", out)


class Lookup(Sandbox):
    """The config is found without --config in both modes."""

    def test_workspace_mode_from_a_folder_inside_it(self):
        self.workspace()
        code, out = self.run_cli("verify", cwd=os.path.join(self.root, "api", "src"), config=False)
        self.assertEqual(code, 3)
        self.assertIn(f"(in {os.path.join(self.root, 'api')})", out)

    def test_workspace_mode_from_the_project_dir_variable(self):
        self.workspace()
        elsewhere = tempfile.TemporaryDirectory()
        self.addCleanup(elsewhere.cleanup)
        code, _ = self.run_cli("branch", "--check", "feature/ABC-1-x", cwd=elsewhere.name, config=False,
                               env={**ENV, "CLAUDE_PROJECT_DIR": self.root})
        self.assertEqual(code, 0)

    def test_repo_memory_mode(self):
        repo = self.repo_memory()
        code, out = self.run_cli("verify", cwd=os.path.join(repo, "src"), config=False)
        self.assertEqual(code, 3)
        self.assertIn("verify api:", out)
        self.assertEqual(self.run_cli("commit-msg", "--check", "nope", cwd=repo, config=False)[0], 1)

    def test_no_config_anywhere(self):
        os.remove(self.config)
        code, out = self.run_cli("commit-msg", config=False)
        self.assertEqual(code, 2)
        self.assertIn("--config", out)


class Hook(Sandbox):
    """repo_hooks.py commit-msg: reminds, never blocks."""

    def hook(self, command, cwd, tool="Bash"):
        payload = {"session_id": "t", "cwd": cwd, "hook_event_name": "PreToolUse", "tool_name": tool,
                   "tool_input": {"command": command}}
        done = subprocess.run([sys.executable, HOOKS, "commit-msg"], input=json.dumps(payload), cwd=cwd, env=ENV,
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout

    def assert_reminds(self, out):
        output = json.loads(out)["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "PreToolUse")
        self.assertIn("<ticket>: <message>", output["additionalContext"])

    def test_bad_message_reminds_with_the_pattern(self):
        repo = self.repo_memory()
        self.assert_reminds(self.hook('git commit -m "add export"', repo))
        self.assert_reminds(self.hook("git add a.py && git commit -am 'add export'", repo))
        self.assert_reminds(self.hook('git commit --message "add export" -m "ABC-1: body"', repo))

    def test_good_message_is_silent(self):
        repo = self.repo_memory()
        self.assertEqual(self.hook('git commit -m "ABC-12: add export"', repo), "")
        self.assertEqual(self.hook('git commit -m "ABC-12: add export" -m "body that fits nothing"', repo), "")

    def test_rtk_form_is_checked(self):
        repo = self.repo_memory()
        self.assert_reminds(self.hook('rtk git commit -m "add export"', repo))
        self.assertEqual(self.hook('rtk git commit -m "ABC-12: add export"', repo), "")

    def test_heredoc_and_file_forms_are_not_checked(self):
        repo = self.repo_memory()
        self.assertEqual(self.hook("git commit -m \"$(cat <<'EOF'\nadd export\nEOF\n)\"", repo), "")
        self.assertEqual(self.hook("git commit -F message.txt", repo), "")
        self.assertEqual(self.hook("git commit", repo), "")

    def test_other_commands_and_tools_are_silent(self):
        repo = self.repo_memory()
        self.assertEqual(self.hook('git log --grep "commit -m bad"', repo), "")
        self.assertEqual(self.hook('git commit -m "add export"', repo, tool="Write"), "")

    def test_no_pattern_or_no_config_is_silent(self):
        repo = self.repo_memory()
        self.write("data folder-os/os-config.yaml", "repos:\n  - name: api\n    path: .\n")
        self.assertEqual(self.hook('git commit -m "add export"', repo), "")
        os.remove(os.path.join(repo, ".claude", "settings.local.json"))
        self.assertEqual(self.hook('git commit -m "add export"', repo), "")

    def test_workspace_mode(self):
        self.workspace()
        self.assert_reminds(self.hook('git commit -m "add export"', os.path.join(self.root, "api")))


if __name__ == "__main__":
    unittest.main()
