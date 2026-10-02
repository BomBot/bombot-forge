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

**Skill version: `202609_20`**

Claude writes a brief and reviews; the agent edits files in an **isolated git worktree**; nothing
reaches your repo until Claude has read the diff and applied it. Tokens burn on the company
DeepSeek key, not Claude's. It replaces the removed `teibto-worker` / `teibto-code` (0.17.0): those were one-shot text calls with no
file access; this one reads, edits and runs commands — and is what the **`teibto-agent`** subagent drives.

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
  give it a task that involves secrets — ever — or production/customer data unless the user OK'd it (for the `ns-reader` profile the OK is the per-account confirmation below)
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

## How to ask the user (at every decision point in this skill)

A choice is never buried in a paragraph. Do these, in this order:

1. **Bullets first.** One block per option, at most three short lines each: **Pros · Cons · Best when**.
   No paragraphs, no "it depends" prose. Say which option you recommend and why in one line.
2. **Then a picker — the last thing in your message.** Use the `AskUserQuestion` tool: a short label, a
   one-line description that carries the key trade-off, the recommended option first and marked
   "(Recommended)". At most 4 options per question, one decision per question, at most 4 questions per
   call (split further decisions into the next round). Use multi-select only when the choices are not
   exclusive. The user can always type their own answer via "Other".
3. **No picker available?** (the tool is not offered, or the run is unattended) Ask the same thing as a
   numbered list in chat, and wait. Never pick for the user and never treat silence as consent.
4. Don't ask what Step 0 already showed, and don't re-ask something already answered.

Decision points here: which CLI when both exist (**OpenCode** / **Cline**), the privacy settings
(**Opt out of telemetry and disable web_search (Recommended for customer repos)** / **Leave as is**), and Step 4
(**Delegate edits to the agent** / **Not yet**).

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
`https://tokenhub-intl.tencentcloudmaas.com/v1`, model `deepseek/deepseek-flash` (the same endpoint and
model the key section below uses). If Cline has no such provider, the user runs, in their own terminal:
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

**Step 4 — record the agent and model.** (`default_delegate` in this file is **superseded since 0.28.0**: how much to hand over is now chosen **per project**, see "Delegation level (per project)"; leave it out or ignore it.) Record `{"agent": "opencode", "model": "<provider-id>/deepseek/deepseek-flash"}`
(use the agent and the model name exactly as that CLI's own config spells them; for Cline `model` may be
omitted) in `~/.config/bombot-forge/agent.json` (no secrets). `agent_run.py` and the `teibto-agent`
subagent read `agent` and `model` from this file, so they need no flags, and **offer** to add a short rule to the global
`~/.claude/CLAUDE.md` (back up, show the diff, wait for OK):

> Code/text edits go to the coding agent via `agent_run.py` (skill `setup-coding-agent`); Claude
> briefs and reviews. Never delegate browser, production, deploy, secrets or customer data.

## The company key and the one-shot helper (moved here from `setup-teibto-worker` in 0.18.0)

The DeepSeek key of the TEIBTO endpoint lives in **`~/.config/teibto/api.env`** (`TEIBTO_API_KEY=…`,
chmod 600) — the per-machine source of truth. OpenCode/Cline keep their own copy in their own config
(you enter it once through their `auth` command); this file is what `ask_cheap.py` reads and what you
re-enter from if a CLI loses its copy.

- Endpoint `https://tokenhub-intl.tencentcloudmaas.com/v1` (OpenAI-compatible), default model
  `deepseek/deepseek-flash`.
- **Iron rules:** the key never goes in a repo, a prompt, a command line, or chat. The user types/pastes
  it themselves (in an editor, or at a hidden prompt) and nobody reads it back — check it is filled by
  **length only**. Never turn off TLS verification to "fix" an SSL error (see the first gotcha). This
  repo is public; its redaction CI blocks `sk-…`-shaped keys as a backstop. Customer data sent through
  any of this leaves to an external provider — only with the user's explicit OK.

**Save the key (per machine).** Default: open the key file in the user's editor. It creates an empty
template only if the file is missing, locks it to 600 and opens it; it never reads or writes a key:

```bash
F=~/.config/teibto/api.env; mkdir -p ~/.config/teibto
[ -s "$F" ] || printf 'TEIBTO_API_KEY=\n' > "$F"; chmod 600 "$F"
open -a "Sublime Text" "$F" 2>/dev/null || open -e "$F"   # fallback: TextEdit
```

