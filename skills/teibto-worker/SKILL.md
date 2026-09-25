---
name: teibto-worker
description: >-
  Use when the user types /teibto-worker <task>, or asks to send a task to teibto-worker
  (DeepSeek on the TEIBTO cloud endpoint). Hands the task to the `teibto-worker` subagent and
  relays its answer plus the verbatim token/cost line. For private data the default is the local
  `local-llm` (Ollama) instead.
---

# /teibto-worker — send a task to DeepSeek (TEIBTO endpoint)

**Skill version: `202609_02`**

A shortcut for delegating one task to the `teibto-worker` subagent, which forwards it to
DeepSeek on the TEIBTO endpoint and reports tokens + an estimated USD cost. Setup lives in
`setup-teibto-worker`; this skill is only the "run a task" entry point.
**Writing or drafting code?** Use `/teibto-code` instead — it adds the worth-it check, the
project brief, and line-by-line verification before anything is applied.

## Which worker

| | `local-llm` (default) | `teibto-worker` |
|---|---|---|
| Runs on | this machine (Ollama) | Tencent Cloud (DeepSeek) |
| Cost | free | paid per token |
| Data | stays local | leaves to an external provider |

Invoking `/teibto-worker` explicitly means "use teibto-worker". Don't silently swap to
`local-llm` — but if the task clearly contains customer data, stop and offer `local-llm` instead.

## Flow

1. **Get the task** from the arguments. None given → ask what to send, and stop.
2. **Data check before sending:**
   - Secrets / passwords / tokens / API keys → never send. Say so and stop.
   - Customer data (names, account ids, records, confidential BRD content) → don't send unless the
     user explicitly OKs it in this conversation; offer `local-llm` as the private option.
   - Public or own non-sensitive content (e.g. this repo's files) → fine; say so in the prompt.
3. **Delegate** with the Agent tool, `subagent_type: "bombot-forge:teibto-worker"`, a
   self-contained prompt: the task, the output format/language, file paths (let the worker pass
   the file to the helper rather than pasting large text), and the data-OK statement from step 2.
4. **Relay** the worker's answer, then its footer **verbatim** (the `[ask_cheap …]` line(s)).
5. **Spot-check the answer** before presenting it — the cheap model makes category/label errors
   (seen: listing a skill under "Agents"). Fix obvious mistakes and say what you corrected.

## Gotchas

- **Tiny inputs aren't cheaper.** The subagent's own Claude overhead (~20k tokens) dwarfs
  DeepSeek's cost on a short file; it pays off on long inputs (transcripts, logs, multi-page docs).
  Still run it when invoked by name — just mention it if the input was tiny.
- **Key missing (exit 2)** → point the user to `setup-teibto-worker`; don't handle the key.
- **Slash name.** Plugin skills are namespaced: `/bombot-forge:teibto-worker` always works; the
  short `/teibto-worker` works when no other skill has the same name.

## Status

v0.1 draft — wraps the verified `teibto-worker` agent. Not yet pressure-tested per
`superpowers:writing-skills`.
