# bombot-forge

BomBot's personal Claude Code plugin — NetSuite delivery skills, forged from real TEIBTO
MFG work (customer SDF deploys, a costing-variance analysis, live verification, a production
fan-out fix).

## Starter set for new members

Paste [docs/onboarding/new-member-starter.md](docs/onboarding/new-member-starter.md) into Claude Code on the new
machine (dev or non-dev). It installs this plugin, then runs **`setup-init`**, which checks everything as one checklist and
walks through the missing pieces in the order below. Every install is asked first, logins are the person's own, and
nothing is written to NetSuite.

## Setup skills — run once per machine

Run each in Claude Code as `/bombot-forge:<name>` (for example `/bombot-forge:setup-browser`). They walk you
through it step by step and test what they set up. **Order** (numbered = must have; `setup-init` runs 1–4 for you):

0. `setup-init` — the checklist and the walk-through (new machine, or "what is missing here?")
1. `setup-cli` Part A — git + GitHub CLI, signed in
2. `setup-global-instructions` — asks dev or non-dev, then merges `~/.claude/CLAUDE.md`
3. `setup-browser` — bsk, Claude in Chrome, Dev Bridge
4. `setup-plugins` — the team's other plugins
5. `setup-cli` Part B — SuiteCloud CLI + SDF project + auth id (devs; re-run later with "ตั้ง SDF ต่อ")

Optional: `setup-coding-agent`, `setup-local-llm`. `setup-browser` and `setup-global-instructions` are written to update
on a re-run instead of overwriting (they back up / merge / ask per key).

| Setup skill | Use when | Writes on this machine |
|---|---|---|
| **0. setup-init** | a new machine, or checking what one is missing: detects Windows/macOS, suggests Bypass (or Auto) permission mode, checks every piece as one checklist with what each is for, asks dev or non-dev, then runs the setup skills below in order and ends with what a new session needs to know | nothing itself (each skill it runs asks first); `~/.claude/onboarding-sdf-todo.md` if SDF is left for later |
| **1./5. setup-cli** | the command-line preset: Part A git + GitHub CLI (install, web login, Teibto repos visible) for everyone; Part B for devs: SuiteCloud CLI, clone a Teibto repo or create an SDF project in the current folder, auth id in the team format (`<ACCOUNT>-Adm-Prod` / `<ACCOUNT>_SB1-Adm-Sand`), read-only `file:list` test. Interactive logins run in the user's own terminal | git/gh/Node/SuiteCloud CLI installs; git identity; `project.json` `defaultAuthId` |
| **2. setup-global-instructions** | setting up or syncing a machine's global `~/.claude/CLAUDE.md`, for a **dev or a non-dev** (one question; OS detected) — builds the text from a bundled redacted snapshot (dev as is; non-dev adds the no-SDF ban, the UI scope A/B/C done through Claude in Chrome one confirmed change at a time, and a narrow JS hotfix lane), then merges section by section and asks only where they conflict (never blind-overwrite); only name and work email are asked; non-dev also gets `permissions.deny` rules for `suitecloud` (a fence, measured: a name built from a variable slips past). `setup-global-instructions-nondev` is now a pointer here | `~/.claude/CLAUDE.md` (merged, backed up first); non-dev also `~/.claude/settings.json` → `permissions.deny` (only after you confirm) |
| **3. setup-browser** | first-time or changed browser setup on a machine — install `bsk` (what it is for, in plain words), optional Claude in Chrome, offers to remove an old cdp setup (Chrome for Testing) if found, Dev Bridge trial (what it is, when it helps, and the Home page URL asked right before the ping), login-click consent (never reads the password); optionally keeps the `bsk` daemon running from login (Windows: Task Scheduler + a hidden `wscript`/.vbs launcher, observed working on one machine; runbook in `references/windows-daemon-hidden.md`); saves a local no-secrets prefs file | `~/.config/bombot-forge/browser.json` (engine choice, Dev Bridge endpoint, login-click consent; no secrets); installs `bsk` |
| **setup-coding-agent** | making Cline (or OpenCode) the worker for code/text edits on the company DeepSeek key — detect, point at the TEIBTO endpoint, privacy check, smoke test, worktree-isolated `agent_run.py`, and the review-then-apply protocol (Claude briefs and reviews; browser/production/deploy/secrets never delegated). Also read-only profiles on OpenCode: `analyze` (DeepSeek hunts a bug in existing code, Claude verifies the cited lines) and `ns-reader` (NetSuite lookups). A delegation log records tokens and your accept/fix/reject verdicts so the setup can be measured. Prepared for Windows, never run there | the company key in `~/.config/teibto/api.env`; `~/.config/bombot-forge/agent.json` (agent + model) only if you opt in to delegating edits; `~/.config/bombot-forge/delegations.jsonl` (numbers and ids only, no task text or code); per-project delegation level (always / medium / low / on-request, optional blocking hook, a per-conversation `!self` switch); deletes the OpenCode session each run creates (`--keep-session` to keep, `--purge-sessions` for old ones); points OpenCode/Cline at the TEIBTO DeepSeek endpoint |
| **4. setup-plugins** | installing the team's other plugins from GitHub, **by group with what each is for**: ก. Teibto team toolkit (must have; private repo, needs `setup-cli` Part A) · ข. working discipline (superpowers, mattpocock-skills, andrej-karpathy-skills, ponytail on trial; plus codegraph, a per-repo code-graph MCP set up by hand) · ค. UI design and web debugging (impeccable, ui-ux-pro-max, chrome-devtools-mcp) · ง. plugins that come with the claude.ai account (checked, never installed). Preset per role: dev = ก+ข, non-dev = ก; extras picked by the user; `marketplace add` + `install` at user scope; skips copies already present (e.g. `@synced`); copies nothing, never logs in | plugins you pick from `plugins.json`, installed from GitHub |
| **setup-local-llm** | setting up / checking the default `local-llm` worker (free, private — Ollama on `bombot-pc` over Tailscale, reached through the `bombot` bridge because Ollama listens on localhost only) — installs the agent from the canonical copy, PASS/FAIL checker (bridge, model, agent), re-snapshot flow | the `bombot` bridge and the `local-llm` agent, registered on this machine |

