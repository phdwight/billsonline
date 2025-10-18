#!/usr/bin/env bash
set -euo pipefail

# Simple macOS screen recording to GIF using ffmpeg.
# Requirements: ffmpeg installed (e.g., `brew install ffmpeg`).
# Usage examples:
#   ./scripts/record_gif.sh out/flow.gif
#   ./scripts/record_gif.sh out/flow.gif 30 1280x800
#   ./scripts/record_gif.sh out/flow.gif 30 1280x800 0.8
#
# Arguments:
#   $1 - output GIF path (required)
#   $2 - frame rate (default: 20)
#   $3 - size WxH (default: 1280x800)
#   $4 - playback speed factor (default: 1.0). Use 0.8 to slow down, 1.2 to speed up.
#
# Notes:
# - On macOS, the screen capture device is `-f avfoundation -i 1:none` for the main display in many cases.
#   You may need to run `ffmpeg -f avfoundation -list_devices true -i ''` to list available devices and adjust.
# - To stop recording, press Ctrl+C.
# - After capturing an intermediate MP4, this script converts it to a compressed GIF using palette for quality.

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <output.gif> [fps=20] [size=1280x800] [speed=1.0]" >&2
  exit 1
fi

OUT_GIF="$1"
FPS="${2:-20}"
SIZE="${3:-1280x800}"
SPEED="${4:-1.0}"

TMP_DIR=$(mktemp -d)
MP4="$TMP_DIR/capture.mp4"
PALETTE="$TMP_DIR/palette.png"

# Record screen to MP4 (Ctrl+C to stop)
# Adjust the avfoundation input index if needed.
echo "Recording... Press Ctrl+C to stop."
ffmpeg -f avfoundation -framerate "$FPS" -i 1:none -video_size "$SIZE" -pix_fmt yuv420p -vf "scale=$SIZE,setpts=PTS/$SPEED" "$MP4"

# Create palette for better GIF quality
ffmpeg -y -i "$MP4" -vf "fps=$FPS,scale=$SIZE:flags=lanczos,palettegen" "$PALETTE"
# Convert to GIF using palette
ffmpeg -y -i "$MP4" -i "$PALETTE" -lavfi "fps=$FPS,scale=$SIZE:flags=lanczos[x];[x][1:v]paletteuse" "$OUT_GIF"

echo "Saved GIF to $OUT_GIF"
