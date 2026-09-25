# Benchmark: 5 models complete a SuiteScript 2.1 Suitelet template (2026-09-25)

One coding task, same prompt, one shot each, graded blind. The purpose is to decide which worker
to use for which kind of work. Referenced by the `teibto-code` skill.

## Result

| Rank | Model | Score /16 | Tokens in / out (reasoning) | Cost (USD) | Time |
|---|---|---|---|---|---|
| 1 | Opus 5.5 (`claude-opus-5-5`) | **15** | 3,574 / 7,099 (2,087) | 0.171 | 62 s |
| 2 | Sonnet 5 (`claude-sonnet-5`) | 13 | 3,640 / 13,251 (8,655) | 0.147 | 117 s |
| 3 | Opus 4.8 (`claude-opus-4-8`) | 12 | 3,578 / 11,095 (6,482) | 0.313 | 124 s |
| 4 | teibto-worker (`deepseek/deepseek-flash`) | 3 | 1,869 / 16,829 (14,365) | 0.010 (off-peak) | 63 s |
| 5 | local-llm (`gpt-oss:20b` on Ollama) | 1 | 1,823 / 9,356 | 0 | 238 s |

Reasoning tokens are included in the output count. Claude costs are what the CLI reports at API
rates. On a subscription plan they are not billed per call. Input counts differ mostly by tokenizer:
the prompt is the same 7.2 KB file for all five, and the Claude baseline context was about 770 tokens.

## Takeaways

1. **Only the three Claude models produced code that would run.** Both cheap models produced code
   that fails at runtime on NetSuite.
2. **Opus 5.5 beat Opus 4.8 on every axis in this run.** It scored higher, used 36% fewer output
   tokens, cost about half as much, and was twice as fast.
3. **The cheapest call is not the cheapest result.** teibto-worker cost $0.01, but its draft needs
   Claude to find and fix a broken query and unsafe parameters. That fix likely costs more than the
   $0.16 saved. This matches the `teibto-code` rule: delegate long, mechanical output, not
   platform-API-heavy logic.
4. **Reasoning volume did not track quality.** DeepSeek spent 85% of its output on reasoning and
   still produced invalid SQL. Opus 5.5 reasoned the least and scored the highest.
5. **Surface checks don't separate models.** All five passed `node --check`, returned the three
   required sections, used only `libCode.stopWatch`, filled every placeholder and updated the
   `@change` header. The differences only showed in a line-by-line review against the real API.

## Task

The input was BomBot's own generic Suitelet 2.1 template (146 lines, no customer data). It uses a
global-`var` module pattern, a `MODULE` array, `DisplayType`/`LayoutType`/`BreakType` constants,
logging through an external `libCode.stopWatch`, a `stepfield` step switch, `__________`
placeholders and a `@change` header. The template itself is not included here.

The prompt asked for a two-step Suitelet:
- **Step 1:** Date From and Date To (DATE, mandatory) plus a Remark field.
- **Step 2:** use SuiteQL (`N/query`) to fetch Sales Orders in that date range. Show them in a LIST
  sublist with Document Number, Date, Customer display name and Total, capped at 500 rows. Echo the
  inputs as read-only fields and add a working Back button.
- **Rules:** keep the template style exactly; call only `libCode.stopWatch`; never invent
  NetSuite ids (use `/* TODO: confirm id */` and list them under Assumptions); respect the
  Suitelet limit of 1,000 units with no searches in loops; update the `@change` header; write
  comments in English.
- **Output:** the `### Code` / `### Where it goes` / `### Assumptions` format that `teibto-code`
  requires.

## Method

- **Same prompt, one shot, no repo access, no tools** for every model.
- **Claude models** ran with `claude -p --model <id> --output-format json --tools ""
  --strict-mcp-config --disable-slash-commands --no-session-persistence --setting-sources ""
  --system-prompt "You are a coding assistant."`, with the prompt on stdin.
  `--setting-sources ""` matters: without it, user settings and CLAUDE.md added about 10k hidden
  input tokens. It is also why `--bare` wasn't used: that mode requires API-key auth.
