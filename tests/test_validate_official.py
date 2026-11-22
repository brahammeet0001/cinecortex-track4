import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
from evaluation.validate_official import validate

VERBS = {"cut", "other"}
NOUNS = {"onion", "other"}
LABELS = {"cooking", "other"}
MANIFEST = {"v1": 100.0}


def good():
    return {
        "team_id": "T01", "video_id": "v1", "duration_sec": 100.0,
        "label": {"name": "cooking", "score": 0.9},
        "actions": [{"segment": [1.0, 3.0], "verb": "cut", "noun": "onion", "score": 0.8}],
        "highlights": [{"segment": [10.0, 20.0]}],
    }


def run(obj, stem="v1"):
    return validate(obj, stem, MANIFEST, VERBS, NOUNS, LABELS)


def test_good_passes():
    errs, _ = run(good())
    assert errs == []


def test_missing_key():
    o = good()
    del o["team_id"]
    assert run(o)[0]


def test_label_must_be_object():
    o = good()
    o["label"] = "cooking"
    assert run(o)[0]


def test_duration_mismatch():
    o = good()
    o["duration_sec"] = 101.0
    assert run(o)[0]


def test_video_id_must_match_filename():
    assert run(good(), stem="other_name")[0]


def test_unknown_verb_is_an_error():
    o = good()
    o["actions"][0]["verb"] = "teleport"
    errs, warns = run(o)
    assert errs and any("supported_classes" in e for e in errs)


def test_non_finite_score_is_an_error():
    o = good()
    o["actions"][0]["score"] = float("nan")
    assert run(o)[0]


def test_too_many_actions():
    o = good()
    o["actions"] = o["actions"] * 2001
    assert run(o)[0]


def test_overlapping_highlights():
    o = good()
    o["highlights"] = [{"segment": [10, 20]}, {"segment": [15, 25]}]
    assert run(o)[0]


def test_unsorted_highlights():
    o = good()
    o["highlights"] = [{"segment": [50, 60]}, {"segment": [10, 20]}]
    assert run(o)[0]


def test_all_highlights_too_short():
    o = good()
    o["highlights"] = [{"segment": [10, 12]}]
    assert run(o)[0]


def test_over_budget_is_only_a_warning():
    o = good()
    o["highlights"] = [{"segment": [0, 10]}, {"segment": [20, 30]}, {"segment": [40, 50]}]
    errs, warns = run(o)
    assert errs == [] and warns
