#!/usr/bin/env bash
# Usage: ./run_batch.sh <videos_dir> <outputs_dir>
set -uo pipefail
VID_DIR="${1:-data/videos}"
OUT_DIR="${2:-outputs}"
HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$OUT_DIR" logs
LOG="logs/batch_$(date +%Y%m%d_%H%M%S).log"
ok=0; fail=0
for f in "$VID_DIR"/*.mp4; do
  [ -e "$f" ] || { echo "No mp4 files in $VID_DIR"; exit 1; }
  id="$(basename "$f" .mp4)"
  start=$(date +%s)
  if "$HERE/run.sh" "$f" "$OUT_DIR/$id.json" >> "$LOG" 2>&1; then
    echo "OK   $id ($(( $(date +%s) - start ))s)" | tee -a "$LOG"; ok=$((ok+1))
  else
    echo "FAIL $id" | tee -a "$LOG"; fail=$((fail+1))
  fi
done
echo "Done: $ok ok, $fail failed. Log: $LOG"
# --- metadata footer ---
{
  echo "git_commit=$(git rev-parse --short HEAD 2>/dev/null || echo none)"
  echo "python=$(python3 --version 2>&1)"
  echo "ffmpeg=$(ffmpeg -version 2>/dev/null | head -1)"
  echo "finished=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} | tee -a "$LOG"
