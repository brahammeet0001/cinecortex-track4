#!/usr/bin/env bash
# Usage: ./check_all.sh [videos_dir] [outputs_dir]
set -uo pipefail
VID="${1:-data/videos}"; OUT="${2:-outputs}"
echo "== unit tests =="; python3 -m pytest -q || exit 1
echo "== manifest (official rows + any local videos) =="
python3 code/submission/make_test_manifest.py "$VID" data_manifest/manifest.csv data/test_manifest.csv || exit 1
echo "== batch run =="; ./run_batch.sh "$VID" "$OUT" || exit 1
echo "== local checker =="; python3 code/submission/check_output.py "$OUT" "$VID" || exit 1
echo "== official validator =="
python3 code/evaluation/validate_official.py --dir "$OUT" \
  --manifest data/test_manifest.csv --classes data_manifest/supported_classes.json || exit 1
echo "ALL CHECKS PASSED"