Nothing secret is stored in this repo: keys and prefs live in `~/.config/...` on each machine.

## Work skills

Used while delivering NetSuite work. Claude picks them from their descriptions; you can also name them.

| Skill | Use when |
|---|---|
| **ns-sdf-prod-deploy** | deploying SDF changes to a live/prod account; import-compare before deploy; per-round prod deploy (temp-authid trap, scoped deploy, smoke-test) |
| **ns-live-verify** | reading/verifying live NetSuite state read-only via the TEIBTO Dev Bridge (`ping` / `query` / `record` / `lookup` / `feature` / `search`; accounts, GL, fields, script deployment; driven through `bsk` by default, `cdp.py` as the alternative) — confirm real state, don't assume |
| **ns-record-write** | writing a field to a live record from a logged-in browser session on a **dev** machine (`bsk` only — cdp removed in 0.47.0; sandbox or production — on production after a dry-run and the round's confirmation; no flag needed; transport failure mid-write = outcome unknown, exit 3) — scoped `submitFields` / load-save helper (structured args, account guard, dry-run), the `permissions.allow` line, and a per-machine setup validator |
| **ns-bundle-to-sdf-repo** | turning an account-owned NetSuite bundle into a version-controlled SDF repo — "Convert to SDF Project" flow, cleaning up legacy auto-generated scriptids via Change ID, and the path-fidelity rules that keep a future deploy landing on the bundle's real live location |
| **browser-engines** | the per-run browser rules: **`bsk`** first (own session + pinned tab, bsk 0.4 cooperate sync, dialog guard, NetSuite identity gate, expired-session login click, bounded `observe`, production UI changes after the round's confirmation), then Claude in Chrome, then the user; **how the Dev Bridge works** (how a call travels, actions, where the address comes from, `ns_read.py`, failure modes); a **first-run walkthrough** that `setup-browser` runs at its end. The old cdp lane is history only: [docs/history/cdp-lane.md](docs/history/cdp-lane.md) |
| **video-transcribe** | transcribing a video/audio file to SRT/TXT/MD via the homelab `bombot` MCP (Tailscale bridge to the `bombot-pc` GPU box with ffmpeg + faster-whisper) — prereq check, Taildrop in + size verify, one `transcribe_video` call (the client times out on long files but the job keeps running — never call twice), Taildrop back, and why the `.md` is a summary, not a transcript |
| **verified-decision-brief** | turning an informal requirement into a stakeholder decision doc grounded in verified as-is (code + live), incl. redaction for sharing |
| **capture-artifact** | after a deploy (`/bombot-forge:capture-artifact`, manual only, needs `bsk`): confirm a capture plan, then red-boxed live screenshots with "was -> now" captions (before -> after sheets, or a numbered current-state pack when no "before" exists). `--local` keeps the pack in the project under `.captures/`, out of git on this machine (`.git/info/exclude`); the default copies it to a new Drive subfolder with a README, adds an overview flow diagram and a wide gallery to the decision-log artifact, and drafts the Slack summary in chat when there is a thread — never sent without the user's OK |
| **slack-daily-recap** | end of the day (`/bombot-forge:slack-daily-recap`, read-only): who tagged or wrote to you in Slack today, every thread read to the end, sorted into unanswered / answered-but-open / FYI with due dates worth a reminder; needs the Slack connector (stops with how to connect it if missing); never sends, reacts or schedules, and leaves credentials and key-bearing links out |
| **github-code-flow** | changing code in a GitHub repo (`/bombot-forge:github-code-flow`, slash command only): issue first, branch, compare with the live target, upload only after OK, PR then wait for the user to merge, port to sandbox; per-repo values in a per-machine config inside `.git` (asked once, re-checked every run), optional auto-use per repo through `CLAUDE.local.md` |

### Using github-code-flow

- Type `/bombot-forge:github-code-flow` in a session opened in the repo, optionally with an issue number or a Slack link.
- First run on a machine: it detects what it can (git author, base branch, `project.json`, `suitecloud account:manageauth --list`) and asks only the rest. The answers go to `.git/bombot-forge/github-flow.json`, inside `.git`, so they are never committed and every worktree shares them.
- Later runs re-check those values (branch and auth ids still exist) and stop if one is gone.
- It can add one line to that repo's `CLAUDE.local.md` (kept out of git) so every session there follows the flow without the slash command. To turn it off, delete the line.
- Uploads to a live account wait for your OK each round; after the PR it stops and waits for you to merge.

## Deprecated

Kept as short redirect stubs so an old reference doesn't dead-end; the old text is in git history.

| Skill | Status |
|---|---|

## Benchmarks

| Date | What | Result |
|---|---|---|
| 2026-09-25 | [Suitelet template → 2-step SuiteQL Suitelet, 5 models, blind-graded](docs/benchmarks/2026-09-25-suitelet-5-models.md) | Opus 5.5 15/16 ($0.17) · Sonnet 5 13 · Opus 4.8 12 ($0.31) · teibto-worker 3 ($0.01) · local-llm 1 (free) |
| 2026-09-26 | [Same task, 4 more local models vs pinned gpt-oss:20b](docs/benchmarks/2026-09-26-local-models.md) | qwen3-coder:30b 1 · glm-4.7-flash 1 · qwen3:30b-a3b 1 · deepseek-coder-v2:16b 0 — keep gpt-oss:20b pinned |

## Onboarding prompts

Prompts a maintainer hands to another developer's Claude (not skills; nothing is invoked automatically).

| Prompt | Use when |
|---|---|
| [new-member-starter.md](docs/onboarding/new-member-starter.md) | a new team member (dev or non-dev): installs this plugin, then runs `setup-init` (see "Starter set for new members" above) |
| [windows-dev-bsk-devbridge.md](docs/onboarding/windows-dev-bsk-devbridge.md) | a Windows developer has no Claude-to-browser link yet: set up `bsk` (daemon at log on, hidden), learn every Dev Bridge action, then a hands-on lesson converting a Saved Search to SuiteQL with proof the results match. Maintainer notes and evidence level: [windows-dev-bsk-devbridge.notes.md](docs/onboarding/windows-dev-bsk-devbridge.notes.md) |

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
- [ ] For `github-code-flow` (discipline rules + per-machine config): first real run on an SDF repo and a
      `plain` repo, config re-check after an auth id is renamed, step 0c line on Windows
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
