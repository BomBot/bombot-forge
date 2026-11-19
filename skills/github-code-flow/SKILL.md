---
name: github-code-flow
description: >-
  The team's end-to-end flow for changing code in a GitHub repo: issue first, branch, compare with the live
  target, edit, upload only after the user's OK, PR, then port to sandbox. Per-repo values (base branch, auth ids,
  deploy scope, files never to touch) live in a per-machine config inside `.git/`, asked once and checked every run.
  Invoked by the user only (`/bombot-forge:github-code-flow`).
disable-model-invocation: true
---

# GitHub code flow

**Skill version: `202611_01`**

One flow for every repo; what differs between repos sits in a config file that never leaves the machine.
Argument (optional): `$ARGUMENTS` - the issue number, the symptom, or a Slack/issue link to start from.

## Iron rules

- **Every write to a live account (file:upload, deploy) waits for the user's OK for that round.** Show the plan
  first: files, the compare result from step 3, the auth id and host it will go to, how you will smoke-test.
- **Never full `project:deploy`, never a wildcard in `deploy.xml`.** `.js` goes up with `file:upload`; report it as
  "uploaded".
- **Target differs from git → stop.** Report, merge what the target has into git first, never overwrite it.
- **Config values are facts to check, not trust.** An auth id or branch in the config that no longer exists means stop
  and ask, never guess a replacement.
- **Never store or print a secret** in the config (auth ids only; tokens and passwords stay in the SuiteCloud store).
- Delete, revert, force-push and merging someone else's PR need the user's OK for that round.

## Step 0 - Load or create the config

Config path (shared by every worktree of the repo, never committed because it is inside `.git`):

```bash
CFG="$(git rev-parse --path-format=absolute --git-common-dir)/bombot-forge/github-flow.json"
```

Not inside a git repo → stop and say so.

### 0a. Found → check it, then tell the session

1. Read the JSON. Re-check what can be checked, all read-only:
   - `base_branch` exists: `git ls-remote --heads origin <base_branch>`.
   - Each `auth.*` id is in `suitecloud account:manageauth --list` (SDF repos).
   - `deploy_scope` folders still exist in the tree.
2. Anything failed → show what failed and ask for the new value; save it only after the user picks it.
3. All good → tell the session in a short list: repo kind, base branch, prod and sandbox auth ids with host, deploy
   scope, files never to touch, issue label scheme. Then go to step 1.
4. Do not copy the config into memory: the file is the single source. Memory keeps only lessons (an error and its
   cause), per the user's memory rules.

### 0b. Not found → "not set up on this machine yet"

Missing does not mean a new project (a fresh clone or another machine looks the same). Detect first, ask only what
is left, one `AskUserQuestion` per decision, detected value as the first option:

| Key | Detect from | Ask when |
|---|---|---|
| `author` | `git config user.name` / `user.email` | either is empty |
| `kind` | `suitecloud.config.js` or `src/manifest.xml` present → `sdf`, else `plain` | always confirm |
| `base_branch` | the repo's `CLAUDE.md`, then `gh repo view --json defaultBranchRef` | always confirm (a repo may keep live code on a non-default branch) |
| `auth.prod` | `defaultAuthId` in `project.json` + `suitecloud account:manageauth --list` | `sdf`; pick from the list, never type |
| `auth.sandbox` | same list | `sdf`; "none" is a valid answer |
| `deploy_scope` | the repo's `CLAUDE.md` / deploy playbook | not written there |
| `never_touch` | the repo's `CLAUDE.md` (mirror-only files, data files, settings) | not written there; "none" is valid |
| `labels` | `gh label list` | no type/area/priority labels found |
| `issue_repo` | `gh repo view --json nameWithOwner` | never (detected) |

Show the whole JSON, wait for OK, then write it:

```json
{
  "version": 1,
  "kind": "sdf",
  "issue_repo": "<owner>/<repo>",
  "base_branch": "<branch>",
  "author": { "name": "<git user.name>", "email": "<git user.email>" },
  "auth": { "prod": "<auth id>", "prod_host": "<host>", "sandbox": "<auth id or null>", "sandbox_host": "<host or null>" },
  "deploy_scope": ["<folder>"],
  "never_touch": ["<path or glob>"],
  "auto": false,
  "labels": { "type": ["bug", "enhancement", "chore"], "area_prefix": "area:", "priority_prefix": "priority:" },
  "updated": "<YYYY-MM-DD>"
}
```

The repo's own `CLAUDE.md` wins over this config when they disagree: say which value differs and ask.

