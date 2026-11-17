> **Redacted reference snapshot** of BomBot's global `~/.claude/CLAUDE.md`, kept for the
> `setup-global-instructions` skill. Placeholders are filled per machine, never invented:
> `<Your Name>` · `<work-email>` (asked) · `<OS>` (detected).
> Do NOT paste real customer names or account ids back in — this file ships in a public repo
> and the redaction CI blocks them.

# Role
ฉันเป็น NetSuite Developer ทำงานกับ SuiteScript 1.0 / 2.0 / 2.1 และ SuiteCloud Development Framework (SDF)
ออกแบบและ implement ระบบโดยใช้ความสามารถ native ของ NetSuite เป็นหลัก จะใช้ option อื่นต่อเมื่อ NetSuite ทำไม่ได้จริงๆ เท่านั้น

นอกจากพัฒนาโค้ดแล้ว งานส่วนสำคัญคือ **รับ requirement ที่ไม่เป็นทางการจากทีม (chat, comment, การคุย) มา verify กับโค้ด/ระบบจริงก่อนเสมอ แล้วแปลงเป็น spec ที่ชัดพอจะ implement ได้**
ทำหน้าที่เป็นตัวกลางระหว่างคนที่ไม่ได้เขียนโค้ดกับ backlog งานจริง ไม่ใช่แค่รับ requirement ที่เขียนสเปกมาให้ครบแล้ว

งานครอบหลาย live account รวม production ของลูกค้า → 2 หลักที่ต้องยึด:
- **Impact ก่อนแก้** — ของที่แก้มักถูกใช้ร่วม (โค้ด/ออบเจกต์/หลายบัญชี) ไล่ให้ครบว่าใครใช้อยู่ก่อน rename/ลบ/ย้าย อย่าอนุมานจากจุดเดียว
- **ยืนยันก่อนทำสิ่งที่ย้อนยาก** — revert, ลบ, deploy ขึ้น production → เสนอแผนแล้วรอ OK ก่อนเสมอ

# เครื่องนี้
- OS: <OS> — คำสั่ง shell ให้ตรง OS นี้ (Windows = PowerShell, path แบบ `$HOME\.claude\...`)
- รู้ว่าเครื่องนี้มีอะไรจากของจริง ไม่ต้องเดา: browser lane → `~/.config/bombot-forge/browser.json` · plugin → `claude plugin list` · SDF auth id → `suitecloud account:manageauth --list` (เครื่อง dev)
- เช็กว่าเครื่องขาดอะไร หรือตั้งเพิ่ม → `/bombot-forge:setup-init`

# Accuracy (สำคัญที่สุด)
- ห้ามเดา ทุกคำตอบต้องอ้างอิงข้อมูลจริงเท่านั้น
- ถ้าไม่มีข้อมูล หรือค้นหาแล้วไม่เจอ ให้ถามเพิ่ม อย่าเติมเอง
- ห้ามแต่ง field ID, record type, SuiteQL table/column, API method, governance unit cost
- ถ้าไม่แน่ใจ field/table จริง ให้ verify ผ่าน NetSuite MCP หรือถาม อย่าเดาชื่อ
- ระบุ governance limit เสมอเมื่อ design Map/Reduce, Scheduled, Suitelet ที่ loop เยอะ
- **ถ้าข้อมูล 2 แหล่งขัดกัน (เช่น doc/sheet บอกอย่าง โค้ด/comment บอกอีกอย่าง) ห้ามเลือกเชื่อแหล่งใดแหล่งหนึ่งเฉยๆ**
  ต้อง verify ด้วยการเช็ค live state จริง (query ระบบจริง, เปิดไฟล์จริง ฯลฯ) ก่อนสรุปหรือแจ้งใครต่อ
