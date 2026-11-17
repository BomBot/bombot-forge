---
name: ns-sdf-prod-deploy
description: >-
  Use when deploying NetSuite SDF customizations (scripts or objects) to a live or
  production account, running a per-round prod deploy, or importing files/objects from a
  target account to compare before deploying. Covers the import-compare-confirm flow and
  the temp defaultAuthId swap.
---

# NetSuite SDF Prod Deploy (import-compare-confirm)

**Skill version: `202611_01`**

Safe delivery of SDF changes to a live account (SB / prod). The account is real customer
data — every step is reversible or gated. Optimized for the TEIBTO multi-account setup
where one repo deploys to several accounts via `defaultAuthId`.

## Iron rules (do not soften)

- **Never an unscoped `suitecloud project:deploy`** — with the project's full `deploy.xml` it pushes every
  object. JS goes by `file:upload`; objects only by `project:deploy` with a `deploy.xml` trimmed to the changed
  objects (step 3).
- **Never leave `project.json` on another account's authid.** The swap and its restore run in **one** shell block
  with a `trap` (below), and every SDF command starts by reading `defaultAuthId`.
- **Sandbox (SB2/dev) = read-only for OBJECT deploy** — SDF object deploy to SB risks
  dropping config. Create new fields/objects **via the UI**; deploy only scripts (JS) there.
- **Prod object/script deploy = per-round approval** — propose the exact plan (files, method,
  authid) and wait for an explicit "go" before the irreversible step.
- **Import-compare BEFORE prod, always** — pull the target's live copy and diff, in case
  someone changed it. Existing-but-different → merge only the delta, never overwrite the whole.
- **When reporting, say "uploaded"** (not "deployed") for `file:upload`.

## Flow

