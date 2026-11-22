#!/usr/bin/env bash
# Usage: ./make_package.sh <TEAM_ID>
# Creates a complete organiser-style package only after all manifest outputs
# pass this repository's local schema validator.
set -euo pipefail
TEAM_ID="${1:?Usage: make_package.sh TEAM_ID}"
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/outputs"
EXPECTED="$(python3 - "$HERE/data_manifest/manifest.csv" <<'PY'
import csv,sys
with open(sys.argv[1], newline='', encoding='utf-8') as f:
    print(sum(1 for _ in csv.DictReader(f)))
PY
)"
ACTUAL="$(find "$OUT" -maxdepth 1 -type f -name '*.json' 2>/dev/null | wc -l | tr -d ' ')"
if [ "$ACTUAL" -ne "$EXPECTED" ]; then
  echo "REFUSING to package: outputs contains $ACTUAL JSON files; manifest requires $EXPECTED." >&2
  echo "Raw dataset videos are not included in the repository. Generate the missing outputs first." >&2
  exit 1
fi
python3 "$HERE/code/evaluation/validate_official.py" \
  --dir "$OUT" \
  --manifest "$HERE/data_manifest/manifest.csv" \
  --classes "$HERE/data_manifest/supported_classes.json" \
  --require-complete \
  --team-id "$TEAM_ID"

python3 - "$HERE" "$HERE/../${TEAM_ID}.zip" "$TEAM_ID" <<'PY'
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile

source = Path(sys.argv[1]).resolve()
archive = Path(sys.argv[2]).resolve()
team_id = sys.argv[3]
skip_dirs = {".git", ".venv", "__pycache__", ".pytest_cache", "data", "logs", "highlights"}
skip_files = {".DS_Store"}

def ignore(directory, names):
    ignored = {name for name in names if name in skip_dirs or name in skip_files}
    ignored.update(name for name in names if name.lower().endswith(".mp4"))
    return ignored

with tempfile.TemporaryDirectory() as tmp:
    package_root = Path(tmp) / team_id
    shutil.copytree(source, package_root, ignore=ignore)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(package_root.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(Path(tmp)))
print(f"Created {archive} ({archive.stat().st_size:,} bytes)")
PY
