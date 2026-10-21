---
name: clip-video
description: Turn a long video (YouTube link or local file) into vertical 9:16 short clips, entirely on this Mac with no API keys. Each clip gets a face-following crop, word-by-word captions and a hook title. Clips come with ready-to-paste titles, descriptions and hashtags for YouTube Shorts, TikTok, Instagram Reels and Facebook Reels, in the video's own language unless another is requested. Use this whenever the user shares a video link and wants clips, shorts, reels, highlights or "the best moments". Also use it for clipping campaigns and creator programs, repurposing a podcast, interview or stream into short-form content, or phrases like "sacá clips de este video", "dale con este url" or "hacé shorts de esto", even if the user never says "clip".
license: MIT
compatibility: macOS on Apple Silicon with Homebrew. Installs yt-dlp, uv, ffmpeg-full and a Python venv (mlx-whisper, OpenCV) on first run; downloads a ~1.6 GB Whisper model.
metadata:
  author: Jonathan Salazar (https://github.com/jonalonso)
  version: "1.1.0"
---

# clip-video

The pipeline replaces SupoClip/OpusClip with free local tools. Claude (you) does the one step those apps pay an LLM API for: reading the transcript and choosing the moments.

```
yt-dlp → ffmpeg wav → mlx-whisper (local) → YOU pick moments → render.py → contact sheets → metadata.json → build_report.py → CLIPS.md
```

`SKILL` below means this skill's folder: `${CLAUDE_SKILL_DIR}`.

**If `$SKILL/scripts/` is not on disk** (some marketplaces load only this text, not the files), get the same files from the public repo and use that copy as `SKILL`. Tell the user before downloading:

```bash
git clone --depth 1 https://github.com/jonalonso/clip-video.git ~/.cache/clip-video/repo 2>/dev/null \
  || git -C ~/.cache/clip-video/repo pull --ff-only
SKILL=~/.cache/clip-video/repo/skills/clip-video
```

### What this skill installs and downloads
Say this to the user on the first run, before installing anything:
- Homebrew packages, only if missing: `yt-dlp`, `uv`, `ffmpeg-full`.
- A Python venv in `~/.cache/clip-video/venv` with `mlx-whisper`, `opencv-python` and `numpy` from PyPI.
- The Whisper model `mlx-community/whisper-large-v3-turbo` from Hugging Face (~1.6 GB, first transcription only).
- The video the user asks for, via yt-dlp, into a temporary work folder.
- One web search for current hashtags (Step 6), plus the git clone above if the scripts are missing.

Nothing else leaves the machine: no uploads, no analytics, no API keys. The transcript is read by you, inside the user's normal Claude session.

## Inputs

- **Video**: a URL (anything yt-dlp supports) or a local file path. Required.
- **Output language** (optional): if absent, use the language Whisper detects in the video. Every text you generate (hook titles, platform titles, descriptions, hashtags, the "why" notes and manual-check notes in CLIPS.md) goes in that one language. Subtitles always stay in the spoken language, because they are the transcription synced to the audio word by word. When the output language differs from the spoken one, the burned hook is in the output language and the subtitles stay as spoken.
- **Campaign brief** (optional): if the user is clipping for a program (e.g. a MrBeast campaign on Vyro), its rules override the defaults here: allowed videos, length, required tags, links and disclosures. Ask for it if they mention a campaign but haven't shared it.
- **Number of clips** (optional): default is about one per 4–5 minutes of source, at least 3 and at most 10.

## Step 1: Setup (first run installs things)

```bash
bash $SKILL/scripts/setup.sh
```

The script prints `PYTHON=...` and `FFBIN=...`; run every Python script below with that interpreter and `-I`, and call ffmpeg as `$FFBIN/ffmpeg`. A plain `ffmpeg` may not exist, or may lack libass. On a fresh machine it installs `yt-dlp`, `uv` and `ffmpeg-full` with Homebrew and builds a venv in `~/.cache/clip-video/venv`; set `CLIP_VIDEO_HOME` to move it. Tell the user what is being installed. `ffmpeg-full` is keg-only and does not replace their normal `ffmpeg`. Apple Silicon is required (mlx-whisper).

## Step 2: Download and transcribe

Use a work folder for heavy files: the session scratchpad if there is one, otherwise `/tmp/clip-video/<video-id>`. The source video can be several GB, so it never goes in the output folder.

```bash
yt-dlp -f 'bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080]' --merge-output-format mp4 \
  --ffmpeg-location "$FFBIN" -o "$WORK/source.%(ext)s" --write-info-json --no-playlist "<URL>"
"$FFBIN/ffmpeg" -v error -y -i "$WORK/source.mp4" -vn -ac 1 -ar 16000 "$WORK/audio.wav"
$PYTHON -I $SKILL/scripts/transcribe.py "$WORK/audio.wav" "$WORK"      # --language xx only if detection is wrong
```

- Read the title, channel, duration and upload date from `source.info.json` (`title`, `channel`, `duration_string`, `upload_date`). Also read its `description` for people's names.
- **Transcribe the full video without `--prompt`.** In the first run, a full pass with a names prompt fixed some names but dropped whole phrases: five "You did it!" lines and the first sentence of the doctor's clip disappeared. Use `--prompt` only to settle a doubtful word in a short snippet (Step 3). Note people's names from the title and description, because Whisper mishears them ("Trey" came out as "train" and "tray").
- Transcription takes about 6 minutes for a 43-minute video on an M1 Pro, and the first run downloads a ~1.6 GB model. Run it in the background, but don't pipe its output through `grep`/`tail`: that hides a crash behind exit code 0. Redirect to a log file instead, and confirm the `transcribed in …s` line and `transcript.txt` exist before moving on.
- If yt-dlp fails on YouTube, `brew upgrade yt-dlp` first. YouTube breaks it often.
- For a local file, skip yt-dlp and point the rest at that file.

Output folder: `./clips/<channel>-<short-title-slug>/` under the current working directory, unless the user names another.

## Step 3: Read the whole transcript and choose the moments

Read all of `$WORK/transcript.txt` (page through it if it is long). Skimming produces generic picks. You are choosing what the paid tools charge for, so take care.

A good clip:
- **Stands alone.** Someone who never saw the video understands the setup and gets the payoff. Starting with the stakes ("If this couple can lose 150 pounds…") beats starting mid-action.
- **Hooks in the first 3 seconds** with the spoken line itself. Start on the strongest sentence, not on filler ("so", "okay", "um").
- **Ends on the payoff** (the reveal, the laugh, the "you did it!"), not after it trails off.
- **Is 20–90 s**, ideally 30–60. Use `parts` to cut dead air or a repeated explanation out of a longer moment instead of dropping it.
- **Covers different beats**: premise, conflict or struggle, a funny moment, a reveal or stunt, an emotional moment, the outcome. Avoid several clips of the same kind of moment.

Skip:
- Sponsor reads and ad segments: "use code…", "link in the description", product pitches.
- Intros and outros asking for subscribes.
- Moments that depend on visuals the transcript can't confirm. If you're unsure, say so in the notes.
- Segments where the transcript shows profanity or slurs. If a segment is too good to skip, keep it and flag it.

Write `clips.json` in the work folder. Times are seconds from the transcript; `render.py` snaps them to word boundaries.

```json
[
  {"id": "01", "start": 0.0, "end": 40.52, "hook": "Lose 150 lbs or get NOTHING"},
  {"id": "03", "parts": [[618.02, 635.38], [645.24, 674.56], [680.42, 713.58]], "hook": "Hold $50,000 for 1 minute"}
]
```

Hook titles are burned on screen for 3.5 s. Write 3–7 words in the output language. They should create curiosity without lying about what happens. Check who does what before writing a pronoun: in the test run, a clip where *both* people read letters was first hooked as "Her letter". The contact sheets in Step 5 show who is on screen.

**Proofread the captions you are about to burn.** Re-read the transcript lines inside each chosen range and look for names or words that make no sense in context. For a doubtful word, cut a snippet of up to 80 s around it and re-transcribe it with the names as a prompt:

```bash
"$FFBIN/ffmpeg" -v error -y -ss <start> -to <end> -i "$WORK/audio.wav" "$WORK/snip.wav"
$PYTHON -I $SKILL/scripts/transcribe.py "$WORK/snip.wav" "$WORK/snip" --prompt "MrBeast challenge with Sarah and Trey."
```

For a fix you are sure of, add `"fixes": {"wrong": "right"}` to that clip; it applies to that clip's captions only. When you can't tell what was said (in the first run Whisper heard "Sherry" both with and without the prompt), don't guess. Leave it and add a note asking the user to listen at that timestamp.

## Step 4: Render

```bash
$PYTHON -I $SKILL/scripts/render.py "$WORK/source.mp4" "$WORK/transcript.json" "$WORK/clips.json" "$OUT"   # background; ~1.5x clip length each
cp "$WORK/clips.json" "$OUT/"
```

Each clip comes out at 1080×1920 H.264/AAC. Faces are tracked per shot. Wide shots whose faces don't fit one crop switch to a "fit" layout: the whole frame over a blurred background. Captions are Poppins ExtraBold with the spoken word in yellow; the hook uses Anton on a yellow box. `render_log.json` records each clip's source ranges, duration and `fit_share`. To re-render one clip, append its id: `render.py … "$OUT" 03`.

## Step 5: Verify before showing anything

1. Check that audio and video durations match for every clip (`$FFBIN/ffprobe -show_entries stream=codec_type,duration`). A mismatch over ~0.1 s means something broke.
2. Make the contact sheets and **look at them**:
   ```bash
   $PYTHON -I $SKILL/scripts/contact_sheet.py "$OUT" "$WORK/review"
   ```
   Look for faces cut off by the crop, captions colliding with the creator's own burned-in text, a wrong hook, or an empty or black clip. Fix the clip list and re-render what's wrong.
3. You cannot hear audio. Never claim the audio sounds right. Tell the user to listen, especially at the joins of multi-part clips.

## Step 6: Titles, descriptions and hashtags

Read `references/platforms.md` first. It has the limits, the "useful maximum" rule the user chose (titles near the limit, long main texts with real content and no padding), the structure of each text, and how to pick hashtags. Run the web search for current hashtags it describes.

Write `$OUT/metadata.json`. Text fields can be a string or a list of paragraphs (joined with blank lines). Hashtags go only in `hashtags` without `#`; the report appends them.

```json
{
  "language": "en",
  "source": {"url": "…", "title": "…", "channel": "…", "duration": "43:16", "uploaded": "2026-10-17"},
  "notes": ["things the user must check by hand, in the output language"],
  "clips": {
    "01": {
      "why": "one line: why this moment works",
      "youtube":   {"title": "…", "description": ["…", "…"], "hashtags": ["MrBeast", "WeightLoss", "…"]},
      "tiktok":    {"caption": ["…"], "hashtags": ["…"]},
      "instagram": {"caption": ["…"], "hashtags": ["…"]},
      "facebook":  {"title": "…", "description": ["…"], "hashtags": ["…"]}
    }
  }
}
```

Then build and validate:

```bash
$PYTHON -I $SKILL/scripts/build_report.py "$OUT"
```

It counts characters the strict way, checks every limit and hashtag rule, and writes `CLIPS.md` with each final text in a copyable block. Fix every ERROR. Fix WARN lines (under target) with more real content, not padding. If a clip genuinely has nothing more to say, a warning is acceptable.

Lessons from the first real run:
- **First drafts come out 30–40% short.** Instagram drafts landed around 1,100–1,300 characters against an 1,800 target. Write fuller from the start. The material that fills the space honestly is the rest of the video: numbers from other days (weigh-ins, prizes), exact quotes from before and after the clip, what the moment sets up next. Re-reading the transcript beats inventing filler.
- **Only attribute a quote when you have seen who says it.** Whisper gives words, not speakers. "Love you, can't talk to you right now" was first written as Trey's line without checking. Either confirm the speaker on a frame at that timestamp, or quote it without a name.
- **Health, money and legal claims are attributed** ("according to the doctor in the video") and health content gets a one-line "not medical advice".
- Every fact has to come from the transcript or from frames you looked at, because these texts go out under the user's account.

## Step 7: Hand off

Tell the user, in their own language:
- Where the folder is. Send one sample clip plus `CLIPS.md` if a file-sending tool exists.
- A table of clips: duration, moment, hook.
- What to check by hand: audio, burned-in text from the original, fit-layout shots.
- **Rights.** Clipping someone else's video and posting it is only safe inside their clipping program or with permission; follow the campaign brief. Say this every time the source isn't the user's own content.

## Timing reference (M1 Pro, 43-min source, 10 clips)

Download ~1–2 min · transcription ~6 min · render ~8 min · metadata depends on how long the writing takes. Run long steps in the background and keep the user posted in one line per step.
