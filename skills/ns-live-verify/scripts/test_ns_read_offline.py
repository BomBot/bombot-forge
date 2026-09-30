#!/usr/bin/env python3
"""Offline tests for ns_read.py — no browser, no network, no real bsk.

The whole bsk layer is stubbed by replacing the loaded module's `_bsk_run` (the single function that
shells out to `bsk`). The stub decodes the JSON body of every fetch the script sends, so the tests
assert on WHAT is sent to the Dev Bridge, not only on exit codes. Only the accounts "4089685_SB2" and
"4089685" are used.
"""
import importlib.util
import io
import json
import os
import re
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPT = os.path.join(_HERE, "ns_read.py")

ACCOUNT = "4089685_SB2"
PROD_ACCOUNT = "4089685"
DEFAULT_PATH = ("/app/site/hosting/scriptlet.nl?script=customscript_teibto_dev_bridge"
                "&deploy=customdeploy_teibto_dev_bridge")
OTHER_PATH = "/app/site/hosting/scriptlet.nl?script=customscript_other_bridge&deploy=customdeploy_other_bridge"


def load_module():
    """Load ns_read.py from this file's directory (no absolute hard-coded path)."""
    spec = importlib.util.spec_from_file_location("ns_read_under_test", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def ping_reply(account=ACCOUNT, env="SANDBOX"):
    return {"ok": True, "action": "ping", "version": "test", "account": account, "envType": env,
            "user": {"id": 1, "role": 3, "roleId": "administrator", "isAdmin": True}, "serverTime": "t"}


class FakeBsk:
    """Records every bsk command; answers with canned JSON. Never a subprocess."""

    def __init__(self, company=ACCOUNT, env="SANDBOX", ping=None, reply=None, dialogs=None,
                 start_error=None, identity=None, int_tab=False):
        self.company, self.env = company, env
        self.ping = json.dumps(ping_reply(company, env)) if ping is None else ping
        self.reply = json.dumps({"ok": True}) if reply is None else reply
        self.dialogs, self.start_error, self.identity, self.int_tab = dialogs, start_error, identity, int_tab
        self.calls = []
        self.bodies = []      # decoded POST bodies, in order
        self.paths = []       # the scriptlet path of each fetch

    @staticmethod
    def decode(expr):
        path = json.loads(re.match(r'fetch\(("(?:[^"\\]|\\.)*")', expr).group(1))
        lit = re.search(r"body:(\"(?:[^\"\\]|\\.)*\")\}\)", expr).group(1)
        return path, json.loads(json.loads(lit))

    def __call__(self, cmd_args, timeout=60):
        self.calls.append(list(cmd_args))
        c = cmd_args[0]
        if c == "session" and cmd_args[1] == "start":
            return (None, self.start_error) if self.start_error else ({"ok": True, "session_id": "sess-read"}, None)
        if c == "session" and cmd_args[1] == "stop":
            return {"ok": True}, None
        if c == "tab":
            return {"ok": True, "tab_id": 4242 if self.int_tab else "tab-read"}, None
        if c == "navigate":
            return {"ok": True}, None
        if c == "evaluate":
            expr = cmd_args[1]
            if self.dialogs is not None:
                return {"ok": True, "value": "x", "dialogs": self.dialogs}, None
            if "nlapiGetContext" in expr:
                v = self.identity if self.identity is not None else json.dumps(
                    {"ok": True, "company": self.company, "environment": self.env})
                return {"ok": True, "value": v}, None
            if expr.startswith("fetch("):
                path, body = self.decode(expr)
                self.paths.append(path)
                self.bodies.append(body)
                return {"ok": True, "value": self.ping if body.get("action") == "ping" else self.reply}, None
            return {"ok": True, "value": "guard"}, None
        return {"ok": True}, None

    def stopped(self):
        return any(c[:2] == ["session", "stop"] for c in self.calls)

    def real_bodies(self):
        return [b for b in self.bodies if b.get("action") != "ping"]


class OfflineReadTest(unittest.TestCase):
    def setUp(self):
        self.mod = load_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = self._cfg({"engine": "bsk"}, "browser.json")

    def tearDown(self):
        self.tmp.cleanup()

    def _cfg(self, data, name):
        path = os.path.join(self.tmp.name, name)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return path

    def invoke(self, args, fake):
        old = self.mod._bsk_run
        self.mod._bsk_run = fake
        buf = io.StringIO()
        try:
            with redirect_stdout(buf):
                code = self.mod.main(args)
        finally:
            self.mod._bsk_run = old
        return code, buf.getvalue()

    def run_cmd(self, argv, fake=None, account=ACCOUNT):
        fake = fake or FakeBsk()
        code, out = self.invoke(argv[:1] + ["--account", account, "--config", self.cfg] + argv[1:], fake)
        return code, out, fake

    # ================= SQL validator (each layer must work ON ITS OWN) =================
    def test_sql_accepts(self):
        for sql in ["SELECT id FROM account", "select 1", "SELECT id FROM t WHERE memo = 'a delete b'",
                    "SELECT 1 FROM dual -- trailing; note\n", "/* header; */ SELECT 1 FROM dual",
                    "SELECT 1 /* a; b */ FROM dual"]:
            with self.subTest(sql=sql):
                self.assertIsNone(self.mod.validate_sql(sql), sql)

    def test_sql_rejects(self):
        for sql in ["SELECT 1; DROP TABLE t", "UPDATE t SET a=1", "DELETE FROM t",
                    "SELECT 1 /* x */; DELETE FROM t", "-- x\nDELETE FROM t", "SELECT 2 FROM t WHERE a=1;",
                    "", "   ", "insert into t values (1)", "x" * 6000,
                    "WITH x AS (SELECT 1 FROM dual) SELECT * FROM x"]:
            with self.subTest(sql=sql[:40]):
                self.assertIsNotNone(self.mod.validate_sql(sql), sql[:40])

    def test_forbidden_keyword_layer_alone(self):
        for sql in ["SELECT 1 FROM t WHERE a IN (INSERT INTO u VALUES (1))",
                    "SELECT 1 FROM dual /* hides nothing */ MERGE INTO t USING u ON (1=1)",
                    "SELECT 1 FROM t WHERE x = 1 GRANT ALL"]:
            with self.subTest(sql=sql):
                self.assertIsNotNone(self.mod.validate_sql(sql), sql)

    def test_first_word_layer_alone(self):
        for sql in ["EXPLAIN SELECT 1 FROM dual", "SHOW TABLES", "DESCRIBE account", "SELECTX id FROM account",
                    "(SELECT 1 FROM dual)", "WITH x AS (SELECT 1 FROM dual) SELECT * FROM x"]:
            with self.subTest(sql=sql):
                self.assertIsNotNone(self.mod.validate_sql(sql), sql)

    def test_rejected_query_never_starts_a_session(self):
        code, out, fake = self.run_cmd(["query", "SELECT 1; DROP TABLE t"])
        self.assertEqual(code, 2)
        self.assertEqual(fake.calls, [])

    # ================= bridge path =================
    def test_bridge_path_validation(self):
        v = self.mod.validate_bridge_path
        self.assertIsNone(v(DEFAULT_PATH))
        self.assertIsNone(v(OTHER_PATH))
        # numeric ids are fine (built with %d so the redaction CI does not read a literal script=<digits>)
        self.assertIsNone(v("/app/site/hosting/scriptlet.nl?script=%d&deploy=%d" % (17, 1)))
        for bad in ["/app/x", "", None, DEFAULT_PATH + "&action=query", DEFAULT_PATH + "&x=1",
                    '/app/site/hosting/scriptlet.nl?script="x"&deploy=1',
                    "https://evil.example/app/site/hosting/scriptlet.nl?script=a&deploy=b",
                    "/app/site/hosting/scriptlet.nl?deploy=b&script=a"]:
            with self.subTest(path=bad):
                self.assertIsNotNone(v(bad), bad)

    def test_bad_cli_bridge_path_never_starts_a_session(self):
        code, out, fake = self.run_cmd(["query", "--bridge-path", "/app/x", "SELECT 1 FROM dual"])
        self.assertEqual(code, 2)
        self.assertEqual(fake.calls, [])

    def test_path_precedence_cli_then_config_then_default(self):
        cfg = self._cfg({"engine": "bsk", "dev_bridge": {"endpoints": {ACCOUNT: {"path": OTHER_PATH}}}}, "e.json")
        fake = FakeBsk()
        self.invoke(["ping", "--account", ACCOUNT, "--config", cfg], fake)
        self.assertEqual(set(fake.paths), {OTHER_PATH})
        fake = FakeBsk()
        self.invoke(["ping", "--account", ACCOUNT, "--config", cfg, "--bridge-path", DEFAULT_PATH], fake)
        self.assertEqual(set(fake.paths), {DEFAULT_PATH})
        fake = FakeBsk()
        self.invoke(["ping", "--account", ACCOUNT, "--config", self.cfg], fake)
        self.assertEqual(set(fake.paths), {DEFAULT_PATH})

    # ================= identity / environment gate =================
    def test_wrong_account_exit_2_and_session_stopped(self):
        code, out, fake = self.run_cmd(["query", "SELECT 1 FROM dual"], FakeBsk(company="4089685_SB9"))
        self.assertEqual(code, 2)
        self.assertEqual(fake.bodies, [])
        self.assertTrue(fake.stopped())

    def test_login_page_exit_3_and_session_stopped(self):
        code, out, fake = self.run_cmd(["whoami"], FakeBsk(identity=json.dumps({"ok": False, "reason": "no-context"})))
        self.assertEqual(code, 3)
        self.assertIn("SESSION EXPIRED", out)
        self.assertTrue(fake.stopped())

    def test_dialog_aborts_exit_3(self):
        code, out, fake = self.run_cmd(["whoami"], FakeBsk(dialogs=[{"type": "confirm"}]))
        self.assertEqual(code, 3)
        self.assertTrue(fake.stopped())

    def test_prod_refused_without_flag_and_nothing_fetched(self):
        code, out, fake = self.run_cmd(["query", "SELECT 1 FROM dual"], FakeBsk(company=PROD_ACCOUNT, env="PRODUCTION"),
                                       account=PROD_ACCOUNT)
        self.assertEqual(code, 2)
        self.assertEqual(fake.bodies, [])
        self.assertIn("--allow-prod-read", out)
        self.assertTrue(fake.stopped())

    def test_prod_allowed_with_flag_warns(self):
        fake = FakeBsk(company=PROD_ACCOUNT, env="PRODUCTION", reply=json.dumps({"ok": True, "rows": []}))
        code, out = self.invoke(["--allow-prod-read", "query", "--account", PROD_ACCOUNT, "--config", self.cfg,
                                 "SELECT 1 FROM dual"], fake)
        self.assertEqual(code, 0)
        self.assertIn("WARNING", out)
        self.assertEqual(len(fake.real_bodies()), 1)

    # ================= the bridge itself is verified before the real request =================
    def test_endpoint_that_does_not_answer_ping_like_the_bridge_is_refused(self):
        fake = FakeBsk(ping=json.dumps({"ok": True, "something": "else"}))
        code, out, fake = self.run_cmd(["query", "SELECT 1 FROM dual"], fake)
        self.assertEqual(code, 2)
        self.assertEqual(fake.real_bodies(), [])

    def test_each_part_of_the_ping_shape_is_required(self):
        good = ping_reply()
        for name, mangle in [("no action", lambda d: d.pop("action")), ("wrong action", lambda d: d.update(action="help")),
                             ("no envType", lambda d: d.pop("envType")), ("no version", lambda d: d.pop("version")),
                             ("not a dict", None)]:
            with self.subTest(name):
                d = dict(good)
                if mangle:
                    mangle(d)
                ping = json.dumps(d) if mangle else json.dumps([1, 2])
                code, out, fake = self.run_cmd(["query", "SELECT 1 FROM dual"], FakeBsk(ping=ping))
                self.assertEqual(code, 2, out)
                self.assertEqual(fake.real_bodies(), [])

    def test_bridge_reporting_another_account_is_refused(self):
        fake = FakeBsk(ping=json.dumps(ping_reply("4089685_SB9")))
        code, out, fake = self.run_cmd(["query", "SELECT 1 FROM dual"], fake)
        self.assertEqual(code, 2)
        self.assertEqual(fake.real_bodies(), [])

    def test_whoami_makes_no_bridge_call(self):
        code, out, fake = self.run_cmd(["whoami"])
        self.assertEqual(code, 0)
        self.assertEqual(fake.bodies, [])
        self.assertEqual(json.loads(out), {"account": ACCOUNT, "environment": "SANDBOX"})

    def test_ping_command_sends_only_the_verifying_ping(self):
        code, out, fake = self.run_cmd(["ping"])
        self.assertEqual(code, 0)
        self.assertEqual(fake.bodies, [{"action": "ping"}])
        self.assertEqual(json.loads(out)["result"]["envType"], "SANDBOX")

    # ================= exactly what is sent, per subcommand =================
    def test_request_bodies(self):
        cases = [
            (["query", "SELECT id FROM account"], {"action": "query", "q": "SELECT id FROM account", "params": []}),
            (["record", "--type", "salesorder", "--id", "123"], {"action": "record", "type": "salesorder", "id": 123}),
            (["record", "--type", "salesorder", "--id", "123", "--fields", "tranid,entity.email", "--meta"],
             {"action": "record", "type": "salesorder", "id": 123, "fields": ["tranid", "entity.email"], "meta": True}),
            (["lookup", "--type", "item", "--id", "7", "--columns", "itemid,displayname"],
             {"action": "lookup", "type": "item", "id": 7, "columns": ["itemid", "displayname"]}),
            (["feature", "--names", "binmanagement,subsidiaries"],
             {"action": "feature", "names": ["binmanagement", "subsidiaries"]}),
            (["search", "--search-id", "customsearch_x", "--limit", "50"],
             {"action": "search", "searchId": "customsearch_x", "limit": 50}),
            (["search", "--type", "transaction", "--filters-json", '[["type","anyof","SalesOrd"]]',
              "--columns", "tranid,entity"],
             {"action": "search", "type": "transaction", "limit": 200, "filters": [["type", "anyof", "SalesOrd"]],
              "columns": ["tranid", "entity"]}),
        ]
        for argv, expected in cases:
            with self.subTest(argv=argv):
                code, out, fake = self.run_cmd(argv)
                self.assertEqual(code, 0, out)
                self.assertEqual(fake.real_bodies(), [expected])
                self.assertEqual(fake.bodies[0], {"action": "ping"})   # verified first

    def test_a_query_with_both_quote_kinds_round_trips_unchanged(self):
        sql = "SELECT id FROM t WHERE a = 'x' AND b = \"y\" AND c = '\\'"
        code, out, fake = self.run_cmd(["query", sql])
        self.assertEqual(code, 0)
        self.assertEqual(fake.real_bodies()[0]["q"], sql)

    def test_argument_validation_refuses_before_any_browser_call(self):
        bad = [
            ["record", "--type", "sales order", "--id", "1"], ["record", "--type", "salesorder", "--id", "1x"],
            ["record", "--type", "salesorder", "--id", "1", "--fields", "a b"],
            ["record", "--type", "salesorder", "--id", "1", "--fields", "a;b"],
            ["lookup", "--type", "item", "--id", "1", "--columns", ","], ["lookup", "--type", "item", "--id", "x", "--columns", "a"],
            ["feature", "--names", "a,b c"], ["feature", "--names", ""],
            ["search"], ["search", "--search-id", "a", "--type", "b"], ["search", "--search-id", "a b"],
            ["search", "--search-id", "a", "--limit", "0"], ["search", "--search-id", "a", "--limit", "1001"],
            ["search", "--type", "t", "--filters-json", "{not json"], ["search", "--type", "t", "--filters-json", '{"a":1}'],
            ["search", "--type", "t", "--filters-json", "[" + "1," * 3000 + "1]"],
            ["search", "--type", "t", "--columns", "a,b;c"],
        ]
        for argv in bad:
            with self.subTest(argv=argv):
                code, out, fake = self.run_cmd(argv)
                self.assertEqual(code, 2, out)
                self.assertEqual(fake.calls, [])

    # ================= bridge answers =================
    def test_ok_false_from_the_bridge_is_exit_1(self):
        for reply in [{"ok": False, "error": "Unknown identifier", "code": "INTERNAL"},
                      {"success": False, "message": "Unknown identifier"}, {"error": "boom"}]:
            with self.subTest(reply=reply):
                code, out, fake = self.run_cmd(["query", "SELECT x FROM account"], FakeBsk(reply=json.dumps(reply)))
                self.assertEqual(code, 1)
                self.assertIn("Unknown identifier" if "Unknown" in json.dumps(reply) else "boom", out)

    def test_ok_false_alone_is_enough_to_fail(self):
        code, out, fake = self.run_cmd(["query", "SELECT 1 FROM dual"],
                                       FakeBsk(reply=json.dumps({"ok": False, "message": "denied"})))
        self.assertEqual(code, 1)

    def test_html_notice_page_is_a_dead_session_exit_3(self):
        code, out, fake = self.run_cmd(["query", "SELECT 1 FROM dual"],
                                       FakeBsk(reply="<html><body>Notice: connection timed out</body></html>"))
        self.assertEqual(code, 3)
        self.assertTrue(fake.stopped())

    def test_word_notice_inside_real_data_is_not_a_dead_session(self):
        reply = json.dumps({"ok": True, "rows": [{"memo": "Notice of change"}], "count": 1})
        code, out, fake = self.run_cmd(["query", "SELECT memo FROM t"], FakeBsk(reply=reply))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["result"]["rows"][0]["memo"], "Notice of change")

    def test_truncation_flag(self):
        reply = json.dumps({"ok": True, "rows": [{"n": "x" * 500}]})
        code, out, fake = self.run_cmd(["query", "SELECT 1 FROM dual", "--max-chars", "100"], FakeBsk(reply=reply))
        d = json.loads(out)
        self.assertTrue(d["truncated"])
        self.assertEqual(len(d["result"]), 100)

    # ================= engine / flags / plumbing =================
    def test_cdp_engine_is_not_implemented(self):
        code, out = self.invoke(["--engine", "cdp", "whoami", "--account", ACCOUNT, "--config", self.cfg], FakeBsk())
        self.assertEqual(code, 2)
        cfg = self._cfg({"engine": "cdp"}, "cdp.json")
        fake = FakeBsk()
        code, out = self.invoke(["whoami", "--account", ACCOUNT, "--config", cfg], fake)
        self.assertEqual(code, 2)
        self.assertEqual(fake.calls, [])

    def test_global_flag_before_the_subcommand(self):
        fake = FakeBsk(company=PROD_ACCOUNT, env="PRODUCTION")
        code, out = self.invoke(["--allow-prod-read", "whoami", "--account", PROD_ACCOUNT, "--config", self.cfg], fake)
        self.assertEqual(code, 0)

    def test_bad_account_is_refused(self):
        for acct in ["", "abc", "4089685_SB2;rm", "4089685-sb2", "../x"]:
            with self.subTest(acct=acct):
                fake = FakeBsk()
                code, out = self.invoke(["whoami", "--account", acct, "--config", self.cfg], fake)
                self.assertEqual(code, 2)
                self.assertEqual(fake.calls, [])

    def test_numeric_tab_id_reaches_bsk_as_a_string(self):
        code, out, fake = self.run_cmd(["whoami"], FakeBsk(int_tab=True))
        self.assertEqual(code, 0)
        for c in fake.calls:
            if c[0] in ("navigate", "evaluate"):
                self.assertEqual(c[c.index("--tab-id") + 1], "4242")
                self.assertTrue(all(isinstance(x, str) for x in c), c)

    def test_every_parsed_bsk_command_asks_for_json(self):
        code, out, fake = self.run_cmd(["ping"])
        for c in fake.calls:
            if c[:2] != ["session", "stop"]:
                self.assertIn("--json", c, c)

    def test_session_bootstrap_and_stop_even_on_failure(self):
        code, out, fake = self.run_cmd(["ping"])
        starts = [c for c in fake.calls if c[:2] == ["session", "start"]]
        navs = [c for c in fake.calls if c[0] == "navigate"]
        self.assertEqual(len(starts), 1)
        self.assertIn("--no-focus", starts[0])
        self.assertIn("4089685-sb2.app.netsuite.com", navs[0][1])
        self.assertTrue(fake.stopped())
        code, out, fake = self.run_cmd(["ping"], FakeBsk(reply="x", ping="<html>Notice</html>"))
        self.assertTrue(fake.stopped())

    def test_session_start_failure_is_exit_3(self):
        code, out, fake = self.run_cmd(["ping"], FakeBsk(start_error="bsk transport: down"))
        self.assertEqual(code, 3)


    def test_repeating_account_is_refused_so_the_last_one_cannot_win(self):
        # the agent permission list matches "--account <listed>" by text; argparse would otherwise let a
        # later --account silently replace it
        fake = FakeBsk()
        with self.assertRaises(SystemExit) as cm:
            self.invoke(["ping", "--account", ACCOUNT, "--account", PROD_ACCOUNT, "--config", self.cfg], fake)
        self.assertEqual(cm.exception.code, 2)
        self.assertEqual(fake.calls, [])

    def test_single_account_in_equals_form_still_works(self):
        code, out = self.invoke(["whoami", "--account=" + ACCOUNT, "--config", self.cfg], FakeBsk())
        self.assertEqual(code, 0)


    def test_it_says_out_loud_that_it_is_opening_a_bsk_window(self):
        # the user asked to be told every time bsk is used
        old = self.mod._bsk_run
        self.mod._bsk_run = FakeBsk()
        out, err = io.StringIO(), io.StringIO()
        try:
            with redirect_stdout(out), redirect_stderr(err):
                self.mod.main(["ping", "--account", ACCOUNT, "--config", self.cfg])
        finally:
            self.mod._bsk_run = old
        text = err.getvalue()
        self.assertIn("bsk", text)
        self.assertIn(ACCOUNT, text)
        self.assertIn("background", text)
        self.assertIn("read-only", text)

    def test_stdout_stays_pure_json_for_a_successful_read(self):
        code, out, fake = self.run_cmd(["ping"])
        json.loads(out)   # raises if the notice leaked into stdout

    def test_expired_session_message_says_it_never_logs_in_and_how_to_check_autofill(self):
        code, out, fake = self.run_cmd(["whoami"], FakeBsk(identity=json.dumps({"ok": False, "reason": "no-context"})))
        self.assertEqual(code, 3)
        self.assertIn("never logs in", out)
        self.assertIn(":-webkit-autofill", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
