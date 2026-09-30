#!/usr/bin/env python3
"""Offline tests for the pieces of agent_run.py that are easy to break silently: the USD price
table lookup (a missing table only shows up as a missing "est. USD" line) and the ns-reader
permission list. No agent CLI, no network."""
import fnmatch
import importlib.util
import json
import os
import stat
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_HERE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class PriceTableTest(unittest.TestCase):
    def test_price_table_sits_next_to_the_scripts_and_is_valid(self):
        path = os.path.join(_HERE, "prices.json")
        self.assertTrue(os.path.isfile(path), "prices.json must live beside agent_run.py")
        data = json.load(open(path, encoding="utf-8"))
        self.assertIn("deepseek/deepseek-flash", data)

    def test_agent_run_finds_a_price_for_the_default_model(self):
        p = load("agent_run").peak_price("deepseek/deepseek-flash")
        self.assertIsInstance(p, dict)
        for k in ("input", "output", "cached_input"):
            self.assertIsInstance(p.get(k), (int, float), k)
            self.assertGreater(p[k], 0, k)

    def test_unknown_model_has_no_price_not_a_guess(self):
        self.assertIsNone(load("agent_run").peak_price("some/model-nobody-priced"))

    def test_ask_cheap_reads_the_same_table(self):
        p = load("ask_cheap").load_prices("deepseek/deepseek-flash")
        self.assertGreater(p.get("input", 0), 0)
        self.assertGreater(p.get("output", 0), 0)


READER = "/cache/run/ns_read.py"
SUBS = ("whoami", "ping", "query", "record", "lookup", "feature", "search")


def decide(rules, command):
    """OpenCode's rule: the LAST matching pattern wins (verified live with allow-before-deny and
    deny-before-allow orderings). No match = deny."""
    verdict = "deny"
    for pat, act in rules.items():
        if fnmatch.fnmatchcase(command, pat):
            verdict = act
    return verdict


class NsReaderPermissionTest(unittest.TestCase):
    def setUp(self):
        self.mod = load("agent_run")

    def rules(self, accounts):
        return self.mod.ns_reader_permission(READER, accounts)["bash"]

    def test_sandbox_style_commands_are_allowed_for_every_subcommand(self):
        r = self.rules([])
        for sub in SUBS:
            self.assertEqual(decide(r, "python3 %s %s --account 4089685_SB2 x" % (READER, sub)), "allow", sub)

    def test_nothing_else_is_allowed(self):
        r = self.rules(["4089685"])
        for cmd in ["ls", "bsk status --json", "python3 /other/ns_write.py --account 1 --type t --id 1",
                    "python3 %s --allow-prod-read query --account 2935624 SELECT" % READER,
                    "VAR=1 python3 %s query --account 4089685_SB2 x" % READER]:
            with self.subTest(cmd=cmd):
                self.assertEqual(decide(r, cmd), "deny")

    def test_prod_flag_is_denied_unless_the_account_is_listed(self):
        r = self.rules(["4089685"])
        listed = "python3 %s --allow-prod-read query --account 4089685 SELECT 1" % READER
        self.assertEqual(decide(r, listed), "allow")
        for sub in SUBS:
            self.assertEqual(decide(r, "python3 %s --allow-prod-read %s --account 4089685 x" % (READER, sub)), "allow", sub)
        for cmd in ["python3 %s --allow-prod-read query --account 2935624 SELECT 1" % READER,
                    "python3 %s --allow-prod-read query --account 4089685x SELECT 1" % READER,
                    "python3 %s query --account 2935624 --allow-prod-read SELECT 1" % READER]:
            with self.subTest(cmd=cmd):
                self.assertEqual(decide(r, cmd), "deny")

    def test_a_listed_account_cannot_be_combined_with_config_or_bridge_path(self):
        r = self.rules(["4089685"])
        for extra in ["--config /tmp/x.json", "--bridge-path /app/x"]:
            for cmd in ["python3 %s --allow-prod-read query --account 4089685 %s SELECT 1" % (READER, extra),
                        "python3 %s query --account 4089685_SB2 %s SELECT 1" % (READER, extra)]:
                with self.subTest(cmd=cmd):
                    self.assertEqual(decide(r, cmd), "deny")

    def test_rule_order_is_what_makes_it_safe(self):
        keys = list(self.rules(["4089685"]).keys())
        i_prod_deny = keys.index("*--allow-prod-read*")
        i_prod_allow = min(k for k in range(len(keys)) if "--allow-prod-read query --account" in keys[k])
        i_bridge = keys.index("*--bridge-path*")
        i_config = keys.index("*--config*")
        self.assertEqual(keys[0], "*")
        self.assertLess(i_prod_deny, i_prod_allow)
        self.assertLess(i_prod_allow, i_bridge)
        self.assertLess(i_prod_allow, i_config)

    def test_unsafe_account_strings_are_refused(self):
        for bad in ["", "1 2", "1*", "4089685 --config x", "a;b", "../x", "1'2"]:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    self.mod.ns_reader_permission(READER, [bad])

    def test_dict_entries_from_agent_json_are_accepted(self):
        r = self.mod.ns_reader_permission(READER, [{"account": "4089685", "confirmed_at": "x"}])["bash"]
        self.assertEqual(decide(r, "python3 %s --allow-prod-read ping --account 4089685 " % READER), "allow")


