# clip-video

**Turn any long video into ready-to-post vertical clips, with titles, descriptions and hashtags for every platform. It runs on your Mac and needs no API keys beyond Claude Code itself.**

`clip-video` is a [Claude Code](https://code.claude.com) plugin. Give it a YouTube link (or a local file) and Claude:

1. downloads the video and transcribes it locally with Whisper,
2. reads the **whole** transcript and picks the moments that work as stand-alone shorts,
3. renders each one as a 1080×1920 clip with a face-following crop, word-by-word captions and a hook title,
4. writes a title, a description and hashtags for **YouTube Shorts, TikTok, Instagram Reels and Facebook Reels**, checks each against that platform's character and hashtag limits, and puts it all in one copy-paste file.

It's a free, local alternative to OpusClip-style tools. The paid step of those apps is an LLM reading your transcript; here Claude does it inside your existing Claude Code session.

## What you get

```
clips/mrbeast-lose-150-lbs/
├── clip_01.mp4 … clip_10.mp4   # 1080x1920 H.264, captions and hook burned in
├── CLIPS.md                    # every title, description and hashtag set, ready to paste
├── metadata.json               # the same texts, structured
├── clips.json                  # which parts of the source each clip uses
└── render_log.json             # durations, source ranges, layout stats
```

Each clip in `CLIPS.md` looks like this:

> **YouTube Shorts** · Title (98/100): *If This Couple Loses 150 Pounds Before Their Wedding, They Win $250,000 (One Rule Ends Everything)*
> Description (1,525/5,000 characters) … `#MrBeast #WeightLoss #WeightLossJourney #Transformation #Challenge`
>
> **TikTok** · Caption (1,097/2,200) · **Instagram Reels** · Caption (1,822/2,200, 5 hashtags) · **Facebook Reels** · Title (163/255) + description (1,146)

## Features

- **Moment picking by Claude.** Claude reads the full transcript and picks moments that stand alone, with a hook in the first seconds and a payoff at the end. It covers different beats of the video, can stitch a clip from several parts to cut dead air, and skips sponsor reads and intros.
- **Face-following 9:16 crop.** It tracks faces shot by shot. When people are too far apart to fit one crop, it switches to the full frame over a blurred background.
- **Word-synced captions** with the spoken word highlighted, plus a hook title on top for the first 3.5 seconds.
- **Copy for four platforms** in one file. Titles run close to each limit and descriptions use the space with real content from the video, never filler. Hashtag counts follow each platform's current rules (for example, Instagram's cap of 5).
- **Automatic language.** It detects the video's language and writes every title, description and hashtag in it, or in any language you ask for. Captions always stay in the spoken language.
- **Built-in checks.** A validator counts characters the strict way (emoji count as 2) and flags anything over a limit. Contact sheets let Claude look at every clip before you do.
- **No extra services or API keys.** Download, transcription, face tracking and rendering run on your machine. The only thing that leaves it is the transcript text Claude reads, as part of your normal Claude Code session.

## Requirements

- macOS on **Apple Silicon** (M1 or newer). Transcription uses [mlx-whisper](https://github.com/ml-explore/mlx-examples/tree/main/whisper).
- [Homebrew](https://brew.sh)
- [Claude Code](https://code.claude.com)
- About 3 GB of free disk space for the tools and the Whisper model, plus room for the source video.

On first run the plugin installs what's missing: `yt-dlp`, `uv` and `ffmpeg-full` through Homebrew, and a Python environment in `~/.cache/clip-video`. `ffmpeg-full` is installed alongside your regular `ffmpeg` and doesn't replace it.

## Install

In Claude Code:

```text
/plugin marketplace add jonalonso/clip-video
/plugin install clip-video@jonalonso
```

<details>
<summary>Manual install (no plugin)</summary>

```bash
git clone https://github.com/jonalonso/clip-video.git
cp -R clip-video/skills/clip-video ~/.claude/skills/
```

Restart Claude Code, then use `/clip-video` instead of `/clip-video:clip-video`.
</details>

## Usage

Just ask, in any language:

```text
Make clips from this video: https://www.youtube.com/watch?v=RE3_PGwDwhw
```

```text
Clip this podcast into shorts, output in Spanish: https://youtu.be/...
```

```text
/clip-video:clip-video ~/Movies/interview.mp4
```

You can also tell it:
- **The output language.** By default it uses the language spoken in the video.
- **How many clips.** By default it makes about one per 4–5 minutes of video, between 3 and 10.
- **A campaign brief** if you're clipping for a creator program. The brief's rules on allowed videos, length, required tags and links override the defaults.
- **Where to save the clips.** By default it uses `./clips/<channel>-<title>/`.

Approximate times on an M1 Pro for a 43-minute video and 10 clips: download 1–2 min, transcription about 6 min, rendering about 8 min, then Claude writes the copy. The first run also downloads a 1.6 GB Whisper model.

## How it works

```text
yt-dlp ─► ffmpeg (16 kHz wav) ─► mlx-whisper (word timestamps, language detection)
      ─► Claude reads the transcript and writes clips.json
      ─► render.py: shot detection + YuNet face tracking + ASS captions ─► clip_XX.mp4
      ─► contact_sheet.py: Claude reviews frames of every clip
      ─► Claude writes metadata.json ─► build_report.py validates limits ─► CLIPS.md
```

| Platform | Title | Main text | Hashtags |
|---|---|---|---|
| YouTube Shorts | 100 | Description 5,000 | 3–8 (the first 3 show above the title) |
| TikTok | none | Caption 2,200 (kept scheduler-safe; the app allows ~4,000) | 3–6 |
| Instagram Reels | none | Caption 2,200, hashtags included | max 5 |
| Facebook Reels | 255 | Description, 1,000+ target | 1–3 |

Limits were checked in October 2026 and live in `skills/clip-video/references/platforms.md`. Platforms change them often, so pull requests are welcome.

## Tips

- **Listen before you post.** Claude checks sync and looks at frames, but it can't hear the audio.
- **Check names in the captions.** Whisper sometimes mishears names. Claude proofreads the chosen clips and fixes the obvious ones, and it flags what it isn't sure about instead of guessing.
- **If a YouTube download fails,** run `brew upgrade yt-dlp`. YouTube breaks yt-dlp often.
- **Re-render one clip** by asking, for example "make clip 3 shorter" or "change the hook of clip 5". Only that clip is rendered again.

## Use it responsibly

Only clip videos you own or have permission to use. Many creators run official clipping programs that pay per view (MrBeast's runs on Vyro, for example). Inside those programs, the campaign brief tells you what's allowed. Posting someone else's content without permission can get your account struck. Every description this plugin writes includes a credit line to the original video.

## Credits

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) and [FFmpeg](https://ffmpeg.org) with libass
- [mlx-whisper](https://github.com/ml-explore/mlx-examples) running OpenAI's Whisper large-v3-turbo
- [YuNet face detector](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet) from OpenCV Zoo, MIT © 2020 Shiqi Yu
- Fonts [Anton](https://fonts.google.com/specimen/Anton) and [Poppins](https://fonts.google.com/specimen/Poppins), SIL Open Font License 1.1

## Support

If this plugin saved you time or helped your channel grow, you can [buy me a coffee ☕](https://www.paypal.com/donate/?hosted_button_id=9VHZSB7CY5Q7S). Thank you!

## License

[MIT](LICENSE) © 2026 [Jonathan Salazar](https://github.com/jonalonso). Bundled fonts and the face model keep their own licenses (see `LICENSE`).
