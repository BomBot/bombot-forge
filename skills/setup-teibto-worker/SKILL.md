---
name: setup-teibto-worker
description: >-
  Use when setting up, testing, or troubleshooting the `teibto-worker` subagent on a machine —
  the worker that delegates bulk low-judgement text work to a cheap external model (deepseek via
  the TEIBTO OpenAI-compatible endpoint). Covers saving `TEIBTO_API_KEY` once per machine without
  it touching a repo or shell history, the smoke test, switching model/endpoint by env var, and
  the python.org-macOS empty-CA-store gotcha.
---

# Setup Teibto Worker (deepseek via TEIBTO endpoint)

**Skill version: `202609_06`**

The `teibto-worker` subagent ships with this plugin (`agents/teibto-worker.md`), so every
machine that installs bombot-forge gets it in every session. It's a thin Claude (haiku) worker
that forwards the task to an external cheap model through `scripts/ask_cheap.py`. The only
per-machine step is the API key.

- Endpoint: `https://tokenhub-intl.tencentcloudmaas.com/v1` (OpenAI-compatible `/chat/completions`)
- Default model: `deepseek/deepseek-flash`
- Key: `TEIBTO_API_KEY` — env var, or the file `~/.config/teibto/api.env` (chmod 600)

## Iron rules (do not soften)

- **The key never goes in a repo, a prompt, or a command line.** Store it only in
  `~/.config/teibto/api.env` (or the env). The helper sends it in the HTTP header and never
  prints it. This repo is public; its redaction CI blocks `sk-…`-shaped keys as a backstop.
- **The user types/pastes the key themselves** — into the key file in an editor, or at a hidden
  prompt. Never into a shell command (lands in history), never into chat, never read back.
- **Never turn off TLS verification** to "fix" an SSL error — see Gotchas for the real fix.
- **Customer data leaves to an external provider** when you delegate to this worker. The agent
  refuses unless the caller explicitly OKs it — keep that rule.

## Setup (per machine)

1. Install/update the plugin so the agent + helper are present:
   ```bash
   claude plugin marketplace update bombot-forge && claude plugin update bombot-forge@bombot-forge
   ```
   Then restart Claude (Cmd+Q, reopen) so the new agent is loaded.
2. Save the key. **Default: open the key file in the user's editor** (BomBot uses Sublime) —
   run this yourself; it creates an empty template only if the file is missing, locks it to
   600, and opens it. It never reads or writes a key:
   ```bash
   F=~/.config/teibto/api.env; mkdir -p ~/.config/teibto
   [ -s "$F" ] || printf 'TEIBTO_API_KEY=\n' > "$F"; chmod 600 "$F"
   open -a "Sublime Text" "$F" 2>/dev/null || open -e "$F"   # fallback: TextEdit
   ```
   Tell the user: paste the key right after `TEIBTO_API_KEY=` (no quotes/spaces), Cmd+S, then
   say "saved". Check it's filled **without reading the value** — length only:
   `sed -n 's/^TEIBTO_API_KEY=//p' ~/.config/teibto/api.env | tr -d '\n' | wc -c` (> 0).

   Alternative (terminal, hidden prompt — the user runs it, it can't run inside Claude's Bash):
   ```bash
   bash -c 'mkdir -p ~/.config/teibto && read -rsp "TEIBTO_API_KEY: " k && printf "TEIBTO_API_KEY=%s\n" "$k" > ~/.config/teibto/api.env && chmod 600 ~/.config/teibto/api.env && echo && echo saved'
   ```
