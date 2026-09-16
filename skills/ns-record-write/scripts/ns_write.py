#!/usr/bin/env python3
"""
ns_write.py — scoped, auditable NetSuite record-write helper (submitFields OR load/save).

Runs ONE of two write modes against the record you name, on a logged-in NetSuite tab in the
QA Chrome (CDP port 9333). It does NOT accept free-form JS — only --type / --id / --set
field=value. That is the whole point of allow-listing this ONE script instead of
`cdp.py eval:*`.

Modes:
  --mode submit  (default) N/record.submitFields  — fast body-field update, no sourcing/UE
  --mode save              record.load -> setValue -> save  — full save (sourcing + UEs fire)

Guards (all must pass before any write):
  1. the live tab's account (N/runtime.accountId) MUST equal --account, else ABORT
  2. dry-run by default — prints current field values + the PLAN and stops;
     you must pass --confirm to actually write
  3. after writing it reads the fields back and prints before -> after

It never reads or types credentials.

Examples:
  # dry-run submitFields on SB2 (safe)
  python3 scripts/qa/ns_write.py --account 4089685_SB2 \
      --type customrecord_mfg_completionusage --id 16525 \
      --set custrecord_mfg_usagecompletion=2935624

  # actually write via submitFields
  python3 scripts/qa/ns_write.py --account 4089685_SB2 \
      --type customrecord_mfg_completionusage --id 16525 \
      --set custrecord_mfg_usagecompletion=2935624 --confirm

  # full load/save (fires sourcing + user-event scripts)
  python3 scripts/qa/ns_write.py --account 4089685_SB2 --mode save \
      --type salesorder --id 12345 --set memo="fixed" --confirm

  # pin a specific tab when several NetSuite tabs are open
  python3 scripts/qa/ns_write.py --tab <TARGET_ID> --account 4089685 ...
"""
import os, sys, json, time, argparse, subprocess

CDP = "/Users/bombot/.claude/skills/netsuite-qa-browser/references/cdp.py"
PORT = "9333"


def _ev(js, tab=None):
    env = dict(os.environ, CDP_PORT=PORT)
    if tab:
        env["TGT_ID"] = tab
    r = subprocess.run(["python3", CDP, "eval", js], env=env,
                       capture_output=True, text=True)
    o = r.stdout.strip()
    if len(o) >= 2 and o[0] == '"' and o[-1] == '"':
        o = o[1:-1]
    return o, r.stderr.strip()


def _await(setup_js, tab=None, tries=25):
    """Fire an async require() that stashes JSON into window.__X, then poll it.
    cdp.py serializes JS null as the string 'None' — reject it while polling."""
    _ev("window.__X=null; " + setup_js, tab)
    for _ in range(tries):
        v, _e = _ev("window.__X", tab)
        if v and v not in ("null", "undefined", "None", ""):
            try:
                return json.loads(v)
            except Exception:
                return {"ok": False, "err": "unparseable: " + v[:200]}
        time.sleep(1)
    return {"ok": False, "err": "timeout waiting for browser result"}


def _s(x):
    return json.dumps(str(x))


