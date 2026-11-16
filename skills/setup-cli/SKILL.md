---
name: setup-cli
description: >-
  Use when a machine needs the team's command-line preset checked, installed and signed in: GitHub CLI (`gh`, plus
  git) for everyone, and for anyone who will edit code the SuiteCloud CLI with an SDF project in the current folder
  (clone a Teibto repo or create a new project), an auth id named the team's way and a read-only `file:list` test.
  Re-run any time (for example "ตั้ง SDF ต่อ"): it checks first and only does what is missing.
---

# Setup CLI (gh + SuiteCloud CLI preset)

**Skill version: `202611_01`**

One preset, two parts. Part A (GitHub CLI) is for every machine. Part B (SuiteCloud CLI + SDF project + auth) is for
anyone who will edit code. Every step: **check → explain in one line what it is for → install if missing → sign in if
not → verify**. Ask before every install; the user does every login in their own browser.

## Iron rules

- **Ask before installing anything** (say the exact command) and before running a downloaded script.
- **Never read, print or type a password, token or one-time code.** Never run `gh auth token` or
  `gh auth status --show-token`. Logins happen in the browser page that the command opens, by the user.
- **Interactive commands go to the user's own terminal.** The agent's shell cannot answer prompts. Give one line to
  paste and say what to choose at each prompt; then verify from here.
- **Read-only in NetSuite.** The only SuiteCloud call this skill makes against an account is `file:list`. Never
  `project:deploy`, `file:upload`, `object:import` into a tracked folder, or anything that writes.
- **Don't guess** a version, package id or prompt wording: check `--help`, `--version`, `winget search` / `brew info`
  on the machine, or Oracle's current docs, and say where it came from.
- Never commit or push.

## Step 0 — look (read-only, do it without asking)

- OS: `uname -s` (macOS) or PowerShell `$env:OS` / `[System.Environment]::OSVersion` (Windows; most office machines).
  Use that OS's commands from here on.
- Part A: `git --version`, `git config --global user.name`, `git config --global user.email`, `gh --version`,
  `gh auth status` (no `--show-token`).
- Part B: `node --version`, `npm --version`, `java -version`, `suitecloud --version`,
  `suitecloud account:manageauth --list` (auth ids only; it prints no secrets), whether the current folder already has
  `suitecloud.config.js` / `project.json` / `src/` (an SDF project) and whether it is empty.
- Show one table: item · what it is for · installed · signed in / set up · next step. Then ask which part to run
  (picker: **Both (Recommended for devs)** / **GitHub only** / **SuiteCloud only**).
- **Non-dev machine** (its `~/.claude/CLAUDE.md` came from the non-dev setup, or `~/.claude/settings.json` has
  `permissions.deny` rules for `suitecloud`): run Part A only and say why — that machine is set up not to run SDF.

## Part A — GitHub CLI

What for: Claude can clone Teibto's repos, read the code and history, and (only when you say so) open issues or PRs.

1. **git missing** → Windows `winget install --id Git.Git -e`; macOS `xcode-select --install` (or `brew install git`).
2. **gh missing** → Windows `winget install --id GitHub.cli -e`; macOS `brew install gh` (no Homebrew → ask; the
   installer from cli.github.com is the alternative). On Windows a freshly installed `gh` may not be on the PATH of the
   already-open shell: open a new terminal, or call it by its full path; check with `Get-Command gh`.
3. **Not signed in** → the user runs in their own terminal: `gh auth login --hostname github.com --git-protocol https --web`
   — press Enter through the prompts, copy the one-time code shown on their screen into the browser page, approve.
   Then `gh auth setup-git` (git uses gh for HTTPS).
4. **git identity missing** → propose `user.name` = their GitHub login and ask which email to use; set with
   `git config --global` after OK.
5. **Verify:** `gh auth status`; `gh api user --jq .login` (the team format is `FirstName-Nickname-Teibto`; if it does not
   match, tell them to change it at GitHub Settings > Account, do not block); `gh repo list Teibto --limit 5` — no repos
   means the org invitation was not accepted yet: stop and tell them.

