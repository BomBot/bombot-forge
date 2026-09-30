#!/usr/bin/env python3
"""
ns_read.py — scoped, READ-ONLY NetSuite reader (Dev Bridge SuiteQL + record.toJSON).

The read-side sibling of ns-record-write/scripts/ns_write.py. A cheap agent may be allowed to run
ONLY this script instead of raw `bsk`, so this file IS the safety boundary:

  * it takes no free-form JS — only --account plus a SELECT/WITH query, or a --type/--id pair
  * it never clicks or types, and it never tries to log in (a login page is a hard stop)
  * account identity is proven in-page (nlapiGetContext) before anything is read
  * non-sandbox accounts are refused unless --allow-prod-read is passed explicitly

It drives ONE bsk session it starts and stops itself (engine bsk only, today). Every bsk command
is scoped with --session and --tab-id; the session is stopped in a `finally`, even on error.

Usage:
  python3 ns_read.py whoami --account 4089685_SB2
  python3 ns_read.py query  --account 4089685_SB2 "SELECT id FROM account"
  python3 ns_read.py query  --account 4089685_SB2 --body-style sql "SELECT 1 FROM dual"
  python3 ns_read.py record --account 4089685_SB2 --type salesorder --id 12345

Global flags (before or after the subcommand):
  --allow-prod-read   allow reading a non-sandbox account (prints a WARNING)
  --engine bsk|cdp    default: the `engine` key in the config file (bsk)
  --config PATH       default ~/.config/bombot-forge/browser.json; env NS_READ_CONFIG overrides

Output: one JSON object on stdout — {"account", "environment", "result"} for query/record,
{"account", "environment"} for whoami. The serialized result is cut at --max-chars (default
20000) and "truncated": true is added when it was cut.

Exit codes: 0 ok · 1 the bridge returned an error · 2 guard/usage/validation refused ·
3 session/transport/dialog problem.
"""
import os, sys, re, json, argparse, subprocess

DEFAULT_CONFIG = "~/.config/bombot-forge/browser.json"

ACCOUNT_RE = re.compile(r"^[0-9]+(_[A-Za-z0-9]+)?$")
RECORD_TYPE_RE = re.compile(r"^[A-Za-z0-9_]+$")
RECORD_ID_RE = re.compile(r"^[0-9]+$")
# Only the Dev Bridge Suitelet, with a query string of safe characters.
BRIDGE_PATH_RE = re.compile(r"^/app/site/hosting/scriptlet\.nl\?[A-Za-z0-9_=&.%-]+$")

# A POST goes to a Suitelet, so the path must be the read-only Dev Bridge, not any Suitelet.
BRIDGE_MARKERS = ("action=dbgQuery", "action=dbgRecord", "step=DEBUG_QUERY")

MAX_SQL_LEN = 5000
FORBIDDEN_RE = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|DROP|ALTER|CREATE|TRUNCATE|GRANT|REVOKE|EXEC|EXECUTE|CALL)\b",
    re.I)
FIRST_WORD_RE = re.compile(r"^([A-Za-z]+)")

# Selected session/tab, set once per run. The script owns both.
ST = {"session": None, "tab": None}

# A page-level dialog guard installed right after navigation: bsk answers every native dialog with
# "accept" and cannot be told not to, so confirm() must never reach it.
DIALOG_GUARD_JS = ("window.alert=function(){};window.confirm=function(){return false};"
                   "window.prompt=function(){return null};window.onbeforeunload=null;'guard'")

# Classic-page identity. If nlapiGetContext is missing (a login / Notice page) we say so instead of
# throwing, and main() turns that into "SESSION EXPIRED or not logged in".
IDENTITY_JS = ("(function(){try{if(typeof nlapiGetContext!=='function'){"
               "return JSON.stringify({ok:false,reason:'no-context'});}"
               "var c=nlapiGetContext();return JSON.stringify({ok:true,company:String(c.getCompany()),"
               "environment:String(c.getEnvironment())});}catch(e){"
               "return JSON.stringify({ok:false,reason:String(e)});}})()")


class SessionProblem(Exception):
    """exit 3: session/transport/dialog problem — stop, do not retry blindly."""


