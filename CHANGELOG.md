# Changelog

Versioning (matches Teibto-Claude-Skills convention):

- **Plugin** = semver (`plugin.json` `version`) + git tag `vX.Y.Z`.
- **Each skill** = `YYYYMM_##` version string in its `SKILL.md` (line under the H1), also
  listed in `plugin.json` description.
- **Commit message** carries both when a skill changes: `type(skill): summary (SKILLVER / PLUGINVER)`
  e.g. `feat(ns-live-verify): add scriptdeployment recipe (202609_02 / 0.2.0)`.
- Bump the skill's `YYYYMM_##` on any skill-body change; bump plugin semver + tag on release.

---

## v0.3.0 — 2026-09-16

- `ns-bundle-to-sdf-repo` **202609_01** (new skill) — distilled from converting bundle 381777
  ("TEIBTO - Custom Button", `4089685-sb2`/`4089685-sb1`) into `Teibto/TEIBTO-CustomButton`.
  Covers: the "Convert to SDF Project" flow + signed-URL download, cleaning up legacy
  auto-generated scriptids via the built-in Change ID tool (leading-underscore trap, the
  `isvalid`-flag submit-blocker workaround, verify-by-URL not by label text), why
  `FileCabinet/` paths must stay unrenamed for deploy path-fidelity, and infra gotchas hit
  along the way (classic-UI megamenu AJAX discovery, `read:packages` scope, package-version
  lag vs repo tags, first-push Actions discovery, `gh api -f/-F` nested-JSON flattening,
  org-level secret-scanning plan lock).

## v0.2.2 — 2026-09-16

Prep for flipping this repo to public.

- `ns-live-verify` **202609_03** — moved the real Prod-A account/script id out of the tracked
  skill file into `notes.private.md` (new, gitignored); `SKILL.md` now carries
  `<PROD_ACCOUNT_ID>` / `<PROD_SCRIPT_ID>` placeholders instead. TEIBTO's own SB2 id stays
  inline (not customer data).
- Restored the "Dev Bridge" term in README/`plugin.json` — confirmed real, points at a
  private repo under `github.com/Teibto`; safe to name since outsiders can't open that repo
  either way.
- README: replaced the "before making public" checklist with a "Public-repo hygiene" note,
  and flagged that **pre-existing git history still contains the real values** (pre-dates this
  pass) — a public flip should squash/rewrite history first, not just clean the current tree.

## v0.2.1 — 2026-09-16

Redaction / hygiene pass from `teibto-redteam` review of the auto-mode-setup permission
proposal (found real customer name + account ids committed, and a misapplied `suitecloud`
permission scope for a repo that has no SDF project of its own).

- `ns-live-verify` **202609_02** — dropped the customer name label (`Srifa` → `Prod-A`);
  numeric account/script ids kept as-is (repo is still private and the recipes are in real
  use) — see README's new "Before making this repo public" checklist for the follow-up pass.
- `ns-record-write` **202609_02** — standardized example `--account` across `SKILL.md` and
  `ns_write.py` to TEIBTO's own SB2 (`4089685_SB2` / `4089685`), replacing an unlabeled
  account id (`8158655`) that wasn't confirmed as TEIBTO's own.
- `ns-sdf-prod-deploy` **202609_02** — generalized its status footer (dropped customer name).
- README/CHANGELOG — generalized internal ticket references (`#221`, `WIP-transfer fan-out`);
  removed the unverified "Dev Bridge" term (not found anywhere in `ns-live-verify`'s actual
  content) from the skill description in README and `plugin.json`.

## v0.2.0 — 2026-09-15

Renamed plugin `teibto-ns-delivery` → **`bombot-forge`** (BomBot's personal NetSuite skills).
Added a record-write skill.

- `ns-record-write` **202609_01** — scoped record write via `ns_write.py` (submit + save
  modes, structured args only, account guard, dry-run default, before→after read-back).
  Includes the exact `permissions.allow` line and `validate-setup.sh` to confirm each machine
  is set up the same.

## v0.1.0 — 2026-09-15

Initial scaffold. Three skills distilled from a real TEIBTO-MFG-Manufacturing session
(Handheld batch deploy, a costing-variance analysis, UE undeploy+verify).

- `ns-sdf-prod-deploy` **202609_01** — import-compare-confirm flow, temp-authid trap,
  scoped deploy, smoke-test, prod guardrails.
- `ns-live-verify` **202609_01** — dbgQuery recipes (SB2 3171 / Prod-A, see `notes.private.md`), SuiteQL
  gotchas, script-deployment / GL / field verification, login handling.
- `verified-decision-brief` **202609_01** — verify as-is from code+live, comparison/GL
  worked examples, who-answers tags, redaction for sharing.

**Status:** v0.1 drafts — not yet TDD/pressure-tested (see README checklist).
