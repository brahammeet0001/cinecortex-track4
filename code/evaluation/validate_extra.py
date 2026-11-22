"""Validator for the OFFICIAL Track 04 output schema (TEAM_README.md), in addition to the
organisers' validate.py (which was NOT in the student zip - ask them for it).

Usage (repo root):
  PYTHONPATH=code python -m evaluation.validate_extra --dir outputs/ \
      [--manifest manifest.csv] [--classes supported_classes.json] [--require-all]
Errors  -> file FAILS (scores 0 for that video per the README).
Warnings-> printed only (e.g. budget > 15%, segment < 4 s).
"""
import argparse
import csv
import json
import math
import sys
from pathlib import Path

REQUIRED = ("team_id", "video_id", "duration_sec", "label", "actions", "highlights")
BUDGET = 0.15
MIN_HIGHLIGHT_S = 4.0
DUR_TOL = 0.5
MAX_ACTIONS = 2000


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _segment(seg, dur, tag, errs):
    if not (isinstance(seg, (list, tuple)) and len(seg) == 2 and all(_num(v) for v in seg)):
        errs.append(f"{tag}.segment must be [start, end] with two numbers")
        return None
    s, e = float(seg[0]), float(seg[1])
    if s < 0 or e <= s:
        errs.append(f"{tag}.segment needs 0 <= start < end (got {s}, {e})")
        return None
    if dur is not None and e > dur + DUR_TOL:
        errs.append(f"{tag}.segment end {e} > duration_sec + {DUR_TOL} ({dur + DUR_TOL:.2f})")
    return s, e


def check(data, filename_stem=None, manifest_duration=None, vocab=None):
    """Return (errors, warnings)."""
    errs, warns = [], []
    if not isinstance(data, dict):
        return ["top level is not an object"], warns
    missing = [k for k in REQUIRED if k not in data]
    if missing:
        return [f"missing key '{k}'" for k in missing], warns

    if not isinstance(data["team_id"], str) or not data["team_id"].strip():
        errs.append("team_id must be a non-empty string")
    vid = data["video_id"]
    if not isinstance(vid, str) or not vid:
        errs.append("video_id must be a non-empty string")
    elif filename_stem is not None and vid != filename_stem:
        errs.append(f"video_id '{vid}' != filename '{filename_stem}'")

    dur = data["duration_sec"]
    if not _num(dur) or dur <= 0:
        errs.append("duration_sec must be a positive number")
        dur = None
    elif manifest_duration is not None and abs(dur - manifest_duration) > DUR_TOL:
        errs.append(f"duration_sec {dur} differs from manifest {manifest_duration} by > {DUR_TOL}")

    lab = data["label"]
    if not isinstance(lab, dict) or not isinstance(lab.get("name"), str) or not lab.get("name"):
        errs.append("label must be {'name': str, 'score': number}")
    else:
        if not _num(lab.get("score")) or not (0 <= lab["score"] <= 1):
            errs.append("label.score must be a number in [0, 1]")
        if vocab and vocab.get("labels") and lab["name"] not in vocab["labels"]:
            errs.append(f"label.name '{lab['name']}' not in supported labels")

    acts = data["actions"]
    if not isinstance(acts, list):
        errs.append("actions must be a list")
    else:
        if len(acts) > MAX_ACTIONS:
            errs.append(f"actions has {len(acts)} items (max {MAX_ACTIONS})")
        for i, a in enumerate(acts):
            tag = f"actions[{i}]"
            if not isinstance(a, dict):
                errs.append(f"{tag} is not an object")
                continue
            _segment(a.get("segment"), dur, tag, errs)
            for k in ("verb", "noun"):
                if not isinstance(a.get(k), str) or not a.get(k):
                    errs.append(f"{tag}.{k} must be a non-empty string")
                elif vocab and vocab.get(k + "s") and a[k] not in vocab[k + "s"]:
                    warns.append(f"{tag}.{k} '{a[k]}' not in supported {k}s")
            if not _num(a.get("score")) or not (0 <= a["score"] <= 1):
                errs.append(f"{tag}.score must be a number in [0, 1]")

    hl = data["highlights"]
    if not isinstance(hl, list) or len(hl) < 1:
        errs.append("highlights must be a list with at least 1 item")
    else:
        segs = []
        for i, h in enumerate(hl):
            tag = f"highlights[{i}]"
            if not isinstance(h, dict):
                errs.append(f"{tag} is not an object")
                continue
            sg = _segment(h.get("segment"), dur, tag, errs)
            if sg:
                segs.append((i, sg))
        for (i0, a), (i1, b) in zip(segs, segs[1:]):
            if b[0] < a[0]:
                errs.append(f"highlights not chronologically sorted at index {i1}")
            elif b[0] < a[1]:
                errs.append(f"highlights[{i0}] and highlights[{i1}] overlap")
        if segs and not any(e - s >= MIN_HIGHLIGHT_S - 1e-9 for _, (s, e) in segs):
            errs.append(f"no highlight segment >= {MIN_HIGHLIGHT_S} s")
        short = [i for i, (s, e) in segs if e - s < MIN_HIGHLIGHT_S - 1e-9]
        if short:
            warns.append(f"highlights {short} are < {MIN_HIGHLIGHT_S} s (ignored in scoring)")
        if dur and segs:
            total = sum(e - s for _, (s, e) in segs)
            if total / dur > BUDGET + 1e-9:
                warns.append(f"highlight total is {total / dur:.1%} of duration (> {BUDGET:.0%})")
    return errs, warns


def load_vocab(path):
    """Best effort: structure of supported_classes.json is not documented."""
    try:
        d = json.load(open(path))
    except Exception:
        return None
    if not isinstance(d, dict):
        return None

    def pick(sub):
        for k, v in d.items():
            if sub in k.lower():
                return set(v.keys()) if isinstance(v, dict) else set(map(str, v)) if isinstance(v, list) else None
        return None

    return {"labels": pick("label"), "verbs": pick("verb"), "nouns": pick("noun")}


def load_manifest(path):
    with open(path, newline="") as f:
        return {r["video_id"]: float(r["duration_sec"]) for r in csv.DictReader(f)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--manifest", default=None)
    ap.add_argument("--classes", default=None)
    ap.add_argument("--require-all", action="store_true", help="fail if manifest videos are missing")
    a = ap.parse_args()
    man = load_manifest(a.manifest) if a.manifest else {}
    vocab = load_vocab(a.classes) if a.classes else None
    files = sorted(Path(a.dir).glob("*.json"))
    bad, team_ids = 0, set()
    for f in files:
        try:
            data = json.load(open(f))
        except Exception as ex:
            print(f"FAIL {f.name}: invalid JSON ({ex})")
            bad += 1
            continue
        if isinstance(data, dict) and isinstance(data.get("team_id"), str):
            team_ids.add(data["team_id"])
        errs, warns = check(data, f.stem, man.get(f.stem), vocab)
        if a.manifest and f.stem not in man:
            warns.append("video_id not in manifest")
        if errs:
            bad += 1
            print(f"FAIL {f.name}")
            for e in errs:
                print("   -", e)
        for w in warns:
            print(f"WARN {f.name}: {w}")
    if len(team_ids) > 1:
        print(f"FAIL: team_id differs across files: {sorted(team_ids)}")
        bad += 1
    missing = sorted(set(man) - {f.stem for f in files})
    if man:
        print(f"manifest coverage: {len(man) - len(missing)}/{len(man)} videos have an output file")
        if missing and a.require_all:
            bad += 1
    print(f"{len(files) - bad}/{len(files)} files OK" if bad <= len(files) else f"{bad} problems")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
