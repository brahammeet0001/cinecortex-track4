from evaluation.intervals import (budget_ratio, intersect_duration,
                                       merge_intervals, tiou, union_duration)


def test_merge_and_union():
    assert merge_intervals([(0, 2), (1, 3), (5, 6)]) == [(0, 3), (5, 6)]
    assert union_duration([(0, 2), (1, 3), (5, 6)]) == 4  # overlap counted once


def test_touching_intervals_merge():
    assert union_duration([(0, 1), (1, 2)]) == 2


def test_intersect():
    assert intersect_duration([(0, 10)], [(5, 15)]) == 5
    assert intersect_duration([(0, 1)], [(2, 3)]) == 0


def test_tiou():
    assert tiou((0, 10), (0, 10)) == 1.0
    assert tiou((0, 10), (10, 20)) == 0.0
    assert abs(tiou((0, 10), (5, 15)) - 5 / 15) < 1e-9


def test_budget_ratio():
    assert budget_ratio([{"start": 0, "end": 15}], 100) == 0.15
    assert budget_ratio([{"start": 0, "end": 10}, {"start": 5, "end": 15}], 100) == 0.15
