---
name: setup-global-instructions
description: >-
  Use when setting up or syncing a machine's global `~/.claude/CLAUDE.md` to the team's NetSuite instructions, for a
  developer or a NON-DEV (consultant / analyst / support who works in the UI and does not write or deploy code). Asks
  one question (will you edit code?), detects Windows or macOS, builds the text from a redacted reference (dev as is;
  non-dev adds the no-SDF ban, the UI scope A/B/C and a narrow JS hotfix lane), then proposes a section-by-section merge
  with the machine's file (never a blind overwrite), asking only where they conflict. Non-dev also gets
  `permissions.deny` rules for `suitecloud`. Formerly two skills; `setup-global-instructions-nondev` now points here.
---

# Setup Global Instructions (dev or non-dev · compare + merge ~/.claude/CLAUDE.md)

**Skill version: `202611_03`**

`~/.claude/CLAUDE.md` is loaded into **every** session on the machine, so a bad edit has a huge blast radius: this
skill **builds, compares and proposes**; it never clobbers.

- Reference (redacted, ships in the plugin): `reference/global-CLAUDE.snapshot.md` (the dev text) and
  `reference/nondev-sections.md` (the non-dev sections). `scripts/build.py` assembles either role; shared sections are
  never copied, so a fix in the snapshot reaches both.
- Target (per machine, real): `~/.claude/CLAUDE.md`, plus `~/.claude/settings.json` for a non-dev.

## Iron rules (do not soften)

- **Never overwrite blind.** Diff, propose, back up first, show, wait for an explicit OK, then write. Changes apply on
  the next session.
- **Placeholders are not real values.** Only two are asked: `<Your Name>` and `<work-email>` — never invent them.
  `<OS>` is filled from detection, not asked.
- **Keep the target's own extra sections** (machine-local) — except, for a non-dev, one that contradicts the ban.
- **Never weaken the non-dev ban while merging.** If the target has its own version of "ห้ามใช้ SDF", show both; the
  default is the reference's. Loosening it is the user's decision, stated in chat.
- **For a non-dev, the text and the deny rules are a pair.** Don't propose one without the other, and say plainly the
  rules are a fence (see *What was verified*).

## How to ask the user

A choice is never buried in a paragraph: bullets first (**Pros · Cons · Best when**, at most three short lines each,
your recommendation in one line), then an `AskUserQuestion` picker as the last thing in the message (recommended
option first, max 4 options, one decision per question, max 4 questions per call). No picker → a numbered list in
chat, and wait. Never pick for the user, never treat silence as consent, and **don't ask what you can detect or what
was already answered** (e.g. the role from `setup-init`).

The only questions this skill asks:

1. **Role** (skip when `setup-init` passed it): *จะได้แก้โค้ด (SuiteScript) หรือ deploy ด้วย SDF ไหม* — **Yes, dev** /
   **No, I work in the NetSuite screens** / **Not sure** (treated as non-dev; switching later is a re-run).
2. **Name and work email** — only if the target does not already have them (look in its `@change` line first).
3. **Each conflicting section** (both sides have it and they differ): **Apply the merge** / **Show the diff first** /
   **Keep mine** — batched up to four per call. Identical, reference-only and target-only sections are not asked about.
4. Non-dev only: a target section that contradicts the ban (**Remove** (recommended) / **Keep**), and the deny rules
   (**Add** / **Not yet**).
5. The final write: **Write it** / **Not yet**.

## Flow

1. **Detect, don't ask:** OS (`uname -s` → macOS; PowerShell `$env:OS` → Windows; most office machines are Windows) and
   whether `~/.claude/CLAUDE.md` exists. Locate this skill's folder (in the installed plugin under
   `~/.claude/plugins/cache/bombot-forge/bombot-forge/<version>/skills/setup-global-instructions/`). Python is
   `python3` (Windows: `python` or `py`).
2. **Role** (question 1).
3. **Build:** `python3 <skill>/scripts/build.py --role <dev|nondev> --out <scratch dir>/global.md`. Exit 2 = the
   snapshot lost a section the non-dev recipe needs: stop and tell the maintainer.
4. **Fill** `<OS>` from step 1, and `<Your Name>` / `<work-email>` (question 2).
5. **Target missing** → propose creating it from the built text. **Target exists** → diff by `# H1` section:
   - identical → skip (say so)
   - reference-only → add (list them in one line, no question)
   - target-only → keep, say it is machine-local; for a non-dev, a section that tells Claude to run `suitecloud`,
     deploy or upload JS (e.g. `SDF Deploy`) → question 4. `Code conventions`, `Editing existing code`,
     `Coding agent` are harmless to a non-dev but unused: keep unless the user wants them gone.
   - both, differing → question 3; the proposed merge keeps the target's real values and machine-specific lines and
     pulls in the reference's newer guidance.
