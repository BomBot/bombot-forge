---
name: browser-engines
description: >-
  Use when driving a browser or reading live NetSuite data through one: BrowserSkill (`bsk`) in the user's
  everyday logged-in Chrome is the lane for reading pages, QA, screenshots, Dev Bridge reads and (after the round's
  confirmation) UI changes on production; Claude in Chrome is the second lane; the user on the screen is the last.
  Covers the per-run bsk rules verified on a Mac (own session + pinned tab, bsk 0.4 cooperate sync, dialog guard,
  NetSuite identity gate, expired-session login click, bounded observe), how the Dev Bridge works, and a first-run
  walkthrough that `setup-browser` runs at its end. The old cdp lane is recorded in docs/history only.
---

# Browser: bsk + Claude in Chrome (and how the Dev Bridge works)

> Renamed from `cdp-browser` in 0.22.0. The old cdp lane is history, not a lane: `docs/history/cdp-lane.md` in this plugin.

**Skill version: `202611_07`**

This skill is the **per-run rules**. Installing and configuring the browser is `setup-browser` (once per machine).
Command reference for `bsk` comes from the upstream `browser-skill` (installed by `bsk install-skill --harness claude-code`).

## Which lane

**Which lanes exist is per machine.** Read `~/.config/bombot-forge/browser.json` (`engine`, `also_installed`,
`claude_in_chrome`) and only ever suggest a lane that is present there.

