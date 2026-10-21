"""Transcribe a 16 kHz mono WAV with mlx-whisper, keeping word-level timestamps.

Usage: python transcribe.py <audio.wav> <out_dir> [--language xx] [--prompt "names, terms"]
Without --language, Whisper detects the spoken language. --prompt biases the
spelling of names Whisper would otherwise mishear ("Trey" heard as "train").
Writes transcript.json (full result), transcript.txt (one timestamped line per
segment) and language.txt (the spoken language code Whisper used).
"""
import argparse
import json
import os
import time
from pathlib import Path

import mlx_whisper

# mlx-whisper shells out to `ffmpeg` to read audio; make sure one exists even
# when only the keg-only ffmpeg-full is installed.
os.environ["PATH"] = "/opt/homebrew/opt/ffmpeg-full/bin:" + os.environ.get("PATH", "")

parser = argparse.ArgumentParser()
parser.add_argument("audio")
parser.add_argument("out_dir", type=Path)
parser.add_argument("--language", default=None, help="force the spoken language, e.g. en, es")
parser.add_argument("--prompt", default=None,
                    help="names and terms to bias spelling, e.g. 'MrBeast challenge with Sarah and Trey.'")
args = parser.parse_args()
args.out_dir.mkdir(parents=True, exist_ok=True)

if args.prompt:
    # With condition_on_previous_text=False, mlx-whisper drops initial_prompt after
    # the first 30 s window. Re-inject it into every window whose prompt is empty.
    import importlib

    # The package re-exports a function named `transcribe`, so fetch the module itself.
    _t = importlib.import_module("mlx_whisper.transcribe")
    _options = _t.DecodingOptions

    def _keep_prompt(**kw):
        if not kw.get("prompt"):
            kw["prompt"] = args.prompt
        return _options(**kw)

    _t.DecodingOptions = _keep_prompt

t0 = time.time()
result = mlx_whisper.transcribe(
    args.audio,
    path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
    language=args.language,
    initial_prompt=args.prompt,
    word_timestamps=True,
    condition_on_previous_text=False,
)
print(f"transcribed in {time.time() - t0:.0f}s, {len(result['segments'])} segments, language={result['language']}")

(args.out_dir / "transcript.json").write_text(json.dumps(result, ensure_ascii=False))
(args.out_dir / "language.txt").write_text(result["language"] + "\n")


def ts(sec):
    m, s = divmod(sec, 60)
    return f"{int(m):02d}:{s:05.2f}"


lines = [f"[{ts(seg['start'])}-{ts(seg['end'])}] {seg['text'].strip()}" for seg in result["segments"]]
(args.out_dir / "transcript.txt").write_text("\n".join(lines) + "\n")
