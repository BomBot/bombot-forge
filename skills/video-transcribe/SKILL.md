---
name: video-transcribe
description: >-
  Use when transcribing a video or audio file to text (SRT with timestamps, plain TXT, and a
  cleaned Markdown) via the homelab `bombot` MCP server — a Tailscale bridge to a Windows GPU
  box (`bombot-gaming`) running ffmpeg + faster-whisper. Covers the prereq check, scp-to-inbox
  → verify-size → `transcribe_video` → scp-results-back flow, the sync-call wait warning, and
  the SSH job-object gotcha.
---

# Video Transcribe (homelab bombot MCP)

**Skill version: `202609_01`**

Transcribe a local video/audio file by handing it to the `bombot` MCP server, a
Tailscale-tunnelled bridge to a Windows machine (`bombot-gaming`) that has ffmpeg +
faster-whisper on GPU. The MCP tool does the whisper run and doc cleanup; this skill is the
**file-shuffling + verification discipline** around it (get the file there intact, wait for the
sync call, bring the results back). Distilled from real runs, not theory.

- MCP server: `bombot` (repo `homelab-mcp` at `/Users/bombot/WebstormProjects/Tools/homelab-mcp/`)
- Relevant tools: `mcp__bombot__transcribe_video`, `mcp__bombot__list_transcribe_inbox`
- Windows box: user `pradc` @ `bombot-gaming`, SSH key `~/.ssh/id_ed25519_winai`
- Windows work dir: `E:\video_transcription\{inbox,outbox}\`

## Iron rules (do not soften)

- **Verify size on Windows == Mac source BEFORE calling `transcribe_video`.** scp can leave a
  half-copied file that whisper will happily transcribe into garbage/truncated output. Compare
  `Length` on the box against `ls -la` on the Mac and only proceed on an exact match.
- **`transcribe_video` is a SYNC blocking call — not fire-and-forget.** It returns only when
  the whole whisper + doc-cleanup run finishes; a long video blocks for a long time. **Tell the
  user it will wait** and roughly how long, then run it — never fire it and go poll something
  else expecting an async job id.
- **Check prereqs before touching files** — Tailscale up + `bombot` MCP `✔ Connected`. A
  failed transcribe halfway is worse than a 5-second prereq check up front (see Prereqs).
- **Check the inbox for leftovers before transcribing** with `mcp__bombot__list_transcribe_inbox`.
  The inbox is a shared folder; if an old job's file is still there, name the exact file you
  mean so you don't transcribe the wrong one.
- **Never read, print, or hardcode `BOMBOT_BRIDGE_TOKEN`.** It authenticates the bridge and
  lives only in `homelab-mcp/.env` (and its match on the Windows side). Reference it by name;
  never by value.

## Prereqs (check first, every time)

```bash
tailscale status        # must NOT be "stopped"; if stopped: tailscale up
claude mcp list         # must show:  bombot: ... ✔ Connected
```

If `bombot` is missing from `claude mcp list`, install/register it from the homelab-mcp repo:

```bash
cd /Users/bombot/WebstormProjects/Tools/homelab-mcp && bash mac/install.sh
```

`install.sh` needs a `.env` with `BOMBOT_BRIDGE_TOKEN` (must match the Windows side) and
`BOMBOT_BRIDGE_URL`. If `.env` is missing/mismatched the bridge won't connect — fix that first,
don't retry transcribe against a dead bridge.

## Flow

1. **Prereqs** — Tailscale up, `bombot` Connected (above). Then
   `mcp__bombot__list_transcribe_inbox` to see what's already in the inbox.

2. **Copy the file to the Windows inbox** (Mac → box, direct scp — no UI):
   ```bash
   scp -i ~/.ssh/id_ed25519_winai "<mac source path>" \
       "pradc@bombot-gaming:/E:/video_transcription/inbox/<same filename>"
   ```
   - Quote **both** paths — source filenames with spaces break the copy silently.
   - The SSH identity is `~/.ssh/id_ed25519_winai`, the remote user is `pradc` (NOT the current
     Mac user), the host is `bombot-gaming`.
   - scp's Windows-drive form is `/E:/...` (leading slash), while native Windows tools use
     `E:\...` (backslash) — both name the same path, used in different commands below.

3. **Verify it arrived intact** (guards a half-copy — Iron rule 1):
   ```bash
   ssh -i ~/.ssh/id_ed25519_winai pradc@bombot-gaming \
     "powershell -NoProfile -Command \"Get-ChildItem 'E:\video_transcription\inbox' | Select-Object Name, Length\""
   ```
   Compare the `Length` for your file against `ls -la "<mac source path>"`. Must match exactly.

4. **Transcribe** — call `mcp__bombot__transcribe_video` with the **full Windows path** and
   `make_doc: true`:
   ```
   video_path: "E:\video_transcription\inbox\<filename>.mp4"
   make_doc:   true
   ```
   Tell the user first that this blocks until done (Iron rule 2). Output is a folder on the box:
   `E:\video_transcription\outbox\<name>_<timestamp>\` containing:
   - `.srt` — segments with timestamps
   - `.txt` — plain text, no timestamps
   - `.md` — readable write-up, cleaned by `qwen3:8b` (best for a human to read)

5. **Bring the whole result folder back to the Mac**:
   ```bash
   scp -i ~/.ssh/id_ed25519_winai -r \
     "pradc@bombot-gaming:/E:/video_transcription/outbox/<folder>/*" \
     <mac destination dir>/
   ```

6. **Hand the files to the user** — `SendUserFile` the `.md` (most readable) and the `.srt`
   (has timestamps). Skip the `.txt` unless asked; it's a subset of the other two.

## Gotchas (hit in real runs)

- **A process spawned on Windows via a plain SSH command dies the instant the SSH session
  ends** — Windows ties the child to that session's Job Object. This does **not** affect
  `transcribe_video`: that runs inside the long-lived `bridge_server.py` (already running on
  the box), invoked over the MCP tunnel, not spawned per-SSH. It **only** bites you if you try
  to (re)start the bridge yourself over SSH — then a `Start-Process` bridge will be reaped when
  you disconnect. To launch a durable process over SSH, create it detached from the session:
  ```powershell
  Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = '<cmd>' }
  ```
- **Shared inbox → wrong-file risk.** If several files sit in `inbox`, `transcribe_video` acts
  on the path you pass — name it exactly; don't assume "the latest" (Iron rule 4).
- **Bridge shows disconnected after a Windows reboot / Tailscale drop** — re-check `tailscale
  status` (both ends) and `claude mcp list` before assuming the tool is broken.

## Quick reference

| Need | Command / tool |
|---|---|
| Tailscale up? | `tailscale status` (→ `tailscale up` if stopped) |
| Bridge connected? | `claude mcp list` → `bombot: ... ✔ Connected` |
| (Re)install bridge | `cd .../homelab-mcp && bash mac/install.sh` (needs `.env`) |
| What's in the inbox | `mcp__bombot__list_transcribe_inbox` |
| Copy file → box | `scp -i ~/.ssh/id_ed25519_winai "<src>" "pradc@bombot-gaming:/E:/video_transcription/inbox/<name>"` |
| Verify size on box | `ssh -i ~/.ssh/id_ed25519_winai pradc@bombot-gaming "powershell -NoProfile -Command \"Get-ChildItem 'E:\video_transcription\inbox' | Select-Object Name, Length\""` |
| Transcribe | `mcp__bombot__transcribe_video` · `video_path` = `E:\...\inbox\<name>` · `make_doc: true` (SYNC) |
| Copy results ← box | `scp -i ~/.ssh/id_ed25519_winai -r "pradc@bombot-gaming:/E:/video_transcription/outbox/<folder>/*" <dest>/` |

## Status

v0.1 draft — flow verified end-to-end on one real transcription run (Mac → `bombot-gaming` →
back). Not yet pressure-tested per `superpowers:writing-skills`. Likely to need a second data
point: whether the `_<timestamp>` outbox folder name is stable enough to glob reliably in step 5
without first `ls`-ing the outbox, and the real wait-time-per-minute-of-video so the user can be
given a concrete estimate up front.
