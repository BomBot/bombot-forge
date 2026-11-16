# คำสั่งสำหรับ Claude: ตั้งเครื่องคนใหม่ของทีม Teibto (starter)

ไฟล์นี้เขียนถึง Claude ที่ทำงานบนเครื่องของคนใหม่ในทีม (ผู้ใช้คือคนที่ส่งไฟล์นี้ให้คุณ) อ่านทั้งไฟล์ก่อน แล้วทำตามทีละขั้น
ตอบผู้ใช้เป็นไทยคำอังกฤษคำ สั้น ภาษาง่าย (ผู้ใช้อาจไม่ใช่ dev)

## กฎ

- ติดตั้งหรือแก้ config อะไรก็ตาม: บอกคำสั่งที่จะรันก่อน แล้วรอผู้ใช้ OK
- ห้ามอ่าน พิมพ์ หรือขอ password, token, รหัส 2FA การ login ทุกชนิดผู้ใช้ทำเองในหน้าเว็บที่เปิดขึ้นมา
- ห้ามเขียนข้อมูลใน NetSuite ห้าม commit, push, deploy หรือส่งข้อความ Slack/email
- ขั้นไหนล้มเหลว ให้หยุด รายงาน error จริง แล้วเสนอทางแก้

## ขั้น 1: ติดตั้ง plugin `bombot-forge`

- ตรวจก่อน: `claude plugin list` มี `bombot-forge` แล้วหรือยัง ถ้ามีแล้วข้ามไปขั้น 2
- ยังไม่มี (บอกผู้ใช้ก่อนว่าจะติดตั้งชุด skill ของทีม แล้วรอ OK):

```
claude plugin marketplace add https://github.com/BomBot/bombot-forge.git
claude plugin install bombot-forge@bombot-forge
```

- ขอให้ผู้ใช้พิมพ์ `/reload-plugins` ในช่องแชท (หรือ restart Claude Code) เพื่อให้ skill ใหม่โหลด

## ขั้น 2: รัน `setup-init`

- ถ้ามี skill `/bombot-forge:setup-init` แล้ว ให้เรียกใช้เลย
- ถ้ายังไม่มี (reload ไม่ติด) ให้อ่าน
  `~/.claude/plugins/cache/bombot-forge/bombot-forge/<version>/skills/setup-init/SKILL.md`
  (ดู `<version>` จาก `claude plugin list`) แล้วทำตามไฟล์นั้น รวมถึง skill อื่นที่มันสั่งให้รัน ก็อ่านจาก path เดียวกัน

`setup-init` จะตรวจ OS ทำ checklist ทุกอย่าง แล้วพาทำทีละขั้นจนจบ ไม่ต้องทำอะไรนอกเหนือจากที่ skill บอก
