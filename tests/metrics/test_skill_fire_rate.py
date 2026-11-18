"""modules/metrics/templates/skill-fire-rate.py: how often each skill fired, from local transcripts."""
import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "repo-memory"))
from sandbox import ROOT, Sandbox, tool, user

FIRE_RATE = os.path.join(ROOT, "modules", "metrics", "templates", "skill-fire-rate.py")
HEADER = "date\tdays\tsessions\tskill\tfires"


class SkillFireRate(Sandbox):
    def rows(self, *args):
        done = self.run_script(FIRE_RATE, *args)
        self.assertEqual((done.returncode, done.stderr), (0, ""))
        lines = done.stdout.splitlines()
        self.assertEqual(lines[0], HEADER)
        return [line.split("\t") for line in lines[1:]]

    def test_counts_each_skill_across_the_sessions_in_the_window(self):
        self.transcript("one", user("go"), tool("Skill", skill="wrap"), tool("Skill", skill="ticket-impact", args="123"))
        self.transcript("two", tool("Skill", skill="wrap"), tool("Edit", file_path=self.path("src/app.py")), age_days=3)
        self.transcript("no-skills", user("hello"), age_days=5)
        self.transcript("too-old", tool("Skill", skill="wiki-lint"), age_days=120)
        self.transcript("agent", tool("Skill", skill="goal"), folder=os.path.join(self.projects(), "one", "subagents"))
        before = self.fingerprint(self.home)
        today = datetime.date.today().isoformat()
        self.assertEqual(self.rows(), [[today, "90", "3", "wrap", "2"], [today, "90", "3", "ticket-impact", "1"]])
        self.assertEqual(self.rows("2"), [[today, "2", "1", "wrap", "1"], [today, "2", "1", "ticket-impact", "1"]])
        self.assertEqual(self.fingerprint(self.home), before)
        self.assertEqual(self.git("status", "--short"), "")

    def test_no_transcripts_prints_only_the_header(self):
        self.assertEqual(self.rows(), [])
        self.assertEqual(self.rows("7"), [])


if __name__ == "__main__":
    unittest.main()
