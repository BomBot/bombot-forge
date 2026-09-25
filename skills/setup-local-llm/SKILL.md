---
name: setup-local-llm
description: >-
  Use when setting up, checking, or repairing the `local-llm` worker on a machine — the free,
  private subagent that delegates bulk text work to Ollama on the tailnet GPU box
  (`bombot-gaming`) through the `ollama` MCP server. Installs the MCP script and agent file from
  canonical copies, registers the MCP server, and runs a PASS/FAIL checker. Also covers
  re-snapshotting when the agent file or MCP script is edited on a machine.
---

# Setup Local LLM (Ollama on bombot-gaming)

**Skill version: `202609_01`**

`local-llm` is the **default** cheap worker — free and private (text stays on your own tailnet).
`teibto-worker` (paid DeepSeek) is the fallback, used when named or when this one is unavailable.

Three pieces, all per machine:

| Piece | Lives at | Canonical copy in this skill |
|---|---|---|
| Ollama + models | `bombot-gaming` (Windows GPU box), port 11434 | — (runs on the box) |
| MCP server `ollama` | `~/.claude/mcp-servers/ollama_mcp_server.py`, user scope | `scripts/ollama_mcp_server.py` |
| Agent `local-llm` | `~/.claude/agents/local-llm.md` | `reference/local-llm.agent.md` |

The agent copy is kept under `reference/`, not the plugin's `agents/` folder, on purpose: shipping
it as a plugin agent would create a second `local-llm` next to the user-level one.

## Iron rules (do not soften)

- **Check before you install.** Run the checker first; only fix what FAILs.
- **Never overwrite a drifted file blind.** If the checker says the agent or MCP script DRIFTED,
  `diff` it against the canonical copy and ask. The machine's copy may hold newer lessons (the agent
  file carries measured model benchmarks) — in that case re-snapshot it here instead (see below).
- **Don't change a working machine's registration** just to match this doc (e.g. an IP vs the
  hostname). If the checker passes, leave it.

## Setup (per machine)

Base dir below = this skill's folder (`<skill>`), shown as "Base directory for this skill".

1. **Check what's missing** (read-only):
   ```bash
   bash "<skill>/scripts/check-local-llm.sh"
   ```
2. **Install the MCP script** (only if missing):
   ```bash
   mkdir -p ~/.claude/mcp-servers && cp "<skill>/scripts/ollama_mcp_server.py" ~/.claude/mcp-servers/
   ```
3. **Register the MCP server** (only if not registered) — stdlib Python, no packages needed:
   ```bash
   claude mcp add ollama -s user -e OLLAMA_URL=http://bombot-gaming:11434 -e OLLAMA_MODEL=gpt-oss:20b -e OLLAMA_KEEP_ALIVE=5m -- python3 "$HOME/.claude/mcp-servers/ollama_mcp_server.py"
   ```
4. **Install the agent** (only if missing):
   ```bash
   mkdir -p ~/.claude/agents && cp "<skill>/reference/local-llm.agent.md" ~/.claude/agents/local-llm.md
   ```
5. Restart Claude (Cmd+Q, reopen), then re-run the checker → `ALL PASS`.

## Re-snapshot (after editing on a machine)

When `~/.claude/agents/local-llm.md` or the MCP script is improved on a machine (new benchmark,
new model pin), copy it back here so other machines get it:
```bash
cp ~/.claude/agents/local-llm.md skills/setup-local-llm/reference/local-llm.agent.md
cp ~/.claude/mcp-servers/ollama_mcp_server.py skills/setup-local-llm/scripts/ollama_mcp_server.py
```
Then bump this skill's version, add a CHANGELOG entry, and commit (the repo's redaction CI must pass).

## Gotchas

- **Ollama isn't on the Mac** — it's on `bombot-gaming` over Tailscale. "Not reachable" usually
  means Tailscale is down on one end, the box is off/asleep, or Ollama isn't running there.
- **One 12 GB GPU is shared** with ComfyUI / Hunyuan3D. Don't route work here during a 3D job;
  the agent calls `unload_ollama` to free VRAM (keep-alive is 5 min for the same reason).
- **Hostname vs IP.** New machines use MagicDNS `bombot-gaming:11434` (verified). An older
  registration may point at the tailnet IP instead — both work; see Iron rule 3.
- **Pinned model** is `gpt-oss:20b` (chosen on measured format-obedience + speed — reasons are in
  the agent file). Missing on the box → `ollama pull gpt-oss:20b` there, not on the Mac.

## Quick reference

| Need | Command |
|---|---|
| Check everything | `bash "<skill>/scripts/check-local-llm.sh"` |
| Ollama up? | `curl -s http://bombot-gaming:11434/api/tags` |
| MCP status | `claude mcp get ollama` |
| Register MCP | Setup step 3 |

## Status

v0.1 draft — checker verified on this machine (ALL PASS) and on a simulated fresh machine (flags
the 3 missing pieces; hostname reaches Ollama). Canonical copies captured 2026-09-25, byte-identical
to this machine's files.
