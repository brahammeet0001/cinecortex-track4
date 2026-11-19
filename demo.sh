#!/usr/bin/env bash
# Demo helper: shows each command, pauses, then runs it. Usage: ./demo.sh [video_id]
VID="${1:-test_001}"
VIDEO="data/videos/${VID}.mp4"
OUT="outputs/${VID}.json"
CLIP="highlights/${VID}_highlight.mp4"

step () {            # step "title"
  echo
  echo "=============================================="
  echo "  $1"
  echo "=============================================="
  sleep 2
}
run () {             # run <command...>: show it, pause, execute it
  echo "\$ $*"
  sleep 2
  eval "$*"
  sleep 3
}

clear
step "CineCorteX: Track 04, action-aware video summarization"
sleep 2

step "1. Input: a first-person video"
run "ffprobe -v error -show_entries format=duration -of default=nw=1 $VIDEO"

step "2. One command runs the pipeline"
run "./run.sh $VIDEO $OUT"

step "3. Output: one JSON per video"
run "cat $OUT"

step "4. Validate the output and the 15% budget"
run "python3 code/submission/check_output.py outputs data/videos"

step "5. Compile the highlight video from the JSON"
run "python3 code/submission/compile_highlights.py $VIDEO $OUT $CLIP"
run "ffprobe -v error -show_entries format=duration -of default=nw=1 $CLIP"

step "6. Done: highlight is at most 15% of the original"
sleep 3
