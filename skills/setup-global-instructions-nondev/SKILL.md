---
name: setup-global-instructions-nondev
description: >-
  Use when setting up or syncing the global `~/.claude/CLAUDE.md` of a NON-DEV NetSuite machine (a
  consultant, analyst or support person who works through the UI and does not write or deploy code): no SDF
  at all, no deploy of XML/JS, no upload of JS; Claude may read, analyse, and make no-code UI changes
  (saved searches, reports, custom fields/records, workflows) one confirmed change at a time through Claude
  in Chrome, plus one narrow lane for an urgent on-site JS hotfix (backup, comment, confirmation, verification, dev note). Builds the text from the dev snapshot plus non-dev sections, proposes a section-by-section
  merge (never a blind overwrite) and adds `permissions.deny` rules for `suitecloud`. For a developer
  machine use `setup-global-instructions`.
---

# Setup Global Instructions — non-dev (read-only, no SDF, no deploy)

**Skill version: `202609_08`**

The dev skill `setup-global-instructions` writes the instructions of someone who deploys code. This one is for
someone who must **not**: the machine's `~/.claude/CLAUDE.md` forbids the SDF CLI entirely, forbids deploying
XML/JS and uploading JS, and tells Claude to work by **reading pulled files, the Dev Bridge and the browser**.
Because a sentence in CLAUDE.md is advice and not a barrier, the skill also proposes `permissions.deny` rules.

**What the user can and cannot do through Claude** (section "ขอบเขตงานผ่าน UI" of the built text):

| Level | What | Rule |
|---|---|---|
| **A** read and analyse | look at pages, run searches, read via the Dev Bridge, explain why a search is wrong, find where something is used, draft a spec for a dev | no confirmation needed; changes nothing |
| **B** no-code UI changes | Saved Search, Report, Dashboard, custom field, custom record, workflow, other no-code settings the user names | allowed in sandbox **and production**, **one chat OK per change**, then 6 fixed steps: plan (naming the account and environment) and wait for the OK → impact check → record the old state → Claude clicks through **Claude in Chrome** in front of the user → compare before/after → roll back if it is wrong |
| **H** JS hotfix (one narrow exception) | edit an **existing** JS file on the account to fix a real bug the site cannot wait on | only when the user says "hotfix" in chat; size by judgement (no line limit) — a big change is better written as a .md for the dev, and the user is told how big it is and decides; **9 fixed steps**: take the file from the account → back it up (+ sha256) → edit a local copy with a greppable `HOTFIX-NODEV` comment (why / what / original) → re-check the diff and syntax → report to the user (diff, size, checked / inferred / not looked at, risk, rollback, **"a dev may overwrite this file"**) and get one OK → Claude uploads through Claude in Chrome → verify by downloading it back and comparing sha256, reproducing the bug, reading the Execution Log → roll back from the backup if wrong → write a .md note for the dev |
| **C** Claude does not do it | SDF, deploy, upload/edit JS (except H), scripts and script deployments, roles/permissions, import and mass update, edit/delete financial transactions, change subsidiary/accounting setup, delete anything | **the user does it by hand**; Claude may draft the steps or spec and check the result afterwards |

Decided by the maintainer on 2026-10-01: B runs on production too (most accounts are still in implementation, not live),
Claude does the clicking (not the user), and custom fields/records/workflows are allowed. Added the same day: the H lane
("open a small gap for urgent fixes on site"), **Claude uploads the file itself** through Claude in Chrome, the size limit is
"by judgement" with the user always told and deciding, and level C is done by hand by the user. The "is the account live?" stop that was added on 2026-10-01 was **cut on 2026-10-02** at the maintainer's request:
what remains before any change is the plan (account, environment, what, expected result) and one OK in the chat.

- Shared sections are **not copied**: `scripts/build_nondev.py` takes them verbatim from the dev snapshot
  (`../setup-global-instructions/reference/global-CLAUDE.snapshot.md`) and adds `reference/nondev-sections.md`.
  Fix a shared section once, in the dev snapshot, and both skills get it.
