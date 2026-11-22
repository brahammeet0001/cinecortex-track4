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


def test_end_to_end_official_schema_and_budget(tmp_path):
    video = tmp_path / "unit_001.mp4"
    out = tmp_path / "unit_001.json"
    make_video(video)
    subprocess.run([sys.executable, str(ROOT / "code" / "main.py"), str(video), str(out)], check=True)
    data = json.loads(out.read_text())
    assert set(data) == {"team_id", "video_id", "duration_sec", "label", "actions", "highlights"}
    assert data["video_id"] == "unit_001"
    assert data["label"]["name"] == "other"
    assert data["actions"] == []  # fallback does not invent semantic actions
    assert data["highlights"]
    assert any(h["segment"][1] - h["segment"][0] >= 4.0 for h in data["highlights"])

    sys.path.insert(0, str(ROOT / "code"))
    from selection.budget import budget_ratio
    intervals = [tuple(h["segment"]) for h in data["highlights"]]
    assert budget_ratio(intervals, data["duration_sec"]) <= 0.15 + 1e-9
    assert intervals == sorted(intervals)
    assert all(a[1] <= b[0] for a, b in zip(intervals, intervals[1:]))


def test_manifest_driven_epic_label(tmp_path):
    # Use the real manifest ID, but a short synthetic file; duration mismatch
    # remains within the validator tolerance only when it matches the row, so
    # this test targets the deterministic label adapter directly.
    sys.path.insert(0, str(ROOT / "code"))
    from main import _parse_label, load_resources
    _, vocab = load_resources()
    assert _parse_label({"label": "other", "label_score": 0.2},
                        "epic_kitchens_100", vocab["labels"]) == {"name": "cooking", "score": 1.0}


def test_missing_video_fails_cleanly(tmp_path):
    result = subprocess.run([sys.executable, str(ROOT / "code" / "main.py"),
                             str(tmp_path / "nope.mp4"), str(tmp_path / "o.json")],
                            capture_output=True, text=True)
    assert result.returncode == 1
    assert "ERROR" in result.stderr


def test_external_perception_plugin_is_adapted_and_cleaned(tmp_path):
    video = tmp_path / "plugin_video.mp4"
    out = tmp_path / "plugin_video.json"
    make_video(video, seconds=10)
    plugin = tmp_path / "fake_perception.py"
    plugin.write_text('''
def predict(video_path, meta):
    return {
        "label": {"name": "ski", "score": 0.82},
        "actions": [
            {"start": -1, "end": 3, "verb": "cut", "noun": "onion", "score": 1.2},
            {"start": 1, "end": 5, "verb": "not-a-verb", "noun": "onion", "score": 0.9}
        ],
        "highlights": [{"start": 0, "end": 4, "importance": 0.9}],
        "perception_source": "test_plugin"
    }
''')
    import os
    env = os.environ.copy()
    env["CINECORTEX_PERCEPTION_PLUGIN"] = "fake_perception:predict"
    env["PYTHONPATH"] = str(tmp_path) + os.pathsep + env.get("PYTHONPATH", "")
    subprocess.run([sys.executable, str(ROOT / "code" / "main.py"), str(video), str(out)],
                   check=True, env=env)
    data = json.loads(out.read_text())
    assert data["label"] == {"name": "ski", "score": 0.82}
    assert data["actions"] == [{
        "segment": [0.0, 3.0], "verb": "cut", "noun": "onion", "score": 1.0
    }]
    assert data["highlights"] == [{"segment": [0.0, 4.0]}]
