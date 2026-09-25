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
    except (KeyError, IndexError, TypeError):
        sys.stderr.write("ask_cheap: unexpected response shape: %s\n" % json.dumps(data)[:500])
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