# ---- config --------------------------------------------------------------------
def resolve_config_path(args):
    cfg = getattr(args, "config", None)
    if cfg:
        return cfg
    env = os.environ.get("NS_READ_CONFIG")
    if env:
        return env
    return os.path.expanduser(DEFAULT_CONFIG)


def load_config(path):
    if not path:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return {}
    return d if isinstance(d, dict) else {}


# ---- guards / validation (all before any browser call) --------------------------
def host_for(account):
    return account.lower().replace("_", "-") + ".app.netsuite.com"


def _sanitize_sql(sql):
    """Drop /* */ and -- comments and the contents of '...' literals, then return the rest.

    A single left-to-right scan so a quote/comment marker inside a string literal is not treated
    as a comment (and vice versa)."""
    out = []
    i, n = 0, len(sql)
    while i < n:
        if sql.startswith("--", i):
            j = sql.find("\n", i)
            if j == -1:
                break
            i = j + 1
            out.append(" ")
            continue
        if sql.startswith("/*", i):
            j = sql.find("*/", i + 2)
            i = n if j == -1 else j + 2
            out.append(" ")
            continue
        if sql[i] == "'":
            i += 1
            while i < n:
                if sql[i] == "'":
                    if i + 1 < n and sql[i + 1] == "'":  # doubled quote = escaped
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            out.append("''")
            continue
        out.append(sql[i])
        i += 1
    return "".join(out)


def validate_sql(sql):
    """Return an error string, or None when the statement is a single read-only SELECT/WITH."""
    if sql is None:
        return "SQL is empty"
    if len(sql) > MAX_SQL_LEN:
        return "SQL is too long (%d > %d chars)" % (len(sql), MAX_SQL_LEN)
    sig = _sanitize_sql(sql).strip()
    if not sig:
        return "SQL is empty"
    if ";" in sig:
        return "SQL must be a single statement (contains ';')"
    m = FIRST_WORD_RE.match(sig)
    word = m.group(1) if m else ""
    if word.upper() not in ("SELECT", "WITH"):
        return "SQL must start with SELECT or WITH (got %r)" % (word or sig[:20])
    bad = FORBIDDEN_RE.search(sig)
    if bad:
        return "SQL contains a forbidden keyword: %s" % bad.group(1).upper()
    return None


def validate_bridge_path(path):
    if not path:
        return "missing bridge path (pass --bridge-path or set dev_bridge.endpoints in the config)"
    if not BRIDGE_PATH_RE.match(path):
        return "bridge path not allowed: %r" % path
    if not any(m in path for m in BRIDGE_MARKERS):
        return ("bridge path is not a Dev Bridge endpoint (needs action=dbgQuery, action=dbgRecord "
                "or step=DEBUG_QUERY): %r" % path)
    return None


# ---- bsk plumbing --------------------------------------------------------------
def _pick(d, *keys):
    if not isinstance(d, dict):
        return None
    for k in keys:
        v = d.get(k)
        if v not in (None, ""):
            return v
    return None


def _bsk_run(cmd_args, timeout=60):
    """Run one `bsk ...` command (BSK_AUTO_START=0). Returns (parsed_json, error)."""
    env = dict(os.environ, BSK_AUTO_START="0")
    cmd = ["bsk"] + list(cmd_args)
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
    return d, None


def _bsk_eval(expr, timeout=60):
    """One `bsk evaluate` on this run's pinned tab. Returns the value; raises SessionProblem."""
    d, err = _bsk_run(["evaluate", expr, "--session", ST["session"], "--tab-id", ST["tab"], "--json"],
                      timeout)
    if err:
        raise SessionProblem(err)
    if d.get("dialogs"):
        raise SessionProblem("native dialog fired (guard leaked): %s" % json.dumps(d["dialogs"])[:200])
    return d.get("value")


def _identity():
    """Read company+environment in-page. Returns (company, environment) or None if not logged in."""
    v = _bsk_eval(IDENTITY_JS)
    if isinstance(v, dict):
        d = v
    elif isinstance(v, str):
        if v.strip().startswith("<"):
            raise SessionProblem("page is HTML; not a classic NetSuite session")
        try:
            d = json.loads(v)
        except ValueError:
            return None
    else:
        return None
    if not isinstance(d, dict) or not d.get("ok"):
        return None
    return str(d.get("company")), str(d.get("environment"))


