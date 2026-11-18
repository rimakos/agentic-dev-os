"""Shared sandbox for the script tests: a fake HOME, a private TMPDIR and a throwaway git repo.

Every script runs as a subprocess with only the variables set here, so nothing reads or writes the
real home folder, and the once-per-session marker files land in the sandbox TMPDIR.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODULE = os.path.join(ROOT, "modules", "repo-memory")
SHELL_HOOKS = os.path.join(ROOT, "template", ".claude", "hooks")


def read(path, mode="r"):
    with open(path, mode) as f:
        return f.read()


def put(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)
    return path


def user(text, **extra):
    """A transcript line for something the user typed."""
    return {"type": "user", "message": {"role": "user", "content": text}, **extra}


def slash(name):
    """A transcript line for a slash command, as Claude Code records it."""
    return user(f"<command-name>/{name}</command-name>\n<command-message>{name}</command-message>")


def tool(name, **tool_input):
    """A transcript line for one tool call by the assistant."""
    block = {"type": "tool_use", "id": "toolu_" + uuid.uuid4().hex[:8], "name": name, "input": tool_input}
    return {"type": "assistant", "message": {"role": "assistant", "content": [block]}}


def context(result):
    """The additionalContext a PreToolUse hook printed, or '' when it stayed silent."""
    if not result.stdout.strip():
        return ""
    output = json.loads(result.stdout)["hookSpecificOutput"]
    assert output["hookEventName"] == "PreToolUse", output
    return output["additionalContext"]


class Sandbox(unittest.TestCase):
    def setUp(self):
        self.base = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.base, True)
        self.home = os.path.join(self.base, "home")
        self.repo = os.path.join(self.home, "work", "acme")
        self.sid = uuid.uuid4().hex
        self.env = {"PATH": os.environ["PATH"], "HOME": self.home, "TMPDIR": os.path.join(self.base, "tmp"),
                    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
                    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}
        os.makedirs(self.env["TMPDIR"])
        self.write(".gitignore", ".claude/settings.local.json\n")
        self.write("docs/knowledge/index.md", "# Knowledge\n")
        self.git("init", "-q", "-b", "main")
        self.commit("start")

    def path(self, relative):
        return os.path.join(self.repo, relative)

    def write(self, relative, text, mode=None):
        path = put(self.path(relative), text)
        if mode:
            os.chmod(path, mode)
        return path

    def git(self, *args):
        done = subprocess.run(["git", *args], cwd=self.repo, env=self.env, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout.strip()

    def commit(self, message):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def run_script(self, script, *args, payload=None, cwd=None, **env):
        """Run a script the way a hook runs it: payload as JSON on stdin (raw when it is a string)."""
        stdin = payload if isinstance(payload, str) else json.dumps(payload) if payload is not None else ""
        runner = ["sh"] if script.endswith(".sh") else [sys.executable]
        return subprocess.run([*runner, script, *args], input=stdin, cwd=cwd or self.repo,
                              env={**self.env, **env}, capture_output=True, text=True, timeout=60)

    def projects(self, repo=None):
        """Where Claude Code keeps the transcripts of sessions started in this repo."""
        return os.path.join(self.home, ".claude", "projects", re.sub(r"[^A-Za-z0-9]", "-", repo or self.repo))

    def transcript(self, name, *entries, age_days=0, folder=None):
        path = os.path.join(folder or self.projects(), name + ".jsonl")
        put(path, "".join(json.dumps(e, separators=(",", ":")) + "\n" for e in entries))
        stamp = time.time() - age_days * 86400
        os.utime(path, (stamp, stamp))
        return path

    def payload(self, tool_name, transcript="", **tool_input):
        """PreToolUse hook input, as Claude Code sends it."""
        return {"session_id": self.sid, "transcript_path": transcript, "cwd": self.repo,
                "hook_event_name": "PreToolUse", "tool_name": tool_name, "tool_input": tool_input}

    def fingerprint(self, *folders):
        """One hash over every file under the folders, to prove a run changed nothing."""
        digest = hashlib.sha256()
        for folder in folders:
            for root, dirs, files in os.walk(folder):
                dirs.sort()
                for name in sorted(files):
                    path = os.path.join(root, name)
                    digest.update(path.encode() + read(path, "rb"))
        return digest.hexdigest()
