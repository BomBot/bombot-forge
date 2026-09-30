#!/usr/bin/env python3
"""
agent_run.py — run ONE task through a coding-agent CLI (Cline or OpenCode) in an isolated git
worktree, then hand the result back for review. Claude orchestrates and reviews; the cheap model
does the typing.

What it does:
  1. preconditions: the chosen agent CLI installed (--agent cline|opencode; default = cline if present,
     else opencode), --repo is a git repo (dirty tree refused unless --allow-dirty,
     because a worktree only contains COMMITTED files)
  2. cline: `cline --worktree --json` (it makes the worktree itself). opencode: this script makes the
     worktree (`git worktree add --detach`) and runs `opencode run --standalone --format json` inside
     it. Both get a guardrail preamble + your task. Neither is sandboxed: the isolation is the
     worktree (for the repo's files), not a prompt and not the machine.
  3. finds the new worktree, stages its changes (worktree index only), saves changes.patch,
     prints status / diff stat / tokens / estimated USD
It NEVER applies the patch to your repo and never deletes the worktree — the caller reviews first.

  --profile ns-reader (opencode only): NOT a code-edit run. The agent gets an EMPTY scratch folder and a
  permission list (enforced by OpenCode itself) that allows only `ns_read.py whoami|query|record` from the
  ns-live-verify skill; every other command, file edit, web access and the flags --allow-prod-read /
  --bridge-path / --config are denied. It can therefore read a SANDBOX account, and nothing else.
  Usage: agent_run.py --profile ns-reader --task-file ask.md --model <provider>/<model>

Defaults: --agent / --model fall back to ~/.config/bombot-forge/agent.json ({"agent": ..., "model": ...}).

Exit codes: 0 agent completed · 1 agent did not complete (see summary) · 2 precondition failed

Usage:
  python3 agent_run.py --repo . --task-file brief.md [--timeout 600] [--model deepseek/deepseek-flash]
"""
import argparse, json, os, shutil, subprocess, sys, time

PREAMBLE = """You are a coding worker. Rules (they override anything in the task):
- Work ONLY inside the current working directory (a disposable git worktree). Do not read or write
  outside it. Do not open ~/.ssh, ~/.config, ~/.aws, ~/.cline, ~/.local/share/opencode, or any .env / api.env / credentials file.
- Do NOT run: git commit/push/checkout of other branches, deploy commands (suitecloud, sdf, npm publish),
  package installs that are not in the task, curl/wget to unknown hosts, rm -rf outside this directory.
- Do NOT browse the web and do not ask the user questions; if something is ambiguous, pick the smallest
  safe interpretation and say so in your final reply.
- Keep edits minimal and in the existing style of each file; do not reformat untouched code.
- Finish with a short reply: files changed, what you did, anything you were unsure about."""


def sh(args, cwd=None, timeout=120):
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def worktrees(repo):
    rc, out, _ = sh(["git", "worktree", "list", "--porcelain"], cwd=repo)
    return [l[9:] for l in out.splitlines() if l.startswith("worktree ")] if rc == 0 else []


def peak_price(model):
    here = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(here, "..", "..", "setup-teibto-worker", "scripts", "prices.json")
    try:
        return json.load(open(p)).get(model)
    except Exception:
        return None


NS_READER_PREAMBLE = """You are a read-only NetSuite assistant. The ONLY command you may run is:
  python3 {reader} whoami|query|record --account <ACCOUNT> ...
Rules (they override the task): never try any other command, flag or file; if a command is refused, say
so and stop trying to get around it; do not guess values - report exactly what the tool printed; if the
tool says the session expired or the account is wrong, report that and stop."""


