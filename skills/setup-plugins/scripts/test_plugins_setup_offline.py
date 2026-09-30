#!/usr/bin/env python3
"""Offline tests for plugins_setup.py with a fake `claude` CLI (a script that keeps its state in a JSON file and
logs every call). No network, no real Claude config."""
import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))

FAKE = r'''#!/usr/bin/env python3
import json, os, sys
st_path = os.environ["FAKE_STATE"]
st = json.load(open(st_path))
open(st_path + ".log", "a").write(json.dumps(sys.argv[1:]) + "\n")
a = sys.argv[1:]
def save(): json.dump(st, open(st_path, "w"))
if a[:3] == ["plugin", "list", "--json"]:
    print(json.dumps([{"id": i} for i in st["installed"]])); sys.exit(0)
if a[:4] == ["plugin", "marketplace", "list", "--json"]:
    print(json.dumps([{"name": m} for m in st["markets"]])); sys.exit(0)
if a[:3] == ["plugin", "marketplace", "add"]:
    src = a[3]
    if src in st.get("fail_add", []):
        sys.stderr.write("fatal: could not read Username for 'https://github.com': terminal prompts disabled\n"); sys.exit(1)
    st["markets"].append(st["catalog"].get(src, "unexpected-name")); save(); sys.exit(0)
if a[:2] == ["plugin", "install"]:
    if a[2] in st.get("fail_install", []):
        sys.stderr.write("plugin not found\n"); sys.exit(1)
    st["installed"].append(a[2]); save(); sys.exit(0)
sys.stderr.write("unexpected: %r\n" % (a,)); sys.exit(9)
'''


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_HERE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class PluginsSetupTest(unittest.TestCase):
    def setUp(self):
        self.mod = load("plugins_setup")
        self.tmp = tempfile.mkdtemp()
        self.fake = os.path.join(self.tmp, "claude")
        open(self.fake, "w").write(FAKE)
        os.chmod(self.fake, 0o755)
        self.state = os.path.join(self.tmp, "state.json")
        self.entries = self.mod.load_manifest()
        self.catalog = {e["source"]: e["marketplace"] for e in self.entries}
        os.environ["CLAUDE_BIN"] = self.fake
        os.environ["FAKE_STATE"] = self.state

    def tearDown(self):
        os.environ.pop("CLAUDE_BIN", None)
        os.environ.pop("FAKE_STATE", None)

    def set_state(self, installed=(), markets=(), **kw):
        json.dump(dict(installed=list(installed), markets=list(markets), catalog=self.catalog, **kw), open(self.state, "w"))
        open(self.state + ".log", "w").close()

    def calls(self):
        return [json.loads(l) for l in open(self.state + ".log") if l.strip()]

    # ---- manifest
    def test_shipped_manifest_is_valid_and_has_the_six_chosen_plugins(self):
        self.assertEqual(sorted(e["name"] for e in self.entries), sorted(
            ["teibto-netsuite-toolkit", "superpowers", "impeccable", "mattpocock-skills", "andrej-karpathy-skills", "ui-ux-pro-max"]))

    def test_manifest_rejects_option_injection_and_odd_sources(self):
        p = os.path.join(self.tmp, "m.json")
        for bad in ["--scope", "http://x/y.git", "a b", "git@github.com:x/y.git", "https://x/y;rm"]:
            with self.subTest(source=bad):
                json.dump({"plugins": [{"name": "a", "marketplace": "b", "source": bad}]}, open(p, "w"))
                with self.assertRaises(ValueError):
                    self.mod.load_manifest(p)

    # ---- classification
    def test_states(self):
        e = {"name": "superpowers", "marketplace": "superpowers-dev", "source": "obra/superpowers"}
        c = self.mod.classify
        self.assertEqual(c(e, ["superpowers@superpowers-dev"], [])[0], "installed")
        self.assertEqual(c(e, ["superpowers@synced"], []), ("elsewhere", "superpowers@synced"))
        self.assertEqual(c(e, [], ["superpowers-dev"])[0], "ready")
        self.assertEqual(c(e, [], [])[0], "needs-marketplace")
        self.assertEqual(c(e, ["superpowers-extra@x"], [])[0], "needs-marketplace")   # a different name is not a match

    # ---- apply
    def test_apply_adds_the_marketplace_then_installs_at_user_scope(self):
        self.set_state()
        res = self.mod.apply(self.entries, ["impeccable"])
        self.assertEqual([(n, s) for n, s, _ in res], [("impeccable", "installed")])
        cmds = [c for c in self.calls() if c[1] in ("marketplace", "install") and c[2] != "list"]
        self.assertEqual(cmds, [["plugin", "marketplace", "add", "pbakaus/impeccable", "--scope", "user"],
                                ["plugin", "install", "impeccable@impeccable", "--scope", "user"]])

    def test_apply_skips_what_is_already_present_even_under_another_marketplace(self):
        self.set_state(installed=["superpowers@synced", "impeccable@impeccable"], markets=["impeccable"])
        res = self.mod.apply(self.entries, ["superpowers", "impeccable"])
        self.assertEqual([s for _, s, _ in res], ["skipped", "skipped"])
        self.assertFalse([c for c in self.calls() if c[1] in ("install",) or c[2] == "add"])

    def test_dry_run_changes_nothing(self):
        self.set_state()
        res = self.mod.apply(self.entries, ["mattpocock-skills"], dry_run=True)
        self.assertEqual(res[0][1], "would-run")
        self.assertEqual(json.load(open(self.state))["installed"], [])

    def test_a_failed_plugin_does_not_stop_the_next_one_and_hints_at_access(self):
        src = next(e["source"] for e in self.entries if e["name"] == "teibto-netsuite-toolkit")
        self.set_state(fail_add=[src])
        res = self.mod.apply(self.entries, ["teibto-netsuite-toolkit", "impeccable"])
        d = {n: (s, m) for n, s, m in res}
        self.assertEqual(d["teibto-netsuite-toolkit"][0], "FAILED")
        self.assertIn("never logs in", d["teibto-netsuite-toolkit"][1])
        self.assertEqual(d["impeccable"][0], "installed")

    def test_marketplace_added_under_a_different_name_is_reported_not_trusted(self):
        self.set_state()
        self.catalog["pbakaus/impeccable"] = "something-else"
        self.set_state()
        res = self.mod.apply(self.entries, ["impeccable"])
        self.assertEqual(res[0][1], "FAILED")
        self.assertIn("something-else", res[0][2])
        self.assertFalse([c for c in self.calls() if c[1] == "install"])

    def test_unknown_name_is_refused_before_anything_runs(self):
        self.set_state()
        with self.assertRaises(ValueError):
            self.mod.apply(self.entries, ["not-in-manifest"])
        self.assertEqual(self.calls(), [])

    def test_only_the_four_allowed_command_shapes_can_run(self):
        self.set_state()
        for bad in [["plugin", "uninstall", "x"], ["auth", "login"], ["plugin", "install", "x@y"],
                    ["plugin", "install", "x@y", "--scope", "project"], ["plugin", "marketplace", "add", "a/b"],
                    ["plugin", "marketplace", "remove", "x"], ["mcp", "add", "x"]]:
            with self.subTest(cmd=bad):
                with self.assertRaises(ValueError):
                    self.mod.run_claude(bad)
        self.assertEqual(self.calls(), [])

    # ---- CLI
    def test_cli_plan_and_all_missing_dry_run(self):
        self.set_state(installed=["impeccable@impeccable"], markets=["impeccable"])
        env = dict(os.environ)
        r = subprocess.run([sys.executable, os.path.join(_HERE, "plugins_setup.py"), "apply", "--all-missing", "--dry-run"],
                           env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("would-run", r.stdout)
        offered = [l.split()[0] for l in r.stdout.splitlines() if "would-run" in l]
        self.assertNotIn("impeccable", offered)          # already installed: not offered
        self.assertEqual(sorted(offered), sorted(["teibto-netsuite-toolkit", "superpowers", "mattpocock-skills",
                                                  "andrej-karpathy-skills", "ui-ux-pro-max"]))
        r2 = subprocess.run([sys.executable, os.path.join(_HERE, "plugins_setup.py")], env=env, capture_output=True, text=True)
        self.assertIn("already installed", r2.stdout)

    def test_cli_exit_code_is_1_when_an_install_fails(self):
        self.set_state(markets=["mattpocock"], fail_install=["mattpocock-skills@mattpocock"])
        r = subprocess.run([sys.executable, os.path.join(_HERE, "plugins_setup.py"), "apply", "mattpocock-skills"],
                           env=dict(os.environ), capture_output=True, text=True)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("FAILED", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=1)
