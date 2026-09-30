---
name: ns-live-verify
description: >-
  Use when you need to read or verify live NetSuite account state — chart of accounts, GL
  postings, custom record/field values, saved searches, or script deployment status — without
  opening the NetSuite UI, especially to confirm real state before or after a change instead
  of assuming.
---

# NetSuite Live Verify (read-only via the TEIBTO Dev Bridge)

**Skill version: `202609_09`**

Run SuiteQL / `record.load().toJSON()` / searches against a live account through a logged-in Chrome
tab, so you verify against **real state** instead of guessing. Read-only. Pairs with
`ns-sdf-prod-deploy` (verify before/after deploy) and browser session handling.

**Reference for the endpoint = the Dev Bridge repo** (`Teibto/TEIBTO-Dev-Bridge`, private; the README
beside `TEIBTO - Dev Bridge.js` has the full action reference). Where this file and the script
disagree, the script wins. This skill was once written against a different, older "tester" Suitelet
(`action=dbgQuery` in the query string / `step=DEBUG_QUERY`); that shape is **not** the Dev Bridge.

## The endpoint

One Suitelet, addressed by script + deploy id; the action travels in the **POST body**:

```
POST /app/site/hosting/scriptlet.nl?script=customscript_teibto_dev_bridge&deploy=customdeploy_teibto_dev_bridge
Content-Type: application/json      {"action": "...", ...}
```

The two ids are the README's *recommended* ones (verified to exist on the sandbox this was tested on);
another account may deploy it under different ids — check the script record, and keep the real ones for
each account in your private notes (`notes.private.md`, gitignored) or in `browser.json`
(`dev_bridge.endpoints["<account>"].path`). Never commit a production account id into this tracked file.

Needs a logged-in `*.app.netsuite.com` tab as **Administrator** (the session cookie authenticates;
no "Available Without Login"). Every reply is `{ok:true, action, ...}` or `{ok:false, error, code}` — check
`ok` first. Body cap 500 KB; `query`/`search` return at most 1000 rows.

| action | request body | reply |
|---|---|---|
| `ping` (GET `?action=ping` also works) | `{}` | `account`, `envType`, `version`, `user{id,role,roleId,isAdmin}`, `serverTime` |
| `help` (GET ok) | `{}` | the action list |
| `query` | `{q:"SELECT …", params:[]}` | `rows[]`, `count`, `truncated` — **SELECT only** |
| `record` | `{type, id, fields?:[…], meta?:true, dynamic?:true}` | `record` (full toJSON with sublists) or `fields{f:{value,text}}`; `meta` adds field + sublist ids |
| `lookup` | `{type, id, columns:[…]}` | `values{…}` (fast single-record read) |
| `feature` | `{names:[…]}` | `features{name:bool}` |
| `search` | `{searchId}` or `{type, filters, columns, limit}` | `results[]`, `count`, `capped` |

`query` details from the script: it must **start with `SELECT`** (so `WITH …` is rejected), contain no
`;`, and none of `insert|update|delete|merge|create|drop|alter|truncate|grant|revoke` as a word — even
inside a string literal. Result keys are always **lowercase** (`AS my_id` → `row.my_id`). The platform
caps non-paged SuiteQL at 5000 rows and the bridge cuts to 1000, so `truncated:true` only means "more
than 1000": count with `SELECT COUNT(*)`, never with `rows.length`. `OFFSET` is silently ignored — page with
the `ROWNUM` double-subquery. Every call is written to the script's Execution Log (who + what).

Two ways to drive the tab — **bsk is the default** (see `browser-engines` for the engine choice):

### Option A — raw `bsk` (verified live on a sandbox; `evaluate` awaits the promise, one call)

Say it first (one line: what for, which account, a background Agent Window closed when done).

```bash
export BSK_AUTO_START=0
bsk session start --no-focus --name lv --json > s.json          # note session_id
bsk tab create --no-active --url about:blank --session <sid> --json > t.json   # note tab_id
# open a CLASSIC NetSuite page first — fetch from about:blank fails
bsk navigate "https://<host>/app/center/card.nl?sc=-29&whence=" --wait-until domcontentloaded --session <sid> --tab-id <tab> --json
# guards from browser-engines: dialog guard + identity gate (company + SANDBOX), then:
bsk evaluate "fetch('/app/site/hosting/scriptlet.nl?script=customscript_teibto_dev_bridge&deploy=customdeploy_teibto_dev_bridge',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'query',q:'<SELECT ...>',params:[]})}).then(r=>r.text())" --session <sid> --tab-id <tab> --json
bsk session stop <sid>                                            # always, even on failure
```