## Part B — SuiteCloud CLI and an SDF project

What for: pull files and objects from a NetSuite account into a git repo, compare them, and (later, with approval)
deploy. This skill only sets it up and proves it can read.

### B1. Install

- **Requirements:** read the supported Node.js and Java versions from Oracle's current SuiteCloud CLI docs before
  installing (they change between releases; don't pick a version from memory). Show the user what you found and where.
- Node.js missing → Windows `winget install --id OpenJS.NodeJS.LTS -e`; macOS `brew install node` (adjust to the version
  the docs require). Java missing → find the package with `winget search` / `brew search` for the JDK version the docs name,
  and show it before installing.
- `npm install -g @oracle/suitecloud-cli`, then `suitecloud --version`. If it shows Oracle's license, **the user
  accepts it** — read it to them in one line, never accept it for them.

### B2. The project in this folder

Ask (picker): **Clone a Teibto repo** / **Create a new SDF project** / **Already here** (Step 0 found one).

- **Clone:** `gh repo list Teibto --limit 100`, let the user pick (search by customer name). Clone into a temporary
  subfolder (`gh repo clone Teibto/<repo> _clone_tmp`), then move **everything** (including `.git` and dotfiles) up into
  the current folder and remove the empty `_clone_tmp`, so the user keeps working in this session. The current folder
  must be empty apart from files the user says are fine; otherwise stop and ask.
- **Create:** `suitecloud project:create --type ACCOUNTCUSTOMIZATION --projectname <name>` (verified flags on
  SuiteCloud CLI 3.0.0; check `--help` on other versions). It creates `<name>/`; move its contents up into the current
  folder the same way. Offer `git init` (no commit).

### B3. Auth id (team format)

The team names auth ids after the account and environment, role Administrator:

| Account | Auth id |
|---|---|
| Production `<ACCOUNT>` (host `<ACCOUNT>.app.netsuite.com`) | `<ACCOUNT>-Adm-Prod` |
| Sandbox `<ACCOUNT>_SB1` (host `<ACCOUNT>-sb1.app.netsuite.com`) | `<ACCOUNT>_SB1-Adm-Sand` |

- Ask for the account's **Home page URL** (log in, click Home, copy the address bar) and derive `<ACCOUNT>` and the
  environment from the host. Don't guess.
- The role must be **Administrator**. Another role → stop and ask; don't invent a suffix.
- **Already in `account:manageauth --list`?** Reuse it: the setup below lets the user pick an existing auth id.
- `account:setup` is interactive only (SuiteCloud CLI 3.0.0 has no flag for the auth id). The user runs, **inside this
  project folder**, in their own terminal: `suitecloud account:setup -i`. Tell them what to pick at each prompt — new
  browser-based login (or the existing id), the auth id name from the table above — then log in and choose the
  Administrator role in the browser that opens. Read the prompt wording from their screen if they paste it; don't
  describe options you have not seen.
- Verify: `project.json` now has `defaultAuthId` equal to that name. `project.json` is machine-local; check `.gitignore`
  and don't commit it.

### B4. Test it is ready (read-only)

- `suitecloud file:list --folder "/SuiteScripts"` → expect a file list (or an empty folder message), not an auth error.
- Report: the account, the auth id, how many files were listed. An auth error → back to B3; don't retry in a loop.

## Finish

One table again (item · status · note), and:

- What is still pending, with the phrase to type later (for example *"ตั้ง SDF ต่อ"* runs this skill again from Part B).
- Remind: deploys follow the global instructions (scoped `deploy.xml`, import-compare first, sandbox objects through the
  UI, production only with approval) and the `ns-sdf-prod-deploy` skill.

## Status

Draft 202611_01, written 2026-11-16. Checked on this Mac: SuiteCloud CLI 3.0.0 `--help` for `project:create`,
`file:list`, `account:setup` (interactive only), and the auth id format from `account:manageauth --list`. Not run end to
end on a clean machine; the Windows commands (`winget` ids, PATH refresh) are not tested here.
