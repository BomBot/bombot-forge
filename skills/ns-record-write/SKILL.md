---
name: ns-record-write
description: >-
  Use when writing to a live NetSuite record from a logged-in browser tab (updating a field,
  fixing a bad value, a scoped submitFields or load/save), instead of allow-listing raw
  `cdp.py eval`. Covers the scoped `ns_write.py` helper (structured args only, submit + save
  modes, account guard, dry-run default), its two engines (bsk: sandbox freely, production only with an explicit `--allow-bsk-prod`; cdp: anywhere),
  the exact `permissions.allow` line it needs, and a validator that checks each machine.
---

# NetSuite Record Write (scoped ns_write helper)

**Skill version: `202609_11`**

Writing to a live NetSuite record from a logged-in browser tab. The **only** sanctioned
write channel here is `scripts/qa/ns_write.py` — a helper that takes **structured args**
(`--type`, `--id`, `--set field=value`) and runs the write in the tab. It does NOT accept
free-form JS, so allow-listing this one script is safe where `Bash(...cdp.py eval:*)` would
hand over full unrestricted browser control.

Two engines drive the tab (**the caller owns the tab**; the helper never opens or closes one):

| Engine | Flags | Where writes are allowed |
|---|---|---|
| `bsk` (BrowserSkill) | `--bsk-session <id> --bsk-tab <id>` | **Sandbox freely.** `bsk` auto-accepts native dialogs, so `--confirm` on any other environment is refused unless you add `--allow-bsk-prod` (see the iron rule below) |
| `cdp` (Chrome for Testing) | `--tab <TARGET_ID>` | Sandbox or production (needs a claimed lane — see `cdp-browser`) |
| `auto` (default) | — | `bsk` if `--bsk-session` is given, else `cdp` |

The helper only runs `N/record` / `N/search` in the page — it clicks nothing, so no dialog is
expected; the guards below exist because a dialog is the failure that can't be undone.

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
- **bsk on production needs `--allow-bsk-prod`.** With `--engine bsk` the helper installs a page-level
  dialog guard first (a dialog that still fires aborts the run) and refuses `--confirm` unless the
  live environment is `SANDBOX` **or** `--allow-bsk-prod` is passed. Why it is safe enough: the
  in-page write is an `N/record` call — it clicks nothing and opened no dialog in any live test.
  Why it is still explicit: `bsk` cannot be told to refuse a dialog, so a dialog that appears
  anyway is answered "OK" by the browser. Rules for using it on production: dry-run first and
  read BEFORE; the user approves that round of writes; one record per call; keep the WARNING line
  in the report; `OUTCOME UNKNOWN` still means stop. Do **not** use `bsk` to *click* things on
  production — only this helper.
- **`OUTCOME UNKNOWN` (exit 3) means stop.** If the transport fails or times out *during* the
  write (bsk `session_busy` / window closed / timeout; cdp timeout), the write may have happened.
  **Never re-run blind** — dry-run the same record and read the current values first.
- **The tab must be on a record page.** The helper uses the SuiteScript 2.x `require`, which the
  Home dashboard does **not** have (`require is not defined`); a record page does. Open the
  target record (or any record) in your pinned tab first.

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
3. **Engine lane (at least one):**
   - **bsk** (sandbox; production with `--allow-bsk-prod`): CLI + extension + daemon per the `cdp-browser` skill; start your own
     session and pinned tab, open a **record page** on the target account, then pass
     `--bsk-session`/`--bsk-tab`. Stop the session when done.
   - **cdp** (anywhere): `cdp.py` on CDP port 9333 with a claimed lane (see `cdp-browser` and
     `netsuite-qa-browser`); pass `--tab`. The QA Chrome must be logged into the target account.
   `scripts/validate-setup.sh` passes when **either** lane is usable.

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

# multiple fields: repeat --set. cdp: pin a tab with --tab <CDP_TARGET_ID> when several NS tabs open.

# 4) same dry-run through bsk (sandbox) — your own session + pinned tab, already on a record page
python3 scripts/qa/ns_write.py --engine bsk --bsk-session <SID> --bsk-tab <TAB> \
    --account 4089685_SB2 --type customrecord_mfg_completionusage --id 16525 \
    --set custrecord_mfg_usagecompletion=2935624
```

- `--account` = expected `runtime.accountId` (`4089685_SB2` sandbox, `4089685` prod). Mismatch → abort.
- Reads BEFORE + AFTER via `N/search.lookupFields` so you get a before→after diff for free.
- Exit codes: `0` ok / dry-run · `1` write failed (the page rejected it) · `2` aborted by a guard · `3` **outcome unknown** (transport failure mid-write — do not re-run blind).
- bsk was verified on a sandbox: dry-run (account guard, BEFORE read, dialog guard, wrong-account abort) and **a live `--confirm` write** (`submitFields` on a sandbox `currency` record: a value the page rejects → exit 1, nothing written; a valid value → `WRITE ok` with AFTER matching, then reverted to the original and re-read). Offline stubs cover the refuse / unknown-outcome paths. `--mode save` and `--mode save --dynamic` were also exercised live the same way (write `AU1`, revert to `AUD`, re-read; both `WRITE ok`) — on a record with no sourcing-dependent fields, so `--dynamic` was proven to run, not proven to source. **`--allow-bsk-prod` was exercised once live** on a customer production account that was still in implementation (`--mode submit`, one free-text field on a custom record, the owner approved the record and the value first): dry-run → write → re-read → revert → re-read, the final value byte-identical to the original; no dialog appeared. That proves the path works, not that production is risk-free — every write leaves System Notes.
- A custom record's `--type` is its **script id** (`customrecord_…`), not the numeric `rectype` in the URL (`INVALID_RCRD_TYPE`). `nlapiGetRecordType()` on the record page gives it.
- **Mid-write transport failure was exercised live on a sandbox with a `bsk` test shim on `PATH`** (the shim only triggers the failure; the helper talked to the real `bsk` and the real page): (a) the session stopped right before the write call → real `not_found` from `bsk` → `OUTCOME UNKNOWN`, exit 3, record unchanged; (b) the write call really ran but its reply was lost → `OUTCOME UNKNOWN`, exit 3, **and the record had changed** — that is exactly why the rule is "re-read, never re-run". Not reproduced: a natural race (the window is ~1 s, and one attempt to kill the session 0.4 s in came too late — the write had already returned).
- Dialogs: a page rejection comes back as the error text, not a dialog — the guard stayed silent in the live run.

## Offline tests for the helper

After changing `ns_write.py`, run `python3 scripts/test_ns_write_offline.py` (no browser, network, `bsk` or `cdp` needed; 17 cases: dry-run, account guard, the `bsk` production opt-in, exit codes 0/1/2/3, argument errors, and the exact write payload — type, id, values, submit vs save, `--dynamic`, value escaping, the in-page account re-check, and that `bsk` and `cdp` send identical JS). It stubs the browser layer, so it proves the guards, exit codes and payload, not that a page accepts a write — live behaviour is covered by the notes above.

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
