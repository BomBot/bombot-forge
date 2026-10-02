#!/usr/bin/env python3
"""Offline tests for ns_write.py — no browser, no network, no bsk/cdp installed.

The browser layer is stubbed on the loaded module by replacing `_await` (which returns the
JSON dict the page would stash) and `_bsk_eval` (the bsk dialog-guard call, which returns
(value, error)). Nothing here shells out.
"""
import importlib.util
import io
import os
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPT = os.path.join(_HERE, "ns_write.py")


def load_module():
    """Load ns_write.py from this file's directory (never an absolute hard-coded path)."""
    spec = importlib.util.spec_from_file_location("ns_write_under_test", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class OfflineWriteTest(unittest.TestCase):
    def setUp(self):
        self.mod = load_module()
        # Reset the engine state before every test, as main() would at process start.
        self.mod.ST = {"engine": "cdp", "session": None, "tab": None}
        self.writes = []
        self.account = "4089685_SB2"
        self.env = "SANDBOX"
        self.write_result = {"ok": True, "savedId": "1"}

        def fake_await(js, tab=None, tries=25):
            if "submitFields" in js or "rec.save" in js:
                self.writes.append(js)
                return dict(self.write_result)
            if "N/runtime" in js:
                return {"ok": True, "acct": self.account, "env": self.env, "url": "h"}
            return {"ok": True, "r": {"memo": "v"}}

        def fake_bsk_eval(expr, timeout=60):
            return ("guard", None)

        self.mod._await = fake_await
        self.mod._bsk_eval = fake_bsk_eval

    def run_main(self, argv):
        sys.argv = ["ns_write.py"] + argv
        out, err = io.StringIO(), io.StringIO()
        code = 0
        with redirect_stdout(out), redirect_stderr(err):
            try:
                self.mod.main()
            except SystemExit as e:
                code = e.code if e.code is not None else 0
        return code, out.getvalue(), err.getvalue()

    def base_args(self, confirm=False):
        args = ["--account", self.account, "--type", "customrecord_x", "--id", "1",
                "--set", "memo=v"]
        if confirm:
            args.append("--confirm")
        return args

    def bsk_args(self):
        return ["--engine", "bsk", "--bsk-session", "s", "--bsk-tab", "t"]

    def confirmed_write(self, argv):
        """Run argv with --confirm and return the single captured write JS string."""
        code, _, err = self.run_main(argv)
        self.assertEqual(code, 0, err)
        self.assertEqual(len(self.writes), 1)
        return self.writes[0]

    # 1. dry-run (no --confirm): exit 0, no write, says DRY-RUN
    def test_dry_run_writes_nothing(self):
        code, out, _ = self.run_main(self.base_args())
        self.assertEqual(code, 0)
        self.assertEqual(self.writes, [])
        self.assertIn("DRY-RUN", out)

    # 2. live account differs from --account, with --confirm: exit 2, no write
    def test_account_mismatch_aborts(self):
        self.account = "4089685"
        self.env = "PRODUCTION"
        code, _, _ = self.run_main(
            ["--account", "4089685_SB2", "--type", "customrecord_x", "--id", "1",
             "--set", "memo=v", "--confirm"])
        self.assertEqual(code, 2)
        self.assertEqual(self.writes, [])

    # 3. bsk + PRODUCTION + --confirm with NO flag: exit 0, writes, warns (the round's confirmation is the guard)
    def test_bsk_production_writes_without_any_flag_and_warns(self):
        self.account = "4089685"
        self.env = "PRODUCTION"
        code, out, _ = self.run_main(self.bsk_args() + self.base_args(confirm=True))
        self.assertEqual(code, 0)
        self.assertEqual(len(self.writes), 1)
        self.assertIn("WARNING", out)
        self.assertIn("NON-sandbox", out)
        self.assertNotIn("no longer needed", out)

    # 4. the old flag is still accepted (old command lines keep working) and says it is ignored
    def test_old_allow_bsk_prod_flag_is_accepted_and_ignored(self):
        self.account = "4089685"
        self.env = "PRODUCTION"
        code, out, _ = self.run_main(
            self.bsk_args() + self.base_args(confirm=True) + ["--allow-bsk-prod"])
        self.assertEqual(code, 0)
        self.assertEqual(len(self.writes), 1)
        self.assertIn("no longer needed", out)

    # 4b. a dry-run still writes nothing and no longer announces a refusal that does not exist
    def test_bsk_production_dry_run_writes_nothing(self):
        self.account = "4089685"
        self.env = "PRODUCTION"
        code, out, _ = self.run_main(self.bsk_args() + self.base_args(confirm=False))
        self.assertEqual(code, 0)
        self.assertEqual(self.writes, [])
        self.assertNotIn("REFUSED", out)
        self.assertIn("DRY-RUN", out)

    # 5. bsk + SANDBOX + --confirm: exit 0, writes
    def test_bsk_sandbox_writes(self):
        self.account = "4089685_SB2"
        self.env = "SANDBOX"
        code, out, _ = self.run_main(self.bsk_args() + self.base_args(confirm=True))
        self.assertEqual(code, 0)
        self.assertEqual(len(self.writes), 1)
        self.assertIn("WRITE ok", out)

    # 6. cdp + --tab + PRODUCTION + --confirm: exit 0, writes
    def test_cdp_production_writes(self):
        self.account = "4089685"
        self.env = "PRODUCTION"
        code, out, _ = self.run_main(
            ["--engine", "cdp", "--tab", "T"] + self.base_args(confirm=True))
        self.assertEqual(code, 0)
        self.assertEqual(len(self.writes), 1)
        self.assertIn("WRITE ok", out)

    # 7. transport failure during the write: exit 3, OUTCOME UNKNOWN
    def test_transport_failure_is_unknown(self):
        self.write_result = {"ok": False, "transport": True, "err": "lost"}
        code, out, _ = self.run_main(self.base_args(confirm=True))
        self.assertEqual(code, 3)
        self.assertIn("OUTCOME UNKNOWN", out)
        # a failed attempt is still an attempt: the write stub was called exactly once
        self.assertEqual(len(self.writes), 1)

    # 8. page-side rejection: exit 1, WRITE FAILED
    def test_page_rejection_fails(self):
        self.write_result = {"ok": False, "err": "INVALID_FLD_VALUE"}
        code, out, _ = self.run_main(self.base_args(confirm=True))
        self.assertEqual(code, 1)
        self.assertIn("WRITE FAILED", out)
        # a failed attempt is still an attempt: the write stub was called exactly once
        self.assertEqual(len(self.writes), 1)

    # 9. no --set: argparse error, exit 2
    def test_no_set_is_argparse_error(self):
        code, _, _ = self.run_main(
            ["--account", "4089685_SB2", "--type", "customrecord_x", "--id", "1"])
        self.assertEqual(code, 2)
        self.assertEqual(self.writes, [])

    # 10. --set without '=': argparse error, exit 2
    def test_bad_set_is_argparse_error(self):
        code, _, _ = self.run_main(
            ["--account", "4089685_SB2", "--type", "customrecord_x", "--id", "1",
             "--set", "memo"])
        self.assertEqual(code, 2)
        self.assertEqual(self.writes, [])

    # 11. submit mode (default): submitFields with the exact type/id/values, no save
    def test_submit_mode_js_payload(self):
        js = self.confirmed_write(self.base_args(confirm=True))
        self.assertIn("submitFields", js)
        self.assertIn('type:"customrecord_x"', js)
        self.assertIn('id:"1"', js)
        self.assertIn('values:{"memo":"v"}', js)
        self.assertNotIn("rec.save", js)

    # 12. save mode: load -> setValue -> save with isDynamic:false, no submitFields
    def test_save_mode_js_payload(self):
        js = self.confirmed_write(
            ["--mode", "save"] + self.base_args(confirm=True))
        self.assertIn("record.load", js)
        self.assertIn("rec.save", js)
        self.assertIn("isDynamic:false", js)
        self.assertIn('rec.setValue({fieldId:"memo", value:"v"})', js)
        self.assertNotIn("submitFields", js)

    # 13. save mode with --dynamic: the load is dynamic
    def test_save_mode_dynamic_flag(self):
        js = self.confirmed_write(
            ["--mode", "save", "--dynamic"] + self.base_args(confirm=True))
        self.assertIn("isDynamic:true", js)
        self.assertNotIn("isDynamic:false", js)

    # 14. two --set values both reach the payload (field id and value each)
    def test_two_sets_both_reach_payload(self):
        js = self.confirmed_write(
            ["--account", self.account, "--type", "customrecord_x", "--id", "1",
             "--set", "memo=a", "--set", "note=b", "--confirm"])
        self.assertIn('"memo":"a"', js)
        self.assertIn('"note":"b"', js)

    # 15. quotes and backslashes in a value are JSON-escaped into the JS string
    def test_value_is_json_escaped(self):
        js = self.confirmed_write(
            ["--account", self.account, "--type", "customrecord_x", "--id", "1",
             "--set", 'memo=say "hi" \\ ok', "--confirm"])
        self.assertIn('"memo":"say \\"hi\\" \\\\ ok"', js)

    # 16. the write JS re-checks the account inside the page
    def test_write_rechecks_account(self):
        js = self.confirmed_write(self.base_args(confirm=True))
        self.assertIn("account changed to", js)
        self.assertIn('"4089685_SB2"', js)

    # 18. cdp and bsk produce byte-identical write JS for the same arguments
    def test_cdp_and_bsk_send_same_js(self):
        bsk_js = self.confirmed_write(
            self.bsk_args() + self.base_args(confirm=True))
        self.writes = []
        # main() keeps engine state in the module (a real run is a fresh process), so reset it
        # or the second run would still think it is bsk
        self.mod.ST = {"engine": "cdp", "session": None, "tab": None}
        cdp_js = self.confirmed_write(
            ["--engine", "cdp", "--tab", "T"] + self.base_args(confirm=True))
        self.assertEqual(bsk_js, cdp_js)


if __name__ == "__main__":
    unittest.main(verbosity=2)
