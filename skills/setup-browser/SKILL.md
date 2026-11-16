---
name: setup-browser
description: >-
  Use when setting up browser automation on a machine for the first time or changing it: install bsk
  (BrowserSkill, drives your everyday logged-in Chrome), optionally connect Claude in Chrome, offer to
  remove an old cdp (Chrome for Testing) setup if one is found, then a read-only Dev Bridge trial and
  whether Claude may click the NetSuite Login button for you. Interactive — asks before each step;
  saves the choices to a per-machine prefs file.
---

# Setup Browser (bsk, Claude in Chrome, Dev Bridge, login consent)

**Skill version: `202611_03`**

Run once per machine (and again to change a choice). It asks, installs what you pick, tests it,
and writes the answers to `~/.config/bombot-forge/browser.json` — a local file with **no
secrets**, never in a repo. Other skills (`browser-engines`, `ns-record-write`, `ns-live-verify`) read
it. Ask **one step at a time** and wait for the answer; never install or click ahead of an OK. Every
decision follows *How to ask the user* below.

## How to ask the user (at every decision point in this skill)

A choice is never buried in a paragraph. Do these, in this order:

1. **Bullets first.** One block per option, at most three short lines each: **Pros · Cons · Best when**.
   No paragraphs, no "it depends" prose. Say which option you recommend and why in one line.
2. **Then a picker — the last thing in your message.** Use the `AskUserQuestion` tool: a short label, a
   one-line description that carries the key trade-off, the recommended option first and marked
   "(Recommended)". At most 4 options per question, one decision per question, at most 4 questions per
   call (split further decisions into the next round). Use multi-select only when the choices are not
   exclusive. The user can always type their own answer via "Other".
3. **No picker available?** (the tool is not offered, or the run is unattended) Ask the same thing as a
   numbered list in chat, and wait. Never pick for the user and never treat silence as consent.
4. Don't ask what Step 0 already showed, and don't re-ask something already answered.

## Iron rules

- **Never read, extract, or type a password.** The login helper only clicks a submit button;
  Chrome's own autofill fills the fields. Not autofilled (`:-webkit-autofill` not set — never judge by the value length), MFA, or a changed page → stop and ask.
- **Say it every time you use `bsk`** (one line before the first `bsk` command of a job: what for, which account/page, a background Agent Window that is closed when done). A notice, not a question: don't wait for a reply.
- **Ask before installing anything** and before running a downloaded script — read it first.
- **Don't guess.** If a step's outcome can't be verified (extension connected, Dev Bridge script
  id), say so and ask; never invent an id, URL, or version.
- **No real account/script ids in this repo.** Whatever the user gives you goes only into the local
  prefs file.
- Installing the browser extensions and turning them on is the **user's** click — an agent can't.

## Step 0 — look before asking (read-only)

Detect the OS first (`uname -s`; on Windows `$env:OS` / `[System.Environment]::OSVersion` in PowerShell) and use
that OS's commands from here on. Then check what already exists: `bsk` on the PATH (`command -v bsk` / PowerShell
`Get-Command bsk -ErrorAction SilentlyContinue`), `BSK_AUTO_START=0 bsk status --json`, an existing
`~/.config/bombot-forge/browser.json`, whether the `mcp__claude-in-chrome__*` tools are available, and **leftovers of the
old cdp lane**: `~/Applications/"Google Chrome for Testing.app"` (macOS), `~/.qa-chrome/`, `cdp.py` copies under the user's
projects (`scripts/qa/cdp.py`), `engine: "cdp"` or `"cdp"` in `also_installed` in `browser.json`. Report it in two lines and
skip any step that is already done and working. **If `browser.json` exists this is an UPDATE run** — see
*Re-running: update, don't overwrite* below; never treat the machine as blank.

## Step 1 — explain bsk (and the old cdp lane, if found)

This plugin's browser lane is **bsk** (BrowserSkill). cdp (Chrome for Testing + `cdp.py`) is no longer set up on new
machines: bsk drives the Chrome the user already works in, is ~22× faster per command (measured), and needs no second
profile to log in to. Tell the user, in plain words, **what it is for**:

- Claude reads a NetSuite page you point at (a record, a saved search result, a script deployment) without you copying
  screens into the chat.
