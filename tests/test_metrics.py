from evaluation.metrics import (action_coverage, action_map, highlight_f1,
                                label_accuracy, scored_highlights)

GT = {"v1": [{"segment": [0, 10], "verb": "cut", "noun": "onion"},
             {"segment": [20, 30], "verb": "wash", "noun": "pan"}]}


def hl(*segs):
    return [{"segment": list(s)} for s in segs]


def test_map_perfect_and_empty():
    assert action_map(GT, GT)[0] == 1.0
    assert action_map({"v1": []}, GT)[0] == 0.0


def test_map_wrong_label_is_zero():
    pred = {"v1": [{"segment": [0, 10], "verb": "cut", "noun": "pan", "score": 0.9}]}
    assert action_map(pred, GT)[0] == 0.0


def test_map_boundary_below_threshold():
    pred = {"v1": [{"segment": [9, 19], "verb": "cut", "noun": "onion", "score": 0.9}]}
    assert action_map(pred, GT)[0] == 0.0


def test_map_uses_score_ranking():
    gt = {"v1": [{"segment": [0, 10], "verb": "cut", "noun": "onion"}]}
    good_first = {"v1": [{"segment": [0, 10], "verb": "cut", "noun": "onion", "score": 0.9},
                         {"segment": [50, 60], "verb": "cut", "noun": "onion", "score": 0.1}]}
    bad_first = {"v1": [{"segment": [0, 10], "verb": "cut", "noun": "onion", "score": 0.1},
                        {"segment": [50, 60], "verb": "cut", "noun": "onion", "score": 0.9}]}
    assert action_map(good_first, gt)[0] > action_map(bad_first, gt)[0]


def test_short_highlights_ignored():
    assert scored_highlights(hl((0, 3.9), (10, 14))) == [(10.0, 14.0)]


def test_coverage_full_and_partial():
    raw, pen, missed = action_coverage(hl((0, 10), (20, 30)), GT["v1"], 200)
    assert raw == 1.0 and missed == []
    raw, pen, missed = action_coverage(hl((0, 10)), GT["v1"], 200)
    assert raw == 0.5 and missed == [("wash", "pan")]


def test_coverage_ignores_segments_under_4s():
    raw, _, _ = action_coverage(hl((0, 3.5)), [{"segment": [0, 3.5], "verb": "a", "noun": "b"}], 200)
    assert raw == 0.0


def test_coverage_penalty_when_over_budget():
    raw, pen, _ = action_coverage(hl((0, 100)), GT["v1"], 100)
    assert pen < raw


def test_highlight_f1():
    g = [[0, 10]]
    assert highlight_f1(hl((0, 10)), g) == 1.0
    assert highlight_f1(hl((20, 30)), g) == 0.0
    assert abs(highlight_f1(hl((0, 5)), [[0, 10]]) - 2 * 1 * 0.5 / 1.5) < 1e-9
    assert highlight_f1(hl((0, 3)), [[0, 3]]) == 0.0  # < 4 s is ignored


def test_label_accuracy():
    assert label_accuracy([('ski', 'ski'), ('bike', 'ski')]) == 0.5
