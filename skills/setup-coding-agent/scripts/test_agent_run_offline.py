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


TOOLS_OFF = ("edit", "webfetch", "websearch", "external_directory", "execute", "subagent", "skill", "question")


class LockdownTest(unittest.TestCase):
    """Tools OpenCode offers beyond bash: each must be denied in every read-only profile (found by asking the
    model to list its tools; `execute` = Code Mode with browser.* tools). Mutation-checked."""

    def setUp(self):
        self.mod = load("agent_run")

    def test_every_extra_tool_is_denied_in_both_profiles(self):
        for name, perm in (("ns-reader", self.mod.ns_reader_permission(READER, [])),
                           ("analyze", self.mod.analyze_permission())):
            for tool in TOOLS_OFF:
                with self.subTest(profile=name, tool=tool):
                    self.assertEqual(perm.get(tool), "deny")

    def test_ns_reader_refuses_redirects_that_leave_the_scratch_folder(self):
        r = self.mod.ns_reader_permission(READER, ["4089685"])["bash"]
        base = "python3 %s whoami --account 4089685_SB2" % READER
        for tail in [" > /etc/x", " >/Users/x/.zshrc", " > ~/x", " >$HOME/x", " > ../x", " 2>/tmp/x"]:
            with self.subTest(tail=tail):
                self.assertEqual(decide(r, base + tail), "deny")

    def test_ns_reader_still_allows_a_query_that_contains_a_greater_than_sign(self):
        r = self.mod.ns_reader_permission(READER, [])["bash"]
        cmd = 'python3 %s query --account 4089685_SB2 "SELECT id FROM employee WHERE id > 0"' % READER
        self.assertEqual(decide(r, cmd), "allow")


class AnalyzePermissionTest(unittest.TestCase):
    def setUp(self):
        self.perm = load("agent_run").analyze_permission()
        self.r = self.perm["bash"]

    def test_git_history_commands_are_allowed(self):
        for cmd in ["git log", "git log --oneline -n 20 -- src/a.js", "git show HEAD~1:src/a.js",
                    "git blame -L 1,20 src/a.js", "git diff HEAD~3 HEAD -- src"]:
            with self.subTest(cmd=cmd):
                self.assertEqual(decide(self.r, cmd), "allow")

    def test_everything_that_reads_or_writes_elsewhere_is_denied(self):
        for cmd in ["cat calc.py", "ls /Users", "wc -c /etc/hosts", "python3 -c 1", "rm -rf x", "git -c core.pager=x log",
                    "git log --oneline > z.txt", "git log >z.txt", "git log > /tmp/z", "git show --output=z HEAD",
                    "git diff --no-index /etc/hosts /dev/null", "git blame --contents /etc/hosts a.js",
                    "git diff --ext-diff HEAD", "git log --textconv", "git push origin x", "git checkout -b x",
                    "git log < /etc/hosts"]:
            with self.subTest(cmd=cmd):
                self.assertEqual(decide(self.r, cmd), "deny")

    def test_secret_looking_files_cannot_be_read(self):
        rd = self.perm["read"]
        for path in ["/w/.env", "/w/app.env.local", "/w/id.pem", "/w/a.key", "/w/aws_credentials.json", "/w/my_secret.txt"]:
            with self.subTest(path=path):
                self.assertEqual(decide(rd, path), "deny")
        self.assertEqual(decide(rd, "/w/src/calc.py"), "allow")


