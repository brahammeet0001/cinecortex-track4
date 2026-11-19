import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
from evaluation.evaluate import dataset_of, scoring_highlights, to_internal, total_ratio


def test_to_internal_converts_official_schema():
    p = {"label": {"name": "cooking", "score": 0.9},
         "actions": [{"segment": [1.0, 3.0], "verb": "cut", "noun": "onion", "score": 0.8}],
         "highlights": [{"segment": [10.0, 20.0]}]}
    q = to_internal(p)
    assert q["label"] == "cooking"
    assert q["actions"][0]["start"] == 1.0 and q["actions"][0]["end"] == 3.0
    assert q["actions"][0]["verb"] == "cut"
    assert q["highlights"] == [{"start": 10.0, "end": 20.0}]


def test_to_internal_skips_malformed_items():
    q = to_internal({"label": "x", "actions": [{"verb": "a"}],
                     "highlights": [{}, {"segment": [1]}]})
    assert q["actions"] == [] and q["highlights"] == [] and q["label"] == "x"


def test_short_highlights_are_ignored():
    hls = [{"start": 0.0, "end": 3.9}, {"start": 10.0, "end": 14.0}]
    assert scoring_highlights(hls) == [{"start": 10.0, "end": 14.0}]


def test_total_ratio_counts_overlap_once():
    hls = [{"start": 0, "end": 10}, {"start": 5, "end": 15}]
    assert abs(total_ratio(hls, 100.0) - 0.15) < 1e-9


def test_dataset_uses_manifest_first():
    g = {"important_segments": [{"start": 0, "end": 1}]}
    assert dataset_of("v", g, {"v": "epic_kitchens_100"}) == "epic_kitchens_100"


def test_dataset_fallback_from_gt_content():
    assert dataset_of("v", {"important_segments": [{"start": 0, "end": 1}]}, {}) == "fpvsum"
    assert dataset_of("v", {"actions": []}, {}) == "epic_kitchens_100"
