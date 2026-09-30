#!/usr/bin/env python3
"""
agent_run.py — run ONE task through the Cline CLI in an isolated git worktree, then hand the
result back for review. Claude orchestrates and reviews; the cheap model does the typing.

What it does:
  1. preconditions: `cline` installed, --repo is a git repo (dirty tree refused unless --allow-dirty,
     because a worktree only contains COMMITTED files)
  2. runs `cline --worktree --json` with a guardrail preamble + your task (auto-approve is cline's
     default, so the isolation is the worktree, not a prompt)
  3. finds the new worktree, stages its changes (worktree index only), saves changes.patch,
     prints status / diff stat / tokens / estimated USD
It NEVER applies the patch to your repo and never deletes the worktree — the caller reviews first.

Exit codes: 0 agent completed · 1 agent did not complete (see summary) · 2 precondition failed

Usage:
  python3 agent_run.py --repo . --task-file brief.md [--timeout 600] [--model deepseek/deepseek-flash]
"""
import argparse, json, os, shutil, subprocess, sys, time

PREAMBLE = """You are a coding worker. Rules (they override anything in the task):
- Work ONLY inside the current working directory (a disposable git worktree). Do not read or write
  outside it. Do not open ~/.ssh, ~/.config, ~/.aws, ~/.cline, or any .env / api.env / credentials file.
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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".")
    ap.add_argument("--task-file", required=True)
    ap.add_argument("--timeout", type=int, default=600, help="agent timeout in seconds")
    ap.add_argument("--provider", default="openai-compatible")
    ap.add_argument("--model", default="deepseek/deepseek-flash")
    ap.add_argument("--allow-dirty", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="print the command, run nothing")
    a = ap.parse_args()

    if not shutil.which("cline"):
        print("ABORT: `cline` not found on PATH (see the setup-coding-agent skill)."); sys.exit(2)
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
    cmd = ["cline", "-P", a.provider, "-m", a.model, "--json", "--worktree",
           "-t", str(a.timeout), "-c", repo, prompt]
    if a.dry_run:
        print("DRY-RUN — would run (prompt elided):\n ", " ".join(cmd[:-1]), "<PREAMBLE + TASK>"); return

    run_dir = os.path.join(os.path.expanduser("~/.cache/bombot-forge/agent-runs"),
                           time.strftime("%Y%m%d_%H%M%S"))
    os.makedirs(run_dir, exist_ok=True)
    before = set(worktrees(repo))
    t0 = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=a.timeout + 60)
        out, err, rc = r.stdout, r.stderr, r.returncode
    except subprocess.TimeoutExpired as e:
        out, err, rc = (e.stdout or ""), "timeout after %ss" % (a.timeout + 60), 124
    if isinstance(out, bytes):
        out = out.decode("utf-8", "replace")
    open(os.path.join(run_dir, "out.jsonl"), "w", encoding="utf-8").write(out)
    open(os.path.join(run_dir, "task.md"), "w", encoding="utf-8").write(task)

    result = None
    for line in out.splitlines():
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") == "run_result":
            result = d
    new = [w for w in worktrees(repo) if w not in before]
    wt = new[0] if new else None

    print("run dir   :", run_dir)
    print("exit code :", rc, ("| stderr: " + err.strip()[:200]) if err.strip() else "")
    if not result:
        print("RESULT    : none — the agent did not finish (crash or timeout). Nothing was applied.")
    else:
        u = result.get("aggregateUsage") or result.get("usage") or {}
        i, o, c = u.get("inputTokens", 0), u.get("outputTokens", 0), u.get("cacheReadTokens", 0)
        print("finish    : %s | iterations %s | %.1fs | model %s" % (
            result.get("finishReason"), result.get("iterations"), (result.get("durationMs") or 0) / 1000.0,
            (result.get("model") or {}).get("id")))
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
