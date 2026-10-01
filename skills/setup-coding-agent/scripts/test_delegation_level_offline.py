#!/usr/bin/env python3
"""Offline tests for delegation_level.py (no Claude, no network). Mutation-checked."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))


def load():
    spec = importlib.util.spec_from_file_location("delegation_level", os.path.join(_HERE, "delegation_level.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class Base(unittest.TestCase):
    def setUp(self):
        self.m = load()
        self.proj = tempfile.mkdtemp()
        subprocess.run(["git", "init", "-q"], cwd=self.proj, check=True)
        os.environ.pop("CLAUDE_PROJECT_DIR", None)

    def path(self, rel):
        return os.path.join(self.proj, *rel.split("/"))

    def read(self, rel):
        return open(self.path(rel), encoding="utf-8").read()

    def always(self, **kw):
        return self.m.install(self.proj, "always", hook=True, **kw)

    def edit(self, rel, tool="Edit", sid="s1", abs_path=False):
        fp = self.path(rel) if abs_path else rel
        return self.m.decide_pretool({"tool_name": tool, "tool_input": {"file_path": fp}, "session_id": sid}, self.proj)


class BlockTest(Base):
    def test_every_level_renders_its_own_rule_and_only_always_mentions_the_hook(self):
        for lv in self.m.LEVELS:
            b = self.m.render_block(lv, hook=(lv == "always"))
            self.assertIn(self.m.MARK_BEGIN, b)
            self.assertIn(self.m.LEVEL_TITLE[lv], b)
            self.assertEqual("hook บล็อก" in b, lv == "always")
        with self.assertRaises(ValueError):
            self.m.render_block("sometimes", False)

    def test_upsert_keeps_every_other_character_and_is_idempotent(self):
        mine = "# my notes\nkeep this\n\n## other\nmore\n"
        once = self.m.upsert_block(mine, self.m.render_block("medium", False))
        self.assertTrue(once.startswith(mine))
        twice = self.m.upsert_block(once, self.m.render_block("medium", False))
        self.assertEqual(once, twice)
        changed = self.m.upsert_block(once, self.m.render_block("low", False))
        self.assertTrue(changed.startswith(mine))
        self.assertEqual(changed.count(self.m.MARK_BEGIN), 1)
        self.assertIn(self.m.LEVEL_TITLE["low"], changed)
        self.assertNotIn(self.m.LEVEL_TITLE["medium"], changed)

    def test_text_after_our_block_survives_a_replace(self):
        text = "before\n" + self.m.render_block("low", False) + "after the block\n"
        out = self.m.upsert_block(text, self.m.render_block("always", True))
        self.assertTrue(out.startswith("before\n"))
        self.assertTrue(out.endswith("after the block\n"))

    def test_remove_block_gives_the_users_text_back(self):
        mine = "# my notes\nkeep this\n"
        self.assertEqual(self.m.remove_block(self.m.upsert_block(mine, self.m.render_block("low", False))).strip(), mine.strip())


class SettingsTest(Base):
    def test_hooks_are_merged_not_replaced_and_removed_cleanly(self):
        theirs = {"permissions": {"allow": ["Bash(ls:*)"]},
                  "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "their.sh"}]}]}}
        with_ours = self.m.merge_hooks(theirs, "/usr/bin/python3", True)
        self.assertEqual(with_ours["permissions"], theirs["permissions"])
        cmds = [h["command"] for e in with_ours["hooks"]["PreToolUse"] for h in e["hooks"]]
        self.assertIn("their.sh", cmds)
        self.assertEqual(sum(1 for c in cmds if self.m.HOOK_TAG in c), 1)
        self.assertEqual(self.m.merge_hooks(with_ours, "/usr/bin/python3", True), with_ours)        # idempotent
        gone = self.m.merge_hooks(with_ours, "/usr/bin/python3", False)
        self.assertEqual(gone, theirs)

    def test_removing_the_only_hooks_deletes_the_empty_hooks_key(self):
        self.assertEqual(self.m.merge_hooks(self.m.merge_hooks({}, "py", True), "py", False), {})


class InstallTest(Base):
    def test_install_always_with_hook_writes_the_expected_files_and_excludes_them(self):
        acts = self.always()
        for rel in (self.m.CONFIG_REL, self.m.MD_REL, self.m.SETTINGS_REL, self.m.HOOK_REL):
            self.assertTrue(os.path.exists(self.path(rel)), rel)
        self.assertEqual(self.m.current_level(self.proj), "always")
        self.assertTrue(any("exclude" in a for a in acts))
        ex = self.read(".git/info/exclude")
        for rel in (self.m.CONFIG_REL, self.m.MD_REL, self.m.HOOK_REL, self.m.OVERRIDE_REL):
            self.assertIn(rel, ex.split("\n"))
        with open(self.path(self.m.HOOK_REL), encoding="utf-8") as a, open(os.path.join(_HERE, "delegation_level.py"), encoding="utf-8") as b:
            self.assertEqual(a.read(), b.read())

    def test_dry_run_changes_nothing(self):
        acts = self.m.install(self.proj, "always", hook=True, dry_run=True)
        self.assertTrue(all(a.startswith("DRY RUN") for a in acts))
        self.assertFalse(os.path.exists(self.path(self.m.CONFIG_REL)))
        self.assertFalse(os.path.exists(self.path(self.m.MD_REL)))

    def test_hook_is_only_installed_at_level_always(self):
        self.m.install(self.proj, "medium", hook=True)
        self.assertFalse(os.path.exists(self.path(self.m.HOOK_REL)))
        self.assertFalse(os.path.exists(self.path(self.m.SETTINGS_REL)))
        self.assertFalse(self.m.read_config(self.proj)["hook"])

    def test_moving_away_from_always_removes_the_hook_and_its_copy_but_keeps_the_users_hooks(self):
        os.makedirs(self.path(".claude"))
        with open(self.path(self.m.SETTINGS_REL), "w") as f:
            json.dump({"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "their.sh"}]}]}}, f)
        self.always()
        self.m.install(self.proj, "low", hook=False)
        self.assertFalse(os.path.exists(self.path(self.m.HOOK_REL)))
        s = json.loads(self.read(self.m.SETTINGS_REL))
        self.assertEqual([h["command"] for e in s["hooks"]["PreToolUse"] for h in e["hooks"]], ["their.sh"])
        self.assertIn(self.m.LEVEL_TITLE["low"], self.read(self.m.MD_REL))

    def test_existing_claude_local_md_is_backed_up_and_its_text_kept(self):
        with open(self.path(self.m.MD_REL), "w", encoding="utf-8") as f:
            f.write("# private\nmy secret note\n")
        self.always()
        self.assertTrue(self.read(self.m.MD_REL).startswith("# private\nmy secret note\n"))
        self.assertTrue([n for n in os.listdir(self.proj) if n.startswith("CLAUDE.local.md.bak.")])

    def test_remove_undoes_everything_it_added_and_nothing_else(self):
        with open(self.path(self.m.MD_REL), "w", encoding="utf-8") as f:
            f.write("# private\nmy note\n")
        self.always()
        self.m.remove(self.proj)
        self.assertEqual(self.read(self.m.MD_REL).strip(), "# private\nmy note\n".strip())
        for rel in (self.m.CONFIG_REL, self.m.HOOK_REL):
            self.assertFalse(os.path.exists(self.path(rel)), rel)
        self.assertNotIn(self.m.HOOK_TAG, self.read(self.m.SETTINGS_REL))
        self.assertEqual(self.m.current_level(self.proj), "on-request")

    def test_default_level_is_on_request_and_a_bad_value_falls_back(self):
        self.assertEqual(self.m.current_level(self.proj), "on-request")
        os.makedirs(self.path(".claude"))
        with open(self.path(self.m.CONFIG_REL), "w") as f:
            f.write('{"level": "turbo"}')
        self.assertEqual(self.m.current_level(self.proj), "on-request")

    def test_bad_level_and_bad_directory_are_refused(self):
        with self.assertRaises(ValueError):
            self.m.install(self.proj, "turbo")
        with self.assertRaises(ValueError):
            self.m.install(os.path.join(self.proj, "nope"), "low")


class PreToolHookTest(Base):
    def setUp(self):
        super().setUp()
        self.always()

    def test_edits_inside_the_project_are_denied_with_a_reason_Claude_can_act_on(self):
        for tool in ("Edit", "Write", "MultiEdit"):
            out = self.edit("src/app.js", tool)
            self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny", tool)
        reason = self.edit("src/app.js")["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn("agent_run.py", reason)
        self.assertIn("!self", reason)
        self.assertIn("Do not ask the user to type it", reason)

    def test_absolute_paths_inside_the_project_are_denied_too(self):
        self.assertIsNotNone(self.edit("src/app.js", abs_path=True))

    def test_allow_listed_files_and_other_tools_and_outside_files_are_allowed(self):
        for rel in ("deploy.xml", "manifest.xml", "CLAUDE.local.md", ".claude/settings.local.json", ".gitignore",
                    ".env", "sub/.env.local", "CLAUDE.md"):
            self.assertIsNone(self.edit(rel), rel)
        self.assertIsNone(self.m.decide_pretool({"tool_name": "Read", "tool_input": {"file_path": "x"}, "session_id": "s"}, self.proj))
        self.assertIsNone(self.m.decide_pretool({"tool_name": "Bash", "tool_input": {"command": "ls"}, "session_id": "s"}, self.proj))
        self.assertIsNone(self.m.decide_pretool({"tool_name": "Edit", "tool_input": {"file_path": "/etc/hosts"}, "session_id": "s"}, self.proj))
        self.assertIsNone(self.edit("../outside.js"))

    def test_nothing_is_blocked_unless_the_level_is_always_and_the_hook_is_on(self):
        self.m.install(self.proj, "medium")
        self.assertIsNone(self.edit("src/app.js"))
        self.m.install(self.proj, "always", hook=False)
        self.assertIsNone(self.edit("src/app.js"))

    def test_the_override_is_for_one_session_only(self):
        self.assertIn("lifted", self.m.handle_userprompt({"session_id": "s1", "prompt": "please !self for now"}, self.proj))
        self.assertIsNone(self.edit("src/app.js", sid="s1"))
        self.assertIsNotNone(self.edit("src/app.js", sid="s2"))

    def test_text_Claude_writes_cannot_lift_the_block(self):
        # the override comes only from what the USER typed (UserPromptSubmit); the magic words inside a tool's own
        # arguments (file content, a command) must not count, or Claude could open the door itself
        for field in ("new_string", "content", "old_string", "file_path"):
            payload = {"tool_name": "Edit", "session_id": "s9",
                       "tool_input": {"file_path": "src/app.js", field: "x !self ให้ claude ทำเองรอบนี้ x"}}
            if field == "file_path":
                payload["tool_input"]["file_path"] = "src/!self.js"
            self.assertIsNotNone(self.m.decide_pretool(payload, self.proj), field)
        self.assertFalse(os.path.exists(self.path(self.m.OVERRIDE_REL)))

    def test_notebook_edits_are_covered_too(self):
        out = self.m.decide_pretool({"tool_name": "NotebookEdit", "tool_input": {"notebook_path": self.path("a.ipynb")}, "session_id": "s"}, self.proj)
        self.assertIsNotNone(out)


class PromptHookTest(Base):
    def setUp(self):
        super().setUp()
        self.always()

    def sessions(self):
        p = self.path(self.m.OVERRIDE_REL)
        return [s["session_id"] for s in json.load(open(p))["sessions"]] if os.path.exists(p) else []

    def test_the_users_phrase_sets_the_override_and_is_case_insensitive_and_thai_works(self):
        self.m.handle_userprompt({"session_id": "a", "prompt": "do it !SELF"}, self.proj)
        self.m.handle_userprompt({"session_id": "b", "prompt": "ขอ ให้ Claude ทำเองรอบนี้ นะ"}, self.proj)
        self.assertEqual(sorted(self.sessions()), ["a", "b"])

    def test_text_without_a_phrase_does_nothing(self):
        self.assertIsNone(self.m.handle_userprompt({"session_id": "a", "prompt": "fix the bug in app.js"}, self.proj))
        self.assertEqual(self.sessions(), [])

    def test_release_phrase_turns_it_off_again(self):
        self.m.handle_userprompt({"session_id": "a", "prompt": "!self"}, self.proj)
        msg = self.m.handle_userprompt({"session_id": "a", "prompt": "ok !agent"}, self.proj)
        self.assertIn("ended", msg)
        self.assertEqual(self.sessions(), [])
        self.assertIsNotNone(self.edit("src/app.js", sid="a"))

    def test_both_phrases_in_one_message_set_nothing(self):
        self.m.handle_userprompt({"session_id": "a", "prompt": "!self !agent"}, self.proj)
        self.assertEqual(self.sessions(), [])

    def test_the_list_is_capped_and_the_same_session_is_not_added_twice(self):
        for i in range(60):
            self.m.handle_userprompt({"session_id": "s%d" % i, "prompt": "!self"}, self.proj)
        self.assertEqual(len(self.sessions()), 50)
        self.assertEqual(self.sessions()[-1], "s59")
        self.m.handle_userprompt({"session_id": "s59", "prompt": "!self"}, self.proj)
        self.assertEqual(self.sessions().count("s59"), 1)

    def test_other_levels_ignore_the_phrase(self):
        self.m.install(self.proj, "medium")
        self.assertIsNone(self.m.handle_userprompt({"session_id": "a", "prompt": "!self"}, self.proj))
        self.assertEqual(self.sessions(), [])


class FailOpenAndCliTest(Base):
    def run_hook(self, kind, stdin, project=None):
        env = dict(os.environ, CLAUDE_PROJECT_DIR=project or self.proj)
        return subprocess.run([sys.executable, os.path.join(_HERE, "delegation_level.py"), "hook", kind], input=stdin,
                              capture_output=True, text=True, env=env, timeout=30)

    def test_garbage_input_never_blocks_and_never_crashes(self):
        self.always()
        for kind in ("pretool", "userprompt"):
            r = self.run_hook(kind, "this is not json")
            self.assertEqual((r.returncode, r.stdout), (0, ""), kind)
            self.assertIn("ignored", r.stderr)

    def test_a_broken_config_file_means_edits_are_allowed(self):
        self.always()
        with open(self.path(self.m.CONFIG_REL), "w") as f:
            f.write("{ not json")
        payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": "a.js"}, "session_id": "s"})
        r = self.run_hook("pretool", payload)
        self.assertEqual((r.returncode, r.stdout), (0, ""))

    def test_the_cli_hook_prints_the_deny_json_and_the_project_copy_runs_on_its_own(self):
        self.always()
        payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": "a.js"}, "session_id": "s"})
        r = self.run_hook("pretool", payload)
        self.assertEqual(json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")
        copy = subprocess.run([sys.executable, self.path(self.m.HOOK_REL), "hook", "pretool"], input=payload, capture_output=True,
                              text=True, env=dict(os.environ, CLAUDE_PROJECT_DIR=self.proj), cwd=tempfile.gettempdir(), timeout=30)
        self.assertEqual(json.loads(copy.stdout)["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_cli_refuses_a_bad_level_and_shows_the_default(self):
        script = os.path.join(_HERE, "delegation_level.py")
        r = subprocess.run([sys.executable, script, "set", "--level", "turbo", "--project", self.proj], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        r = subprocess.run([sys.executable, script, "show", "--project", self.proj], capture_output=True, text=True)
        self.assertIn("on-request (default - nothing set)", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=1)
