import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


def make_video(path, seconds=60):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi",
                    "-i", f"testsrc=duration={seconds}:size=320x180:rate=25",
                    "-pix_fmt", "yuv420p", str(path)], check=True)


def test_end_to_end_official_schema(tmp_path):
    video, out = tmp_path / "unit_001.mp4", tmp_path / "unit_001.json"
    make_video(video)
    subprocess.run([sys.executable, str(ROOT / "code" / "main.py"), str(video), str(out)], check=True)
    d = json.loads(out.read_text())
    assert set(d) == {"team_id", "video_id", "duration_sec", "label", "actions", "highlights"}
    assert d["video_id"] == "unit_001"
    segs = [tuple(h["segment"]) for h in d["highlights"]]
    assert segs == sorted(segs)
    assert sum(e - s for s, e in segs) <= 0.15 * 60
    assert max(e - s for s, e in segs) >= 4.0


def test_missing_video_fails_cleanly(tmp_path):
    r = subprocess.run([sys.executable, str(ROOT / "code" / "main.py"),
                        str(tmp_path / "nope.mp4"), str(tmp_path / "o.json")],
                       capture_output=True, text=True)
    assert r.returncode == 1 and "ERROR" in r.stderr
