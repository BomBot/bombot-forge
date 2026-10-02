#!/usr/bin/env python3
"""
ns_write.py — scoped, auditable NetSuite record-write helper (submitFields OR load/save).

Runs ONE of two write modes against the record you name, on a logged-in NetSuite tab. It does
NOT accept free-form JS — only --type / --id / --set field=value. That is the whole point of
allow-listing this ONE script instead of `cdp.py eval:*`.

Two engines drive the tab (the caller owns the tab; this script never opens or closes one):
  --engine cdp   Chrome for Testing over CDP (port 9333): pass --tab <TARGET_ID>. Production OK.
  --engine bsk   BrowserSkill: pass --bsk-session <id> --bsk-tab <id> (your own pinned tab, already
                 on a classic NetSuite page). --confirm works on any environment; on a non-sandbox
                 account it prints a WARNING. The protection is the round's confirmation (the caller
                 lists the write and gets the user's OK) plus dry-run first; this helper's in-page
                 write is an N/record call that clicks nothing and opened no dialog in any live test.
                 --allow-bsk-prod is still accepted (no longer needed) so old command lines keep working.
  --engine auto  (default) bsk if --bsk-session is given, else cdp.

Modes:
  --mode submit  (default) N/record.submitFields  — fast body-field update, no sourcing/UE
  --mode save              record.load -> setValue -> save  — full save (sourcing + UEs fire)

Guards (all must pass before any write):
  1. the live tab's account (N/runtime.accountId) MUST equal --account, else ABORT
  2. dry-run by default — prints current field values + the PLAN and stops;
     you must pass --confirm to actually write
  3. after writing it reads the fields back and prints before -> after
  4. bsk only: native-dialog guard installed first (a dialog that still fires aborts); a write to
     a non-sandbox account prints a WARNING (no flag needed since 0.30.0)
  5. a transport failure/timeout during the write = OUTCOME UNKNOWN (exit 3): never re-run blind

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

  # pin a specific tab when several NetSuite tabs are open (cdp)
  python3 scripts/qa/ns_write.py --tab <TARGET_ID> --account 4089685 ...

  # same dry-run through bsk (own session + pinned tab, on a classic NetSuite page)
  python3 scripts/qa/ns_write.py --engine bsk --bsk-session <SID> --bsk-tab <TAB> \
      --account 4089685_SB2 --type customrecord_mfg_completionusage --id 16525 \
      --set custrecord_mfg_usagecompletion=2935624
"""
import os, sys, json, time, argparse, subprocess

CDP = os.environ.get("CDP_SCRIPT", "/Users/bombot/.claude/skills/netsuite-qa-browser/references/cdp.py")
PORT = os.environ.get("CDP_PORT", "9333")

# Selected engine, set once in main(): the caller owns the tab for both engines.
ST = {"engine": "cdp", "session": None, "tab": None}

# A page-level dialog guard: bsk answers every native dialog with "accept" and cannot be told not
# to, so confirm() must never reach it. Reinstalled per run (a navigation drops it).
DIALOG_GUARD_JS = ("window.alert=function(){};window.confirm=function(){return false};"
                   "window.prompt=function(){return null};window.onbeforeunload=null;'guard'")


def _bsk_eval(expr, timeout=60):
    """One `bsk evaluate` on the caller's pinned tab. Returns (value, error)."""
    env = dict(os.environ, BSK_AUTO_START="0")
    cmd = ["bsk", "evaluate", expr, "--session", ST["session"], "--tab-id", ST["tab"], "--json"]
    try:
        r = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, "bsk transport: %s" % e
    try:
        d = json.loads(r.stdout)
    except ValueError:
        return None, "bsk transport: rc=%s %s" % (r.returncode, (r.stderr or r.stdout).strip()[:200])
    if r.returncode != 0 or d.get("ok") is False:
        return None, "bsk transport: rc=%s %s" % (r.returncode, json.dumps(d)[:200])
    if d.get("dialogs"):
        return None, "native dialog fired (guard leaked): %s" % json.dumps(d["dialogs"])[:200]
    return d.get("value"), None


def _await_bsk(setup_js, secs=20):
    """bsk awaits promises, so poll window.__X inside the page instead of from Python."""
    expr = ("new Promise(function(res){window.__X=null;%s var n=0;(function p(){"
            "if(window.__X!==null&&window.__X!==undefined){res(window.__X)}"
            "else if(++n>%d){res(JSON.stringify({ok:false,transport:true,"
            "err:'timeout waiting for browser result'}))}else{setTimeout(p,100)}})();})"
            % (setup_js, secs * 10))
    v, err = _bsk_eval(expr, timeout=secs + 15)
    if err:
        return {"ok": False, "err": err, "transport": True}
    try:
        return json.loads(v)
    except Exception:
        return {"ok": False, "err": "unparseable: %s" % str(v)[:200], "transport": True}


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
    if ST["engine"] == "bsk":
        return _await_bsk(setup_js)
    _ev("window.__X=null; " + setup_js, tab)
    for _ in range(tries):
        v, _e = _ev("window.__X", tab)
        if v and v not in ("null", "undefined", "None", ""):
            try:
                return json.loads(v)
            except Exception:
                return {"ok": False, "err": "unparseable: " + v[:200]}
        time.sleep(1)
    return {"ok": False, "err": "timeout waiting for browser result", "transport": True}


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
    ap.add_argument("--engine", choices=["auto", "cdp", "bsk"], default="auto",
                   help="auto = bsk when --bsk-session is given, else cdp")
    ap.add_argument("--tab", default=None, help="(cdp) CDP target id to pin (optional)")
    ap.add_argument("--bsk-session", default=None, help="(bsk) your own session id")
    ap.add_argument("--bsk-tab", default=None,
                   help="(bsk) your own pinned tab id, already on a classic NetSuite page")
    ap.add_argument("--allow-bsk-prod", action="store_true",
                    help="(deprecated, no effect) bsk may write on any environment; kept so old command "
                         "lines still parse")
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

    # ---- engine ----------------------------------------------------------------
    engine = args.engine
    if engine == "auto":
        engine = "bsk" if args.bsk_session else "cdp"
    if engine == "bsk":
        if not (args.bsk_session and args.bsk_tab):
            ap.error("--engine bsk needs --bsk-session and --bsk-tab (your own pinned tab)")
        if args.tab:
            ap.error("--tab is for the cdp engine; use --bsk-tab with bsk")
        ST.update(engine="bsk", session=args.bsk_session, tab=args.bsk_tab)
        _v, err = _bsk_eval(DIALOG_GUARD_JS)
        if err:
            print("ABORT: could not install the dialog guard:", err); sys.exit(2)
    print("engine =", engine)

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
    if args.allow_bsk_prod:
        print("NOTE: --allow-bsk-prod is no longer needed (ignored).")
    if engine == "bsk" and str(guard.get("env")).upper() != "SANDBOX":
        print("WARNING: writing to a NON-sandbox account (env=%r) via bsk — the round's confirmation is the guard."
              % guard.get("env"))

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
        if res.get("transport"):
            print("OUTCOME UNKNOWN — the write may or may not have happened (%s)." % res.get("err"))
            print("Do NOT re-run. Re-read the record (dry-run, no --confirm) to see its values, "
                  "then decide."); sys.exit(3)
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