Return only what you need from the reply — some browser-automation bridges block strings that look like
URLs / query strings, so never print the endpoint and pick out fields instead of dumping a whole `toJSON()`.
Read-only: never run writes through this path.

### Option B — `cdp.py` (needs a registered NetSuite lane / claimed tab; pin `TGT_ID`)

Fire the fetch into a `window` variable, read it back in a **separate** call (the console does not await):

```bash
export CDP_PORT=9333; export TGT_ID=<target-tab-id>
python3 cdp.py eval 'window.__r=null; fetch("/app/site/hosting/scriptlet.nl?script=customscript_teibto_dev_bridge&deploy=customdeploy_teibto_dev_bridge",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action:"query",q:"<SELECT ...>",params:[]})}).then(r=>r.json()).then(j=>window.__r=JSON.stringify(j).slice(0,900)); "fired"'
sleep 3
python3 cdp.py eval 'window.__r'
```

### Option C — the scoped helper `scripts/ns_read.py` (for agents that must not run raw `bsk`)

The read-side sibling of `ns_write.py`: one command, no free-form JS, its own `bsk` session that it
always stops. `python3 scripts/ns_read.py <whoami|ping|query|record|lookup|feature|search> --account <ACCOUNT> …`

- **Identity gate every run** (company from `nlapiGetContext()` must equal `--account`), and the request
  goes out only after the endpoint answers the bridge's own `ping` in the expected shape *and* reports the
  same account. A login or "Notice" page is a hard stop (exit 3) — it never logs in, clicks or types.
- **Sandbox freely; anything else needs `--allow-prod-read`** (the data goes to whichever model runs the
  script — say so to the user first).
- `query` takes one `SELECT` (validated before any browser call, mirroring the bridge: no `WITH`, no `;`,
  no DML words). Other subcommands validate every argument (ids, comma lists, JSON filters ≤ 5000 chars,
  `--limit` 1–1000).
- The path is only `…scriptlet.nl?script=<id>&deploy=<id>` — from `--bridge-path`, else config
  `dev_bridge.endpoints["<account>"].path`, else the README's default ids. Nothing else can ride along.
- Exit codes: `0` ok · `1` the bridge answered `ok:false` · `2` refused by a guard · `3` session/transport/dialog.
- It announces itself on stderr (`[ns_read] using bsk: opening a background Agent Window …`); stdout stays pure JSON.
- Engine `bsk` only. `cdp` prints "not implemented" (exit 2) — no lane is bound on the machine it was
  written on, so it could not be tested.
- **Verified live on a sandbox** with the default ids: `ping`, `query` (a `COUNT(*)`), `record` (a field
  subset and a full dump, cut by `--max-chars`), `lookup`, `feature`, `search` (ad-hoc), a bad column
  (bridge `ok:false` → exit 1), and the local refusals. **Not verified live:** a saved search
  (`--search-id`), `--meta`, `--filters-json` with a real filter, any non-sandbox read.
- 38 offline tests: `python3 scripts/test_ns_read_offline.py`.

## SuiteQL gotchas (cost real time)

- **`acctnumber` is a STRING** → `WHERE acctnumber = '113006'` (quotes). Numeric compare errors.
- **`LIKE` needs quoted pattern** → `WHERE fullname LIKE '%Variance%'` (bare `%...%` = parse error).
- **account name columns**: `name`/`displayname` are invalid identifiers; use `fullname`, or
  `record` (`accountsearchdisplayname` under `.fields`). `acctnumber` may itself hold a name
  for placeholder accounts.
- **checkbox fields** return `'T'`/`'F'`/`null` (string), not boolean.
- **multiselect** via SuiteQL returns `null` even when set → use the `record` action.
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

When a fetch returns the login/timeout page: **do not log in inside the `bsk` Agent Window** — there Chrome
did not autofill (email at 0 characters after 10 s, focused or in the background; measured). Open the login
page in a **real tab** instead (Claude in Chrome, or ask the user to open it), where Chrome fills email +
password. Then: **click `#login-submit` only — never read the password field.** If the button is disabled,
click the background outside the login box once (blur → enables), then click submit. Fields empty in a real
tab → stop and ask. `ns_read.py` stops with exit 3 and says so; it never logs in.

## Status

v0.1 draft — recipes verified live on SB2 + a customer account this session. Reference skill; test retrieval
(can an agent find + apply the right recipe) per superpowers:writing-skills.