def _fetch_js(path, body_obj):
    """Same-origin POST from the tab. json.dumps every interpolated value, never concatenate."""
    body_text = json.dumps(body_obj)
    return ("fetch(%s,{method:'POST',headers:{'Content-Type':'application/json'},body:%s})"
            ".then(function(r){return r.text();})" % (json.dumps(path), json.dumps(body_text)))


def _read_response(raw):
    """Turn the bridge text into (exit_code, result). 0 = ok, 1 = bridge error, 3 = session gone."""
    if not isinstance(raw, str):
        raw = json.dumps(raw)
    try:
        data = json.loads(raw)
    except ValueError:
        if raw.strip().startswith("<") or "Notice" in raw:
            print("SESSION EXPIRED or not logged in (bridge returned an HTML notice page)")
            return 3, None
        print("bridge returned an unparseable response:", raw[:200])
        return 1, None
    # the SB2 tester answers {"success": false, "message": ...} (no "error" key) — still a failure
    if isinstance(data, dict) and ("error" in data or data.get("success") is False):
        print(json.dumps(data, ensure_ascii=False))
        return 1, None
    return 0, data


def emit(account, environment, result, max_chars):
    ser = json.dumps(result, ensure_ascii=False, default=str)
    out = {"account": account, "environment": environment}
    if isinstance(max_chars, int) and max_chars >= 0 and len(ser) > max_chars:
        out["result"] = ser[:max_chars]
        out["truncated"] = True
    else:
        out["result"] = result
    print(json.dumps(out, ensure_ascii=False))


# ---- CLI -----------------------------------------------------------------------
def _global_flags():
    # SUPPRESS so that a subparser (which re-parses into a fresh namespace and copies it back)
    # cannot clobber a global flag given BEFORE the subcommand. A missing flag stays absent, so
    # main() reads it with getattr().
    g = argparse.ArgumentParser(add_help=False)
    g.add_argument("--allow-prod-read", action="store_true", default=argparse.SUPPRESS,
                   help="allow reading a non-sandbox account; prints a WARNING and continues")
    g.add_argument("--engine", choices=["bsk", "cdp"], default=argparse.SUPPRESS,
                   help="default: the config's `engine` key (bsk)")
    g.add_argument("--config", default=argparse.SUPPRESS,
                   help="config JSON path (env NS_READ_CONFIG overrides)")
    return g


def build_parser():
    g = _global_flags()
    ap = argparse.ArgumentParser(description="Scoped, read-only NetSuite reader (Dev Bridge).",
                                 parents=[g])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("whoami", parents=[g], help="prove account identity, read nothing else")
    p.add_argument("--account", required=True, help="e.g. 4089685_SB2 or 4089685")

    p = sub.add_parser("query", parents=[g], help="run one SELECT/WITH via the Dev Bridge")
    p.add_argument("--account", required=True, help="e.g. 4089685_SB2 or 4089685")
    p.add_argument("--bridge-path", default=None, help="Dev Bridge scriptlet URL (config fallback)")
    p.add_argument("--body-style", choices=["q", "sql"], default=None,
                   help="'q' -> {q} (default); 'sql' -> {qtype,sql}")
    p.add_argument("--max-chars", type=int, default=20000, help="cut the serialized result here")
    p.add_argument("sql", help="a single SELECT/WITH statement")

    p = sub.add_parser("record", parents=[g], help="read one record via action=dbgRecord")
    p.add_argument("--account", required=True, help="e.g. 4089685_SB2 or 4089685")
    p.add_argument("--bridge-path", default=None, help="Dev Bridge scriptlet URL (config fallback)")
    p.add_argument("--type", required=True, help="record type id (e.g. salesorder)")
    p.add_argument("--id", required=True, help="record internal id")
    p.add_argument("--max-chars", type=int, default=20000, help="cut the serialized result here")

    return ap


