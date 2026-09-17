> **Redacted reference snapshot** of BomBot's global `~/.claude/CLAUDE.md`, kept for the
> `setup-global-instructions` skill. Customer/personal identifiers are replaced with
> placeholders — fill them from your own values on each machine, never invent:
> `<Your Name>` · `<work-email>` · `<personal-gmail>` · `<PROJECT>` (a customer project folder)
> · `<qa-project>` (the repo that holds the canonical `cdp.py`).
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

# Communication style
- ตอบสั้น กระชับ ตรงประเด็น ไม่เกริ่นนำ ไม่มีอารัมภบท
- ไม่ต้องมีคำขึ้นต้นเชิงมารยาท เช่น "Great question", "I'd be happy to help"
- ไม่สรุปซ้ำสิ่งที่เพิ่งทำตอนจบ เว้นแต่มีประเด็นสำคัญ
- พูดคุยทั่วไปตอบเป็นภาษาไทยได้เลย

# Slack / การสื่อสารกับทีม
- ห้ามโพสต์/ตอบ Slack thread แทนฉันทันที — ร่างมาให้ฉัน review ก่อนเสมอ รอฉันเคาะค่อยโพสต์
  (แม้ฉันเคยบอก "ตอบเลย" ในรอบก่อน รอบถัดไปก็ยังต้องร่างให้ดูก่อนทุกครั้ง)
- **ข้อความที่จะส่งออกนอกระบบ (Slack, email, ฯลฯ) draft ต้องมาโผล่ในแชทนี้ให้ฉันเห็นเป็น text โดยตรง**
  ห้ามใช้ tool ที่ไปสร้าง draft ค้างไว้ในระบบปลายทางแทน (เช่น draft ฝั่ง Slack เอง) เพราะต้องให้ฉันเปิดแอปอื่นไปดู/กดส่งเอง
  — พิมพ์ draft ในแชท รอฉัน confirm แล้วค่อยเรียก tool ส่งจริง
- เสนอด้วยว่าคำถาม/ประเด็นไหนควรให้ "ฉัน" เป็นคนตอบเอง (ให้ทีมเห็นว่าฉันคิดเอง ไม่ใช่ให้ AI ทำทั้งหมด)
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



# graphify
- **graphify** (`~/.claude/skills/graphify/SKILL.md`) - any input to knowledge graph. Trigger: `/graphify`
When the user types `/graphify`, invoke the Skill tool with `skill: "graphify"` before doing anything else.

# Claude Code: ย้าย project folder แล้ว session resume ไม่ได้

อาการ: `Working directory no longer exists: <old path>` ตอนเปิด session ใน Claude Mac app / CLI หลังย้ายโฟลเดอร์ project

Claude Code เก็บ session ที่อิง `cwd` ใน **2 ที่** ต้องแก้ทั้งคู่:

## 1) `~/.claude/projects/<encoded-path>/` (CLI session storage)
- ชื่อโฟลเดอร์ encode จาก path จริง: `/`, `@`, `_`, space, `.` → `-`
  - เช่น `/Users/bombot/WebstormProjects/<PROJECT>` → `-Users-bombot-WebstormProjects-<PROJECT>`
- ต้องแก้ทุกไฟล์ `.jsonl` ใต้โฟลเดอร์ (รวม `<sessionId>/subagents/agent-*.jsonl` และ `tool-results/*.txt`) ที่มี `"cwd":"<old>"`

## 2) `~/Library/Application Support/Claude/` (Mac desktop app)
- `claude-code-sessions/<workspaceUUID>/<projectUUID>/local_*.json` — มี `"cwd"` และ `"originCwd"`
- `local-agent-mode-sessions/...` — โครงสร้างเดียวกัน
- `claude_desktop_config.json` — MCP server `cwd` paths

## ขั้นตอนแก้

1. Backup ก่อน:
   - `tar -czf backup.tar.gz ./<old-encoded-folder>` (ใส่ `./` หน้าชื่อที่ขึ้นต้นด้วย `-` เพื่อกัน tar แปลความเป็น flag)
2. **Replace แบบ per-project** ในไฟล์ทั้งสองที่ — อย่า replace prefix แบบเหมารวม เพราะถ้ามี project อื่นในโฟลเดอร์เก่าที่ **ไม่ได้ย้าย** (เช่น MCP config ชี้ project บน Drive อยู่) จะพังของพวกนั้น
3. Rename โฟลเดอร์ใน `~/.claude/projects/` เป็น encoded path ใหม่
4. **Quit Claude Mac app ด้วย Cmd+Q แล้วเปิดใหม่** (app cache session list ไว้ใน memory)

## ไม่ต้องแก้ (เก็บ runtime state ไม่ผูก path)
- `~/.claude/sessions/` (pid file), `~/.claude/session-env/`, `~/.claude/shell-snapshots/`, `~/.claude/tasks/`, `~/.claude/plans/`, `~/.claude/todos/`

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

# Browser automation (2 ทาง: cdp.py + Claude in Chrome)

