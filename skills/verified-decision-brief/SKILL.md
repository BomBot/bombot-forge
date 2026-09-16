---
name: verified-decision-brief
description: >-
  Use when turning an informal or ambiguous requirement (chat, comment, BRD, handoff) into a
  decision document for stakeholders, when the current (as-is) behaviour must be proven against
  real code and live data before proposing changes, or when producing an analysis brief another
  person or AI will act on.
---

# Verified Decision Brief

**Skill version: `202609_01`**

Turn a fuzzy requirement into a spec/decision doc where **every "as-is" claim is verified
against real code + live state, not assumed**. The intake-to-spec core of the TEIBTO dev role:
be the bridge between non-coders and the backlog, and never hand someone an assumption dressed
as a fact.

## The method

1. **Verify as-is first — from source, not memory.**
   - Read the actual code path (entry → the branch that really runs), not a summary.
   - Confirm on the live account with `ns-live-verify` (GL postings, field values, deployment state).
   - When two sources disagree (doc vs code vs comment), the live system breaks the tie.
   - Label each fact: verified-from-code / live-verified / from-doc(unverified).
2. **Frame the decision, not just the question.** For each open point give options + a
   recommendation with the trade-off, so the reader can decide (or hand it to an expert).
3. **Make numbers legible to a non-accountant AND checkable by an expert** — a worked example
   with real account numbers + a formula, plus one line stating the non-obvious insight
   (e.g. "the net totals are identical both ways — the only difference is X").
4. **Tag who answers each point** — 🟢 you decide / 🟡 dev can verify / 🔴 needs a domain expert.
   Mark decided items so the doc shows progress, not just a wall of questions.

## Output shape

- Sections: **problem → as-is (verified) → requirement source → mechanism example →
  questions (each: options, GL/worked example, recommendation, who-answers, status) → status summary**.
- Self-contained: the recipient (person or their AI) can act **without opening the source docs**.
  Embed the relevant source content; don't rely on links they may not be able to open.
- Provide **both HTML (to read) and Markdown (for another AI to ingest)** when it will be
  fed to a model. Put analysis docs under `reviews/<issue>/`.

## Sharing: redact before it leaves the team

Before sending outside the immediate team, scan for and handle:
- **Cross-client references** — another customer's name / that you did their implementation.
  Redact; it's rarely needed for the analysis anyway.
- **Internal staff names** — generalize to role for external recipients; fine to keep for internal.
- **Private DM links** — the recipient can't open them and they expose who's in the DM; embed
  the (redacted) content instead of pasting the raw link.
- **Customer chart-of-accounts / confidential BRD** — share only with people authorized on that
  account; ask if unsure.

Decide internal vs external audience explicitly — it changes what to redact. When the recipient
turns out to be internal (and even the domain expert on the "other" account), un-redact what is
now relevant and useful to them.

## Guardrails

- **Do not present an inferred as-is as verified.** If you only read the doc, say so, and go
  verify before the brief ships. "Material variance stays in WIP (code inference)" and "…(live
  GL confirmed)" are different claims — never let the first wear the clothes of the second.
- **A sandbox full of test data is not clean evidence** — trace one real transaction/record
  rather than trusting an account-level aggregate polluted by test rows.
- Recommendations are the dev's proposal; the domain expert still decides the 🔴 items.

## Status

v0.1 draft — extracted from a costing-variance analysis (5 briefs, HTML+MD, verified from
Cost Allocation code + live GL). Technique skill; test that an agent can apply the method to a
fresh requirement per superpowers:writing-skills.
