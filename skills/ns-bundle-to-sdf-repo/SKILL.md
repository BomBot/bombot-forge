---
name: ns-bundle-to-sdf-repo
description: >-
  Use when turning an existing NetSuite bundle (account-owned, "Convert to SDF Project"
  available on its Bundle Details page) into a version-controlled SDF repo — extracting the
  conversion zip, cleaning up legacy auto-generated scriptids, wiring the repo so a future
  `file:upload`/deploy still lands on the bundle's real live paths, and scaffolding it as a
  Teibto standards repo.
---

# NetSuite Bundle → SDF Repo (Convert to SDF Project)

**Skill version: `202609_02`**

Turns a live, account-owned bundle into a proper git repo without breaking its ability to
sync back to the account it came from. Distilled from converting one of TEIBTO's own bundles
on `4089685-sb2`/`4089685-sb1` into a private Teibto standards repo.

## Iron rules (do not soften)

- **Never rename paths under the extracted `FileCabinet/`** — those paths are the *live*
  File Cabinet location. Rename them in the repo and a future `file:upload` creates a new
  sibling path instead of updating the file that's actually deployed. Objects/ folder layout
  inside the SDF project is free to reorganize (SDF deploys objects by scriptid, not by file
  path in the project).
- **Don't rewrite legacy code to satisfy the current lint config.** Pre-2021 SuiteScript
  fails rules that didn't exist yet (`no-undef` on the SS2.0 global `log`, `no-redeclare`,
  `no-extra-boolean-cast`, `no-useless-escape`, `no-regex-spaces`, `valid-typeof` are the ones
  seen so far). Scope an ESLint override to the migrated folder instead, and record it as an
  opt-out (reason + approver + date) in README — don't touch the code to go green.
- **Verify the conversion zip is fresh before trusting it** — re-check the File Cabinet file's
  size/timestamp after a short wait; NetSuite's own confirm dialog says conversion "can take
  some time." A stale zip from a previous conversion looks identical at a glance.
- **Renaming a legacy scriptid on a bundle's *release* account (installs > 0) needs an
  explicit go-ahead**, separate from the dev/test account (installs = 0). Check
  "No. Installs" and "Availability" on the Bundle Details page for both accounts before
  touching the release one — it's the one other accounts may pull updates from.

## Flow

1. **Find the bundle** — Bundle Details page (`bundledetails.nl?id=<bundleid>`), reached from
   `bundlelist.nl` or by grepping the bundle's components for a known object. Read Overview
   (Company, Availability, No. Installs, Available Since) and Components (object/file list —
   note: the conversion often pulls in an extra dependency not shown here, e.g. a form).
2. **Convert to SDF Project** — button on Bundle Details. Confirm the dialog (mentions results
   land in `File Cabinet > SuiteBundles > SDF_Conversions`). This is async — the button click
   returns immediately; the file appears after some seconds.
3. **Fetch the zip** — browse to `SuiteBundles/SDF_Conversions/` (see Gotchas for the folder-
   click quirk), find `sdf_conversion_<bundleid>.zip`, re-check its timestamp is fresh (§ Iron
   rules), then use its row's **Download** link — that URL is signed
   (`core/media/media.nl?...&h=<hash>&...`) and downloadable with a plain `curl`, no session
   cookie needed.
4. **Inspect before trusting** — unzip, read `status.xml` (`totalimportedcount`, `warningcount`,
   the closing `<summary>` line) and diff the file list against what the Components tab showed;
   the extra items are real dependencies (e.g. the record's entry form), not junk.
5. **Clean up legacy scriptids** *(optional, only if asked)* — see the dedicated section below.
   Do this **before** copying `Objects/*.xml` into the repo, then `object:import` the renamed
   object fresh instead of hand-editing the extracted XML (the file's own `scriptid=` attribute
   needs to change too, and a fresh import guarantees it matches live state).
6. **Lay out the repo** (Variant A NetSuite SDF, per `teibto-dev-standards`
   REPO-SETUP-PLAYBOOK.md): `src/FileCabinet/<exact live path>/...` verbatim,
   `src/Objects/<kebab-slice-name>/*.xml` grouped however's readable.
7. **`npm install` for the shared ESLint package** — see Gotchas for the package-registry auth
   and version-pin traps.
8. **Scaffold, secret-scan, commit, tag, push** per the standard playbook flow — nothing
   bundle-specific here.

## Renaming a legacy auto-generated scriptid (Change ID)

Pre-2021 objects sometimes have IDs like `custform_224_4089685_sb2_387` — NetSuite
auto-generated, sometimes even embedding a *different* account's id (a copy-across-accounts
artifact). NetSuite has a built-in, non-destructive rename:

1. Open the object's edit page, click **Change ID** (present on custom forms; the button's
   `onclick` reveals the real URL, e.g. `custentryformchangeid.nl?formid=<id>` — don't guess
   this URL pattern, read it off the button).
2. The page shows **Old ID** and a **New ID** field. The "New ID" field is the *suffix only* —
   the object-type prefix (`custform`, `customrecord`, …) is a **separate, fixed, non-editable
   label** shown next to it. **Type the leading underscore yourself**
   (`_thl_custombtnconfig`), or the result mis-joins into `custformthl_custombtnconfig` (no
   underscore) — this is silent, no validation error, only visible by re-checking the ID on
   the object's edit page after Save.
