---
name: setup-local-llm
description: >-
  Use when setting up, checking, or repairing the `local-llm` worker on a machine — the free,
  private subagent that delegates bulk text work to Ollama on the tailnet GPU box
  (`bombot-pc`) through the `bombot` MCP bridge (Ollama there listens on localhost only).
  Installs the agent file from the canonical copy and runs a PASS/FAIL checker. Also covers
  re-snapshotting when the agent file is edited on a machine.
---

# Setup Local LLM (Ollama on bombot-pc, via the bombot bridge)

**Skill version: `202609_03`**

`local-llm` is the **default** cheap worker — free and private (text stays on your own tailnet).
paid DeepSeek (`ask_cheap.py`, see `setup-coding-agent`) is the fallback when this one is unavailable; the old `teibto-worker` subagent was removed in 0.17.0.

**Changed 05/10/2026:** the GPU box moved from `bombot-gaming` (retired) to `bombot-pc`. Ollama
there binds `127.0.0.1` only, on purpose, so the Mac can no longer call it directly; every call
goes through the `bombot` MCP bridge (token auth). The agent therefore uses the bridge's tools
`mcp__bombot__ask_ollama` / `list_ollama_models` / `unload_ollama` (same names and arguments as
the old `ollama` MCP). Set up the bridge first with `video-transcribe`'s prereqs
(`bash ~/homelab-mcp/mac/install.sh`).

Two pieces, per machine:

| Piece | Lives at | Canonical copy in this skill |
|---|---|---|
| Ollama + models + bridge | `bombot-pc` (Windows GPU box); bridge `http://bombot-pc.<tailnet>.ts.net:8765` | — (runs on the box); Mac side: `~/homelab-mcp` |
| Agent `local-llm` | `~/.claude/agents/local-llm.md` | `reference/local-llm.agent.md` |

`scripts/ollama_mcp_server.py` is kept only for a machine whose Ollama *is* reachable directly
(register it as `ollama` and point a copy of the agent at `mcp__ollama__*`); the default setup
below does not use it.

The agent copy is kept under `reference/`, not the plugin's `agents/` folder, on purpose: shipping
it as a plugin agent would create a second `local-llm` next to the user-level one.

## Iron rules (do not soften)

- **Check before you install.** Run the checker first; only fix what FAILs.
- **Never overwrite a drifted file blind.** If the checker says the agent or MCP script DRIFTED,
  `diff` it against the canonical copy and ask. The machine's copy may hold newer lessons (the agent
  file carries measured model benchmarks) — in that case re-snapshot it here instead (see below).
- **Don't change a working machine's registration** just to match this doc. If the checker
  passes, leave it. **Do not remove an old `ollama` MCP on your own** — report it (the checker
  prints a NOTE) and ask.

## How to ask the user (at every decision point in this skill)

A choice is never buried in a paragraph. Do these, in this order:

1. **Bullets first.** One block per option, at most three short lines each: **Pros · Cons · Best when**.
   No paragraphs, no "it depends" prose. Say which option you recommend and why in one line.
2. **Then a picker — the last thing in your message.** Use the `AskUserQuestion` tool: a short label, a
   one-line description that carries the key trade-off, the recommended option first and marked
   "(Recommended)". At most 4 options per question, one decision per question, at most 4 questions per
   call (split further decisions into the next round). Use multi-select only when the choices are not
   exclusive. The user can always type their own answer via "Other".
3. **No picker available?** (the tool is not offered, or the run is unattended) Ask the same thing as a
   numbered list in chat, and wait. Never pick for the user and never treat silence as consent.
4. Don't ask what Step 0 already showed, and don't re-ask something already answered.

## Setup (per machine)

Base dir below = this skill's folder (`<skill>`), shown as "Base directory for this skill".

1. **Check what's missing** (read-only):
   ```bash
   bash "<skill>/scripts/check-local-llm.sh"
   ```
2. **Get the `bombot` bridge connected** (only if the checker says it is not): follow the
   prereqs in `video-transcribe` (needs `~/homelab-mcp/.env` from the box's owner).
3. **Install the agent** (only if missing; if it exists and DRIFTED, `diff` and ask first):
   ```bash
   mkdir -p ~/.claude/agents && cp "<skill>/reference/local-llm.agent.md" ~/.claude/agents/local-llm.md
   ```
4. Restart Claude (Cmd+Q, reopen), then re-run the checker → `ALL PASS`.

## Re-snapshot (after editing on a machine)

When `~/.claude/agents/local-llm.md` is improved on a machine (new benchmark, new model pin),
copy it back here so other machines get it:
```bash
cp ~/.claude/agents/local-llm.md skills/setup-local-llm/reference/local-llm.agent.md
```
Then bump this skill's version, add a CHANGELOG entry, and commit (the repo's redaction CI must pass).

## Gotchas

- **Ollama isn't on the Mac** — it's on `bombot-pc`, reachable only through the bridge.
  `curl bombot-pc:11434` timing out is normal. "Not reachable" means Tailscale is down on one
  end, the box is off/asleep, or `bridge_server.py` is not running there.
- **Always pass `model`.** The bridge's default model (`deepseek-coder-v2:16b`) is not pulled on
  the box, so a call without `model: "gpt-oss:20b"` fails. The agent file says so.
- **The old `ollama` MCP can show ✔ Connected while useless** — it is a stdio process that
  starts fine and then points at `bombot-gaming`'s IP (offline). Do not trust its status.
- **One 12 GB GPU is shared** with ComfyUI / Hunyuan3D. Don't route work here during a 3D job;
  the agent calls `unload_ollama` to free VRAM. The same GPU also runs `transcribe_video`
  (whisper `large-v3`, ~3 GB): two whisper runs plus Ollama pushed VRAM to 10 of 12 GB.
- **Pinned model** is `gpt-oss:20b` (chosen on measured format-obedience + speed — reasons are in
  the agent file). Missing on the box → `ollama pull gpt-oss:20b` there, not on the Mac.

## Quick reference

| Need | Command |
|---|---|
| Check everything | `bash "<skill>/scripts/check-local-llm.sh"` |
| Bridge up? | `curl -s http://bombot-pc.taila8b350.ts.net:8765/health` |
| MCP status | `claude mcp get bombot` |
| Models on the box | `mcp__bombot__list_ollama_models` |

## Status

v0.2 — bridge route checked on 05/10/2026 on this machine: checker passes tailscale, `bombot`
connected, bridge health, `gpt-oss:20b` pulled (and fails when asked for a missing model); one
`ask_ollama` call with `model: "gpt-oss:20b"` through the bridge returned `OK`. The installed
`~/.claude/agents/local-llm.md` on this machine is still the old one (checker reports DRIFT until
the user approves replacing it). Not verified: the `local-llm` subagent itself running end to end
through `mcp__bombot__*`, a fresh machine, Windows.
