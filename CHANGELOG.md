# Changelog

Versioning (matches Teibto-Claude-Skills convention):

- **Plugin** = semver (`plugin.json` `version`) + git tag `vX.Y.Z`.
- **Each skill** = `YYYYMM_##` version string in its `SKILL.md` (line under the H1), also
  listed in `plugin.json` description.
- **Commit message** carries both when a skill changes: `type(skill): summary (SKILLVER / PLUGINVER)`
  e.g. `feat(ns-live-verify): add scriptdeployment recipe (202609_02 / 0.2.0)`.
- Bump the skill's `YYYYMM_##` on any skill-body change; bump plugin semver + tag on release.

## v0.28.0 — 2026-10-01

- **Per-project delegation level.** `setup-coding-agent` **202609_19** adds `delegation_level.py` and a section "Delegation level
  (per project)": the user picks **always / medium / low / on-request** for a project and it is remembered there. It writes a
  marked block into the project's **`CLAUDE.local.md`** (Claude Code loads it every session — verified), the choice into
  `.claude/bombot-forge.local.json`, and adds the files to `.git/info/exclude`: all personal, nothing to commit. Other content of
  `CLAUDE.local.md` and `settings.local.json` is never touched (backed up first); `show` / `remove` report and undo exactly that.
- **`always` can be enforced.** Opt-in hook: `PreToolUse` denies `Edit`/`Write`/`MultiEdit`/`NotebookEdit` inside the project (allow
  list: `.claude/**`, `CLAUDE.md`, `CLAUDE.local.md`, `.gitignore`, `deploy.xml`, `manifest.xml`, `.env*`) and tells Claude to use
  `agent_run.py`. **Per-conversation switch** as the maintainer asked: the *user* types `!self` (or `ให้ claude ทำเองรอบนี้`) and
  a `UserPromptSubmit` hook records that session; `!agent` ends it. Text Claude writes into a tool call cannot turn it on (a test
  caught that my first test suite missed this; fixed). A copy of the script is placed in the project so a plugin update cannot
  break the hook path.