- Target (per machine, real): `~/.claude/CLAUDE.md` and `~/.claude/settings.json`.

## What was verified, and on what

| Claim | Status |
|---|---|
| `build_nondev.py` produces 9 sections (Role, Accuracy, Communication, Slack, the ban, way of working, Git, Session memory, Browser automation), the kept ones byte-identical to the dev snapshot, and refuses if a needed section disappears | **tested offline** (mutation-checked) |
| A `permissions.deny` rule set blocks the SDF CLI | **measured** with the real `claude -p` in `bypassPermissions` mode against a fake `suitecloud` that logs any real run: with no rule the command ran; with the rules, `suitecloud …`, `bash -c '…'` and `$(which suitecloud) …` did **not** run |
| The rules cannot be evaded | **no — measured:** `s=suite; ${s}cloud file:list` ran. Patterns match the command **text**; a name built from a variable, or an npm script whose text does not contain `suitecloud`, gets through. The rules are a fence, not a wall |
| A deny rule beats an existing allow rule for the same command (dev machines allow `suitecloud file:upload`) | **not tested** — so the skill proposes removing those allow entries too |
| The rules in the table above are what the maintainer chose | **decided** 2026-10-01 (production allowed with a per-change OK; Claude clicks via Claude in Chrome; field/record/workflow allowed); written into the built text and covered by offline tests |
| A model actually follows the 6 steps and stops where it should (unexpected dialog) | **not tested** — the text is advice, not enforcement. The real barrier is the user's **NetSuite role permissions**; check them for each non-dev user |
| Claude in Chrome completes a NetSuite UI customisation, and copes with NetSuite's native dialogs | **not tested** |
| A hotfix survives a later deploy by a dev | **it does not by itself** — a dev who deploys from the repo overwrites the account file and the fix is lost. The lane only reduces the risk (greppable tag, dev note, a warning to the user in the confirmation); it needs the user to tell the dev |
| "By judgement" keeps hotfixes small | **not enforced** — there is no line limit, so the protection is the report-and-decide step, not a rule a test can check |
| Claude in Chrome can upload a file into File Cabinet, replace the existing one so that scripts still point at it, and the download-back hash matches | **not tested** (the MCP has a file-upload tool; it was never tried on NetSuite) |
| `node --check` (or another syntax check) exists on a non-dev machine | **unknown** — the text says to report "syntax not checked" when there is no tool |
| The "pull files" channels named in the instructions (a project git repo, or a download from File Cabinet in the browser) match how this team really gets files | **assumption** — confirm with the maintainer |
| Merge onto a real, diverged non-dev machine | **not run** |

## Iron rules (do not soften)

- **Never overwrite `~/.claude/CLAUDE.md` or `settings.json` blind.** Diff, propose, back up first
  (`cp <file> <file>.bak.$(date +%Y%m%d_%H%M%S)`), show, wait for an explicit OK, then write. Changes apply on the next session.
- **Never weaken the ban while merging.** If the target has its own version of the "ห้ามใช้ SDF" section, show both
  side by side; the default is the reference's. Removing or loosening it is the user's decision, stated in chat.
- **The text and the deny rules are a pair.** Don't propose one without the other, and say plainly that the rules
  are a fence (see the table).
- **Placeholders are not real values.** `<Your Name>`, `<work-email>`, `<personal-gmail>`, `<PROJECT>`, `<qa-project>`
  come from the user on that machine — ask if unknown, never invent.
- **Keep the target's own extra sections** — except one that contradicts the ban (next section).

## How to ask the user (at every decision point in this skill)

A choice is never buried in a paragraph. Do these, in this order:

1. **Bullets first.** One block per option, at most three short lines each: **Pros · Cons · Best when**.
   No paragraphs, no "it depends" prose. Say which option you recommend and why in one line.
2. **Then a picker — the last thing in your message.** Use the `AskUserQuestion` tool: a short label, a
   one-line description that carries the key trade-off, the recommended option first and marked
   "(Recommended)". At most 4 options per question, one decision per question, at most 4 questions per
   call (split further decisions into the next round). Use multi-select only when the choices are not
   exclusive. The user can always type their own answer via "Other".
