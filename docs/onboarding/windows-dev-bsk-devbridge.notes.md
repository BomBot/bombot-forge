# Notes for the maintainer: `windows-dev-bsk-devbridge.md`

The prompt file is written to be read by the other developer's Claude. These notes are for the maintainer and are not meant
to be handed to that Claude.

## How to use

Install the plugin on the developer's machine, then give them `windows-dev-bsk-devbridge.md` to pass to their Claude.

Assumptions baked into the prompt (edit the prompt if they are not true for the next person): Windows, Chrome already
logged in to NetSuite, role Administrator, Dev Bridge already deployed, production only so every step is read-only.

## Evidence level (2026-11-04)

- Steps 1-6 come from the plugin's own skills (`setup-browser`, `browser-engines`, `ns-live-verify`). Not verified:
  `ns_read.py` on Windows, a saved search through `--search-id`, any non-sandbox read (the skills say so themselves), and the
  Windows daemon recipe is from one machine.
- Step 7 comes from two places, both written by earlier Claude sessions and not re-run here:
  - Project memory notes of a manufacturing project: `reference-savedsearch-to-suiteql-conversion` (four layers of proof:
    semantic map, funnel, sandwich, canary; edge probes; measuring traps), `reference-215-recalcwip-suiteql-cutover`
    (the live search had a `ROUND`, the repo XML and the code comment did not), `dev-bridge-live-suiteql` (Records
    Catalog endpoint for field ids and joins).
  - The code of that conversion (a Map/Reduce function that replaced a saved-search full scan): the numbered filter
    comments, `ROUND`, `runSuiteQLPaged` with page size 1000, `IN` lists cut into chunks of 900, a separate `mainline = 'T'`
    existence query.
  The code agrees with the notes on the points that could be checked there (the `ROUND`, the paging, the chunking).
  Timing numbers differ between the two notes (and the code comment), so the prompt quotes none.

## Open points

- Records Catalog (7.3): the note says to use it, but nobody has re-run it for this prompt. The prompt tells Claude to try
  it and report.
- The Dev Bridge write Suitelet (`preview.old` of a saved-search definition) is mentioned in the project notes as a way to
  read the live definition. It is a different Suitelet from the read-only Dev Bridge and the other developer may not have
  it, so the prompt uses `search.load()` / `--search-id` / `object:import` instead.
- Measurement and canary advice (7.8, 7.9) are from one conversion. Treat them as advice, not rules.
- A question to the session that did the conversion was held by that session (different permission mode) and never
  delivered. The notes above answered most of it; ask that session directly if something is still unclear.
- A dedicated skill (`ns-search-to-query`) is still only planned. If it gets written, step 7 can shrink to "use that skill".

## Redaction

No real account ids, script ids or customer names belong in either file. Run the CI's redaction patterns before committing.