def main():
    ap = argparse.ArgumentParser(description="Scoped NetSuite record writer")
    ap.add_argument("--account", required=True,
                   help="expected N/runtime.accountId (e.g. 4089685_SB2 or 4089685). "
                        "Write ABORTS if the live tab's account differs.")
    ap.add_argument("--type", required=True, help="record type id")
    ap.add_argument("--id", required=True, help="record internal id")
    ap.add_argument("--set", action="append", default=[], metavar="FIELD=VALUE",
                   help="body field to set (repeatable)")
    ap.add_argument("--mode", choices=["submit", "save"], default="submit",
                   help="submit = submitFields (default); save = load/setValue/save")
    ap.add_argument("--dynamic", action="store_true",
                   help="(save mode) load in dynamic mode so field sourcing runs")
    ap.add_argument("--tab", default=None, help="CDP target id to pin (optional)")
    ap.add_argument("--confirm", action="store_true",
                   help="actually write; without it this is a dry-run")
    args = ap.parse_args()

    if not args.set:
        ap.error("need at least one --set FIELD=VALUE")
    values = {}
    for pair in args.set:
        if "=" not in pair:
            ap.error("bad --set %r (want FIELD=VALUE)" % pair)
        k, v = pair.split("=", 1)
        values[k.strip()] = v
    fields = list(values.keys())

    # ---- Guard 1: account identity -------------------------------------------
    guard = _await(
        "require(['N/runtime'], function(rt){ window.__X = JSON.stringify("
        "{ok:true, acct:String(rt.accountId), env:rt.envType, url:location.host}); });",
        args.tab)
    if not guard.get("ok"):
        print("ABORT: could not read account from tab:", guard.get("err")); sys.exit(2)
    live = guard.get("acct")
    print("live tab account =", live, "| env =", guard.get("env"), "| host =", guard.get("url"))
    if live != args.account:
        print("ABORT: live account %r != --account %r (wrong tab / wrong login)"
              % (live, args.account)); sys.exit(2)

    # ---- read BEFORE ---------------------------------------------------------
    cols = "[" + ",".join(_s(f) for f in fields) + "]"
    before = _await(
        "require(['N/search'], function(s){ try{ var r=s.lookupFields("
        "{type:%s, id:%s, columns:%s}); window.__X=JSON.stringify({ok:true, r:r}); }"
        "catch(e){ window.__X=JSON.stringify({ok:false, err:String(e)}); } });"
        % (_s(args.type), _s(args.id), cols), args.tab)
    print("BEFORE:", json.dumps(before.get("r", before), ensure_ascii=False))
    print("\nPLAN [mode=%s%s]: type=%s id=%s values=%s"
          % (args.mode, " dynamic" if args.dynamic else "", args.type, args.id,
             json.dumps(values, ensure_ascii=False)))

    if not args.confirm:
        print("\nDRY-RUN (no --confirm) — nothing written."); return

    # ---- WRITE ---------------------------------------------------------------
    vals_js = "{" + ",".join("%s:%s" % (_s(k), _s(v)) for k, v in values.items()) + "}"
    acct_guard = ("if(String(rt.accountId)!==%s){ window.__X=JSON.stringify({ok:false,"
                 "err:'account changed to '+rt.accountId}); return; }" % _s(args.account))
    if args.mode == "submit":
        write_js = (
            "require(['N/record','N/runtime'], function(record, rt){ try{ %s"
            "  var id=record.submitFields({type:%s, id:%s, values:%s});"
            "  window.__X=JSON.stringify({ok:true, savedId:id});"
            "}catch(e){ window.__X=JSON.stringify({ok:false, err:String(e)}); } });"
            % (acct_guard, _s(args.type), _s(args.id), vals_js))
    else:  # save
        setters = "".join("rec.setValue({fieldId:%s, value:%s});" % (_s(k), _s(v))
                          for k, v in values.items())
        write_js = (
            "require(['N/record','N/runtime'], function(record, rt){ try{ %s"
            "  var rec=record.load({type:%s, id:%s, isDynamic:%s}); %s"
            "  var id=rec.save({enableSourcing:true, ignoreMandatoryFields:false});"
            "  window.__X=JSON.stringify({ok:true, savedId:id});"
            "}catch(e){ window.__X=JSON.stringify({ok:false, err:String(e)}); } });"
            % (acct_guard, _s(args.type), _s(args.id),
               "true" if args.dynamic else "false", setters))
    res = _await(write_js, args.tab)
    if not res.get("ok"):
        print("WRITE FAILED:", res.get("err")); sys.exit(1)
    print("WRITE ok (mode=%s), savedId =" % args.mode, res.get("savedId"))

    # ---- read AFTER (verify) -------------------------------------------------
    after = _await(
        "require(['N/search'], function(s){ try{ var r=s.lookupFields("
        "{type:%s, id:%s, columns:%s}); window.__X=JSON.stringify({ok:true, r:r}); }"
        "catch(e){ window.__X=JSON.stringify({ok:false, err:String(e)}); } });"
        % (_s(args.type), _s(args.id), cols), args.tab)
    print("AFTER :", json.dumps(after.get("r", after), ensure_ascii=False))


if __name__ == "__main__":
    main()
