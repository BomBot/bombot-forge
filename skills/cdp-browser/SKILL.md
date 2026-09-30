---
name: cdp-browser
description: >-
  Use when driving a browser: BrowserSkill (`bsk`) is the default for read-only checks, QA,
  screenshots and Dev Bridge reads in the browser you're already logged in to; the cdp lane
  (Chrome for Testing + `cdp.py`, port 9333) is for writes, anything where a native dialog matters,
  and `lens`/`netlog`/`stub`/`diff`. Covers which engine to pick (with measured numbers), the bsk
  safety recipes verified on a Mac (own session + pinned tab, dialog guard, NetSuite identity gate,
  bounded observe), and the cdp launch/commands/coordinator rules. For NetSuite session recovery
  (black screen, SSO loop, permission gates) pair with `netsuite-qa-browser`.
---

# Browser driving: bsk for read/QA, cdp for the rest

**Skill version: `202609_07`**

Two engines, one rule: **read/QA → `bsk`; UI-driven writes, production writes and anything a dialog could touch → cdp.** (The scoped `ns_write.py` helper clicks nothing, so it may write through `bsk` on a sandbox — see `ns-record-write`.)
This skill is the policy + verified recipes. Command reference for `bsk` comes from the upstream
`browser-skill` (installed by `bsk install-skill --harness claude-code`); `cdp.py` is your own tool
(not bundled — large, and its `login` subcommand reads credentials from a local env file).

## Pick the engine

