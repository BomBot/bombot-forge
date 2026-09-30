# bombot-forge

BomBot's personal Claude Code plugin — NetSuite delivery skills, forged from real TEIBTO
MFG work (customer SDF deploys, a costing-variance analysis, live verification, a production
fan-out fix).

## Setup skills — run once per machine

Run each in Claude Code as `/bombot-forge:<name>` (for example `/bombot-forge:setup-browser`). They walk you
through it step by step and test what they set up. There is no hard dependency between them; a
sensible order is the one below. `setup-browser` and `setup-global-instructions` are written to update
on a re-run instead of overwriting (they back up / merge / ask per key).

| Setup skill | Use when | Writes on this machine |
|---|---|---|
| **setup-global-instructions** | setting up or syncing a machine's global `~/.claude/CLAUDE.md` to the canonical NetSuite-dev instructions — compares a bundled redacted snapshot against the machine's file and proposes a section-by-section merge (never blind-overwrite); real customer/email/path values filled per-machine | `~/.claude/CLAUDE.md` — compared with the bundled redacted snapshot, merged section by section, backed up first |
| **setup-browser** | first-time or changed browser setup on a machine — choose `bsk` or `cdp` with trade-offs, install, optional Claude in Chrome, Dev Bridge trial, login-click consent (never reads the password); optionally keeps the `bsk` daemon running from login (Windows Task Scheduler, reported working, example untested); saves a local no-secrets prefs file | `~/.config/bombot-forge/browser.json` (engine choice, Dev Bridge endpoint, login-click consent; no secrets); installs `bsk` or Chrome for Testing |
| **setup-coding-agent** | making Cline (or OpenCode) the worker for code/text edits on the company DeepSeek key — detect, point at the TEIBTO endpoint, privacy check, smoke test, worktree-isolated `agent_run.py`, and the review-then-apply protocol (Claude briefs and reviews; browser/production/deploy/secrets never delegated). Also read-only profiles on OpenCode: `analyze` (DeepSeek hunts a bug in existing code, Claude verifies the cited lines) and `ns-reader` (NetSuite lookups). A delegation log records tokens and your accept/fix/reject verdicts so the setup can be measured. Prepared for Windows, never run there | the company key in `~/.config/teibto/api.env`; `~/.config/bombot-forge/agent.json` (agent + model) only if you opt in to delegating edits; `~/.config/bombot-forge/delegations.jsonl` (numbers and ids only, no task text or code); points OpenCode/Cline at the TEIBTO DeepSeek endpoint |
| **setup-plugins** | installing the team's Claude Code plugins from their GitHub source on a new machine — shows what is already present (including copies under another marketplace, e.g. `@synced`), you pick which to install, then `marketplace add` + `install` at user scope; copies nothing, never logs in | plugins you pick from `plugins.json` (teibto-netsuite-toolkit, superpowers, impeccable, mattpocock-skills, andrej-karpathy-skills, ui-ux-pro-max), installed from GitHub |
| **setup-local-llm** | setting up / checking the default `local-llm` worker (free, private — Ollama on `bombot-gaming` over Tailscale via the `ollama` MCP) — installs the MCP script + agent from canonical copies, registers the MCP, PASS/FAIL checker, re-snapshot flow | the `ollama` MCP and the `local-llm` agent, registered on this machine |

Nothing secret is stored in this repo: keys and prefs live in `~/.config/...` on each machine.

## Work skills

Used while delivering NetSuite work. Claude picks them from their descriptions; you can also name them.