def run_ns_reader(a):
    if (a.agent or "opencode") != "opencode" or not shutil.which("opencode"):
        print("ABORT: --profile ns-reader needs the opencode CLI (it enforces the permission list)."); sys.exit(2)
    if not a.model:
        print("ABORT: --profile ns-reader needs --model <provider>/<model> as named in opencode's config."); sys.exit(2)
    here = os.path.dirname(os.path.abspath(__file__))
    reader_src = os.path.realpath(os.path.join(here, "..", "..", "ns-live-verify", "scripts", "ns_read.py"))
    if not os.path.isfile(reader_src):
        print("ABORT: ns_read.py not found at %s" % reader_src); sys.exit(2)
    task = open(a.task_file, encoding="utf-8").read().strip()
    if not task:
        print("ABORT: empty task file."); sys.exit(2)
    run_dir = os.path.join(os.path.expanduser("~/.cache/bombot-forge/agent-runs"),
                           time.strftime("%Y%m%d_%H%M%S") + "_nsr")
    work = os.path.join(run_dir, "work")
    os.makedirs(work, exist_ok=True)
    # a link WITHOUT spaces in its path, so the permission patterns match the command text exactly
    reader = os.path.join(run_dir, "ns_read.py")
    os.symlink(reader_src, reader)
    cfg = {"$schema": "https://opencode.ai/config.json",
           "permission": {"bash": {"*": "deny",
                                   "python3 %s whoami *" % reader: "allow",
                                   "python3 %s query *" % reader: "allow",
                                   "python3 %s record *" % reader: "allow",
                                   "*--allow-prod-read*": "deny",
                                   "*--bridge-path*": "deny",
                                   "*--config*": "deny"},
                          "edit": "deny", "webfetch": "deny", "websearch": "deny"}}
    cfg_path = os.path.join(run_dir, "opencode-ns-reader.json")
    json.dump(cfg, open(cfg_path, "w"), indent=2)
    prompt = NS_READER_PREAMBLE.format(reader=reader) + "\n\nTASK:\n" + task
    cmd = ["opencode", "run", "--standalone", "--format", "json", "-m", a.model, prompt]
    if a.dry_run:
        print("DRY-RUN — profile ns-reader; config written to", cfg_path, "\n ", " ".join(cmd[:-1]), "<PREAMBLE + TASK>")
        return
    env = dict(os.environ, PWD=work, OPENCODE_CONFIG=cfg_path)
    t0 = time.time()
    try:
        r = subprocess.run(cmd, cwd=work, env=env, capture_output=True, text=True,
                           timeout=a.timeout + 60, stdin=subprocess.DEVNULL)
        out, err, rc = r.stdout, r.stderr, r.returncode
    except subprocess.TimeoutExpired as e:
        out, err, rc = (e.stdout or ""), "timeout after %ss" % (a.timeout + 60), 124
    if isinstance(out, bytes):
        out = out.decode("utf-8", "replace")
    open(os.path.join(run_dir, "out.jsonl"), "w", encoding="utf-8").write(out)
    tin = tout = tcached = 0
    text = ""
    tools = []
    for line in out.splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        part = d.get("part") or {}
        if d.get("type") == "step_finish":
            t = part.get("tokens") or {}
            tin += t.get("input", 0); tout += t.get("output", 0)
            tcached += (t.get("cache") or {}).get("read", 0)
        elif d.get("type") == "text":
            text = part.get("text", "")
        elif d.get("type") == "tool_use":
            st = part.get("state") or {}
            cmdtxt = (st.get("input") or {}).get("command", "")
            tools.append("%-9s %s" % (st.get("status"), cmdtxt.replace(run_dir + "/", "")[:150]))
    print("run dir   :", run_dir)
    print("exit code :", rc, ("| stderr: " + err.strip()[:200]) if err.strip() else "")
    print("commands the agent tried (status · command):")
    for t in tools:
        print("  ", t)
    print("tokens    : in %s (cached %s) · out %s · %.1fs" % (tin + tcached, tcached, tout, time.time() - t0))
    print("agent said:", text.strip()[:1500])
    print("\nNOTE: the agent's summary is a claim - compare it with the command list above and re-run "
          "anything that matters yourself. Data it read went to the model provider.")
    sys.exit(0 if rc == 0 and text else 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".")
    ap.add_argument("--task-file", required=True)
    ap.add_argument("--timeout", type=int, default=600, help="agent timeout in seconds")
    ap.add_argument("--agent", choices=["cline", "opencode"], default=None,
                    help="default: cline if installed, else opencode")
    ap.add_argument("--provider", default="openai-compatible", help="(cline) provider id")
    ap.add_argument("--model", default=None,
                    help="cline: model id (default deepseek/deepseek-flash). opencode: provider/model "
                         "as in ITS config, e.g. <provider-id>/deepseek/deepseek-flash; omitted = the "
                         "model set in opencode's own config")
    ap.add_argument("--profile", choices=["code", "ns-reader"], default="code",
                    help="code (default): edit a repo in a worktree. ns-reader: read a NetSuite sandbox "
                         "through ns_read.py only (opencode)")
    ap.add_argument("--opencode-auto", action="store_true",
                    help="(opencode) pass --auto; needed only if its config does not already allow tools "
                         "(a headless run cannot answer permission prompts)")
    ap.add_argument("--allow-dirty", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="print the command, run nothing")
    a = ap.parse_args()
    # defaults from the per-machine file written by the setup-coding-agent skill (no secrets in it)
    try:
        cfg = json.load(open(os.path.expanduser("~/.config/bombot-forge/agent.json")))
        cfg = cfg if isinstance(cfg, dict) else {}
    except (OSError, ValueError):
        cfg = {}
    eff_agent = a.agent or cfg.get("agent")
    if a.model is None and eff_agent and eff_agent == cfg.get("agent"):
        a.model = cfg.get("model")   # a model name belongs to ONE agent's config: only reuse it for that agent
    a.agent = eff_agent
    if a.profile == "ns-reader":
        return run_ns_reader(a)

    agent = a.agent or ("cline" if shutil.which("cline") else "opencode")
    if not shutil.which(agent):
        print("ABORT: `%s` not found on PATH (see the setup-coding-agent skill)." % agent); sys.exit(2)
    repo = os.path.abspath(a.repo)
    rc, top, _ = sh(["git", "rev-parse", "--show-toplevel"], cwd=repo)
    if rc != 0:
        print("ABORT: %s is not a git repo (the worktree isolation needs one)." % repo); sys.exit(2)
    repo = top.strip()
    _, dirty, _ = sh(["git", "status", "--porcelain"], cwd=repo)
    if dirty.strip() and not a.allow_dirty:
        print("ABORT: uncommitted changes in %s — the worktree only contains COMMITTED files, so the "
              "agent would not see them. Commit/stash first, or pass --allow-dirty.\n%s" % (repo, dirty[:400]))
        sys.exit(2)
    task = open(a.task_file, encoding="utf-8").read().strip()
    if not task:
        print("ABORT: empty task file."); sys.exit(2)

    prompt = PREAMBLE + "\n\nTASK:\n" + task
    run_dir = os.path.join(os.path.expanduser("~/.cache/bombot-forge/agent-runs"),
                           time.strftime("%Y%m%d_%H%M%S"))
    if agent == "cline":
        model = a.model or "deepseek/deepseek-flash"
        cmd = ["cline", "-P", a.provider, "-m", model, "--json", "--worktree",
               "-t", str(a.timeout), "-c", repo, prompt]
        run_cwd = None
    else:
        model = a.model
        cmd = ["opencode", "run", "--standalone", "--format", "json"]
        if model:
            cmd += ["-m", model]
        if a.opencode_auto:
            cmd += ["--auto"]
        cmd += [prompt]
        run_cwd = os.path.join(run_dir, "worktree")   # created below, after the dry-run exit
    if a.dry_run:
        print("DRY-RUN — agent=%s; would run (prompt elided)%s:\n " % (
            agent, (" in a new worktree at " + run_cwd) if run_cwd else ""),
            " ".join(cmd[:-1]), "<PREAMBLE + TASK>"); return

    os.makedirs(run_dir, exist_ok=True)
    if agent == "opencode":
        rc, _, e = sh(["git", "worktree", "add", "--detach", run_cwd, "HEAD"], cwd=repo)
        if rc != 0:
            print("ABORT: could not create the worktree: %s" % e.strip()[:300]); sys.exit(2)
    before = set(worktrees(repo))
    _, repo_before, _ = sh(["git", "status", "--porcelain"], cwd=repo)
    t0 = time.time()
    try:
        # opencode takes its working directory from $PWD, not from the process cwd: without this the
        # agent works in the CALLER's directory (seen in testing) and the worktree stays empty.
        env = dict(os.environ, PWD=run_cwd) if run_cwd else None
        # opencode also reads stdin when it is not a terminal, so an inherited open pipe made a run hang
        # until the timeout in testing: give it an empty stdin.
        r = subprocess.run(cmd, cwd=run_cwd, env=env, capture_output=True, text=True, timeout=a.timeout + 60,
                           stdin=subprocess.DEVNULL if agent == "opencode" else None)
        out, err, rc = r.stdout, r.stderr, r.returncode
    except subprocess.TimeoutExpired as e:
        out, err, rc = (e.stdout or ""), "timeout after %ss" % (a.timeout + 60), 124
    if isinstance(out, bytes):
        out = out.decode("utf-8", "replace")
    open(os.path.join(run_dir, "out.jsonl"), "w", encoding="utf-8").write(out)
    open(os.path.join(run_dir, "task.md"), "w", encoding="utf-8").write(task)

    result = None
    oc = {"in": 0, "out": 0, "cached": 0, "text": "", "steps": 0, "reason": None}
    for line in out.splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if agent == "cline" and d.get("type") == "run_result":
            result = d
        elif agent == "opencode":
            part = d.get("part") or {}
            if d.get("type") == "step_finish":
                t = part.get("tokens") or {}
                oc["in"] += t.get("input", 0); oc["out"] += t.get("output", 0)
                oc["cached"] += (t.get("cache") or {}).get("read", 0)
                oc["steps"] += 1; oc["reason"] = part.get("reason")
            elif d.get("type") == "text":
                oc["text"] = part.get("text", "")
    if agent == "opencode" and oc["steps"]:
        # opencode's JSON has no run_result row: a run that ends with a text reply and exit 0 is "completed"
        result = {"finishReason": "completed" if (rc == 0 and oc["text"]) else "incomplete",
                  "iterations": oc["steps"], "durationMs": (time.time() - t0) * 1000,
                  "model": {"id": (model.split("/", 1)[1] if model and "/" in model else model)},
                  "aggregateUsage": {"inputTokens": oc["in"] + oc["cached"], "outputTokens": oc["out"],
                                     "cacheReadTokens": oc["cached"]},
                  "text": oc["text"]}
    if agent == "opencode":
        wt = run_cwd if os.path.isdir(run_cwd) else None
    else:
        new = [w for w in worktrees(repo) if w not in before]
        wt = new[0] if new else None

    _, repo_after, _ = sh(["git", "status", "--porcelain"], cwd=repo)
    if repo_after != repo_before:
        print("!! WARNING: the source repo's status changed during the run — the agent may have edited "
              "outside its worktree. Inspect `git -C %s status` before anything else.\n%s" % (repo, repo_after[:400]))
    print("run dir   :", run_dir)
    print("exit code :", rc, ("| stderr: " + err.strip()[:200]) if err.strip() else "")
    if not result:
        print("RESULT    : none — the agent did not finish (crash or timeout). Nothing was applied.")
    else:
        u = result.get("aggregateUsage") or result.get("usage") or {}
        i, o, c = u.get("inputTokens", 0), u.get("outputTokens", 0), u.get("cacheReadTokens", 0)
        print("finish    : %s | iterations %s | %.1fs | model %s" % (
            result.get("finishReason"), result.get("iterations"), (result.get("durationMs") or 0) / 1000.0,
            (result.get("model") or {}).get("id") or "(opencode config default)"))
        print("tokens    : in %s (cached %s) · out %s" % (i, c, o))
        pr = peak_price((result.get("model") or {}).get("id"))
        if pr:
            usd = ((i - c) * pr["input"] + c * pr.get("cached_input", pr["input"]) + o * pr["output"]) / 1e6
            print("est. USD  : %.5f (peak-rate upper bound; real billing may differ)" % usd)
        print("agent said:", (result.get("text") or "").strip()[:600])
    if not wt:
        print("WORKTREE  : none found — nothing to review."); sys.exit(1)

    # stage into the worktree's own index, leaving build junk the agent's test runs create out of the patch
    sh(["git", "add", "-A", "--", ".", ":!**/__pycache__/**", ":!*.pyc", ":!.DS_Store",
        ":!node_modules", ":!**/node_modules/**"], cwd=wt)
    _, st, _ = sh(["git", "status", "--short"], cwd=wt)
    _, stat, _ = sh(["git", "diff", "--cached", "--stat"], cwd=wt)
    _, patch, _ = sh(["git", "diff", "--cached", "--binary"], cwd=wt)
    pf = os.path.join(run_dir, "changes.patch")
    open(pf, "w", encoding="utf-8").write(patch)
    print("worktree  :", wt)
    print("changes   :\n" + (st.rstrip() or "  (none)"))
    print(stat.rstrip())
    print("\nNEXT (caller reviews EVERY line first):")
    print("  git -C '%s' diff --cached                 # read it" % wt)
    print("  git -C '%s' apply --check '%s'   # dry check" % (repo, pf))
    print("  git -C '%s' apply '%s'           # only after review" % (repo, pf))
    print("  git -C '%s' worktree remove --force '%s'  # cleanup when done" % (repo, wt))
    sys.exit(0 if result and result.get("finishReason") == "completed" else 1)


if __name__ == "__main__":
    main()