3. Smoke test (prints the model's reply; exit 0):
   ```bash
   S=$(ls ~/.claude/plugins/cache/bombot-forge/bombot-forge/*/skills/setup-teibto-worker/scripts/ask_cheap.py | sort -V | tail -1)
   python3 "$S" <<<'Reply with exactly: pong'
   ```

## Using it

Type `/teibto-worker <task>` (the `teibto-worker` skill), or ask for it by name:
> "ให้ teibto-worker สรุป transcript นี้เป็น bullet ภาษาไทย"

The local `local-llm` (Ollama, free, private) stays the default for this kind of work;
`teibto-worker` is picked when you name it or when `local-llm` is unavailable/busy/not good enough.

Change model or endpoint without code changes (env vars read by the helper):
`TEIBTO_MODEL`, `TEIBTO_BASE_URL`, `TEIBTO_TIMEOUT`, `TEIBTO_ENV_FILE`.

## Token usage + cost

Every call prints a usage line on stderr, from the response's OpenAI-style `usage` field (works
for any OpenAI-compatible provider):
`[ask_cheap model: … | tokens in=N out=N total=N (cached=N, reasoning=N incl. in out) | cost=$X]`

- `prompt_tokens` includes cached tokens; `completion_tokens` includes reasoning tokens (both
  confirmed on the live endpoint: reasoning ≤ out).
- **Cost needs a verified rate card.** Prices live in `scripts/prices.json` (USD per 1M tokens
  at peak, keyed by the model id the response returns). A model with no `input`/`output` shows
  `cost=n/a` — never fill it from a blog/aggregator figure. Per-machine flat override:
  `TEIBTO_PRICE_IN` / `TEIBTO_PRICE_OUT` / `TEIBTO_PRICE_CACHED`.
- `deepseek/deepseek-flash` uses DeepSeek's official **V4.1-Flash** rates (peak: in $0.30,
  cached in $0.006, out $1.20; off-peak = half, outside 01–04 & 06–10 UTC Mon–Fri). The helper
  picks peak/off-peak from the call time and labels the cost. These are DeepSeek's own API rates —
  the TEIBTO/TokenHub bill may differ, so the figure is `cost≈` (an estimate).
- Formula: `((in − cached)·input + cached·cached_input + out·output) / 1e6`
  (`cached_input` falls back to `input` if unset).

## Gotchas (hit for real)

- **`SSL: CERTIFICATE_VERIFY_FAILED` on macOS** — Python from python.org ships with an empty CA
  store (0 CAs loaded) until "Install Certificates.command" is run. The helper falls back to
  `certifi`, then `/etc/ssl/cert.pem`, so it still verifies properly. `curl` isn't affected
  (it uses the system store) — a quick way to tell a cert-store problem from an endpoint problem.
- **HTTP 401 `authentication_error` "API Key does not exist"** — the key file is missing/typo'd
  or the key was revoked. Re-run setup step 2. (A fake key returns exactly this, which is also
  how the endpoint URL was verified.)
- **Exit code 2** = no key found (env unset and no `~/.config/teibto/api.env`) — the helper
  prints the setup command.
- **Helper not found** — the agent globs the plugin cache; if the plugin isn't installed or was
  never updated past the version that added this skill, the glob is empty. Run setup step 1.

## Later: more than one cheap model

Right now there's one provider, so there's nothing to prioritise. When a second one is added,
the plan is a provider list with an order and an on/off flag (priority = order, inactive =
`enabled: false`), handled inside the helper — the agent stays the same.

## Quick reference

| Need | Command |
|---|---|
| Update plugin | `claude plugin marketplace update bombot-forge && claude plugin update bombot-forge@bombot-forge` |
| Save key (default) | open `~/.config/teibto/api.env` in Sublime — Setup step 2 |
| Save key (terminal) | the `bash -c 'read -rsp …'` line in Setup step 2 |
| Smoke test | `python3 "$S" <<<'Reply with exactly: pong'` |
| Switch model | `TEIBTO_MODEL=<id>` |
| Key location | `~/.config/teibto/api.env` (chmod 600) |

## Status

v0.1 draft — helper verified against the live endpoint (401 with a fake key, TLS fallback
tested on a python.org Python with an empty CA store). Real-key round trip pending the user
saving the key. Not yet pressure-tested per `superpowers:writing-skills`.