- QA after a change: open the page, check a value, take a screenshot (`capture-artifact` builds before/after packs).
- The Dev Bridge (step 4) runs through it: read-only SuiteQL / record reads from your logged-in tab.
- It runs in a separate background **Agent Window** that is closed when done; it cannot use the tabs you have open.
- One caution to say out loud: bsk **auto-accepts every browser dialog** (cannot be turned off), so on production
  Claude lists every click/submit and waits for your OK for that round.

**cdp found (Step 0)?** Recommend removing it, and ask (picker: **Remove it (Recommended)** / **Keep it for now**):

- Remove: list exactly what will go (Chrome for Testing app, each `~/.qa-chrome/<name>` profile, each `cdp.py` copy) and
  that `ns_write.py --engine cdp` and the cdp lane of `browser-engines` stop working on this machine. Move to the
  Trash (macOS `~/.Trash`, Windows Recycle Bin), never `rm`. Quit Chrome for Testing first. A `cdp.py` that is tracked
  in a project's git is **not** deleted here — tell the user which project and leave it to them.
- Keep: record it in `also_installed` as today; nothing else changes.

Record `engine: "bsk"`. Never set `engine: "cdp"` on a new machine; an existing `"cdp"` value changes only if the user
agrees.

## Step 2 — install bsk

1. Read upstream `install.sh` (`Tencent/BrowserSkill`; macOS/Linux → `~/.local/bin`), show the user
   what it does, run it on OK. Windows: follow upstream `AGENT_INSTALL.md`; don't improvise.