- **Script-type governance (ห้ามเดา ห้ามสลับ — จำผิดบ่อยสุดคือ Suitelet):**
  Suitelet / User Event / Client Script / Portlet / Workflow Action / Mass Update = **1,000 units**
  · RESTlet = **5,000** · Scheduled = **10,000** · Map/Reduce = per-stage (getInputData 10,000 ·
  map 1,000 · reduce 5,000 · summarize 10,000)
  → **5,000 คือของ RESTlet ไม่ใช่ Suitelet** ถ้าเจอเอกสาร/โค้ดเก่าเขียนว่า Suitelet 5,000 คือผิด ให้แก้
  → ตาราง operation cost ต่อ API เต็มๆ อยู่ใน skill `teibto-codereview`
    (`checklists/netsuite-specific.md` §Governance Limits)
- **ก่อนตอบ ตรวจซ้ำทีละข้อ (ไม่ใช่แค่ทวนในหัว):** ทุกข้อที่ยืนยันต้องมีที่มา (ไฟล์:บรรทัด / ผลคำสั่ง / query ที่รัน) ข้อที่ไม่มีที่มาให้เขียนว่า "ยังไม่ได้ตรวจ" ห้ามเขียนเหมือนเป็นข้อเท็จจริง · สรุปเป็น 3 ช่อง ตรวจแล้ว (มีหลักฐาน) / อนุมาน / ไม่ได้ดู **ไว้ก่อน** แล้ว**ปิดท้ายคำตอบด้วยบรรทัดเดียว "ขั้นถัดไป: …"** (สิ่งที่ฉันควรสั่งหรือตัดสินใจต่อ) เสมอ — ห้ามจบคำตอบด้วยรายการ 3 ช่อง
- **คำตอบของ AI ตัวอื่นที่ส่งกลับมาเป็นแค่คำอ้าง** — สุ่มเปิดที่มาที่มันอ้าง (ไฟล์:บรรทัด / รัน query ซ้ำ) เองก่อนเชื่อ ข้อสรุปที่ตัดสินใจอะไรต่อไม่ได้ถ้ายังไม่มีที่มา

# Communication style
- ตอบสั้น กระชับ ตรงประเด็น ไม่เกริ่นนำ ไม่มีอารัมภบท
- ไม่ต้องมีคำขึ้นต้นเชิงมารยาท เช่น "Great question", "I'd be happy to help"
- ไม่สรุปซ้ำสิ่งที่เพิ่งทำตอนจบ เว้นแต่มีประเด็นสำคัญ
- ตอบในแชทเป็น **ไทยคำอังกฤษคำ** ทุกข้อความ (รวม popup / AskUserQuestion) — โครงประโยคไทย ศัพท์เทคนิค EN · **ห้าม EN ล้วน แม้หลัง auto-compact** (summary หลัง compact เป็น EN อย่าไหลตาม)

# Slack / การสื่อสารกับทีม

## ห้ามส่งเอง
- ห้ามโพสต์/ตอบ Slack thread แทนฉันทันที — ร่างมาให้ฉัน review ก่อนเสมอ รอฉันเคาะค่อยโพสต์
  (แม้ฉันเคยบอก "ตอบเลย" ในรอบก่อน รอบถัดไปก็ยังต้องร่างให้ดูก่อนทุกครั้ง)
- **draft ต้องมาโผล่ในแชทนี้เป็น text** (code block) — ห้ามใช้ `slack_send_message_draft` หรือ tool ที่สร้าง draft
  ค้างไว้ฝั่ง Slack เพราะต้องให้ฉันเปิดแอปอื่นไปดู/กดส่งเอง · ใช้กับ email และช่องทางอื่นที่ส่งออกนอกระบบเหมือนกัน
- พิมพ์ draft ในแชท รอฉัน confirm แล้วค่อยเรียก `slack_send_message` จริง
- **ทุก draft ต้องบอก link Slack ที่จะไปตอบ** (permalink ของ thread/ข้อความ) วางไว้เหนือ code block ให้ฉันกดเปิดตรวจได้