Tell the user to paste the key right after `TEIBTO_API_KEY=` (no quotes/spaces), save, and say "saved".
Check without reading the value: `sed -n 's/^TEIBTO_API_KEY=//p' ~/.config/teibto/api.env | tr -d '\n' | wc -c` (> 0).
Terminal alternative (hidden prompt; the user runs it — it cannot run inside Claude's Bash):

```bash
bash -c 'mkdir -p ~/.config/teibto && read -rsp "TEIBTO_API_KEY: " k && printf "TEIBTO_API_KEY=%s\n" "$k" > ~/.config/teibto/api.env && chmod 600 ~/.config/teibto/api.env && echo && echo saved'
```

**`scripts/ask_cheap.py`** sends ONE prompt to that endpoint and prints the reply (stdlib only; the key
goes only in the HTTP header). Smoke test — expect `pong` and a usage line, exit 0:

```bash
S=$(ls ~/.claude/plugins/cache/bombot-forge/bombot-forge/*/skills/setup-coding-agent/scripts/ask_cheap.py | sort -V | tail -1)
python3 "$S" <<<'Reply with exactly: pong'
```

Env switches: `TEIBTO_MODEL`, `TEIBTO_BASE_URL`, `TEIBTO_TIMEOUT`, `TEIBTO_ENV_FILE`. Exit codes: 0 ok · 1
request/HTTP error · 2 no key found (it prints the setup command).

**Token usage + cost.** Every `ask_cheap.py` call prints a usage line on stderr from the response's
`usage` field: `[ask_cheap model: … | tokens in=N out=N total=N (cached=N, reasoning=N incl. in out) | cost≈$X peak|off-peak]`.
Prices live in **`scripts/prices.json`** (USD per 1M tokens at peak, keyed by the model id the response
returns) and `agent_run.py` reads the same file for its `est. USD` line. A model with no price shows
`cost=n/a` — never fill it from a blog or aggregator figure. `deepseek/deepseek-flash` uses DeepSeek's
official V4.1-Flash rates (peak in $0.30 / cached $0.006 / out $1.20; off-peak half, outside 01–04 and
06–10 UTC Mon–Fri); TEIBTO/TokenHub billing may differ, so the figure is an estimate. Formula:
`((in − cached)·input + cached·cached_input + out·output) / 1e6`. Per-machine flat override:
`TEIBTO_PRICE_IN` / `TEIBTO_PRICE_OUT` / `TEIBTO_PRICE_CACHED`. `python3 scripts/test_agent_run_offline.py`
checks the table is found and valid.

Gotchas (hit for real):
- **`SSL: CERTIFICATE_VERIFY_FAILED` on macOS** — Python from python.org ships an empty CA store until
  "Install Certificates.command" is run. The helper falls back to `certifi`, then `/etc/ssl/cert.pem`, so it
  still verifies. `curl` is not affected (system store) — a quick way to tell cert store from endpoint.
- **HTTP 401 "API Key does not exist"** — key file missing/typo'd or the key was revoked; save it again.
- **Helper not found** — the glob above is empty when the plugin isn't installed or is older than 0.18.0:
  run `claude plugin marketplace update bombot-forge && claude plugin update bombot-forge@bombot-forge`.

## The subagent `teibto-agent`

Ships in `agents/teibto-agent.md`. Ask for it by name ("ให้ teibto-agent …") or let Claude pick it when
the project's delegation level calls for it. It is a thin haiku runner: it checks the repo is clean, runs `agent_run.py` once,
and returns the helper's output verbatim plus the `changes.patch` path, marked **NOT REVIEWED**. It never
applies, commits or edits the repo — Claude (the caller) does the review and the apply per the protocol
below. It refuses to run without `agent.json` (it never guesses a provider or model). **Not yet exercised
through the Agent tool** — the file was written and the command path it uses was run by hand; a subagent
is only loaded at session start, so the first real call needs a fresh session after the plugin update.

## Profile `ns-reader` — let the agent READ NetSuite (sandbox, plus accounts the user confirmed), nothing else (OpenCode only)

`agent_run.py --profile ns-reader --task-file ask.md --model <provider>/<model>` runs the agent in an
EMPTY scratch folder (no repo, no patch) with a permission list that **OpenCode itself enforces**:
the only shell commands allowed are `ns_read.py whoami|ping|query|record|lookup|feature|search` (from `ns-live-verify`); every
other command, all file edits, web fetch/search, and the flags `--allow-prod-read`, `--bridge-path`
and `--config` are denied. So it can read a SANDBOX account through the Dev Bridge and every account listed in
`agent.json` → `read_accounts` (see below), and can neither click, write, log in, nor run raw `bsk`/`cdp.py`. The Dev Bridge endpoint is the README's default script/deploy ids unless the local `browser.json` has
`dev_bridge.endpoints["<account>"].path`; the agent cannot pass its own (`--bridge-path` is denied).
A non-sandbox account NOT in that list stays out of the agent's reach (`agent_run.py` runs it with `BOMBOT_NS_READ_STRICT=1`, so `ns_read.py` refuses
it without `--allow-prod-read`, which the permission list only lets the agent pass for confirmed accounts). Claude's own reads need no flag or approval (since 0.30.0).

