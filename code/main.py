import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingest.probe import probe
from selection.budget import within_budget, union_duration

LIMIT = 0.15


def placeholder(meta):
    dur = meta["duration_s"]
    return {
        "label": "unknown",
        "actions": [],
        "highlights": [{"start": 0.0, "end": round(0.10 * dur, 2), "importance": 0.5}],
    }


def get_prediction(video_path, meta):
    # 1) Member B's model
    try:
        from perception.predict import predict
        try:
            return predict(video_path, meta)
        except Exception:
            print("WARNING: perception.predict failed:", file=sys.stderr)
            traceback.print_exc()
    except ImportError:
        print("NOTE: perception.predict not found", file=sys.stderr)
    # 2) motion baseline
    try:
        from perception.baseline import predict as baseline_predict
        print("NOTE: using motion baseline", file=sys.stderr)
        return baseline_predict(video_path, meta)
    except Exception:
        print("WARNING: baseline failed:", file=sys.stderr)
        traceback.print_exc()
    # 3) placeholder
    print("NOTE: using placeholder", file=sys.stderr)
    return placeholder(meta)


def enforce_budget(highlights, dur):
    """Keep highest-importance intervals first until the 15% budget is full."""
    kept = []
    for h in sorted(highlights, key=lambda x: x.get("importance", 0), reverse=True):
        trial = kept + [h]
        if within_budget([(x["start"], x["end"]) for x in trial], dur, LIMIT):
            kept.append(h)
    return sorted(kept, key=lambda x: x["start"])


def main(video_path, out_path):
    meta = probe(video_path)
    dur = meta["duration_s"]
    pred = get_prediction(video_path, meta)

    highlights = [h for h in pred.get("highlights", [])
                  if 0 <= h["start"] < h["end"] <= dur + 1e-6]
    if not within_budget([(h["start"], h["end"]) for h in highlights], dur, LIMIT):
        print("WARNING: highlights exceed 15%, trimming", file=sys.stderr)
        highlights = enforce_budget(highlights, dur)

    result = {
        "video_id": meta["video_id"],
        "label": pred.get("label", "unknown"),
        "actions": pred.get("actions", []),
        "highlights": highlights,
    }
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(result, indent=2))
    used = union_duration([(h["start"], h["end"]) for h in highlights])
    print(f"Wrote {out_path} ({dur:.1f}s, {meta['fps']:.2f} fps, highlight {used / dur:.1%})")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: main.py <video.mp4> <out.json>", file=sys.stderr)
        sys.exit(2)
    try:
        main(sys.argv[1], sys.argv[2])
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
