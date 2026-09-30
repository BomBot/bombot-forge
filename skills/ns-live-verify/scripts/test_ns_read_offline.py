#!/usr/bin/env python3
"""Offline tests for ns_read.py — no browser, no network, no real bsk.

The whole bsk layer is stubbed by replacing the loaded module's `_bsk_run` (the single function
that shells out to `bsk`). Nothing here ever invokes the real tool. Only the accounts
"4089685_SB2" and "4089685" are used.
"""
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPT = os.path.join(_HERE, "ns_read.py")

ACCOUNT = "4089685_SB2"
PROD_ACCOUNT = "4089685"
BRIDGE = "/app/site/hosting/scriptlet.nl?script=customscript_dev_bridge&deploy=1&action=dbgQuery"
BRIDGE_RECORD = BRIDGE.replace("dbgQuery", "dbgRecord")


def load_module():
    """Load ns_read.py from this file's directory (no absolute hard-coded path)."""
    spec = importlib.util.spec_from_file_location("ns_read_under_test", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeBsk:
    """Records every bsk command and answers with canned JSON. Never a subprocess."""

    def __init__(self, company=ACCOUNT, env="SANDBOX", fetch_text=None, dialogs=None,
                 start_error=None, identity=None):
        self.company = company
        self.env = env
        self.fetch_text = json.dumps({"ok": True}) if fetch_text is None else fetch_text
        self.dialogs = dialogs
        self.start_error = start_error
        self.identity = identity
        self.calls = []

    def __call__(self, cmd_args, timeout=60):
        self.calls.append(list(cmd_args))
        c = cmd_args[0]
        if c == "session" and len(cmd_args) > 1 and cmd_args[1] == "start":
            if self.start_error:
                return None, self.start_error
            return {"ok": True, "session_id": "sess-read"}, None
        if c == "session" and len(cmd_args) > 1 and cmd_args[1] == "stop":
            return {"ok": True}, None
        if c == "tab":
            return {"ok": True, "tab_id": "tab-read"}, None
        if c == "navigate":
            return {"ok": True}, None
        if c == "evaluate":
            expr = cmd_args[1]
            if self.dialogs is not None:
                return {"ok": True, "value": "x", "dialogs": self.dialogs}, None
            if "nlapiGetContext" in expr:
                if self.identity is not None:
                    return {"ok": True, "value": self.identity}, None
                return {"ok": True, "value": json.dumps(
                    {"ok": True, "company": self.company, "environment": self.env})}, None
            if "fetch(" in expr:
                return {"ok": True, "value": self.fetch_text}, None
            return {"ok": True, "value": "guard"}, None
        return {"ok": True}, None

    def eval_exprs(self):
        return [c[1] for c in self.calls if c[0] == "evaluate"]

    def fetch_expr(self):
        for e in self.eval_exprs():
            if "fetch(" in e:
                return e
        return None

    def stopped(self):
        return any(c[0] == "session" and len(c) > 1 and c[1] == "stop" for c in self.calls)


class OfflineReadTest(unittest.TestCase):
    def setUp(self):
        self.mod = load_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = self._write_cfg("bsk", os.path.join(self.tmp.name, "browser.json"))
        self.cfg_cdp = self._write_cfg("cdp", os.path.join(self.tmp.name, "cdp.json"))

    def tearDown(self):
        self.tmp.cleanup()

    def _write_cfg(self, engine, path):
        cfg = {"engine": engine, "dev_bridge": {"endpoints": {
            ACCOUNT: {"path": BRIDGE, "body_style": "q"},
            PROD_ACCOUNT: {"path": BRIDGE, "body_style": "q"},
        }}}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f)
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

    # ---- SQL validator, table-driven ----------------------------------------
    def test_sql_validator_accepts(self):
        for sql in ["SELECT id FROM account",
                    "select 1",
                    "WITH x AS (SELECT 1 FROM dual) SELECT * FROM x",
                    "SELECT 'a delete b' FROM t",
                    "SELECT * FROM t WHERE fullname LIKE '%Variance%'"]:
            with self.subTest(sql=sql):
                self.assertIsNone(self.mod.validate_sql(sql))

    def test_sql_validator_rejects(self):
        cases = ["SELECT 1; DROP TABLE t",
                 "UPDATE t SET a=1",
                 "DELETE FROM t",
                 "SELECT 1 /* x */; DELETE FROM t",
                 "-- x\nDELETE FROM t",
                 "SELECT 1 FROM t WHERE a=1 UNION SELECT 2; ",
                 "",
                 "insert into t values (1)"]
        for sql in cases:
            with self.subTest(sql=sql):
                self.assertIsNotNone(self.mod.validate_sql(sql))

    def test_sql_validator_rejects_too_long(self):
        sql = "SELECT '" + ("a" * 6000) + "'"
        self.assertIsNotNone(self.mod.validate_sql(sql))

    # ---- validation happens before any browser call -------------------------
    def test_rejected_query_never_starts_session(self):
        fake = FakeBsk()
        code, out = self.invoke(
            ["query", "--account", ACCOUNT, "--bridge-path", BRIDGE,
             "--config", self.cfg, "UPDATE t SET a=1"], fake)
        self.assertEqual(code, 2)
        self.assertIn("refused", out)
        self.assertEqual(fake.calls, [])  # no session start, no anything

    def test_bad_bridge_path_never_starts_session(self):
        fake = FakeBsk()
        for bad in ["/app/x",
                    '/app/site/hosting/scriptlet.nl?script="x"&deploy=1']:
            with self.subTest(path=bad):
                code, _ = self.invoke(
                    ["query", "--account", ACCOUNT, "--bridge-path", bad,
                     "--config", self.cfg, "SELECT 1 FROM dual"], fake)
                self.assertEqual(code, 2)
        self.assertEqual(fake.calls, [])

    def test_bridge_path_validation_direct(self):
        self.assertIsNone(self.mod.validate_bridge_path(BRIDGE))
        self.assertIsNotNone(self.mod.validate_bridge_path("/app/x"))
        self.assertIsNotNone(self.mod.validate_bridge_path(
            '/app/site/hosting/scriptlet.nl?script="x"&deploy=1'))

    # ---- identity / environment gate ---------------------------------------
    def test_wrong_account_exit_2_and_session_stopped(self):
        fake = FakeBsk(company=PROD_ACCOUNT, env="SANDBOX")
        code, out = self.invoke(["whoami", "--account", ACCOUNT, "--config", self.cfg], fake)
        self.assertEqual(code, 2)
        self.assertIn("wrong account", out.lower())
        self.assertTrue(fake.stopped())

    def test_login_page_exit_3_and_session_stopped(self):
        fake = FakeBsk(identity=json.dumps({"ok": False, "reason": "no-context"}))
        code, out = self.invoke(["whoami", "--account", ACCOUNT, "--config", self.cfg], fake)
        self.assertEqual(code, 3)
        self.assertIn("SESSION EXPIRED", out)
        self.assertTrue(fake.stopped())

    def test_dialog_guard_aborts_exit_3(self):
        fake = FakeBsk(dialogs=["confirm"])
        code, out = self.invoke(["whoami", "--account", ACCOUNT, "--config", self.cfg], fake)
        self.assertEqual(code, 3)
        self.assertIn("dialog", out.lower())
        self.assertTrue(fake.stopped())

    def test_sandbox_query_ok_without_flag(self):
        fake = FakeBsk(fetch_text=json.dumps({"rows": [{"id": 1}], "count": 1}))
        code, out = self.invoke(
            ["query", "--account", ACCOUNT, "--bridge-path", BRIDGE,
             "--config", self.cfg, "SELECT id FROM account"], fake)
        self.assertEqual(code, 0)
        d = json.loads(out)
        self.assertEqual(d["account"], ACCOUNT)
        self.assertEqual(d["environment"], "SANDBOX")
        self.assertEqual(d["result"], {"rows": [{"id": 1}], "count": 1})
        self.assertTrue(fake.stopped())

    def test_prod_refused_without_flag(self):
        fake = FakeBsk(company=PROD_ACCOUNT, env="PRODUCTION")
        code, out = self.invoke(
            ["query", "--account", PROD_ACCOUNT, "--bridge-path", BRIDGE,
             "--config", self.cfg, "SELECT 1 FROM dual"], fake)
        self.assertEqual(code, 2)
        self.assertIn("sandbox", out.lower())
        self.assertIsNone(fake.fetch_expr())  # no data was fetched
        self.assertTrue(fake.stopped())

    def test_prod_allowed_with_flag_warns(self):
        fake = FakeBsk(company=PROD_ACCOUNT, env="PRODUCTION",
                       fetch_text=json.dumps({"rows": []}))
        code, out = self.invoke(
            ["query", "--account", PROD_ACCOUNT, "--bridge-path", BRIDGE, "--allow-prod-read",
             "--config", self.cfg, "SELECT 1 FROM dual"], fake)
        self.assertEqual(code, 0)
        self.assertIn("WARNING", out)
        self.assertIsNotNone(fake.fetch_expr())

    # ---- bridge response handling -------------------------------------------
    def test_session_expired_bridge_page_exit_3(self):
        fake = FakeBsk(fetch_text="<html><title>Notice</title><body>timed out</body></html>")
        code, out = self.invoke(
            ["query", "--account", ACCOUNT, "--bridge-path", BRIDGE,
             "--config", self.cfg, "SELECT 1 FROM dual"], fake)
        self.assertEqual(code, 3)
        self.assertIn("SESSION EXPIRED", out)

    def test_bridge_error_exit_1(self):
        fake = FakeBsk(fetch_text=json.dumps({"error": "INVALID_SUITEQL"}))
        code, out = self.invoke(
            ["query", "--account", ACCOUNT, "--bridge-path", BRIDGE,
             "--config", self.cfg, "SELECT bad"], fake)
        self.assertEqual(code, 1)
        self.assertIn("INVALID_SUITEQL", out)

    def test_truncation_sets_flag(self):
        fake = FakeBsk(fetch_text=json.dumps({"rows": ["x" * 300]}))
        code, out = self.invoke(
            ["query", "--account", ACCOUNT, "--bridge-path", BRIDGE, "--max-chars", "20",
             "--config", self.cfg, "SELECT 1 FROM dual"], fake)
        self.assertEqual(code, 0)
        d = json.loads(out)
        self.assertTrue(d.get("truncated"))
        self.assertEqual(len(d["result"]), 20)

    # ---- record -------------------------------------------------------------
    def test_record_path_becomes_dbgRecord(self):
        fake = FakeBsk(fetch_text=json.dumps({"record": {"id": "12345"}}))
        code, out = self.invoke(
            ["record", "--account", ACCOUNT, "--bridge-path", BRIDGE,
             "--type", "salesorder", "--id", "12345", "--config", self.cfg], fake)
        self.assertEqual(code, 0)
        expr = fake.fetch_expr()
        self.assertIn(BRIDGE_RECORD.split("?")[1], expr)
        self.assertNotIn("dbgQuery", expr)
        d = json.loads(out)
        self.assertEqual(d["account"], ACCOUNT)
        self.assertEqual(d["result"], {"record": {"id": "12345"}})

    def test_record_bad_type_and_id_refused(self):
        for extra in (["--type", "foo-bar", "--id", "1"], ["--type", "salesorder", "--id", "12x"]):
            with self.subTest(extra=extra):
                fake = FakeBsk()
                code, _ = self.invoke(
                    ["record", "--account", ACCOUNT, "--bridge-path", BRIDGE,
                     "--config", self.cfg] + extra, fake)
                self.assertEqual(code, 2)
                self.assertEqual(fake.calls, [])

    # ---- JS construction ----------------------------------------------------
    def test_query_js_escapes_both_quotes(self):
        sql = 'SELECT \'a"b\' FROM account'
        fake = FakeBsk(fetch_text=json.dumps({"rows": []}))
        code, _ = self.invoke(
            ["query", "--account", ACCOUNT, "--bridge-path", BRIDGE,
             "--config", self.cfg, sql], fake)
        self.assertEqual(code, 0)
        expr = fake.fetch_expr()
        self.assertIsNotNone(expr)
        # the interpolated body is json.dumps-escaped, so neither raw quote can break out
        self.assertIn(json.dumps(json.dumps({"q": sql})), expr)
        self.assertNotIn(sql, expr)
        self.assertIn('\\"', expr)

    def test_body_style_sql(self):
        sql = "SELECT 1 FROM dual"
        fake = FakeBsk(fetch_text=json.dumps({"rows": []}))
        code, _ = self.invoke(
            ["query", "--account", ACCOUNT, "--bridge-path", BRIDGE, "--body-style", "sql",
             "--config", self.cfg, sql], fake)
        self.assertEqual(code, 0)
        self.assertIn(json.dumps(json.dumps({"qtype": "sql", "sql": sql})), fake.fetch_expr())

    # ---- engine / config ----------------------------------------------------
    def test_engine_cdp_not_implemented(self):
        code, out = self.invoke(
            ["whoami", "--account", ACCOUNT, "--engine", "cdp", "--config", self.cfg],
            FakeBsk())
        self.assertEqual(code, 2)
        self.assertIn("engine cdp is not implemented", out)

    def test_engine_default_from_config_is_cdp(self):
        code, out = self.invoke(["whoami", "--account", ACCOUNT, "--config", self.cfg_cdp],
                                FakeBsk())
        self.assertEqual(code, 2)
        self.assertIn("engine cdp is not implemented", out)

    def test_global_flags_before_subcommand(self):
        # a global flag placed BEFORE the subcommand must not be clobbered by subparser defaults
        fake = FakeBsk()
        code, out = self.invoke(
            ["--engine", "cdp", "--config", self.cfg, "whoami", "--account", ACCOUNT], fake)
        self.assertEqual(code, 2)
        self.assertIn("engine cdp is not implemented", out)
        self.assertEqual(fake.calls, [])

    def test_config_provides_bridge_path(self):
        fake = FakeBsk(fetch_text=json.dumps({"rows": []}))
        code, _ = self.invoke(
            ["query", "--account", ACCOUNT, "--config", self.cfg, "SELECT 1 FROM dual"], fake)
        self.assertEqual(code, 0)
        self.assertIn("action=dbgQuery", fake.fetch_expr())

    # ---- bsk session bootstrap ---------------------------------------------
    def test_session_bootstrap_and_stop(self):
        fake = FakeBsk(fetch_text=json.dumps({"rows": []}))
        code, _ = self.invoke(
            ["query", "--account", ACCOUNT, "--bridge-path", BRIDGE,
             "--config", self.cfg, "SELECT 1 FROM dual"], fake)
        self.assertEqual(code, 0)
        starts = [c for c in fake.calls if c[0] == "session" and c[1] == "start"]
        tabs = [c for c in fake.calls if c[0] == "tab"]
        navs = [c for c in fake.calls if c[0] == "navigate"]
        self.assertEqual(len(starts), 1)
        self.assertEqual(len(tabs), 1)
        self.assertEqual(len(navs), 1)
        self.assertIn("--no-focus", starts[0])
        self.assertIn("--session", tabs[0])
        self.assertIn("4089685-sb2.app.netsuite.com", navs[0][1])
        self.assertTrue(fake.stopped())


    # ---- added after review: three real defects the first draft let through --------
    def test_numeric_tab_id_is_passed_to_bsk_as_string(self):
        # bsk's JSON returns tab_id as a NUMBER; subprocess argv must be str
        class IntTabBsk(FakeBsk):
            def __call__(self, cmd_args, timeout=60):
                if cmd_args[0] == "tab":
                    self.calls.append(list(cmd_args))
                    return {"ok": True, "tab_id": 4242}, None
                return FakeBsk.__call__(self, cmd_args, timeout)
        fake = IntTabBsk()
        code, _ = self.invoke(["whoami", "--account", ACCOUNT, "--config", self.cfg], fake)
        self.assertEqual(code, 0)
        after_tab = [c for c in fake.calls if c[0] in ("navigate", "evaluate")]
        self.assertTrue(after_tab)
        for c in after_tab:
            self.assertEqual(c[c.index("--tab-id") + 1], "4242")
            self.assertTrue(all(isinstance(x, str) for x in c), c)

    def test_only_the_dev_bridge_is_allowed_not_any_suitelet(self):
        fake = FakeBsk()
        other = "/app/site/hosting/scriptlet.nl?script=customscript_other&deploy=1"
        code, _ = self.invoke(["query", "--account", ACCOUNT, "--bridge-path", other,
                               "--config", self.cfg, "SELECT 1 FROM dual"], fake)
        self.assertEqual(code, 2)
        self.assertEqual(fake.calls, [])
        self.assertIsNotNone(self.mod.validate_bridge_path(other))
        for ok in (BRIDGE, BRIDGE_RECORD,
                   "/app/site/hosting/scriptlet.nl?script=customscript_x&deploy=1&step=DEBUG_QUERY"):
            self.assertIsNone(self.mod.validate_bridge_path(ok), ok)

    def test_word_notice_inside_real_data_is_not_a_dead_session(self):
        fake = FakeBsk(fetch_text=json.dumps({"rows": [{"memo": "Notice of change"}], "count": 1}))
        code, out = self.invoke(["query", "--account", ACCOUNT, "--bridge-path", BRIDGE,
                                 "--config", self.cfg, "SELECT memo FROM t"], fake)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["result"]["rows"][0]["memo"], "Notice of change")


    # ---- each SQL defence must work ON ITS OWN (the layers used to mask one another) ------
    def test_forbidden_keyword_layer_alone(self):
        # starts with WITH, single statement, no ';' -> only the keyword check can stop these
        for sql in ["WITH x AS (SELECT 1 FROM dual) DELETE FROM t",
                    "WITH x AS (SELECT 1 FROM dual) UPDATE t SET a = 1",
                    "SELECT 1 FROM t WHERE a IN (INSERT INTO u VALUES (1))",
                    "SELECT 1 FROM dual /* hides nothing */ MERGE INTO t USING u ON (1=1)"]:
            with self.subTest(sql=sql):
                self.assertIsNotNone(self.mod.validate_sql(sql), sql)

    def test_first_word_layer_alone(self):
        # no forbidden keyword and no ';' -> only the SELECT/WITH start check can stop these
        for sql in ["EXPLAIN SELECT 1 FROM dual", "SHOW TABLES", "DESCRIBE account",
                    "SELECTX id FROM account", "(SELECT 1 FROM dual)"]:
            with self.subTest(sql=sql):
                self.assertIsNotNone(self.mod.validate_sql(sql), sql)

    def test_comments_are_stripped_before_judging(self):
        # a ';' or a leading comment inside comments must not cause a false refusal
        for sql in ["SELECT 1 FROM dual -- trailing; note\n",
                    "/* header; */ SELECT 1 FROM dual",
                    "SELECT 1 /* a; b */ FROM dual"]:
            with self.subTest(sql=sql):
                self.assertIsNone(self.mod.validate_sql(sql), sql)


    def test_every_bsk_command_we_parse_asks_for_json(self):
        # live testing: `bsk navigate` without --json prints plain text and _bsk_run's JSON parse failed
        fake = FakeBsk()
        self.invoke(["whoami", "--account", ACCOUNT, "--config", self.cfg], fake)
        for c in fake.calls:
            if c[:2] == ["session", "stop"]:
                continue  # its output is not parsed
            self.assertIn("--json", c, c)


    def test_success_false_from_the_bridge_is_exit_1(self):
        # seen live: a bad column returns {"success": false, "message": ...} with no "error" key
        fake = FakeBsk(fetch_text=json.dumps({"success": False, "message": "Unknown identifier"}))
        code, out = self.invoke(["query", "--account", ACCOUNT, "--bridge-path", BRIDGE,
                                 "--config", self.cfg, "SELECT nosuchcolumn FROM account"], fake)
        self.assertEqual(code, 1)
        self.assertIn("Unknown identifier", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
