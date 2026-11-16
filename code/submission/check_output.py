"""Local sanity checker. Usage: python code/submission/check_output.py <outputs_dir> <videos_dir>
NOT the official validator: replace/extend with validate.py from the student kit."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ingest.probe import probe
from selection.budget import budget_ratio

REQUIRED = ["video_id", "label", "actions", "highlights"]
LIMIT = 0.15


def check(json_path, video_path):
    errs = []
    d = json.loads(Path(json_path).read_text())
    for k in REQUIRED:
        if k not in d:
            errs.append(f"missing key: {k}")
    if errs:
        return errs
    dur = probe(video_path)["duration_s"]
    if d["video_id"] != Path(json_path).stem:
        errs.append("video_id does not match filename")
    for i, h in enumerate(d["highlights"]):
        s, e = h.get("start"), h.get("end")
        if not isinstance(s, (int, float)) or not isinstance(e, (int, float)):
            errs.append(f"highlight {i}: start/end not numbers")
        elif not (0 <= s < e <= dur + 1e-6):
            errs.append(f"highlight {i}: bad interval [{s}, {e}] for duration {dur:.2f}")
    for i, a in enumerate(d["actions"]):
        s, e = a.get("start"), a.get("end")
        if not isinstance(s, (int, float)) or not isinstance(e, (int, float)) or not (0 <= s < e <= dur + 1e-6):
            errs.append(f"action {i}: bad interval")
    ivs = [(h["start"], h["end"]) for h in d["highlights"]
           if isinstance(h.get("start"), (int, float)) and isinstance(h.get("end"), (int, float))]
    r = budget_ratio(ivs, dur)
    if r > LIMIT:
        errs.append(f"budget exceeded: {r:.3f} > {LIMIT}")
    return errs


if __name__ == "__main__":
    out_dir, vid_dir = Path(sys.argv[1]), Path(sys.argv[2])
    bad = 0
    for jp in sorted(out_dir.glob("*.json")):
        vp = vid_dir / f"{jp.stem}.mp4"
        if not vp.exists():
            print(f"SKIP {jp.name}: no video {vp}")
            continue
        errs = check(jp, vp)
        if errs:
            bad += 1
            print(f"FAIL {jp.name}: " + "; ".join(errs))
        else:
            print(f"PASS {jp.name}")
    sys.exit(1 if bad else 0)
