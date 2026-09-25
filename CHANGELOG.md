# Changelog

Versioning (matches Teibto-Claude-Skills convention):

- **Plugin** = semver (`plugin.json` `version`) + git tag `vX.Y.Z`.
- **Each skill** = `YYYYMM_##` version string in its `SKILL.md` (line under the H1), also
  listed in `plugin.json` description.
- **Commit message** carries both when a skill changes: `type(skill): summary (SKILLVER / PLUGINVER)`
  e.g. `feat(ns-live-verify): add scriptdeployment recipe (202609_02 / 0.2.0)`.
- Bump the skill's `YYYYMM_##` on any skill-body change; bump plugin semver + tag on release.

---

## v0.8.1 — 2026-09-25

- `setup-cheap-worker` **202609_04** — cost is now live for `deepseek/deepseek-flash` using
  DeepSeek's official **V4.1-Flash** rate card (peak: input $0.30 / cached input $0.006 / output
  $1.20 per 1M; off-peak = half, outside 01–04 & 06–10 UTC Mon–Fri). The helper picks peak or
  off-peak from the call time and labels it. Shown as `cost≈` because these are DeepSeek's own API
  rates, not a confirmed TEIBTO/TokenHub bill. Boundary-tested (09:59 peak, 10:00 off-peak,
  Saturday off-peak; 1M in + 1M out at peak = $1.50).

## v0.8.0 — 2026-09-25

- `setup-cheap-worker` **202609_03** — every `ask_cheap.py` call now reports token usage
  (in / out / total, plus cached and reasoning) from the response's `usage` field, and a USD cost
  when a price is configured. `cheap-worker` puts tokens + cost + call count in its footer,
  summed across chunked calls.
  - Prices live in `scripts/prices.json` (USD per 1M, per model id) with env overrides. Shipped
    **empty for `deepseek/deepseek-flash`** on purpose: the only public figure found (~$0.14/1M on
    a TokenHub article) has no input/output split and names `deepseek-v4-flash`, not the id this
    endpoint returns — so cost shows `n/a` until the rate card is confirmed.

## v0.7.1 — 2026-09-25

- `setup-cheap-worker` **202609_02** — `ask_cheap.py` now prints the model that actually
  answered to stderr (`[ask_cheap model: <id>]`), and `cheap-worker` must copy that verbatim into
  its `via cheap-worker (<model>)` footer. Found on the first end-to-end poke: the haiku forwarder
  labelled a correct deepseek answer as "Claude 3.5 Sonnet" — a guessed name. Missing line now
  means "didn't reach the external model", not "make one up".

## v0.7.0 — 2026-09-25

First plugin **agent** (the repo was skills-only until now).

- `agents/cheap-worker.md` (new agent) — a haiku forwarder that hands bulk low-judgement text
  work to a cheap external model (default `deepseek/deepseek-flash` on the TEIBTO
  OpenAI-compatible endpoint). Ships with the plugin, so every machine with bombot-forge gets it
  in every session. Refuses secrets; refuses customer data unless the caller explicitly OKs it.
- `setup-cheap-worker` **202609_01** (new skill) — per-machine setup: save `TEIBTO_API_KEY` at a
  hidden prompt into `~/.config/teibto/api.env` (chmod 600), smoke test, env-var switches.
  Includes `scripts/ask_cheap.py` (stdlib only; key only in the HTTP header, never printed).
  - Verified against the live endpoint: a fake key returns `401 authentication_error`, proving
    URL + request shape.
  - Gotcha found and fixed: python.org macOS Python loads 0 CAs → `CERTIFICATE_VERIFY_FAILED`.
    Helper falls back to certifi, then `/etc/ssl/cert.pem`; verification stays on.
