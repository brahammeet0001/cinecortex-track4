#!/usr/bin/env bash
# Usage: ./check_all.sh [videos_dir] [outputs_dir]
# If a raw video directory is supplied/present, run inference before validation.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
VID="${1:-data/videos}"
OUT="${2:-outputs}"

cd "$HERE"
echo "== unit tests =="
python3 -m pytest -q

if [ -d "$VID" ] && find "$VID" -maxdepth 1 -type f -iname '*.mp4' -print -quit | grep -q .; then
  echo "== batch inference =="
  ./run_batch.sh "$VID" "$OUT"
else
  echo "== batch inference skipped: no source videos found in $VID =="
fi

if compgen -G "$OUT/*.json" > /dev/null; then
  echo "== local submission-schema validation (not organiser validate.py) =="
  python3 code/evaluation/validate_official.py \
    --dir "$OUT" \
    --manifest data_manifest/manifest.csv \
    --classes data_manifest/supported_classes.json
else
  echo "== output validation skipped: no JSON files in $OUT =="
fi

if [ -f validate.py ]; then
  echo "== organiser-provided validator =="
  python3 validate.py --dir "$OUT"
else
  echo "NOTE: organiser validate.py is absent from this repository; local checks are not official validation."
fi
