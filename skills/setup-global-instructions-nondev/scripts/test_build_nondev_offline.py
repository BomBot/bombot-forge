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
        starts = ["Role", "Accuracy", "Communication style", "Slack", "ห้ามใช้ SDF", "ขอบเขตงานผ่าน UI", "Hotfix JS",
                  "วิธีทำงาน", "Git", "Session memory", "Browser automation"]
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
        self.assertIn("script record และ script deployment", ban)
        self.assertIn("ขอบเขตงานผ่าน UI", ban)

    def test_ui_changes_go_through_claude_in_chrome_in_front_of_the_user_and_deletion_is_level_C(self):
        scope = self.nondev("ขอบเขตงานผ่าน UI")
        self.assertIn("ใช้ Claude in Chrome ไม่ใช่ `bsk`", scope)
        self.assertIn("ฉันไม่เห็น", scope)          # the reason is visibility, not a ban on bsk clicking
        c_line = [l for l in scope.splitlines() if l.startswith("**ระดับ C")][0]
        for thing in ["SDF", "JS", "role/permission", "ลบอะไรก็ตาม"]:
            self.assertIn(thing, c_line)

    def hotfix_steps(self):
        hf = self.nondev("Hotfix JS")
        return hf, [l for l in hf.splitlines() if l[:3] in tuple("%d. " % n for n in range(1, 10))]

    def test_the_hotfix_lane_is_narrow_and_has_nine_steps(self):
        hf, steps = self.hotfix_steps()
        self.assertEqual(len(steps), 9, steps)
        for word in ["บั๊กจริง", "หน้างานรอไม่ได้", "ดุลยพินิจ", "ไฟล์ .md ส่งให้ dev", "Claude in Chrome", "ห้าม SDF", "bsk",
                     "ฟีเจอร์ใหม่ การปรับปรุง หรือ refactor **ไม่เข้า**"]:
            self.assertIn(word, hf)

    def test_every_hotfix_is_backed_up_commented_confirmed_and_verified(self):
        hf, steps = self.hotfix_steps()
        for word in ["HOTFIX-NODEV", "why:", "what:", "original:", "sha256", "สำรองไฟล์เดิม", "ดาวน์โหลดไฟล์บน account กลับมาเทียบ",
                     "ย้อนกลับ", "ตรวจซ้ำว่าแก้ถูกจริง", "รายงานฉันก่อนขอ OK", "OK ในแชตใช้ได้ครั้งเดียว"]:
            self.assertIn(word, hf)
        idx = lambda needle: next(i for i, l in enumerate(steps) if needle in l)
        self.assertLess(idx("สำรองไฟล์เดิม"), idx("แก้ในสำเนาในเครื่องก่อน"))      # backup before editing
        self.assertLess(idx("แก้ในสำเนาในเครื่องก่อน"), idx("อัปโหลดผ่าน Claude in Chrome"))   # edit locally, upload later
        self.assertLess(idx("รายงานฉันก่อนขอ OK"), idx("อัปโหลดผ่าน Claude in Chrome"))        # tell the user, get OK, then upload
        self.assertLess(idx("อัปโหลดผ่าน Claude in Chrome"), idx("verify หลังอัปโหลด"))

    def test_the_dev_overwrite_warning_is_in_the_confirmation_and_in_the_note(self):
        hf, steps = self.hotfix_steps()
        confirm = [l for l in steps if "รายงานฉันก่อนขอ OK" in l][0]
        note = [l for l in steps if "เขียนโน้ตให้ dev" in l][0]
        for line in (confirm, note):
            self.assertIn("ทับ", line)
        self.assertIn("เอาไฟล์จาก repo หรือ SDF deploy ทับไฟล์นี้ก่อน merge", note)
        self.assertIn("บอก dev ตรงๆ", note)

    def test_the_ban_names_exactly_one_exception_and_sdf_has_none(self):
        ban = self.nondev("ห้ามใช้ SDF")
        self.assertIn("ไม่มีข้อยกเว้น", ban)
        self.assertIn("ข้อยกเว้นเดียว", ban)
        self.assertIn("Hotfix JS", ban)
        self.assertNotIn("ไม่มีข้อยกเว้น)", ban.splitlines()[0])      # the heading no longer claims there is none for JS

    def test_level_C_is_done_by_hand_by_the_user(self):
        c_line = [l for l in self.nondev("ขอบเขตงานผ่าน UI").splitlines() if l.startswith("**ระดับ C")][0]
        self.assertIn("ผู้ใช้แก้ด้วยมือเอง", c_line)
        self.assertIn("ยกเว้น hotfix", c_line)

    def test_the_three_lists_come_first_and_the_reply_ends_with_a_next_step_line(self):
        # a reply that ends in a list left the chat input without a suggested next prompt (reported 2026-10-01);
        # the rule must say: lists first, then one closing "next step" line, never end on the lists
        self.assertIn("**ไว้ก่อน** แล้ว**ปิดท้ายคำตอบด้วยบรรทัดเดียว", self.out)
        self.assertIn("ขั้นถัดไป", self.out)
        self.assertIn("ห้ามจบคำตอบด้วยรายการ 3 ช่อง", self.out)
        self.assertNotIn("ท้ายคำตอบสรุปเป็น 3 ช่อง", self.out)

    def test_the_kept_browser_section_confirms_the_round_instead_of_banning_bsk_clicks(self):
        self.assertNotIn("ห้ามใช้ bsk *คลิก*", self.out)
        self.assertIn("ต้องยืนยันก่อนทุกรอบ", self.out)
        self.assertIn("list ให้ฉันเห็นว่ารอบนี้จะ process/คลิก/submit/update อะไรบ้าง", self.out)
        self.assertIn("dialog ที่ไม่อยู่ใน list", self.out)

    def test_browser_lanes_are_read_from_the_machine_and_cdp_is_never_assumed(self):
        # a machine that chose bsk only must not be sent to cdp: lanes come from browser.json, escalation is Claude in Chrome then the user
        self.assertIn("~/.config/bombot-forge/browser.json", self.out)
        self.assertIn("เฉพาะ lane ที่เครื่องนั้นมีจริง", self.out)
        self.assertIn("เครื่องที่เลือก bsk อย่างเดียวห้ามพูดถึงหรือสลับไป cdp", self.out)
        self.assertIn("fallback (เฉพาะเครื่องที่ติดตั้ง)", self.out)
        self.assertNotIn("ใช้ cdp แทนจะปลอดภัยกว่า", self.out)
        self.assertNotIn("(fallback / write บน production)", self.out)

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
