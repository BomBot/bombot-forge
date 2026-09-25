#!/usr/bin/env bash
# PASS/FAIL check of the local-llm setup on this machine (read-only; changes nothing).
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL="$(dirname "$HERE")"
MCP_DST="$HOME/.claude/mcp-servers/ollama_mcp_server.py"
AGENT_DST="$HOME/.claude/agents/local-llm.md"
FAILS=0
pass() { echo "PASS  $*"; }
fail() { echo "FAIL  $*"; FAILS=$((FAILS + 1)); }
same() { [ -f "$1" ] && [ "$(shasum -a 256 < "$1")" = "$(shasum -a 256 < "$2")" ]; }

# Use the URL/model the MCP server is actually registered with, if any.
REG="$(claude mcp get ollama 2>/dev/null || true)"
URL="$(printf '%s\n' "$REG" | sed -n 's/.*OLLAMA_URL=\([^ ]*\).*/\1/p' | head -1)"
MODEL="$(printf '%s\n' "$REG" | sed -n 's/.*OLLAMA_MODEL=\([^ ]*\).*/\1/p' | head -1)"
URL="${URL:-${OLLAMA_URL:-http://bombot-gaming:11434}}"
MODEL="${MODEL:-${OLLAMA_MODEL:-gpt-oss:20b}}"

# 1. Tailscale (Ollama lives on the tailnet GPU box)
if tailscale status >/dev/null 2>&1; then pass "tailscale up"
else fail "tailscale not running — run: tailscale up"; fi

# 2. Ollama reachable, pinned model pulled
TAGS="$(curl -s -m 8 "$URL/api/tags" || true)"
if [ -n "$TAGS" ]; then
  pass "ollama reachable at $URL"
  if printf '%s' "$TAGS" | python3 -c "import json,sys; sys.exit(0 if '$MODEL' in [m['name'] for m in json.load(sys.stdin).get('models',[])] else 1)"; then
    pass "model $MODEL is pulled"
  else fail "model $MODEL not found on the box — pull it there: ollama pull $MODEL"; fi
else fail "ollama not reachable at $URL (box off? Ollama not running? Tailscale down?)"; fi

# 3. MCP server script installed and identical to the canonical copy
if same "$MCP_DST" "$HERE/ollama_mcp_server.py"; then pass "MCP script matches canonical"
elif [ -f "$MCP_DST" ]; then fail "MCP script DRIFTED from canonical — diff before copying: diff \"$MCP_DST\" \"$HERE/ollama_mcp_server.py\""
else fail "MCP script missing: $MCP_DST"; fi

# 4. MCP server registered and connected
if printf '%s\n' "$REG" | grep -q "Connected"; then pass "MCP 'ollama' registered + connected"
elif [ -n "$REG" ]; then fail "MCP 'ollama' registered but NOT connected — check URL/script path"
else fail "MCP 'ollama' not registered (see Setup step 3)"; fi

# 5. Agent file installed and identical to the canonical copy
if same "$AGENT_DST" "$SKILL/reference/local-llm.agent.md"; then pass "agent local-llm matches canonical"
elif [ -f "$AGENT_DST" ]; then fail "agent DRIFTED from canonical — diff before copying: diff \"$AGENT_DST\" \"$SKILL/reference/local-llm.agent.md\""
else fail "agent missing: $AGENT_DST"; fi

echo "---"
[ "$FAILS" -eq 0 ] && echo "ALL PASS" || echo "$FAILS check(s) failed"
exit "$FAILS"