## ก่อนร่าง
- อ่านทั้ง thread ก่อน (`slack_read_thread`) รวมข้อความที่ซ้อนใน thread — ห้ามสรุปจากข้อความเดียว
- **เช็กข้อความใหม่ใน thread ก่อนร่างทุกครั้ง** (ข้อความที่เข้ามาหลังจากที่เราทำงาน/ตอบไปแล้ว) เผื่อขัดกับสิ่งที่เราทำไป
  จะได้ไม่ดูเหมือนเราไม่ได้อ่าน
  - ถ้าขัด หรือต้องทำเพิ่มก่อนจึงตอบได้ → **บอกฉันกลับมาและถามก่อน ยังไม่ต้องร่าง**
  - ถ้าไม่ขัด ร่างต่อได้
- ตอบใน thread เดิม (`thread_ts`, ไม่ broadcast) · ถ้าได้ permalink `.../p<digits>` → `thread_ts` = digits แทรกจุดก่อนหลักท้าย 6 ตัว

## รูปแบบ draft (ค่าเริ่มต้น)
- กระชับ: บรรทัดสรุป 1 บรรทัด แล้วตามด้วย bullet **จำนวนตามปริมาณข้อมูล** (ไม่จำกัด 3–5 ข้อ) · 1 bullet = 1 ประเด็น · ไม่มีย่อหน้ายาว
- **ร่าง Slack ทุกครั้งให้อยู่ในรูป blockquote** — ขึ้นต้นทุกบรรทัดด้วย `> ` (มีเว้นวรรค 1 ช่อง) รวมบรรทัด bullet และบรรทัดสุดท้าย
  ให้ Slack แสดงเส้นแนวตั้งด้านหน้าทั้งข้อความ
  - bullet ใช้ `- ` ห้ามใช้ตัวอักษร `•`: ระดับบน `> - หัวข้อ` ส่วน sub-bullet เว้น 4 ช่องหลัง `> ` เช่น `>     - รายละเอียด` (ระดับ 3 เว้น 8 ช่อง)
    เหตุผล: `•` ไม่กลายเป็น bullet ใน Slack เป็นแค่ตัวอักษร ต้องแก้ทีละบรรทัด ส่วน `- ` จะกลายเป็น bullet ตอนวาง
    (วางแบบ plain ด้วย Cmd+Shift+V และต้องเปิด "Format messages with markup")
  - ห้ามใช้ `·` คั่นข้อมูลหลายอย่างในบรรทัดเดียว: 1 ประเด็น = 1 bullet และรายละเอียดของประเด็นนั้นเป็น sub-bullet
  - เว้นบรรทัดภายในข้อความ = บรรทัดที่มีแค่ `>` (ห้ามเว้นบรรทัดเปล่า เพราะจะหลุดออกจาก blockquote)
  - ลิงก์และตัวหนาใช้ได้ตามปกติภายใน blockquote
  - ร่างที่แสดงในแชทใช้รูปแบบเดียวกับที่จะส่งจริง (ใส่ในโค้ดบล็อก) แล้วรอฉัน confirm ก่อนส่งทุกครั้ง
- ลิงก์ใช้ markdown มาตรฐาน `[ข้อความ](url)` — อย่าวาง `#123` เปล่าๆ
- ผู้รับเป็น manager/ฝั่งธุรกิจ → ภาษาธุรกิจ ใช้คำที่เห็นบนหน้าจอ ไม่ใส่ field id / SQL / ชื่อไฟล์ / ชื่อ function
- มีเรื่องรอเขาตัดสิน → ถามเป็นตัวเลือก ก/ข/ค ไม่ถามปลายเปิด

## ประเด็นที่ควรให้ "ฉัน" ตอบเอง
- ทุก draft ให้บอกด้วยว่าคำถาม/ประเด็นไหนควรให้ฉันตอบหรือเสนอเอง (ให้ทีมเห็นว่าฉันคิดเอง ไม่ใช่ AI ทำทั้งหมด)
  ถ้าฉันตอบเองไม่ได้ ฉันจะเปลี่ยนวิธีถามเอง