FAKE_OPENCODE = """#!/usr/bin/env python3
import json, os, sys
if sys.argv[1:3] == ["session", "delete"]:
    open(os.environ["FAKE_DEL_LOG"], "a").write(sys.argv[3] + "\\n")
    sys.exit(int(os.environ.get("FAKE_DEL_RC", "0")))
if sys.argv[1:3] == ["debug", "paths"]:
    print("home  /x"); print("db    " + os.environ.get("FAKE_DB", "/nonexistent.db")); sys.exit(0)
SID = "ses_fake123"
if os.environ.get("FAKE_WRITE"):
    open(os.path.join(os.environ["PWD"], "new.txt"), "w").write("hi\\n")
print(json.dumps({"type": "tool_use", "sessionID": SID, "part": {"tool": "shell", "state": {"status": "error", "input": {"command": "cat x"}}}}))
print(json.dumps({"type": "tool_use", "sessionID": SID, "part": {"tool": "read", "state": {"status": "completed", "input": {"path": "a.py"}}}}))
print(json.dumps({"type": "step_finish", "sessionID": SID, "part": {"tokens": {"input": 100, "output": 50, "cache": {"read": 40}}, "reason": "stop"}}))
print(json.dumps({"type": "text", "sessionID": SID, "part": {"text": os.environ.get("FAKE_TEXT", "done")}}))
"""


