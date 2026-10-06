---
name: video-transcribe
description: >-
  Use when transcribing a video or audio file to text (SRT with timestamps, plain TXT, and a
  Markdown summary) via the homelab `bombot` MCP server — a Tailscale bridge to a Windows GPU
  box (`bombot-pc`) running ffmpeg + faster-whisper. Covers the prereq check, Taildrop-to-box →
  verify-size → `transcribe_video` → get-results-back flow, why a long file makes the client
  time out while the job keeps running, and why the `.md` is not a transcript.
---

# Video Transcribe (homelab bombot MCP)

**Skill version: `202609_02`**

Transcribe a local video/audio file by handing it to the `bombot` MCP server, a
Tailscale-tunnelled bridge to a Windows machine (`bombot-pc`) that has ffmpeg +
faster-whisper on GPU. The MCP tool does the whisper run and the summary; this skill is the
**file-shuffling + verification discipline** around it (get the file there intact, wait out the
call, bring the results back). Distilled from real runs, not theory.

- MCP server: `bombot` (repo `homelab-mcp`, unpacked on the Mac at `~/homelab-mcp/`)
- Relevant tools: `mcp__bombot__transcribe_video`, `mcp__bombot__list_transcribe_inbox`
- Box: `bombot-pc` (Tailscale). **No SSH on it** (no sshd) — files travel by **Taildrop**
  (`tailscale file cp`), not scp. The former box `bombot-gaming` is retired.
