---
name: setup-init
description: >-
  Use when setting up a new team member's machine from zero, or checking what an existing machine is missing:
  "/setup-init", "ตั้งเครื่องใหม่", "เช็คว่าเครื่องพร้อมไหม". Detects Windows or macOS, checks every piece of the team
  setup (GitHub CLI, this plugin, global instructions, browser lane + Dev Bridge, team plugins, SuiteCloud CLI + SDF for
  devs) as one checklist, explains what each piece is for, then walks through the missing ones in order by running the
  matching setup skill. Ends with what a new session needs to know.
---

# Setup Init (new machine, one checklist)

**Skill version: `202611_02`**

The front door for a new machine. It does not install anything itself: it checks, explains, and runs the setup
skills in order, each of which asks before it changes anything. Speak plain Thai mixed with English terms; the user may
not be a developer.

## Iron rules

- Every install, config change and login goes through the setup skill that owns it, and that skill asks first.
- **Never read, print or type a password, token or one-time code.** Logins are the user's, in their browser.
- Nothing is written to NetSuite. Nothing is committed, pushed, deployed or sent (Slack, email).
- A step that fails: stop, show the real error, offer a fix. Never skip it silently.

## Step 0 — mode and OS

1. **Permission mode.** Tell the user that setup runs many commands, so the smoothest way is to switch this session
   to **Bypass permissions** (or **Auto** if they prefer Claude to check risky commands first) — in the Claude app it is
   the mode picker next to the message box; in the terminal, Shift+Tab cycles modes. It is their switch; the skills
   still ask before every install. Then carry on in whatever mode they choose.
2. **OS:** `uname -s` (macOS) or PowerShell `$env:OS` (Windows). Most office machines are Windows: use PowerShell
   commands and Windows paths from here on, and pass the OS to every skill you run.

## Step 1 — the checklist (read-only, do it without asking)

Check every item and show **one table**: # · item · what it is for · installed · set up / signed in · next step.

| # | Item | What it is for | How to check |
|---|---|---|---|
| 1 | git + GitHub CLI (`gh`) | clone and read Teibto's code | `git --version`, `gh --version`, `gh auth status`, `gh repo list Teibto --limit 1` |
| 2 | plugin `bombot-forge` | these setup and NetSuite skills | `claude plugin list` (version) |
| 3 | global instructions | how Claude works for you in every session: rules, Slack drafts, browser lanes | `~/.claude/CLAUDE.md` exists and has the team sections (e.g. `# Accuracy`, `# Browser automation`) |
| 4 | browser lane: bsk (+ Claude in Chrome) | Claude reads NetSuite pages in your logged-in Chrome | `bsk` on the PATH, `BSK_AUTO_START=0 bsk status --json` shows a connected browser, `~/.config/bombot-forge/browser.json` |
| 5 | Dev Bridge | read-only SuiteQL / record reads, to check real data instead of guessing (Administrator only) | `dev_bridge.enabled` in `browser.json` |
| 6 | team plugins | code review, KM, release notes, process skills | `claude plugin list` against `setup-plugins/plugins.json` |
| 7 | Python | runs the Dev Bridge helper `ns_read.py` | `python3 --version` (Windows: `python` / `py`) |
| 8 | SuiteCloud CLI + SDF project (devs) | pull and later deploy NetSuite files/objects | `node`, `java`, `suitecloud --version`, `suitecloud account:manageauth --list`, an SDF project in this folder |

Also flag an old **cdp** setup (Chrome for Testing, `~/.qa-chrome/`, `cdp.py`): `setup-browser` will offer to remove it.

## Step 2 — role (one question, picker)

*Will you edit code (SuiteScript) or deploy with SDF?*
- **Yes — dev** → global instructions for devs, and item 8.
- **No — I work in the NetSuite screens** → non-dev global instructions (Claude may read code and explain it, but not
  deploy); item 8 is skipped.
- **Not sure** → treat as non-dev for now; switching later is a re-run.

## Step 3 — walk the missing items, in this order

For each item that is not ready: say in one line what it is for, run its skill (invoke `/bombot-forge:<skill>`; if
slash commands of this plugin are not loaded yet, read `SKILL.md` from
`~/.claude/plugins/cache/bombot-forge/bombot-forge/<version>/skills/<skill>/SKILL.md` and follow it), verify, tick it.
Items already ready: say so and move on.

1. **`setup-cli` Part A** — git + gh, signed in, Teibto repos visible.
2. **Plugin** — already installed if this skill is running. After a fresh install the user types `/reload-plugins`
   (or restarts Claude Code) so the slash commands appear.
3. **Global instructions** — dev: `setup-global-instructions`; non-dev: `setup-global-instructions-nondev`. Merge with an
   existing file, never overwrite.
4. **`setup-browser`** — bsk, optional Claude in Chrome, Dev Bridge trial (it asks for the Home page URL at that step),
   login-click consent. On Windows, the daemon-at-log-on step.
5. **`setup-plugins`** — pass the role: the preset (dev = team toolkit + working-discipline plugins; non-dev = team
   toolkit) is offered first, extras by group after. Needs step 1 done (the team toolkit is a private repo).
6. **`setup-cli` Part B** (devs only) — SuiteCloud CLI, clone a repo or create an SDF project here, auth id, `file:list`
   test. Not ready now → write `~/.claude/onboarding-sdf-todo.md` (what is left) and give the phrase *"ตั้ง SDF ต่อ"*.

## Step 4 — finish

1. The checklist table again, after the run (ready / skipped / failed + note).
2. **What a new session needs to know:** nothing extra. Every new session loads `~/.claude/CLAUDE.md` (the rules and
   the browser lanes) and the plugin skills by themselves, and the browser rules point Claude at
   `~/.config/bombot-forge/browser.json` for which lanes this machine has. To use the browser, just ask, e.g.
   *"ใช้ bsk เปิด <ลิงก์ NetSuite> แล้วบอกว่า field X มีค่าอะไร"* or *"ใช้ Dev Bridge เช็คว่า script นี้ deploy อยู่ไหม"*.
   Restart Claude Code once if this session installed the plugin or changed `CLAUDE.md`.
3. Pending items with the phrase to continue later.

## Status

Draft 202611_01, written 2026-11-16 from the maintainer's checklist. Not run end to end on a clean machine. The
`/reload-plugins` command is taken from a string in Claude Code 2.1.281 ("reload-plugins (or relaunch) to load what
qualifies"), not tried.
