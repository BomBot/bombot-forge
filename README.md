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
| **ns-bundle-to-sdf-repo** | turning an account-owned NetSuite bundle into a version-controlled SDF repo — "Convert to SDF Project" flow, cleaning up legacy auto-generated scriptids via Change ID, and the path-fidelity rules that keep a future deploy landing on the bundle's real live location |
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
- [ ] For `ns-bundle-to-sdf-repo` (has discipline rules): only one conversion so far — needs
      a second bundle conversion to confirm the Change ID `isvalid`-flag workaround and the
      "no plain branch-push trigger" CI gotcha generalize, not one-off
- [ ] Decide final layout for your setup (`skills/` plugin format here vs `.claude/skills/`
      + `.agents/skills/` mirror used by teibto-dev-standards)

## Public-repo hygiene

**Status: public since 2026-09-16.**

- [x] Drop customer-identifying labels/repo names from every skill and replace with generic
      wording (no customer name is spelled out anywhere in this repo, including past-tense
      changelog entries describing what was redacted — restating the redacted value in the
      "here's what we removed" note defeats the redaction, so don't)
- [x] Keep only a generic `<ACCOUNT_ID>` / `<SCRIPT_ID>` template row in `ns-live-verify`;
      real per-account rows live only in `notes.private.md` (gitignored, not in this repo).
      TEIBTO's own SB2 (`4089685`) stays inline since it's not customer data
- [x] Generalize internal ticket references (`#221`, `WIP-transfer fan-out`, etc.)
- [x] Drop the plugin manifest's personal contact email — a GitHub profile link is enough
      attribution for a public repo
- [x] Squash git history — commits that had a real customer name / account id in their tree
      are gone from `origin/master`; current history starts clean
- [x] Flip visibility to public
- [x] Verified against the **live public repo** via `gh api repos/BomBot/bombot-forge/...`
      (not just a local grep) — a local-only check missed the changelog re-exposure above and
      the leftover contact email on the first pass

This repo has no SDF project of its own (no `project.json`/`manifest.xml`), so a permission-
tuning pass here should skip gating `suitecloud` subcommands — they don't apply and add no
protection.

**Enforced automatically:** `.github/workflows/redaction-check.yml` greps every push/PR for
known-sensitive strings + any bare 7-8 digit number in tracked `.md`/`.py`/`.json` files and
fails CI on a match — see that file for the exact pattern. This replaces relying on
remembering to run a check by hand before adding new skill content.

## Provenance

Distilled 2026-09-15 from the TEIBTO-MFG-Manufacturing session covering: Handheld batch
deploy to a customer account, a costing-variance analysis (2-ท่อน, Summary Variance),
per-issue git migration, and UE undeploy+verify.
