---
name: seeneo-edit
description: Edit the user's own video footage with the seeneo tools. Cut silences and flubbed lines, trim and order clips, add Thai/English/Chinese captions, reframe to 9:16, 1:1, 4:5 or 16:9, add music and render an mp4, all locally for free. Hand off to the seeneo.ai server only for AI video shots, hosted HTML overlay renders or private cloud storage. Use when the user asks to edit, cut, caption or subtitle a video, or to make a Reel, TikTok or Short. Thai and Chinese triggers include ตัดต่อวิดีโอ, ใส่ซับ, ตัดช่วงเงียบ, 剪辑视频, 加字幕.
---

# seeneo video editing

You edit the user's own footage. Do the work on their machine with the free `seeneo-local` tools. Use the `seeneo` server tools only when the user asks for something the local tools can't do, and only with their consent.

## Ground rules

- Reply in the user's language (ไทย, English or 中文). Leave file paths and tool arguments as they are.
- Work locally first. `seeneo-local` is free, needs no account and never sends footage anywhere.
- **Ask before any upload.** Name the exact files and their sizes, say what the server will do with them, and wait for a clear yes in this conversation. If they don't say yes, don't upload.
- **Paid steps: quote first.** Show the exact settings and the price in credits (1 credit = THB 1), wait for a clear yes, then call with that quote. A new setting needs a new quote and a new yes.
- Only promise what you can check. Don't call results "perfect" or "best quality", don't give a fixed delivery time, and don't promise the same person or character looks identical across shots. Render size follows the first clip's long side (drafts cap it at 540 px). Reframing landscape footage to 9:16 enlarges the cropped area, so it can look softer than the source. Say so when it matters.
- Work only on files the user gave you. If a path is unclear, ask. Never guess one. Pass absolute paths to the `seeneo-local` tools (Codex requires them).
- Every output goes to the output folder: `$SEENEO_OUT_DIR` if set, otherwise `./seeneo-out` in Claude Code and a `seeneo-out` folder next to the first input file in Codex. Tell the user the path of each file you make.
- Use music, logos and footage only if the user owns them or is allowed to use them. If you're unsure, ask.

## Local workflow

1. **Probe** each file with `probe(path)` to get duration, size, fps, rotation and audio. Mention files that have no audio or are rotated.
2. **Look** with `frames(path, count=6)`, which returns one contact sheet. Use `times_s=[...]` to check specific moments such as a cut point or a caption spot. Keep `count` low and only look again where you need to.
3. **Listen**
   - Talking or speech: call `transcribe(path, language=...)`. Pass `th`, `en` or `zh` when you know the language, otherwise `auto`. Use `quality="best"` only when the user wants extra accuracy and accepts a slower run. The first run downloads speech-recognition files once, so pass on the size note to the user.
   - Pacing and dead air: call `find_silence(path)`. The `speech` ranges are what to keep. Raise `min_silence_s` for fewer cuts. Raise `noise_db` toward `-30` in noisy rooms.
4. **Plan** the edit and show it before you render: clips with in/out times, order, aspect and fit, transition, caption style and position, and music. Ask only about choices that change the result (aspect, caption look, music). For everything else, pick a sensible default and say which one you picked.
5. **Draft** with `render(..., draft=true)`, which is small and fast.
6. **Check the draft** with `frames(<draft output>, times_s=[...])` at cut points and caption moments. Fix bad cuts, captions that overflow and crops that cut off faces, then make another draft if needed.
7. **Final render**: the same `render` call without `draft=true`. Report the path, duration, resolution and file size.

### Building the clip list

- From transcript cues, keep the lines the user wants and drop restarts and repeats. Cut at cue edges with about 0.1 s of padding.
- From `speech` ranges, merge ranges that are less than about 0.3 s apart so speech doesn't sound choppy.
- Every clip needs `0 ≤ start_s < end_s ≤ duration`. The limits are 200 clips and 60 minutes of output.
- `aspect`: `9:16` for Reels, TikTok and Shorts, `1:1` or `4:5` for feed posts, `16:9` for YouTube, or `source` to keep the original. `fit="crop"` fills the frame, so check with `frames` that faces stay in shot. `fit="pad"` keeps the whole picture and adds bars.
- `transition="fade"` (`transition_s` about 0.3) smooths changes between scenes. Use `none` for fast talking-head cuts.

### Captions

- Caption times follow the **rendered** timeline. With one uncut clip, use the `srt_path` from `transcribe` directly. When you cut or join clips, run `transcribe` on the draft render and use that SRT for the final render, because the draft and the final have the same timing. You can also pass re-timed `cues` yourself, but fades shorten the timeline.
- Before the final render, check names, brand words and anything the speech recognition misheard, and fix them with the user. Take extra care with Thai spelling. Keep each cue short and easy to read.
- Presets (`captions.style`):
  - `clean` is plain and easy to read, for interviews and tutorials.
  - `bold` is big and punchy, for short-form hooks.
  - `glow` is coloured glowing text, for lively or night content.
  - `box` puts text on a solid box, which reads well over busy footage.
- `position`: on `9:16`, `middle` stays clear of the app buttons and captions that platforms add. Use `bottom` for `16:9`.
- Custom look: `style_config` with `fontFamily, fontSizePx, fill, highlight, stroke, strokeWidthPx, glowColor, glowSizePx, wordsPerScreen`. Setting `highlight` on cues that have word timings highlights the current word. Use 2–4 `wordsPerScreen` for fast vertical videos.
- Thai and Chinese text needs a font that supports it. The tools pick one automatically, and `fontFamily` can name an installed font (for Thai, Kanit works well).

### Music

- `music={path, volume_db=-18, duck=true}`. `duck` lowers the music while someone speaks. Keep `loudnorm=true` so the volume is even for social apps.

## Handing off to the seeneo server

Use it only when the user asks for one of these:

- **AI video shot**, meaning a new generated clip such as B-roll or an establishing shot. *Powered by MiniMax H3.* Call `create_project`, then `quote_h3`. Show the exact settings and credits and wait for a clear yes. Then call `generate_h3` with exactly the same settings and the `quote_id`. A prompt-only shot uploads nothing. The server decides where shots are available and refuses some topics. Pass its answer on plainly and don't try to work around a refusal. Tell the user the shot is AI-generated, and don't promise how it will look.
- **Animated HTML/WebGL overlay rendered on the server.** After upload consent: `create_project` → `create_upload` → `confirm_upload` → `add_html_overlay` → `quote(action="render")` → clear yes → `render(quote_id=...)`.
- **Private cloud copy** of a project in the user's seeneo.ai account. This also needs upload consent.

Steps:

1. Explain why the local tools aren't enough and what the server step needs. Local tools are always free. Server tasks need a seeneo.ai sign-in, and paid server steps use credits, which today need an active seeneo plan (THB 299/month).
2. If the `seeneo` tools need sign-in, tell the user how to sign in with their seeneo.ai account. In Claude Code they run `/mcp` and choose `seeneo`. In Codex they run `codex mcp login seeneo` in a terminal, then retry. Sign-in is only through the seeneo.ai page in the browser. Never ask for, accept or pass an API key, token or password.
3. Call `whoami` to see the plan, credits and limits. If something is missing, share the `upgrade` or `top_up` link it returns. Don't push.
4. Call `start_workflow` for the server's step order and follow it.
5. Get upload consent for the exact files, then quote, then a clear yes, then call. Poll `get_job` every 5–10 s. After each paid step, tell the user how many credits are left.
6. Fetch results with `get_download_url` and save them into the output folder with `curl -o`. Then continue editing locally, for example by placing an AI shot into the local `render`.