### 0c. Offer: use this flow automatically in this repo

Ask once (`AskUserQuestion`, "no" is fine) whether every session in this repo should follow this flow without the
slash command. Yes →

1. `git check-ignore -q CLAUDE.local.md` fails → add `CLAUDE.local.md` to `.git/info/exclude` (local only; never
   edit the repo's `.gitignore`, that would need a commit).
2. Append to the repo's `CLAUDE.local.md` (show the line, wait for OK):
   `- ก่อนแก้โค้ดใน repo นี้ ให้ทำตาม skill bombot-forge:github-code-flow (เรียกด้วย Skill tool ถ้าเรียกไม่ได้ ให้อ่าน ~/.claude/plugins/cache/bombot-forge/bombot-forge/<version>/skills/github-code-flow/SKILL.md โดยดู <version> จาก claude plugin list)`
3. Record `"auto": true` in the config. Turning it off = delete that line and set `"auto": false`.

`CLAUDE.local.md` is untracked, so a session opened directly in a worktree folder does not load it; the flow itself
still works there (the config is in `.git`).

## Step 1 - Issue before code

- Search first: `gh issue list --repo <issue_repo> --state all --search "<words from the symptom>"`. Same problem →
  use that issue.
- None → open one. Title `[Bug|Enhancement|Chore][Area] short summary`; one type label + `area:*` + `priority:*`
  (+ `source:slack` when it came from Slack). Body: the request in the requester's own words with the link, facts
  verified, assumptions marked as such, acceptance criteria, files to touch.
- Assign yourself (`--assignee @me`), tell the user the issue number.

## Step 2 - Branch

- `git fetch`, then branch from `origin/<base_branch>`: `fix/<issue>-<slug>` or `feat/<issue>-<slug>`.
- Another session working in the same tree → `git worktree add` (the config is shared, nothing to redo).

## Step 3 - Compare with the live target before editing (`sdf` only)

- `suitecloud file:import --paths "<file cabinet path>" --excludeproperties` (uses `auth.prod`; see the auth-swap
  note in step 7 if `defaultAuthId` is not prod), then `git diff` that file.
- Differs → stop, report, merge the target's part into git first.

## Step 4 - Edit

- Only what the issue needs; keep the file's style. Touching a path in `never_touch` or outside `deploy_scope` → ask.
- `@change` header at the top in the user's format, with `(#<issue>)` on the detail line, author from the config.
- No hardcoded internal ids outside the repo's config/lib file when the repo has one.
- New logic → a small test or self-check where the repo keeps them.
- Commit messages reference `(#<issue>)`.

## Step 5 - Upload to prod (`sdf` only, after OK)

- Plan → OK → `suitecloud file:upload --paths "<path>"`.
- Objects: a scoped `deploy.xml` + trimmed `manifest.xml`, `project:validate --server` first, restore both files right
  after; never commit them.
- Verify: import the file back and compare `shasum` with git. Smoke-test the real page right away.

## Step 6 - PR and merge

- Push, `gh pr create --base <base_branch>`; body has `Fixes #<n>` (bug) or `Closes #<n>`, plus the upload and
  smoke-test results.
- Stop after the PR and wait: squash-merge only when the user says so (never on your own after a passing
  smoke-test); then `gh pr view <n> --json state` must say `MERGED`. Comment the outcome on the
  issue.

## Step 7 - Port to sandbox (`sdf`, `auth.sandbox` set, after step 6)

- `file:import` / `file:upload` take no `--authid`: swap `defaultAuthId` in `project.json` and restore it in the same
  shell block with `trap`. Never commit the swapped file.
- Import from the sandbox and compare first; it may differ from prod. Sandbox has something prod lacks → stop, report.
- Internal ids the file uses must match on the sandbox; different → stop, never change git away from prod.
- Files only (`file:upload`). Never deploy objects to a sandbox; new fields or objects are made in the UI.
- Smoke-test, then comment "ported to sandbox <date>" on the issue.

## Repo kind `plain`

Steps 1, 2, 4 and 6 only.

## Status

202611_01 (2026-11-19): draft distilled from one team repo's working prompt with every account-specific value moved
into the config. Not run end to end. Not verified: `--path-format=absolute` on the Git for Windows build the team
uses, `disable-model-invocation` hiding the skill from automatic use (seen in other plugins' skills, not tested here),
and whether the `CLAUDE.local.md` line (step 0c) can call the skill through the Skill tool or falls back to reading the file.
