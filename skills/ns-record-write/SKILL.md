---
name: ns-record-write
description: >-
  Use when writing to a live NetSuite record from a logged-in QA-browser session (updating a
  field, fixing a bad value, a scoped submitFields or load/save), instead of allow-listing
  raw `cdp.py eval`. Covers the scoped `ns_write.py` helper (structured args only, submit +
  save modes, account guard, dry-run default), the exact `permissions.allow` line it needs,
  and a validator that checks each machine is set up the same way.
---

# NetSuite Record Write (scoped ns_write helper)

**Skill version: `202609_02`**

Writing to a live NetSuite record from a logged-in browser tab. The **only** sanctioned
write channel here is `scripts/qa/ns_write.py` — a helper that takes **structured args**
(`--type`, `--id`, `--set field=value`) and runs the write in the tab. It does NOT accept
free-form JS, so allow-listing this one script is safe where `Bash(...cdp.py eval:*)` would
hand over full unrestricted browser control.

Two modes, one script:
- `--mode submit` (default) — `N/record.submitFields` (fast body-field update; no sourcing / no user-event scripts)
- `--mode save` — `record.load → setValue → save` (full save; sourcing + UEs fire; add `--dynamic` for sourcing during load)

## Iron rules (do not soften)

- **Never allow-list raw `cdp.py eval`.** That approves ANY JS on ANY logged-in account
  (reads password fields, any mutation). Allow-list only the fixed, auditable helper script.
- **Prod write = explicit instruction, per record.** A write is irreversible-ish; the user
  must have asked for THIS write. The helper defaults to dry-run — never pass `--confirm`
  unless the user asked to write.
- **Account guard is mandatory.** The helper aborts if the live tab's `runtime.accountId`
  ≠ `--account` (checked before the write AND again inside the write callback). Always pass
  the account you intend, so a wrong tab / wrong login cannot be written by accident.
  Re-read whether it names sandbox vs prod before `--confirm`.
- **Dry-run first, always.** Run without `--confirm`, read the BEFORE values + the PLAN, then
  re-run with `--confirm`. Verify the AFTER read matches intent.
- **Prefer `submit` over `save`.** submitFields is narrower (body only, no side effects).
  Use `save` only when you need sourcing or user-event scripts to fire. Sublist edits are
  NOT supported yet — do not force them through `--set`.
- **No credentials, ever.** The browser session cookie authenticates the write.

## Setup (per project + per machine)

1. **Script (per project, via git):** the helper lives at `scripts/qa/ns_write.py` in the
   project repo. The canonical copy is in this skill at `scripts/ns_write.py` — copy it into
   a new project once, then commit it so all machines get the same file through git:
   ```bash
   mkdir -p scripts/qa
   cp "<this-skill>/scripts/ns_write.py" scripts/qa/ns_write.py
   ```
2. **Allow rule (per machine, personal):** add this ONE line to the project's
   `.claude/settings.local.json` (not committed — so it is per-machine and must be added on
   each of your computers). Merge into the existing `permissions.allow` array, don't overwrite:
   ```json
   "Bash(python3 scripts/qa/ns_write.py:*)"
   ```
   A known-good full allow block for NetSuite work (write helper + read-only SDF; note
   `project:deploy` is deliberately NOT listed so prod deploy stays gated):
   ```json
   "permissions": {
     "allow": [
       "Bash(xxd:*)",
       "Bash(python3 scripts/qa/ns_write.py:*)",
       "Bash(npx suitecloud file:upload:*)",
       "Bash(npx suitecloud project:validate:*)",
       "Bash(npx suitecloud object:import:*)"
     ]
   }
   ```
3. **cdp.py + QA Chrome:** the helper drives `cdp.py` on CDP port 9333 (see
   `netsuite-qa-browser`). The QA Chrome must be up and logged into the target account.

> Path form matters: always invoke as `python3 scripts/qa/ns_write.py ...` from the project
> root (relative). The allow rule matches that literal prefix; an absolute path will NOT match.

## How to call

```bash
# 1) DRY-RUN (safe) — shows current values + the plan, writes nothing
python3 scripts/qa/ns_write.py \
    --account 4089685_SB2 \
    --type customrecord_mfg_completionusage --id 16525 \
    --set custrecord_mfg_usagecompletion=2935624

# 2) WRITE via submitFields — same command + --confirm (only after the user asked)
python3 scripts/qa/ns_write.py \
    --account 4089685_SB2 \
    --type customrecord_mfg_completionusage --id 16525 \
    --set custrecord_mfg_usagecompletion=2935624 --confirm

# 3) full load/save (fires sourcing + UEs); --dynamic loads in dynamic mode
python3 scripts/qa/ns_write.py --account 4089685_SB2 --mode save \
    --type salesorder --id 12345 --set memo="fixed" --confirm

# multiple fields: repeat --set. pin a tab with --tab <CDP_TARGET_ID> when several NS tabs open.
```

- `--account` = expected `runtime.accountId` (`4089685_SB2` sandbox, `4089685` prod). Mismatch → abort.
- Reads BEFORE + AFTER via `N/search.lookupFields` so you get a before→after diff for free.

## Validate the setup (run on EACH machine)

```bash
bash "<this-skill>/scripts/validate-setup.sh"     # run from a project root
```
Prints PASS/FAIL for:
1. `scripts/qa/ns_write.py` exists **and** matches the skill's canonical copy (no drift)
2. `.claude/settings.local.json` contains `Bash(python3 scripts/qa/ns_write.py:*)`
3. `cdp.py` present at the expected path
4. (info) QA Chrome answering on CDP port 9333

Check 2 FAIL = the allow rule is not added on this machine yet → add it (Setup step 2). Run
this on all 3 computers to confirm they match.

## When NOT this skill

- **Field write via SDF / File Cabinet** — that is code, not record data → `ns-sdf-prod-deploy`.
- **Sublist edits / transform** — `save` mode here does body fields only; sublists need a
  bespoke script. Don't force them through `--set`.
- **Reading / verifying only** — no write needed → `ns-live-verify`.
