---
name: cdp-browser
description: >-
  Use when driving Chrome for Testing over CDP with the `cdp.py` helper (port 9333, fixed
  persistent profile) — launching the browser, running `tabs`/`nav`/`eval`/`a11y`/`click`/`shot`,
  taking render-accurate screenshots, piercing shadow-DOM web components, and the safe
  click-submit auto-login. The browser-driver mechanics; for NetSuite QA session recovery
  (black screen, SSO loop, permission gates) pair with `netsuite-qa-browser`.
---

# CDP Browser (Chrome for Testing + cdp.py)

**Skill version: `202609_01`**

Drive a dedicated **Chrome for Testing** over the DevTools Protocol with the `cdp.py` helper.
It runs on a **fixed CDP port (9333)** and a **persistent profile**, so the session (and
trusted-device token) survives across runs — no re-login every time. Chrome for Testing is
installed separately from the main Chrome and does **not** auto-update, so it won't break
mid-task when Chrome bumps a version.

`cdp.py` is your own tool (canonical copy at `~/WebstormProjects/<qa-project>/scripts/qa/cdp.py`,
copied into projects as `scripts/qa/cdp.py`) — this skill is how to **use** it, not a copy of it.
Related: `netsuite-qa-browser` owns the NetSuite-specific session-recovery playbook (black
screen / hang, session drop, 2FA/SSO loop, CDP not responding, File Cabinet hash verify, role
switching, permission-gate proof).

## When to use which browser

| | Chrome for Testing (cdp.py, port 9333) | Claude in Chrome (MCP, main Chrome) |
|---|---|---|
| Use for | QA/verify NetSuite, automation, screenshots, driving shadow DOM, multi-account login | tasks that need the main Google/Chrome session (e.g. Google Sheets under `<work-email>`) |
| Driven by | `cdp.py` (eval/click/shot) | `mcp__claude-in-chrome__*` (navigate/computer/read_page) — pick Browser 1/2 |

- ❌ Don't use the 9333 profile (a `<personal-gmail>` login) to open Google Sheets owned by
  `<work-email>` → Access denied. Use claude-in-chrome (main Chrome) for that.

## Launch Chrome for Testing (fixed profile)

```
~/Applications/Google Chrome for Testing.app     # binary (separate from main Chrome)
~/.qa-chrome/<task>                               # persistent profile — session stays logged in
CDP port 9333
```

```bash
~/Applications/"Google Chrome for Testing.app"/Contents/MacOS/"Google Chrome for Testing" \
  --user-data-dir="$HOME/.qa-chrome/<task>" --remote-debugging-port=9333 \
  --no-first-run --no-default-browser-check --disable-session-crashed-bubble about:blank
```

- **⚠️ Chrome 136+ ignores `--remote-debugging-port` when using the default profile** — you
  **must** pass a `--user-data-dir`. The fixed profile is not optional; it's what makes CDP work
  at all on current Chrome.
- One profile per kind of work (`~/.qa-chrome/<task>`) keeps sessions from colliding.

## cdp.py commands

```bash
export CDP_PORT=9333
python3 cdp.py tabs | url | nav <url> [wait] | eval "<js>" | evalf <file.js>
python3 cdp.py a11y [query]           # accessibility tree → @NNNN refs usable with click; pierces shadow DOM
python3 cdp.py click <sel|@ref>       # real click via Input event (not synthetic)
python3 cdp.py shot <out.png> [sel] [--dsf=N] [--vw=W] [--vh=H]
```

## Screenshots — use `cdp.py shot` only

`Page.captureScreenshot` tells Chrome to **render the page** to PNG — it is not a screen grab.
So it's correct even if another window covers Chrome or Chrome isn't frontmost (unlike macOS
`screencapture`, which captures whatever is painted on screen). It writes a real file to disk,
so you can embed it in an HTML report — unlike an extension screenshot that only lives in chat.

Gotchas that have bitten:
- **`--vw/--vh/--dsf` must be passed on the `shot` call itself** — a separate `viewport` command
  has no effect (the Emulation override dies with the websocket).
- **`shot <sel>` uses `document.querySelector` and can't pierce shadow DOM** — for web-component
  apps, shoot the whole viewport and crop afterward.
- **Cropping to one element drops popups/dropdowns** — they're on a different layer.
- A tab that isn't frontmost **in Chrome** won't be painted — `shot` calls `Page.bringToFront`
  for you already.

## Web-component apps (nested shadow DOM)

For apps built as web components (deeply nested shadow roots), `document.querySelector` from
outside finds nothing. Use `cdp.py a11y` to get a `@ref`, then `click` it — or write a helper
that walks `shadowRoot` itself. **Synthetic events (`el.click()` / `dispatchEvent`) are rejected
by some apps** — fire a real `Input.dispatchMouseEvent` at actual coordinates (import `cdp` and
use `cdp.C()`, which sets `suppress_origin=True`; a raw websocket connection gets a 403 origin
check).

## Auto-login (safe: click submit, never type credentials)

When a session expires and a page bounces to the login screen (Chrome has autofill set up):
1. If the **Login button is disabled**, click the background outside the login box once (fires
   `blur` → the button enables).
2. Click **Login / submit**.
- 🔑 **Never read or extract the password field** — only click submit; the credential belongs to
  Chrome, not to you.
- If the fields are **empty** (not autofilled) → **stop and ask**; never type a credential.
- 2FA/trusted-device: the persistent profile keeps the token ~30 days, so it usually won't
  re-prompt for a TOTP.

> `cdp.py` also has a fuller `login` subcommand that reads `NS_EMAIL`/`NS_PASSWORD`/`NS_TOTP_SECRET`
> from a local `NS_ENVFILE` (`.env`) for hands-off login. That `.env` stays on the machine and is
> never committed. Prefer the click-submit path above unless you specifically need the automated one.

## Quick reference

| Need | Command |
|---|---|
| Launch (fixed profile) | `"…/Google Chrome for Testing" --user-data-dir="$HOME/.qa-chrome/<task>" --remote-debugging-port=9333 …` |
| List tabs / current url | `python3 cdp.py tabs` · `python3 cdp.py url` |
| Navigate | `python3 cdp.py nav <url> [wait]` |
| Run JS | `python3 cdp.py eval "<js>"` · `python3 cdp.py evalf <file.js>` |
| Find a clickable (pierces shadow DOM) | `python3 cdp.py a11y [query]` → `@NNNN` |
| Real click | `python3 cdp.py click <sel\|@ref>` |
| Render-accurate screenshot | `python3 cdp.py shot out.png [--dsf=N --vw=W --vh=H]` |

## Status

v0.1 draft — distilled from BomBot's own browser-automation conventions (verified in use). Not
yet pressure-tested per `superpowers:writing-skills`. The `cdp.py` script itself is intentionally
not bundled here (it's a large personal tool with a credential-reading `login` command); this
skill documents its usage, which is what's reusable.