class GrantReadAccountTest(unittest.TestCase):
    def setUp(self):
        self.mod = load("agent_run")
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "agent.json")

    def tearDown(self):
        self.tmp.cleanup()

    def grant(self, account="4089685", **kw):
        args = dict(session_id="sess-1", session_name="My session", note="user confirmed", path=self.path)
        args.update(kw)
        return self.mod.grant_read_account(account, **args)

    def test_creates_the_file_and_records_who_when_and_where(self):
        status = self.grant()
        self.assertEqual(status, "added")
        d = json.load(open(self.path))
        e = d["read_accounts"][0]
        self.assertEqual(e["account"], "4089685")
        self.assertEqual(e["session_id"], "sess-1")
        self.assertEqual(e["session_name"], "My session")
        self.assertEqual(e["note"], "user confirmed")
        self.assertRegex(e["confirmed_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$")
        self.assertRegex(e["confirmed_at_utc"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        self.assertEqual(stat.S_IMODE(os.stat(self.path).st_mode), 0o600)

    def test_keeps_the_other_keys_and_backs_up_the_old_file(self):
        json.dump({"default_delegate": True, "agent": "opencode", "model": "p/m", "extra": [1]}, open(self.path, "w"))
        self.grant()
        d = json.load(open(self.path))
        self.assertEqual((d["default_delegate"], d["agent"], d["model"], d["extra"]), (True, "opencode", "p/m", [1]))
        backups = [f for f in os.listdir(self.tmp.name) if f.startswith("agent.json.bak.")]
        self.assertEqual(len(backups), 1)
        self.assertNotIn("read_accounts", json.load(open(os.path.join(self.tmp.name, backups[0]))))

    def test_granting_twice_does_not_duplicate_or_rewrite(self):
        self.grant()
        before = open(self.path).read()
        self.assertEqual(self.grant(session_id="sess-2"), "already")
        self.assertEqual(open(self.path).read(), before)

    def test_session_id_is_required_and_the_account_is_validated(self):
        with self.assertRaises(ValueError):
            self.grant(session_id="")
        with self.assertRaises(ValueError):
            self.grant(account="1 2")
        self.assertFalse(os.path.exists(self.path))

    def test_revoke_removes_only_that_account(self):
        self.grant("4089685")
        self.grant("2935624")
        self.assertEqual(self.mod.revoke_read_account("4089685", path=self.path), "removed")
        d = json.load(open(self.path))
        self.assertEqual([e["account"] for e in d["read_accounts"]], ["2935624"])
        self.assertEqual(self.mod.revoke_read_account("99999", path=self.path), "not-found")


if __name__ == "__main__":
    unittest.main(verbosity=2)
