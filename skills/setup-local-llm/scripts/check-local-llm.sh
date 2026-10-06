#!/usr/bin/env bash
# PASS/FAIL check of the local-llm setup on this machine (read-only; changes nothing).
# Route: Mac -> `bombot` MCP bridge (Tailscale) -> Ollama on the GPU box (127.0.0.1 there).
# The bridge token is read from the MCP registration only to make one authenticated call;
# it is never printed.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL="$(dirname "$HERE")"
AGENT_DST="$HOME/.claude/agents/local-llm.md"
MODEL="${OLLAMA_MODEL:-gpt-oss:20b}"
FAILS=0
pass() { echo "PASS  $*"; }
fail() { echo "FAIL  $*"; FAILS=$((FAILS + 1)); }
same() { [ -f "$1" ] && [ "$(shasum -a 256 < "$1")" = "$(shasum -a 256 < "$2")" ]; }

REG="$(claude mcp get bombot 2>/dev/null || true)"
URL="$(printf '%s\n' "$REG" | sed -n 's/.*BOMBOT_BRIDGE_URL=\([^ ]*\).*/\1/p' | head -1)"
TOKEN="$(printf '%s\n' "$REG" | sed -n 's/.*BOMBOT_BRIDGE_TOKEN=\([^ ]*\).*/\1/p' | head -1)"
CLIENT="$(printf '%s\n' "$REG" | sed -n 's/^ *Args: *//p' | head -1)"

# 1. Tailscale (the GPU box lives on the tailnet)
if tailscale status >/dev/null 2>&1; then pass "tailscale up"
else fail "tailscale not running — run: tailscale up"; fi

# 2. bombot MCP registered and connected
if printf '%s\n' "$REG" | grep -q "Connected"; then pass "MCP 'bombot' registered + connected"
elif [ -n "$REG" ]; then fail "MCP 'bombot' registered but NOT connected — check URL/script path (and that the box is on)"
else fail "MCP 'bombot' not registered — run: bash ~/homelab-mcp/mac/install.sh (needs .env)"; fi

# 3. Bridge health lists the Ollama tools
HEALTH="$(curl -s -m 8 "${URL:-http://invalid}/health" || true)"
if printf '%s' "$HEALTH" | grep -q '"ask_ollama"'; then pass "bridge healthy at $URL (ask_ollama listed)"
else fail "bridge not answering at ${URL:-<unset>} (box off? bridge_server.py not running? Tailscale down?)"; fi

# 4. Pinned model is pulled on the box (one authenticated call through the bridge client)
if [ -n "$URL" ] && [ -n "$TOKEN" ] && [ -f "$CLIENT" ]; then
  MODELS="$(printf '%s\n' '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
    '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"list_ollama_models","arguments":{}}}' \
    | BOMBOT_BRIDGE_URL="$URL" BOMBOT_BRIDGE_TOKEN="$TOKEN" python3 "$CLIENT" 2>/dev/null \
    | python3 -c "
import sys, json
for line in sys.stdin:
    d = json.loads(line)
    if d.get('id') == 2:
        print(d['result']['content'][0]['text'])
" 2>/dev/null || true)"
  if printf '%s' "$MODELS" | grep -q -- "- $MODEL "; then pass "model $MODEL is pulled on the box"
  else fail "model $MODEL not listed by the bridge — pull it on the box: ollama pull $MODEL"; fi
else
  fail "cannot call the bridge (URL/token/client path not found in 'claude mcp get bombot')"
fi

# 5. Agent file installed and identical to the canonical copy
if same "$AGENT_DST" "$SKILL/reference/local-llm.agent.md"; then pass "agent local-llm matches canonical"
elif [ -f "$AGENT_DST" ]; then fail "agent DRIFTED from canonical — diff before copying: diff \"$AGENT_DST\" \"$SKILL/reference/local-llm.agent.md\""
else fail "agent missing: $AGENT_DST"; fi

# 6. Old direct 'ollama' MCP: informational only (it cannot reach a localhost-only Ollama)
if claude mcp get ollama >/dev/null 2>&1; then
  echo "NOTE  an 'ollama' MCP is still registered (direct to $(claude mcp get ollama 2>/dev/null | sed -n 's/.*OLLAMA_URL=\([^ ]*\).*/\1/p' | head -1)); the agent no longer uses it"
fi

echo "---"
[ "$FAILS" -eq 0 ] && echo "ALL PASS" || echo "$FAILS check(s) failed"
exit "$FAILS"
