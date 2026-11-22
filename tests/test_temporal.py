import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))
from temporal import normalize_actions

VERBS = {"cut", "open", "other"}
NOUNS = {"onion", "fridge", "other"}


def test_clips_bounds_and_clamps_scores():
    got = normalize_actions([
        {"start": -2, "end": 3, "verb": "cut", "noun": "onion", "score": 1.5},
        {"start": 8, "end": 14, "verb": "open", "noun": "fridge", "score": 0.7},
    ], 10, verbs=VERBS, nouns=NOUNS)
    assert got == [
        {"start": 0.0, "end": 3.0, "verb": "cut", "noun": "onion", "score": 1.0},
        {"start": 8.0, "end": 10.0, "verb": "open", "noun": "fridge", "score": 0.7},
    ]


def test_invalid_predictions_are_removed():
    got = normalize_actions([
        {"start": float("nan"), "end": 3, "verb": "cut", "noun": "onion", "score": 0.5},
        {"start": 1, "end": 1, "verb": "cut", "noun": "onion", "score": 0.5},
        {"start": 1, "end": 3, "verb": "made-up", "noun": "onion", "score": 0.5},
        {"start": 1, "end": 3, "verb": "cut", "noun": "onion", "score": float("inf")},
    ], 10, verbs=VERBS, nouns=NOUNS)
    assert got == []


def test_same_class_duplicates_and_adjacent_proposals_merge():
    got = normalize_actions([
        {"start": 1, "end": 3, "verb": "cut", "noun": "onion", "score": 0.6},
        {"start": 1.1, "end": 3.1, "verb": "cut", "noun": "onion", "score": 0.9},
        {"start": 3.15, "end": 5, "verb": "cut", "noun": "onion", "score": 0.7},
    ], 10, verbs=VERBS, nouns=NOUNS)
    assert len(got) == 1
    assert got[0]["start"] == 1.0
    assert got[0]["end"] == 5.0
    assert got[0]["score"] == 0.9


def test_different_action_classes_are_not_merged_even_when_overlapping():
    got = normalize_actions([
        {"start": 1, "end": 5, "verb": "cut", "noun": "onion", "score": 0.8},
        {"start": 2, "end": 4, "verb": "open", "noun": "fridge", "score": 0.7},
    ], 10, verbs=VERBS, nouns=NOUNS)
    assert len(got) == 2
    assert got[0]["start"] == 1.0 and got[1]["start"] == 2.0


def test_official_segment_shape_and_deterministic_sorting():
    got = normalize_actions([
        {"segment": [5, 7], "verb": "open", "noun": "fridge", "score": 0.4},
        {"segment": [1, 2], "verb": "cut", "noun": "onion", "score": 0.4},
    ], 10, verbs=VERBS, nouns=NOUNS)
    assert [a["start"] for a in got] == [1.0, 5.0]
