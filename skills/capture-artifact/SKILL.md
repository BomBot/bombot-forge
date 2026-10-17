---
name: capture-artifact
description: >-
  Use when the user types /capture-artifact (or says "capture red boxes into the artifact", "capture กรอบแดง ใส่
  artifact") after a deploy: capture every changed screen from the live environment with red boxes + explanation,
  save the pack in a new Google Drive subfolder with a README, add it as a wide gallery to the decision-log artifact,
  then draft the Slack summary in chat for the user to review. Manual only.
disable-model-invocation: true
---

# capture-artifact

**Skill version: `202610_02`**

Turns "what we just deployed" into red-boxed screenshots with captions, put in Drive and in the artifact the
stakeholder reads, plus a Slack summary **drafted for the user to approve**. Slash command: `/bombot-forge:capture-artifact`.

Argument (optional): `$ARGUMENTS` - an issue number, module name, or the artifact URL to add the images to. Without
one, use what was deployed in this session and that work's decision-log artifact. If neither can be found, ask the
user one question.

## Inputs to settle first (ask once if missing, do not guess)

| Input | Where it comes from |
|---|---|
| `<DRIVE_BASE>` - local Google Drive sync folder for AI material | the project's `CLAUDE.local.md` or memory; else ask. Looks like `~/Library/CloudStorage/GoogleDrive-<account>/My Drive/<folder>/` |
| `<PROJECT>` - the project's subfolder under it | same; else ask |
| Slack recipient and thread | the user, or the thread the work was raised in |

## Steps

1. **Method.** Read `references/capture-style.md` (layouts, overlay technique, Drive and gallery rules) and follow it.
   If the project keeps its own style note in memory, that overrides it where they differ.
2. **Capture (live environment, read-only).** Tell the user in one line what you are about to open with `bsk` and
   where; use your own session and pinned tab, run the identity gate, close your session when done (see
   `browser-engines`). Capture every changed spot of this round with `scripts/annotate-overlay.js`.
   - "Before" shots exist (`<DRIVE_BASE>/<PROJECT>/_shots/...` or an older pack) -> layout A, before -> after.
   - None -> layout B, current state with numbered boxes; say in the README why there is no "before".
   - Every box is numbered; item N in the caption = box N; each item says "was -> now".
   - Preview every shot as a ~1100px JPEG before keeping it. Box off-screen or hidden = re-shoot.
   - Shot `00` = one summary page with every change.
   - If the round's screens were not saved yet, also copy the after-deploy shots to
     `_shots/<module>/<YYYYMMDD-HHMM>/` as next round's "before".
3. **Drive.** Create `<DRIVE_BASE>/<PROJECT>/<YYYYMMDD>-<Module>-<issue>-<slug>/` first, then `cp` the files in
   (never read base64 into context, never use the Drive MCP for images). Files `NN-<short title>.png`, 2x, unshrunk.
   Write `README.md` with a table: file, page/section, what the stakeholder asked (quote the Slack words), what it
   was changed to, artifact link.
4. **Artifact.** Read the decision-log artifact first, then publish over the same URL (never a new one) with the
   shots as `files` (`img/sNN.jpg`, JPEG q80 from the 2x). Add `section.shots` after the status table, wider than the
   reading column, `<figure>` + `<figcaption>`. No links around images; no Drive image links. Update the status
   table / decision log for this round on the same page if not done yet.
5. **Slack draft - never send yourself.** Follow the Slack rules in the user's global `~/.claude/CLAUDE.md`
   (section "Slack / การสื่อสารกับทีม"); the points that matter here:
   - Before drafting, re-read the thread, including messages that arrived after the work. If a new message
     contradicts what was done, or more work is needed first, **tell the user and ask; do not draft yet**.
   - Show the **Slack link of the thread you would reply in**, above the draft.
   - The draft goes **in chat as a code block**, written as a blockquote: every line starts with `> ` (a lone `>`
     for a blank line, never an empty line), bullets as `> • ...`. Do not use the Slack draft tool. Wait for the OK.
   - Reader is a manager: business language, no field ids, SQL, file names or function names. One summary line,
     then as many bullets as the content needs (one point per bullet): what changed (in words the user sees on
     screen), the key number now, the artifact link and that the pictures are in its screenshots section, and any
     open decision as lettered options (a / b / c).
   - Tell the user which questions they should answer or propose themselves.
   - Only after the OK: send in the work's existing thread and give the message link.
6. **Close.** Tell the user the Drive folder, the artifact URL (version), and `SendUserFile` shot `00`. If you found
   a new trick or trap, update the project's existing style note in memory (or tell the user it belongs in
   `references/capture-style.md`) rather than creating a duplicate.
   End the reply per the global rule (checked / inferred / not looked at, then one "next step" line).

## Guardrails

- The live-environment capture is read-only: overlay injection changes the DOM only; do not click, submit, or save.
- Drafting is not sending: nothing goes to Slack, email, or anyone else until the user says OK in this chat.
- Customer names, record ids and account numbers stay in the user's own Drive/artifact; none of that belongs in this repo.
