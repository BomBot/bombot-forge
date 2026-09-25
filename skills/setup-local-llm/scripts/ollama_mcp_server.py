"""
Minimal MCP (stdio) server exposing the local Ollama box as a tool.

Why this exists: Claude Code subagents can only run on Anthropic models
(`model:` accepts sonnet/opus/haiku/fable/a full model id/inherit), so you
cannot make a subagent *think* with Ollama. You can, however, give an agent a
TOOL that delegates work to Ollama — which is what this provides.

Hand-rolled JSON-RPC because the `mcp` package isn't installed in the embedded
Python and this needs no dependencies beyond the stdlib.

Protocol notes:
  - one JSON object per line on stdin/stdout
  - stdout is RESERVED for JSON-RPC; all logging goes to stderr
"""
import json
import os
import sys
import urllib.request
import urllib.error

OLLAMA = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
# Pinned model. Override per-call, or globally via OLLAMA_MODEL in .mcp.json.
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:14b")
# How long Ollama keeps the model resident. Short by default: this machine has
# a single 12GB card that ComfyUI / Hunyuan3D also need, and a resident 9GB
# LLM is what makes 3D jobs spill to system RAM.
KEEP_ALIVE = os.environ.get("OLLAMA_KEEP_ALIVE", "5m")

SERVER_INFO = {"name": "ollama", "version": "1.0.0"}


def log(msg):
    print(f"[ollama-mcp] {msg}", file=sys.stderr, flush=True)


def _post(path, payload, timeout=600):
    req = urllib.request.Request(
        OLLAMA + path, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _get(path, timeout=10):
    with urllib.request.urlopen(OLLAMA + path, timeout=timeout) as r:
        return json.loads(r.read())


# ----------------------------------------------------------------- tools
def tool_ask(args):
    prompt = (args.get("prompt") or "").strip()
    if not prompt:
        return "ERROR: prompt is empty"
    model = args.get("model") or DEFAULT_MODEL
    msgs = []
    if args.get("system"):
        msgs.append({"role": "system", "content": args["system"]})
    msgs.append({"role": "user", "content": prompt})
    body = {"model": model, "messages": msgs, "stream": False,
            "keep_alive": KEEP_ALIVE}
    if args.get("temperature") is not None:
        body["options"] = {"temperature": float(args["temperature"])}
    try:
        r = _post("/api/chat", body)
    except urllib.error.HTTPError as e:
        return f"ERROR from Ollama ({e.code}): {e.read()[:400].decode('utf-8','replace')}"
    except Exception as e:
        return f"ERROR calling Ollama at {OLLAMA}: {e}"
    txt = (r.get("message") or {}).get("content", "")
    # qwen3 emits chain-of-thought in <think> blocks; strip so the caller gets
    # only the answer (the reasoning is rarely what the caller asked for).
    if "</think>" in txt:
        txt = txt.split("</think>", 1)[1]
    return txt.strip() or "(empty response)"


def tool_models(args):
    try:
        tags = _get("/api/tags").get("models", [])
    except Exception as e:
        return f"ERROR: cannot reach Ollama at {OLLAMA}: {e}"
    lines = [f"pinned default: {DEFAULT_MODEL}", ""]
    for m in tags:
        gb = m.get("size", 0) / 1e9
        lines.append(f"- {m.get('name')}  ({gb:.1f} GB)")
    try:
        loaded = _get("/api/ps").get("models", [])
        lines.append("")
        lines.append("loaded now: " +
                     (", ".join(m.get("name", "?") for m in loaded) or "none"))
    except Exception:
        pass
    return "\n".join(lines)


def tool_unload(args):
    """Free VRAM before a GPU job (3D generation) needs the card."""
    model = args.get("model") or DEFAULT_MODEL
    try:
        _post("/api/chat", {"model": model, "messages": [], "keep_alive": 0},
              timeout=30)
        return f"unloaded {model} (VRAM released)"
    except Exception as e:
        return f"ERROR unloading {model}: {e}"


TOOLS = [
    {
        "name": "ask_ollama",
        "description": (
            f"Send a prompt to the LOCAL Ollama model (default: {DEFAULT_MODEL}) "
            "and return its reply. Runs on this machine — free, private, no API "
            "cost — but slower and weaker than Claude. Good for bulk/rote text "
            "work: summarising, drafting, translating, renaming, classifying, "
            "boilerplate. NOTE: it shares the single 12GB GPU with ComfyUI and "
            "the 3D pipeline, so avoid calling it while a 3D job is running."),
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "The instruction or question."},
                "system": {"type": "string", "description": "Optional system prompt."},
                "model": {"type": "string",
                          "description": f"Override the pinned model (default {DEFAULT_MODEL})."},
                "temperature": {"type": "number", "description": "0.0-1.0, optional."},
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "list_ollama_models",
        "description": "List models available on the local Ollama box, their sizes, and which are currently loaded in VRAM.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "unload_ollama",
        "description": "Unload the model from VRAM (keep_alive=0). Call before starting a 3D/ComfyUI GPU job so the 12GB card is free.",
        "inputSchema": {
            "type": "object",
            "properties": {"model": {"type": "string"}},
        },
    },
]

HANDLERS = {"ask_ollama": tool_ask, "list_ollama_models": tool_models,
            "unload_ollama": tool_unload}


# ----------------------------------------------------------------- JSON-RPC
def reply(mid, result=None, error=None):
    msg = {"jsonrpc": "2.0", "id": mid}
    if error is not None:
        msg["error"] = error
    else:
        msg["result"] = result
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def handle(req):
    method = req.get("method")
    mid = req.get("id")
    params = req.get("params") or {}

    # notifications carry no id and must get no response
    if mid is None:
        return

    if method == "initialize":
        reply(mid, {
            "protocolVersion": params.get("protocolVersion", "2025-06-18"),
            "capabilities": {"tools": {}},
            "serverInfo": SERVER_INFO,
        })
    elif method == "ping":
        reply(mid, {})
    elif method == "tools/list":
        reply(mid, {"tools": TOOLS})
    elif method == "tools/call":
        name = params.get("name")
        fn = HANDLERS.get(name)
        if not fn:
            reply(mid, error={"code": -32602, "message": f"unknown tool: {name}"})
            return
        try:
            text = fn(params.get("arguments") or {})
            is_err = isinstance(text, str) and text.startswith("ERROR")
            reply(mid, {"content": [{"type": "text", "text": text}],
                        "isError": bool(is_err)})
        except Exception as e:
            reply(mid, {"content": [{"type": "text", "text": f"ERROR: {e}"}],
                        "isError": True})
    else:
        reply(mid, error={"code": -32601, "message": f"method not found: {method}"})


def main():
    log(f"started; ollama={OLLAMA} pinned_model={DEFAULT_MODEL} keep_alive={KEEP_ALIVE}")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception as e:
            log(f"bad json: {e}")
            continue
        try:
            handle(req)
        except Exception as e:
            log(f"handler crashed: {e}")


if __name__ == "__main__":
    main()