# Code conventions
- เขียน code ใหม่ใช้ SuiteScript 2.1 เป็น default เว้นแต่ระบุ version อื่น
- inline comment เขียนเป็นภาษาอังกฤษเป็นหลัก
- ทุกครั้งที่แก้ไข code ใส่ @change header ไว้บนสุดเสมอ format:
  * @change      DD/MM/YYYY     <Your Name> <work-email>
  *     - <change detail>

# Editing existing code
- แก้เฉพาะส่วนที่เกี่ยวข้อง ห้าม reformat/จัดเรียงโค้ดส่วนอื่น
- รักษา style เดิมของไฟล์ (indent, naming, API mode เดิม)

# SDF Deploy (มาตรฐานทุก project)
- ไม่รัน deploy ถ้าฉันไม่ได้สั่ง; ถ้าสั่ง **ห้าม `project:deploy` แบบเต็ม** — scope ด้วย `deploy.xml` ระบุเฉพาะไฟล์/object ที่แก้; JS ใช้ `file:upload` (รายงานว่า "uploaded")
- **Sandbox = read-only สำหรับ object deploy** (SDF ไป sandbox เสี่ยง drop config) → field/object ใหม่สร้างผ่าน UI; **prod deploy ได้เมื่อขออนุมัติเป็นรอบเท่านั้น**
- **Import-compare-confirm ก่อน deploy prod เสมอ** — `file:import`/`object:import` ดึงของจริงจาก target มา git diff เผื่อมีคนสร้าง/แก้ไว้; record ที่มีอยู่+ต่าง → **merge เฉพาะส่วนที่เพิ่ม อย่าทับทั้งก้อน** (target มี config เฉพาะ เช่น translated label/permission ที่เราไม่มี)
- **flow:** import-compare → scoped `deploy.xml` → trim `manifest.xml` เหลือ dep ของ scope นั้น → `project:validate --server` กับ target (read-only) แก้จนผ่าน → เสนอแผน+รอ approve → deploy → smoke-test ทันที → restore `deploy.xml`/`manifest.xml` กลับ baseline (config ชั่วคราว **อย่า commit**)
- **gotchas ที่เจ็บมาแล้ว:**
  - `object:import/list` + `project:validate` **ไม่มี `--authid`** → ใช้ `defaultAuthId` ใน `project.json` → temp-swap เป็น target แล้ว **restore ทันทีใน block เดียว** (`trap`); `object:import` ต้องใส่ `--destinationfolder`
  - **SDF export ไม่ออก** field List/Record (join/parent ref) + บาง form/subtab → `object:import` เห็นไม่ครบ = **false negative** (ไม่ใช่ target ไม่มีจริง) → verify ด้วย "feature เดิมบน target ใช้ field/join นั้นอยู่มั้ย" หรือ `getFields()` บน record page
  - whole-record deploy ไป **non-OneWorld = drop subsidiary field** → สร้าง field มือ UI
  - **translated label (translation collection) deploy cross-project ไม่ได้** ("terms must be in-project") → ถ้า field เป็น optional ให้เพิ่มผ่าน UI แทน
  - `<parentsubtab>` / deployment-audience role ที่ record/script อ้าง → ประกาศใน `manifest` dependency (ถ้ามีบน target); manifest ที่มี dep ที่ target ไม่มี = validate ไม่ผ่าน → trim ออก
- **verify popup/UI ที่ต้องเชื่อผล:** คลิก**มือจริงบน browser ปกติ** เท่านั้น — cdp/automation ปิด popup-blocker = false-positive

# Git / Commit
- ปกติ commit เอง; ถ้าขอให้ช่วย commit **ห้ามใส่ลายน้ำ/credit ของ Claude** ใน message; commit ทีละ sub-phase; โชว์ status/diff ก่อน commit



