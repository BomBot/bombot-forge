# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

`bombot-forge` is a **Claude Code plugin**: a collection of skills (`skills/<name>/SKILL.md`), not an
application. There is no build, lint, or test command — the "product" is the skill instructions
themselves, plus one helper script (`skills/ns-record-write/scripts/ns_write.py`) that skill invokes.
Changes here take effect the next time a Claude Code session loads this plugin's skills.

## Versioning (two independent version numbers — keep both in sync)

- **Plugin** = semver in `.claude-plugin/plugin.json` (`version` field) + git tag `vX.Y.Z`.
- **Each skill** = a `YYYYMM_##` string on the line under the H1 in its `SKILL.md`, and mirrored
  in `plugin.json`'s `description` field (`"ns-live-verify 202609_01"` etc.) — both must be updated
  together when a skill body changes.
- Commit message format when a skill changes: `type(skill): summary (SKILLVER / PLUGINVER)`
  e.g. `feat(ns-live-verify): add scriptdeployment recipe (202609_02 / 0.2.0)`.
- Record every change in `CHANGELOG.md` under a new version heading — this is the authoritative
  history of what each skill version contains (don't rely on git log alone).

## Repo structure

```
.claude-plugin/plugin.json   # plugin manifest: name, semver, author, description (mirrors skill versions)
skills/<name>/SKILL.md       # one folder per skill — frontmatter (name + description) drives when
                              # Claude auto-invokes it; body is the instructions given to the agent
skills/<name>/scripts/       # optional per-skill support scripts (ns-record-write, setup-teibto-worker, setup-local-llm)
agents/<name>.md             # plugin subagents, auto-installed with the plugin (teibto-worker)
README.md                    # skill index table + status checklist
docs/benchmarks/             # dated model comparisons (one file per run; don't edit old runs)
CHANGELOG.md                 # versioned history, see convention above
```

Add `references/` or `scripts/` inside a skill folder once a section grows past ~100 lines or a
reusable script emerges — don't split prematurely.

## Editing a skill

- `SKILL.md` frontmatter `description` is what makes Claude decide to invoke the skill — keep it
  specific to trigger conditions ("use when X"), not a summary of the content.
- These skills encode **discipline rules for irreversible/live-account actions** (SDF prod deploy,
  live NetSuite record writes). When editing `ns-sdf-prod-deploy` or `ns-record-write`, preserve the
  "Iron rules" sections' intent — they exist because a softer version already failed once in
  production. Don't loosen a guardrail without understanding why it's there (check `CHANGELOG.md`
  and git history for the incident it came from).
- `ns-live-verify` and `verified-decision-brief` are reference/technique skills (no destructive
  actions) — lower bar to extend, e.g. adding a new verified SuiteQL recipe or endpoint.

## ns-record-write's script (the one piece of real code)

`skills/ns-record-write/scripts/ns_write.py` is the canonical copy; consuming projects copy it to
their own `scripts/qa/ns_write.py` and commit it there (see that skill's Setup section). If you
change the canonical copy, the skill body's setup instructions assume projects will re-sync
manually — there's no automated distribution. `validate-setup.sh` in the same folder is a
per-machine checker (script drift, permissions allow-rule present, `cdp.py` present, QA Chrome
reachable on CDP port 9333) — run it after changing the write helper to confirm nothing silently
drifted from the canonical copy.

## Status

All four skills are v0.1/v0.2 drafts distilled from real TEIBTO NetSuite delivery sessions, not
yet pressure-tested per `superpowers:writing-skills` (baseline-without-skill vs with-skill subagent
runs). See `README.md`'s checklist before treating any "Iron rule" as battle-hardened.