1. **Verify local state** — target files committed / match HEAD (`git status --porcelain -- <files>`).
2. **Import-compare** — temp-swap authid to target → `file:import`/`object:import` the same
   paths → `git diff` vs repo HEAD → confirm the target's `+` lines are all OLD code the repo
   refactored past (not someone's live hotfix) → `git checkout --` to restore the repo version.
3. **Scope** — `deploy.xml` lists only changed objects; trim `manifest.xml` to that scope's
   deps; `project:validate --server` against target (read-only) until it passes. For objects, also
   `project:deploy --dryrun` (a preview; flag checked on CLI 3.0.0) and show its list in the proposal.
4. **Propose + wait for "go"** (prod). Name the account and the authid out loud, and check the authid belongs to
   that account: it is in `suitecloud account:manageauth --list`, and the team name says so (`<ACCOUNT>-Adm-Prod`,
   `<ACCOUNT>_SB1-Adm-Sand`; see `setup-cli`). A name that does not match the account → stop and ask.
5. **Deploy** — one block: swap authid → `file:upload` (or scoped `project:deploy`) → restore (the `trap` does it
   even when the command fails).
6. **Verify + smoke-test** on the target right away:
   - JS: `file:import` the same paths (swap block again) → `git diff -- <paths>` must be empty (the account now has
     exactly the repo's file) → `git checkout -- <paths>`.
   - Script record / deployment status: `ns-live-verify` (`ns_read.py query … FROM scriptdeployment`), no UI needed.
   - Then load the changed feature (see *Smoke-test*).
7. **Restore** `deploy.xml`/`manifest.xml` to baseline — temporary config is **never committed**.

## Temp-authid swap (the critical pattern)

`file:import` / `file:upload` / `object:import` / `object:list` / `project:validate` / `project:deploy` have **no
`--authid`** (checked on SuiteCloud CLI 3.0.0 `--help`) — they use `defaultAuthId` in `project.json`. Swap only that
key, act, and restore in the SAME block; the `trap` restores even when the command fails:

```bash
cd <project-root>
( set -e
  BAK=$(mktemp); cp project.json "$BAK"
  trap 'cp "$BAK" project.json; rm -f "$BAK"; echo "restored: $(python3 -c "import json;print(json.load(open(\"project.json\"))[\"defaultAuthId\"])")"' EXIT
  python3 - "<TARGET-AUTHID>" <<'PY'
import json, sys
p = "project.json"; d = json.load(open(p)); d["defaultAuthId"] = sys.argv[1]; json.dump(d, open(p, "w"), indent=2)
PY
  suitecloud file:upload --paths "/SuiteScripts/.../<file>.js"
)
```

Tested 2026-11-17 with a fake `project.json` and a failing command: the authid was restored, other keys kept.
`mktemp` (not a fixed `/tmp` name) so two sessions cannot restore each other's file.

Windows (PowerShell; not run on Windows yet):

```powershell
$bak = New-TemporaryFile; Copy-Item project.json $bak -Force
try {
  $j = Get-Content project.json -Raw | ConvertFrom-Json; $j.defaultAuthId = '<TARGET-AUTHID>'
  $j | ConvertTo-Json | Set-Content project.json
  suitecloud file:upload --paths "/SuiteScripts/.../<file>.js"
} finally { Copy-Item $bak project.json -Force; Remove-Item $bak; "restored: " + (Get-Content project.json -Raw | ConvertFrom-Json).defaultAuthId }
```

**Before any SDF command** (also outside this flow): read `defaultAuthId`. If it names an account other than the one
you mean (for example a prod authid left by an interrupted run), restore it first and tell the user.

## Gotchas (hit in production)

- **The auto-mode classifier may block the swap block** (a prod mutation wrapped in a trap). Don't split it into
  separate calls to get past it: a failure between the calls leaves `project.json` on the prod authid. Ask the user
  to approve the one block (or run it in their terminal). If it must be split, the restore call runs **whatever
  happened** in between, then read `defaultAuthId` back.
- `object:import` needs `--destinationfolder`. SDF export **misses** List/Record join fields
  and some forms → `object:import` false-negatives; verify with "does the target feature use
  that field/join already" or `getFields()`, not by SDF export alone.
- **Whole-record deploy to non-OneWorld = drops subsidiary field** → create field via UI.
- **Translated labels (translation collection) can't deploy cross-project** ("terms must be
  in-project") → if the field is optional, add it via UI on the target.
- `<parentsubtab>` / deployment-audience role a record/script references → declare in
  `manifest` dependency **only if the target has it**; a dep the target lacks fails validate → trim it.
- Roles differ per account — a role internal-id valid on SB may be inactive/missing on prod
  (`Invalid audslctrole reference key`) → point at `ADMINISTRATOR` or the target's real role.

## Smoke-test

Load the changed feature on the target and confirm it renders / runs with no error. For a
JS-only upload the main risk is a syntax error breaking the page — a clean boot rules that
out. UI behaviour that needs a real human interaction (popups, transient-activation) is
verified by a **real browser click**, not automation (see `ns-live-verify` for read checks).

## Quick reference

| Action | Command |
|---|---|
| list authids | `suitecloud account:manageauth --list` |
| import to compare | `suitecloud file:import --paths "<path>"` (after authid swap) |
| upload JS | `suitecloud file:upload --paths "<path>"` (inside the swap block) |
| preview an object deploy | `suitecloud project:deploy --dryrun` (inside the swap block) |
| validate on target | `suitecloud project:validate --server` (uses defaultAuthId) |
| restore after import | `git checkout -- "<path>"` |

## Status

v0.1 draft — extracted from a real Handheld batch → customer prod deploy. Pressure-test with
subagent scenarios (see superpowers:writing-skills) before treating the Iron rules as bulletproof.
202611_01 (2026-11-17): one trap block for the authid swap (the old "split into calls" gotcha removed),
key-only edit with `mktemp`, a check of `defaultAuthId` before any SDF command, `--dryrun` preview, authid-to-account
check, upload verified by importing it back, Windows commands (untested). CLI flags re-checked on 3.0.0.
