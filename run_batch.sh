#!/usr/bin/env bash
# Usage: ./run_batch.sh <videos_dir> <outputs_dir>
set -uo pipefail
VID_DIR="${1:-data/videos}"
OUT_DIR="${2:-outputs}"
HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$OUT_DIR" "$HERE/logs"
LOG="$HERE/logs/batch_$(date +%Y%m%d_%H%M%S).log"
shopt -s nullglob nocaseglob
videos=("$VID_DIR"/*.mp4)
shopt -u nullglob nocaseglob
if [ ${#videos[@]} -eq 0 ]; then
  echo "No MP4 files in $VID_DIR" >&2
  exit 1
fi
ok=0; fail=0
for f in "${videos[@]}"; do
  id="$(basename "$f")"
  id="${id%.*}"
  start=$(date +%s)
  if "$HERE/run.sh" "$f" "$OUT_DIR/$id.json" >> "$LOG" 2>&1; then
    echo "OK   $id ($(( $(date +%s) - start ))s)" | tee -a "$LOG"
    ok=$((ok+1))
  else
    echo "FAIL $id" | tee -a "$LOG"
    fail=$((fail+1))
  fi
done
{
  echo "git_commit=$(git -C "$HERE" rev-parse --short HEAD 2>/dev/null || echo none)"
  echo "python=$(python3 --version 2>&1)"
  echo "ffmpeg=$(ffmpeg -version 2>/dev/null | head -1)"
  echo "finished=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "summary=$ok ok, $fail failed"
} | tee -a "$LOG"
echo "Done: $ok ok, $fail failed. Log: $LOG"
[ "$fail" -eq 0 ]
