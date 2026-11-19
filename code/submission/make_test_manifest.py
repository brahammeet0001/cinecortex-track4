"""Usage: make_test_manifest.py <videos_dir> <src_manifest.csv> <dst_manifest.csv>
Copies the official manifest and appends rows for local videos that are not in it."""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ingest.probe import probe


def main(videos_dir, src, dst):
    with open(src, newline="") as f:
        rows = list(csv.reader(f))
    header = rows[0]
    low = [h.strip().lower() for h in header]
    id_col = next((i for i, h in enumerate(low) if "video" in h and "id" in h), None)
    if id_col is None:
        id_col = next((i for i, h in enumerate(low) if h in ("id", "video", "name", "filename")), None)
    dur_col = next((i for i, h in enumerate(low) if "dur" in h), None)
    if id_col is None or dur_col is None:
        print(f"Cannot find id/duration columns in header: {header}")
        sys.exit(1)
    known = {r[id_col] for r in rows[1:] if len(r) > id_col}
    added = 0
    for v in sorted(Path(videos_dir).glob("*.mp4")):
        if v.stem in known or v.name in known:
            continue
        row = [""] * len(header)
        row[id_col] = v.stem
        row[dur_col] = f"{probe(str(v))['duration_s']:.3f}"
        rows.append(row)
        added += 1
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    with open(dst, "w", newline="") as f:
        csv.writer(f).writerows(rows)
    print(f"Wrote {dst} (+{added} local videos)")


if __name__ == "__main__":
    main(*sys.argv[1:4])