- Redaction CI — new guard for `sk-…`-shaped API keys (20+ chars, so placeholders like
  `sk-XXXXX` and words like `task-` don't trip it).
- Priority / enable-disable across multiple cheap models is deliberately deferred until there's
  a second provider (one provider = nothing to order).

## v0.6.0 — 2026-09-18

- `cdp-browser` **202609_01** (new skill) — driving Chrome for Testing over CDP with the
  personal `cdp.py` helper: launching on a fixed persistent profile (port 9333, `--user-data-dir`
  is mandatory on Chrome 136+), the `tabs`/`nav`/`eval`/`a11y`/`click`/`shot` commands,
  render-accurate `shot` screenshots (why they beat macOS `screencapture`), piercing nested
  shadow-DOM web components (a11y `@ref` / `Input.dispatchMouseEvent` via `cdp.C()`), and the
  safe click-submit auto-login (never read the password field). Generic browser mechanics, so
  **no `ns-` prefix**; cross-references `netsuite-qa-browser` for the NetSuite-specific session
  recovery. The `cdp.py` script itself is deliberately **not** bundled — it's a large personal
  tool with a credential-reading `login` command, so the skill documents usage only.

## v0.5.0 — 2026-09-18

- `setup-global-instructions` **202609_01** (new skill) — set up / sync a machine's global
  `~/.claude/CLAUDE.md` to the canonical NetSuite-dev instructions. Ships a **redacted**
  snapshot of the real global file at `reference/global-CLAUDE.snapshot.md` (customer project
  names, work + personal emails, and the author name replaced with placeholders — `bombot` in
  `/Users/bombot/...` paths is kept, it's the public handle). The skill compares
  the snapshot against the machine's existing file and proposes a **section-by-section merge**,
  never a blind overwrite: back up first, keep the target's machine-local sections, fill
  placeholders from the user's own values (ask, never invent), confirm before writing. Snapshot
  is a point-in-time capture — re-captured (redacted) on request via the maintainer redaction map
  in the SKILL.
  - Design note: the snapshot is public-safe because it's redacted; it passes the repo's
    redaction CI (no known-redacted customer name, no bare 7-8 digit id). Real customer/account
    values live only on
    each machine's own `~/.claude/CLAUDE.md`, never back in the snapshot.

## v0.4.1 — 2026-09-17

- Renamed skill `ns-video-transcribe` → **`video-transcribe`** (content unchanged, still
  `202609_01`). The `ns-` prefix implied a NetSuite tie the skill doesn't have — it's a generic
  homelab-MCP transcription flow. Also dropped "NetSuite" from the skill's H1 title. Folder,
  frontmatter `name`, README row, and `plugin.json` description updated to match.

## v0.4.0 — 2026-09-17

- `ns-video-transcribe` **202609_01** (new skill) — transcribe a video/audio file to
  SRT/TXT/MD through the homelab `bombot` MCP server (a Tailscale bridge to a Windows GPU box,
  `bombot-gaming`, running ffmpeg + faster-whisper). Covers: the prereq check (Tailscale up +
  `bombot` MCP connected, else `homelab-mcp/mac/install.sh` with a matching `.env`), scp'ing the
  file to the Windows inbox and verifying its size matches before transcribing (guards a
  half-copy), the fact that `mcp__bombot__transcribe_video` is a **sync/blocking** call that must
  be flagged to the user, scp'ing the whole result folder back, and the Windows SSH job-object
  gotcha (SSH-spawned processes die on disconnect — doesn't affect the tool, only bridge
  restarts). Uses `mcp__bombot__list_transcribe_inbox` to avoid transcribing the wrong file in a
  shared inbox.

## v0.3.3 — 2026-09-17

Make the repo installable as a plugin marketplace (not just a bare plugin).

- Added `.claude-plugin/marketplace.json` — a single-plugin marketplace manifest pointing at
  this repo's own plugin (`source: "./"`). Previously the repo only had `plugin.json`, so
  `/plugin marketplace add BomBot/bombot-forge` failed with "no manifest found at
  `.claude-plugin/marketplace.json`". Passes `claude plugin validate .`.
- Install flow: `/plugin marketplace add BomBot/bombot-forge` →
  `/plugin install bombot-forge@bombot-forge`.

## v0.3.2 — 2026-09-16

Second `teibto-redteam` confirmation pass (verified against live GitHub, not local claims) —
F1–F6 all held, but the new CI gate had a gap and two nits.

- `.github/workflows/redaction-check.yml` — now catches NetSuite ids **by param**
  (`script=`/`compid=` values not on an allowlist), not only by digit count. The original
  script-id leak was 4 digits — short enough to slip past the 7-8 digit bare-number check.
  Also now scans `.sh` files. Negative-tested: a planted short script-id param fails the build.
- Added `notes.private.md.example` — committed template so a fresh clone knows the shape of
  the gitignored real-values file without any real id in the repo.
- CHANGELOG/README — stopped restating the redacted ticket number in the very lines
  describing that it was generalized (same self-defeating pattern as the v0.3.1 fix, lower
  severity).

## v0.3.1 — 2026-09-16

Fix pass from a `teibto-redteam` review of the repo *after* it went public — traced the
actual live GitHub content via `gh api` (not just a local grep) and found the redaction
itself had re-exposed what it removed, plus one item never in scope before.

- `ns-live-verify` **202609_04** — removed the named prod-account row entirely (even as a
  placeholder, naming a specific target added no value); `SKILL.md` now carries only a
  generic `<ACCOUNT_ID>` / `<SCRIPT_ID>` template row, real rows live only in
  `notes.private.md`.
- `ns-bundle-to-sdf-repo` **202609_02** — dropped the specific bundle id and private target
  repo name; the technique doesn't need either to be useful.
- `plugin.json` — removed the personal contact email from the author field.
- CHANGELOG (this file, retroactively) — past entries that described the redaction by
  **restating the redacted customer name and account id** have been rewritten to describe
  the change without repeating the value. Documenting a redaction by quoting the redacted
  value defeats the redaction — don't do that again.
- Added `.github/workflows/redaction-check.yml` — CI now fails on the known-redacted
  customer name or any 7-8 digit number not on an explicit allowlist, instead of relying on
  someone remembering to grep by hand before every push.

## v0.3.0 — 2026-09-16

- `ns-bundle-to-sdf-repo` **202609_01** (new skill) — distilled from converting one of
  TEIBTO's own bundles (own dev/release accounts) into a private Teibto standards repo.
  Covers: the "Convert to SDF Project" flow + signed-URL download, cleaning up legacy
  auto-generated scriptids via the built-in Change ID tool (leading-underscore trap, the
  `isvalid`-flag submit-blocker workaround, verify-by-URL not by label text), why
  `FileCabinet/` paths must stay unrenamed for deploy path-fidelity, and infra gotchas hit
  along the way (classic-UI megamenu AJAX discovery, `read:packages` scope, package-version
  lag vs repo tags, first-push Actions discovery, `gh api -f/-F` nested-JSON flattening,
  org-level secret-scanning plan lock).

## v0.2.2 — 2026-09-16

Prep for flipping this repo to public.

- `ns-live-verify` **202609_03** — moved real per-account endpoint values out of the tracked
  skill file into `notes.private.md` (new, gitignored); `SKILL.md` now carries a generic
  `<ACCOUNT_ID>` / `<SCRIPT_ID>` template row instead. TEIBTO's own SB2 id stays inline (not
  customer data).
- Restored the "Dev Bridge" term in README/`plugin.json` — confirmed real, points at a
  private repo elsewhere under TEIBTO's own GitHub org; safe to name the term without naming
  the specific repo, since outsiders can't open it either way.
- README: replaced the "before making public" checklist with a "Public-repo hygiene" note,
  and flagged that **pre-existing git history still contains the real values** (pre-dates this
  pass) — a public flip should squash/rewrite history first, not just clean the current tree.

## v0.2.1 — 2026-09-16

Redaction / hygiene pass from `teibto-redteam` review of the auto-mode-setup permission
proposal (found real customer name + account ids committed, and a misapplied `suitecloud`
permission scope for a repo that has no SDF project of its own).

- `ns-live-verify` **202609_02** — dropped the customer-identifying label from the prod
  account row; numeric account/script ids kept as-is at the time (repo was still private) —
  see README's new "Before making this repo public" checklist for the follow-up pass.
- `ns-record-write` **202609_02** — standardized example `--account` across `SKILL.md` and
  `ns_write.py` to TEIBTO's own SB2 (`4089685_SB2` / `4089685`), replacing a placeholder
  account id whose ownership was never confirmed.
- `ns-sdf-prod-deploy` **202609_02** — generalized its status footer (dropped customer name).
- README/CHANGELOG — generalized internal ticket references and fix labels to a neutral
  description; removed the unverified "Dev Bridge" term (not found anywhere in
  `ns-live-verify`'s actual content) from the skill description in README and `plugin.json`.

## v0.2.0 — 2026-09-15

Renamed plugin `teibto-ns-delivery` → **`bombot-forge`** (BomBot's personal NetSuite skills).
Added a record-write skill.

- `ns-record-write` **202609_01** — scoped record write via `ns_write.py` (submit + save
  modes, structured args only, account guard, dry-run default, before→after read-back).
  Includes the exact `permissions.allow` line and `validate-setup.sh` to confirm each machine
  is set up the same.

## v0.1.0 — 2026-09-15

Initial scaffold. Three skills distilled from a real TEIBTO-MFG-Manufacturing session
(Handheld batch deploy, a costing-variance analysis, UE undeploy+verify).

- `ns-sdf-prod-deploy` **202609_01** — import-compare-confirm flow, temp-authid trap,
  scoped deploy, smoke-test, prod guardrails.
- `ns-live-verify` **202609_01** — dbgQuery recipes (SB2 3171 / a customer account, see
  `notes.private.md`), SuiteQL
  gotchas, script-deployment / GL / field verification, login handling.
- `verified-decision-brief` **202609_01** — verify as-is from code+live, comparison/GL
  worked examples, who-answers tags, redaction for sharing.

**Status:** v0.1 drafts — not yet TDD/pressure-tested (see README checklist).
