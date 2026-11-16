"""Extra output checks, run IN ADDITION to the official validate.py.

Usage:
  PYTHONPATH=code python -m evaluation.validate_extra --dir outputs/ [--durations durations.json]
durations.json = {"P01_01": 312.4, ...}  (seconds). Without it, duration/budget checks are skipped.
"""
import argparse
import json
import math
import sys
from pathlib import Path

from .intervals import union_duration

REQUIRED = ("video_id", "label", "actions", "highlights")
BUDGET = 0.15
TOLERANCE = 0.005  # absolute tolerance on the ratio; confirm with organisers


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def check(data, filename_stem=None, duration=None):
    """Return a list of error strings (empty list = OK)."""
    errs = []
    if not isinstance(data, dict):
        return ["top level is not an object"]
    for k in REQUIRED:
        if k not in data:
            errs.append(f"missing key '{k}'")
    if errs:
        return errs
    if not isinstance(data["video_id"], str) or not data["video_id"]:
        errs.append("video_id must be a non-empty string")
    elif filename_stem is not None and data["video_id"] != filename_stem:
        errs.append(f"video_id '{data['video_id']}' != filename '{filename_stem}'")
    if not isinstance(data["label"], str):
        errs.append("label must be a string")
    for name, extra in (("actions", ("verb", "noun")), ("highlights", ())):
        if not isinstance(data[name], list):
            errs.append(f"{name} must be a list")
            continue
        for i, it in enumerate(data[name]):
            tag = f"{name}[{i}]"
            if not isinstance(it, dict):
                errs.append(f"{tag} is not an object")
                continue
            for k in extra:
                if not isinstance(it.get(k), str) or not it.get(k):
                    errs.append(f"{tag}.{k} must be a non-empty string")
            s, e = it.get("start"), it.get("end")
            if not (_num(s) and _num(e)):
                errs.append(f"{tag} start/end must be finite numbers")
                continue
            if s < 0 or e <= s:
                errs.append(f"{tag} needs 0 <= start < end (got {s}, {e})")
            if duration is not None and e > duration + 1e-6:
                errs.append(f"{tag} end {e} beyond video duration {duration}")
            if name == "highlights":
                imp = it.get("importance")
                if not _num(imp) or not (0 <= imp <= 1):
                    errs.append(f"{tag}.importance must be a number in [0,1]")
    if duration and isinstance(data["highlights"], list) and not errs:
        ratio = union_duration([(h["start"], h["end"]) for h in data["highlights"]]) / duration
        if ratio > BUDGET + TOLERANCE:
            errs.append(f"highlight union is {ratio:.1%} of video (> {BUDGET:.0%})")
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--durations", default=None)
    a = ap.parse_args()
    durs = json.load(open(a.durations)) if a.durations else {}
    bad = 0
    files = sorted(Path(a.dir).glob("*.json"))
    for f in files:
        try:
            data = json.load(open(f))
        except Exception as ex:  # invalid JSON
            print(f"FAIL {f.name}: invalid JSON ({ex})")
            bad += 1
            continue
        errs = check(data, f.stem, durs.get(f.stem))
        if errs:
            bad += 1
            print(f"FAIL {f.name}")
            for e in errs:
                print("   -", e)
    print(f"{len(files) - bad}/{len(files)} files OK")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
