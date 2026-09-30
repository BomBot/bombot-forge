---
name: setup-teibto-worker
description: >-
  DEPRECATED since plugin 0.18.0 — its key step, the `ask_cheap.py` helper and the price table moved
  into the `setup-coding-agent` skill. Do not use; use setup-coding-agent.
---

# Setup Teibto Worker — DEPRECATED

**Skill version: `202609_08`**

Everything this skill did now lives in **`setup-coding-agent`** (section "The company key and the
one-shot helper"): saving `TEIBTO_API_KEY` to `~/.config/teibto/api.env`, the `ask_cheap.py` helper and
its smoke test, the token/USD price table (`prices.json`, also read by `agent_run.py`), and the gotchas
(python.org macOS certificate store, 401, exit code 2).

| Old | New location |
|---|---|
| `skills/setup-teibto-worker/scripts/ask_cheap.py` | `skills/setup-coding-agent/scripts/ask_cheap.py` |
| `skills/setup-teibto-worker/scripts/prices.json` | `skills/setup-coding-agent/scripts/prices.json` |
| Save the key / smoke test | `setup-coding-agent` → "The company key and the one-shot helper" |

The key file path (`~/.config/teibto/api.env`) did not change, so a machine that already saved its key
needs nothing. The old text is in git history (`git log -- skills/setup-teibto-worker`).