**เลือก browser ให้ถูก:**
| | Chrome for Testing (cdp.py, port 9333) | Claude in Chrome (MCP, Chrome หลัก) |
|---|---|---|
| ใช้เมื่อ | QA/verify NetSuite, automation, screenshot, ขับ shadow DOM, login หลาย account | งานที่ต้องใช้ session Google/Chrome หลัก (เช่น Google Sheets, login `<work-email>`) |
| ขับด้วย | `cdp.py` (eval/click/shot) | `mcp__claude-in-chrome__*` (navigate/computer/read_page) — ระบุ Browser 1/2 |
- ❌ อย่าใช้ 9333 (`<personal-gmail>`) เข้า Google Sheets ของ `<work-email>` = Access denied → ใช้ claude-in-chrome Browser 2

**Auto-login (session หมด → เด้งหน้า login)** — Chrome ตั้ง autofill email/password ไว้แล้ว:
1. ถ้าปุ่ม Login/เข้าสู่ระบบ **disable อยู่** → คลิกพื้นหลังนอกกรอบ login 1 ครั้ง (trigger blur → ปุ่ม enable)
2. กดปุ่ม **Login / เข้าสู่ระบบ** (ได้ทั้ง cdp.py click และ claude-in-chrome)
- 🔑 **ห้ามอ่าน/ดึงค่า field password** — แค่คลิก submit; credential เป็นของ Chrome ไม่ใช่ของ Claude
- field ไม่ถูก autofill (ว่าง) → หยุด ถามก่อน **ห้ามพิมพ์ credential เอง**
- 2FA/trusted-device: profile เก็บ token ~30 วัน มักไม่ถาม TOTP

---

**Chrome for Testing (cdp.py) — รายละเอียด:**
มี **Google Chrome for Testing** ลงไว้แล้ว (ติดตั้ง 18/08/2026) แยกขาดจาก Chrome ตัวหลัก
ตัวหลัก update ปกติ ตัวนี้ไม่ auto-update จึงไม่พังเองกลางทาง

```
~/Applications/Google Chrome for Testing.app     # binary
~/.qa-chrome/<งาน>                                # profile (session ค้างอยู่ ไม่ต้อง login ซ้ำ)
CDP port 9333
```

เปิด

```bash
~/Applications/"Google Chrome for Testing.app"/Contents/MacOS/"Google Chrome for Testing" \
  --user-data-dir="$HOME/.qa-chrome/<งาน>" --remote-debugging-port=9333 \
  --no-first-run --no-default-browser-check --disable-session-crashed-bubble about:blank
```

ขับด้วย `cdp.py` (ต้นฉบับ `~/WebstormProjects/<qa-project>/scripts/qa/cdp.py` · ดู skill `netsuite-qa-browser`)

```bash
export CDP_PORT=9333
python3 cdp.py tabs | url | nav <url> [wait] | eval "<js>" | evalf <file.js>
python3 cdp.py a11y [คำค้น]          # ได้ ref @NNNN ที่ใช้กับ click ได้ — เจาะ shadow DOM ให้
python3 cdp.py click <sel|@ref>       # คลิกจริงด้วย Input event
python3 cdp.py shot <out.png> [sel] [--dsf=N] [--vw=W] [--vh=H]
```

**capture หน้าจอ** — ใช้ `cdp.py shot` เท่านั้น
`Page.captureScreenshot` สั่งให้ Chrome **เรนเดอร์หน้าเว็บ** ออกมาเป็น PNG ไม่ใช่ถ่ายหน้าจอ
⇒ หน้าต่างอื่นทับ หรือ Chrome ไม่ได้อยู่บนสุด ก็ได้ภาพถูกต้อง (ต่างจาก `screencapture` ของ macOS ที่ภาพจะโดนทับ)
เขียนไฟล์ลงดิสก์ได้จริง จึงเอาไปฝังใน HTML/รายงานได้ — ต่างจาก screenshot ของ extension ที่ได้แค่ภาพในแชต

กับดักที่เจ็บมาแล้ว
- `--vw/--vh/--dsf` **ต้องส่งตอน `shot`** สั่ง `viewport` แยกคำสั่งไม่มีผล (Emulation override ตายพร้อม websocket)
- `shot <sel>` ใช้ `document.querySelector` **เจาะ shadow DOM ไม่ได้** — แอปที่เป็น web component ให้ถ่ายทั้ง viewport แล้ว crop ทีหลัง
- crop เฉพาะ element จะ**ตก popup/dropdown** เพราะอยู่คนละ layer
- แท็บที่ไม่ได้อยู่หน้าสุด **ใน Chrome** จะไม่ถูกวาด (`shot` เรียก `Page.bringToFront` ให้เองแล้ว)

**แอปที่เป็น web component (shadow DOM ซ้อนหลายชั้น)** เช่น MFG Handheld / Release 2.0
`document.querySelector` จากภายนอกหาไม่เจอ ⇒ ใช้ `cdp.py a11y` เอา `@ref` แล้ว `click` หรือเขียน
helper เดินทะลุ `shadowRoot` เอง · **synthetic event (`el.click()` / `dispatchEvent`) บางแอปไม่รับ**
ต้องยิง `Input.dispatchMouseEvent` ที่พิกัดจริง (import `cdp` แล้วใช้ `cdp.C()` — มันตั้ง `suppress_origin=True`
ให้แล้ว ถ้าต่อ websocket เองจะโดน 403 origin check)

⚠️ Chrome 136+ **เมิน `--remote-debugging-port` ถ้าใช้ default profile** ⇒ ต้องมี `--user-data-dir` เสมอ
