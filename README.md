# bombot-forge

BomBot's personal Claude Code plugin — NetSuite delivery skills, forged from real TEIBTO
MFG work (customer SDF deploys, a costing-variance analysis, live verification, a production
fan-out fix).

## Skills

| Skill | Use when |
|---|---|
| **ns-sdf-prod-deploy** | deploying SDF changes to a live/prod account; import-compare before deploy; per-round prod deploy (temp-authid trap, scoped deploy, smoke-test) |
| **ns-live-verify** | reading/verifying live NetSuite state read-only via Dev Bridge / dbgQuery (accounts, GL, fields, script deployment) — confirm real state, don't assume |
| **ns-record-write** | writing a field to a live record from a logged-in browser session — scoped `submitFields` helper (structured args, account guard, dry-run), the `permissions.allow` line, and a per-machine setup validator |
| **verified-decision-brief** | turning an informal requirement into a stakeholder decision doc grounded in verified as-is (code + live), incl. redaction for sharing |

## Structure

```
bombot-forge/
  .claude-plugin/plugin.json     # plugin manifest
  skills/<name>/SKILL.md         # one folder per skill
  README.md
```

Add-per-skill support files (`references/`, `scripts/`) go inside each skill folder when a
section grows past ~100 lines or a reusable script emerges.

## Status: v0.1 drafts — NOT yet TDD-tested

These skills are first drafts distilled from one session's real work. Per
`superpowers:writing-skills`, a skill isn't done until it's been pressure-tested:

- [ ] Run baseline subagent scenarios WITHOUT each skill; capture rationalizations/gaps
- [ ] Verify agents comply/apply correctly WITH the skill
- [ ] For `ns-sdf-prod-deploy` (has discipline rules): close loopholes, add rationalization table
- [ ] For `ns-live-verify` (reference): test retrieval — can an agent find + apply the right recipe
- [ ] For `ns-record-write` (has discipline rules + script): verify dry-run-first + account-guard
      compliance; confirm `validate-setup.sh` passes on all 3 machines
- [ ] For `verified-decision-brief` (technique): test application to a fresh requirement
- [ ] Decide final layout for your setup (`skills/` plugin format here vs `.claude/skills/`
      + `.agents/skills/` mirror used by teibto-dev-standards)

## Public-repo hygiene

`ns-live-verify`'s "Prod-A" row uses `<PROD_ACCOUNT_ID>` / `<PROD_SCRIPT_ID>` placeholders —
the real values live in `notes.private.md` (gitignored, not in this repo; not distributed with
it). Substitute them locally before running anything against that account. TEIBTO's own SB2
(`4089685`) is left inline since it's not customer data.

Before flipping visibility again (or forking this into a new repo), re-run:
`grep -rniE "srifa|[0-9]{7,8}" --include='*.md' --include='*.py' .` — should return nothing
outside `notes.private.md` (which git ignores anyway) and this checklist's own example command.

This repo has no SDF project of its own (no `project.json`/`manifest.xml`), so a permission-
tuning pass here should skip gating `suitecloud` subcommands — they don't apply and add no
protection; the grep check above is the actual guard for this repo.

**Note:** git history predating this pass (commits before the `notes.private.md` rework)
still contains the real account/script id and the original "Srifa" label in their diffs —
`git log -p` on the old commits exposes them even though the current files are clean. Squash
or rewrite history before going public if that matters for this repo.

## Provenance

Distilled 2026-09-15 from the TEIBTO-MFG-Manufacturing session covering: Handheld batch
deploy to a customer account, a costing-variance analysis (2-ท่อน, Summary Variance),
per-issue git migration, and UE undeploy+verify.
