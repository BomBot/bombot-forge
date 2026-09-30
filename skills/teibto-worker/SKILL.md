---
name: teibto-worker
description: >-
  DEPRECATED since plugin 0.17.0 — the `teibto-worker` subagent this skill called was removed and
  replaced by `teibto-agent`. Do not use; for edits use setup-coding-agent / teibto-agent, for the
  private default use local-llm.
---

# /teibto-worker — DEPRECATED

**Skill version: `202609_04`**

The `teibto-worker` subagent (a haiku forwarder to DeepSeek) was **removed in 0.17.0**. Do not call
`subagent_type: "bombot-forge:teibto-worker"` — it no longer exists.

| You wanted | Use now |
|---|---|
| An edit to files in a git repo, done on the company DeepSeek key | the **`teibto-agent`** subagent (skill `setup-coding-agent` sets it up) |
| A read of a NetSuite sandbox by a cheap model | `agent_run.py --profile ns-reader` (`setup-coding-agent`) |
| Bulk text work (summarise, translate) that must stay private | `local-llm` (Ollama, free) |
| One-off DeepSeek text call from a shell | `python3 <plugin>/skills/setup-coding-agent/scripts/ask_cheap.py` (kept; key setup in `setup-coding-agent`) |

The old flow is in git history (`git log -- skills/teibto-worker`) if it needs to come back.
