import json
import subprocess
from pathlib import Path


def probe(video_path: str) -> dict:
    p = Path(video_path)
    if not p.is_file():
        raise FileNotFoundError(f"Video not found: {video_path}")

    cmd = ["ffprobe", "-v", "error", "-print_format", "json",
           "-show_format", "-show_streams", str(p)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {res.stderr.strip()}")

    info = json.loads(res.stdout)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    if v is None:
        raise RuntimeError("No video stream found")

    num, den = v["avg_frame_rate"].split("/")
    fps = float(num) / float(den) if float(den) else 0.0
    duration = float(info["format"].get("duration") or v.get("duration") or 0)
    if duration <= 0:
        raise RuntimeError("Could not determine duration")

    return {
        "video_id": p.stem,
        "path": str(p),
        "duration_s": duration,
        "fps": fps,
        "width": int(v["width"]),
        "height": int(v["height"]),
        "codec": v["codec_name"],
        "decode_ok": True,
    }
