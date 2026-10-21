---
name: capture-artifact
description: >-
  Use when the user types /capture-artifact (or says "capture red boxes into the artifact", "capture กรอบแดง ใส่
  artifact", "capture แต่รูป") after a deploy: capture every changed screen from the live environment with red boxes +
  explanation, then either keep the pack only in the project (`--local`, kept out of git on this machine) or save it in
  a new Google Drive subfolder with a README, add it as a wide gallery to the decision-log artifact, and draft the Slack
  summary in chat for the user to review. Manual only.
disable-model-invocation: true
---

# capture-artifact

**Skill version: `202610_03`**

Turns "what we just deployed" into red-boxed screenshots with captions. Slash command: `/bombot-forge:capture-artifact`.

Argument (optional): `$ARGUMENTS` - `--local` and/or an issue number, module name, or the artifact URL to add the images
to. Without one, use what was deployed in this session and that work's decision-log artifact. If neither can be found,
ask the user one question.

## Modes

| | full (default) | `--local` ("capture แต่รูป") |
|---|---|---|
| Plan, capture, red boxes, shot `00` | yes | yes |
| Save in `<project>/.captures/<YYYYMMDD>-<module>-<issue>/` + `README.md` | no | yes (kept out of git, see step 4) |
| Drive subfolder + README | yes | no |
| Decision-log artifact gallery | yes | no |
| Slack draft | yes, if there is a thread (step 6) | no |

After a `--local` run, offer to publish later (Drive + artifact + Slack) from the shots already saved; do not re-shoot
unless they are stale.

## Prerequisites (check first, stop if one fails)

- **`bsk` installed and answering** - `BSK_AUTO_START=0 bsk status --json`. This skill needs it: no fallback to `cdp` or
  Claude in Chrome (Claude in Chrome cannot write a screenshot file to disk). If it fails, stop and tell the user to run
  `/bombot-forge:setup-browser`.
- Full mode only: **`<DRIVE_BASE>` exists** (`test -d`). If Google Drive is not mounted, `mkdir -p` would create a plain
  local folder that never syncs and nothing would warn. Stop and say so.

## Inputs to settle first (ask once if missing, do not guess)

| Input | Where it comes from |
|---|---|
| `<DRIVE_BASE>` - local Google Drive sync folder for AI material (full mode) | the project's `CLAUDE.local.md` or memory; else ask. Looks like `~/Library/CloudStorage/GoogleDrive-<account>/My Drive/<folder>/` |
| `<PROJECT>` - the project's subfolder under it (full mode) | same; else ask |
| Decision-log artifact URL (full mode) | `$ARGUMENTS`, the work's earlier artifact, or ask. If it cannot be found, ask: never create a new one silently |
| Slack thread (optional) | the user, or the thread the work was raised in. **No thread is a valid case** (step 6) |

## Steps

1. **Method.** Read `references/capture-style.md` (layouts, overlay technique, Drive and gallery rules) and follow it.
   If the project keeps its own style note in memory, that overrides it where they differ.
2. **Capture plan - confirm before shooting.** Build a numbered list of the screens to capture from the issue and what was
   deployed in this session (page, section, what changed: was -> now). Show it and wait for the user's OK. State which
   environment it is (production or sandbox); the footer of every sheet carries account, environment and date, and a
   sandbox shot is never labelled PROD.
3. **Capture (live environment, read-only).** Tell the user in one line what you are about to open with `bsk` and where;
   use your own session and pinned tab, run the identity gate, close your session when done (see `browser-engines`). If
   the session expired mid-run, follow the global auto-login rule (check `:-webkit-autofill`, click Login, never type a
   credential). Shoot with `scripts/annotate-overlay.js`.
   - "Before" shots exist (`_shots/<module>/...` in the Drive project folder or in `.captures/_shots/`, or an older
     pack) -> layout A, before -> after. **Check the folder's timestamp**: a "before" from a different deploy than the
     one just before this change is wrong; say where each "before" came from in the sheet footer.
   - None -> layout B, current state with numbered boxes; say in the README why there is no "before".
   - Every box is numbered; item N in the caption = box N; each item says "was -> now".
   - Preview every shot as a ~1100px JPEG before keeping it. Box off-screen or hidden = re-shoot.
   - Look at each preview for data that is not needed to show the change (other customers' names, prices, personal
     data). If found, tell the user and ask: mask it, pick another view, or keep it.
   - Shot `00` = one summary page with every change.
   - If the round's screens were not saved yet, also copy the after-deploy shots to `_shots/<module>/<YYYYMMDD-HHMM>/`
     (Drive in full mode, `.captures/_shots/` in `--local`) as next round's "before".
4. **Save.**
   - **`--local`:** folder `<project root>/.captures/<YYYYMMDD>-<module>-<issue>/` (project root = `git rev-parse
     --show-toplevel`, else the working directory), files `NN-<short title>.png`, 2x, unshrunk, plus a `README.md`
     (file, page/section, what changed, was -> now). **Keep it out of git on this machine without touching the
     project's `.gitignore`:**
     ```bash
     EXC=$(git rev-parse --git-path info/exclude)      # works in a worktree too
     grep -qxF '.captures/' "$EXC" || echo '.captures/' >> "$EXC"
     git check-ignore -q .captures/x || echo "NOT IGNORED"
     ```
     This is a convenience, not a gate: if it reports `NOT IGNORED` (not a git repo, or files under it are already
     tracked), say so in one line and **carry on capturing**. `info/exclude` stays on this machine only. Also say if the
     project folder sits inside a cloud-synced folder (git ignore does not stop that sync).
   - **full:** create `<DRIVE_BASE>/<PROJECT>/<YYYYMMDD>-<Module>-<issue>-<slug>/` first, then `cp` the files in (never
     read base64 into context, never use the Drive MCP for images). Files `NN-<short title>.png`, 2x, unshrunk. Write
     `README.md` with a table: file, page/section, what the stakeholder asked (quote the Slack words if there is a thread;
     else the issue text, else `-`, never invent a quote), what it was changed to, artifact link.
   - **Folder exists already** (same day, same slug): do not overwrite; add a `-2`, `-3` suffix.
5. **Artifact (full mode).** Read the decision-log artifact first, then publish over the same URL (never a new one) with
   the shots as `files` (`img/sNN.jpg`, JPEG q80 from the 2x). Add `section.shots` after the status table, wider than the
   reading column, `<figure>` + `<figcaption>`. No links around images; no Drive image links. Update the status table /
   decision log for this round on the same page if not done yet. Page limit is 16 MB (about 30 shots at ~400 KB): above
   that, lower the JPEG quality or split the gallery.
6. **Slack draft (full mode) - never send yourself.** Follow the Slack rules in the user's global `~/.claude/CLAUDE.md`
   (section "Slack / การสื่อสารกับทีม"); the points that matter here:
   - **No thread:** skip the reply. Ask once whether the user wants a standalone message drafted (for a channel or DM
     they name; never pick one yourself). If yes, draft it the same way, with the link line reading "no thread -
     target: <what the user said>".
   - With a thread: before drafting, re-read it, including messages that arrived after the work. If a new message
     contradicts what was done, or more work is needed first, **tell the user and ask; do not draft yet**.
   - Show the **Slack link of the thread you would reply in**, above the draft.
   - The draft goes **in chat as a code block**, written as a blockquote: every line starts with `> ` (a lone `>` for a
     blank line, never an empty line), bullets as `> • ...`. Do not use the Slack draft tool. Wait for the OK.
   - Reader is a manager: business language, no field ids, SQL, file names or function names. One summary line, then as
     many bullets as the content needs (one point per bullet): what changed (in words the user sees on screen), the key
     number now, the artifact link and that the pictures are in its screenshots section, and any open decision as
     lettered options (a / b / c).
   - Tell the user which questions they should answer or propose themselves.
   - Only after the OK: send in the work's existing thread and give the message link.
7. **Close.** Tell the user where the pack is (`.captures/...` path, or the Drive folder + artifact URL with version) and
   `SendUserFile` shot `00`. If you found a new trick or trap, update the project's existing style note in memory (or
   tell the user it belongs in `references/capture-style.md`) rather than creating a duplicate. End the reply per the
   global rule (checked / inferred / not looked at, then one "next step" line).

## Guardrails

- The live-environment capture is read-only on data. UI-only clicks are fine (expand an accordion, switch a tab, scroll,
  close a panel). Never submit, save, delete or press anything that writes. Any dialog that appears = stop and report.
- Drafting is not sending: nothing goes to Slack, email, or anyone else until the user says OK in this chat.
- Customer names, record ids and account numbers stay in the user's own Drive/artifact/`.captures`; none of that belongs
  in this repo.