class LedgerTest(unittest.TestCase):
    def setUp(self):
        self.mod = load("agent_run")
        self.tmp = tempfile.mkdtemp()
        self.log = os.path.join(self.tmp, "sub", "d.jsonl")

    def run_rec(self, run_id, **kw):
        rec = dict(kind="run", run_id=run_id, profile="analyze", completed=True, tokens_in=100, tokens_cached=40,
                   tokens_out=50, usd_est=0.001, seconds=10.0, tools_denied=1)
        rec.update(kw)
        self.assertTrue(self.mod.log_event(rec, self.log))

    def test_log_is_created_private_and_appended(self):
        self.run_rec("r1"); self.run_rec("r2")
        self.assertEqual(stat.S_IMODE(os.stat(self.log).st_mode), 0o600)
        self.assertEqual([r["run_id"] for r in self.mod.read_log(self.log)], ["r1", "r2"])

    def test_bad_lines_are_skipped_not_fatal(self):
        self.run_rec("r1")
        open(self.log, "a").write("not json\n[1,2]\n")
        self.assertEqual(len(self.mod.read_log(self.log)), 1)

    def test_outcome_needs_a_known_run_and_a_known_verdict(self):
        self.run_rec("r1")
        with self.assertRaises(ValueError):
            self.mod.log_outcome("nope", "accepted", path=self.log)
        with self.assertRaises(ValueError):
            self.mod.log_outcome("r1", "great", path=self.log)
        self.mod.log_outcome("r1", "fixed", 7, "off by one", path=self.log)
        self.assertEqual(self.mod.read_log(self.log)[-1]["claude_fixed_lines"], 7)

    def test_summary_counts_the_latest_verdict_and_flags_unreviewed(self):
        for i in range(3):
            self.run_rec("r%d" % i)
        self.run_rec("u1", usd_est=None)
        self.mod.log_outcome("r0", "rejected", path=self.log)
        self.mod.log_outcome("r0", "accepted", path=self.log)      # changed my mind: latest wins
        self.mod.log_outcome("r1", "fixed", 4, path=self.log)
        prof, unrev = self.mod.summarize_log(self.mod.read_log(self.log))
        g = prof["analyze"]
        self.assertEqual((g["runs"], g["accepted"], g["fixed"], g["rejected"], g["fixed_lines"]), (4, 1, 1, 0, 4))
        self.assertEqual(g["usd_unpriced"], 1)
        self.assertEqual(unrev, ["r2", "u1"])

    def test_report_says_when_quality_cannot_be_judged(self):
        self.run_rec("r1")
        txt = self.mod.format_report(self.mod.read_log(self.log))
        self.assertIn("no verdicts recorded yet", txt)
        self.assertIn("Not recorded: Claude's own tokens", txt)

    def test_usd_estimate_uses_the_provider_stripped_id_and_never_guesses(self):
        m = self.mod
        self.assertAlmostEqual(m.usd_estimate("p/deepseek/deepseek-flash", 100, 40, 50),
                               m.usd_estimate("deepseek/deepseek-flash", 100, 40, 50))
        self.assertIsNone(m.usd_estimate("p/unpriced/model", 1, 0, 1))

    def cli(self, *args, fake_write=False, extra_env=None):
        import subprocess, sys as _sys
        home = os.path.join(self.tmp, "home"); os.makedirs(home, exist_ok=True)
        bindir = os.path.join(self.tmp, "bin"); os.makedirs(bindir, exist_ok=True)
        fake = os.path.join(bindir, "opencode")
        open(fake, "w").write(FAKE_OPENCODE); os.chmod(fake, 0o755)
        env = dict(os.environ, HOME=home, USERPROFILE=home, PATH=bindir + os.pathsep + os.environ["PATH"])   # USERPROFILE: what expanduser uses on Windows
        env.update(extra_env or {})
        env.pop("BOMBOT_FORGE_LOG", None)
        env.setdefault("FAKE_DEL_LOG", os.path.join(self.tmp, "del.log"))
        if fake_write:
            env["FAKE_WRITE"] = "1"
        r = subprocess.run([_sys.executable, os.path.join(_HERE, "agent_run.py")] + list(args), env=env,
                           capture_output=True, text=True, timeout=120)
        return r, os.path.join(home, ".config", "bombot-forge", "delegations.jsonl")

    def repo(self):
        import subprocess
        d = os.path.join(self.tmp, "repo"); os.makedirs(d)
        open(os.path.join(d, "a.py"), "w").write("x = 1\n")
        for c in (["init", "-q"], ["add", "a.py"], ["-c", "user.email=a@b", "-c", "user.name=t", "commit", "-qm", "i"]):
            subprocess.run(["git"] + c, cwd=d, check=True)
        open(os.path.join(self.tmp, "ask.md"), "w").write("SECRET-CUSTOMER-TASK find the bug")
        return d

    def test_analyze_run_writes_one_ledger_line_without_task_text(self):
        repo = self.repo()
        r, log = self.cli("--profile", "analyze", "--repo", repo, "--task-file", os.path.join(self.tmp, "ask.md"),
                          "--model", "p/deepseek/deepseek-flash")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("logged    : run id", r.stdout)
        raw = open(log).read()
        self.assertNotIn("SECRET-CUSTOMER-TASK", raw)
        rec = json.loads(raw)
        self.assertEqual((rec["profile"], rec["tokens_in"], rec["tokens_cached"], rec["tokens_out"]), ("analyze", 140, 40, 50))
        self.assertEqual((rec["tools_tried"], rec["tools_denied"], rec["repo"], rec["completed"]), (2, 1, "repo", True))
        self.assertGreater(rec["usd_est"], 0)

    def test_code_run_logs_lines_changed_and_the_verdict_round_trips(self):
        repo = self.repo()
        r, log = self.cli("--profile", "code", "--agent", "opencode", "--repo", repo,
                          "--task-file", os.path.join(self.tmp, "ask.md"), "--model", "p/deepseek/deepseek-flash",
                          fake_write=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        rec = json.loads(open(log).read().splitlines()[0])
        self.assertEqual((rec["profile"], rec["files_changed"], rec["lines_added"], rec["lines_removed"]), ("code", 1, 1, 0))
        r2, _ = self.cli("--log-outcome", rec["run_id"], "--verdict", "fixed", "--claude-fixed-lines", "3")
        self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)
        r3, _ = self.cli("--log-report")
        self.assertIn("fixed by Claude 1 (3 lines)", r3.stdout)
        r4, _ = self.cli("--log-outcome", "nonexistent-run-id", "--verdict", "accepted")
        self.assertEqual(r4.returncode, 2)

    # ---- OpenCode session cleanup
    def deleted(self):
        p = os.path.join(self.tmp, "del.log")
        return open(p).read().split() if os.path.exists(p) else []

    def test_session_ids_are_parsed_deduped_and_validated(self):
        out = "\n".join([json.dumps({"sessionID": "ses_a1"}), json.dumps({"sessionID": "ses_a1"}),
                         json.dumps({"sessionID": "ses_b2"}), json.dumps({"sessionID": "../etc"}),
                         json.dumps({"sessionID": "ses_x; rm -rf /"}), json.dumps({"type": "text"}), "not json"])
        self.assertEqual(self.mod.session_ids(out), ["ses_a1", "ses_b2"])

    def test_delete_refuses_anything_that_is_not_a_session_id(self):
        ok, msg = self.mod.delete_session("ses_x; rm -rf /")
        self.assertFalse(ok)
        self.assertIn("refused", msg)
        self.assertEqual(self.deleted(), [])

    def test_a_finished_analyze_run_deletes_the_session_it_created(self):
        repo = self.repo()
        r, log = self.cli("--profile", "analyze", "--repo", repo, "--task-file", os.path.join(self.tmp, "ask.md"),
                          "--model", "p/deepseek/deepseek-flash")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.deleted(), ["ses_fake123"])
        self.assertIn("session   : deleted ses_fake123", r.stdout)
        rec = json.loads(open(log).read().splitlines()[0])
        self.assertEqual((rec["session_id"], rec["session_deleted"]), ("ses_fake123", True))

    def test_keep_session_leaves_it_alone_and_says_so(self):
        repo = self.repo()
        r, log = self.cli("--profile", "analyze", "--repo", repo, "--task-file", os.path.join(self.tmp, "ask.md"),
                          "--model", "p/deepseek/deepseek-flash", "--keep-session")
        self.assertEqual(self.deleted(), [])
        self.assertIn("kept ses_fake123 (--keep-session)", r.stdout)
        self.assertFalse(json.loads(open(log).read().splitlines()[0])["session_deleted"])

    def test_a_failed_delete_does_not_fail_the_run_but_is_reported_and_logged(self):
        repo = self.repo()
        r, log = self.cli("--profile", "analyze", "--repo", repo, "--task-file", os.path.join(self.tmp, "ask.md"),
                          "--model", "p/deepseek/deepseek-flash", extra_env={"FAKE_DEL_RC": "1"})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("COULD NOT delete", r.stdout)
        self.assertFalse(json.loads(open(log).read().splitlines()[0])["session_deleted"])

    def test_a_code_run_on_opencode_also_deletes_its_session(self):
        repo = self.repo()
        r, log = self.cli("--profile", "code", "--agent", "opencode", "--repo", repo,
                          "--task-file", os.path.join(self.tmp, "ask.md"), "--model", "p/deepseek/deepseek-flash",
                          fake_write=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.deleted(), ["ses_fake123"])

    def make_db(self, home):
        import sqlite3
        db = os.path.join(self.tmp, "oc.db")
        root = os.path.join(home, ".cache", "bombot-forge", "agent-runs")
        con = sqlite3.connect(db)
        con.execute("CREATE TABLE session_v2 (id text primary key, directory text not null)")
        rows = [("ses_in1", root + "/20260101_010101/worktree"), ("ses_in2", root + "/20260101_020202_nsr/work"),
                ("ses_out", "/somewhere/else/worktree"),
                # differs from the root only where a LIKE pattern would treat '_' as a wildcard
                ("ses_lookalike", root.replace("home_x", "homeXx") + "/20260101_030303/worktree"),
                ("ses_prefix", root + "-old/20260101/worktree")]
        con.executemany("INSERT INTO session_v2 VALUES (?, ?)", rows)
        con.commit(); con.close()
        return db, root

    def test_purge_finds_only_sessions_inside_the_agent_runs_cache(self):
        home = os.path.join(self.tmp, "home_x"); os.makedirs(home)
        db, root = self.make_db(home)
        got = self.mod.agent_run_sessions(db, root)
        self.assertEqual(sorted(got), [("ses_in1", "20260101_010101"), ("ses_in2", "20260101_020202_nsr")])

    def test_purge_is_a_dry_run_until_yes(self):
        home = os.path.join(self.tmp, "home_x"); os.makedirs(home)
        db, root = self.make_db(home)
        import subprocess, sys as _sys
        bindir = os.path.join(self.tmp, "bin"); os.makedirs(bindir, exist_ok=True)
        fake = os.path.join(bindir, "opencode"); open(fake, "w").write(FAKE_OPENCODE); os.chmod(fake, 0o755)
        env = dict(os.environ, HOME=home, USERPROFILE=home, FAKE_DB=db, PATH=bindir + os.pathsep + os.environ["PATH"],
                   FAKE_DEL_LOG=os.path.join(self.tmp, "del.log"))
        run = lambda *a: subprocess.run([_sys.executable, os.path.join(_HERE, "agent_run.py")] + list(a), env=env,
                                        capture_output=True, text=True, timeout=60)
        r = run("--purge-sessions")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("2 session(s)", r.stdout)
        self.assertIn("dry run", r.stdout)
        self.assertEqual(self.deleted(), [])
        r = run("--purge-sessions", "--yes")
        self.assertEqual(sorted(self.deleted()), ["ses_in1", "ses_in2"])
        self.assertNotIn("ses_out", r.stdout)


