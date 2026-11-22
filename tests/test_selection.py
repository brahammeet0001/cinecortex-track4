import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))
from selection.budget import select_highlights, union_duration, within_budget


def test_selects_scored_non_overlapping_highlights_within_budget():
    candidates = [
        {"start": 0, "end": 4, "importance": 0.2},
        {"start": 2, "end": 6, "importance": 0.99},
        {"start": 8, "end": 12, "importance": 0.8},
        {"start": 14, "end": 18, "importance": 0.7},
    ]
    got = select_highlights(candidates, 100)
    intervals = [(h["start"], h["end"]) for h in got]
    assert (2.0, 6.0) in intervals
    assert all(b[0] >= a[1] for a, b in zip(intervals, intervals[1:]))
    assert within_budget(intervals, 100)
    assert all(e - s >= 4 for s, e in intervals)


def test_actions_add_marginal_coverage_value():
    candidates = [
        {"start": 0, "end": 4, "importance": 0.5},
        {"start": 8, "end": 12, "importance": 0.4},
    ]
    actions = [{"start": 8, "end": 12, "verb": "cut", "noun": "onion", "score": 0.9}]
    got = select_highlights(candidates, 40, actions=actions)
    assert got[0]["start"] == 8.0


def test_empty_candidates_returns_neutral_minimum_interval():
    got = select_highlights([], 40)
    assert got == [{"start": 0.0, "end": 4.0, "importance": 0.0}]


def test_short_video_minimum_and_budget_conflict_is_explicit():
    got = select_highlights([], 11.13)
    assert got == [{"start": 0.0, "end": 4.0, "importance": 0.0}]
    assert union_duration([(h["start"], h["end"]) for h in got]) > 0.15 * 11.13


def test_short_candidates_are_not_artificially_extended():
    got = select_highlights([{"start": 1, "end": 3, "importance": 1.0}], 40)
    # Candidate isn't stretched into an asserted important highlight; the
    # only result is the explicitly neutral empty-proposal fallback.
    assert got == [{"start": 0.0, "end": 4.0, "importance": 0.0}]