| Task | Engine | Why |
|---|---|---|
| Read a page, smoke/QA, screenshots, Dev Bridge / SuiteQL reads | **bsk** | Uses the browser you're already logged in to; no separate profile or login |
| Record write through the scoped `ns_write.py` (no clicks, no dialogs) | **bsk** (production needs `--allow-bsk-prod` + approval) or cdp | The helper adds its own guards: dialog guard, explicit opt-in for non-sandbox on bsk, stop on unknown outcome |
| Any **UI-driven** write (clicking Save, filling forms, buttons) or anything a dialog could touch | **cdp** | `bsk` **auto-accepts every native dialog** (`alert`/`confirm`/`prompt`/`beforeunload`) and can't be told not to (verified below) |
| `lens` / `netlog` / `stub` / `diff`, shadow-DOM piercing (`a11y`), coordinate work | **cdp** | Not in `bsk` |
| Unattended or long runs | **cdp** (or don't) | A person closing the Agent Window kills a `bsk` run |

When in doubt, use cdp. NetSuite record-form QA belongs to a dedicated skill, not here.

## Lane priority (per machine)

1. **`bsk` or `cdp.py`** — whichever the machine chose in `setup-browser` (recorded in
   `~/.config/bombot-forge/browser.json`, key `engine`). `cdp.py` drives only **Chrome for Testing
   with its own profile**: Chrome 136+ ignores `--remote-debugging-port` on the default profile, so
   it cannot drive your everyday Chrome. A machine on everyday Chrome uses `bsk`.
2. **Claude in Chrome** (MCP, everyday Chrome) — optional; when the lane above is missing or
   unsuitable. Not verified here against native dialogs — treat it like `bsk` for anything that
   changes data.
3. **The user acts on the screen** — the last resort, and the only choice for a data-changing
   click when the lane above would auto-accept a dialog. Say exactly what to click and check the
   result afterwards through a read lane.

## Deprecation status (soft — nothing is removed)

- **Deprecated: cdp for read-only checks, QA and screenshots.** New read/QA work starts on `bsk`.
- **Not deprecated:** cdp for production writes, UI-driven writes / dialog-sensitive work,
  `lens`/`netlog`/`stub`/`diff`, shadow-DOM piercing, unattended runs.
- **Fallback rule:** use the cdp lane whenever `bsk` is unusable on the machine — `bsk` not
  installed, `BSK_AUTO_START=0 bsk status --json` fails (no daemon / no extension connected),
  no Chrome/Edge extension allowed, an unsupported OS/arch, or a broken auto-update.
- **Stays in the tree:** the cdp lane below, `ns_write.py --engine cdp`, and `netsuite-qa-browser`.
- **Revisit** once `bsk` has run on more than one machine and over long sessions, and once the
  team decides on production writes through `bsk`. Today: allowed only for the scoped `ns_write.py`
  helper with `--allow-bsk-prod`; never for UI clicks.

## Measured on this machine (2026-09-29, Apple Silicon Mac, Chrome 152, bsk 0.3.1)

| What | bsk | cdp.py |
|---|---|---|
| `eval 1+1`, one process per command, n=10 (median, min–max) | **18 ms** (15–33) | 409 ms (256–1401) |
| Screenshot to file, n=3 | 210 ms | 709 ms (different browsers — not the same pixels) |
| `navigate` example.com, n=5 | 352 ms | 3,688 ms — cdp looks like a built-in wait; **not comparable** |
| `evaluate` awaiting a `fetch()` (Dev Bridge `ping`) | one command, 1.2 s | needs the two-call `window.__r` pattern |

Read these with the caveats: cdp side ran as a throwaway headless Chrome for Testing (the shared
browser's coordinator refuses tab creation), one process per command (how these skills call it —
not the runner's JSONL session), small n, no NetSuite. **On real NetSuite pages the page dominates:**
Home took 14–19 s to `load` (8.9 s to `domcontentloaded`) with bsk, so engine speed barely moves
end-to-end time — the win is per-command overhead and not needing a second logged-in browser.

## bsk lane

### Setup (once per machine)

1. **CLI** — upstream `install.sh` (macOS/Linux; installs to `~/.local/bin`, verifies a checksum).
   Read it before running. Repo: `Tencent/BrowserSkill`.
2. **Extension** — the user installs it in Chrome/Edge (Chrome Web Store link is in the upstream
   `AGENT_INSTALL.md`) and turns the connection on in its popup. An agent can't do this.
3. **Daemon** — `bsk daemon start` (survived after the command returned on macOS). For agent
   commands set `BSK_AUTO_START=0`, redirect output to a file instead of piping (the team saw a
   hang from `bsk doctor | tail`, inferred), then run `bsk doctor` → expect all `ok`.
4. **Skill** — `bsk install-skill --harness claude-code` puts the upstream `browser-skill` in
   `~/.claude/skills`. It carries no network/telemetry instructions (read on install) but it
   **updates itself with the CLI**; the daemon also auto-updates every ~30 min unless
   `BSK_AUTO_UPDATE=off`.
5. **Pin caveat** — Teibto's `flow-runner.py` refuses anything but daemon **and** extension `0.3.0`.
   `0.3.1` works with direct `bsk` commands, not with that runner.

### Every run

0. **Say it.** Tell the user **each time you start using `bsk`** — one line in the chat before the first `bsk` command of the job: what for, which account/page, and that it opens a *background Agent Window* (own session, closed when done). Not for every command inside the same job. `bsk` always works inside an **Agent Window** (a separate window that only the
   session owns): `tab create` makes tabs *in that window* and there is no `bsk` mode that opens a tab in
   the user's everyday window. `--no-focus` / `--no-active` (below) keep it from stealing focus — that is the
   least intrusive `bsk` can be. If the user must SEE the page or log in, use a real tab instead (step 5).
1. **Own session, always stopped:** `bsk session start --no-focus --name <job> --json` → `session_id`.
   `bsk session stop <id>` at the end **even on failure**; confirm `bsk status` shows 0 sessions.
2. **Own tab, pinned:** `bsk tab create --no-active --url about:blank --session <id> --json` →
   `tab_id`; pass `--tab-id` on every command. Without it a command follows the active tab, which a
   peer can move. One command per session at a time (a second is refused with `session_busy`).
3. **Dialog guard after every navigation** (the page changes, the guard is gone):
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
5. **Expired session (redirected to the login page):** **do not try to log in inside the Agent Window.**
   Measured on this Mac (Chrome 152, bsk 0.3.1): on the NetSuite login page the email field stayed at 0
   characters for 10 s in an Agent Window — with the window in the background *and* with it focused — so
   "Chrome was too slow" is not the explanation; an Agent Window simply did not get autofill. An empty email
   there says nothing about whether the user saved credentials. Hand off to a **real tab**:
   - **Claude in Chrome** (if installed; skill `setup-browser`) opens a new *tab* in the user's own window,
     where autofill works — then follow the auto-login rule there (`#login-submit` enabled → click once;
     never read or type a credential; stop on an MFA prompt).
   - Otherwise tell the user to log in in their own Chrome (on macOS `open -a "Google Chrome" "<login url>"`
     opens it as a tab — **not yet exercised**), and re-run the read after they say they're in.
   - `bsk tab borrow` moves a user's tab into the Agent Window (the user confirms each time) — **not
     exercised**, and the tab then lives in that window.
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
or popups, so `bsk` still must not *click* data-changing UI on production. `ns_write.py` is not
affected (it calls `N/record`, clicks nothing). If a hung dialog blocks the session, dismiss it by
hand, then `bsk session stop <id>` again and confirm `session_count` is 0.

### Concurrency soak (2026-09-30, one Mac, read-only, sandbox)

3 bsk sessions in parallel, each with its own pinned tab, 30 minutes, one cycle every ~20 s per
session (navigate → guard → identity gate → per-session marker check): **273 cycles, 0 failures,
0 cross-talk between tabs, 0 stray dialogs**; navigate p50 0.93 s / max 1.82 s, evaluate p50 0.19 s /
max 1.71 s; `session_count` back to 0 after `session stop`. Not covered: more than 3 sessions,
sessions longer than 30 minutes, writes during contention, other OSes.

### Known limits (Teibto's tests, mostly Windows — recheck on this Mac before relying)

- `fill` fails or is silently dropped on `<input type=date>`, React-controlled inputs and Quill
  editors; values starting with `-` need `--value=<v>`. Details: `Teibto/teibto-browser-qa`,
  `references/engine2-bsk.md` §4.
- Screenshot of a **background** tab is documented to fail; on macOS/0.3.1 it succeeded (not
  investigated — may be because it was the window's only tab).
- Closing the Agent Window mid-run kills the run — including after a Save. Tell the owner first.
- Everything above was measured with a person's real Chrome: an Agent Window shares its logins and is
  **not** a sandbox — but it does **not** get autofill (see step 5).

## cdp lane (Chrome for Testing + cdp.py)

Dedicated **Chrome for Testing** over the DevTools Protocol on a **fixed port (9333)** and a
**persistent profile** (session and trusted-device token survive). It's separate from the main
Chrome and doesn't auto-update. `cdp.py` talks CDP directly — no daemon layer; its header records
the reason (an earlier daemon-based tool hung silently). `bsk` is a daemon too, and its team tests
are loopback-only, so keep cdp for long or unattended work.

### Launch (fixed profile)

```bash
~/Applications/"Google Chrome for Testing.app"/Contents/MacOS/"Google Chrome for Testing" \
  --user-data-dir="$HOME/.qa-chrome/<task>" --remote-debugging-port=9333 \
  --no-first-run --no-default-browser-check --disable-session-crashed-bubble about:blank
```

- **Chrome 136+ ignores `--remote-debugging-port` on the default profile** — `--user-data-dir` is
  mandatory. One profile per kind of work.
- **Shared NetSuite browser + coordinator.** On a browser registered as shared, `cdp.py newtab` is
  **refused** ("use ns-session tab <account> or claim_tab"). Don't work around it. Check
  `python3 cdp.py ns-session status <compid>` (read-only): `bound:false` means no lane is registered
  for that account on this machine (true for SB2 on 2026-09-29), and `ns-session bind` is a registry
  change for the session owner to decide. With a lane: `TGT_ID=$(python3 cdp.py ns-session tab <compid>)`,
  work in that tab only, close only that tab.

### Commands

```bash
export CDP_PORT=9333
python3 cdp.py tabs | url | nav <url> [wait] | eval "<js>" | evalf <file.js>
python3 cdp.py a11y [query]           # accessibility tree → @NNNN refs usable with click; pierces shadow DOM
python3 cdp.py click <sel|@ref>       # real click via Input event (not synthetic)
python3 cdp.py shot <out.png> [sel] [--dsf=N] [--vw=W] [--vh=H]
```

### Screenshots — `cdp.py shot`

`Page.captureScreenshot` renders the page to PNG — it's not a screen grab, so a covered or
non-frontmost Chrome still gives the right image (unlike macOS `screencapture`), and it writes a real
file you can embed in a report.
- `--vw/--vh/--dsf` must be passed on the `shot` call itself (a separate `viewport` command dies
  with the websocket).
- `shot <sel>` uses `document.querySelector` — can't pierce shadow DOM; shoot the viewport and crop.
- Cropping to one element drops popups/dropdowns (different layer).

### Web-component apps (nested shadow DOM)

`document.querySelector` from outside finds nothing → `cdp.py a11y` for a `@ref`, then `click`, or
walk `shadowRoot` yourself. Synthetic events (`el.click()`/`dispatchEvent`) are rejected by some
apps — fire a real `Input.dispatchMouseEvent` (import `cdp`, use `cdp.C()`, which sets
`suppress_origin=True`; a raw websocket gets a 403 origin check).

### Auto-login (click submit, never type credentials)

Same rule as bsk step 5: if the Login button is disabled, click the background once (fires `blur`);
click **Login**; never read the password field; empty fields → stop and ask. `cdp.py login` (reads
`NS_EMAIL`/`NS_PASSWORD`/`NS_TOTP_SECRET` from a local `NS_ENVFILE`) exists for hands-off login —
prefer click-submit.

## Other browsers

Claude in Chrome (`mcp__claude-in-chrome__*`) drives the main Chrome for tasks that need the main
Google session (e.g. Sheets under `<work-email>`). Don't use the 9333 profile (a `<personal-gmail>`
login) for those — Access denied.

## Quick reference

| Need | bsk | cdp |
|---|---|---|
| Session / tab | `bsk session start --no-focus --json` · `bsk tab create --no-active --url about:blank …` | `cdp.py ns-session tab <compid>` |
| Navigate | `bsk navigate <url> --wait-until domcontentloaded …` | `cdp.py nav <url>` |
| Run JS | `bsk evaluate "<js>" …` (awaits promises) | `cdp.py eval "<js>"` |
| Bounded page view | `bsk observe --max-tokens 600 …` | `cdp.py a11y <query>` |
| Screenshot | `bsk screenshot --out f.png …` | `cdp.py shot f.png` |
| Cleanup | `bsk session stop <id>` · `bsk status` | close only your own tab |

## Status

v0.2 — bsk lane verified 2026-09-29 on one Apple Silicon Mac against a NetSuite sandbox (login,
identity gate, Home read, dialog behaviour, `evaluate`+`fetch`); numbers above are from that run.
Not yet pressure-tested per `superpowers:writing-skills`. Not measured: cdp against a bound NetSuite
lane on this Mac, long sessions, multi-agent contention on macOS.
