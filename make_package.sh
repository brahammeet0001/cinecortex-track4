#!/usr/bin/env bash
# Usage: ./make_package.sh <TEAM_ID>   -> creates ../<TEAM_ID>.zip
set -euo pipefail
TEAM_ID="${1:?Usage: make_package.sh TEAM_ID}"
HERE="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp -d)"
mkdir -p "$TMP/$TEAM_ID"
rsync -a --exclude='.venv' --exclude='data' --exclude='.git' --exclude='logs' \
      --exclude='highlights' --exclude='__pycache__' --exclude='.DS_Store' --exclude='demo.sh' --exclude='team_id.txt.bak' \
      "$HERE/" "$TMP/$TEAM_ID/"
(cd "$TMP" && zip -rq "$HERE/../${TEAM_ID}.zip" "$TEAM_ID")
echo "Created $(cd "$HERE/.." && pwd)/${TEAM_ID}.zip"
ls -lh "$HERE/../${TEAM_ID}.zip"
