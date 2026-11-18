#!/usr/bin/env bash
# Usage: ./check_all.sh [videos_dir] [outputs_dir]
set -uo pipefail
VID="${1:-data/videos}"; OUT="${2:-outputs}"
echo "== unit tests =="; python3 -m pytest -q || exit 1
echo "== batch run =="; ./run_batch.sh "$VID" "$OUT" || exit 1
echo "== local checker =="; python3 code/submission/check_output.py "$OUT" "$VID" || exit 1
if [ -f validate.py ]; then
  echo "== official validator =="
  echo "(edit this line to match validate.py's real usage once you have read it)"
  python3 validate.py "$OUT" || exit 1
fi
echo "ALL CHECKS PASSED"
