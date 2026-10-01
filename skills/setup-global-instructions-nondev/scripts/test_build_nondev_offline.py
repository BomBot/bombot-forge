#!/usr/bin/env python3
"""Offline tests for build_nondev.py (no network, no Claude)."""
import importlib.util
import json
import os
import re
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))


def load():
    spec = importlib.util.spec_from_file_location("build_nondev", os.path.join(_HERE, "build_nondev.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class BuildNondevTest(unittest.TestCase):
    def setUp(self):
        self.m = load()
        self.out = self.m.build()
        self.dev = self.m.split_h1(open(self.m.DEV_SNAPSHOT, encoding="utf-8").read())

    def heads(self, text):
        return [h for h, _ in self.m.split_h1(text) if h]

    def test_sections_and_order(self):
        h = self.heads(self.out)
        starts = ["Role", "Accuracy", "Communication style", "Slack", "ห้ามใช้ SDF", "ขอบเขตงานผ่าน UI", "วิธีทำงาน",
                  "Git", "Session memory", "Browser automation"]
        self.assertEqual(len(h), len(starts), h)
        for got, want in zip(h, starts):
            self.assertTrue(got.startswith(want), (got, want))

    def test_developer_only_sections_are_gone(self):
        for dropped in ["SDF Deploy", "Code conventions", "Editing existing code", "Coding agent", "graphify",
                        "Claude Code: ย้าย project folder"]:
            self.assertNotIn(dropped, "\n".join(self.heads(self.out)))
        self.assertNotIn("project:deploy", self.out.split("# ห้ามใช้ SDF", 1)[0])

    def test_kept_sections_are_byte_identical_to_the_dev_snapshot(self):
        for prefix in ["Accuracy", "Communication style", "Slack", "Session memory", "Browser automation"]:
            body = self.m.pick(self.dev, prefix)
            self.assertIn(body, self.out, prefix)

    def test_the_ban_names_the_sdf_commands_and_the_upload(self):
        ban = self.m.pick(self.m.split_h1(open(self.m.OVERRIDES, encoding="utf-8").read()), "ห้ามใช้ SDF")
        for word in ["suitecloud", "project:deploy", "file:upload", "object:deploy", "XML", "JS", "File Cabinet"]:
            self.assertIn(word, ban)

    def nondev(self, prefix):
        return self.m.pick(self.m.split_h1(open(self.m.OVERRIDES, encoding="utf-8").read()), prefix)

    def test_the_ui_scope_has_three_levels_and_the_seven_steps(self):
        scope = self.nondev("ขอบเขตงานผ่าน UI")
        for level in ["ระดับ A", "ระดับ B", "ระดับ C"]:
            self.assertIn(level, scope)
        for word in ["go-live", "ผลกระทบ", "จดสภาพเดิม", "Claude in Chrome", "ย้อนกลับ", "OK"]:
            self.assertIn(word, scope)
        steps = [l for l in scope.splitlines() if l[:3] in ("1. ", "2. ", "3. ", "4. ", "5. ", "6. ", "7. ")]
        self.assertEqual(len(steps), 7, steps)

    def test_a_live_or_unknown_account_stops_the_run(self):
        scope = self.nondev("ขอบเขตงานผ่าน UI")
        self.assertRegex(scope, r"live แล้วหรือไม่รู้ → หยุด")

    def test_ui_customisation_is_allowed_in_B_and_no_longer_banned_in_the_ban_section(self):
        ban, scope = self.nondev("ห้ามใช้ SDF"), self.nondev("ขอบเขตงานผ่าน UI")
        b_line = [l for l in scope.splitlines() if l.startswith("**ระดับ B")][0]
        for thing in ["custom field", "custom record", "workflow", "Saved Search"]:
            self.assertIn(thing, b_line)
        # the old line banned these through the UI; the ban now only names scripts, and points at the scope section
        self.assertNotIn("ห้ามสร้าง/แก้ script, script deployment, workflow", ban)
        self.assertIn("script และ script deployment", ban)
        self.assertIn("ขอบเขตงานผ่าน UI", ban)

    def test_changes_through_bsk_clicks_stay_forbidden_and_deletion_is_level_C(self):
        scope = self.nondev("ขอบเขตงานผ่าน UI")
        self.assertIn("ห้ามใช้ `bsk` คลิก/กรอกเพื่อเปลี่ยนค่า", scope)
        c_line = [l for l in scope.splitlines() if l.startswith("**ระดับ C")][0]
        for thing in ["SDF", "JS", "role/permission", "ลบอะไรก็ตาม"]:
            self.assertIn(thing, c_line)

    def test_fenced_hash_lines_are_not_headings(self):
        sample = "# A\nx\n```bash\n# not a heading\nls\n```\n# B\ny\n"
        self.assertEqual([h for h, _ in self.m.split_h1(sample) if h], ["A", "B"])

    def test_missing_shared_section_is_refused_not_papered_over(self):
        broken = "".join(b for h, b in self.dev if not (h and h.startswith("Browser automation")))
        with self.assertRaises(ValueError):
            self.m.build(dev_text=broken)

    def test_missing_nondev_section_is_refused(self):
        with self.assertRaises(ValueError):
            self.m.build(nondev_text="# Role\nonly this\n")

    def test_deny_rules_are_the_measured_set(self):
        self.assertEqual(self.m.DENY_RULES, ["Bash(suitecloud:*)", "Bash(npx suitecloud:*)", "Bash(*suitecloud*)"])
        self.assertEqual(json.loads(json.dumps(self.m.DENY_RULES)), self.m.DENY_RULES)

    def test_no_account_shaped_numbers(self):     # the repo's redaction CI rejects bare 7-8 digit numbers
        self.assertEqual(re.findall(r"(?<![0-9])[0-9]{7,8}(?![0-9])", self.out), [])


if __name__ == "__main__":
    unittest.main(verbosity=1)
