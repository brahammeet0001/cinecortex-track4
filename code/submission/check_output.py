"""Local Track 04 schema checker (not the organiser-provided validator).

Usage: python code/submission/check_output.py <outputs_dir>
       python code/submission/check_output.py <outputs_dir> <videos_dir>
The optional videos_dir is retained for backwards compatibility; durations
are checked against the supplied manifest rather than re-probing each video.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "code"))
from evaluation.validate_official import validate


def check(json_path: str | Path, manifest: dict, verbs: set[str], nouns: set[str], labels: set[str]) -> tuple[list[str], list[str]]:
    path = Path(json_path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"invalid JSON: {exc}"], []
    return validate(data, path.stem, manifest, verbs, nouns, labels)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("outputs_dir")
    parser.add_argument("videos_dir", nargs="?", help="Ignored; retained for the legacy CLI")
    args = parser.parse_args()

    manifest = {}
    with (ROOT / "data_manifest" / "manifest.csv").open(newline="", encoding="utf-8") as handle:
        manifest = {r["video_id"]: float(r["duration_sec"]) for r in csv.DictReader(handle)}
    classes = json.loads((ROOT / "data_manifest" / "supported_classes.json").read_text(encoding="utf-8"))
    vocab = set(classes["verbs"]), set(classes["nouns"]), set(classes["labels"])

    files = sorted(Path(args.outputs_dir).glob("*.json"))
    if not files:
        print(f"No JSON files found in {args.outputs_dir}")
        return 1
    bad = 0
    for path in files:
        errors, warnings = check(path, manifest, *vocab)
        print(("PASS " if not errors else "FAIL ") + path.name)
        for error in errors:
            print("  ERROR:", error)
        for warning in warnings:
            print("  warn: ", warning)
        bad += bool(errors)
    print(f"{len(files) - bad}/{len(files)} files pass local checks; manifest contains {len(manifest)} target videos")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