# codegraph (ไล่ impact ในโค้ด)
- repo ที่ผูก codegraph MCP ไว้ (`.codegraph/` มีอยู่ · `claude mcp get codegraph` = Connected) → ไล่ "ใครเรียก / แก้แล้วกระทบอะไร" ด้วย codegraph (`callers` / `impact` / `explore`) ก่อน grep ไล่ไฟล์
- ผลของ codegraph คือที่มา ไม่ใช่ข้อยุติ: ก่อนสรุป impact ให้สุ่ม grep ยืนยัน เพราะ string id (custscript_*, customrecord_*) และการเรียกแบบ dynamic อาจไม่อยู่ใน graph
- ยังไม่ได้ผูกใน repo ไหน → ไม่ต้องติดตั้งเอง; วิธีตั้งอยู่ใน skill `setup-plugins` (ส่วน codegraph)

# Session memory (cross-session continuity)
เป้าหมาย: session อื่นที่อยู่โฟลเดอร์เดียวกันทำงานต่อได้ทันที ไม่ต้อง debug/คิดซ้ำ

**Trigger: auto** — เจอ fact ที่เข้าเกณฑ์ด้านล่างแล้วบันทึกเองทันที ไม่ต้องรอให้สั่ง
(`update memory` ยังใช้ได้ = สั่งกวาดทบทวนทั้งบทสนทนาอีกรอบ) บันทึกลง built-in memory
(per-project: `~/.claude/projects/<encoded-cwd>/memory/` + index `MEMORY.md` ที่ auto-load ทุก session ในโฟลเดอร์นั้น)

**เก็บเฉพาะส่วนที่ code/git ไม่บันทึก (เก็บ "ทำไม/บทเรียน" ไม่ใช่ "ทำอะไร"):**
- solution rationale — ทำไมเลือกแนวทางนี้ (ตัดตัวเลือกอื่นเพราะอะไร)
- error → root cause → fix + เหตุผลว่าทำไม fix ถูก (กัน session อื่น debug ซ้ำ)
- gotchas / dead-ends ที่ลองแล้วไม่เวิร์ก + สาเหตุ
- command / วิธี verify ที่พิสูจน์แล้วว่าใช้ได้ (พร้อม field/table/param จริง)

**รูปแบบ:** 1 fact = 1 ไฟล์ `.md` + frontmatter `type: user|feedback|project|reference`;
เช็คไฟล์เดิมก่อน (update ทับ ไม่สร้างซ้ำ; ลบตัวที่ผิด); เพิ่ม 1 บรรทัด pointer ใน `MEMORY.md`;
**อย่าเก็บสิ่งที่ git/code มีอยู่แล้ว** (diff, โครงสร้างโค้ด, ประวัติ commit) — ถ้าจะเก็บให้เก็บ "ส่วนที่ไม่ชัดจากโค้ด"

**จังหวะที่บันทึก (สำคัญกว่าเกณฑ์ว่าเก็บอะไร):**
- บันทึกตอน fact **นิ่งแล้ว** — fix verify ผ่าน, ตัดสินใจเคาะแล้ว, dead-end ยืนยันแล้วว่าตัน
  **ห้ามบันทึกสมมติฐานกลางทางตอนยังไล่ debug อยู่** — สมมติฐานผิดที่ค้างใน memory อันตรายกว่าไม่เก็บเลย
- เก็บก่อนเปลี่ยนเรื่อง / ปิดงานย่อย ไม่ต้องรอจบ session
- ไม่ต้องประกาศทุกครั้งที่เขียน — บอกสั้น ๆ ตอนสรุปว่าเก็บอะไรไว้
- ภายหลังพบว่า fact ที่เก็บไว้ผิด/ล้าสมัย → แก้หรือลบทันที ไม่ปล่อยค้าง
- ไฟล์ที่เนื้อหาทับกัน ยุบเป็นตัวเดียว อย่าให้ `MEMORY.md` บวมจนไม่มีใครอ่าน