3. **If the New ID field won't take keyboard input on some account** (worked fine on one
   account, silently rejected on another; `el.value` reads back empty right after typing, and
   clicking Save does nothing — no error, page just stays on the change-id URL): the field has
   a separate `isvalid` flag the framework checks before allowing submit, which a real
   `change`/`blur` cycle sets and a plain keystroke sequence sometimes doesn't reach in time.
   Fix:
   ```js
   const el = document.getElementById('newid');
   el.focus(); el.value = '_your_suffix';
   el.dispatchEvent(new Event('change', {bubbles:true, cancelable:true}));
   el.blur();
   // confirm before clicking Save:
   el.isvalid === true
   ```
4. **Verify by URL, not by page text.** Clicking Save redirects to the object's edit page on
   success (`custentryform.nl?...`) and stays on `custentryformchangeid.nl?...` on failure —
   check `cdp.py url`. The "New ID / custform" label text is unchanged either way (it's the
   static prefix label, not a live preview) — reading it proves nothing.
5. **Same object may exist on more than one account** if the bundle was published from one
   account (its "release" copy — Availability: Shared, No. Installs > 0) and developed on
   another (dev copy, Availability: Private, No. Installs: 0). The legacy ID is often identical
   on both (it travels with the bundle). Fix both, independently — the tool call in step 1-4 is
   per-account, there's no bulk apply.

## Gotchas

- **A File Cabinet folder row's click handler is `showFolderContents(<id>)` (AJAX), not a
  normal link.** `nav`-ing straight to the row's `href` lands on that folder's *properties/edit*
  page instead of its contents list. Call the JS function directly:
  `cdp.py eval "(() => { showFolderContents(<id>); return 'ok'; })()"`.
- **Classic NetSuite top-nav megamenus (Customization, Setup, …) render their submenu items
  via AJAX only after the menu is opened** — querying the DOM for a menu link right after page
  load finds nothing. Use `cdp.py a11y "<menu label>"` to get a clickable ref, click it, then
  `a11y` again for the next level down; read the real target off the resulting link's
  `onclick`/`loadrightpane(...)` rather than guessing `*.nl` URLs — guessed URLs (`custrecordtype.nl`,
  `custrecordtypes.nl`, `custrecords.nl` vs `custrecordindexlist.nl`, etc.) are wrong more often
  than right and 404 silently informative but slow.
- **`@teibto/eslint-config-suitescript` needs `read:packages`** on whatever token
  `NODE_AUTH_TOKEN` resolves to. `gh auth token` alone is usually missing that scope —
  `gh auth refresh -h github.com -s read:packages` adds it (device-flow: prints a one-time
  code + URL, needs a human to open it in a browser; the command hangs until they do — don't
  block silently on it, surface the code/URL and continue other work while it waits).
- **The package's latest published version can lag the `teibto-dev-standards` repo's latest
  git tag.** Don't assume `^<latest-tag>` resolves — `npm view @teibto/eslint-config-suitescript
  versions --json` and pin to the actual latest published one, or `npm install` fails
  `ETARGET`.
- **A workflow with only `push: {tags: [...]}` + `pull_request` triggers (no plain branch-push
  trigger) does not fire on the push that first introduces the workflow file** — this is a
  general GitHub Actions first-discovery quirk, not specific to tags. If the first tag push
  (bundled with the initial `main` push) shows no run in `gh run list`, delete and re-push just
  the tag (`git push --delete origin vX.Y.Z && git push origin vX.Y.Z`) — now that the workflow
  is discoverable on the default branch, the tag push triggers normally.
- **`gh api -X PATCH/PUT` with `-f`/`-F` flags flattens nested JSON to strings**, which fails
  schema validation on endpoints with nested objects (e.g. branch protection's
  `required_status_checks.strict` needs a real boolean). Write the payload to a JSON file and
  pass `--input file.json` instead of stacking `-f`/`-F`.
- **Secret scanning (GitHub Advanced Security) can be locked at the org's plan/billing level**
  (`"Secret scanning cannot be enabled due to a lock on metered usage"`) even though the repo
  API call looks like it should just work. Not a config mistake — record it as a plan fallback
  in README (which gate is GitHub-enforced vs which is enforced by `scripts/secret-scan.sh` in
  CI as mitigation) rather than retrying the API call.

## Quick reference

| Need | Where |
|---|---|
| Trigger conversion | Bundle Details page → **Convert to SDF Project** button |
| Find the output zip | File Cabinet → `SuiteBundles/SDF_Conversions/sdf_conversion_<bundleid>.zip` |
| Download without a session | the row's **Download** link — signed URL, plain `curl` works |
| Rename a legacy scriptid | object's edit page → **Change ID** button → read its real `onclick` URL |
| Check available package versions | `npm view @teibto/eslint-config-suitescript versions --json` |
| Add missing token scope | `gh auth refresh -h github.com -s read:packages` |
| Branch-protection API with nested fields | write JSON file, `gh api ... --input file.json` |

## Status

v0.1 draft — one conversion so far (own `4089685-sb2`/`sb1` accounts). Not yet pressure-tested per
`superpowers:writing-skills`. Things likely to need a second data point before trusting as
general: whether *every* legacy custom-object type exposes a "Change ID" button the same way
(only tested on a custom form so far), and whether the `isvalid`-flag workaround generalizes
to other change-id-style pages or was specific to that one account's page render.
