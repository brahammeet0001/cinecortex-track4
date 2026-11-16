#!/usr/bin/env bash
set -euo pipefail
if [ $# -ne 2 ]; then
  echo "Usage: run.sh <video.mp4> <out.json>" >&2
  exit 2
fi
HERE="$(cd "$(dirname "$0")" && pwd)"
python3 "$HERE/code/main.py" "$1" "$2"