| Claim | Status |
|---|---|
| OpenCode's per-command `bash` permission (`allow`/`deny` globs, last match wins) is enforced | **verified**: `echo *` allowed, `ls` denied; `echo A && ls`, `echo B; ls` and `echo $(ls)` also denied |
| With the profile: `whoami` and `query` run, `--allow-prod-read`, `--bridge-path`, raw `bsk`, `ns_write.py` are denied | **verified live** on a sandbox (2 allowed, 4 denied) |
| `NS_READ_CONFIG` reaches the command the agent runs | verified (the query used the config's endpoint) |
| Listed non-sandbox account: `--allow-prod-read query --account <listed>` runs; an unlisted account, `--account <listed>x`, `--account <other> --allow-prod-read`, and a listed account with `--config` / `--bridge-path` are all denied | **verified live** with OpenCode's real matcher on the exact generated rules (a stub `ns_read.py` that only echoes; 2 allowed, 5 denied) |
| A later rule overrides an earlier one (last match wins) | **verified live**: an allow after a broader deny runs; the same allow before it is denied |
| Repeating `--account` (so a later one could replace the listed one) | `ns_read.py` refuses it (offline test); the permission glob alone would not |
| A read against a real non-sandbox account through the agent | **verified live** on a customer production account not yet live, after the user confirmed it: `whoami` and `ping` ran with the exact confirmed form; the same form on a different production account was refused by OpenCode; the same account without `--allow-prod-read` was refused by `ns_read.py`. Identity only — no record or query was read in that test |
| Env-prefixed commands (`VAR=x python3 …`) and other quoting tricks are denied | reasoned from the glob rule, **not tested** |
| OpenCode 2.0.20 also gives a headless run `execute` (Code Mode: `browser.*` / `opencode.*` tools), `subagent`, `skill`, `question`; with no rule for them they were available | **measured** (a model asked to list its tools; `execute` ran a `search()`). Since 0.22.8 all four are `deny` (**verified**: the tool list shrinks to `glob, grep, read, shell`). Until then `ns-reader` did **not** block them; whether `browser.*` could actually reach the web was **not tested** |
| `external_directory: deny` also stops the shell from touching other folders | **no — measured**: it covers read/glob/grep only; `git log > /outside/file` wrote a file outside the folder |
| A `>` redirect is checked against the bash list | **no — measured**: pipes, `&&`, `;`, `$(…)` are checked per command, `>` is not. Since 0.22.8 redirects whose target has `/`, `~`, `$` or `..` are denied (**verified live** with the real config: absolute, `>path`, `~/…` denied). A relative redirect (`> x.txt`) still works and only writes inside this run's empty scratch folder. Fail-closed side effect: a query containing both `>` and `/` is refused |
| Cline equivalent | none — the profile refuses `--agent cline` |
| `cdp` engine | not implemented in `ns_read.py` |

### Confirming a non-sandbox account (production not yet live, customer data)

The DeepSeek key of the TEIBTO endpoint is the user's trusted provider (their statement: enterprise terms,
no training on the data — **not verified by this skill**). Customer data read through the `ns-reader`
profile goes to that provider. So each non-sandbox account is opened **one at a time, by the user**:

1. A task needs account `A`, it is not a sandbox and not in `read_accounts` → **ask the user** (bullets
   then a picker, per *How to ask*): what leaves (query results and record data go to the model
   provider), what stays off (writes, clicks, login, every other account), that it is revocable.
   Options: **Yes, allow reading `A`** / **Not now**.
