---
name: setup-browser
description: >-
  Use when setting up browser automation on a machine for the first time or changing it: choose
  between bsk (BrowserSkill, everyday Chrome) and cdp (Chrome for Testing) with the trade-offs,
  install the chosen one, optionally connect Claude in Chrome, then offer a Dev Bridge trial and
  record whether Claude may click the NetSuite Login button for you. Interactive — asks before
  each step; saves the choices to a per-machine prefs file.
---

# Setup Browser (engine choice, install, Dev Bridge, login consent)

**Skill version: `202609_04`**

Run once per machine (and again to change a choice). It asks, installs what you pick, tests it,
and writes the answers to `~/.config/bombot-forge/browser.json` — a local file with **no
secrets**, never in a repo. Other skills (`cdp-browser`, `ns-record-write`, `ns-live-verify`) read
it. Ask **one step at a time** and wait for the answer; never install or click ahead of an OK.

## Iron rules

- **Never read, extract, or type a password.** The login helper only clicks a submit button;
  Chrome's own autofill fills the fields. Empty fields, MFA, or a changed page → stop and ask.
- **Ask before installing anything** and before running a downloaded script — read it first.
- **Don't guess.** If a step's outcome can't be verified (extension connected, Dev Bridge script
  id), say so and ask; never invent an id, URL, or version.
- **No real account/script ids in this repo.** Whatever the user gives you goes only into the local
  prefs file.
- Installing the browser extensions and turning them on is the **user's** click — an agent can't.

## Step 0 — look before asking (read-only)

Check what already exists: `command -v bsk`, `BSK_AUTO_START=0 bsk status --json`,
`ls ~/Applications/"Google Chrome for Testing.app"`, an existing `~/.config/bombot-forge/browser.json`,
and whether the `mcp__claude-in-chrome__*` tools are available. Report it in two lines and skip
any step that is already done and working. **If `browser.json` exists this is an UPDATE run** — see
*Re-running: update, don't overwrite* below; never treat the machine as blank.

## Step 1 — pick the engine

Show this table and recommend **bsk** for anyone who works in their everyday Chrome:

| | **bsk** (BrowserSkill) | **cdp** (Chrome for Testing + `cdp.py`) |
|---|---|---|
| Browser | Your **everyday Chrome/Edge**, already logged in | A **separate** Chrome for Testing with its own profile (log in once there) |
| Speed per command | Fast (measured ~22× per command vs cdp) | Slower per command |
| Setup | CLI + extension you turn on + daemon | Chrome for Testing + fixed profile + `cdp.py` (yours, not bundled) |
| Native dialogs | **Auto-accepts every one, can't be turned off** — so: never click data-changing UI on production; the scoped `ns_write.py` helper is fine (no clicks) | You control them; popup-blocker off is a false-positive risk for popup checks |
| Extras | — | `lens`, `netlog`, `stub`, `diff`, shadow-DOM piercing, unattended runs |
| Risk | Third-party (Tencent) daemon that **auto-updates** (~30 min; `BSK_AUTO_UPDATE=off` to pin); verified on one Mac only here | Can't drive your everyday Chrome (Chrome 136+ ignores the debug port on the default profile) |
| Production writes | `ns_write.py --allow-bsk-prod` only, after dry-run + your approval | `ns_write.py --engine cdp`, and UI-driven writes |

Ask: **bsk, cdp, or both?** Record `engine` (primary) and `also_installed`.

## Step 2a — install bsk (if chosen)

1. Read upstream `install.sh` (`Tencent/BrowserSkill`; macOS/Linux → `~/.local/bin`), show the user
   what it does, run it on OK. Windows: follow upstream `AGENT_INSTALL.md`; don't improvise.
