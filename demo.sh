#!/usr/bin/env bash
# Demo helper for screen recording. Usage: ./demo.sh <video.mp4>
set -u
VIDEO="${1:?Usage: ./demo.sh <video.mp4>}"
ID="$(basename "$VIDEO" .mp4)"
OUT="outputs/${ID}.json"
CLIP="highlights/${ID}_highlight.mp4"
mkdir -p outputs highlights

step () { echo; echo "=============================================="; echo "  $1"; echo "=============================================="; sleep 2; }
run () { echo "\$ $*"; sleep 2; eval "$*"; sleep 3; }

clear
step "Hacksmiths: Track 04, action-aware video summarization"
sleep 2
step "1. Input: a first-person video"
run "ffprobe -v error -show_entries format=duration -of default=nw=1 \"$VIDEO\""
step "2. One command runs the pipeline"
run "./run.sh \"$VIDEO\" \"$OUT\""
step "3. Output: one JSON per video (official schema)"
run "cat \"$OUT\""
step "4. Validate against the official schema"
run "python3 code/evaluation/validate_official.py --dir outputs --manifest data_manifest/manifest.csv --classes data_manifest/supported_classes.json"
if [ -f code/submission/compile_highlights.py ]; then
  step "5. Compile the highlight video from the JSON"
  run "python3 code/submission/compile_highlights.py \"$VIDEO\" \"$OUT\" \"$CLIP\""
  run "ffprobe -v error -show_entries format=duration -of default=nw=1 \"$CLIP\""
fi
step "Done: highlights are at most 15% of the original"
sleep 3
