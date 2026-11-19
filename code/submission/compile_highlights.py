"""Usage: python code/submission/compile_highlights.py <video.mp4> <result.json> <out.mp4>
Cuts the highlight segments from the original video and joins them into one MP4 (video only)."""
import json
import subprocess
import sys
from pathlib import Path


def compile_highlights(video, result_json, out_mp4):
    d = json.loads(Path(result_json).read_text())
    ivs = sorted(tuple(h["segment"]) for h in d["highlights"] if h["segment"][1] > h["segment"][0])
    if not ivs:
        raise ValueError("No highlight segments to compile")
    expr = "+".join(f"between(t,{s:.3f},{e:.3f})" for s, e in ivs)
    vf = f"select='{expr}',setpts=N/FRAME_RATE/TB"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(video),
           "-vf", vf, "-an", str(out_mp4)]
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    compile_highlights(*sys.argv[1:])
    print(f"Wrote {sys.argv[3]}")
