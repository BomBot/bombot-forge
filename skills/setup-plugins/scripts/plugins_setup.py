#!/usr/bin/env python3
"""
plugins_setup.py - show which of the plugins listed in ../plugins.json this machine already has, and install
the ones the USER picked, from their GitHub source, at user scope.

  python3 plugins_setup.py                     # plan (default): one line per plugin + what apply would run
  python3 plugins_setup.py apply NAME [NAME..] [--dry-run]
  python3 plugins_setup.py apply --all-missing [--dry-run]

It runs only these `claude` commands (anything else is refused in code, not by convention):
  plugin list --json | plugin marketplace list --json | plugin marketplace add <source> --scope user |
  plugin install <plugin>@<marketplace> --scope user
It never logs in, never reads a token, and never installs a plugin name that is not in plugins.json.

Exit codes: 0 ok / nothing to do - 1 at least one install failed - 2 refused (bad name, bad manifest, no claude CLI)
Env: CLAUDE_BIN overrides the `claude` executable (used by the offline tests).
"""
import argparse, json, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(HERE, "..", "plugins.json")
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
SOURCE_RE = re.compile(r"^(https://[A-Za-z0-9._~/@:-]+|[A-Za-z0-9._-]+/[A-Za-z0-9._-]+)$")
AUTH_HINT = re.compile(r"authenticat|permission denied|could not read|not found|403|401|access", re.I)


def claude_bin():
    return os.environ.get("CLAUDE_BIN") or shutil.which("claude") or "claude"


def run_claude(args):
    """Run `claude plugin ...` - only the four shapes this script needs. Returns (rc, stdout, stderr)."""
    ok = (args[:3] == ["plugin", "list", "--json"] and len(args) == 3) or \
         (args[:4] == ["plugin", "marketplace", "list", "--json"] and len(args) == 4) or \
         (args[:3] == ["plugin", "marketplace", "add"] and len(args) == 6 and args[4:] == ["--scope", "user"]) or \
         (args[:2] == ["plugin", "install"] and len(args) == 5 and args[3:] == ["--scope", "user"])
    if not ok:
        raise ValueError("refused command: %r" % (args,))
    r = subprocess.run([claude_bin()] + args, capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL)
    return r.returncode, r.stdout, r.stderr


def load_manifest(path=None):
    with open(path or MANIFEST, encoding="utf-8") as f:
        d = json.load(f)
    seen = set()
    for e in d.get("plugins", []):
        for k in ("name", "marketplace", "source"):
            if not isinstance(e.get(k), str) or not e[k]:
                raise ValueError("manifest entry missing %r: %r" % (k, e))
        if not NAME_RE.match(e["name"]) or not NAME_RE.match(e["marketplace"]):
            raise ValueError("bad plugin/marketplace name: %r" % (e,))
        if not SOURCE_RE.match(e["source"]) or e["source"].startswith("-"):
            raise ValueError("bad source (want owner/repo or an https git URL): %r" % (e["source"],))
        if e["name"] in seen:
            raise ValueError("duplicate plugin name: %s" % e["name"])
        seen.add(e["name"])
    return d["plugins"]


def read_state():
    rc, out, err = run_claude(["plugin", "list", "--json"])
    if rc != 0:
        raise RuntimeError("`claude plugin list` failed: %s" % (err or out).strip()[:200])
    installed = [p.get("id") or p.get("name") or "" for p in json.loads(out or "[]")]
    rc, out, err = run_claude(["plugin", "marketplace", "list", "--json"])
    if rc != 0:
        raise RuntimeError("`claude plugin marketplace list` failed: %s" % (err or out).strip()[:200])
    markets = [m.get("name") for m in json.loads(out or "[]")]
    return installed, markets


def classify(entry, installed, markets):
    """('installed'|'elsewhere'|'ready'|'needs-marketplace', detail)"""
    want = "%s@%s" % (entry["name"], entry["marketplace"])
    if want in installed:
        return "installed", want
    others = [i for i in installed if i.split("@")[0] == entry["name"]]
    if others:
        return "elsewhere", ", ".join(others)
    if entry["marketplace"] in markets:
        return "ready", want
    return "needs-marketplace", want


def plan(entries, installed, markets):
    lines = []
    for e in entries:
        st, detail = classify(e, installed, markets)
        label = {"installed": "already installed", "elsewhere": "already present as " + detail + " - not installed again",
                 "ready": "missing - marketplace known, install only", "needs-marketplace": "missing - marketplace + install"}[st]
        lines.append("  %-26s %-40s %s" % (e["name"], e["source"], label))
    return lines


def apply(entries, names, dry_run=False):
    by = {e["name"]: e for e in entries}
    bad = [n for n in names if n not in by]
    if bad:
        raise ValueError("not in plugins.json: %s" % ", ".join(bad))
    installed, markets = read_state()
    results = []
    for n in names:
        e = by[n]
        st, detail = classify(e, installed, markets)
        if st in ("installed", "elsewhere"):
            results.append((n, "skipped", "already present (%s)" % detail))
            continue
        cmds = []
        if st == "needs-marketplace":
            cmds.append(["plugin", "marketplace", "add", e["source"], "--scope", "user"])
        cmds.append(["plugin", "install", "%s@%s" % (e["name"], e["marketplace"]), "--scope", "user"])
        if dry_run:
            results.append((n, "would-run", " ; ".join("claude " + " ".join(c) for c in cmds)))
            continue
        failed = None
        for c in cmds:
            rc, out, err = run_claude(c)
            if rc != 0:
                msg = (err or out).strip().splitlines()[-1][:240] if (err or out).strip() else "exit %d" % rc
                hint = " (no access to the repo? this script never logs in - get access or skip it)" if AUTH_HINT.search(err + out) else ""
                failed = "%s: %s%s" % (" ".join(c[:3]), msg, hint)
                break
            if c[1] == "marketplace":
                _, markets = read_state()
                if e["marketplace"] not in markets:
                    failed = "added %s but no marketplace named %r appeared (names now: %s) - fix plugins.json" % (
                        e["source"], e["marketplace"], ", ".join(markets) or "none")
                    break
        results.append((n, "FAILED" if failed else "installed", failed or "ok"))
        if not failed:
            installed.append("%s@%s" % (e["name"], e["marketplace"]))
    return results


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("plan")
    a = sub.add_parser("apply")
    a.add_argument("names", nargs="*")
    a.add_argument("--all-missing", action="store_true")
    a.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    if not (shutil.which("claude") or os.environ.get("CLAUDE_BIN")):
        print("REFUSED: the `claude` CLI is not on PATH."); return 2
    try:
        entries = load_manifest()
        if args.cmd in (None, "plan"):
            installed, markets = read_state()
            print("plugins.json - %d plugins (source: GitHub)" % len(entries))
            print("\n".join(plan(entries, installed, markets)))
            return 0
        names = list(args.names)
        if args.all_missing:
            installed, markets = read_state()
            names += [e["name"] for e in entries if classify(e, installed, markets)[0] in ("ready", "needs-marketplace")
                      and e["name"] not in names]
        if not names:
            print("nothing to install."); return 0
        results = apply(entries, names, args.dry_run)
    except (ValueError, RuntimeError, OSError) as e:
        print("REFUSED:", e); return 2
    for n, st, msg in results:
        print("  %-26s %-9s %s" % (n, st, msg))
    if any(st == "installed" for _, st, _ in results):
        print("\nRestart Claude Code to load the new plugins.")
    return 1 if any(st == "FAILED" for _, st, _ in results) else 0


if __name__ == "__main__":
    sys.exit(main())
