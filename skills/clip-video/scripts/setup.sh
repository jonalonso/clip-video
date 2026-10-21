#!/usr/bin/env bash
# Checks the clip-video toolchain, installs what is missing, and prints the
# Python interpreter the other scripts must run with.
#   yt-dlp, uv, ffmpeg-full (keg-only, has libass for captions) via Homebrew
#   a Python venv with mlx-whisper, opencv-python, numpy (Apple Silicon only)
# The venv lives outside the skill folder so plugin updates don't wipe it:
#   ${CLIP_VIDEO_HOME:-~/.cache/clip-video}/venv
set -euo pipefail

if [ "$(uname -s)" != "Darwin" ] || [ "$(uname -m)" != "arm64" ]; then
  echo "clip-video needs macOS on Apple Silicon (mlx-whisper)." >&2
  exit 1
fi
command -v brew >/dev/null 2>&1 || { echo "Homebrew is required: https://brew.sh" >&2; exit 1; }

HOME_DIR="${CLIP_VIDEO_HOME:-$HOME/.cache/clip-video}"
VENV="$HOME_DIR/venv"

missing=()
command -v yt-dlp >/dev/null 2>&1 || missing+=(yt-dlp)
command -v uv >/dev/null 2>&1 || missing+=(uv)
[ -x "$(brew --prefix)/opt/ffmpeg-full/bin/ffmpeg" ] || missing+=(ffmpeg-full)
if [ ${#missing[@]} -gt 0 ]; then
  echo "installing with Homebrew: ${missing[*]}"
  HOMEBREW_NO_AUTO_UPDATE=1 brew install "${missing[@]}"
fi

if [ ! -x "$VENV/bin/python" ]; then
  echo "creating $VENV"
  mkdir -p "$HOME_DIR"
  uv venv --python 3.12 -q "$VENV"
  VIRTUAL_ENV="$VENV" uv pip install -q mlx-whisper opencv-python numpy
fi

"$VENV/bin/python" -c 'import mlx_whisper, cv2, numpy'
echo "PYTHON=$VENV/bin/python"
echo "FFBIN=$(brew --prefix)/opt/ffmpeg-full/bin"
