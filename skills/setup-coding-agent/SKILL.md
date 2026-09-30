---
name: setup-coding-agent
description: >-
  Use when setting up or using a coding agent CLI (Cline or OpenCode, whichever the machine
  has) as the worker for ALL code/text edits, with Claude only briefing it and reviewing the
  result — for example to spend the company's DeepSeek tokens instead of Claude's. Covers
  detecting which CLI exists, pointing it at the TEIBTO DeepSeek endpoint, the privacy settings to
  check, a smoke test, the worktree-isolated run helper `agent_run.py`, and the review-then-apply
  protocol. Not for browser, production, deploy, or secret-handling work — those stay with Claude.
---

# Setup Coding Agent (Cline / OpenCode as the worker, Claude as reviewer)

**Skill version: `202609_02`**

Claude writes a brief and reviews; the agent edits files in an **isolated git worktree**; nothing
reaches your repo until Claude has read the diff and applied it. Tokens burn on the company
DeepSeek key, not Claude's. This is the agentic sibling of `teibto-worker` / `teibto-code`
(those are one-shot text calls with no file access; this one reads, edits and runs commands).

## What was verified, and on what

| Claim | Status |
|---|---|
| Cline CLI `3.0.66` headless: `cline -P <provider> -m <model> --json --worktree -t <sec> -c <repo> "<prompt>"` | verified on a Mac |
| Cline's `openai-compatible` provider pointed at the TEIBTO endpoint with `deepseek/deepseek-flash` | verified (already configured on this machine) |
| `--worktree` makes a detached worktree under `~/.cline/worktrees/<id>/<repo>`; the source repo stays untouched | verified |
| `--json` ends with a `run_result` row: finish reason, iterations, tokens, model | verified |
| `agent_run.py` end to end on a scratch repo: bug fixed, patch reviewed, applied, test passes, worktree removed | verified — 2 runs, ~5–10 s, est. ≈ US$0.005 each |
| OpenCode `2.0.20`: `opencode run --standalone --format json -m <provider>/<model> "<prompt>"` run inside a worktree that `agent_run.py` creates | verified on a Mac: 3 runs on a scratch repo; bug fixed, patch reviewed and applied, test passes, source repo untouched; ≈ US$0.004 and ~11 s per run |
| OpenCode reads `$PWD`, not the process cwd | **verified the hard way**: with only `cwd=` set, the agent worked in the CALLER's directory and found no files. `agent_run.py` now sets `PWD` too |
| OpenCode reads stdin when it is not a terminal | verified: an inherited open pipe made a run hang until the timeout; `agent_run.py` gives it `/dev/null` |
| Cline hooks (`--hooks-dir`) as a real guard against dangerous commands | **not tested** |

## Iron rules

- **Cline's default is auto-approve ON** (`--auto-approve true`): the agent can run shell commands
  and edit files without asking. The worktree isolates **edits to the repo**, not the machine.
  The guardrail preamble in `agent_run.py` is advice to the model, **not enforcement**. So: never
  give it a task that involves secrets, production, or customer data without the user's explicit OK
  (it goes to an external provider), and never point it at a repo you can't afford to have it
  read.
- **Never apply without reading every changed line.** `agent_run.py` saves `changes.patch` and
  stops. Claude reads the diff, runs the tests itself, then applies. A cheap model's "tests pass"
  is a claim, not evidence.
- **These stay with Claude and are never delegated:** anything in a browser (bsk/cdp), any
  production action, SDF deploys, Slack/email, secrets and credentials, and every decision the
  global `CLAUDE.md` says needs an OK.
- **Nobody types the API key into chat or a command line.** The user enters it in their own
  terminal (or it is already configured — check with the smoke test, don't read the key file).
- **Don't guess another CLI's flags.** For OpenCode (or anything else), read its `--help` first and
  say what you could not verify.

## Setup

**Step 0 — detect (read-only).** `command -v cline opencode`, versions, and whether
`~/.cline/data/settings/providers.json` has a provider for the TEIBTO endpoint (look at provider
names and the base URL only — **never print `apiKey` values**). If both CLIs exist, ask which to
use; if neither, offer to help install Cline (`cline --help` afterwards) and stop until the user
has done it.

**OpenCode path (`--agent opencode`).** Nothing to install on a machine that has it; its provider is
whatever `~/.config/opencode/opencode.jsonc` defines — look for a provider whose `baseURL` is the
TEIBTO endpoint and pass `--model <that-provider-id>/deepseek/deepseek-flash` (model ids contain a
`/`). Without `--model` the helper uses OpenCode's own default model, which may not be the company
key — say which one ran. `opencode run` has no worktree flag, so **the helper creates the worktree
itself** (`git worktree add --detach`). OpenCode's JSON has no `run_result` row: the helper sums the
`step_finish` tokens and calls a run "completed" when it exited 0 and ended with a text reply.
**Check the config's `permission` value:** on the machine used to test it was `"allow"` (every tool
auto-approved, shell included) — the same exposure as Cline's default. Show the user; don't change it
without their OK. If a machine's config does NOT allow tools, a headless run can't answer prompts:
pass `--opencode-auto` knowingly. A running OpenCode desktop app keeps a background service — the
helper uses `--standalone` (a private server), so it doesn't touch the user's sessions.