- **teibto-worker** was called through `ask_cheap.py` directly, so the ~20k-token haiku
  forwarder overhead is not included.
- **local-llm** was called through Ollama `/api/chat` directly. Token counts are
  `prompt_eval_count` and `eval_count`.
- **Grading was blind.** Outputs were shuffled to A–E and a separate Opus grader scored them
  without seeing the mapping. Decisive claims were then spot-checked against the code before the
  mapping was revealed.
- **The code was not run on NetSuite.** That was the user's choice. "Fails at runtime" means
  reviewed against the real API.

### Rubric (0–2 each, max 16)

1. SuiteQL validity: table `transaction`, `type = 'SalesOrd'`, `tranid`, `trandate`,
   `BUILTIN.DF(entity)`, `foreigntotal`.
2. Date handling: parse with `format.parse`, then bind safely with `TO_DATE`.
3. 500-row cap in SQL: `FETCH FIRST` or a `ROWNUM` subquery.
4. Sublist population: correct API, and no null or `''` values passed to `setSublistValue`,
   because NetSuite throws on them.
5. Step flow and Back button: the step switch works and Back leads to a real URL.
6. Template fidelity and scope: `N/query` in the same position in `MODULE`, the `define` params and
   the assignments.
7. Robustness: validation, error handling, empty-result message, governance.
8. Honest Assumptions.

## Per-model notes

- **Opus 5.5 (15).** The query is correct: `BUILTIN.DF`, `foreigntotal` flagged with a TODO,
  `format.parse` to ISO and then `TO_DATE`, and `ROWNUM <= 500` in a correct subquery. It guards
  every sublist value against null or empty. Back uses `url.resolveScript` with the runtime script
  and deployment ids. It is missing a From ≤ To check, try/catch and an empty-result message.
- **Sonnet 5 (13).** Structure is as good as Opus 5.5, and it uses `FETCH FIRST 500 ROWS ONLY`. It
  sets `value: row.x || ''` in `setSublistValue`, which throws on real data with a null customer or
  total. It uses `t.total`, but flags it honestly. There is no guard when step 2 is opened without
  dates.
- **Opus 4.8 (12).** The query and dates are correct and the sublist is null-safe. But it fetches
  every row and caps with `Math.min(..., 500)`, Back is `history.back()`, which fails when step 2 is
  opened directly, and its TODO sits on the display date instead of the uncertain column.
- **teibto-worker (3).** The query fails: it uses `LIMIT 500`, which SuiteQL does not support, and
  passes JS `Date` objects as `runSuiteQL` params with no `TO_DATE`. It uses the doubtful
  `transaction.amount` with no TODO and has no null guards. Back is a second submit button. It
  dropped the original `@change` history line.
- **local-llm (1).** It calls APIs that don't exist: `addSublistField`, `setSublistValue` with
  `sublistId`/`fieldId` keys, `getScriptId()` and `getDeploymentId()`, and the column
  `c.internalid`. It builds SQL by string concatenation, reads `.results[i].tranid` instead of
  `.values`, and references a field group it never created.

**Shared gaps:** none of the five validated From ≤ To, used try/catch, or showed an explicit
"no results" message.

## Caveats

- One run per model, so run-to-run variance is unmeasured. Ranks 2 and 3 are one point apart.
- The grader was an Opus model. Grading was blind, but a same-family style preference can't be
  ruled out.
- This is one task type: platform-API-heavy logic. Long mechanical output such as HTML/CSS
  boilerplate may favour the cheap workers more.
- teibto-worker cost is at off-peak rate. It would be about double at peak.

## Re-running

Build a new prompt file, then run each model the same way, one shot each (method above). Shuffle
the outputs and grade them blind with this rubric. Record the results as a new dated file in this
folder rather than editing this one.