1. **`bsk`** — the default for everything: reading a page, smoke/QA, screenshots, Dev Bridge / SuiteQL reads, record
   writes through `ns_write.py` (dry-run, then the round's confirmation), and UI-driven changes on production after the
   round's confirmation (below). It uses the browser you're already logged in to, in a separate background Agent Window.
2. **Claude in Chrome** (`mcp__claude-in-chrome__*`, everyday Chrome, real tabs) — when `bsk` is down, for a step you want
   in a tab the user can see, or for sites that need the main Google session (Sheets, Drive under the work account). Not
   verified against native dialogs: treat it like `bsk` for anything that changes data.
3. **The user acts on the screen** — the last resort, or when the user prefers to click. Say exactly what to click and
   check the result afterwards through a read lane.

cdp (Chrome for Testing + `cdp.py`) is no longer a lane of these skills; how it worked is recorded in
`docs/history/cdp-lane.md`. Don't suggest it or installing it. A machine whose `browser.json` still lists it: offer the
removal in `setup-browser` Step 1.

### Changing data in the UI on production — confirm the round, then go

There is **no ban** on clicking, filling or submitting on production through `bsk` (removed in 0.29.0: a user working on a
production account that is not live yet could do nothing with `bsk`). The protection is the **confirmation of the round**:

1. **List it before you start** — which pages, which buttons, which records, which values, and which step might raise a
   confirm — and wait for the user's OK. The OK covers that round only.
2. Run the usual hygiene: own session, pinned tab, dialog guard after every navigation, identity gate (company and
   environment match what was approved).
3. **Stop** if a dialog shows up that was not in the list (the `dialogs` field of a result must stay empty), or if an
   outcome is unknown. Report; do not click on.
4. The guard is a seat belt, not a barrier (see "Dialog guard — what it does NOT cover": top window only). So a step that
   may raise a confirm, or lives in an iframe or popup, goes into the list as a **flagged step** and the user chooses: carry
   on with `bsk`, use Claude in Chrome (no safer than `bsk` for dialogs), or click that step themselves.
5. `ns_write.py` follows the same rule (no flag since 0.30.0): dry-run first, list the write and get the round's OK, one
   record at a time.

Why bsk and not cdp: ~22x less overhead per command and no second browser to log in to (numbers in `docs/history/cdp-lane.md`);
on real NetSuite pages the page load dominates either way.

## bsk lane

### After a `bsk` update (the daemon updates itself)

**Passive check — run it whenever bsk fails to connect or refuses actions it used to accept** (not on every run):
`BSK_AUTO_START=0 bsk status --json` → read it with Python, not by eye:

- `browsers[].version_skew: true`, or `compatibility.browsers[].features[]` with `available: false` and a
  `blocked_by[].component: "extension"` → the **Chrome extension is behind the CLI**. The CLI and daemon update
  themselves; the extension updates only through Chrome. Tell the user, in plain words, with the versions
  (`cli_version` vs `extension_version`) and bsk's own `recovery` text: open `chrome://extensions`, turn on Developer
  mode, click **Update** (or wait for the Chrome Web Store), then reload the BrowserSkill extension and check it
  reconnects (the Update-button route is standard Chrome, not yet tried for this extension). Re-run `bsk status`. Updating the CLI again does not fix it. Seen 2026-11-17 on this Mac: CLI 0.5.0
  (protocol 1.9), extension 0.4.2 (protocol 1.8), `dom_read` and `unverified_script` blocked; `ns_read.py ping` failed
  with `strict observation changed` after 5 syncs. After the user updated the extension to 0.5.0, skew cleared and
  `ns_read.py` ping + query worked with **no code change** (SB2).
- `daemon_version` differs from `bsk --version` → the daemon is behind. On Windows (0.4.1) the old daemon kept
  running after an update. Ask the user before stopping it (shared by sessions, never kill it yourself; see
  `setup-browser/references/windows-daemon-hidden.md`).
- Empty `browsers` → Chrome is closed or the extension's connection is off (popup toggle, right profile).

The upstream `browser-skill` updates itself with the CLI.

### Every run

0. **Say it.** Tell the user **each time you start using `bsk`** — one line in the chat before the first `bsk` command of the job: what for, which account/page, and that it opens a *background Agent Window* (own session, closed when done). Not for every command inside the same job. It is a **notice, not a question**: do not wait for a reply and do not ask for approval — send it and keep working. (Approvals that DO exist come from elsewhere: a non-sandbox account not yet confirmed, a production write, or Login clicking without consent.) `bsk` always works inside an **Agent Window** (a separate window that only the
   session owns): `tab create` makes tabs *in that window* and there is no `bsk` mode that opens a tab in
   the user's everyday window. `--no-focus` / `--no-active` (below) keep it from stealing focus — that is the
   least intrusive `bsk` can be. If the user must SEE the page or log in, use a real tab instead (step 5).
1. **Own session, always stopped:** `bsk session start --no-focus --name <job> --json` → `session_id`.
   `bsk session stop <id>` at the end **even on failure**. **Never `bsk session stop --all`, and never expect `session_count` to be 0.** The daemon is shared: another Claude session of the same person may be using `bsk` right now, and `--all` would kill its run (this happened once). Stop only YOUR id; confirm with `bsk session list` that your id is gone and leave every other session alone.
2. **Own tab, pinned - the one `session start` already opened:** the new Agent Window starts with exactly one
   `about:blank` tab (measured on this Mac, bsk 0.3.3), so do **not** `tab create` (that adds a second tab). Read its
   id: `bsk tab list --session <id> --scope agent --json` -> the single `tab_id`; pass `--tab-id` on every command
   and `navigate` that tab. (`--scope agent` lists only your own window, not the user's tabs.) If the list does not
   show exactly one tab, fall back to `bsk tab create --no-active --url about:blank --session <id> --json`. Without it a command follows the active tab, which a
   peer can move. One command per session at a time (a second is refused with `session_busy`).
2b. **bsk 0.4+: `cooperate sync` before every page action** (measured on bsk 0.4.2, 2026-11-06; the daemon updates
   itself, so a machine set up on 0.3.x can be on 0.4 without anyone noticing - check `bsk --version`):
   - `evaluate` (and `click`, and every `navigate` after the first) is refused with `permission_denied` /
     `cooperation_sync_required` until you run `bsk cooperate sync --session <id> --tab-id <tab> --json` and pass
     **both** `--context <context_id>` and `--observation <observation_id>` from that reply. Use the **top-level**
     `observation_id`, not `observation.observation_id` (a different id). Missing either -> `observation_required` /
     `control_context_invalid`.
   - An observation works **once**: sync again before the next action (a reused one -> `observation_required`). The
     context stays valid while the page does not change. NetSuite pages re-render between the sync and the action
     (`observation_changed`, seen live on a sandbox), so allow a few sync-and-retry rounds.
   - **A page that never stops changing** (a dashboard portlet counting down "Auto refresh in 58s") cannot be won by
     re-syncing (bsk 0.5.0, issue #1). For a **read** script use `--context <context_id> --unverified` with no
     `--observation` (offered when `bsk status --json` lists `unverified_script` as available), and make the script
     check its own preconditions (host, company) and throw before it does anything. The reply carries
     `verified: false`, which is expected. Do not use it for a write: navigate to a page that does not change instead.
   - Not needed: the **first** `navigate` from `about:blank` (and `sync` fails there with `frame_unobservable`, so
     navigate first), `screenshot`, `observe`, `tab list`, `session start/stop`.
   - Retry a refused action only when the reply says `data.effect_state: "none"` (nothing ran). Never call
     `cooperate wait` and never act when the sync reply's `state` shows `editing: true` or a `mode` other than
     `ready`: someone else is driving that tab - stop and tell the user.
   - Parse the JSON from a file or with Python. Piping it through zsh `echo` turns the `\n` inside strings into real
     line breaks and the ids come out empty (this cost a test run).
   - `ns_read.py` / `ns_write.py` do all of this themselves (try, sync on a sync refusal, retry); this is for raw `bsk`.
3. **Dialog guard after every navigation** (the page changes, the guard is gone; on bsk 0.4+ add the sync flags, step 2b):
   ```bash
   bsk evaluate "window.alert=function(){};window.confirm=function(){return false};window.prompt=function(){return null};window.onbeforeunload=null" --session <id> --tab-id <tab>
   ```
   Verified on macOS: without it `confirm()` returned `true` and the result listed
   `handled: "accepted"`; with it `confirm()` returned `false` and no dialog was reported. Assert
   the `dialogs` field of every result stays empty.
4. **NetSuite identity gate before reading anything past the login page:**
   ```js
   JSON.stringify({co:nlapiGetContext().getCompany(), env:nlapiGetContext().getEnvironment()})
   ```
   Must match the account you mean and (for anything beyond reads) `SANDBOX`. A login page has no
   `nlapiGetContext`, so the gate also catches an expired session. Fetching `/app/...` from
   `about:blank` fails — open a classic NetSuite page first.
5. **Expired session (redirected to the login page):** **Judge "did Chrome fill the form?" by `:-webkit-autofill` (a boolean) — NEVER by the value length.** Chrome hides an
   autofilled value from page scripts until the user interacts with the page. Measured on this Mac (Chrome 152,
   bsk 0.3.1): on the NetSuite login page, a `bsk` Agent Window (background *and* focused) and a hidden Claude in
   Chrome tab all had both fields matching `:-webkit-autofill` while the email `value.length` was **0**. The one
   time it read 20 was in a tab the user had just clicked — consistent with the rule, not proven. So "the email looks empty" from `value.length` says nothing, and an agent that stopped on it was
   stopping for no reason. (An earlier version of this skill said the Agent Window "does not get autofill"; that
   was wrong — it came from reading the length only.)
   Then, with the user's consent (`auto_login_click`) and the flag on: if the Login button is disabled, click the page
   background outside the white login panel (right side of the screen) once so `blur` enables it; click `#login-submit`
   once (on 0.4+ after a fresh sync, step 2b; never read or type a credential; stop on an MFA prompt or any page change)
   and check that the URL left the login page. Both clicks must be real `bsk click`s: on 2026-11-18 a JS
   `element.click()` from `evaluate` on the disabled button left the page on `enterpriselogin.nl`, and the selector
   `body` aims at the middle of the page, which is the login panel, not the background. A refusal "User activity
   revoked this action" means the user is in that Chrome: stop, do not retry. **Tested (2026-09-30, SB2):** a `bsk`
   click on `#login-submit` with both fields `:-webkit-autofill` (values hidden, length 0) submitted them and landed on
   the Home page (`SANDBOX`, no MFA). Repeated after the user logged out (a real expired session): `ns_read.py` stopped at the login page without logging in, then the same click landed on Home again. If it does not leave the login page, or there is no consent,
   hand off to a **real tab** (the user's own Chrome, where they can see it and press Login):
   - Open it for them: on macOS `open -a "Google Chrome" "<login url>"` **verified**: it opens a new *tab* in the
     already-open Chrome window (`bsk tab list --scope user` then showed it in a user window). Tell the user which
     tab it is, wait for the URL to leave the login page, then re-run the read. You cannot close that tab yourself.
   - **Claude in Chrome** (connected on this Mac; skill `setup-browser`) works in normal tabs: it puts its tabs in a
     Chrome **tab group** — the first use with no group creates one new window holding it (verified), later tabs
     join the group. Its `javascript_tool` can read the same `:-webkit-autofill` flag (verified) and run `fetch`.
   - Do not use `bsk tab borrow`: its confirmation prompt shows for about a second, so a person cannot click it in time
     (one attempt timed out, one worked only with a countdown). The two hand-offs above need no confirmation.
   A login counts in the account's "My login audit".
6. **Read cheaply.** `bsk observe` on a one-paragraph page returned 18.6 KB (one node per
   character) — always cap it: `bsk observe --max-tokens 600 …` gave 2.6 KB on the NetSuite Home
   page. Prefer `evaluate` for targeted reads (titles, counts, one value); save screenshots to a
   file (`--out`), don't return image bytes. `evaluate` awaits promises, so a `fetch(...).then(…)`
   returns in one call.
7. **Console:** filter out `chrome-extension://` entries — another extension's messages were half
   of the log; judge only the page's own.
8. **Faster navigation:** `bsk navigate <url> --wait-until domcontentloaded`, then wait for the
   element you need (Home: 8.9 s vs 14–19 s for the default `load`).

### Dialog guard — what it does NOT cover (tested on a Mac against a sandbox, 2026-09-30)

A page-level guard (`window.confirm=()=>false` …) is **not** a safety barrier. Measured on a
sandbox NetSuite page:

| Case | Result |
|---|---|
| no guard, top window `confirm()` | accepted by `bsk`, page got `true`; reported in `dialogs` |
| guard installed, top window `confirm()` | returns `false`, no dialog — guard works |
| guard installed, **same-origin iframe** `confirm()` | **accepted (`true`)** — the iframe is a new window, the guard is not in it |
| guard installed, **popup** (`window.open`) `confirm()` | **not auto-accepted**: the dialog stayed on screen for a human and the `evaluate` hung until the 120 s timeout; `bsk session stop` then failed with "cleanup timed out" until the dialog was dismissed |
| guard, then navigate | guard gone (the new page's `confirm` is the page's own) |
| page re-arms `onbeforeunload`, then navigate | no dialog reported — **inconclusive** (Chrome only shows it after a user gesture, which this test had none of) |

What follows: the guard must be reinstalled after **every** navigation and does not reach iframes
or popups, so the guard is a seat belt and not a barrier: on production the round's confirmation must list every click,
and any dialog outside that list ends the run. `ns_write.py` is not affected (it calls `N/record`, clicks nothing). If a hung dialog blocks the session, dismiss it by
hand, then `bsk session stop <id>` again (your id only) and confirm it is gone from `bsk session list`.

### Concurrency soak (2026-09-30, one Mac, read-only, sandbox)

3 bsk sessions in parallel, each with its own pinned tab, 30 minutes, one cycle every ~20 s per
session (navigate → guard → identity gate → per-session marker check): **273 cycles, 0 failures,
0 cross-talk between tabs, 0 stray dialogs**; navigate p50 0.93 s / max 1.82 s, evaluate p50 0.19 s /
max 1.71 s; the session was gone from `bsk session list` after `session stop` (on a machine with no other sessions the count was back to 0). Not covered: more than 3 sessions,
sessions longer than 30 minutes, writes during contention, other OSes.

### Known limits (Teibto's tests, mostly Windows — recheck on this Mac before relying)

- `fill` fails or is silently dropped on `<input type=date>`, React-controlled inputs and Quill
  editors; values starting with `-` need `--value=<v>`. Details: `Teibto/teibto-browser-qa`,
  `references/engine2-bsk.md` §4.
- Screenshot of a **background** tab is documented to fail; on macOS/0.3.1 it succeeded (not
  investigated — may be because it was the window's only tab).
- Closing the Agent Window mid-run kills the run — including after a Save. Tell the owner first.
- Everything above was measured with a person's real Chrome: an Agent Window shares its logins and is
  **not** a sandbox. Chrome autofills forms there too, but hides the filled value from scripts (see step 5).

## How the Dev Bridge works

**What it is.** A Suitelet (`Teibto/TEIBTO-Dev-Bridge`, private repo; its README is the action reference) deployed in the
NetSuite account. It answers JSON for read-only actions, so Claude checks the real state of records, GL, fields and
script deployments instead of guessing. Recipes and SuiteQL gotchas: `ns-live-verify`.

**How a call travels.**

1. A `bsk` session opens a classic NetSuite page in the user's Chrome profile (the Agent Window shares the user's login).
2. Dialog guard + identity gate (company and environment are the account the user meant).
3. `fetch` from inside that page: `POST /app/site/hosting/scriptlet.nl?script=<script id>&deploy=<deploy id>` with a JSON
   body `{"action": "...", ...}`. The **session cookie** authenticates it — no token, no "Available Without Login".
4. The Suitelet runs the action as the logged-in user and replies `{ok:true, action, ...}` or `{ok:false, error, code}`.
   Every call lands in the script's Execution Log (who + what).
5. `bsk session stop <your id>`.

**Who and what.** Any role (bridge `2026.10.30-001`+): it runs as the caller's role, so results follow that role's
permissions; every reply carries `asRole`, and a NetSuite refusal comes back `ok:false` with `nsCode` (e.g.
`INSUFFICIENT_PERMISSION`). An older deployment is Administrator-only (`FORBIDDEN`). Actions: `ping` (account, envType,
user, role), `help`, `query` (SELECT-only SuiteQL: must start with `SELECT`, no `WITH`, no `;`, no DML words even inside
strings; first 5,000 rows, `capped` means more), `queryPage` (1,000 a page, up to 10 pages a call, `totalCount`),
`count` (total rows of a query or search, no data), `record` (full JSON with sublists, or chosen fields / sublists),
`lookup`, `feature`, `search` (paged, `totalCount`). Nothing writes. To see what another role can read, switch role in
NetSuite (it changes every tab of that account in that Chrome profile — tell the user, switch back after); recipe in the
Dev Bridge repo `docs/dev-notes/dev-bridge-suiteql-verification.md` → *Testing as another role*.

**Where the address comes from.** Default ids `customscript_teibto_dev_bridge` / `customdeploy_teibto_dev_bridge`;
another account may use other ids, saved per account in `browser.json` → `dev_bridge.endpoints["<account>"].path`. The
host and account come from the Home page URL the user pasted in `setup-browser` (`dev_bridge.host` / `account`).
Never commit an account id.

**How Claude calls it — prefer the helper.** `python3 <plugin>/skills/ns-live-verify/scripts/ns_read.py
<whoami|ping|query|query-page|count|record|lookup|feature|search> --account <ACCOUNT> ...` opens and stops its own bsk session, does the
identity gate, pings the bridge before the real request, handles bsk 0.4 cooperate sync, and validates every argument.
Exit codes: `0` ok, `1` bridge said `ok:false`, `2` refused by a guard, `3` session/login/transport (it never logs in).
Raw `bsk evaluate "fetch(...)"` is for when the helper cannot do it (recipe: `ns-live-verify` Option A).

**When it fails.** An HTML "Notice / connection timed out" or login page instead of JSON = the session expired, not a
query error: step 5 below, then retry. `ok:false` with a SuiteQL error = fix the query (`ns-live-verify` gotchas). Not
deployed in that account = say so and stop; deploying it is a separate decision.

## First run — walkthrough (`setup-browser` runs this at its end)

Show the user how a real run looks, read-only, narrating each step in one plain line. Use the account from
`browser.json` (`dev_bridge.account`/`host`); no account there → ask for the Home page URL, or do steps 1–4 only.

1. The notice (Every run step 0), then `bsk session start --no-focus --name walkthrough --json` and the one tab it opened.
   *"เปิด Agent Window เบื้องหลังของ Claude เอง ไม่ยุ่งกับ tab ที่คุณเปิดอยู่"*
2. `navigate` to the Home page (`--wait-until domcontentloaded`). Login page → step 5 (consent from `browser.json`).
3. Dialog guard, then the identity gate. *"กันไม่ให้ popup ยืนยันโดนกดเอง และเช็คว่าอยู่ถูกบัญชี"*
4. `bsk observe --max-tokens 600` or a screenshot to a file: show what Claude "sees".
5. Dev Bridge (if enabled): `ns_read.py ping` then `ns_read.py query --account <ACCOUNT> "SELECT COUNT(*) AS n FROM script"`.
   *"อ่านข้อมูลจริงผ่าน Dev Bridge แบบอ่านอย่างเดียว"*
6. `bsk session stop <id>` and confirm your id is gone from `bsk session list`.
7. Close with three things to remember: Claude tells you each time it opens bsk; on production every click/submit is
   listed for your OK first; and how to ask (e.g. *"ใช้ bsk เปิด <ลิงก์> แล้วบอกค่า field X"*, *"ใช้ Dev Bridge เช็คว่า
   script นี้ deploy อยู่ไหม"*).

## Claude in Chrome

`mcp__claude-in-chrome__*` drives the main Chrome in real tabs (its own tab group). Use it for sites that need the main
Google session (Sheets, Drive under the work account), as the second lane when `bsk` is down, or for a step the user wants
to watch. Its `javascript_tool` can read `:-webkit-autofill` and run `fetch` (verified). Not verified against native
dialogs: confirm the round like `bsk` before changing data.

## Quick reference (bsk)

| Need | Command |
|---|---|
| Session / tab | `bsk session start --no-focus --json` · `bsk tab list --session <id> --scope agent --json` (use the one tab it opened; `tab create` only as fallback) |
| Navigate | `bsk navigate <url> --wait-until domcontentloaded …` |
| Run JS | `bsk evaluate "<js>" …` (awaits promises; 0.4+: after a fresh `cooperate sync`, step 2b) |
| Bounded page view | `bsk observe --max-tokens 600 …` |
| Screenshot | `bsk screenshot --out f.png …` |
| Dev Bridge read | `ns_read.py <action> --account <ACCOUNT> …` |
| Cleanup | `bsk session stop <id>` (your id only) · `bsk session list` |

## Status

v0.3 — bsk lane verified 2026-09-29 on one Apple Silicon Mac against a NetSuite sandbox (login, identity gate, Home read,
dialog behaviour, `evaluate`+`fetch`), bsk 0.4.2 cooperate sync 2026-11-06. Dev Bridge flow as implemented by
`ns_read.py` (verified live on a sandbox; see `ns-live-verify`). The first-run walkthrough is new in 202611_03 and not yet
run end to end. Not yet pressure-tested per `superpowers:writing-skills`.
