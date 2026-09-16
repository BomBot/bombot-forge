---
name: ns-live-verify
description: >-
  Use when you need to read or verify live NetSuite account state — chart of accounts, GL
  postings, custom record/field values, saved searches, or script deployment status — without
  opening the NetSuite UI, especially to confirm real state before or after a change instead
  of assuming.
---

# NetSuite Live Verify (read-only via dbgQuery)

**Skill version: `202609_04`**

Run SuiteQL / `record.toJSON` against a live account through a logged-in Chrome tab, so you
verify against **real state** instead of guessing. Read-only, SELECT-only. Pairs with
`ns-sdf-prod-deploy` (verify before/after deploy) and browser session handling.

## Endpoints (TEIBTO)

| Account | Endpoint | Auth |
|---|---|---|
| SB2 (4089685) | `script=3171&deploy=1&compid=4089685_SB2&step=DEBUG_QUERY` | Admin session |
| *(any other account)* | `script=<SCRIPT_ID>&deploy=1&compid=<ACCOUNT_ID>&action=dbgQuery&debug=1` | Admin session |

Add a row per real account to `notes.private.md` (gitignored, not in this repo) as you set
each one up — never commit a production account id / script id into this tracked file.

Both are POST, same-origin `fetch` from a logged-in `*.app.netsuite.com` Admin tab. Fire the
fetch to a `window.__r` var, read it back in a **separate** call (fetch is async).

```bash
# via cdp.py (Chrome for Testing, port 9333); pin the tab with TGT_ID
export CDP_PORT=9333; export TGT_ID=<target-tab-id>
python3 cdp.py eval 'window.__r=null; fetch("/app/site/hosting/scriptlet.nl?script=<SCRIPT_ID>&deploy=1&compid=<ACCOUNT_ID>&action=dbgQuery&debug=1",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({q:"<SELECT ...>"})}).then(r=>r.text()).then(t=>window.__r=t.slice(0,900)); "fired"'
sleep 3
python3 cdp.py eval 'window.__r'
```

- SB2 tester body: `{qtype:"sql", sql:"..."}` (also `qtype:"whoami"`, `qtype:"load",recordType,id`).
- `action=dbgQuery` body: `{q:"<SELECT>", params?:[]}` → `{rows,count,truncated}`;
  `action=dbgRecord` body `{type,id}` → `record.toJSON()` (fields nested under `.record.fields`).

## SuiteQL gotchas (cost real time)

- **`acctnumber` is a STRING** → `WHERE acctnumber = '113006'` (quotes). Numeric compare errors.
- **`LIKE` needs quoted pattern** → `WHERE fullname LIKE '%Variance%'` (bare `%...%` = parse error).
- **account name columns**: `name`/`displayname` are invalid identifiers; use `fullname`, or
  `dbgRecord` (`accountsearchdisplayname` under `.fields`). `acctnumber` may itself hold a name
  for placeholder accounts.
- **checkbox fields** return `'T'`/`'F'`/`null` (string), not boolean.
- **multiselect** via SuiteQL returns `null` even when set → use `dbgRecord`.
- Big `ORDER BY DESC` over a huge table can throw "unexpected SuiteScript error" → bound by
  date or id range.
- A response that is an HTML "Notice / connection timed out" page = **session expired**, not a
  query error. Re-login (below) and retry.

## Verification recipes (proven)

```sql
-- account by number → internal id
SELECT id, acctnumber FROM account WHERE acctnumber = '113006'
-- what posts to an account, by transaction type (is a mechanism live?)
SELECT t.type type, COUNT(*) cnt, SUM(tal.amount) net
FROM transactionaccountingline tal, transaction t
WHERE t.id = tal.transaction AND tal.account = <id> GROUP BY t.type
-- full GL of one transaction (Dr/Cr per account)
SELECT a.acctnumber, tal.debit, tal.credit
FROM transactionaccountingline tal, account a
WHERE tal.account=a.id AND tal.transaction=<txnId> AND tal.posting='T'
-- custom record + fields (e.g. WO Type config)
SELECT id, name, <custrecord_x> FROM customrecord_mfg_work_order_type
-- is a script deployment active? (UE off = isdeployed 'F')
SELECT sd.scriptid, sd.status, sd.isdeployed FROM scriptdeployment sd, script s
WHERE sd.script=s.id AND s.scriptid='customscript_...'
-- custom transaction TYPES present
SELECT id, name, scriptid FROM customtransactiontype
-- link a WOC → its WO + issues (createdfrom not queryable directly)
SELECT previousdoc, nextdoc, linktype FROM previoustransactionlink WHERE nextdoc=<id>
```

**Disable-a-script check:** a UE is off when every `scriptdeployment.isdeployed = 'F'` — then
confirm on a real record page that the injected element/global function is absent (e.g. the
custom button's `window.<fn>` is `undefined`), which is stronger than the deployment flag alone.

## Session / login handling

When a fetch returns the login/timeout page: navigate the tab to any account page → it bounces
to `enterpriselogin.nl`. Chrome autofills email+password. **Click `#login-submit` only — never
read the password field.** If the button is disabled, click the background outside the login box
once (blur → enables), then click submit. Fields empty (not autofilled) → stop and ask.

## Status

v0.1 draft — recipes verified live on SB2 + a customer account this session. Reference skill; test retrieval
(can an agent find + apply the right recipe) per superpowers:writing-skills.
