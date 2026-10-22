"""Render vertical 9:16 clips from a landscape source.

Each clip gets a face-following crop (per shot, smoothed), a blurred-background
"fit" layout for shots whose faces are too far apart to share one crop,
word-synced captions with the spoken word highlighted, and a hook title on top
for the first seconds.

Usage: python render.py <source.mp4> <transcript.json> <clips.json> <out_dir> [clip_id ...]
clips.json: [{"id": "01", "start": 123.4, "end": 170.2, "hook": "..."},
             {"id": "02", "parts": [[300.0, 320.5], [331.2, 360.0]], "hook": "...",
              "fixes": {"train": "Trey"}}, ...]
"fixes" replaces misheard caption words in that clip only.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

ASSETS = Path(__file__).resolve().parent.parent / "assets"
FFMPEG = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"   # keg-only build with libass, needed for captions
FFPROBE = "/opt/homebrew/opt/ffmpeg-full/bin/ffprobe"
FACE_MODEL = str(ASSETS / "models" / "face_detection_yunet_2023mar.onnx")
FONTS_DIR = ASSETS / "fonts"

OUT_W, OUT_H = 1080, 1920
AN_W, AN_H = 640, 360          # analysis resolution
CUT_THRESHOLD = 28.0           # mean abs grey diff (0-255) on a 64x36 thumbnail
MIN_FACE_FRAC = 0.035          # ignore faces narrower than this fraction of the source width
HOOK_SECONDS = 3.5
CAPTION_Y = 1420


def probe(src):
    out = subprocess.run(
        [FFPROBE, "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height,r_frame_rate", "-of", "json", src],
        capture_output=True, text=True, check=True).stdout
    s = json.loads(out)["streams"][0]
    num, den = map(int, s["r_frame_rate"].split("/"))
    return s["width"], s["height"], s["r_frame_rate"], num / den


def decode(src, start, dur, scale=None):
    vf = ["-vf", f"scale={scale[0]}:{scale[1]}"] if scale else []
    return subprocess.Popen(
        [FFMPEG, "-v", "error", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", src,
         *vf, "-an", "-pix_fmt", "bgr24", "-f", "rawvideo", "-"],
        stdout=subprocess.PIPE, bufsize=10**8)


def analyze(src, start, dur, W):
    detector = cv2.FaceDetectorYN.create(FACE_MODEL, "", (AN_W, AN_H), 0.7)
    proc = decode(src, start, dur, (AN_W, AN_H))
    size = AN_W * AN_H * 3
    sx = W / AN_W
    cuts, faces, prev, n = [0], {}, None, 0
    while True:
        buf = proc.stdout.read(size)
        if len(buf) < size:
            break
        frame = np.frombuffer(buf, np.uint8).reshape(AN_H, AN_W, 3)
        thumb = cv2.cvtColor(cv2.resize(frame, (64, 36), interpolation=cv2.INTER_AREA),
                             cv2.COLOR_BGR2GRAY).astype(np.int16)
        if prev is not None and np.abs(thumb - prev).mean() > CUT_THRESHOLD:
            cuts.append(n)
        prev = thumb
        if n % 2 == 0:
            _, dets = detector.detect(frame)
            if dets is not None:
                faces[n] = [((d[0] + d[2] / 2) * sx, d[2] * sx) for d in dets if d[2] * sx >= MIN_FACE_FRAC * W]
        n += 1
    proc.wait()
    return n, cuts, faces


def plan(n, cuts, faces, W, H, fps):
    """Per-frame crop x (left edge) and layout ('crop' or 'fit')."""
    cw = int(round(H * 9 / 16 / 2) * 2)
    centers = np.full(n, W / 2.0)
    layout = np.array(["crop"] * n, dtype=object)
    bounds = sorted(set(cuts)) + [n]
    for a, b in zip(bounds, bounds[1:]):
        pts, spread_frames, detected_frames, prev = [], 0, 0, None
        for f in range(a, b):
            cands = faces.get(f)
            if not cands:
                continue
            detected_frames += 1
            big = max(c[1] for c in cands)
            peers = [c for c in cands if c[1] >= 0.6 * big]
            if len(peers) >= 2 and max(c[0] for c in peers) - min(c[0] for c in peers) > 0.9 * cw:
                spread_frames += 1
            if prev is None:
                pick = max(cands, key=lambda c: c[1])
            else:
                pick = max(cands, key=lambda c: c[1] - 0.5 * abs(c[0] - prev))
            prev = pick[0]
            pts.append((f, pick[0]))
        if not pts:
            continue
        if detected_frames and spread_frames / detected_frames > 0.5:
            layout[a:b] = "fit"
            continue
        fs, cs = zip(*pts)
        track = np.interp(np.arange(a, b), fs, cs)
        if np.ptp(cs) < 0.08 * W:
            track[:] = np.median(cs)
        else:
            k = max(3, int(fps * 0.7)) | 1
            padded = np.pad(track, k // 2, mode="edge")
            track = np.convolve(padded, np.ones(k) / k, mode="valid")
        centers[a:b] = track
    x0 = np.clip(centers - cw / 2, 0, W - cw).astype(int)
    return cw, x0, layout


def compose(frame, x, cw, layout, W, H):
    if layout == "crop":
        return cv2.resize(frame[:, x:x + cw], (OUT_W, OUT_H), interpolation=cv2.INTER_LANCZOS4)
    fit_h = int(round(OUT_W * H / W / 2) * 2)
    bg_src = frame[:, (W - cw) // 2:(W + cw) // 2]
    bg = cv2.GaussianBlur(cv2.resize(bg_src, (OUT_W // 8, OUT_H // 8), interpolation=cv2.INTER_AREA), (0, 0), 4)
    bg = (cv2.resize(bg, (OUT_W, OUT_H), interpolation=cv2.INTER_LINEAR) * 0.55).astype(np.uint8)
    y = (OUT_H - fit_h) // 2
    bg[y:y + fit_h] = cv2.resize(frame, (OUT_W, fit_h), interpolation=cv2.INTER_AREA)
    return bg


def ass_time(t):
    t = max(t, 0)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def clean(word):
    return word.strip().replace("\\", "").replace("{", "").replace("}", "")


def group_words(words, max_words=3, max_chars=14, max_gap=0.5):
    groups, cur = [], []
    for w in words:
        text = clean(w["word"])
        if not text:
            continue
        if cur and (len(cur) >= max_words
                    or len(" ".join(clean(c["word"]) for c in cur) + " " + text) > max_chars
                    or w["start"] - cur[-1]["end"] > max_gap
                    or clean(cur[-1]["word"])[-1:] in ".?!,"):
            groups.append(cur)
            cur = []
        cur.append(w)
    if cur:
        groups.append(cur)
    return groups


def build_ass(parts, hook, path):
    """parts: [(words shifted to clip time, part end in clip time), ...]"""
    hi = r"{\c&H0000E5FF&\fscx112\fscy112}"
    lo = r"{\c&H00FFFFFF&\fscx100\fscy100}"
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {OUT_W}", f"PlayResY: {OUT_H}",
        "WrapStyle: 0", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
        "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Cap,Poppins ExtraBold,98,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,0,0,0,0,100,100,0,0,1,8,4,5,60,60,0,1",
        "Style: Hook,Anton,100,&H00101010,&H00101010,&H0000D7FF,&H00000000,0,0,0,0,100,100,1,0,3,22,0,8,90,90,250,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    if hook:
        lines.append(f"Dialogue: 1,{ass_time(0)},{ass_time(HOOK_SECONDS)},Hook,,0,0,0,,"
                     rf"{{\fad(150,250)}}{clean(hook).upper()}")
    for words, part_end in parts:
        groups = group_words(words)
        for gi, g in enumerate(groups):
            texts = [clean(w["word"]).upper() for w in g]
            next_start = groups[gi + 1][0]["start"] if gi + 1 < len(groups) else part_end
            for wi, w in enumerate(g):
                s = w["start"]
                if wi + 1 < len(g):
                    e = g[wi + 1]["start"]
                else:
                    e = min(next_start, w["end"] + 0.4)
                body = " ".join(f"{hi}{t}{lo}" if j == wi else t for j, t in enumerate(texts))
                lines.append(f"Dialogue: 0,{ass_time(s)},{ass_time(e)},Cap,,0,0,0,,"
                             rf"{{\an5\pos({OUT_W // 2},{CAPTION_Y})}}{body}")
    Path(path).write_text("\n".join(lines) + "\n")


def fix_word(word, fixes):
    """Replace a misheard caption word ({"train": "Trey"}), keeping trailing punctuation."""
    core = word.strip()
    trail = ""
    while core and core[-1] in ".,!?;:":
        core, trail = core[:-1], core[-1] + trail
    for wrong, right in fixes.items():
        if core.lower() == wrong.lower():
            return " " + right + trail if right else ""
    return word


def merge_split_numbers(words):
    """Whisper splits "100,000" into "100" + ",000"; join them back into one caption word."""
    merged = []
    for w in words:
        if merged and re.match(r"^[,.]\d{3}", w["word"].strip()) and re.search(r"\d$", merged[-1]["word"].strip()):
            merged[-1] = dict(merged[-1], word=merged[-1]["word"].rstrip() + w["word"].strip(), end=w["end"])
        else:
            merged.append(w)
    return merged


def snap(words, start, end):
    inside = [w for w in words if w["start"] >= start - 0.3 and w["end"] <= end + 0.3]
    if not inside:
        return start, end
    after = [w for w in words if w["start"] > inside[-1]["end"]]
    t1 = inside[-1]["end"] + 0.35
    if after:
        t1 = min(t1, after[0]["start"] - 0.02)
    return max(0.0, inside[0]["start"] - 0.12), t1


def render_clip(src, words, clip, out_dir, W, H, fps_str, fps):
    """A clip is one range ("start"/"end") or several ("parts": [[s, e], ...]) joined with hard cuts."""
    ranges = [snap(words, s, e) for s, e in clip.get("parts", [[clip.get("start"), clip.get("end")]])]
    name = f"clip_{clip['id']}"
    ass_path = out_dir / f"{name}.ass"

    ass_parts, plans, offset = [], [], 0.0
    for t0, t1 in ranges:
        shifted = [dict(w, word=fix_word(w["word"], clip.get("fixes", {})),
                        start=w["start"] - t0 + offset, end=w["end"] - t0 + offset)
                   for w in words if w["start"] >= t0 - 0.05 and w["end"] <= t1 + 0.05]
        ass_parts.append((shifted, t1 - t0 + offset))
        n, cuts, faces = analyze(src, t0, t1 - t0, W)
        cw, x0, layout = plan(n, cuts, faces, W, H, fps)
        plans.append((n, x0, layout))
        offset += t1 - t0
    build_ass(ass_parts, clip.get("hook"), ass_path)
    all_layout = np.concatenate([p[2] for p in plans])
    fit_share = float(np.mean(all_layout == "fit")) if len(all_layout) else 0.0
    print(f"{name}: {len(ranges)} part(s), {offset:.1f}s, fit={fit_share:.0%}", flush=True)

    audio_in, audio_fx = [], []
    for k, (t0, t1) in enumerate(ranges):
        d = t1 - t0
        audio_in += ["-ss", f"{t0:.3f}", "-t", f"{d:.3f}", "-i", src]
        audio_fx.append(f"[{k + 1}:a]afade=t=in:d=0.03,afade=t=out:st={d - 0.03:.3f}:d=0.03[a{k}]")
    concat_in = "".join(f"[a{k}]" for k in range(len(ranges)))
    graph = ";".join([f"[0:v]ass={ass_path}:fontsdir={FONTS_DIR}[v]", *audio_fx,
                      f"{concat_in}concat=n={len(ranges)}:v=0:a=1[a]"])
    enc = subprocess.Popen(
        [FFMPEG, "-v", "error", "-y",
         "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{OUT_W}x{OUT_H}", "-framerate", fps_str, "-i", "-",
         *audio_in, "-filter_complex", graph, "-map", "[v]", "-map", "[a]",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-shortest",
         str(out_dir / f"{name}.mp4")],
        stdin=subprocess.PIPE)
    size = W * H * 3
    for (t0, t1), (n, x0, layout) in zip(ranges, plans):
        dec = decode(src, t0, t1 - t0)
        i = 0
        while True:
            buf = dec.stdout.read(size)
            if len(buf) < size:
                break
            frame = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
            k = min(i, n - 1)
            enc.stdin.write(compose(frame, x0[k], cw, layout[k], W, H).tobytes())
            i += 1
        dec.wait()
    enc.stdin.close()
    if enc.wait() != 0:
        raise SystemExit(f"encoder failed for {name}")
    ass_path.unlink()
    return {"id": clip["id"], "file": f"{name}.mp4", "hook": clip.get("hook"),
            "source_ranges": [[round(a, 2), round(b, 2)] for a, b in ranges],
            "duration": round(offset, 1), "fit_share": round(fit_share, 2)}


def main():
    src, transcript, clips_path, out_dir = sys.argv[1:5]
    only = set(sys.argv[5:])
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    words = merge_split_numbers(
        [w for seg in json.loads(Path(transcript).read_text())["segments"] for w in seg.get("words", [])])
    clips = json.loads(Path(clips_path).read_text())
    W, H, fps_str, fps = probe(src)
    log_path = out_dir / "render_log.json"
    # Re-rendering a subset keeps the other clips' entries in the log.
    log = {r["id"]: r for r in json.loads(log_path.read_text())} if only and log_path.exists() else {}
    for c in clips:
        if not only or c["id"] in only:
            log[c["id"]] = render_clip(src, words, c, out_dir, W, H, fps_str, fps)
    order = [c["id"] for c in clips]
    log_path.write_text(json.dumps(sorted(log.values(), key=lambda r: order.index(r["id"])
                                          if r["id"] in order else len(order)), indent=2))


if __name__ == "__main__":
    main()