2. Only after a yes **in this conversation**, run — do not hand-edit the JSON:
   ```bash
   python3 "$S" --grant-read-account A --session-id "<id>" --session-name "<title>" --note "<what the user said>"
   ```
   `<id>` and `<title>` come from `get_session` with `"self"` when that tool is available (its `sessionId`
   and `title`), else the session folder in the scratchpad path. The entry stores the account, the local
   time and UTC time of the confirmation, the session id and name, and the note. It refuses without an id.
   The file is backed up, then written atomically (chmod 600).
3. From then on the agent may run exactly `python3 <reader> --allow-prod-read <sub> --account A ...`; do not ask
   again for `A`. A yes for `A` says nothing about any other account.
4. To take it back: `--revoke-read-account A`.


Before an `ns-reader` run, tell the user in one line that the agent will use `bsk` (a background Agent Window per
`ns_read.py` call, closed when it finishes; each call also prints a `[ns_read] using bsk …` notice). It is a notice, not a request for approval — send it and start the run.

Things to know: whatever the agent reads goes to the model provider; its summary is a claim, so
`agent_run.py` prints the list of commands it actually tried — compare them. The `--standalone`
server OpenCode starts watches the parent folders up to the home directory (its own log shows
`watcher` on `/Users/<you>`), and on macOS that produced permission prompts for iCloud Drive and
Music once. Answer **Don't Allow** — nothing here needs them. Whether config `watcher.ignore` avoids
it was **not tested**.

## Delegation level (per project)

How much edit work Claude hands to the agent is a **per-project, personal** setting, chosen when the user asks to set it
(e.g. "set the delegation level of this project"). Ask with the picker (bullets first, see the convention in
`setup-browser`), then run `delegation_level.py set --level <name> [--hook] --project <dir>` (add `--dry-run` first and show it).

| Level | Claude… | Enforced by |
|---|---|---|
| **always** | writes a brief and runs `agent_run.py` for every delegable edit; **does not edit project files itself**; only briefs, reviews, applies | the CLAUDE.local.md block, plus (optional) a hook that blocks Edit/Write |
| **medium** | hands over most well-scoped, testable edits; keeps the very small, ambiguous or design-heavy ones | text only |
| **low** | hands over only large repetitive jobs with a clear test | text only |
| **on-request** (**default**) | hands over only when the user says so ("send it to the agent") | text only |

- **What it writes (all personal, none committed):** `CLAUDE.local.md` (one marked block; the rest of the file is never
  touched, and it is backed up first), `.claude/bombot-forge.local.json` (the choice), and — only for `always` with the hook —
  `.claude/settings.local.json` (just our two hook entries; other settings and hooks are kept), a copy of the script as
  `.claude/bombot-forge-hook.py` (so a plugin update cannot break the hook path) and `.claude/bombot-forge-override.json`.
  They are added to `.git/info/exclude` (per clone) unless git already ignores them. `delegation_level.py show` / `remove`
  report and undo exactly this.
- **The hook (level `always`, opt-in):** a `PreToolUse` hook denies `Edit`/`Write`/`MultiEdit`/`NotebookEdit` on files inside the project and
  tells Claude to use `agent_run.py`. Not blocked: files outside the project and an allow list (`.claude/**`, `CLAUDE.md`,
  `CLAUDE.local.md`, `.gitignore`, `deploy.xml`, `manifest.xml`, `.env*`) — config and things that must never be delegated.
- **"This conversation, Claude does it" (the per-conversation switch):** the **user** types `!self` (or `ให้ claude ทำเองรอบนี้`)
  in a message; a second hook (`UserPromptSubmit`) reads *that* text and records the session id, so edits are allowed for that
  conversation only. `!agent` (or `กลับไปส่ง agent`) turns it off. Text Claude writes into a tool call cannot turn it on
  (tested). The words are in the local JSON and can be changed.
- **Verified:** with the real `claude` CLI — a blocked edit leaves the file unchanged and Claude is told why; `!self` in the same
  message lets the edit through; an allow-listed file edits normally; the block in `CLAUDE.local.md` is visible to Claude;
  `CLAUDE.local.md` is loaded; 31 offline tests with 8 mutations.