2. **Open the extension page for the user**: `open "https://chromewebstore.google.com/detail/browserskill/hhcmgoofomhgciiibhipgmgkgnoenaoi"`
   (macOS; use the platform's opener elsewhere). Tell them: *Add to Chrome, then open the
   extension popup and turn the connection on.*
3. `bsk daemon start`, then `bsk doctor` (redirect to a file rather than piping) → expect all `ok`.
4. `bsk install-skill --harness claude-code`.
5. Verify: `BSK_AUTO_START=0 bsk status --json` lists a connected browser; open a throwaway session
   (`bsk session start --no-focus`, use the one `about:blank` tab it opens, `bsk session stop`) and confirm
   your session id is gone from `bsk session list` — stop only your own id, never `--all`, and do not expect the count to be 0 (another Claude session may be using the same daemon). Details and per-run rules: skill `browser-engines`.

## Step 3 — Claude in Chrome (optional)

Say it is **optional** and that it is the second-priority lane (after bsk) — useful when bsk is down, for a
step that will raise a native dialog you want handled in a real tab, or for sites that need your main Chrome/Google
session (Google Sheets, Drive). Ask (picker: **I'll install it myself** /
**Walk me through it** / **Skip — it's optional**): *install it yourself from the link, or want me to walk you
through?* Link:
`https://chromewebstore.google.com/detail/claude/fcoeoabgfenejglbffodgkkbkcdhcgfn`.
After they install, test it: load the tools (`ToolSearch` → `select:mcp__claude-in-chrome__tabs_context_mcp`)
and call `tabs_context_mcp`. Record `claude_in_chrome: true|false|declined`.

Lane priority to state at the end (name only the lanes this machine actually has; never mention cdp on a machine
without it): **1. bsk · 2. Claude in Chrome · 3. you act on the screen** (the last resort, or when you prefer to click).

## Step 4 — offer a Dev Bridge trial

Explain in plain words:

- **What it is:** a read-only Suitelet (`Teibto/TEIBTO-Dev-Bridge`) deployed in the NetSuite account. Claude calls it
  through the logged-in bsk tab: SELECT-only SuiteQL, a record as JSON, field lookups, feature checks, searches.
  Nothing is written. **Administrator role only.**
- **When it helps:** "is this script deployment active?", "what is in this field on SO 1234?", "which transactions
  post to this account?", converting a Saved Search to SuiteQL and proving the rows match, checking the real state
  before and after a change instead of guessing.
- **Needs:** bsk working (step 2) and the user logged in to that account in the same Chrome profile.

Ask with a picker (**Try it now** / **Later** / **Skip**). Skip this step without asking when step 2 did not pass.

If yes:
1. **Now (not earlier) ask for the Home page URL.** Tell the user exactly: *in your everyday Chrome, log in to the
   account you work in, click the NetSuite logo / Home, then copy the whole address bar and paste it here.* It looks
   like `https://<ACCOUNT>.app.netsuite.com/app/center/card.nl?sc=-29...` (a sandbox has `-sb1` / `-sb2` in the host).
   Why it is needed: the host and account id come from it, and bsk cannot see the user's own tabs to read it.
   Derive host and account from the URL (`<ACCOUNT>` / `<ACCOUNT>_SB2` style); don't guess. More than one account →
   one now, the rest by re-running this step later.
2. The bridge is addressed by a script id + deploy id. The repo's README recommends
   `customscript_teibto_dev_bridge` / `customdeploy_teibto_dev_bridge`, and `ns_read.py` tries those. If the
   account uses other ids, ask the user for them (from the script record). If the bridge isn't deployed in
   that account, say so and stop — deploying it is a separate decision.
3. Test it: `python3 <plugin>/skills/ns-live-verify/scripts/ns_read.py ping --account <ACCOUNT>` (on Windows `python`
   or `py` if `python3` is missing). Confirm `account` and `envType` match what they expect and `user.isAdmin` is true.
   Then one `query` with `SELECT COUNT(*) AS n FROM script` to show a real read. Non-sandbox accounts are read
   read-only with a NOTE; name the account in what you tell the user. (Only the delegated agent is gated, see
   `setup-coding-agent`.)
4. Save under `dev_bridge` in the prefs file (`enabled`, `host`, `account`; and, only when the ids are not
   the defaults, `endpoints["<account>"] = {"path": "/app/site/hosting/scriptlet.nl?script=<id>&deploy=<id>"}`).

## Step 5 — Login helper consent

Ask with a picker (**Yes, click Login for me** / **No, ask me each time**): *If a NetSuite page falls back to
the login screen, may I click **Login / เข้าสู่ระบบ** for you?* State plainly: **I will never read your password field.** It works only if Chrome is set to
autofill the email + password on its own, without asking you to type or unlock anything at fill
time. Record `auto_login_click: true|false`.

**Reading the form.** Check whether Chrome filled it with `:-webkit-autofill` (a boolean on the email field), **never
by the value length**: Chrome hides an autofilled value from page scripts until the user interacts with the page, so
the length is 0 even when the form is filled (measured in a `bsk` Agent Window, foreground and background, and in a
hidden Claude in Chrome tab). Reading the length is what used to make agents stop with "email is empty". Whether a
`bsk` click on Login submits those hidden values has **not** been tested; if it does not leave the login page, hand
off to a real tab (`browser-engines` step 5).

How the helper works when consented (this is the exact rule):
1. Check that Chrome **filled** the email field: `:-webkit-autofill` matches (never touch the password field, never
   read a value). Not filled → stop and tell the user; do not type anything.
2. Check whether the **Login button is disabled**.
3. If disabled: click the **page background outside the white panel, on the right side of the
   screen**, to trigger blur so the button enables. Re-check.
4. Click **Login / เข้าสู่ระบบ**. If it was never disabled, just click it.
5. A 2FA / trusted-device prompt or any change in the page → stop and ask.
The click: `bsk click '#login-submit'` (on bsk 0.4+ after a fresh `cooperate sync`, `browser-engines` step 2b; logged in on SB2 with the hidden autofilled values, 2026-09-30 — still verify the URL left the login page), or Claude in Chrome's click on a real tab; if neither works, the user presses Login in their own tab.

## Step 5b — keep the `bsk` daemon running from login (optional, `bsk` only)

The daemon is the background process that joins the browser extension to the `bsk` command. Ordinary `bsk`
commands start it on their own (BrowserSkill's own environment guide says so), so **most machines need nothing**.
Offer this only when it helps: the agent host kills child processes after a command, the user wants it already up
before the first command, or they saw the daemon missing after a reboot.

- **Look first (read-only):** `BSK_AUTO_START=0 bsk status --json` (PowerShell: `$env:BSK_AUTO_START = '0'; bsk status --json`)
  — a daemon already answering means there is nothing to do. On Windows also check whether the task exists:
  `Get-ScheduledTask -TaskName 'bsk-daemon' -ErrorAction SilentlyContinue`.
- **Ask first** (see *How to ask*): creating a login task is a persistent change on the machine. Default: **No**.
- **Windows — Task Scheduler with a hidden launcher.** A Windows *service* is not recommended (the daemon uses the user's
  own `~/.bsk` folder; reasoning, not tested). Observed on one machine (bsk 0.4.1, reported by a session after a read-only
  inspection): Task `bsk-daemon`, trigger *At log on* of the user, action `wscript.exe //B //Nologo "<...>\bsk-hidden.vbs"`,
  where the .vbs runs `bsk.exe daemon start --foreground --daemon-idle 1440m` with window style 0. Result: `LastTaskResult`
  0, daemon up ~12 s after log on, `MainWindowHandle` 0 (no window). Running `bsk.exe` straight from the Task opens a
  console window. An older Task that opened a cmd window was left **Disabled, not deleted**. **Full runbook (look, plan +
  OK, create, verify, undo) and the exact .vbs: `references/windows-daemon-hidden.md`.** Not captured: the Task's
  Settings XML and whether a window flashes at log on. Don't stop or restart a daemon that is already running to "test"
  the task (it may belong to another session; ask the user first).
  After `bsk update` on that machine the old daemon kept running; see the reference.
- **macOS (LaunchAgent) / Linux (`systemd --user`):** the same `bsk daemon start --foreground` under that
  OS's supervisor is possible, **not tested**. One known risk: the daemon **replaces itself on auto-update** (the
  old process exits after spawning its successor — seen in `~/.bsk/daemon.log*`), so a supervisor set to restart
  on exit could start a second copy that races the successor for `daemon.lock`. Test across an update before relying on it.
- Setting this up does not connect the browser: Chrome must also be running with the extension, or `bsk status`
  shows an empty `browsers` list.
- No new key in `browser.json`: whether the task exists is read from the machine (the *Look first* check), not
  from the prefs file.

## Re-running: update, don't overwrite

A machine that was set up before keeps its choices. On every re-run (also from an older session):

1. **Read first.** Load `~/.config/bombot-forge/browser.json` and show the current values in one
   small table (engine, also_installed, claude_in_chrome, auto_login_click, dev_bridge).
2. **Ask per key: keep or change?** (a picker per key: **Keep** (default) / **Change**). Ask only about a key the user brought up,
   plus any key that is **new** in this skill version and missing from the file. Never re-ask
   what is already answered.
3. **Verify, don't reinstall.** Re-check that what the file says is still true (`bsk status`, the extension
   connected). Fix only what is actually broken. Never reinstall a working `bsk`, and never change a version pin,
   unless the user asks.
4. **Merge, don't replace.** Keep keys this skill doesn't know (another skill or the user may have
   added them). Only touch keys the user chose to change.
5. **Back up, then write atomically.** `cp browser.json browser.json.bak.<YYYYMMDD_HHMMSS>` first;
   write a temp file next to it and `mv` it into place. If the file's modified time changed since
   you read it (another session ran setup meanwhile), re-read, re-merge, and tell the user.
6. **Nothing to change → write nothing** and say so.

A machine whose file still says `engine: "cdp"` or lists `cdp` in `also_installed`: offer the Step 1 removal once;
if the user keeps it, leave the keys as they are. Removal is never automatic.

## Step 6 — write the prefs and summarize

Apply *Re-running* above first. Then write `~/.config/bombot-forge/browser.json` (create the folder;
chmod 600 is fine but there are no secrets):

```json
{
  "schema": 1,
  "engine": "bsk",
  "also_installed": [],
  "claude_in_chrome": "declined",
  "auto_login_click": false,
  "dev_bridge": { "enabled": false }
}
```

`schema` lets a later version of this skill add keys without guessing: a missing or older `schema`
means "ask about the new keys", never "start over".

Finish with a short table: what is installed and tested, the lane priority, what changed versus the
previous file (or "no change"), and the one rule to remember —
**on production, list every click/submit and get the user's OK for the round first.**

## Gotchas

- Setup can't turn the extension's connection on; if `bsk status` shows no browser after the user
  says they did, ask them to check the extension popup and the right Chrome profile.
- The daemon auto-updates itself; Teibto's `flow-runner.py` pins bsk `0.3.0` (refuses `0.3.1`) —
  direct `bsk` commands work on either.
- The prefs file is per machine and private; if it gets committed by mistake, remove it from the
  repo — it can hold an account host.

## Status

v0.1 draft — written from the flow the maintainer specified; not yet run end to end on a clean
machine. Steps 4–5 depend on a Dev Bridge deployment the user already has.
Step 5b (daemon at login): Windows layout observed on one machine on 2026-11-03 (bsk 0.4.1, `wscript` + .vbs, no window) from a
session's read-only report; Task Settings XML not captured, log off/on not tried. macOS/Linux untested.
