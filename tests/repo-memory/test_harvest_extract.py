"""harvest_extract.py: past sessions boiled down to what the user said."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sandbox import MODULE, Sandbox, read, slash, tool, user

HARVEST = os.path.join(MODULE, "harvest_extract.py")


class HarvestExtract(Sandbox):
    def harvest(self, **env):
        out = os.path.join(self.home, "acme-os", "harvest", "sessions.md")
        done = self.run_script(HARVEST, "--out", out, **env)
        self.assertEqual((done.returncode, done.stderr), (0, ""))
        self.assertIn(out, done.stdout)
        return read(out)

    def test_keeps_what_the_user_said_and_the_files_changed(self):
        self.transcript(
            "one",
            user("add a retry to the client<system-reminder>injected rules</system-reminder>", timestamp="2026-01-02T09:00:00Z"),
            user([{"type": "text", "text": "and log each attempt"}, {"type": "tool_result", "content": "tool output"}]),
            user("a meta line", isMeta=True),
            slash("agentic-dev-os:wrap"),
            {**tool("Edit", file_path=self.path("src/client.py")), "timestamp": "2026-01-02T09:30:00Z"},
            tool("Read", file_path=self.path("src/unread.py")),
        )
        self.transcript("empty")
        self.transcript("no-user-text", tool("Edit", file_path=self.path("src/silent.py")))
        text = self.harvest()
        for kept in ("add a retry to the client", "and log each attempt", "/agentic-dev-os:wrap", "one.jsonl",
                     "Files changed: src/client.py", "2026-01-02T09:00 to 09:30"):
            self.assertIn(kept, text)
        for dropped in ("injected rules", "tool output", "a meta line", "command-message", "unread.py", "silent.py",
                        "empty.jsonl", self.repo):
            self.assertNotIn(dropped, text)
        self.assertEqual(self.git("status", "--short"), "")

    def test_sessions_come_out_oldest_first_and_long_messages_are_cut(self):
        self.transcript("b", user("second session", timestamp="2026-02-01T10:00:00Z"))
        self.transcript("a", user("first session " + "x" * 2000, timestamp="2026-01-01T10:00:00Z"))
        text = self.harvest()
        self.assertLess(text.index("first session"), text.index("second session"))
        self.assertIn("[...]", text)
        self.assertNotIn("x" * 801, text)

    def test_follows_claude_config_dir(self):
        config = os.path.join(self.base, "config")
        self.transcript("moved", user("in the other config dir"), folder=os.path.join(config, "projects", os.path.basename(self.projects())))
        self.transcript("default", user("in the default config dir"))
        text = self.harvest(CLAUDE_CONFIG_DIR=config)
        self.assertIn("in the other config dir", text)
        self.assertNotIn("in the default config dir", text)

    def test_no_sessions_still_writes_the_file(self):
        self.assertIn("0 sessions", self.harvest())
    def test_sessions_of_another_project_with_a_similar_name_are_left_out(self):
        self.transcript("mine", user("about this repo"))
        other = os.path.join(self.home, "elsewhere", "notacme")
        self.transcript("theirs", user("about an unrelated project"), folder=self.projects(other))
        self.assertNotIn("about an unrelated project", self.harvest())


if __name__ == "__main__":
    unittest.main()
