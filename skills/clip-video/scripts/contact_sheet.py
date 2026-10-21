"""Build contact sheets to eyeball crops, captions and hook titles.

Six evenly spaced frames per clip form one row; five rows make one sheet.

Usage: python contact_sheet.py <clips_dir> <sheet_dir>
Prints the path of every sheet written.
"""
import subprocess
import sys
from pathlib import Path

FFMPEG = "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg"
FFPROBE = "/opt/homebrew/opt/ffmpeg-full/bin/ffprobe"
FRAMES, ROWS = 6, 5


def run(*args):
    subprocess.run([FFMPEG, "-v", "error", "-y", *args], check=True)


def main():
    clips = sorted(Path(sys.argv[1]).glob("clip_*.mp4"))
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)

    rows = []
    for clip in clips:
        dur = float(subprocess.run(
            [FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(clip)],
            capture_output=True, text=True, check=True).stdout)
        frames = []
        for k in range(FRAMES):
            t = 0.8 + k * (dur - 1.6) / (FRAMES - 1)
            frame = out / f"{clip.stem}_{k}.png"
            run("-ss", f"{t:.2f}", "-i", str(clip), "-frames:v", "1", "-vf", "scale=180:320", str(frame))
            frames.append(frame)
        row = out / f"row_{clip.stem}.png"
        run(*[a for f in frames for a in ("-i", str(f))], "-filter_complex", f"hstack={FRAMES}", str(row))
        for frame in frames:
            frame.unlink()
        rows.append(row)

    for i in range(0, len(rows), ROWS):
        chunk = rows[i:i + ROWS]
        sheet = out / f"sheet_{i // ROWS + 1}.png"
        if len(chunk) == 1:
            chunk[0].replace(sheet)
        else:
            run(*[a for r in chunk for a in ("-i", str(r))], "-filter_complex", f"vstack={len(chunk)}", str(sheet))
            for r in chunk:
                r.unlink()
        print(sheet)


if __name__ == "__main__":
    main()
