import importlib.util
import json
import os
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "check_package", Path(__file__).resolve().parents[1] / "code" / "tools" / "check_package.py")
cp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cp)


def make_pkg(root, ids=("A_1", "B_2"), team="team_x"):
    root = Path(root)
    for d in ("code", "weights", "outputs", "data_manifest"):
        (root / d).mkdir(parents=True, exist_ok=True)
    (root / "run.sh").write_text("#!/bin/bash\npython3 code/main.py \"$1\" \"$2\"\n")
    os.chmod(root / "run.sh", 0o755)
    (root / "requirements.txt").write_text("numpy==2.5.5\n")
    (root / "README.md").write_text("# x\n")
    (root / "code" / "main.py").write_text("print('hi')\n")
    man = root / "data_manifest" / "manifest.csv"
    man.write_text("video_id,duration_sec,dataset\n" + "".join(f"{i},100,epic_kitchens_100\n" for i in ids))
    for i in ids:
        (root / "outputs" / f"{i}.json").write_text(json.dumps({
            "team_id": team, "video_id": i, "duration_sec": 100.0,
            "label": {"name": "cooking", "score": 0.9}, "actions": [],
            "highlights": [{"segment": [0, 15]}]}))
    return str(man)


def run(root, man, **kw):
    return cp.run_checks(root, manifest=man, **kw)


def test_valid_package_passes_final(tmp_path):
    man = make_pkg(tmp_path)
    errs, _ = run(tmp_path, man, team_id="team_x", final=True)
    assert errs == [], errs


def test_missing_output_warning_then_error(tmp_path):
    man = make_pkg(tmp_path)
    (tmp_path / "outputs" / "B_2.json").unlink()
    e1, w1 = run(tmp_path, man)
    assert e1 == [] and any("no output" in w for w in w1)
    e2, _ = run(tmp_path, man, final=True)
    assert any("no output" in e for e in e2)


def test_video_inside_package_is_error(tmp_path):
    man = make_pkg(tmp_path)
    (tmp_path / "weights" / "clip.mp4").write_bytes(b"x")
    errs, _ = run(tmp_path, man)
    assert any("video file" in e for e in errs)


def test_hardcoded_video_id_is_error(tmp_path):
    man = make_pkg(tmp_path)
    (tmp_path / "code" / "cheat.py").write_text("if vid == 'A_1':\n    pass\n")
    errs, _ = run(tmp_path, man)
    assert any("A_1" in e and "cheat.py" in e for e in errs)


def test_similar_id_substring_is_not_flagged(tmp_path):
    man = make_pkg(tmp_path)
    (tmp_path / "code" / "ok.py").write_text("x = 'A_10'\n")
    errs, _ = run(tmp_path, man)
    assert not any("ok.py" in e for e in errs)


def test_placeholder_team_id(tmp_path):
    man = make_pkg(tmp_path, team="TEAM_ID")
    e1, w1 = run(tmp_path, man)
    assert e1 == [] and any("placeholder" in w for w in w1)
    e2, _ = run(tmp_path, man, final=True)
    assert any("placeholder" in e for e in e2)


def test_mixed_and_wrong_team_ids(tmp_path):
    man = make_pkg(tmp_path)
    d = json.loads((tmp_path / "outputs" / "B_2.json").read_text())
    d["team_id"] = "other"
    (tmp_path / "outputs" / "B_2.json").write_text(json.dumps(d))
    errs, _ = run(tmp_path, man)
    assert any("differs" in e for e in errs)
    man2 = make_pkg(tmp_path / "p2")
    errs2, _ = run(tmp_path / "p2", man2, team_id="not_x")
    assert any("expected" in e for e in errs2)


def test_run_sh_not_executable(tmp_path):
    man = make_pkg(tmp_path)
    os.chmod(tmp_path / "run.sh", 0o644)
    errs, _ = run(tmp_path, man)
    assert any("executable" in e for e in errs)


def test_extra_output_and_bad_json(tmp_path):
    man = make_pkg(tmp_path)
    (tmp_path / "outputs" / "Z_9.json").write_text(json.dumps({"video_id": "Z_9"}))
    (tmp_path / "outputs" / "A_1.json").write_text("{not json")
    errs, warns = run(tmp_path, man, final=True)
    assert any("invalid JSON" in e for e in errs)
    assert any("not in manifest" in e for e in errs)


def test_network_call_is_warning(tmp_path):
    man = make_pkg(tmp_path)
    (tmp_path / "code" / "net.py").write_text("import requests\nrequests.get('http://x')\n")
    errs, warns = run(tmp_path, man)
    assert errs == [] and any("download" in w for w in warns)


def test_video_in_local_data_dir_is_warning_until_final(tmp_path):
    man = make_pkg(tmp_path)
    (tmp_path / "data" / "videos").mkdir(parents=True)
    (tmp_path / "data" / "videos" / "x.mp4").write_bytes(b"x")
    e1, w1 = run(tmp_path, man)
    assert e1 == [] and any("video file" in w for w in w1)
    e2, _ = run(tmp_path, man, final=True)
    assert any("video file" in e for e in e2)


def test_checker_does_not_flag_itself(tmp_path):
    man = make_pkg(tmp_path)
    (tmp_path / "code" / "tools").mkdir()
    import shutil
    shutil.copy(cp.__file__, tmp_path / "code" / "tools" / "check_package.py")
    errs, warns = run(tmp_path, man)
    assert errs == [] and not any("check_package.py" in w for w in warns)