| Skill | Use when |
|---|---|
| **ns-sdf-prod-deploy** | deploying SDF changes to a live/prod account; import-compare before deploy; per-round prod deploy (temp-authid trap, scoped deploy, smoke-test) |
| **ns-live-verify** | reading/verifying live NetSuite state read-only via the TEIBTO Dev Bridge (`ping` / `query` / `record` / `lookup` / `feature` / `search`; accounts, GL, fields, script deployment; driven through `bsk` by default, `cdp.py` as the alternative) — confirm real state, don't assume |
| **ns-record-write** | writing a field to a live record from a logged-in browser session (`bsk` on sandbox, or on production only with an explicit `--allow-bsk-prod`; `cdp` anywhere; transport failure mid-write = outcome unknown, exit 3) — scoped `submitFields` / load-save helper (structured args, account guard, dry-run), the `permissions.allow` line, and a per-machine setup validator |
| **ns-bundle-to-sdf-repo** | turning an account-owned NetSuite bundle into a version-controlled SDF repo — "Convert to SDF Project" flow, cleaning up legacy auto-generated scriptids via Change ID, and the path-fidelity rules that keep a future deploy landing on the bundle's real live location |
| **browser-engines** | which browser engine to use: **`bsk` (BrowserSkill) for read/QA** — measured ~18 ms vs ~409 ms per command, verified recipes (own session + pinned tab, dialog guard, NetSuite identity gate, bounded `observe`) — and **cdp (`cdp.py`, Chrome for Testing on a fixed profile) for writes, dialogs and `lens`/`netlog`/`stub`/`diff`**; includes the shared-browser coordinator rules; cdp for read/QA is **soft-deprecated** (kept as fallback when `bsk` is unusable on a machine) |
| **video-transcribe** | transcribing a video/audio file to SRT/TXT/MD via the homelab `bombot` MCP (Tailscale bridge to a Windows GPU box with ffmpeg + faster-whisper) — prereq check, scp-to-inbox + size verify, the sync `transcribe_video` wait, scp-results-back, and the SSH job-object gotcha |
| **verified-decision-brief** | turning an informal requirement into a stakeholder decision doc grounded in verified as-is (code + live), incl. redaction for sharing |

## Deprecated

Kept as short redirect stubs so an old reference doesn't dead-end; the old text is in git history.

| Skill | Status |
|---|---|
| **teibto-code** | *(deprecated in 0.17.0)* replaced by the `teibto-agent` subagent — see `setup-coding-agent`; the verify-before-apply rule carries over |
| **teibto-worker** | *(deprecated in 0.17.0)* the subagent it called was removed; use `teibto-agent` (edits), `local-llm` (private text) or `ask_cheap.py` |
| **setup-teibto-worker** | *(deprecated in 0.18.0)* moved into `setup-coding-agent`: saving `TEIBTO_API_KEY` at a hidden prompt, the `ask_cheap.py` helper and the token/USD price table |
| **cdp-browser** | *(renamed in 0.22.0)* now **`browser-engines`** — the skill covers `bsk` first and `cdp`; the old name is a redirect stub |

## Benchmarks

| Date | What | Result |
|---|---|---|
| 2026-09-25 | [Suitelet template → 2-step SuiteQL Suitelet, 5 models, blind-graded](docs/benchmarks/2026-09-25-suitelet-5-models.md) | Opus 5.5 15/16 ($0.17) · Sonnet 5 13 · Opus 4.8 12 ($0.31) · teibto-worker 3 ($0.01) · local-llm 1 (free) |
| 2026-09-26 | [Same task, 4 more local models vs pinned gpt-oss:20b](docs/benchmarks/2026-09-26-local-models.md) | qwen3-coder:30b 1 · glm-4.7-flash 1 · qwen3:30b-a3b 1 · deepseek-coder-v2:16b 0 — keep gpt-oss:20b pinned |

## Agents

Subagents shipped in `agents/` (auto-installed with the plugin):

| Agent | Use when |
|---|---|
| **teibto-agent** | handing ONE well-scoped edit in a git repo to the machine's coding-agent CLI (OpenCode/Cline on the company DeepSeek key) via `agent_run.py` — edits an isolated worktree, returns a patch marked NOT REVIEWED; Claude reviews and applies. Also runs `--profile analyze` for a read-only bug hunt (a report, no patch). Not for browser, production, deploy, secrets or customer data (haiku runner; needs `setup-coding-agent` first) |

