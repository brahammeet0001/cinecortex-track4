import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ingest.probe import probe
from selection.budget import within_budget


def main(video_path, out_path):
    meta = probe(video_path)
    dur = meta["duration_s"]

    # PLACEHOLDER highlight: first 10% of the video. B replaces this with the real selector.
    highlights = [{"start": 0.0, "end": round(0.10 * dur, 2), "importance": 0.5}]
    assert within_budget([(h["start"], h["end"]) for h in highlights], dur)

    result = {
        "video_id": meta["video_id"],
        "label": "unknown",  # must match supported_classes.json once we have it
        "actions": [],
        "highlights": highlights,
    }
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(result, indent=2))
    print(f"Wrote {out_path} ({dur:.1f}s, {meta['fps']:.2f} fps)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: main.py <video.mp4> <out.json>", file=sys.stderr)
        sys.exit(2)
    try:
        main(sys.argv[1], sys.argv[2])
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