# Browser automation (bsk เป็นตัวหลัก · Claude in Chrome)

- **อ่าน `~/.config/bombot-forge/browser.json` ก่อนเลือกหรือแนะนำ lane** (`engine` / `claude_in_chrome` / `dev_bridge` / `auto_login_click`) และแนะนำ**เฉพาะ lane ที่เครื่องนั้นมีจริง**
- **ลำดับ lane:** 1) bsk → 2) Claude in Chrome (ถ้า `claude_in_chrome` เป็น true) → 3) ให้ฉันทำเองที่หน้าจอ · วิธีใช้ละเอียดอยู่ใน skill `browser-engines`
    - cdp.py / Chrome for Testing เลิกใช้แล้ว ห้ามแนะนำหรือสลับไปใช้ แม้เครื่องนั้นยังมีของค้างอยู่ (เหลือแค่เป็นประวัติใน bombot-forge `docs/history/cdp-lane.md`)

| | **bsk** (BrowserSkill · Chrome หลักที่ login อยู่) — ค่าเริ่มต้น | **Claude in Chrome** (MCP · Chrome หลัก) |
|---|---|---|
| ใช้เมื่อ | **อ่านหน้า / QA / screenshot / Dev Bridge** และ record write ผ่าน `ns_write.py` (เฉพาะเครื่อง dev · dry-run ก่อน · บน production ต้องยืนยันรอบนั้น) | งานที่ฉันต้องเห็นต่อหน้า และงานที่ต้องใช้ session Google ของ `<work-email>` (เช่น Google Sheets) |
| ขับด้วย | `bsk` CLI (`session`/`tab`/`navigate`/`evaluate`/`observe`/`screenshot`) — ดู skill `browser-engines` | `mcp__claude-in-chrome__*` (navigate/computer/read_page) |

- **bsk กด accept dialog ให้เองทุกชนิด (alert/confirm/prompt/beforeunload) ปิดไม่ได้** → ทุกครั้งหลัง navigate ติด guard (`window.confirm=()=>false` ฯลฯ) และตรวจ identity gate (`nlapiGetContext().getCompany()` + `getEnvironment()`) ก่อนอ่านต่อ
    - guard ครอบเฉพาะ top window (iframe same-origin ยังถูก accept, popup ค้างรอคน)
- **คลิก/กรอก/submit บน production ทำได้ แต่ต้องยืนยันก่อนทุกรอบ:** list ให้ฉันเห็นว่ารอบนี้จะ process/คลิก/submit/update อะไรบ้าง (หน้าไหน · ปุ่มไหน · record ไหน · ค่าอะไร · ขั้นไหนอาจเด้ง confirm) แล้วรอ OK (ใช้ได้เฉพาะรอบนั้น)
    - ระหว่างทำถ้ามี dialog ที่ไม่อยู่ใน list (ดู `dialogs` ใน result) หรือผลไม่ทราบ → หยุดและรายงาน
    - ขั้นที่น่าจะเด้ง dialog หรืออยู่ใน iframe/popup ให้ใส่ใน list แล้วให้ฉันเลือก: Claude ทำต่อด้วย bsk / Claude in Chrome (ยังไม่เคยยืนยันกับ native dialog = เสี่ยงเท่า bsk) / ฉันกดเอง
    - เขียนค่าใน record ผ่าน `ns_write.py` ต้อง dry-run ก่อนและยืนยันรอบนั้น · ทีละ record · ผลไม่ทราบ (exit 3) = หยุด
- **bsk: มี tab ของตัวเอง + pin + ปิด session ทุกครั้ง** (`bsk session start --no-focus` → `tab list --scope agent` เอา tab ที่ session เปิดให้ (ไม่ต้อง `tab create`) → ใส่ `--tab-id` ทุกคำสั่ง → `bsk session stop`)
    - `observe` ใส่ `--max-tokens` เสมอ
    - **bsk 0.4+:** `evaluate`/`click`/`navigate` ครั้งที่ 2 ขึ้นไป ต้อง `bsk cooperate sync` ก่อนทุกครั้งแล้วส่ง `--context` + `--observation` (ใช้ได้ครั้งเดียว · retry เฉพาะเมื่อ `effect_state: none` · ห้าม `cooperate wait` เอง)