- Box paths (confirmed 05/10/2026 by `list_transcribe_inbox` and by the box's own session):
  inbox `H:\Local-LLM\video_transcription\inbox\`, outbox
  `H:\Local-LLM\video_transcription\outbox\<name>_<epoch>\`, whisper model `large-v3`.
  Taildrop lands files in `D:\User Files\Downloads\` on the box.

## Iron rules (do not soften)

- **Verify size on the box == Mac source BEFORE calling `transcribe_video`.** A half-copied file
  is transcribed into garbage/truncated output. Taildrop on Windows writes `.partial` until the
  file is complete, so also check no `.partial` is left. The Mac-side line
  `bombot-pc is not replying; trying anyway` appeared on a good transfer (the box just ACKs
  slowly) — it is not proof of failure or of success; compare sizes.
- **Call `transcribe_video` ONCE per file. A client timeout does not cancel the job.** The call
  is synchronous and the bridge's client gives up after 600 s, but the job on the box keeps
  running and writes its results to the outbox. A second call starts a second whisper run next
  to the first (two runs on a 12 GB GPU took VRAM from ~6 to 10 GB and risk OOM, and two
  `_<epoch>` folders appeared). After a timeout: **look in the outbox, do not re-call.**
- **Tell the user the call blocks and will likely time out** for anything long. Measured:
  87 min of video → about 50 min from the first outbox folder (14:48) to the last file (15:38),
  and the box's session read in its bridge log that this first-ever run also had to download
  `large-v3` (no HF token = slow; not checked by me). Budget 0.5–1× the video length.
- **Check prereqs before touching files** — Tailscale up + `bombot` MCP `✔ Connected`.
- **Check the inbox for leftovers** with `mcp__bombot__list_transcribe_inbox`; if an old file is
  there, name the exact file you mean.
- **The `.md` is NOT a transcript.** It is a summary written by a small local model (`qwen3:8b`);
  measured 7.6 KB from a 123 KB transcript, opening with "from the conversation you described…".
  Never cite it as what the meeting decided — use the `.txt` / `.srt`, and check names, field
  ids and NetSuite terms against the video or the live system (whisper mishears them).
- **Never read, print, or hardcode `BOMBOT_BRIDGE_TOKEN`.** It authenticates the bridge and
  lives only in `~/homelab-mcp/.env` (and its match on the box). Reference it by name.
- **Sending a recording to the box is sending it off the Mac.** It is the user's own machine on
  their tailnet, but meeting recordings can hold customer data: do it only on the user's OK.

## Prereqs (check first, every time)

```bash
tailscale status        # must NOT be "stopped"; bombot-pc should be listed and not offline
claude mcp list         # must show:  bombot: ... ✔ Connected
```

If `bombot` is missing, register it from the unpacked repo (needs `.env` with the URL and
`BOMBOT_BRIDGE_TOKEN`; the shipped `install.sh` had CRLF line endings and failed on macOS with
`set: pipefail: invalid option` until `sed -i '' $'s/\r$//' mac/install.sh`):

```bash
bash ~/homelab-mcp/mac/install.sh
```

## Flow

1. **Prereqs** (above), then `mcp__bombot__list_transcribe_inbox`.

2. **Send the file to the box** (Taildrop — no SSH, no UI; the user's OK first):
   ```bash
   tailscale file cp "<mac source path>" bombot-pc:
   ```
   It lands in `D:\User Files\Downloads\<filename>` on the box. Quote the path (spaces and
   parentheses are fine when quoted).

3. **Verify it arrived intact.** The bridge has no tool that lists that folder, so ask the box's
   own Claude session (or the user at the box) for the exact size and that no `.partial` is
   left; compare with `ls -l "<mac source path>"`. Must match exactly.

4. **Transcribe** — call `mcp__bombot__transcribe_video` once, with the **absolute Windows
   path** (an absolute path is accepted; no need to move the file into the inbox):
   ```
   video_path: "D:\User Files\Downloads\<filename>.mp4"
   make_doc:   true
   language:   "th"      # set it; leave out for auto-detect
   ```
   Expect the client to time out on a long file (Iron rule 2). Then poll the outbox, not the tool.

5. **Find the result** in `H:\Local-LLM\video_transcription\outbox\<name>_<epoch>\`:
   `.srt` (segments with timestamps), `.txt` (plain), `.md` (summary — see Iron rule 5), and
   `audio.wav` (the extracted audio, ~1.9 MB per minute; leave it, do not copy it back).
   Done when `.srt`/`.txt`/`.md` exist; `.md` is written last. The bridge has no tool to list the
   outbox either, so read it through the box's Claude session or at the box.

6. **Bring the three result files back** — from the box: `tailscale file cp <srt> <txt> <md>
   <mac-tailscale-name>:` (this Mac is `teibto-pradchaya` on the tailnet). They showed up in
   `~/Downloads/` without any command on the Mac (the Tailscale app saves incoming files);
   `tailscale file get <dir>` received nothing. Compare sizes with what the box reported.

7. **Hand over** — `SendUserFile` the `.srt` and `.txt`; mention the `.md` only as a summary.
   For screenshots tied to a sentence, take the timestamp from the `.srt` and cut a frame from
   the original video: `ffmpeg -ss <hh:mm:ss> -i "<video>" -frames:v 1 out.png`.

## Gotchas (hit in real runs)

- **Two sessions, one job.** A second Claude session on the box also called `transcribe_video`
  on the same file 49 s later. Result: two outbox folders (`_<epoch>`), two whisper processes
  on the GPU. Stopping the extra one (only its own process, never `bridge_server.py` — that is
  the bridge itself) left the other to finish. Agree who calls it before anyone does.
- **The bridge is a single process.** Killing `bridge_server.py` kills every `bombot` tool and any
  job running through it.
- **Ollama on the box listens on 127.0.0.1 only, on purpose.** `curl bombot-pc:11434` times out
  from the Mac; go through the bridge (`ask_ollama`) — see `setup-local-llm`.
- **A process spawned on Windows through a plain SSH command dies with the SSH session** (Job
  Object). Not relevant now (no SSH on `bombot-pc`), kept for any box that does have sshd.
- **Bridge shows disconnected after a reboot / Tailscale drop** — re-check `tailscale status`
  (both ends) and `claude mcp list` before assuming the tool is broken.
- **Tool list differs by client copy.** The shipped `mcp_bridge_client.py` still advertised
  `ask_9arm` / `list_9arm_models` (the 9arm gateway has expired); they were removed from the
  Mac copy. The server's `/health` still lists them.

## Quick reference

| Need | Command / tool |
|---|---|
| Tailscale up? | `tailscale status` |
| Bridge connected? | `claude mcp list` → `bombot: ... ✔ Connected` |
| (Re)install bridge | `bash ~/homelab-mcp/mac/install.sh` (needs `.env`; strip CRLF if it fails) |
| What's in the inbox | `mcp__bombot__list_transcribe_inbox` |
| Mac → box | `tailscale file cp "<src>" bombot-pc:` → `D:\User Files\Downloads\` |
| Transcribe (once) | `mcp__bombot__transcribe_video` · absolute Windows `video_path` · `make_doc: true` · `language: "th"` |
| After a timeout | check `H:\Local-LLM\video_transcription\outbox\` — do not call again |
| Box → Mac | on the box: `tailscale file cp <3 files> teibto-pradchaya:` → `~/Downloads/` |
| Frame at a sentence | `ffmpeg -ss <time> -i "<video>" -frames:v 1 out.png` |

## Status

Flow verified end to end on 05/10/2026 with one real 87-minute Thai meeting (548 MB): Taildrop
Mac → `bombot-pc` (size matched), one `transcribe_video` (client timed out, job finished,
`.srt` 166,954 B / `.txt` 122,940 B / `.md` 7,622 B), results back by Taildrop (sizes matched).
Not verified: transcript accuracy over the whole file (only the opening was read); behaviour
when the bridge restarts mid-job; English or mixed-language audio; whether `transcribe_video`
returns early for short files (this one never returned a result to the client).
