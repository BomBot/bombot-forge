---
name: setup-global-instructions
description: >-
  Use when setting up or syncing a machine's global `~/.claude/CLAUDE.md` to match BomBot's
  canonical NetSuite-dev instructions — on a fresh machine, or to reconcile drift between
  machines. Compares the bundled reference snapshot against the machine's existing global
  CLAUDE.md and proposes a section-by-section merge (never a blind overwrite). The reference is
  redacted; real customer/email/path values are filled per-machine.
---

# Setup Global Instructions (compare + merge ~/.claude/CLAUDE.md)

**Skill version: `202609_01`**

Bring a machine's **global** `~/.claude/CLAUDE.md` in line with the canonical NetSuite-dev
operating instructions, kept here as a redacted snapshot at
`reference/global-CLAUDE.snapshot.md`. This file is loaded into **every** session on the
machine, so a bad edit has a huge blast radius — the skill **compares and proposes**, it never
clobbers.

- Reference (redacted, in this repo): `reference/global-CLAUDE.snapshot.md`
- Target (per machine, real): `~/.claude/CLAUDE.md`
- The reference is a **point-in-time snapshot**. When BomBot changes the real global CLAUDE.md,
  it's re-captured (redacted) on request — see *Updating the snapshot*.

## Iron rules (do not soften)

- **Never overwrite `~/.claude/CLAUDE.md` blind.** Always diff the reference against what's on
  the machine and propose a merge. The target may hold machine-specific or newer content the
  snapshot doesn't. Back it up first: `cp ~/.claude/CLAUDE.md ~/.claude/CLAUDE.md.bak.$(date +%Y%m%d_%H%M%S)`.
- **Placeholders are NOT real values.** The reference redacts customer/personal identifiers to
  `<Your Name>`, `<work-email>`, `<personal-gmail>`, `<PROJECT>`, `<qa-project>`. Fill these
  from the user's own values on that machine — **ask if unknown, never invent** an email, a
  customer name, or a path (Accuracy rule).
- **Merge by section, keep the target's extras.** Diff on `# H1` headings. Never drop a section
  the target has but the reference lacks — it's likely that machine's own addition.
- **Confirm before writing.** Show the proposed merged result (or a diff) and wait for an
  explicit OK before writing `~/.claude/CLAUDE.md`. Changes apply on the next session start.

## Flow

1. **Read both** — `reference/global-CLAUDE.snapshot.md` (bundled) and `~/.claude/CLAUDE.md`
   (may not exist yet).
2. **Target missing** → propose creating it from the reference, with every placeholder listed
   for the user to fill. Don't write until they're filled or explicitly deferred.
3. **Target exists** → diff **section by section** (`# H1` heading = one section):
   - identical → skip (say so, don't churn it)
   - reference-only section → propose adding it
   - target-only section → **keep as-is**, note it's machine-local
   - both but differing → show both sides, propose a merge that keeps the target's real values
     and machine-specific lines while pulling in the reference's newer guidance
4. **Fill placeholders** from the user's private values (ask when unknown). Never paste a real
   customer name / account id **into the snapshot** — only into the machine's `~/.claude/CLAUDE.md`.
5. **Back up → show → confirm → write** the target. Then note it takes effect next session.
6. If the machine has no bombot-forge checkout, the reference still ships inside the installed
   plugin at `~/.claude/plugins/.../setup-global-instructions/reference/global-CLAUDE.snapshot.md`
   — read it from there.

## Gotchas

- **Redaction CI blocks real identifiers.** bombot-forge is public; its CI (see
  `.github/workflows/redaction-check.yml`) fails on the known-redacted customer name or any bare
  7-8 digit number. The snapshot must stay redacted — real customer/account values live only on
  the machine's own `~/.claude/CLAUDE.md`, never back in the snapshot.
- **The snapshot drifts.** It's frozen at capture time; the machine's real file may be newer.
  When they disagree, the machine's file is the live truth for that machine — merge forward,
  don't assume the snapshot wins.
- **Don't name a plugin file exactly `CLAUDE.md`.** `claude plugin validate` warns that a
  plugin-root `CLAUDE.md` isn't loaded as context — that's why the snapshot is named
  `global-CLAUDE.snapshot.md` in a `reference/` subfolder, so it's inert data, not auto-loaded.

## Updating the snapshot (maintainer)

When BomBot updates the real `~/.claude/CLAUDE.md` and says "update the snapshot": copy the new
content into `reference/global-CLAUDE.snapshot.md` and re-apply the redaction map, then verify
it's clean before committing.

| Real value | Placeholder |
|---|---|
| work email (e.g. `name@company.com`) | `<work-email>` |
| personal gmail | `<personal-gmail>` |
| author full name | `<Your Name>` |
| a customer project folder name | `<PROJECT>` |
| the repo holding the canonical `cdp.py` | `<qa-project>` |

Verify before commit — the repo's redaction CI must pass on this folder. It guards the
known-redacted customer name and any bare 7-8 digit id (exact patterns in
`.github/workflows/redaction-check.yml`). A quick local number check that must return nothing:
```bash
grep -rnoE "[0-9]{7,8}" skills/setup-global-instructions/
```
Then eyeball the snapshot for any customer name / email you forgot to placeholder. (`bombot`
in `/Users/bombot/...` paths is kept — it's BomBot's public handle, not a secret.)

## Quick reference

| Need | Do |
|---|---|
| Compare this machine | read `reference/global-CLAUDE.snapshot.md` vs `~/.claude/CLAUDE.md`, diff by `# H1` |
| Back up target | `cp ~/.claude/CLAUDE.md ~/.claude/CLAUDE.md.bak.$(date +%Y%m%d_%H%M%S)` |
| Placeholders to fill | `<Your Name>` · `<work-email>` · `<personal-gmail>` · `<PROJECT>` · `<qa-project>` |
| Reference (installed plugin) | `~/.claude/plugins/.../setup-global-instructions/reference/global-CLAUDE.snapshot.md` |
| Re-snapshot check | redaction CI passes + `grep -rnoE "[0-9]{7,8}" skills/setup-global-instructions/` empty |

## Status

v0.1 draft — snapshot captured 2026-09-18 from BomBot's machine, redacted (customer names,
emails). Not yet pressure-tested per `superpowers:writing-skills`. Likely to need: a real
second-machine merge to confirm the section-by-section flow handles a target that has genuinely
diverged (not just an empty/fresh machine).