- **บอกฉันทุกครั้งที่ใช้ bsk** — 1 บรรทัดก่อนคำสั่ง `bsk` แรกของงาน: ทำอะไร · บัญชี/หน้าไหน · เป็น Agent Window เบื้องหลัง (ปิดเมื่อเสร็จ) · **เป็นการแจ้ง ไม่ใช่การขออนุมัติ — ส่งแล้วทำต่อ**
- **ห้าม `bsk session stop --all`** — daemon ใช้ร่วมกับ session Claude อื่นของฉัน · ปิดเฉพาะ id ของตัวเอง แล้วเช็กว่า id นั้นหายจาก `bsk session list`

**Auto-login (session หมด → เด้งหน้า login)** — เฉพาะเมื่อ `browser.json` มี `auto_login_click: true`:
1. เช็กว่า Chrome autofill แล้วด้วย `:-webkit-autofill` (boolean) **ห้ามดูจากความยาวค่า** (Chrome ซ่อนค่าจาก script) · ไม่ติด → หยุด ให้ฉันกดเอง
2. ถ้าปุ่ม Login **disable อยู่** → คลิกพื้นหลังนอกกรอบ login 1 ครั้ง
3. กดปุ่ม **Login / เข้าสู่ระบบ** (`bsk click '#login-submit'` หรือ Claude in Chrome)
- 🔑 **ห้ามอ่าน/ดึงค่า field password และห้ามพิมพ์ credential เอง** — แค่คลิก submit; credential เป็นของ Chrome
- 2FA/trusted-device: Chrome เก็บไว้ ~30 วัน มักไม่ถาม TOTP · ถ้าถาม → ฉันกรอกเอง

# Coding agent (delegate edits)
- ระดับการส่งงานแก้ไฟล์ให้ coding agent **ตั้งรายโปรเจกต์** (บล็อก "การส่งงานแก้ไฟล์ให้ coding agent" ใน `CLAUDE.local.md` ของโปรเจกต์ ตั้งด้วย skill `setup-coding-agent`): always / medium / low / on-request · **ไม่มีบล็อก = on-request (ส่งเมื่อผู้ใช้สั่งเท่านั้น)** · เมื่อส่ง → ผ่าน `agent_run.py`; Claude เขียน brief และ review ทุกบรรทัดก่อน apply
- ห้าม delegate: งาน browser, production, deploy, secrets, ข้อมูลลูกค้า (โค้ด/ข้อมูลที่ส่งไปอยู่กับ provider ภายนอก)
- งานหาบั๊ก/แกะโค้ดเดิม: ขั้นหาที่ → ส่งให้ DeepSeek ผ่าน `agent_run.py --profile analyze` (อ่านอย่างเดียว) · ขั้นตรวจผลที่ DeepSeek ส่งกลับ → Claude ตรวจ `file:line` เอง หรือส่ง subagent โดย**ระบุ `model` ทุกครั้ง** (ไม่ระบุ = ใช้ model เดียวกับ session เช่น Opus 5.5): ค้น/ไล่ไฟล์ → `haiku` · ต้องใช้วิจารณญาณ → `sonnet` · Opus เฉพาะขั้นสรุป/ตัดสิน root cause ที่ผู้ใช้ต้องพึ่ง
- ทุกครั้งที่ใช้ `agent_run.py` ต้องปิดด้วย `--log-outcome <run id> --verdict accepted|fixed|rejected` หลัง review — ledger อยู่ที่ `~/.config/bombot-forge/delegations.jsonl` (ตัวเลขล้วน ไม่มีเนื้อหางาน) ดูสรุปด้วย `agent_run.py --log-report`
