import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


def make_video(path, seconds=40):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi",
                    "-i", f"testsrc=duration={seconds}:size=320x180:rate=25",
                    "-pix_fmt", "yuv420p", str(path)], check=True)


def test_end_to_end_valid_and_within_budget(tmp_path):
    video = tmp_path / "unit_001.mp4"
    out = tmp_path / "unit_001.json"
    make_video(video)
    subprocess.run([sys.executable, str(ROOT / "code" / "main.py"), str(video), str(out)], check=True)
    d = json.loads(out.read_text())
    for key in ("video_id", "label", "actions", "highlights"):
        assert key in d
    assert d["video_id"] == "unit_001"
    sys.path.insert(0, str(ROOT / "code"))
    from selection.budget import budget_ratio
    ivs = [(h["start"], h["end"]) for h in d["highlights"]]
    assert budget_ratio(ivs, 40.0) <= 0.15 + 1e-9


def test_missing_video_fails_cleanly(tmp_path):
    r = subprocess.run([sys.executable, str(ROOT / "code" / "main.py"),
                        str(tmp_path / "nope.mp4"), str(tmp_path / "o.json")],
                       capture_output=True, text=True)
    assert r.returncode == 1
    assert "ERROR" in r.stderr
