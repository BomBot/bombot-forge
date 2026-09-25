# Benchmark: 4 more local models on the same Suitelet task (2026-09-26)

A follow-up to [2026-09-25-suitelet-5-models.md](2026-09-25-suitelet-5-models.md). It uses the
identical prompt file (sha256 prefix `7f7f2354d675`), the same 16-point rubric and blind grading.
The question: does any other model on the Ollama box beat the pinned `gpt-oss:20b` for `local-llm`?

## Result

| Rank | Model | Score /16 | Tokens in / out | Reasoning | Time |
|---|---|---|---|---|---|
| — | *anchor:* Opus 5.5 (yesterday's output, re-graded) | *15* | — | — | — |
| — | *anchor:* `gpt-oss:20b` (yesterday's output, re-graded) | *3* | — | — | — |
| 1 | `qwen3-coder:30b` (= `teibto-main`) | 1 | 1,770 / 2,252 | none | 73 s |
| 1 | `glm-4.7-flash` | 1 | 1,749 / 13,125 | 44k chars | 310 s |
| 1 | `qwen3:30b-a3b` | 1 | 1,772 / 10,748 | 37k chars | 264 s |
| 4 | `deepseek-coder-v2:16b` | 0 | 2,024 / 2,285 | none | 115 s |

All local runs cost $0. They ran one at a time on the single 12 GB GPU with `num_ctx` 32768 and
`keep_alive` 0, so each model unloaded before the next started. Every run ended with
`done_reason: stop`, so no output was truncated.

**The re-graded anchors show the grading scale held.** Opus 5.5 scored 15 again. `gpt-oss:20b`
scored 3 against 1 yesterday; ±2 at the bottom of the scale is grader noise.

## Takeaways

1. **None of the four beats `gpt-oss:20b`, so keep it pinned for `local-llm`.** All four scored
   0–1, and every one would throw at runtime.
2. **Thinking didn't help.** `glm-4.7-flash` and `qwen3:30b-a3b` reasoned for 4–5 minutes and still
   scored 1, the same as `qwen3-coder:30b`, which answered in 73 s with no reasoning.
3. **The same mistakes appeared across models.** None of these is a single-model bug:
   - 4 of 6 answers never loaded `N/query`, and two of those also shadowed `query` with the SQL
     string.
   - Every answer except Opus 5.5 used `LIMIT 500`, which SuiteQL rejects.
   - Most used a `salesorder` table or a header `total` instead of `transaction` / `foreigntotal`,
     and several joined on `customer.internalid` instead of `id`.
   - They put dates into the SQL as quoted strings instead of `TO_DATE` with bound params.
   - They invented `serverWidget` and `runtime` APIs, such as `addSublistField`,
     `serverWidget.DisplayType.READONLY`, `createList`, `getScriptId()` and `getRange`.
   - Most claimed "confirmed" or "none" under Assumptions for identifiers they had invented.
4. **Local models are for bulk text work, not NetSuite-API code.** This matches the `local-llm`
   agent's existing rule against code that must be correct. Across both runs, only the Claude
   models produced SuiteScript that would run.

## Notes on the custom models

`teibto-main` and `teibto-alt` share weights with other models on the box (compared by weight-blob
digest):
- `teibto-main` = `qwen3-coder:30b` with `num_ctx` 65536.
- `teibto-alt` = `gpt-oss:20b` with `num_ctx` 65536.

Neither was benchmarked separately; the weights are covered by the rows above. The 64k context
only matters for long inputs.

## Method

- Same `prompt.txt` as the 2026-09-25 run, called one shot through Ollama `/api/chat` with
  `stream: false`, `keep_alive: 0` and `options.num_ctx: 32768`, one model at a time.
- Any `<think>` blocks were stripped before grading. The reasoning size above is the length of
  Ollama's `message.thinking` field.
- Grading was blind across 6 entries: the 4 new outputs plus two anchors from the previous run,
  shuffled to A–F. A separate Opus grader scored them without the mapping. Decisive claims (invalid
  `LIMIT`, invented APIs, `internalid` joins) were spot-checked against the code before the mapping
  was revealed.
- The code was not run on NetSuite. "Throws at runtime" means reviewed against the real API.

## Caveats

- One run per model. The anchors show the grader's scale held, but not each model's run-to-run
  variance.
- This is one task type, platform-API-heavy code. Local models may still do well on the bulk text
  work `local-llm` is meant for.