2. **Open the extension page for the user**: `open "https://chromewebstore.google.com/detail/browserskill/hhcmgoofomhgciiibhipgmgkgnoenaoi"`
   (macOS; use the platform's opener elsewhere). Tell them: *Add to Chrome, then open the
   extension popup and turn the connection on.*
3. `bsk daemon start`, then `bsk doctor` (redirect to a file rather than piping) → expect all `ok`.
4. `bsk install-skill --harness claude-code`.
5. Verify: `BSK_AUTO_START=0 bsk status --json` lists a connected browser; open a throwaway session
   (`bsk session start --no-focus`, own tab on `about:blank`, `bsk session stop`) and confirm
   `session_count` is back to 0. Details and per-run rules: skill `cdp-browser`.

## Step 2b — install cdp (if chosen)

Follow the `cdp-browser` skill's cdp lane: Chrome for Testing, a fixed profile under
`~/.qa-chrome/<name>`, port 9333, `cdp.py` supplied by the user. Verify with `cdp.py tabs`.

## Step 3 — Claude in Chrome (optional)

Say it is **optional** and that it is the second-priority lane (after bsk/cdp) — useful when the
first lane is missing, or for sites that need your main Chrome/Google session. Ask: *install it
yourself from the link, or want me to walk you through?* Link:
`https://chromewebstore.google.com/detail/claude/fcoeoabgfenejglbffodgkkbkcdhcgfn`.
After they install, test it: load the tools (`ToolSearch` → `select:mcp__claude-in-chrome__tabs_context_mcp`)
and call `tabs_context_mcp`. Record `claude_in_chrome: true|false|declined`.

Lane priority to state at the end: **1. bsk or cdp · 2. Claude in Chrome · 3. you act on the
screen** (the last resort, and the only choice for a data-changing click a dialog could hit).

## Step 4 — offer a Dev Bridge trial

Explain: *Dev Bridge (`Teibto/TEIBTO-Dev-Bridge`) is a read-only Suitelet in your NetSuite account.
Through the logged-in browser tab it runs SELECT-only SuiteQL, loads a record as JSON, looks up fields,
checks features and runs searches, so Claude can check the real state of records, GL and script
deployments instead of guessing — nothing is written. Administrator role only.* Ask whether to try it.

If yes:
1. Ask the user to **copy the URL of the Home page of the account they work in** and paste it.
   Derive the host and account id from it (`<ACCOUNT>` / `<ACCOUNT>-sb2` style) — don't guess.
2. The bridge is addressed by a script id + deploy id. The repo's README recommends
   `customscript_teibto_dev_bridge` / `customdeploy_teibto_dev_bridge`, and `ns_read.py` tries those. If the
   account uses other ids, ask the user for them (from the script record). If the bridge isn't deployed in
   that account, say so and stop — deploying it is a separate decision.
3. Test it: `python3 <plugin>/skills/ns-live-verify/scripts/ns_read.py ping --account <ACCOUNT>` (bsk lane).
   Confirm `account` and `envType` match what they expect and `user.isAdmin` is true. Non-sandbox
   accounts need `--allow-prod-read` — say why (the data goes to the model provider) before adding it.
4. Save under `dev_bridge` in the prefs file (`enabled`, `host`, `account`; and, only when the ids are not
   the defaults, `endpoints["<account>"] = {"path": "/app/site/hosting/scriptlet.nl?script=<id>&deploy=<id>"}`).

## Step 5 — Login helper consent

Ask: *If a NetSuite page falls back to the login screen, may I click **Login / เข้าสู่ระบบ** for
you?* State plainly: **I will never read your password field.** It works only if Chrome is set to
autofill the email + password on its own, without asking you to type or unlock anything at fill
time. Record `auto_login_click: true|false`.

How the helper works when consented (this is the exact rule):
1. Check that the **email field already has a value** (never touch the password field). Empty →
   stop and tell the user; do not type anything.
2. Check whether the **Login button is disabled**.
3. If disabled: click the **page background outside the white panel, on the right side of the
   screen**, to trigger blur so the button enables. Re-check.
4. Click **Login / เข้าสู่ระบบ**. If it was never disabled, just click it.
5. A 2FA / trusted-device prompt or any change in the page → stop and ask.
With bsk the click is `bsk click '#login-submit'` on the machine's own pinned tab; with cdp use
`cdp.py click`; with Claude in Chrome use its click.

## Re-running: update, don't overwrite

A machine that was set up before keeps its choices. On every re-run (also from an older session):

1. **Read first.** Load `~/.config/bombot-forge/browser.json` and show the current values in one
   small table (engine, also_installed, claude_in_chrome, auto_login_click, dev_bridge).
2. **Ask per key: keep or change?** Default is **keep**. Ask only about a key the user brought up,
   plus any key that is **new** in this skill version and missing from the file. Never re-ask
   what is already answered.
3. **Verify, don't reinstall.** Re-check that what the file says is still true (`bsk status`,
   `cdp.py tabs`, the extension connected). Fix only what is actually broken. Never reinstall a
   working `bsk`/Chrome for Testing, and never change a version pin, unless the user asks.
4. **Merge, don't replace.** Keep keys this skill doesn't know (another skill or the user may have
   added them). Only touch keys the user chose to change.
5. **Back up, then write atomically.** `cp browser.json browser.json.bak.<YYYYMMDD_HHMMSS>` first;
   write a temp file next to it and `mv` it into place. If the file's modified time changed since
   you read it (another session ran setup meanwhile), re-read, re-merge, and tell the user.
6. **Nothing to change → write nothing** and say so.

Engine change (bsk ↔ cdp) is a change like any other: ask, install only the missing side, keep
the other installed (`also_installed`) unless the user wants it removed — removal is never automatic.

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
**no data-changing clicks on production through bsk**.

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
