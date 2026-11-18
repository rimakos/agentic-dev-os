"""setup_repo.py: install, upgrade, migrate and refuse, all inside a fake HOME."""
import json
import os
import subprocess
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sandbox import MODULE, Sandbox, put, read

SETUP = os.path.join(MODULE, "setup_repo.py")
WRAP_RATE = "date\tsessions\tsessions_with_edits\twrapped\tknowledge_commits\n"


def entry(command):
    return {"type": "command", "timeout": 10, "command": command}


class SetupRepo(Sandbox):
    def setUp(self):
        super().setUp()
        self.data = os.path.join(self.home, "acme-os")
        self.local = self.path(".claude/settings.local.json")

    def setup(self, *args, name="acme", rules="no", cwd=None):
        return subprocess.run([sys.executable, SETUP, "--name", name, "--rules", rules, *args], cwd=cwd or self.repo,
                              env=self.env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)

    def installed(self, *args, **kwargs):
        done = self.setup(*args, **kwargs)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done.stdout

    def settings(self):
        return json.loads(read(self.local))

    def manifest(self):
        return json.loads(read(os.path.join(self.data, "os-manifest.json")))

    def commands(self, event=None, matcher=None):
        return [h["command"] for name, groups in self.settings()["hooks"].items() for group in groups
                for h in group["hooks"] if event in (None, name) and matcher in (None, group.get("matcher"))]

    def ours(self):
        return [c for c in self.commands() if self.data + "/hooks/" in c]

    def state(self):
        """The data folder (without backups and manifest, which record each run) plus the settings file."""
        keep = [os.path.join(self.data, d) for d in ("hooks", "metrics", "reviews")]
        return self.fingerprint(*keep, os.path.dirname(self.local)), read(os.path.join(self.data, "os-config.yaml"))

    def assert_each_mode_once(self):
        ours = self.ours()
        self.assertEqual(len(ours), len(set(ours)), ours)
        for mode in ("session-start", "pre-commit", "outbound", "knowledge-edit"):
            self.assertEqual(sum(f" {mode}" in c for c in ours), 1, (mode, ours))

    def assert_refused(self, done, reason):
        self.assertNotEqual(done.returncode, 0)
        self.assertIn("Stopped", done.stderr)
        self.assertIn(reason, done.stderr)

    def test_fresh_install_writes_the_data_folder_and_only_the_ignored_settings_file(self):
        out = self.installed()
        self.assertIn("Set up", out)
        for name in ("hooks/wrap_check.py", "hooks/repo_hooks.py", "harvest_extract.py", "reviews/lessons.md",
                     "os-config.yaml", "metrics", "backups"):
            self.assertTrue(os.path.exists(os.path.join(self.data, name)), name)
        manifest = self.manifest()
        self.assertEqual((manifest["mode"], os.path.realpath(manifest["repo"])), ("repo", self.repo))
        self.assert_each_mode_once()
        self.assertTrue(all(c in self.ours() for c in self.commands()))
        self.assertIn("Bash(git push:*)", self.settings()["permissions"]["ask"])
        self.assertFalse(os.path.exists(os.path.join(self.home, ".claude", "CLAUDE.md")))
        self.assertEqual(self.git("status", "--short"), "")

    def test_the_installed_hooks_run(self):
        self.installed()
        for command in self.ours():
            done = subprocess.run(command, shell=True, cwd=self.repo, env=self.env, input="{}", capture_output=True, text=True)
            self.assertEqual((done.returncode, done.stderr), (0, ""), command)

    def test_running_again_changes_nothing(self):
        self.installed()
        before, commands = self.state(), self.commands()
        self.assertIn("Upgraded", self.installed())
        self.assertEqual(self.state(), before)
        self.assertEqual(self.commands(), commands)
        self.assert_each_mode_once()
        self.assertEqual(self.git("status", "--short"), "")

    def test_the_users_own_settings_are_kept_and_backed_up(self):
        original = json.dumps({"permissions": {"allow": ["Bash(ls:*)"], "ask": ["Bash(rm:*)"]}, "hooks": {
            "PreToolUse": [{"matcher": "Bash", "hooks": [entry("echo the-users-own-hook")]}]}})
        self.write(".claude/settings.local.json", original)
        self.installed()
        self.installed()
        settings = self.settings()
        self.assertEqual(settings["permissions"]["allow"], ["Bash(ls:*)"])
        self.assertIn("Bash(rm:*)", settings["permissions"]["ask"])
        self.assertEqual(self.commands().count("echo the-users-own-hook"), 1)
        self.assert_each_mode_once()
        backup = self.manifest()["backups"][self.local]
        self.assertTrue(backup.startswith(self.data + os.sep))
        self.assertEqual(read(backup), original)

    def test_start_and_gate_add_their_hooks(self):
        self.write("tools/check.sh", "#!/bin/sh\nexit 0\n", 0o755)
        self.commit("gate")
        self.installed("--start", "/begin", "--gate", "tools/check.sh", "--memory", "docs/knowledge/")
        self.assertEqual(sum(c.endswith("first-edit --start /begin") for c in self.ours()), 1)
        self.assertEqual(sum(c.endswith("pre-push --gate tools/check.sh") for c in self.ours()), 1)
        self.assertEqual(sum(c.endswith("knowledge-edit --memory docs/knowledge") for c in self.ours()), 1)

    def test_a_repo_with_its_own_bash_guard_gets_no_second_one(self):
        self.installed()
        self.assertFalse(all(c.startswith("python3") for c in self.commands("PreToolUse", "Bash")))
        self.write(".claude/settings.json", json.dumps({"hooks": {"PreToolUse": [
            {"matcher": "Bash", "hooks": [entry("echo the-repos-guard")]}]}}))
        self.commit("own guard")
        self.installed(name="guarded")
        self.assertTrue(all(c.startswith("python3") for c in self.commands("PreToolUse", "Bash")))

    def test_rules_yes_adds_the_core_block_once_and_keeps_what_was_there(self):
        global_md = os.path.join(self.home, ".claude", "CLAUDE.md")
        put(global_md, "# Mine\n\n- my own rule\n")
        self.installed(rules="yes")
        self.installed(rules="yes")
        self.installed(rules="no")
        text = read(global_md)
        self.assertTrue(text.startswith("# Mine\n\n- my own rule\n"))
        self.assertEqual(text.count("AGENTIC-DEV-OS:BEGIN core"), 1)
        self.assertEqual(text.count("AGENTIC-DEV-OS:END core"), 1)
        self.assertEqual(read(self.manifest()["backups"][global_md]), "# Mine\n\n- my own rule\n")

    def test_stops_before_writing_when_the_repo_is_not_ready(self):
        self.write("src/keep.txt", "x\n")
        cases = [("from a sub-folder", dict(cwd=self.path("src")), "root of the repo"),
                 ("no knowledge folder", dict(args=["--memory", "docs/nope"]), "not found"),
                 ("gate missing", dict(args=["--gate", "tools/nope.sh"]), "not found")]
        for label, case, reason in cases:
            with self.subTest(label):
                self.assert_refused(self.setup(*case.get("args", []), cwd=case.get("cwd")), reason)
        with self.subTest("settings file not git-ignored"):
            self.write(".gitignore", "")
            self.assert_refused(self.setup(), "not git-ignored")
        self.assertFalse(os.path.exists(self.data))
        self.assertFalse(os.path.exists(self.path(".claude")))

    def test_without_a_name_it_stops(self):
        done = subprocess.run([sys.executable, SETUP], cwd=self.repo, env=self.env, stdin=subprocess.DEVNULL,
                              capture_output=True, text=True)
        self.assert_refused(done, "--name")

    def older_install(self):
        """A hand-made install of the same repo in ~/Workspace/acme-os, its hooks next to the new ones."""
        old = os.path.join(self.home, "Workspace", "acme-os")
        for sub in ("hooks", "reviews", "metrics"):
            os.makedirs(os.path.join(old, sub))
        put(os.path.join(old, "reviews", "lessons.md"), 
            "# Review lessons\n\n- Ask whether the new flag is checked on every surface.\n- Ask whether a moved method kept its name.\n")
        put(os.path.join(old, "metrics", "wrap-rate.tsv"), WRAP_RATE + "2026-10-01\t4\t3\t2\t1\n")
        put(os.path.join(old, "metrics", "scoreboard.tsv"), "week\tcaught\n2026-W40\t3\n")
        put(os.path.join(self.data, "metrics", "wrap-rate.tsv"), WRAP_RATE + "2026-11-16\t2\t1\t1\t0\n")
        settings = self.settings()
        settings["hooks"]["SessionStart"].append({"hooks": [entry(f'python3 "{old}/hooks/wrap_check.py" session-start --memory docs/knowledge')]})
        settings["hooks"]["PreToolUse"].append({"matcher": "Bash", "hooks": [
            entry(f'python3 "{old}/hooks/wrap_check.py" pre-commit --memory docs/knowledge'),
            entry(f"python3 {old}/hooks/repo_hooks.py outbound"),
            entry("echo the-users-own-hook")]})
        settings["permissions"]["allow"] = ["Bash(ls:*)"]
        put(self.local, json.dumps(settings))
        return old

    def test_an_older_install_of_the_same_repo_is_migrated(self):
        self.installed()
        old = self.older_install()
        old_before = self.fingerprint(old)
        out = self.installed()
        self.assertIn("Migrated the older install", out)
        self.assertEqual([c for c in self.commands() if old in c], [])
        self.assertEqual(self.commands().count("echo the-users-own-hook"), 1)
        self.assert_each_mode_once()
        self.assertEqual(self.settings()["permissions"]["allow"], ["Bash(ls:*)"])
        lessons = read(os.path.join(self.data, "reviews", "lessons.md"))
        for line in ("- Ask whether the new flag is checked on every surface.", "- Ask whether a moved method kept its name."):
            self.assertEqual(lessons.count(line), 1)
        rows = read(os.path.join(self.data, "metrics", "wrap-rate.tsv"))
        self.assertEqual(rows.count(WRAP_RATE), 1)
        self.assertIn("2026-11-16\t2\t1\t1\t0\n", rows)
        self.assertIn("2026-10-01\t4\t3\t2\t1\n", rows)
        self.assertTrue(os.path.exists(os.path.join(self.data, "metrics", "scoreboard.tsv")))
        self.assertEqual(self.fingerprint(old), old_before)
        move = self.manifest()["migrated"][0]
        self.assertEqual((os.path.realpath(move["from"]), move["hooks_removed"]), (old, 3))
        self.assertNotIn(self.local, self.manifest()["backups"])
        self.assertEqual(self.git("status", "--short"), "")

        before = self.state()
        self.assertIn("Nothing to migrate", self.installed())
        self.assertEqual(self.state(), before)
        self.assertEqual(len(self.manifest()["migrated"]), 1)

    def test_hook_entries_into_a_folder_that_is_gone_are_removed(self):
        self.installed()
        settings = self.settings()
        gone = os.path.join(self.home, "gone-os")
        settings["hooks"]["PreToolUse"].append({"matcher": "Bash", "hooks": [entry(f'python3 "{gone}/hooks/repo_hooks.py" outbound')]})
        put(self.local, json.dumps(settings))
        self.installed()
        self.assertEqual([c for c in self.commands() if gone in c], [])
        self.assert_each_mode_once()

    def test_a_data_folder_owned_by_another_repo_is_refused(self):
        other = os.path.join(self.home, "other-os")
        put(os.path.join(other, "os-manifest.json"), json.dumps({"mode": "repo", "repo": os.path.join(self.home, "work", "other")}))
        before = self.fingerprint(other)
        self.assert_refused(self.setup(name="other"), "belongs to another repo")
        self.assertEqual(self.fingerprint(other), before)
        self.assertEqual(os.listdir(other), ["os-manifest.json"])
        self.assertFalse(os.path.exists(self.path(".claude")))

    def test_a_hook_entry_into_another_repos_data_folder_is_refused(self):
        self.installed()
        other = os.path.join(self.home, "other-os")
        put(os.path.join(other, "os-manifest.json"), json.dumps({"mode": "repo", "repo": os.path.join(self.home, "work", "other")}))
        put(os.path.join(other, "reviews", "lessons.md"), "- another repo's lesson\n")
        settings = self.settings()
        settings["hooks"]["PreToolUse"].append({"matcher": "Bash", "hooks": [entry(f'python3 "{other}/hooks/repo_hooks.py" outbound')]})
        put(self.local, json.dumps(settings))
        before, manifest = self.state(), self.manifest()
        self.assert_refused(self.setup(), "belongs to another repo")
        self.assertEqual(self.state(), before)
        self.assertEqual(self.manifest(), manifest)
        self.assertNotIn("another repo", read(os.path.join(self.data, "reviews", "lessons.md")))

    def test_a_personal_skill_with_a_plugin_skills_name_is_reported_and_left_alone(self):
        skill = os.path.join(self.home, ".claude", "skills", "wrap", "SKILL.md")
        put(skill, "name: wrap\n")
        out = self.installed()
        self.assertIn("wrap", self.manifest()["skill_collisions"])
        self.assertIn("share a name with the plugin's", out)
        self.assertEqual(read(skill), "name: wrap\n")

    def test_another_os_on_the_machine_is_reported_and_left_alone(self):
        other = os.path.join(self.home, "ws", ".claude", "os-manifest.json")
        put(other, '{"mode": "workspace"}')
        out = self.installed()
        self.assertIn(os.path.join(self.home, "ws") + ":", out)
        self.assertEqual(read(other), '{"mode": "workspace"}')
    def test_own_entries_written_with_a_home_variable_are_replaced(self):
        self.installed()
        text = read(self.local).replace(self.data, "$HOME/acme-os")
        put(self.local, text)
        self.installed()
        for mode in ("session-start", "pre-commit", "outbound", "knowledge-edit"):
            self.assertEqual(sum(f" {mode}" in c for c in self.commands()), 1, mode)


if __name__ == "__main__":
    unittest.main()