def main(argv=None):
    args = build_parser().parse_args(argv)

    # ---- engine (config default) -----------------------------------------------
    cfg = load_config(resolve_config_path(args))
    engine = getattr(args, "engine", None) or cfg.get("engine") or "bsk"
    if engine != "bsk":
        if engine == "cdp":
            print("engine cdp is not implemented in ns_read.py yet")
        else:
            print("engine %s is not implemented in ns_read.py yet" % engine)
        return 2

    # ---- account -> host --------------------------------------------------------
    account = args.account
    if not ACCOUNT_RE.match(account):
        print("refused: --account must look like 4089685_SB2 or 4089685 (got %r)" % account)
        return 2
    host = host_for(account)

    # ---- validation BEFORE any browser call ------------------------------------
    path = None
    body_style = "q"
    if args.cmd in ("query", "record"):
        path = args.bridge_path
        if not path:
            endpoints = (cfg.get("dev_bridge") or {}).get("endpoints") or {}
            entry = endpoints.get(account) or {}
            path = entry.get("path")
            body_style = entry.get("body_style") or "q"
        if args.cmd == "record" and path:
            path = path.replace("dbgQuery", "dbgRecord")
        err = validate_bridge_path(path)
        if err:
            print("refused:", err)
            return 2
        if getattr(args, "body_style", None):
            body_style = args.body_style
        if body_style not in ("q", "sql"):
            print("refused: unknown body_style %r (want q or sql)" % body_style)
            return 2
        if args.cmd == "query":
            err = validate_sql(args.sql)
            if err:
                print("refused:", err)
                return 2
        else:
            if not RECORD_TYPE_RE.match(args.type):
                print("refused: --type must be [A-Za-z0-9_]+ (got %r)" % args.type)
                return 2
            if not RECORD_ID_RE.match(args.id):
                print("refused: --id must be digits (got %r)" % args.id)
                return 2

    # ---- browser: own session, always stopped ----------------------------------
    ST["session"] = None
    ST["tab"] = None
    session = None
    try:
        d, err = _bsk_run(["session", "start", "--no-focus", "--name", "ns-read", "--json"])
        if err:
            print("could not start bsk session:", err)
            return 3
        session = _pick(d, "session_id", "sessionId", "id")
        if not session:
            print("could not start bsk session: no session id")
            return 3
        ST["session"] = session

        d, err = _bsk_run(["tab", "create", "--no-active", "--url", "about:blank",
                           "--session", session, "--json"])
        if err:
            print("could not create bsk tab:", err)
            return 3
        tab = _pick(d, "tab_id", "tabId", "id")
        if not tab:
            print("could not create bsk tab: no tab id")
            return 3
        tab = str(tab)  # bsk returns a JSON number; subprocess argv must be str
        ST["tab"] = tab

        url = "https://%s/app/center/card.nl?sc=-29&whence=" % host
        d, err = _bsk_run(["navigate", url, "--wait-until", "domcontentloaded",
                           "--session", session, "--tab-id", tab, "--json"])
        if err:
            print("could not navigate to NetSuite:", err)
            return 3

        # dialog guard first, then the mandatory identity gate, before anything is read
        _bsk_eval(DIALOG_GUARD_JS)
        ident = _identity()
        if ident is None:
            print("SESSION EXPIRED or not logged in")
            return 3
        company, env = ident
        if company != account:
            print("wrong account: page is %r but --account is %r" % (company, account))
            return 2
        allow_prod = getattr(args, "allow_prod_read", False)
        if str(env).upper() != "SANDBOX" and not allow_prod:
            print("refused: %s is not a sandbox (environment=%r) and data read from it goes to "
                  "whichever model is running this script; re-run with --allow-prod-read to proceed."
                  % (account, env))
            return 2
        if str(env).upper() != "SANDBOX":
            print("WARNING: --allow-prod-read — reading LIVE data from a NON-sandbox account "
                  "(%s, environment=%s)." % (account, env))

        if args.cmd == "whoami":
            print(json.dumps({"account": account, "environment": env}, ensure_ascii=False))
            return 0

        if args.cmd == "query":
            body_obj = {"q": args.sql} if body_style == "q" else {"qtype": "sql", "sql": args.sql}
        else:
            body_obj = {"type": args.type, "id": args.id}

        raw = _bsk_eval(_fetch_js(path, body_obj))
        code, result = _read_response(raw)
        if code != 0:
            return code
        emit(account, env, result, args.max_chars)
        return 0
    except SessionProblem as e:
        print("SESSION/TRANSPORT problem:", e)
        return 3
    finally:
        if session:
            _bsk_run(["session", "stop", session])


if __name__ == "__main__":
    sys.exit(main())
