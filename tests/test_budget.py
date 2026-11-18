import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
from selection.budget import union_duration, within_budget, budget_ratio


def test_union_counts_overlap_once():
    assert union_duration([(0, 10), (5, 15), (20, 25)]) == 20


def test_union_ignores_empty_and_reversed():
    assert union_duration([(5, 5), (9, 3)]) == 0


def test_within_budget_boundary():
    assert within_budget([(0, 15)], 100)          # exactly 15%
    assert not within_budget([(0, 15.1)], 100)    # just over


def test_budget_ratio():
    assert budget_ratio([(0, 10)], 100) == 0.1