**Step 1 — point it at the company key's endpoint.** Endpoint
`https://tokenhub-intl.tencentcloudmaas.com/v1`, model `deepseek/deepseek-flash` (same as
`setup-teibto-worker`). If Cline has no such provider, the user runs, in their own terminal:
`cline auth -p openai-compatible -b https://tokenhub-intl.tencentcloudmaas.com/v1 -m deepseek/deepseek-flash`
and enters the key when asked (Cline keeps its own copy in `~/.cline/data/settings/`; the
per-machine source of truth stays `~/.config/teibto/api.env`).

**Step 2 — privacy check; ask before changing anything.** On the machine this was written on,
`~/.cline/data/settings/global-settings.json` had `telemetryOptOut: false` and the `web_search`
tool enabled. Show the user both values and explain: telemetry sends usage data to the vendor, and
web search sends query text out. Recommend opting out of telemetry and disabling `web_search` for
any customer-related repo. Back the file up, show the diff, edit only after their OK.

**Step 3 — smoke test.** Scratch repo, nothing real:

```bash
T=$(mktemp -d) && cd "$T" && git init -q && git config user.email t@t && git config user.name t \
 && printf 'def add(a, b):\n    return a - b\n' > calc.py \
 && printf 'from calc import add\nassert add(2, 3) == 5\n' > test_calc.py \
 && git add -A && git commit -q -m init \
 && echo 'calc.py has a bug: add() subtracts. Fix it so `python3 test_calc.py` passes. Touch only calc.py.' > brief.md
python3 <skill-dir>/scripts/agent_run.py --repo "$T" --task-file brief.md --timeout 180
```

Expect `finish: completed`, a one-line patch in `calc.py`, and a token/USD line. Then apply
(`git apply <run dir>/changes.patch`), run `python3 test_calc.py`, and remove the worktree with
the last command the helper printed.

**Step 4 — make it the default (opt-in).** Ask: *"Delegate all code/text edits to the agent, with
me only briefing and reviewing?"* If yes, record `{"default_delegate": true, "agent": "cline"}` in
`~/.config/bombot-forge/agent.json` (no secrets), and **offer** to add a short rule to the global
`~/.claude/CLAUDE.md` (back up, show the diff, wait for OK):

> Code/text edits go to the coding agent via `agent_run.py` (skill `setup-coding-agent`); Claude
> briefs and reviews. Never delegate browser, production, deploy, secrets or customer data.

## The protocol Claude follows (when `default_delegate` is on)

1. **Decide.** Is it an edit/authoring task inside one git repo with no secrets and no production
   effect? If not, do it yourself. Customer data present → ask the user first.
2. **Commit or stash** the repo (the worktree only has committed files — the helper refuses a dirty tree).
3. **Write the brief** to a file: goal, exact files, acceptance test (a command that must pass),
   what not to touch, the repo's conventions (style, headers). One task per run.
4. **Run** `agent_run.py --repo . --task-file brief.md`. Report tokens and the USD estimate.
5. **Review** `git -C <worktree> diff --cached` line by line against the brief; run the tests and
   lint yourself in the worktree or after applying. Anything off → fix it yourself, or re-brief
   with the specific defect (don't just re-run).
6. **Apply** with `git apply`, **commit per the repo's rules**, then **remove the worktree**.
7. **Say what it cost and what you changed from the agent's output.**

## Gotchas

- The patch leaves out `__pycache__`, `*.pyc`, `.DS_Store`, `node_modules` (the agent's test runs
  create them); everything else it created or changed is in `changes.patch`.
- The agent's own "files changed" list uses worktree paths; trust `git status`, not its prose.
- The run folder (`~/.cache/bombot-forge/agent-runs/<time>/`) keeps `out.jsonl` (the full event
  log, may contain file contents) and `task.md` — delete it when the work is customer-related.
- Cline auto-updates itself (`autoUpdateEnabled`); re-run the smoke test after an update.
- `--worktree` needs a git repo; detached HEAD, so nothing is committed on a branch.
- If auto mode blocks a step while doing this, stop and offer the three choices in
  `setup-browser` → "If auto mode blocks a step".

## Status

v0.1 draft — Cline and OpenCode paths each verified on one Mac with scratch-repo runs. No enforcement layer beyond the worktree; hooks are a possible next step. Not yet run
on a real customer repo.