- **Not a wall:** Claude can still change files through `Bash` (that is also how `git apply` of a reviewed patch works), so
  `always` stops edits made by the editing tools, not a determined detour. A message the user *pastes* that contains `!self`
  counts as typed. The hook fails open (a broken hook never blocks Claude). Applies to Claude Code on this machine only; **not run on
  Windows** (the hook command quotes the interpreter path for a POSIX shell).
- **Not measured:** whether `always` actually saves tokens. Claude still writes a brief and reads the whole diff, so for a
  one-line change doing it directly is cheaper. `--log-report` shows the agent side; Claude's own tokens are not recorded.
- **Default and old setups:** a project with nothing set is **on-request** — nothing is handed over unprompted. This replaces the
  earlier machine-wide `default_delegate: true` behaviour (projects not yet configured no longer delegate by themselves).

## The protocol Claude follows (whenever it hands an edit to the agent)

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
8. **Record the verdict — every time, so the setup can be measured.** `agent_run.py` printed a `logged : run id …`
   line; close it with
   `agent_run.py --log-outcome <run id> --verdict accepted|fixed|rejected [--claude-fixed-lines N] [--note "<no customer data>"]`
   (accepted = used as-is · fixed = you corrected it · rejected = thrown away or redone; for `analyze`: findings
   confirmed / partly right / wrong). A run with no verdict is counted as unreviewed and tells us nothing about quality.

## Measuring it (the delegation log)

Every `agent_run.py` run (`code`, `analyze`, `ns-reader`) appends one line to `~/.config/bombot-forge/delegations.jsonl`
(mode 600 on macOS/Linux; override with `BOMBOT_FORGE_LOG`). It sits beside `agent.json` on purpose: not in `~/.claude/cache` — that is Claude Code's own cache and gets cleaned, while this must persist, and each `--log-outcome` appends a verdict line. It holds numbers and ids
only — profile, agent, model, tokens (in / cached / out), estimated USD, seconds, exit, how many commands the sandbox
refused, files and lines changed, task length — **never the task text, the agent's reply or any code**.
`agent_run.py --log-report [--since YYYY-MM-DD]` totals it per profile with the share of results used as-is.

What it can and cannot tell you: it proves the DeepSeek side (how much, how often it finished, how often Claude
accepted or had to fix the result). It does **not** record Claude's own tokens or what an all-Claude run would have
cost; for the saving, compare a period with and without delegation from the session usage by hand. **Not yet measured
on real work** — the log was exercised only on scratch repos.

## Investigating existing code (bug hunts, audits): DeepSeek finds, Claude checks

The delegation level covers edits. Investigation is two separate jobs, and they go to different places:

1. **Find it — DeepSeek, `--profile analyze` (OpenCode only).**
   `agent_run.py --profile analyze --repo . --task-file ask.md` gives the agent a throw-away worktree of HEAD
   (committed files only — no `.env`, no untracked scraps) and a permission list OpenCode enforces: it can read and
   search with its own read/glob/grep and run only `git log|show|blame|diff`. No edits, no other command, no web, no
   path outside the folder, no `execute`/`subagent`/`skill`/`question` tools, no `>`/`<`, no `--output`,
   `--ext-diff`, `--textconv`, `--no-index`, `--contents`; `.env`/`.pem`/`.key`/`*secret*`/`*credentials*` cannot be
   read. Output is a report (suspects with `file:line`, each claim marked SEEN or INFERRED), not a patch. The worktree
   is removed afterwards. **Verified live** (seeded off-by-one found at `calc.py:5`; forced attempts at `> file`
   inside and outside the folder, `git diff --no-index`, `git blame --contents`, and a pipe were all denied; `git log`
   and `git blame` ran). Code it reads goes to the model provider, as with edits.
2. **Check it — Claude, cheap model.** What DeepSeek returns is a claim. Verify the cited `file:line` yourself, and if
   the check itself is delegated to a subagent, **pass `model`** (an Agent call with none runs on the session's model —
   seen: six "Audit …" agents, 80–160k tokens each, all on Opus 5.5): `haiku` for lookups, `sonnet` for judgement.
   Keep Opus (or inherit) only for the final root-cause call the user will rely on.

Not measured: how often the DeepSeek report is right on a large real repo, and the cost saving over an all-Claude audit.

## Windows

`agent_run.py` was changed to run on Windows, but it has **never been run on Windows** — everything below is read from
the code paths and checked by offline tests that fake the OS-specific failure, nothing more.

