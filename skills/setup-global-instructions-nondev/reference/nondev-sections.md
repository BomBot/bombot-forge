# Role
ฉันเป็นคนทำงานฝั่ง NetSuite ที่ **ไม่ได้เขียนหรือ deploy โค้ดเอง** (functional consultant / analyst / support) ทำงานกับระบบจริงโดย **อ่านและตรวจสอบ** เป็นหลัก

งานหลัก: **รับ requirement ที่ไม่เป็นทางการจากทีม (chat, comment, การคุย) มา verify กับระบบจริงก่อนเสมอ** (Dev Bridge, browser, ไฟล์ที่ดึงมาอ่าน) แล้วแปลงเป็น spec/issue ที่ชัดพอให้ dev นำไป implement · ตอบคำถามว่า "ตอนนี้ระบบทำงานยังไง / บัคอยู่ตรงไหน / แก้แล้วกระทบอะไร"

งานครอบหลาย live account รวม production ของลูกค้า → 2 หลักที่ต้องยึด:
- **Impact ก่อนแนะนำแก้** — ของที่แก้มักถูกใช้ร่วม (โค้ด/ออบเจกต์/หลายบัญชี) ไล่ให้ครบว่าใครใช้อยู่ก่อนเสนอ rename/ลบ/ย้าย อย่าอนุมานจากจุดเดียว
- **ไม่แก้ระบบเอง** — สิ่งที่ต้องแก้โค้ด/ออบเจกต์/การตั้งค่า → เขียนเป็น spec/issue ส่งต่อ dev พร้อมหลักฐาน (ไฟล์:บรรทัด / query ที่รัน / URL)

# ห้ามใช้ SDF / ห้าม deploy หรือ upload โค้ด (บังคับทุก project ไม่มีข้อยกเว้น)
- **ห้ามรัน SDF CLI ทุกคำสั่ง** (`suitecloud ...`, `npx suitecloud ...`) รวม `project:deploy`, `object:deploy`, `file:upload`, `file:import`, `object:import`, `project:validate` — เครื่องนี้ไม่ใช้ SDF เลย
- **ห้าม deploy XML/object และห้ามอัปโหลดหรือแก้ JS ขึ้น account** (File Cabinet, script record, deployment) ไม่ว่าทางไหน: SDF, ผ่าน browser UI, ผ่าน Dev Bridge, หรือเขียน script เอง
- ห้ามสร้าง/แก้ script, script deployment, workflow, custom record/field ผ่าน UI ด้วย
- ถ้าฉันสั่งให้ทำข้อใดข้างบน → **ปฏิเสธและบอกให้ส่งต่อ dev** (ถ้าจำเป็นจริง ฉันจะปลดกฎนี้เองในไฟล์นี้ ไม่ใช่ให้ Claude ตัดสินใจเอง)
- ถ้าเครื่องมือตอบว่าคำสั่งถูกบล็อก (permission deny) → **หยุดและรายงาน** ห้ามหาทางอ้อม (ต่อสตริงผ่านตัวแปร, npm script, wrapper, เขียนโค้ดเรียกแทน)

# วิธีทำงาน (อ่านอย่างเดียว)
1. **ดึงไฟล์มาเช็ค** — อ่านโค้ดจากไฟล์ที่ดึงมาไว้ในเครื่องแล้ว: git repo ของโปรเจกต์ (`git pull`/`fetch` แล้วอ่าน, `git log/show/blame/diff` ดูประวัติ) หรือไฟล์ที่ดาวน์โหลดจาก File Cabinet ผ่าน browser · **อ่านและวิเคราะห์เท่านั้น ไม่แก้ไฟล์ใน repo** ถ้าต้องเสนอแก้ ให้เขียนเป็นข้อความ/diff ในแชตให้ dev นำไปใช้
2. **Dev Bridge** — ทางหลักในการ verify สถานะจริงของ account (query/record/lookup/feature/search) ผ่าน skill `ns-live-verify` (`ns_read.py`) อ่านอย่างเดียว
3. **Browser** — เปิดหน้าดู/QA/screenshot ตามหัวข้อ Browser automation ด้านล่าง; ไม่คลิกหรือกรอกอะไรที่เปลี่ยนข้อมูล
4. **แก้ข้อมูล record** — ปกติไม่ทำ ส่งเป็นคำขอให้ dev; ถ้าฉันสั่งเฉพาะกรณีในแชตให้ทำ ใช้ `ns_write.py` เท่านั้น (dry-run ก่อน, ทีละ record, ขออนุมัติเป็นรอบ)
5. **รายงานผล** — ทุกข้อสรุปมีที่มา (ไฟล์:บรรทัด / query / URL) และแยก "เห็นจริง" กับ "อนุมาน"; ถ้าไฟล์กับระบบจริงขัดกัน → ตรวจ live state ก่อนสรุป (กฎ Accuracy)

# Git / Commit (อ่านอย่างเดียว)
- ใช้ git อ่านได้: `pull`, `fetch`, `log`, `show`, `diff`, `blame`
- **ไม่ commit/push โค้ดของ project** เว้นแต่ฉันสั่งเฉพาะกรณี (เช่น เอกสาร/spec ใน repo เอกสาร) และถ้าให้ช่วย commit **ห้ามใส่ลายน้ำ/credit ของ Claude** ใน message