The `local-llm` agent is not shipped here: `setup-local-llm` installs it (with its `ollama` MCP) on each machine.

## Structure

```
bombot-forge/
  .claude-plugin/plugin.json     # plugin manifest
  skills/<name>/SKILL.md         # one folder per skill
  skills/setup-plugins/plugins.json   # the GitHub-sourced plugin list that skill installs from
  agents/<name>.md               # plugin subagents
  README.md
```

Add-per-skill support files (`references/`, `scripts/`) go inside each skill folder when a
section grows past ~100 lines or a reusable script emerges.

## Status: v0.1 drafts — NOT yet TDD-tested

These skills are first drafts distilled from one session's real work. Per
`superpowers:writing-skills`, a skill isn't done until it's been pressure-tested:

- [ ] Run baseline subagent scenarios WITHOUT each skill; capture rationalizations/gaps
- [ ] Verify agents comply/apply correctly WITH the skill
- [ ] For `ns-sdf-prod-deploy` (has discipline rules): close loopholes, add rationalization table
- [ ] For `ns-live-verify` (reference): test retrieval — can an agent find + apply the right recipe
- [ ] For `ns-record-write` (has discipline rules + script): verify dry-run-first + account-guard
      compliance; confirm `validate-setup.sh` passes on all 3 machines
- [ ] For `verified-decision-brief` (technique): test application to a fresh requirement
- [ ] For `ns-bundle-to-sdf-repo` (has discipline rules): only one conversion so far — needs
      a second bundle conversion to confirm the Change ID `isvalid`-flag workaround and the
      "no plain branch-push trigger" CI gotcha generalize, not one-off
- [ ] Decide final layout for your setup (`skills/` plugin format here vs `.claude/skills/`
      + `.agents/skills/` mirror used by teibto-dev-standards)

## Public-repo hygiene

**Status: public since 2026-09-16.**

- [x] Drop customer-identifying labels/repo names from every skill and replace with generic
      wording (no customer name is spelled out anywhere in this repo, including past-tense
      changelog entries describing what was redacted — restating the redacted value in the
      "here's what we removed" note defeats the redaction, so don't)
- [x] Keep only a generic `<ACCOUNT_ID>` / `<SCRIPT_ID>` template row in `ns-live-verify`;
      real per-account rows live only in `notes.private.md` (gitignored, not in this repo).
      TEIBTO's own SB2 (`4089685`) stays inline since it's not customer data
- [x] Generalize internal ticket references and fix labels to neutral descriptions
- [x] Drop the plugin manifest's personal contact email — a GitHub profile link is enough
      attribution for a public repo
- [x] Squash git history — commits that had a real customer name / account id in their tree
      are gone from `origin/master`; current history starts clean
- [x] Flip visibility to public
- [x] Verified against the **live public repo** via `gh api repos/BomBot/bombot-forge/...`
      (not just a local grep) — a local-only check missed the changelog re-exposure above and
      the leftover contact email on the first pass

This repo has no SDF project of its own (no `project.json`/`manifest.xml`), so a permission-
tuning pass here should skip gating `suitecloud` subcommands — they don't apply and add no
protection.

**Enforced automatically:** `.github/workflows/redaction-check.yml` greps every push/PR of
tracked `.md`/`.py`/`.json`/`.sh` files for three things and fails CI on a match: (1) a
known-redacted customer name, (2) a NetSuite `script=`/`compid=` id not on an allowlist —
caught by param, so a short 3-4 digit script id doesn't slip past a digit-count filter, (3)
any bare 7-8 digit account-shaped number not on the allowlist. This replaces relying on
remembering to run a check by hand before adding new skill content.

## Provenance

Distilled 2026-09-15 from the TEIBTO-MFG-Manufacturing session covering: Handheld batch
deploy to a customer account, a costing-variance analysis (2-ท่อน, Summary Variance),
per-issue git migration, and UE undeploy+verify.