6. **Back up → show → confirm → write** `~/.claude/CLAUDE.md`:
   - macOS: `cp ~/.claude/CLAUDE.md ~/.claude/CLAUDE.md.bak.$(date +%Y%m%d_%H%M%S)`
   - Windows: `Copy-Item "$HOME\.claude\CLAUDE.md" "$HOME\.claude\CLAUDE.md.bak.$(Get-Date -Format yyyyMMdd_HHmmss)"`
7. **Non-dev — deny rules:** `build.py --deny-rules`; read `~/.claude/settings.json` (may not exist); merge into
   `permissions.deny` keeping every other key; list any `permissions.allow` entry mentioning `suitecloud` and offer to
   remove it; back up, show, confirm, write. After a restart, a harmless `suitecloud --version` must be **denied
   before it runs** (not "command not found").
8. **Finish:** tell the user to restart Claude Code. Non-dev: Claude in Chrome is required (level B changes are clicked
   in front of the user) → `setup-browser`; remind the maintainer that the real limit is the user's NetSuite role.

## Non-dev scope (in `nondev-sections.md`)

| Level | What | Rule |
|---|---|---|
| **A** read and analyse | pages, searches, Dev Bridge reads, explain, find usages, draft a spec for a dev | no confirmation; changes nothing |
| **B** no-code UI changes | Saved Search, Report, Dashboard, custom field / record, workflow, other no-code settings | sandbox **and production**, one chat OK per change, 6 fixed steps (plan naming account + environment → impact → record the old state → Claude clicks through **Claude in Chrome** in front of the user → compare → roll back if wrong) |
| **H** JS hotfix (one narrow exception) | edit an **existing** JS file for a real bug the site cannot wait on | only when the user says "hotfix"; 9 fixed steps (backup + sha256, greppable `HOTFIX-NODEV` comment, report + one OK incl. "a dev may overwrite this", Claude uploads via Claude in Chrome, verify by downloading back, roll back, a .md note for the dev) |
| **C** not through Claude | SDF, deploy, other JS, scripts / deployments, roles, import / mass update, financial transactions, subsidiary / accounting setup, deleting | the user does it by hand; Claude may draft the steps and check afterwards |

Decided by the maintainer 2026-10-01/02: B runs on production too, Claude clicks, field/record/workflow allowed, the H
lane added, and the "is the account live?" stop was cut.

## What was verified, and on what

| Claim | Status |
|---|---|
| `build.py` builds the non-dev text (12 sections, the shared ones byte-identical to the snapshot) and `--role dev` returns the snapshot as is; it refuses if a needed section disappears | **tested offline** (23 tests) |
| `permissions.deny` blocks the SDF CLI | **measured** with real `claude -p` in bypass mode against a fake `suitecloud`: direct call, `bash -c '…'` and `$(which suitecloud)` blocked |
| The rules cannot be evaded | **no — measured:** `s=suite; ${s}cloud file:list` ran. A fence, not a wall |
| A deny rule beats an existing allow rule for the same command | **not tested** — so the skill offers to remove those allow entries |
| A model follows the B / H steps and stops on an unexpected dialog; Claude in Chrome handles NetSuite dialogs and File Cabinet upload | **not tested** |
| The Windows backup command and paths | **not run** on Windows |
| Merge onto a real, diverged machine | **not run** end to end |

## Gotchas

- **Redaction CI** (public repo): no customer names, no bare 7–8 digit numbers in this folder. Check before committing:
  `grep -rnoE "[0-9]{7,8}" skills/setup-global-instructions/` must be empty.
- **The snapshot drifts** from the maintainer's real file; on a machine, its own file is the live truth — merge
  forward.
- **Don't name a plugin file exactly `CLAUDE.md`** (`claude plugin validate` warns it is not loaded as context) — hence
  `global-CLAUDE.snapshot.md` in `reference/`.
- A change to a shared section reaches non-dev machines on their next run. Dev-only text goes in a dev-only section
  (one the non-dev recipe drops).

## Updating (maintainer)

- "update the snapshot": copy the real `~/.claude/CLAUDE.md` into `reference/global-CLAUDE.snapshot.md`, then:
  - put `<Your Name>` / `<work-email>` / `<OS>` back in place of the real values;
  - keep the header;
  - drop sections that are personal to the maintainer's machine.
- Then run the redaction check above and `python3 scripts/test_build_offline.py`.
- Non-dev-only text: edit `reference/nondev-sections.md`. Add or drop a shared section: `RECIPE` in `scripts/build.py`
  (and the test's expected list). Keep snapshot headings stable — the recipe matches them by prefix.

## Status

202611_03 (2026-11-17):
- The dev and non-dev skills were merged into one, with a role question and OS detection.
- The snapshot was re-captured:
  - The Browser section was rewritten: bsk, then Claude in Chrome. cdp is history; auto-login follows the consent; `ns_write` is dev-only.
  - A new "เครื่องนี้" section (OS plus where to look for tools).
  - codegraph replaces graphify.
  - The project-folder-move note was dropped.
  - The placeholders are down to name, email and OS.
- Not run end to end on a clean machine or on Windows.
