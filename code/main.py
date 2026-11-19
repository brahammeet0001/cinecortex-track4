import os
import sys
import json
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingest.probe import probe
from submission.schema import load_classes, to_official


def get_team_id():
    tid = os.environ.get("TEAM_ID")
    if tid:
        return tid.strip()
    f = ROOT / "team_id.txt"
    if f.exists():
        return f.read_text().strip()
    return "TEAM_ID"


def placeholder(meta):
    dur = meta["duration_s"]
    return {"label": "unknown", "actions": [],
            "highlights": [{"start": 0.0, "end": round(0.10 * dur, 2), "importance": 0.5}]}


def baseline(video_path, meta):
    try:
        from perception.baseline import predict as baseline_predict
        print("NOTE: using motion baseline", file=sys.stderr)
        return baseline_predict(video_path, meta)
    except Exception:
        print("WARNING: baseline failed:", file=sys.stderr)
        traceback.print_exc()
        return placeholder(meta)


def get_prediction(video_path, meta):
    try:
        from perception.predict import predict          # Member B's model
    except ImportError:
        print("NOTE: perception.predict not found", file=sys.stderr)
        return baseline(video_path, meta)
    try:
        pred = predict(video_path, meta)
    except Exception:
        print("WARNING: perception.predict failed:", file=sys.stderr)
        traceback.print_exc()
        return baseline(video_path, meta)
    if not pred.get("highlights"):                       # model gave no highlights: borrow baseline's
        pred["highlights"] = baseline(video_path, meta)["highlights"]
    return pred


def main(video_path, out_path):
    meta = probe(video_path)
    pred = get_prediction(video_path, meta)
    result = to_official(meta, pred, load_classes(), get_team_id())
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(result, indent=2))
    total = sum(h["segment"][1] - h["segment"][0] for h in result["highlights"])
    print(f"Wrote {out_path} ({meta['duration_s']:.1f}s, {len(result['highlights'])} segments, "
          f"highlight {total / meta['duration_s']:.1%})")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: main.py <video.mp4> <out.json>", file=sys.stderr)
        sys.exit(2)
    try:
        main(sys.argv[1], sys.argv[2])
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