- **Verified with the real `claude` CLI:** blocked edit leaves the file unchanged; `!self` in the same message lets it through; an
  allow-listed file edits; Claude can state the level from the block. Hook payloads (`session_id`, `prompt`, `tool_input.file_path`,
  `CLAUDE_PROJECT_DIR`) were read from a live run, not assumed. Tests: 31 (new file) with eight mutations (override not
  session-scoped, hook failing closed, allow list ignored, outside-project policed, whole file overwritten, tool-call text lifts the
  block, hook at every level, user's hooks wiped) each caught, then restored.
- **Behaviour change — read this:** the default for a project with nothing set is **on-request** (nothing is handed over unprompted).
  This replaces the machine-wide `default_delegate: true` of earlier versions, which is now ignored for the decision. The global
  CLAUDE.md "Coding agent" rule and `teibto-agent`'s description say so (`setup-global-instructions` **202609_17**). Machines that
  want the old behaviour set the project to `medium` or `always`.
- **Limits stated in the skill:** Claude can still change files through `Bash` (so `always` stops the editing tools, not a determined
  detour; this is also what lets `git apply` work); a pasted message containing `!self` counts as typed; the hook fails open; **not
  run on Windows**; whether `always` saves tokens is **not measured** (for a one-line change it likely costs more).

---

## v0.27.1 — 2026-10-01

- **The three-list summary no longer ends the reply.** 0.25.0 told Claude to *end* every answer with "checked (with evidence) /
  inferred / not looked at". A user then saw that replies ending that way left the chat input **without a suggested next
  prompt**. The Accuracy rule now says: put the three lists first, then **close with one line "ขั้นถัดไป: …"** (what the user
  should say or decide next), and never end on the lists. Dev snapshot + non-dev build carry it (`setup-global-instructions`
  **202609_16**, `setup-global-instructions-nondev` **202609_05**); the user's own `~/.claude/CLAUDE.md` is updated by hand and
  other machines get it by re-running the setup skill.
- **Not verified:** that this is the cause of the missing suggestion, or that it brings the suggestion back. The suggestion is a
  feature of the Claude Code app; how it is produced was being checked against the docs when this was written. A test asserts the
  wording (lists first, a closing next-step line, no "end with the lists"), not the UI behaviour. The three-list wording that
  `agent_run.py` sends to DeepSeek is unchanged — its output goes back to Claude, not straight to the user.

---

## v0.27.0 — 2026-10-01

- **`setup-global-instructions-nondev` 202609_04: a narrow lane for an urgent JS hotfix, and level C done by hand.**
  Maintainer's decisions: level C is something the **user does by hand** (Claude may draft steps/spec and check the result);
  JS stays banned **except** an on-site hotfix of a real bug that cannot wait. New section "Hotfix JS" in the built text, nine
  fixed steps: use the file as it is on the account → back it up outside the repo and record its sha256 → edit a local copy
  with a greppable comment `HOTFIX-NODEV <DD/MM/YYYY> <name> | why | what | original` → re-check the diff, syntax and what uses
  the file → report to the user (diff, size, checked / inferred / not looked at, risk, rollback, **the warning that a dev may
  overwrite the file**) and get one OK → **Claude uploads through Claude in Chrome** → verify (download it back and compare
  sha256, reproduce the bug, Execution Log) → roll back from the backup if wrong → write a .md note for the dev, and remind the
  user to tell the dev directly. Large changes: Claude offers a .md for the dev first; the user decides.
- The ban section keeps "no SDF, no XML deploy" with **no exception** and names the hotfix as the **single** exception for JS
  (existing files only: no new file, script record or deployment). Its heading no longer claims "no exceptions".
- **Size is "by judgement" as the maintainer chose — it is not enforced** (no line limit); the protection is that the user is
  told how big it is and decides. Also unenforced: a dev overwriting the file later. Both are written in the skill.
  **Not tested:** Claude in Chrome uploading to File Cabinet, replacing a file so scripts still point at it, the download-back
  hash; whether `node --check` exists on a non-dev machine (the text says to report "syntax not checked" otherwise).
- Tests: 18 for the builder (was 13), including step order (backup before edit, report before upload, upload before verify), the
  overwrite warning in both the confirmation and the note, and the single-exception wording; six mutations (warning removed,
  sha256 dropped, tag dropped, heading claims no exceptions, level C no longer by hand, report/upload order swapped) each made
  a test fail, then were restored.

---

## v0.26.0 — 2026-10-01

- **`setup-global-instructions-nondev` 202609_03: what a non-dev user can and cannot do through Claude, decided with the
  maintainer.** New section "ขอบเขตงานผ่าน UI" in the built text, three levels. **A** read/analyse (no confirmation).
  **B** no-code UI changes — Saved Search, Report, Dashboard, custom field, custom record, workflow, other no-code settings
  the user names — allowed in sandbox **and production**, one chat OK per change, then seven fixed steps (plan; ask whether the
  account is live; impact check; record the old state; Claude clicks through **Claude in Chrome** in front of the user, never
  `bsk`; compare before/after; roll back if wrong). **C** never: SDF, deploy, upload/edit JS, scripts and deployments,
  roles/permissions, import and mass update, edit/delete financial transactions, subsidiary/accounting setup, delete anything.
- The ban section no longer forbids custom fields/records/workflows through the UI (it contradicted the intent); it still bans
  scripts and deployments. Role rewritten: Claude helps both to analyse and to customise through the UI.
- **My addition, not requested:** a live or unknown-status account stops level B until the user re-confirms with a rollback
  plan. Reason: the maintainer's justification for allowing production was "most accounts are not live yet"; one line to
  remove in `reference/nondev-sections.md` if unwanted.
- Stated in the skill as not tested: a model following the seven steps, and Claude in Chrome completing a NetSuite
  customisation or handling its native dialogs. The text is advice; the enforced limit is the user's NetSuite role.
- Tests: 13 for the builder (was 9); mutations (old UI ban back, live-account stop removed, rollback step dropped, `bsk`-click
  ban removed) each made a test fail, then were restored.

---

## v0.25.0 — 2026-09-30

- **The worker must show a source for every claim.** A bare "check your answer again" lets a model answer "correct"
  without opening anything, so the wording demands evidence: *every statement needs a source (file:line, command output,
  or the query run); with no source, write "not verified"; end with VERIFIED / INFERRED / NOT LOOKED AT (NOT CHECKED for
  code).* It is one shared constant (`VERIFY_CORE`) added to the prompts of all three profiles (`code`, `analyze`,
  `ns-reader`), and a test asserts the prompt the agent actually receives contains it. A live `analyze` run followed the
  format (its one runtime claim, `0 / -1` giving `-0.0`, was labelled INFERRED and checked true by hand).
- The same rule, in Thai, in the **Accuracy** section of the global CLAUDE.md snapshot (so the dev and the non-dev skills both
  carry it), plus a second line: another AI's reply is only a claim — open a sample of the sources it cites before trusting it.
  `setup-global-instructions` **202609_15**, `setup-global-instructions-nondev` **202609_02** (built from that snapshot).
- `setup-coding-agent` **202609_18**: new section "Making the worker show its evidence". Stated there: this makes replies
  easier to check, **not** correct — the caller still spot-checks. **Not measured** whether it raises the accepted-as-is
  rate; compare `--log-report` before and after (earlier runs used the old wording).
- Tests: 46 (was 45); mutations (analyze prompt loses the core, code prompt loses it) each made a test fail, then were restored.

---

## v0.24.3 — 2026-09-30

- **Sessions are marked so an escaped one can be found.** Every `opencode run` that `agent_run.py` starts now passes
  `--title "[agent_run] <run id> <profile>"` (verified live: OpenCode stores exactly that title). `--purge-sessions` selects
  a session by its directory inside the agent-runs cache **or** by that title prefix, so it is still found if its folder
  was moved or deleted; a database without a `title` column falls back to directory only. The title carries only the run id
  and profile, never the task; as a side effect OpenCode no longer titles the session with an LLM summary of the prompt.
- No change to what is deleted: a finished run still deletes its own session; `--purge-sessions` still lists first and
  deletes only with `--yes`. Sessions created before this version have no title marker (directory match only).
- `setup-coding-agent` **202609_17**. Tests: 45 (was 43); mutations (drop `--title` from the analyze command, purge ignores
  the title marker) each made a test fail, then were restored.

---

## v0.24.2 — 2026-09-30

- Test-only fix: the 0.24.1 tests used made-up run folder names shaped like dates (eight digits), which the repo's
  redaction check treats as account-shaped numbers, so CI failed on 0.24.1. Replaced with non-numeric names. The local
  check had printed the hit count before the commit and it was not acted on.

---

## v0.24.1 — 2026-09-30

- **`agent_run.py` deletes the OpenCode session each run creates** (all three profiles, OpenCode only). Until now every
  run left a session in OpenCode's database holding the whole conversation, i.e. whatever the agent read — a second copy
  of possibly customer data next to `out.jsonl`. The id comes from the run's own event stream (validated as `ses_…`), the
  delete is `opencode session delete <id> --standalone`, a failure is reported and logged but never fails the run.
  `--keep-session` opts out. Ledger gains `session_id` / `session_deleted`.
- **`--purge-sessions [--yes]`** lists, and with `--yes` deletes, the sessions whose directory is inside
  `~/.cache/bombot-forge/agent-runs/` (id + run folder name shown, dry run by default). The match is a string prefix
  on purpose: a `LIKE` would treat `_` in a path as a wildcard (a test catches that).
- `setup-coding-agent` **202609_16**: new section "OpenCode sessions". Verified live (session count 33 before and after a
  run; `session delete` removes session and message rows). Not verified: a timed-out run may print no session id, so its
  session is left. `out.jsonl` in the run folder is still kept and is not pruned.
- Tests: 43 (was 35); four mutations (analyze stops deleting, purge uses `LIKE`, `--keep-session` ignored, no id
  validation before delete) each made a test fail, then were restored.

---

## v0.24.0 — 2026-09-30

- **New skill `setup-global-instructions-nondev` (202609_01)** — the global `~/.claude/CLAUDE.md` for a non-dev NetSuite
  machine: **no SDF at all** (`suitecloud` in any form), no deploy of XML/JS, no upload/edit of JS on the account; work by
  reading pulled files (a git repo or a File Cabinet download — assumption to confirm), the Dev Bridge and the browser;
  record edits only through `ns_write.py` on a per-case yes. Not a copy of the dev skill: `scripts/build_nondev.py` keeps
  five sections of the dev snapshot verbatim (Accuracy, Communication, Slack, Session memory, Browser automation), drops
  the developer-only ones, and adds `reference/nondev-sections.md`; the flow (diff by section, backup, confirm) is the dev
  skill's. A target section that contradicts the ban (`SDF Deploy`) is shown and offered for removal.
- **Deny rules, measured.** The skill also proposes `permissions.deny` = `Bash(suitecloud:*)`, `Bash(npx suitecloud:*)`,
  `Bash(*suitecloud*)`. Tested with the real `claude -p` in `bypassPermissions` mode against a fake `suitecloud` that logs
  any real run: with no rule it ran; with the rules a direct call, `bash -c '…'` and `$(which suitecloud) …` did not.
  **Evaded:** `s=suite; ${s}cloud file:list` ran (the patterns match the command text). Also untested: deny vs an existing
  allow entry. Both are stated in the skill; the CLAUDE.md ban covers what the rule cannot.
- Tests: 9 (`test_build_nondev_offline.py`); three mutations (keep `SDF Deploy`, drop `file:upload` from the ban,
  fence-blind heading split) each made a test fail, then were restored.

---

## v0.23.2 — 2026-09-30

- `setup-browser` **202609_14**: new optional Step 5b, *keep the `bsk` daemon running from login*. Explains what the
  daemon is, that ordinary `bsk` commands already start it (so the default is **No**), and the Windows recipe as a
  Task Scheduler task at logon running `bsk.exe daemon start --foreground` with no time limit and no second instance.
  Status stated in the skill: the maintainer reported the Task Scheduler approach works on Windows, but the exact
  settings were not captured — the PowerShell example is from Microsoft's cmdlet docs and was **not run**; hiding the
  console window not verified; macOS LaunchAgent / Linux `systemd --user` untested, with the known risk that the
  daemon replaces itself on auto-update (seen in `~/.bsk/daemon.log*`) and a restart-on-exit supervisor could race
  its successor. No new `browser.json` key (the state is read from the machine).

---

## v0.23.1 — 2026-09-30

- README only (no skill body changed): the `setup-coding-agent` row now mentions the `analyze` and `ns-reader` profiles,
  the delegation log (`~/.config/bombot-forge/delegations.jsonl`) and the untested-on-Windows note; the `teibto-agent` row
  mentions `--profile analyze`; the Structure block lists `plugins.json`. These were missing from 0.22.8 – 0.23.0.

---

## v0.23.0 — 2026-09-30

- **New skill `setup-plugins` (202609_01)**: installs the team's Claude Code plugins from their **GitHub source**, only
  the ones the user picks. `plugins.json` lists six (teibto-netsuite-toolkit, superpowers, impeccable, mattpocock-skills,
  andrej-karpathy-skills, ui-ux-pro-max); `scripts/plugins_setup.py` shows what is present, then runs `claude plugin
  marketplace add` + `install <plugin>@<marketplace> --scope user`. Guards, all in code and covered by offline tests: only
  four command shapes may run; a name not in the file is refused; a plugin already present under any marketplace
  (`@synced` included) is skipped; a marketplace that appears under a different name than the file says is reported, not
  trusted; a repo it cannot read is reported and the run continues; it never logs in.
  Tests: 12 with a fake `claude`; three mutations (drop the "present elsewhere" check, allow any scope, skip the
  marketplace-name check) each made a test fail, then were restored. Live: the real CLI in a throwaway `HOME` installed
  two public plugins, reported the unreadable repo, and a re-run installed nothing.
  Not covered: skills that are plain folders or symlinks in `~/.claude/skills`, plugins that only come from the account
  sync, and the locally uploaded `9arm-skills` (no GitHub source); private-repo installs with real access; Windows.
- **CI fix**: the two previous pushes (0.22.9, 0.22.10) failed the redaction check because a test used a made-up
  eight-digit run id, which the "account-shaped number" scan rejects. Replaced with a non-numeric id. The earlier
  "nothing left to do" after 0.22.10 was said without checking CI.

---

## v0.22.10 — 2026-09-30

- **Ledger moved** from `~/.local/share/bombot-forge/delegations.jsonl` (0.22.9, one day old, no real entries on the
  author's machine) to `~/.config/bombot-forge/delegations.jsonl`, beside `agent.json`/`browser.json`. Not
  `~/.claude/cache`: that is Claude Code's own cache (it keeps `changelog.md`, `model-catalog`, and runs a cleanup), and
  the ledger must persist. Anyone who ran 0.22.9 with real work must move the file by hand.
- **`agent_run.py` prepared for Windows — never run on Windows.** `python` instead of `python3` in the allowed
  command; forward slashes in permission globs; `ns_read.py` copied when symlinks are refused; agent CLI launched by
  its full `which` path (`opencode.cmd`); UTF-8 for JSON files; console switched to UTF-8 (a cp1252 console crashed on a
  Thai reply — mutation-checked); `teibto-agent` locates the helper with a Python one-liner (tested on macOS, picks
  0.22.9 over 0.9.0 by version number). New `setup-coding-agent` **202609_15** "Windows" section lists what is handled,
  what is unknown (which shell OpenCode uses there and whether it checks `>`/`|` the same way; `chmod` no-op; the
  browser skills' macOS-only steps) and a forced-escape check to run on a new OS before trusting `analyze`/`ns-reader`.
  `setup-global-instructions` **202609_14**.
- Tests: 35 (was 30) — forward-slash globs with `python`, symlink-refused fallback to copy, ledger location, Thai reply on
  a cp1252 console. Mutations (drop the stdout switch, drop the symlink fallback) each made a test fail, then were restored.

---

## v0.22.9 — 2026-09-30

- **Delegation log so the setup can be measured.** Each `agent_run.py` run (`code`, `analyze`, `ns-reader`) appends one
  line to `~/.local/share/bombot-forge/delegations.jsonl` (mode 600; `BOMBOT_FORGE_LOG` overrides): tokens in/cached/out,
  estimated USD, seconds, exit, sandbox-refused commands, files/lines changed, task length, run id — **no task text,
  reply, file names or code**. New `--log-outcome <run id> --verdict accepted|fixed|rejected [--claude-fixed-lines N]
  [--note]` (refuses an unknown run or verdict; latest verdict wins) and `--log-report [--since]` (per-profile totals,
  share used as-is, unreviewed runs). `setup-coding-agent` **202609_14**: protocol step 8 "record the verdict" and a
  "Measuring it" section; `teibto-agent` returns the `logged : run id` line; global `CLAUDE.md` + snapshot
  (`setup-global-instructions` **202609_13**) carry the rule.
- Limits stated in the skill: the log proves the DeepSeek side and the review outcomes only; Claude's own tokens and the
  all-Claude baseline are not recorded. Exercised on scratch repos only, not on real work yet.
- Tests: 30 (was 22), incl. three end-to-end runs through a fake `opencode` (ledger line written, no task text in it,
  lines-changed counted, verdict round-trip). Mutations (analyze stops logging; verdict for an unknown run accepted)
  each made a test fail, then were restored. Live: one real `analyze` run logged and reported.

---

## v0.22.8 — 2026-09-30

- **New `agent_run.py --profile analyze`** (OpenCode only): read-only bug hunt in an existing repo, run by DeepSeek.
  Throw-away worktree of HEAD, OpenCode-enforced permissions (read/glob/grep + `git log|show|blame|diff` only), report
  out (suspects with `file:line`, SEEN vs INFERRED), no patch. `setup-coding-agent` **202609_13**: the "Subagents that
  do NOT edit" section became "Investigating existing code: DeepSeek finds, Claude checks" — DeepSeek finds; Claude
  verifies the cited lines, using `haiku`/`sonnet` subagents with an explicit `model`, Opus only for the final root-cause
  call. `teibto-agent` may pass `--profile analyze`. Global `CLAUDE.md` (+ snapshot, `setup-global-instructions`
  **202609_12**) carries the two-step rule.
- **Security fix to the existing `ns-reader` profile, found while testing `analyze`.** Two holes, both measured:
  1. OpenCode 2.0.20 also gives the model `execute` (Code Mode with `browser.*` / `opencode.*` tools), `subagent`,
     `skill` and `question`. `ns-reader` set no rule for them, so they were available (`execute` ran a `search()`).
     Now all four are `deny` in both read-only profiles. Not tested: whether `browser.*` could really have reached the
     web or read a local file.
  2. `external_directory: deny` does **not** cover the shell, and a `>` redirect is not checked against the bash list
     (`git log > /outside/file` wrote a file outside the folder). Through `ns_read.py query … > /any/file` the agent could
     have overwritten a file the user owns. Redirects whose target contains `/`, `~`, `$` or `..` are now denied in both
     profiles (`analyze` denies `>` and `<` outright). Verified live against the real configs: absolute, `>path`, `~/…`
     denied; a relative redirect still writes, into the run's empty scratch folder only. A query containing both `>` and
     `/` is now refused (fail-closed).
  No known misuse happened; the earlier "everything else is denied" statement for `ns-reader` was too strong.
- Tests: 22 in `test_agent_run_offline.py` (was 16); three mutations (drop `execute` deny, drop the `analyze` `>` deny,
  drop the `ns-reader` redirect escapes) each made a test fail, then were restored. Live: `analyze` found a seeded
  off-by-one and refused forced escapes; `ns-reader` still ran `whoami` and a `COUNT(*)` on SB2 (`id > 0` allowed).

---

## v0.22.7 — 2026-09-30

- **Non-edit subagents must set `model`.** A session with `default_delegate` on still ran a batch of "Audit …" Agent
  subagents on Opus 5.5 (80–160k tokens each): the delegate protocol covers edits only, and an Agent call with no
  `model` inherits the main session's. New section in `setup-coding-agent` **202609_12** and a line in the user's
  global `CLAUDE.md`: `haiku` for sweeps, `sonnet` for audits needing judgement, Opus only for the final call.
  `setup-global-instructions` **202609_11**: the snapshot now carries the "Coding agent" section too (it was missing).
  Not measured: whether the model rule actually cuts cost — it was not run on a real audit.

---

## v0.22.6 — 2026-09-30

- The `bsk` Login click re-tested on a **truly expired session** (the user logged out of SB2 first): `ns_read.py whoami`
  stopped at the login page without logging in (exit 3), the form was redirected to automatically with both fields
  `:-webkit-autofill` and the button enabled, one `#login-submit` click landed on Home (`4089685_SB2`, `SANDBOX`, no MFA).
  Removes the caveat from 0.22.5. `browser-engines` **202609_16**.

---

## v0.22.5 — 2026-09-30

- **`tab borrow` removed from the guidance** (`browser-engines` **202609_15**): its confirmation prompt shows for about
  a second, so nobody can click it in time; the two hand-offs that need no confirmation (`open -a "Google Chrome"`,
  Claude in Chrome) stay. It is no longer listed among the approvals that exist.
- **`bsk click '#login-submit'` tested** on SB2 (4089685_SB2): both fields matched `:-webkit-autofill` with
  `value.length` 0, one click submitted the hidden values and landed on Home (`SANDBOX`, no MFA). Caveat: the session
  was still valid when the login page was opened, so this was not a truly expired-session run. `ns-live-verify`
  **202609_11**, `setup-browser` **202609_13**, `setup-global-instructions` **202609_10**. The user turned
  `auto_login_click` on for this machine.

---

## v0.22.4 — 2026-09-30

- "Say it every time `bsk` is used" now says what it is: a **notice, not a question** — send it and keep working, no
  waiting for a reply and no approval step, so it never blocks a run. `browser-engines` **202609_14**,
  `setup-browser` **202609_12**, `setup-coding-agent` **202609_11**, `setup-global-instructions` **202609_09** and the
  user's global `CLAUDE.md`. Approvals that remain by design are listed in `browser-engines` step 0: the extension's
  `tab borrow` prompt, a non-sandbox account not yet confirmed, production writes, and Login clicking without consent.

---

## v0.22.3 — 2026-09-30

**Correction of my own earlier finding (0.21.0 – 0.22.2).**

- Those releases said an `bsk` Agent Window "does not get autofill" (email 0 characters for 10 s). **That was wrong.**
  Re-measured, this time reading the boolean `:-webkit-autofill` as well: in an Agent Window opened in the background
  and one opened focused, and in a hidden Claude in Chrome tab, **both the email and the password fields matched
  `:-webkit-autofill` while the email `value.length` was 0**. Chrome hides an autofilled value from page scripts until
  the user interacts with the page; the earlier "20 characters" came from a tab the user had just clicked (the
  borrow prompt). The real cause of the user's issue ("the email looked empty, so the agent stopped") was
  **reading the length**, not the window.
- Fixed in `browser-engines` **202609_13**, `setup-browser` **202609_11**, `ns-live-verify` **202609_10**, `ns_read.py`
  (its expired-session message; 1 test reworded), `setup-global-instructions` **202609_08** and the user's global
  `CLAUDE.md`: check autofill with `:-webkit-autofill`, never the value length; the rule "field empty → stop" in the
  global instructions now reads "`:-webkit-autofill` not set → stop". The advice "never log in inside the Agent
  Window" is withdrawn; hand-off to a real tab stays as the fallback.
- New verified facts: Claude in Chrome is connected on this Mac and keeps its tabs in a Chrome **tab group** (the
  first use with no group opened one new window holding it); its `javascript_tool` reads the same autofill flag.
  **Not tested:** that a `bsk click '#login-submit'` submits the hidden autofilled values.

---

## v0.22.2 — 2026-09-30

- `browser-engines` **202609_12**, `setup-browser` **202609_10** — the real-tab hand-off, second try, with the user
  ready: `bsk tab borrow` was confirmed in ~2 s. In the real tab Chrome **had autofilled** the login form
  (email 20 characters; email and password both matched `:-webkit-autofill`; only the email length was read)
  and it **survived the borrow** for the 6 s watched. That settles the earlier question: the empty email was
  the Agent Window (it never got autofill), not speed. Facts recorded: the prompt shows for ~1 s so warn the
  user first (a 10 s countdown worked) and use `--timeout 120`; a borrowed tab cannot be `tab close`d until
  `tab return`; `session stop` returns borrowed tabs by itself. **Not tried:** clicking Login in the borrowed
  tab, and a borrow when the user is not watching.

---

## v0.22.1 — 2026-09-30

- `browser-engines` **202609_11**, `setup-browser` **202609_09** — the `bsk tab borrow` confirmation, as the user
  saw it: the prompt appeared for about **one second**, too brief to click, which is why the earlier test timed
  out. Login hand-off therefore no longer leans on borrow: open the login page as a real tab (verified) and let
  the user press Login, or use Claude in Chrome. Where the prompt lives is still unknown; the daemon log
  (info level) records nothing about borrow requests, so it cannot say either.

---

## v0.22.0 — 2026-09-30

**Rename (breaking for anything that calls the old name).**

- `cdp-browser` → **`browser-engines`** (**202609_10**): it chooses between `bsk` and `cdp` and holds the
  verified `bsk` recipes, so a name with only `cdp` in it misled (the user asked "is there a bsk-browser
  skill?"). Moved with `git mv`; content unchanged apart from a one-line rename note. Invoke it as
  `/bombot-forge:browser-engines`.
- A `cdp-browser` **redirect stub** (**202609_10**) stays so old references do not dead-end; delete it once
  nothing points at it.
- References updated: `setup-browser` **202609_08**, `ns-record-write` **202609_12** (text + `validate-setup.sh`
  message), `ns-live-verify` **202609_09**, the README, the global instructions snapshot
  (`setup-global-instructions` **202609_07**) and the user's own `~/.claude/CLAUDE.md` (backed up first).
  Older CHANGELOG entries keep the old name on purpose — they describe what shipped then.
- Anything outside this repo that names `cdp-browser` (a project `CLAUDE.md`, a script, a note) still works
  through the stub but should be switched.

---

## v0.21.2 — 2026-09-30

- `cdp-browser` **202609_09** — the real-tab hand-off, tried on a Mac (Chrome 152, bsk 0.3.1). **Verified:**
  `open -a "Google Chrome" <login url>` opens a new *tab* in the already-open Chrome window, and
  `bsk tab list --scope user` sees it in a user window (not an Agent Window). **Not verified:** `bsk tab
  borrow` — the confirmation prompt was not answered within 60 s, so it timed out (exit 4, `confirmation_timeout`);
  whether autofill happens in that tab and survives the borrow is still unknown. bsk's hint is not to repeat
  the request, so it was not repeated. The test session was stopped by id and the login tab was left for the
  user to close (bsk cannot close a tab in the user's window).

---

## v0.21.1 — 2026-09-30

- **Fix: the skills told the agent to confirm "`session_count` is 0" after stopping its session** — wrong when
  another Claude session shares the `bsk` daemon, and it pushed a run into `bsk session stop --all`, which
  stopped that other session's work. `cdp-browser` **202609_08**, `setup-browser` **202609_07** and the global
  instructions snapshot (`setup-global-instructions` **202609_06**) now say: stop only your own id, never
  `--all`, confirm the id is gone from `bsk session list`, and do not expect the count to be 0. (`ns_read.py`
  already stopped only its own session id.)

---

## v0.21.0 — 2026-09-30

- **Issue: sessions that hit the NetSuite login page saw an empty email, so the auto-login stopped.** The
  suspected causes were "the read was too fast" or "the page was opened in the Agent Window". Live test
  (Chrome 152, bsk 0.3.1): on the login page the email stayed at **0 characters for 10 s** in an Agent Window
  opened in the background *and* in one opened focused, so it is not speed — an Agent Window did not get
  autofill. Consequence written into `cdp-browser` **202609_07**, `setup-browser` **202609_06** and
  `ns-live-verify` **202609_08**: never try to log in inside a `bsk` Agent Window; hand off to a **real tab**
  (Claude in Chrome, or ask the user to open the page) and apply the auto-login rule there. Those hand-off
  routes, `open -a "Google Chrome" <url>` and `bsk tab borrow` are **not yet exercised**.
- **Say it every time `bsk` is used** (the user's request): one line in the chat before the first `bsk`
  command of a job — what for, which account/page, a background Agent Window closed when done. Written
  into the three skills, `setup-coding-agent` **202609_10** (before an `ns-reader` run) and the global
  instructions snapshot (`setup-global-instructions` **202609_05**); `ns_read.py` also announces itself on
  stderr and keeps stdout pure JSON. 38 offline tests (3 new).
- **Not done, and why:** "open a new tab, not a new window". `bsk` cannot: every session owns an Agent Window
  and `tab create` only makes tabs inside it (`--no-focus` / `--no-active` are the least intrusive it gets).
  A tab in the user's own window is what Claude in Chrome does.
- Also disclosed: while measuring this I ran `bsk session stop --all` once, which stops every session on the
  machine, including one that may have belonged to another Claude session. Sessions are stopped by id.

---

## v0.20.1 — 2026-09-30

- `setup-coding-agent` **202609_09** — docs only: the confirmed-account path was exercised end to end. After the
  user confirmed one customer production account (not yet live) through the picker, it was recorded with
  local + UTC time, session id and name; the agent then ran `whoami` and `ping` on it, its attempt on a
  different production account was refused by OpenCode, and the run without `--allow-prod-read` was refused
  by `ns_read.py`. Identity only — no record or query was read. One tool call in the agent's log had an
  empty command (a non-shell tool); not investigated.

---

## v0.20.0 — 2026-09-30

- **`ns-reader` can read the accounts the user confirmed, not only sandboxes** (`setup-coding-agent`
  **202609_08**). Sandbox-only was the author's own precaution about customer data leaving; the user's
  work is mostly on production that is not live yet and they trust the provider key, so: each non-sandbox
  account is opened one at a time by the user. `agent_run.py --grant-read-account <A> --session-id <id>
  [--session-name] [--note]` records the account with local + UTC time, session id and name, and the note in
  `agent.json` → `read_accounts` (backup + atomic write, chmod 600, refuses without a session id);
  `--revoke-read-account <A>` removes it. The profile then allows exactly
  `ns_read.py --allow-prod-read <sub> --account <A> ...` for those accounts and nothing else.
- The rule order carries the security (OpenCode applies the **last** matching rule — verified both ways):
  deny all → allow the subcommands → deny `--allow-prod-read` → allow it per confirmed account →
  deny `--bridge-path` and `--config` last so no allow above can override them. Verified with OpenCode's
  real matcher on the exact generated rules (2 allowed, 5 denied). `ns_read.py` now refuses a repeated
  `--account`, which the permission glob alone would not catch. The agent is also told that data it reads
  may contain instructions and must be treated as data.
- Tests: `test_agent_run_offline.py` 16 (permission order, unsafe account strings, grant/revoke, backup,
  no duplicate), `test_ns_read_offline.py` 35. Not yet done: a real read of a real non-sandbox account
  through the agent (needs the user's confirmation for a specific account).

---

## v0.19.0 — 2026-09-30

- **How the setup skills ask the user.** A setup choice used to come out as a long paragraph ending in a
  sentence ("bsk / cdp / both?"), easy to miss. New rule, written into `setup-browser` **202609_05**,
  `setup-coding-agent` **202609_07**, `setup-local-llm` **202609_02** and `setup-global-instructions`
  **202609_04**: bullets first (Pros · Cons · Best when, ≤ 3 lines per option, recommendation in one
  line), then a picker via `AskUserQuestion` as the last thing in the message (short label, one-line
  trade-off, recommended first, ≤ 4 options, one decision per question, ≤ 4 questions per call); if the
  tool is unavailable or the run is unattended, the same as a numbered list in chat — never pick for the
  user. `setup-browser` also names the concrete option set for engine choice, Claude in Chrome, the Dev
  Bridge trial, login consent, keep/change on re-run, and the auto-mode-blocked choices.
  Not yet exercised in a fresh session: the picker rendering and the fallback are as written, not observed.

---

## v0.18.1 — 2026-09-30

- README: new top section "Setup skills — run once per machine" (setup-global-instructions, setup-browser,
  setup-coding-agent, setup-local-llm) with what each writes on the machine; the rest regrouped into
  "Work skills" and "Deprecated" (teibto-code, teibto-worker, setup-teibto-worker); `verified-decision-brief`
  moved from the Agents table (it is a skill); Agents lists only what `agents/` ships (`teibto-agent`).

---

## v0.18.0 — 2026-09-30

- **`setup-teibto-worker` deprecated (202609_08 stub) and folded into `setup-coding-agent` (202609_06).**
  Moved with `git mv`: `ask_cheap.py` and `prices.json` now live in `skills/setup-coding-agent/scripts/`;
  the key-saving steps, smoke test, cost formula and gotchas are the new section "The company key and
  the one-shot helper". `agent_run.py` reads `prices.json` from beside itself. The key file path
  (`~/.config/teibto/api.env`) is unchanged, so an already-configured machine needs nothing.
- New `scripts/test_agent_run_offline.py` (4 tests): the price table sits beside `agent_run.py`, is valid,
  gives the default model a positive price, gives an unknown model none (no guessed prices), and
  `ask_cheap.py` reads the same table. Written first; it failed before the move and passes after.
- `teibto-worker` skill stub **202609_04**: paths updated. `ask_cheap.py` is kept (moved) because it was not
  confirmed unused.
- Anything that ran `.../skills/setup-teibto-worker/scripts/ask_cheap.py` by that path (a script or a
  note outside this repo) must switch to `.../skills/setup-coding-agent/scripts/ask_cheap.py`.

---

## v0.17.1 — 2026-09-30

- **Fix: `ns_read.py` / `ns-live-verify` pointed at the wrong endpoint.** They were written against an
  older tester Suitelet (`action=dbgQuery` in the URL, `step=DEBUG_QUERY`, body `{qtype:"sql"}`), not the
  TEIBTO Dev Bridge (`Teibto/TEIBTO-Dev-Bridge`, read from its README and script). The real bridge is one
  Suitelet addressed by script + deploy id with the action in the POST body (`ping`, `query`, `record`,
  `lookup`, `feature`, `search`, `help`). So the earlier note "`record` not verified — the SB2 tester has
  no `dbgRecord`" was a symptom of the wrong endpoint, not a limit of the bridge: `record` works.
- `ns-live-verify` **202609_07** — rewritten around the real API (endpoint, action table, `query` rules from
  the script: must start with SELECT so no `WITH`, no `;`, DML words rejected even in literals, lowercase
  keys, the 5000/1000 row caps, `OFFSET` ignored). `ns_read.py` now has `whoami`, `ping`, `query`,
  `record`, `lookup`, `feature`, `search`; before the real request it verifies the endpoint answers `ping`
  in the bridge's shape and reports the same account; the path can only be `scriptlet.nl?script=&deploy=`;
  default ids are the README's. Verified live on a sandbox (all but a saved search, `--meta`, a real
  `--filters-json`). 33 offline tests; each guard mutation-checked.
- `setup-coding-agent` **202609_05**: the `ns-reader` allow-list now covers all seven subcommands (config
  written and read back; not re-run live through the agent). `setup-browser` **202609_04**: Dev Bridge step
  uses the default ids and `ns_read.py ping`.

---

## v0.17.0 — 2026-09-30

**Breaking.**

- **Removed the `teibto-worker` subagent** (the haiku forwarder to DeepSeek). **New subagent
  `teibto-agent`** in its place: a thin haiku runner that hands ONE well-scoped edit to the machine's
  coding-agent CLI (OpenCode or Cline, company DeepSeek key) through `agent_run.py`, and returns the
  run report and the patch path marked NOT REVIEWED — it never applies, commits or edits the repo;
  the caller reviews every line and applies. It refuses to run without `~/.config/bombot-forge/agent.json`.
  Not yet exercised through the Agent tool (a subagent only loads at session start).
- `teibto-worker` **202609_03** and `teibto-code` **202609_03** skills are now deprecated redirect
  stubs (their old flow called the removed subagent; it is in git history). `setup-teibto-worker`
  **202609_07** keeps `ask_cheap.py`, `prices.json` and the key step, text updated.
- `setup-coding-agent` **202609_04** + `agent_run.py`: `--agent` / `--model` now default from
  `~/.config/bombot-forge/agent.json` (a model name is only reused for the agent it was saved with);
  documents `teibto-agent`. Other repos or sessions that call `subagent_type: bombot-forge:teibto-worker`
  (for example a project-level `teibto-code` skill) will break and must be switched.

---

## v0.16.1 — 2026-09-30

- `setup-coding-agent` **202609_03** + `agent_run.py --profile ns-reader` — lets an OpenCode agent
  READ a NetSuite sandbox with an enforced allow-list: only `ns_read.py whoami|query|record`; all
  other commands, edits, web access and the flags `--allow-prod-read` / `--bridge-path` / `--config`
  are denied by OpenCode's own permission system. Verified live (2 allowed, 4 denied); compound
  commands (`&&`, `;`, `$(…)`) verified denied. Prints the commands the agent actually tried.
  Known: OpenCode's `--standalone` server watches parent folders up to the home directory, which
  triggered macOS iCloud/Music prompts once (answer Don't Allow); `watcher.ignore` untested.
  `default_delegate` is still NOT turned on by any skill.

---

## v0.16.0 — 2026-09-30

- `ns-live-verify` **202609_06** — new scoped read helper `scripts/ns_read.py` (`whoami`, `query`,
  `record`) so a coding agent can be allowed to run ONLY this instead of raw `bsk`: mandatory
  identity gate, SELECT/WITH-only SQL validated before any browser call, Dev-Bridge-only endpoints,
  sandbox unless `--allow-prod-read`, own `bsk` session always stopped, never logs in or clicks.
  Drafted by the coding agent (≈ US$0.03, 25 iterations), then reviewed: I fixed three defects
  (numeric tab id, any-Suitelet path, the word "Notice" in real data read as a dead session), and
  live testing on a sandbox found two more the stubs had hidden (`bsk navigate` needs `--json`;
  the tester answers `{"success": false}` with no `error` key). 31 offline tests, each SQL defence
  layer and each guard mutation-checked. `cdp` engine not implemented.

---

## v0.15.4 — 2026-09-30

- `ns-record-write` **202609_11** — offline suite grows from 10 to 17 cases: it now checks what is
  actually sent to the write (record type and id, values, submit vs save, `--dynamic`, JSON
  escaping of a value with quotes and a backslash, the in-page account re-check, and that `bsk` and
  `cdp` send byte-identical JS), and that a failed write still counts as one attempt. Drafted by the
  coding agent (≈ US$0.008); I fixed one flaw in its test 18 (engine state leaked between the two
  runs, so the cdp run was not really cdp — found because a mutant survived). Mutation check: seven
  deliberate breaks of the helper (swapped type/id, dropped dynamic flag, ignored mode, dropped
  second value, removed account re-check, no escaping, cdp/bsk divergence) are each caught.

---

## v0.15.3 — 2026-09-30

- `ns-record-write` **202609_10** — adds `scripts/test_ns_write_offline.py`: 10 offline cases (no
  browser, network, `bsk` or `cdp`) for the helper's guards and exit codes, including the
  `--allow-bsk-prod` opt-in. Drafted by the coding agent (OpenCode on the company DeepSeek key,
  ≈ US$0.011), then reviewed line by line and mutation-checked: deliberately breaking the bsk
  production guard (both directions), the account guard, the dry-run guard and the exit-3 rule each
  makes at least one test fail. The tests do not check the values passed to the write.

---

## v0.15.2 — 2026-09-30

- `setup-coding-agent` **202609_02** + `agent_run.py` — OpenCode is now a supported worker
  (`--agent cline|opencode`, default = cline if present). The helper creates the worktree for it and
  parses its JSON (tokens summed from `step_finish`). Two real bugs found by testing and fixed:
  OpenCode takes its directory from `$PWD` (setting only `cwd=` made the agent work in the caller's
  directory), and it hung when stdin was an open pipe. New guard: warn if the source repo's status
  changes during a run. Documented that the tested machine's OpenCode config auto-approves every
  tool (`permission: "allow"`).

---

## v0.15.1 — 2026-09-30

- `setup-browser` **202609_03** — re-running is now an update, not a fresh setup: read the existing
  `browser.json` first, ask keep/change per key (default keep, ask only new or requested keys),
  verify instead of reinstalling, merge unknown keys, back up then write atomically (re-merge if
  another session changed the file), write nothing when nothing changed. Adds `schema: 1` to the
  file. Engine change never removes the other side automatically.

---

## v0.15.1 — 2026-09-30

- `cdp-browser` **202609_06** — concurrency soak recorded: 3 parallel bsk sessions, 30 min, 273 cycles,
  0 failures, no cross-talk, no stray dialogs, clean teardown (read-only, sandbox, one Mac).

---

## v0.15.0 — 2026-09-30

- **New skill `setup-coding-agent` 202609_01** — use Cline (or OpenCode, if that is what the machine
  has) as the worker for code/text edits so tokens burn on the company DeepSeek key, with Claude
  only briefing and reviewing. `scripts/agent_run.py` runs one task through `cline --worktree --json`
  in an isolated git worktree, stages the result into the worktree's own index, writes
  `changes.patch` (build junk excluded), prints tokens + an estimated USD, and stops — it never
  applies or deletes anything. Verified on one Mac: two scratch-repo runs (bug fixed, patch
  reviewed, applied, test passed, worktree removed; ~5–10 s, ≈ US$0.005 each) and the dirty-tree
  refusal. NOT verified: OpenCode (not installed), Cline hooks as a guard, a real customer repo.
  Honest limit recorded: Cline defaults to auto-approve, so the worktree isolates repo edits, not
  the machine; the guardrail preamble is advice, not enforcement.

---

## v0.14.5 — 2026-09-30

- `cdp-browser` **202609_05** — measured what the page-level dialog guard does NOT cover: it works
  on the top window only; a same-origin iframe's `confirm()` is still auto-accepted; a popup's
  dialog is not auto-accepted and hangs `bsk evaluate`/`session stop` until a human dismisses it;
  the guard is lost on navigation. Conclusion recorded: the guard is not a safety barrier, so no
  data-changing UI clicks on production through `bsk`; `ns_write.py` unaffected.

---

## v0.14.4 — 2026-09-30

- `ns-record-write` **202609_09** — docs only: mid-write transport failure verified live on a
  sandbox (a `bsk` shim triggers the failure; real `bsk`, real page). Session stopped before the
  write → exit 3, record unchanged. Reply lost after a real write → exit 3, record HAD changed,
  which is why exit 3 means "re-read, never re-run". Every test value was reverted.

---

## v0.14.3 — 2026-09-30

- `ns-record-write` **202609_08** — `--allow-bsk-prod` verified live once on a customer production
  account still in implementation: `--mode submit` on one free-text field, owner-approved record
  and value, dry-run → write → re-read → revert → re-read, final value identical, no dialog.
  Docs: custom-record `--type` must be the script id, not the URL's numeric `rectype`. Fix: the
  dry-run NOTE no longer says "use --engine cdp" as the only way (it mentions the flag).

---

## v0.14.2 — 2026-09-30

- `setup-global-instructions` **202609_03** — snapshot's "Browser automation" section matches
  `--allow-bsk-prod`: production writes through `bsk` only via `ns_write.py --allow-bsk-prod`
  (dry-run first, per-round approval, one record per call, exit 3 = stop), no UI clicks on
  production through `bsk`; lane priority added (bsk/cdp → Claude in Chrome → user acts) and the
  note that `cdp.py` cannot drive the everyday Chrome.

---

## v0.14.1 — 2026-09-30

- `setup-browser` **202609_02** — new "If auto mode blocks a step" section: stop, explain, and offer
  three choices (user adds the allow rule; user switches to Manual/Accept-edits; user switches mode
  and Claude edits the allow rules after showing the diff and a backup). Never change the mode or
  rules unasked, keep rules narrow, and a mode switch doesn't pre-approve a guardrail change.

---

## v0.14.0 — 2026-09-30

- `ns-record-write` **202609_07** + `ns_write.py` — new `--allow-bsk-prod`: `--confirm` through `bsk`
  on a non-sandbox account is still refused unless this flag is passed (dry-run first, the user
  approves the round, a WARNING line is printed). Acceptable because the in-page write is an
  `N/record` call that clicks nothing and opened no dialog in any live test; explicit because `bsk`
  auto-accepts any dialog that does appear. UI clicks on production stay off-limits for `bsk`.
  Offline suite is now 10 cases (3 new for the flag).
- `cdp-browser` **202609_04** — lane priority (1 bsk/cdp per machine, 2 Claude in Chrome, 3 the user
  acts on the screen); notes that `cdp.py` cannot drive the everyday Chrome (136+ ignores the debug
  port on the default profile); production wording updated.
- **New skill `setup-browser` 202609_01** — interactive per-machine setup: choose bsk or cdp
  (trade-off table), install (bsk: opens the Web Store page), optional Claude in Chrome, Dev Bridge
  trial (asks for the Home URL), login-click consent (never reads the password field); writes
  `~/.config/bombot-forge/browser.json` (no secrets, local only). Not yet run end to end on a clean
  machine.

---

## v0.13.3 — 2026-09-29

- `ns-record-write` **202609_06** — docs only: `--mode save --dynamic` through bsk verified live on a
  sandbox (write, revert, re-read). The test record has no sourcing-dependent fields, so it shows
  dynamic mode runs, not that field sourcing fires.

---

## v0.13.2 — 2026-09-29

- `ns-record-write` **202609_05** — docs only: `--mode save` through bsk verified live on a sandbox.

---

## v0.13.1 — 2026-09-29

- `ns-record-write` **202609_04** — docs only: records the first live `--confirm` write through bsk on a
  sandbox (page-rejected value → exit 1, nothing written; valid value → `WRITE ok`, AFTER matches,
  reverted and re-read). `--mode save` via bsk and a real mid-write transport failure remain
  unexercised.

---

## v0.13.0 — 2026-09-29

- `ns-record-write` **202609_03** + `ns_write.py` — new `--engine {auto,cdp,bsk}` with
  `--bsk-session` / `--bsk-tab` (the caller owns the session and pinned tab). The write logic that runs
  in the page is unchanged; only the transport is new (`bsk evaluate` awaits promises, so the
  result is polled in the page instead of from Python). New guards for bsk: a page-level dialog
  guard installed first (a dialog that still fires aborts); **`--confirm` refused unless the
  environment is `SANDBOX`** (team policy — bsk auto-accepts dialogs); and for **both** engines a
  transport failure or timeout *during* the write now exits `3` with "OUTCOME UNKNOWN — do not
  re-run blind" (previously a cdp timeout printed a plain failure). `CDP_SCRIPT` / `CDP_PORT` env
  overrides for the cdp path.
  - Verified live on the SB2 sandbox, **dry-run only** (nothing was written): account guard read
    `SANDBOX`, BEFORE read through `N/search`, wrong `--account` aborts, `auto` picks bsk, no dialogs.
  - Verified with offline stubs (7 cases): bsk on production refuses `--confirm` without calling
    the write; unknown-outcome exit 3 on bsk and cdp; page-side failure exit 1; success prints
    AFTER; cdp on production still allowed.
  - **Not exercised: a live `--confirm` write through bsk.** Do the first one on a throwaway
    sandbox record.
  - Found while testing: the helper needs a **record page** — the Home dashboard has no `require`
    (`require is not defined`); a currency record page does. Documented as a precondition.
  - `validate-setup.sh` now passes when either lane is usable (bsk or cdp) instead of requiring cdp.py.
- `cdp-browser` **202609_03** — soft deprecation, nothing removed: cdp is deprecated for
  read/QA only; it stays for production writes, UI-driven writes, `lens`/`netlog`/`stub`/`diff`,
  shadow DOM, unattended runs, and as the fallback whenever `bsk` is unusable on a machine
  (`BSK_AUTO_START=0 bsk status --json` fails, no extension, unsupported OS). Engine table now
  separates "`ns_write.py` (bsk on sandbox)" from "UI-driven writes (cdp)".
- `setup-global-instructions` **202609_02** — reference snapshot's "Browser automation" section
  re-captured (bsk default, cdp fallback, coordinator note), still redacted. The real
  `~/.claude/CLAUDE.md` on this machine got the same edit (backup kept alongside).

## v0.12.0 — 2026-09-29

- `cdp-browser` **202609_02** — now the engine-choice + recipes skill: **`bsk` (BrowserSkill,
  `Tencent/BrowserSkill`) is the default for read-only checks and QA; cdp stays for writes,
  dialog-sensitive work, `lens`/`netlog`/`stub`/`diff` and unattended/production.** Verified on an
  Apple Silicon Mac against the SB2 sandbox: install (arm64 build, checksum OK), daemon + extension
  connect, login via the autofilled `#login-submit`, identity gate (company + `SANDBOX`), Home read,
  session stopped with 0 left over.
  - Measured (bsk 0.3.1, Chrome 152; cdp side = throwaway headless Chrome for Testing, one process
    per command): `eval 1+1` **18 ms vs 409 ms** (n=10); screenshot 210 vs 709 ms (different
    browsers); `navigate` not comparable. On real NetSuite pages the page dominates (Home 14–19 s
    to `load`, 8.9 s to `domcontentloaded`) — the win is per-command overhead and not needing a second
    logged-in browser, not end-to-end speed.
  - Confirmed on macOS: **`bsk` auto-accepts `confirm()`** (`handled: accepted`, returned `true`);
    a page-level override returns `false` with no dialog — hence "writes stay on cdp".
  - New facts: `observe` is 18.6 KB on a one-paragraph page → cap with `--max-tokens`
    (2.6 KB on Home); `evaluate` awaits promises; console output includes other extensions'
    messages (filter `chrome-extension://`); Teibto's `flow-runner.py` pins bsk `0.3.0` and refuses
    `0.3.1`; upstream skill and daemon self-update unless `BSK_AUTO_UPDATE=off`.
  - Correction to 202609_01: it described `cdp.py newtab` as freely usable. On a shared NetSuite
    browser it is refused; the lane comes from `ns-session tab <compid>` after `ns-session bind`
    (a registry change for the session owner). `ns-session status` showed SB2 unbound on this Mac.
- `ns-live-verify` **202609_05** — adds Option A: run dbgQuery through `bsk evaluate` (awaits
  `fetch`, one command, 1.2 s for `whoami`, verified) instead of the two-call `window.__r` pattern;
  the cdp recipe stays as Option B.
- Not changed: `ns-record-write` (writes) and the global CLAUDE.md snapshot in
  `setup-global-instructions` still describe cdp-first.

## v0.11.2 — 2026-09-26

- New `docs/benchmarks/2026-09-26-local-models.md`: four more local Ollama models (`qwen3-coder:30b`,
  `glm-4.7-flash`, `qwen3:30b-a3b`, `deepseek-coder-v2:16b`) on the same prompt and rubric, run one
  at a time on the 12 GB GPU and graded blind next to two re-graded anchors from the 2026-09-25 run.
  Opus 5.5 re-scored 15 and `gpt-oss:20b` 3, so the grading scale held. All four new models scored
  0–1, so `gpt-oss:20b` stays pinned for `local-llm`. Long reasoning (4–5 min) didn't raise scores.
  The file also records that `teibto-main` / `teibto-alt` share weights with `qwen3-coder:30b` /
  `gpt-oss:20b` and differ only in a 64k context.
- README Benchmarks table gets the new row.

## v0.11.1 — 2026-09-25

- New `docs/benchmarks/2026-09-25-suitelet-5-models.md`: 5 models (Opus 5.5, Sonnet 5, Opus 4.8,
  teibto-worker, local-llm) on one Suitelet 2.1 coding task, with the same prompt, one shot,
  blind grading on an 8-criterion rubric, plus tokens, USD and time. Opus 5.5 won (15/16, $0.17).
  Both cheap workers produced code that would fail at runtime. The file records the method for
  re-runs, including the `claude -p --setting-sources ""` trick that removes ~10k hidden input
  tokens.
- `teibto-code` **202609_02**: cites the benchmark in its Gotchas.
- README gets a Benchmarks table; CLAUDE.md lists `docs/benchmarks/`.

## v0.11.0 — 2026-09-25

- `teibto-code` **202609_01** (new skill) — `/teibto-code <task>`: delegate a coding task to
  teibto-worker and verify before applying. Worth-it check (delegate only long mechanical output;
  ~20k-token worker overhead — measured: 23.7k haiku + 3.4k DeepSeek ≈ $0.004 / 28 s vs an Opus
  subagent 63.5k / 5 s, both correct), data check (customer data = ask every time; secrets never),
  attaches the repo's `docs/ai/teibto-worker-brief.md` (part above "For the caller" only), required
  `### Code / ### Where it goes / ### Assumptions` output, line-by-line verify (ids, limits,
  forbidden APIs, style, change header), Claude applies + syntax-checks + runs the project's test
  flow, report with the verbatim usage footer. Generalised from a NetSuite-repo prototype —
  project-specific rules stay in each repo's brief. Requested via the MFG session.
  - Live test: all 3 sections returned; an identifier it wasn't given came back as
    `/* TODO: confirm id */` + an Assumptions bullet (not invented). 95% of output tokens were
    reasoning.
- `teibto-worker` agent — may now draft code under `teibto-code` (caller verifies); coding tasks
  go in one call and the 3 sections are returned verbatim, never edited or split. Its old
  "not for correctness-critical code" line contradicted this flow and is replaced.
- `teibto-worker` skill **202609_02** — points code work to `/teibto-code`.

## v0.10.0 — 2026-09-25

- `setup-local-llm` **202609_01** (new skill) — per-machine setup for the default `local-llm`
  worker: Ollama on `bombot-gaming` over Tailscale, reached through the `ollama` MCP server.
  Ships canonical copies of the MCP script (`scripts/ollama_mcp_server.py`, stdlib only) and the
  agent (`reference/local-llm.agent.md`), the exact `claude mcp add` line, and a read-only
  PASS/FAIL checker (`scripts/check-local-llm.sh`: Tailscale, Ollama reachable, pinned model
  pulled, script + agent match canonical, MCP connected).
  - Why: the MCP script lived **only** in `~/.claude/mcp-servers/` on one machine, in no git repo.
    Now it's versioned and reproducible.
  - The agent copy sits in `reference/`, not `agents/`, so the plugin doesn't register a second
    `local-llm` beside the user-level one.
  - Docs use MagicDNS `bombot-gaming:11434` (verified reachable) instead of the tailnet IP.
  - Verified: ALL PASS on this machine; a simulated fresh machine flags exactly the 3 missing
    pieces.

## v0.9.0 — 2026-09-25

- **Renamed `cheap-worker` → `teibto-worker`** (agent) and `setup-cheap-worker` →
  **`setup-teibto-worker`** **202609_06** (skill folder moved; `ask_cheap.py` / `prices.json`
  unchanged). The name now says which worker it is: DeepSeek on the TEIBTO key.
- `teibto-worker` **202609_01** (new skill) — `/teibto-worker <task>` entry point: data check
  (never secrets; customer data only with explicit OK, else offer `local-llm`), delegate to the
  agent, relay the verbatim usage line, spot-check the answer.
- Separated from the user's existing local worker `local-llm` (Ollama — free, private). Both
  described the same kind of work, so a vague "use a cheap AI" could pick either; the
  `teibto-worker` description now defers to `local-llm` by default and is chosen when named or
  when local is unavailable/busy. `local-llm`'s own file (user-level, outside this repo) is untouched.

## v0.8.2 — 2026-09-25

- `setup-cheap-worker` **202609_05** — default key setup is now "open the key file in the
  user's editor" (Sublime, TextEdit fallback): Claude creates an empty template only if the file
  is missing, locks it to 600 and opens it; the user pastes + saves; Claude checks it's filled by
  **length only**. The hidden-prompt terminal command stays as the alternative. Verified the step
  never overwrites an existing key.
- `cheap-worker` agent — footer must paste each `[ask_cheap …]` usage line **verbatim** (full
  model id, `≈`, peak/off-peak label), plus a `total:` line when chunked. Found on the README
  summary run: the agent shortened `deepseek/deepseek-flash` to `deepseek-flash` and dropped
  `≈ peak`, even though the numbers were right.

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
