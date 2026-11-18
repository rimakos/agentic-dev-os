import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PR_PY = Path(__file__).resolve().parents[2] / "modules" / "pr" / "pr.py"

TRICKY_BODY = (
    "## What changed\n"
    "\n"
    "Run `make build` with $HOME and ${VAR} left alone, plus $(whoami).\n"
    "\n"
    "\n"
    "It's \"quoted\" and 'single', thanks @reviewer and @team/core.\n"
    "- a list item\n"
    "    indented \\n stays two characters\n"
)

FAKE_CLI = """#!/usr/bin/env python3
import json, os, sys
with open(os.environ["PR_TEST_RECORD"], "w") as record:
    json.dump(sys.argv, record)
"""


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


class PrTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.tmp)

        # A copy of pr.py, so the conventions script next to it is the test's own or none.
        self.script = self.tmp / "plugin" / "modules" / "pr" / "pr.py"
        self.script.parent.mkdir(parents=True)
        shutil.copy(PR_PY, self.script)

        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        self.record = self.tmp / "argv.json"
        for name in ("az", "gh"):
            cli = self.bin / name
            cli.write_text(FAKE_CLI)
            cli.chmod(0o755)

        self.body = self.tmp / "body.md"
        self.body.write_bytes(TRICKY_BODY.encode())

    def make_repo(self, host, pushed=True):
        """A repo on branch feature/1-thing whose origin is a local bare repo with the host in its path."""
        origin = self.tmp / host / "org" / "project" / "_git" / "repo"
        origin.mkdir(parents=True)
        git(origin, "init", "--bare", "-b", "main")
        self.repo = self.tmp / "work"
        self.repo.mkdir()
        git(self.repo, "init", "-b", "main")
        git(self.repo, "-c", "user.name=t", "-c", "user.email=t@example.com",
            "-c", "commit.gpgsign=false", "commit", "--allow-empty", "-m", "first")
        git(self.repo, "remote", "add", "origin", str(origin))
        git(self.repo, "push", "origin", "main")
        git(self.repo, "checkout", "-b", "feature/1-thing")
        if pushed:
            git(self.repo, "push", "origin", "feature/1-thing")

    def pr(self, *args):
        env = dict(os.environ, PATH=f"{self.bin}{os.pathsep}{os.environ['PATH']}",
                   PR_TEST_RECORD=str(self.record))
        return subprocess.run([sys.executable, str(self.script), *args],
                              cwd=self.repo, env=env, capture_output=True, text=True)

    def recorded(self):
        return json.loads(self.record.read_text())[1:]

    def create(self, *extra):
        return self.pr("create", "--title", "1: add thing", "--body-file", str(self.body), *extra)

    def test_describe_prints_the_preview_and_calls_nothing(self):
        self.make_repo("dev.azure.com")
        result = self.pr("describe", "--title", "1: add thing", "--body-file", str(self.body), "--ticket", "1")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Title:  1: add thing", result.stdout)
        self.assertIn("Source: feature/1-thing", result.stdout)
        self.assertIn("Ticket: 1", result.stdout)
        self.assertIn(TRICKY_BODY, result.stdout)
        self.assertFalse(self.record.exists())

    def test_create_without_yes_previews_and_does_not_call_the_cli(self):
        self.make_repo("dev.azure.com")
        result = self.create("--target", "main")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(TRICKY_BODY, result.stdout)
        self.assertIn("Command: az repos pr create", result.stdout)
        self.assertIn("Preview only", result.stdout)
        self.assertFalse(self.record.exists())

    def test_create_yes_on_azure_devops_calls_az_with_exact_argv(self):
        self.make_repo("dev.azure.com")
        result = self.create("--target", "main", "--ticket", "42", "--draft", "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.recorded(), [
            "repos", "pr", "create", "--title", "1: add thing",
            f"--description=@{self.body}", "--source-branch", "feature/1-thing",
            "--target-branch", "main", "--work-items", "42", "--draft",
        ])

    def test_create_yes_on_github_calls_gh_with_exact_argv(self):
        self.make_repo("github.com")
        result = self.create("--target", "main", "--draft", "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.recorded(), [
            "pr", "create", "--title", "1: add thing", "--body-file", str(self.body),
            "--head", "feature/1-thing", "--base", "main", "--draft",
        ])

    def body_sent(self, host):
        """The bytes of the file the CLI was told to read, after a create --yes."""
        self.make_repo(host)
        self.assertEqual(self.create("--yes").returncode, 0)
        argv = self.recorded()
        # The body travels as a file path, never as text a shell could expand.
        self.assertFalse([a for a in argv if "What changed" in a])
        if host == "github.com":
            return Path(argv[argv.index("--body-file") + 1]).read_bytes()
        description = next(a for a in argv if a.startswith("--description=@"))
        return Path(description.removeprefix("--description=@")).read_bytes()

    def test_tricky_body_reaches_az_unchanged(self):
        self.assertEqual(self.body_sent("dev.azure.com"), TRICKY_BODY.encode())

    def test_tricky_body_reaches_gh_unchanged(self):
        self.assertEqual(self.body_sent("github.com"), TRICKY_BODY.encode())

    def test_update_yes_calls_the_cli_with_exact_argv(self):
        self.make_repo("dev.azure.com")
        preview = self.pr("update", "77", "--body-file", str(self.body))
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertFalse(self.record.exists())
        result = self.pr("update", "77", "--title", "1: new title", "--body-file", str(self.body), "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.recorded(), [
            "repos", "pr", "update", "--id", "77", "--title", "1: new title",
            f"--description=@{self.body}",
        ])

    def test_update_yes_on_github(self):
        self.make_repo("github.com")
        result = self.pr("update", "77", "--title", "1: new title", "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.recorded(), ["pr", "edit", "77", "--title", "1: new title"])

    def test_branch_not_pushed_exits_3_with_the_push_command(self):
        self.make_repo("dev.azure.com", pushed=False)
        result = self.create("--yes")
        self.assertEqual(result.returncode, 3)
        self.assertIn("git push -u origin feature/1-thing", result.stdout)
        self.assertFalse(self.record.exists())

    def test_title_convention_failure_stops_before_the_cli(self):
        self.make_repo("dev.azure.com")
        conventions = self.script.parents[1] / "conventions" / "conventions.py"
        conventions.parent.mkdir()
        conventions.write_text(
            "import sys\n"
            "assert sys.argv[1:3] == ['commit-msg', '--check']\n"
            "if not sys.argv[3][0].isdigit():\n"
            "    print('expected <ticket>: <message>')\n"
            "    sys.exit(1)\n"
        )
        bad = self.pr("create", "--title", "add thing", "--body-file", str(self.body), "--yes")
        self.assertEqual(bad.returncode, 1)
        self.assertIn("expected <ticket>: <message>", bad.stderr)
        self.assertFalse(self.record.exists())
        self.assertEqual(self.create("--yes").returncode, 0)

    def test_unknown_host_exits_2(self):
        self.make_repo("git.example.org")
        result = self.create()
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown git host", result.stderr)

    def test_missing_cli_exits_2(self):
        self.make_repo("github.com")
        only_git = self.tmp / "only-git"
        only_git.mkdir()
        (only_git / "git").symlink_to(shutil.which("git"))
        env = dict(os.environ, PATH=str(only_git))
        result = subprocess.run(
            [sys.executable, str(self.script), "create", "--title", "t", "--body-file", str(self.body)],
            cwd=self.repo, env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("'gh' is not on the PATH", result.stderr)


if __name__ == "__main__":
    unittest.main()
