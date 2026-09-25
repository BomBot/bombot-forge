#!/usr/bin/env python3
"""
ask_cheap.py — send one prompt to the cheap model behind the TEIBTO endpoint and print the reply.

Usage:
  python3 ask_cheap.py [prompt_file] [-s "system prompt"]
  python3 ask_cheap.py <<'EOF'        # prompt from stdin when no file is given
  ...prompt...
  EOF

Config (env vars, all optional except the key):
  TEIBTO_API_KEY    API key. If unset, read from TEIBTO_ENV_FILE.
  TEIBTO_ENV_FILE   KEY=VALUE file holding the key (default ~/.config/teibto/api.env)
  TEIBTO_BASE_URL   OpenAI-compatible base URL (default tokenhub-intl, /v1)
  TEIBTO_MODEL      model id (default deepseek/deepseek-flash)
  TEIBTO_TIMEOUT    seconds (default 120)

The key is sent only in the Authorization header — never printed, never on the command line.
Exit codes: 0 ok · 1 request/HTTP error · 2 missing key/config.
"""
import argparse
import json
import os
import ssl
import sys
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "https://tokenhub-intl.tencentcloudmaas.com/v1"
DEFAULT_MODEL = "deepseek/deepseek-flash"
DEFAULT_ENV_FILE = "~/.config/teibto/api.env"
SETUP_HINT = (
    "Save the key once per machine (typed, not echoed):\n"
    "  bash -c 'mkdir -p ~/.config/teibto && read -rsp \"TEIBTO_API_KEY: \" k && "
    "printf \"TEIBTO_API_KEY=%s\\n\" \"$k\" > ~/.config/teibto/api.env && "
    "chmod 600 ~/.config/teibto/api.env && echo && echo saved'"
)


def load_key():
    key = os.environ.get("TEIBTO_API_KEY", "").strip()
    if key:
        return key
    path = os.path.expanduser(os.environ.get("TEIBTO_ENV_FILE", DEFAULT_ENV_FILE))
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line.startswith("TEIBTO_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return ""


def load_prices(model):
    """USD per 1M tokens for this model: prices.json next to this script, overridden by env."""
    p = {}
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "prices.json"),
                  encoding="utf-8") as fh:
            p = dict(json.load(fh).get(model) or {})
    except (FileNotFoundError, ValueError):
        pass
    for key, env in (("input", "TEIBTO_PRICE_IN"), ("output", "TEIBTO_PRICE_OUT"),
                     ("cached_input", "TEIBTO_PRICE_CACHED")):
        if os.environ.get(env):
            p[key] = float(os.environ[env])
    return p


def usage_line(model, usage):
    """One stderr line with token counts (and USD cost when prices are configured)."""
    u = usage or {}
    pin, pout = int(u.get("prompt_tokens") or 0), int(u.get("completion_tokens") or 0)
    cached = int((u.get("prompt_tokens_details") or {}).get("cached_tokens") or 0)
    reasoning = int((u.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0)
    total = int(u.get("total_tokens") or pin + pout)
    line = "[ask_cheap model: %s | tokens in=%d out=%d total=%d (cached=%d, reasoning=%d incl. in out)" % (
        model, pin, pout, total, cached, reasoning)
    pr = load_prices(model)
    if pr.get("input") is not None and pr.get("output") is not None:
        cached_rate = pr["cached_input"] if pr.get("cached_input") is not None else pr["input"]
        # OpenAI-style usage: prompt_tokens includes cached tokens; completion includes reasoning.
        cost = ((pin - cached) * pr["input"] + cached * cached_rate + pout * pr["output"]) / 1e6
        line += " | cost=$%.6f" % cost
    else:
        line += " | cost=n/a (no price set for this model)"
    return line + "]"


def tls_context():
    # python.org macOS builds ship with an empty CA store until "Install Certificates" is run.
    ctx = ssl.create_default_context()
    if ctx.cert_store_stats().get("x509_ca", 0):
        return ctx
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass
    if os.path.exists("/etc/ssl/cert.pem"):
        return ssl.create_default_context(cafile="/etc/ssl/cert.pem")
    return ctx


def main():
    ap = argparse.ArgumentParser(description="Ask the cheap TEIBTO-endpoint model one question")
    ap.add_argument("prompt_file", nargs="?", help="file with the prompt (default: stdin)")
    ap.add_argument("-s", "--system", default="You are a helpful assistant.")
    args = ap.parse_args()

    key = load_key()
    if not key:
        sys.stderr.write("ask_cheap: no TEIBTO_API_KEY found (env or %s).\n%s\n"
                         % (os.environ.get("TEIBTO_ENV_FILE", DEFAULT_ENV_FILE), SETUP_HINT))
        return 2

    if args.prompt_file and args.prompt_file != "-":
        with open(args.prompt_file, encoding="utf-8") as fh:
            prompt = fh.read()
    else:
        prompt = sys.stdin.read()
    if not prompt.strip():
        sys.stderr.write("ask_cheap: empty prompt\n")
        return 2

    base = os.environ.get("TEIBTO_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    body = json.dumps({
        "model": os.environ.get("TEIBTO_MODEL", DEFAULT_MODEL),
        "messages": [
            {"role": "system", "content": args.system},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        base + "/chat/completions", data=body, method="POST",
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=float(os.environ.get("TEIBTO_TIMEOUT", "120")),
                                    context=tls_context()) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:500]
        sys.stderr.write("ask_cheap: HTTP %s from %s\n%s\n" % (e.code, base, detail))
        return 1
    except (urllib.error.URLError, TimeoutError) as e:
        sys.stderr.write("ask_cheap: request failed: %s\n" % e)
        return 1

    try:
        sys.stdout.write(data["choices"][0]["message"]["content"])
        sys.stdout.write("\n")
        model = data.get("model") or os.environ.get("TEIBTO_MODEL", DEFAULT_MODEL)
        sys.stderr.write(usage_line(model, data.get("usage")) + "\n")
    except (KeyError, IndexError, TypeError):
        sys.stderr.write("ask_cheap: unexpected response shape: %s\n" % json.dumps(data)[:500])
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