class PortabilityTest(unittest.TestCase):
    """Windows-facing behaviour that can be checked on any OS. NOT a substitute for a run on Windows."""

    def setUp(self):
        self.mod = load("agent_run")

    def test_permission_globs_use_forward_slashes_and_the_given_interpreter(self):
        reader = self.mod.glob_path("C:\\Users\\a\\run\\ns_read.py")
        self.assertEqual(reader, "C:/Users/a/run/ns_read.py")
        r = self.mod.ns_reader_permission(reader, ["4089685"], py="python")["bash"]
        self.assertEqual(decide(r, "python %s query --account 4089685_SB2 x" % reader), "allow")
        self.assertEqual(decide(r, "python3 %s query --account 4089685_SB2 x" % reader), "deny")
        self.assertEqual(decide(r, "python %s --allow-prod-read query --account 4089685 x" % reader), "allow")

    def test_link_falls_back_to_a_copy_when_symlinks_are_not_allowed(self):
        d = tempfile.mkdtemp()
        src = os.path.join(d, "s.py"); open(src, "w").write("print(1)\n")
        real = os.symlink
        try:
            def refuse(*a, **k):
                raise OSError("A required privilege is not held by the client")   # what Windows raises
            os.symlink = refuse
            self.assertEqual(self.mod.link_or_copy(src, os.path.join(d, "c.py")), "copy")
        finally:
            os.symlink = real
        self.assertEqual(open(os.path.join(d, "c.py")).read(), "print(1)\n")
        self.assertEqual(self.mod.link_or_copy(src, os.path.join(d, "l.py")), "link")

    def test_interpreter_name_matches_the_os(self):
        self.assertEqual(self.mod.PY_CMD, "python" if os.name == "nt" else "python3")

    def test_ledger_lives_beside_agent_json_not_in_claude_code_cache(self):
        self.assertTrue(self.mod.LOG_PATH.startswith("~/.config/bombot-forge/"))
        self.assertNotIn(".claude", self.mod.LOG_PATH)

    def test_thai_agent_reply_does_not_crash_a_legacy_console(self):
        # a cp1252 console raises UnicodeEncodeError on Thai unless main() reconfigures stdout (mutation-checked)
        L = LedgerTest("test_report_says_when_quality_cannot_be_judged")
        L.setUp()
        repo = L.repo()
        r, _ = L.cli("--profile", "analyze", "--repo", repo, "--task-file", os.path.join(L.tmp, "ask.md"),
                     "--model", "p/deepseek/deepseek-flash",
                     extra_env={"FAKE_TEXT": "\u0e1e\u0e1a\u0e1a\u0e31\u0e4a\u0e01\u0e17\u0e35\u0e48\u0e1a\u0e23\u0e23\u0e17\u0e31\u0e14 5",
                                "PYTHONIOENCODING": "cp1252"})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("UnicodeEncodeError", r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
