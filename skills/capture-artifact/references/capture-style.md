# Capture style — red boxes + explanation (reference for `capture-artifact`)

Why this exists: the reader of these packs is a non-developer stakeholder who looks at the picture and the label,
not at code or issue text. Each capture has to answer "what is this page" and "what changed, from what to what".

## What every capture must have

- **Red box** on exactly the spot that changed: 3px `#e11d1d`, radius 6, padded 4-8px so it never covers the text it
  frames. Box a whole column or row group, not single words.
- **Red label** (white bold 13-14px on `#e11d1d`) that says what changed, in the form `N - was X -> now Y`, not just
  "here". Put it outside the data: in a margin, over a dark header bar, or to the left of a modal. Never over table
  rows. Keep it inside the viewport.
- **Sharp images:** crop at 2x DPR. Never shrink a full 1710px viewport (a reader called that "not sharp"). For a
  narrow widget (portlet), set its container to about 380px wide in the page, screenshot, then crop the top-left at
  2x. No resampling.

## Two layouts

**A. Before -> after sheets** (use when "before" shots exist). One sheet per change:
number badge + title; a sub line quoting what the stakeholder asked; a white box with "**What this page is** ... .
**Change:** ..."; **before** (grey tag) -> **after** (green tag) images; a footer with account, environment + date,
issue, and where the before/after images came from.

**B. Numbered current-state pack** (use when nobody kept the old screens). Each shot = red boxes with number badges
plus one corner caption panel (kicker, title, a "was ..." sub line, a numbered list where item N = box N, each item
saying what changed and what it was before). Say in the README that there is no "before" and why.

Both: pack = `00` summary sheet (what the page is + numbered list of the changes) + `01...NN` one per change +
`README.md`.

**Keep "before" shots from now on.** Once a change is live the old screen cannot be re-shot. At every deploy's smoke
test, also screenshot the changed screens and copy them to `<DRIVE_BASE>/<PROJECT>/_shots/<module>/<YYYYMMDD-HHMM>/`
(or `.captures/_shots/<module>/<YYYYMMDD-HHMM>/` in `--local` mode). A "before" is only valid if it is the last deploy before
this change: check the folder's timestamp.
The scratchpad dies with the session, so it cannot hold "before" shots for another session.

## Technique

- **Capture:** `bsk screenshot --out <png>` writes a real file (so does `cdp.py shot`). The `claude-in-chrome`
  screenshot does not write a file to disk, so it cannot feed this workflow. Browser handling (own session, pinned
  tab, dialog guard, identity gate) is in `browser-engines`.
- **Overlay:** inject `scripts/annotate-overlay.js` with `bsk evaluate`, then per shot: scroll, `__A({...})`,
  screenshot.
- **Overlay failures seen:**
  - A box whose element is scrolled off-screen just disappears, and the numbering stops matching the panel.
  - Collapsed accordions must be opened first (a UI-only click: allowed; never press anything that writes).
  - The caption panel can cover the last box: move it (`pos:'tr'`).
  - A sticky header or summary dock hides about 60px at the top: scroll first.
  - Labels near the right edge or on full-width blocks get cut off: box a fixed width and put the label inside or below.
- **Cropping:** `sips -c H W --cropOffset y x` ignores the offset and crops from the centre (gives a blank image).
  Crop with PIL `Image.crop((l, t, r, b))`.
- **Sheets as local HTML:** lay the sheet out as a local HTML page (title, "what this page is", "change", before ->
  after). Draw the boxes over the "before" PNG as `%`-positioned divs so Thai labels render in the browser and no PIL
  font is needed. Serve with `python3 -m http.server`, then `bsk screenshot --full-page`. If the content is shorter
  than the viewport, measure the `.sheet` bottom x 2 before cropping, and never overwrite the only copy. In a modal,
  put labels in the side margin (max-width about 175px), not over table rows; clamp the label y to the viewport; a
  label-only anchor needs its border box hidden.
- **Look at every shot** as a small JPEG preview (about 1100px, `sips -s format jpeg -s formatOptions 65
  --resampleWidth 1100`) before keeping it. Box off-screen or hidden under a panel = re-shoot.

## Where it goes

1. **Drive, by local copy.** Google Drive desktop syncs a local folder, so `cp` from the shot folder is instant and
   costs zero tokens. Do **not** push images through the Drive MCP `create_file`: it takes inline content only, and a
   118 KB image cost more than 100K tokens just to read. Create the subfolder first, then `cp`. Name files
   `NN-<short title>.png`; keep the 2x originals.
2. **The decision-log artifact** the stakeholder reads: add the shots there (gallery recipe below) rather than a long
   Slack upload, which confuses the reader.
3. `SendUserFile` the `00` sheet so the user sees it in chat.

## Artifact gallery recipe

- Put the images **inside the artifact** with the publish `files` map (`{"img/s01.jpg": "<dir>/s01.jpg", ...}` +
  `root` = scratchpad). Do not link Drive images: a Drive share link opens a preview page, it does not render as
  `<img>`. Keep the Drive folder name as a footer line for the originals.
- Use the **2x originals** (about 3420px wide) -> JPEG q80 (about 400 KB each; 15 shots is about 5.8 MB, well under
  the 16 MB page limit). Set the `<img>` width/height attributes to the real size and use `loading="lazy"`.
- The gallery is `<section class="shots" id="shots">` after the status table, with a jump link. It is **wider than
  the reading column** so text inside the shots is readable without clicking:
  `.shots{align-self:center;width:min(76rem,calc(100vw - 32px))}` inside the flex-column wrapper (verified at
  1710px: 1216px vs 752px, no horizontal scroll).
- **Do not wrap the images in links.** Opening an artifact file in a new tab is blocked by claude.ai
  (`ERR_BLOCKED_BY_RESPONSE`). Phones pinch-zoom instead.
- Each shot is a `<figure>` with a `<figcaption>`: number, title, one line on what changed. Shot `00` is the summary
  sheet.
- A local `http.server` preview of the artifact HTML shows broken Thai because the file has no charset (the publish
  adds the skeleton). The published artifact renders fine.
