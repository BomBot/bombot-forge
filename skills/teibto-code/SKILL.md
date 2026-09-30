---
name: teibto-code
description: >-
  DEPRECATED since plugin 0.17.0 — it delegated code drafts to the removed `teibto-worker`
  subagent. Do not use; delegate code edits to `teibto-agent` (see setup-coding-agent), which edits
  an isolated worktree and leaves review and apply to the caller.
---

# /teibto-code — DEPRECATED

**Skill version: `202609_03`**

`teibto-code` sent a one-shot drafting request to the `teibto-worker` subagent and verified the text
that came back. That subagent was **removed in 0.17.0**; do not call `bombot-forge:teibto-worker`.

Use **`teibto-agent`** instead: it runs the machine's coding-agent CLI (OpenCode or Cline) on the
company DeepSeek key against an isolated git worktree and returns a patch. **The verification rules
carry over unchanged** — the caller reads every changed line, runs the acceptance test itself, and
only then applies; a cheap model's "tests pass" is a claim, not evidence. Setup, the protocol and the
limits are in the `setup-coding-agent` skill.

Two measurements worth keeping from this skill's benchmark (docs/benchmarks/2026-09-25-suitelet-5-models.md):
the cheap models' drafts still contained errors a reviewer had to catch, and delegation only pays off
when the output is big enough to amortise the orchestration overhead.

The old flow is in git history (`git log -- skills/teibto-code`) if it needs to come back.
