"""Local check for the official schema. Usage: check_output.py <outputs_dir> <videos_dir>
The authoritative check is code/evaluation/validate_official.py; run both."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ingest.probe import probe
from submission.schema import load_classes

KEYS = {"team_id", "video_id", "duration_sec", "label", "actions", "highlights"}
CAP = 0.15


def num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def check(jp, vp, classes):
    labels, verbs, nouns = classes
    try:
        d = json.loads(Path(jp).read_text())
    except Exception as e:
        return [f"invalid JSON: {e}"]
    errs = []
    if set(d) != KEYS:
        return [f"keys {sorted(d)} != {sorted(KEYS)}"]
    dur = probe(vp)["duration_s"]
    if d["video_id"] != Path(jp).stem:
        errs.append("video_id does not match filename")
    if not num(d["duration_sec"]) or abs(d["duration_sec"] - dur) > 0.5:
        errs.append(f"duration_sec {d['duration_sec']} vs {dur:.2f}")
    lab = d["label"]
    if not (isinstance(lab, dict) and lab.get("name") in labels and num(lab.get("score"))
            and 0 <= lab["score"] <= 1):
        errs.append("bad label")
    for i, a in enumerate(d["actions"]):
        seg = a.get("segment")
        if not (isinstance(seg, list) and len(seg) == 2 and all(num(v) for v in seg)
                and 0 <= seg[0] < seg[1] <= dur + 0.5):
            errs.append(f"action {i}: bad segment")
        if a.get("verb") not in verbs | {"other"} or a.get("noun") not in nouns | {"other"}:
            errs.append(f"action {i}: bad verb/noun")
        if not (num(a.get("score")) and 0 <= a["score"] <= 1):
            errs.append(f"action {i}: bad score")
    segs = []
    for i, h in enumerate(d["highlights"]):
        seg = h.get("segment")
        if set(h) != {"segment"} or not (isinstance(seg, list) and len(seg) == 2
                                         and all(num(v) for v in seg) and 0 <= seg[0] < seg[1] <= dur + 1e-6):
            errs.append(f"highlight {i}: bad")
        else:
            segs.append(tuple(seg))
    if segs:
        if segs != sorted(segs) or any(segs[i][1] > segs[i + 1][0] for i in range(len(segs) - 1)):
            errs.append("highlights not sorted / overlap")
        if sum(e - s for s, e in segs) > CAP * dur:
            errs.append("highlights exceed 15%")
        if max(e - s for s, e in segs) < 4.0:
            errs.append("no highlight >= 4.0 s")
    else:
        errs.append("no highlights")
    return errs


if __name__ == "__main__":
    out_dir, vid_dir = Path(sys.argv[1]), Path(sys.argv[2])
    classes = load_classes()
    bad = 0
    for jp in sorted(out_dir.glob("*.json")):
        vp = vid_dir / f"{jp.stem}.mp4"
        if not vp.exists():
            print(f"SKIP {jp.name}: no video {vp}")
            continue
        errs = check(jp, vp, classes)
        bad += bool(errs)
        print(("FAIL " + jp.name + ": " + "; ".join(errs)) if errs else f"PASS {jp.name}")
    sys.exit(1 if bad else 0)
