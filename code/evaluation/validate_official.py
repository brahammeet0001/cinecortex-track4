"""Validate Track 04 output JSONs against the official schema (as understood so far)."""
import argparse
import csv
import json
import sys
from pathlib import Path

KEYS = ["team_id", "video_id", "duration_sec", "label", "actions", "highlights"]
MIN_HL = 4.0
BUDGET = 0.15
DUR_TOL = 0.5


def is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def check_seg(seg, dur, where, errs):
    if not (isinstance(seg, list) and len(seg) == 2 and all(is_num(v) for v in seg)):
        errs.append(f"{where}: segment must be [start, end] numbers")
        return None
    s, e = seg
    if not (0 <= s < e):
        errs.append(f"{where}: need 0 <= start < end, got {seg}")
        return None
    if dur is not None and e > dur + DUR_TOL:
        errs.append(f"{where}: end {e} is past duration {dur}")
    return (s, e)


def validate(obj, stem, manifest, verbs, nouns, labels):
    errs, warns = [], []
    if not isinstance(obj, dict):
        return ["top level must be a JSON object"], []
    missing = [k for k in KEYS if k not in obj]
    extra = [k for k in obj if k not in KEYS]
    if missing:
        errs.append(f"missing keys: {missing}")
    if extra:
        warns.append(f"extra keys: {extra}")

    team = obj.get("team_id")
    if not (isinstance(team, str) and team.strip()):
        errs.append("team_id must be a non-empty string")

    vid = obj.get("video_id")
    if vid != stem:
        errs.append(f"video_id {vid!r} does not match file name {stem!r}")
    if manifest and vid not in manifest:
        warns.append(f"video_id {vid!r} is not in the manifest")

    dur = obj.get("duration_sec")
    if not is_num(dur) or dur <= 0:
        errs.append("duration_sec must be a positive number")
        dur = None
    elif vid in manifest and abs(dur - manifest[vid]) > DUR_TOL:
        errs.append(f"duration_sec {dur} differs from manifest {manifest[vid]} by more than {DUR_TOL}s")

    label = obj.get("label")
    if not isinstance(label, dict) or "name" not in label or "score" not in label:
        errs.append("label must be an object with name and score")
    else:
        if label["name"] not in labels:
            warns.append(f"label name {label['name']!r} is not in supported_classes labels")
        if not (is_num(label["score"]) and 0 <= label["score"] <= 1):
            errs.append("label score must be a number between 0 and 1")

    actions = obj.get("actions")
    if not isinstance(actions, list):
        errs.append("actions must be a list")
    else:
        for i, a in enumerate(actions):
            w = f"actions[{i}]"
            if not isinstance(a, dict):
                errs.append(f"{w}: must be an object")
                continue
            check_seg(a.get("segment"), dur, w, errs)
            if a.get("verb") not in verbs:
                errs.append(f"{w}: verb {a.get('verb')!r} not in supported verbs")
            if a.get("noun") not in nouns:
                errs.append(f"{w}: noun {a.get('noun')!r} not in supported nouns")
            sc = a.get("score")
            if not (is_num(sc) and 0 <= sc <= 1):
                errs.append(f"{w}: score must be a number between 0 and 1")

    hl = obj.get("highlights")
    if not isinstance(hl, list):
        errs.append("highlights must be a list")
    else:
        segs = []
        for i, h in enumerate(hl):
            if not isinstance(h, dict) or "segment" not in h:
                errs.append(f"highlights[{i}]: must be an object with segment")
                continue
            s = check_seg(h["segment"], dur, f"highlights[{i}]", errs)
            if s:
                segs.append(s)
        if segs != sorted(segs):
            errs.append("highlights are not sorted by start time")
        ordered = sorted(segs)
        for a, b in zip(ordered, ordered[1:]):
            if b[0] < a[1]:
                errs.append(f"highlights overlap: {a} and {b}")
        long_ones = [s for s in segs if s[1] - s[0] >= MIN_HL]
        if not long_ones:
            errs.append(f"need at least one highlight of {MIN_HL}s or longer")
        short = len(segs) - len(long_ones)
        if short:
            warns.append(f"{short} highlight(s) shorter than {MIN_HL}s are ignored in scoring")
        total = sum(e - s for s, e in segs)
        if dur and total > BUDGET * dur:
            warns.append(f"highlights use {total / dur:.1%} of the video (limit {BUDGET:.0%})")
    return errs, warns


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--classes", required=True)
    a = ap.parse_args()

    manifest = {}
    with open(a.manifest) as f:
        for r in csv.DictReader(f):
            manifest[r["video_id"]] = float(r["duration_sec"])
    c = json.load(open(a.classes))
    verbs, nouns, labels = set(c["verbs"]), set(c["nouns"]), set(c["labels"])

    files = sorted(Path(a.dir).glob("*.json"))
    ok, teams = 0, set()
    for f in files:
        try:
            obj = json.loads(f.read_text())
        except Exception as ex:
            print(f"FAIL {f.name}: invalid JSON ({ex})")
            continue
        errs, warns = validate(obj, f.stem, manifest, verbs, nouns, labels)
        if isinstance(obj, dict) and isinstance(obj.get("team_id"), str):
            teams.add(obj["team_id"])
        print(("PASS " if not errs else "FAIL ") + f.name)
        for e in errs:
            print("   ERROR:", e)
        for w in warns:
            print("   warn: ", w)
        ok += not errs
    if len(teams) > 1:
        print(f"WARNING: more than one team_id across files: {sorted(teams)}")
    print(f"{ok}/{len(files)} files OK (manifest lists {len(manifest)} videos)")
    sys.exit(0 if ok == len(files) else 1)


if __name__ == "__main__":
    main()
