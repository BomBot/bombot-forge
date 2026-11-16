# cdp lane — history (no longer a skill)

**Information only.** The plugin used to have a second browser lane: Chrome for Testing driven over the DevTools Protocol by
`cdp.py` (skill `cdp-browser`, renamed `browser-engines` in 0.22.0). Since 0.41.0 the skills use bsk and Claude in
Chrome only; `setup-browser` offers to remove an old cdp setup, and the `cdp-browser` stub was removed. This page records
how it worked and why bsk replaced it. `ns_write.py` / `ns_read.py` still accept `--engine cdp` for a machine that kept it.

When a machine still has it, cdp is the lane for: `lens` / `netlog` / `stub` / `diff`, shadow-DOM piercing (`a11y`),
coordinate-level clicks (`Input.dispatchMouseEvent`), and long unattended runs (a person closing a bsk Agent Window kills
the run). It is also the fallback when bsk is unusable on that machine (not installed, `BSK_AUTO_START=0 bsk status --json`
fails, extension not allowed, broken auto-update).

## Why bsk became the default — measured on this machine (2026-09-29, Apple Silicon Mac, Chrome 152, bsk 0.3.1)

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

## Other browsers (cdp-specific)

Don't use the 9333 profile (a `<personal-gmail>` login) for Google Sheets/Drive under `<work-email>` — Access denied. Use
Claude in Chrome there.

| Need | cdp |
|---|---|
| Session / tab | `cdp.py ns-session tab <compid>` |
| Navigate | `cdp.py nav <url>` |
| Run JS | `cdp.py eval "<js>"` (fire into `window.__r`, read it back in a second call) |
| Bounded page view | `cdp.py a11y <query>` |
| Screenshot | `cdp.py shot f.png` |
| Cleanup | close only your own tab |