- Handled: config, cache and ledger live under `%USERPROFILE%\.config` / `.cache` (same relative names as elsewhere);
  the interpreter in the allowed command is `python` (not `python3`); paths inside permission globs use forward slashes
  (a backslash is a glob escape); `ns_read.py` is **copied** when a symlink is not allowed; the agent CLI is launched by
  the full path `which` finds (npm installs `opencode.cmd`); JSON files are read/written as UTF-8; the console is
  switched to UTF-8 so a Thai reply cannot crash `print()` (mutation-checked with a cp1252 console); `teibto-agent` finds
  the helper with a small Python one-liner instead of `ls | sort -V`.
- Not handled / unknown: `chmod 600` does nothing on Windows (the file keeps your profile's permissions); which shell
  OpenCode uses for its `bash` tool there, and so whether its permission list treats `>`, `|`, `&&` the way it does on
  macOS; `bsk` and `cdp` launch steps in the browser skills are macOS-only (`open -a`, Chrome paths).
- Before trusting `analyze` or `ns-reader` on a new OS, **prove the enforcement there** — the permission list is the
  only barrier. Run the profile with a task that orders forced attempts and check nothing was written: e.g. for
  `analyze` in a scratch repo, `git log --oneline > rel.txt`, the same with an absolute path outside the folder,
  `git diff --no-index <any file> NUL`, and `git log | head -1`. Every one must come back `Permission denied` and no file
  may appear. If one runs, stop using that profile there and report it.

## Making the worker show its evidence

A bare "check your answer again" does little: a model can re-read its own reply and say "yes, correct" without opening
anything. So every prompt `agent_run.py` sends (`code`, `analyze`, `ns-reader`) carries the same demand — **every claim
needs a source** (file:line, command output, or the query run), a claim without one must say *not verified*, and the reply
ends with three lists (VERIFIED with its source / INFERRED / NOT LOOKED AT or NOT CHECKED). When you write a brief, keep that
shape in mind: ask for the acceptance-test output, not "it works". The wording lives in `VERIFY_CORE` in `agent_run.py`.

This makes the reply **easier to check, not correct**. It is still the agent's claim: open a sample of the cited
`file:line`, re-run the query or the test, and treat anything without a source as unverified. **Not measured:** whether the
wording raises the share of results accepted as-is — compare the `used as-is` rate in `--log-report` before and after
(runs from before 0.25.0 have the old wording).

## OpenCode sessions (each run leaves one; we delete it)

`opencode run` stores every run as a **session** in OpenCode's own database (`opencode debug paths` → `db`), with
the whole conversation — including code or data the agent read. `agent_run.py` never resumes one, so:

- **Default: a finished run deletes the session it created** (`--profile code`, `analyze`, `ns-reader`, OpenCode
  only). It takes the id from the `sessionID` in the run's own event stream and runs `opencode session delete <id>
  --standalone`, so nothing else can be touched (the id must look like `ses_…`). The line `session   : deleted …`
  is printed and `session_id` / `session_deleted` go into the delegation log. **`--keep-session`** skips it (for debugging).
- **Every session we start is titled `[agent_run] <run id> <profile>`** (`opencode run --title`): a marker that does not
  depend on the run folder, so a session that escaped deletion (timeout, failed delete) is still findable — by that title in
  OpenCode's UI and by `--purge-sessions`. The title carries no task text (without it OpenCode titles a session with a
  summary of the prompt). The ledger also records each run's `session_id`. Sessions from before 0.24.3 have no title and are
  found by their directory alone.
- The per-run folder `~/.cache/bombot-forge/agent-runs/<run>/` still holds `out.jsonl` (the full event log, which
  also contains what the agent read) — delete it yourself when the work is customer-related. Nothing prunes that folder yet.
- **Old sessions:** `agent_run.py --purge-sessions` lists the sessions whose directory is inside that agent-runs
  cache **or whose title starts with `[agent_run] `** (id + run name only; a string-prefix match, not a `LIKE`, so `_` in a path is not a wildcard).
  `--yes` deletes them. **Show the user the list and get an OK first.** Sessions from anywhere else are never listed.
- **Verified:** on OpenCode 2.0.20 a fresh session is created per run, and `session delete` removes the session and its
  message rows from the database (row counts checked before/after); a live `analyze` run left the session count unchanged.
  **Not verified:** a run that times out may have no session id in its output — then nothing is deleted and the line says so;
  Cline has its own task store, not handled here.

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