3. **No picker available?** Ask the same thing as a numbered list in chat, and wait. Never pick for the user and
   never treat silence as consent.
4. Don't ask what the look-first step already showed, and don't re-ask something already answered.

Decision points: each section that differs (**Apply** / **Show the diff first** / **Keep mine**), each
conflicting section (**Remove** / **Keep**), the deny rules (**Add** / **Not yet**), the final writes.

## Flow

1. **Build the reference text:** `python3 <this skill>/scripts/build_nondev.py --out <scratch dir>/nondev.md`
   (find the script inside the installed plugin, e.g. under `~/.claude/plugins/cache/bombot-forge/bombot-forge/<version>/skills/`).
   Exit 2 means the dev snapshot lost a section this recipe keeps — stop and tell the maintainer.
2. **Read** `~/.claude/CLAUDE.md` (may not exist). Missing → propose creating it from the built text with the
   placeholders listed; don't write until they are filled or explicitly deferred.
3. **Diff by `# H1` section:**
   - identical → skip, say so
   - reference-only → propose adding
   - target-only → keep, note it is machine-local — **except** a section that contradicts the ban:
     `SDF Deploy`, and anything telling Claude to run `suitecloud`, deploy, or upload JS. Show it and ask
     **Remove** / **Keep** (recommend Remove). `Code conventions`, `Editing existing code`, `Coding agent` are
     harmless to a non-dev but unused: keep unless the user wants them gone.
   - both, differing → show both sides, propose a merge that keeps the target's real values
4. **Fill placeholders**, then **back up → show → confirm → write** `~/.claude/CLAUDE.md`.
5. **Deny rules (`~/.claude/settings.json`):** print `build_nondev.py --deny-rules`; read the file (may not exist).
   Merge into the existing `permissions.deny` array (create it if absent), keep every other key, back up, show, confirm,
   write. Also list any `permissions.allow` entry that mentions `suitecloud` and offer to remove it (deny is expected to
   win, but that was not tested). Tell the user to restart Claude Code.
6. **Verify after the restart:** ask Claude to run a harmless `suitecloud --version`. Expected: a permission denial
   **before** the command runs (not "command not found"). Then remind the user of the honest limit: a name built from
   a variable or an npm script can slip past a text pattern; the CLAUDE.md ban covers what the rule cannot.
7. **Offer the tools this workflow leans on:** `setup-browser` — for a non-dev machine **Claude in Chrome (its Step 3) is
   required**, because level B changes are clicked through it in front of the user (not through `bsk`, which works in a background window the user cannot see); the Dev Bridge trial covers the
   read side — and `setup-plugins` if the user wants the team's plugins. Don't start them without a yes. Also remind the
   maintainer that the real limit on what a user can change is their NetSuite role, not this text.

## Gotchas

- **Redaction CI blocks real identifiers** (public repo): no customer names, no bare 7–8 digit numbers in this folder.
- **The dev snapshot is a point-in-time copy**, so the built text is too; the machine's own file is the live truth.
- **Don't name a plugin file exactly `CLAUDE.md`** — the built text is written to a scratch file or the target, never
  into the plugin.
- Anything the maintainer changes in the dev snapshot's kept sections reaches non-dev machines on their next run —
  that is intended; if a change is dev-only, put it in a dev-only section (one this recipe drops).

## Updating (maintainer)

- Non-dev-only text: edit `reference/nondev-sections.md`, run `python3 scripts/test_build_nondev_offline.py`.
- Add or drop a shared section: change `RECIPE` in `scripts/build_nondev.py` (and the test's expected list).
- Keep the dev snapshot's section headings stable: the recipe matches them by prefix and the build fails if one is missing.

## Status

v0.1 draft — assembler and tests run on macOS; the deny rules measured with a fake binary; the A/B/C scope decided by
the maintainer but never exercised end to end (no run of level B or of a hotfix on a real account, no check that Claude in Chrome
handles NetSuite dialogs or file uploads); not yet applied on a real non-dev machine, and the "pull files" channels are the maintainer's
to confirm.
