---
name: teibto-code
description: >-
  Use when delegating a coding task to teibto-worker (DeepSeek on the TEIBTO endpoint) — the
  user types /teibto-code <task>, or asks teibto-worker to write or draft code. Decides whether
  delegating is worth it, runs the data check, attaches the repo's worker brief if it has one,
  delegates, then verifies every result line by line before the calling Claude applies it.
---

# /teibto-code — delegate code to teibto-worker, verify before applying

**Skill version: `202609_02`**

The worker (DeepSeek) has **no repo context** and **invents platform identifiers** (field/table/
record ids, API methods, config keys). It only saves tokens when the output is long. The calling
Claude stays responsible for correctness: the worker drafts, Claude verifies and applies.
For plain text work (summaries, translation) use `/teibto-worker` instead.

## 1. Is it worth delegating?

- **Delegate:** long, mechanical output — UI HTML/CSS/JS, boilerplate, several similar or repeated
  helpers, query drafts, test scaffolding.
- **Do it yourself:** a single short function, impact analysis, multi-file business logic,
  anything that needs live system state, deploys, spec decisions.
- **Why:** the worker costs ~20k tokens of its own overhead. Measured 2026-09-25 on one function:
  teibto-worker = 23.7k haiku + 3.4k DeepSeek (≈ $0.004, 28 s); an Opus general-purpose subagent =
  63.5k tokens (5 s); both answers correct. So it wins on cost only when the output is big enough
  to amortise the overhead, and it's slower.
- If the user **didn't name the worker explicitly**, say this in one line and do the task directly.
  If they did, delegate.

## 2. Data check (before sending anything)

| Content | Rule |
|---|---|
| The repo's own code, internal docs | OK — state it in the prompt |
| Customer data: query results from any customer/live account, Slack threads, customer sheets, customer names / values | **Ask the user first, every time.** No standing approval. |
| Secrets, passwords, tokens, API keys | Never. Stop. |

Strip customer values out of code excerpts (sample data, hard-coded ids from a customer system),
or ask.

## 3. Build the prompt

Self-contained — the worker sees only what you send. Write it to the scratchpad and have the
worker pass the file to its helper (large code doesn't survive being retyped):

1. The data-OK statement from step 2.
2. **The project brief**, if the repo has `docs/ai/teibto-worker-brief.md`: send only the part
   **above** its "For the caller" line (the rest is for you). No brief → state the language/API
   version, indent style, and the project's hard rules (forbidden APIs, limits) inline.
3. The task: what to build, inputs/outputs, edge cases.
4. The real code it must fit into — the function(s) being replaced plus enough surrounding code to
   show the file's style — with real file paths.
5. **Every platform identifier it needs**, copied from the repo, so it doesn't guess.
6. The required output format, verbatim:
   ```
   ### Code
   <one fenced block per changed function or file section — complete functions, not fragments>

   ### Where it goes
   <file path + which existing function/line it replaces or follows>

   ### Assumptions
   <bullets: any id / behaviour assumed; "none" if none>
   ```

Delegate with the Agent tool, `subagent_type: "bombot-forge:teibto-worker"`, telling it this is a
coding task (return the sections verbatim, don't split the prompt).

## 4. Verify — every result, no exceptions

1. **Read it line by line** against the spec and the **real file** (re-read the file — don't trust
   the excerpt you sent).
2. **Every identifier / table / API** it used: confirm in the repo or the live system. Resolve
   everything under **Assumptions** and every `TODO` before applying.
3. **Platform limits and forbidden APIs** listed in the brief (or the project's CLAUDE.md).
4. **Style + scope:** matches the file (indent, API version, naming); touches only what the task
   asked; the change header is present if the brief/project requires one.
5. **Apply it yourself** with the Edit tool (the worker never writes files), then a syntax check
   for the language (`node --check`, `python3 -m py_compile`, …), then the project's normal
   test / upload flow.

## 5. Report

Briefly:
- what was delegated,
- what you **changed or rejected** from the worker's output, and why,
- the worker's usage footer verbatim (`via teibto-worker: [ask_cheap …]`).

If fixing the output cost more than writing it would have, say so — that's the signal to stop
delegating that kind of task.

## Gotchas (measured)

- **Benchmark (2026-09-25, same Suitelet task, blind-graded /16):** Opus 5.5 15 · Sonnet 5 13 ·
  Opus 4.8 12 · teibto-worker 3 · local-llm 1. Both cheap workers produced code that fails at
  runtime on NetSuite-API-heavy logic (invalid `LIMIT`, invented APIs). Keep them for long mechanical
  output, and verify line by line. Full write-up: `docs/benchmarks/2026-09-25-suitelet-5-models.md`.

- **Reasoning tokens dominate the DeepSeek bill.** A 2-function draft (2026-09-25): 208 in / 6,272
  out, of which **5,942 were reasoning** (95%) → ≈ $0.0076. Output length ≠ cost; the thinking is.
- **The TODO rule works — and is exactly why step 4 exists.** Given an identifier it wasn't told
  (a project regex), it wrote `LOT_NO_PATTERN.test(s) /* TODO: confirm id */` and listed it under
  Assumptions instead of inventing a pattern. The draft references an undefined name — applying it
  unverified would ship a `ReferenceError`.
- **Format compliance:** all three sections came back as required on the test run; still check —
  a missing `### Assumptions` means you don't know what it guessed.

## Project briefs

A repo opts in by adding `docs/ai/teibto-worker-brief.md`: the model-facing part first (context,
coding rules, platform ids policy, limits, the output format above), then a line starting
**"For the caller"**, then caller-only notes. Keep project-specific rules (platform limits,
change-header format, forbidden APIs) there — not in this skill.

## Status

v0.1 — generalised from a project-level prototype in a NetSuite repo (2026-09-25). Not yet
pressure-tested per `superpowers:writing-skills`.
