from evaluation.metrics import (action_coverage, action_map,
                                     highlight_f1, label_accuracy)

GT = {"v1": [{"verb": "cut", "noun": "onion", "start": 0, "end": 10},
             {"verb": "wash", "noun": "pan", "start": 20, "end": 30}]}


def test_map_perfect_and_empty():
    assert action_map(GT, GT)[0] == 1.0
    assert action_map({"v1": []}, GT)[0] == 0.0


def test_map_wrong_label_is_zero():
    pred = {"v1": [{"verb": "cut", "noun": "pan", "start": 0, "end": 10}]}
    assert action_map(pred, GT)[0] == 0.0


def test_map_boundary_below_threshold():
    pred = {"v1": [{"verb": "cut", "noun": "onion", "start": 9, "end": 19}]}  # tIoU ~0.05
    assert action_map(pred, GT)[0] == 0.0


def test_coverage_full_and_partial():
    hl = [{"start": 0, "end": 10}, {"start": 20, "end": 30}]
    raw, pen, missed = action_coverage(hl, GT["v1"], 200, budget=0.15)
    assert raw == 1.0 and missed == []
    raw, pen, missed = action_coverage([{"start": 0, "end": 10}], GT["v1"], 200)
    assert raw == 0.5 and missed == [("wash", "pan")]


def test_coverage_penalty_when_over_budget():
    hl = [{"start": 0, "end": 100}]  # 100% of a 100 s video
    raw, pen, _ = action_coverage(hl, GT["v1"], 100)
    assert pen < raw


def test_highlight_f1():
    g = [{"start": 0, "end": 10}]
    assert highlight_f1([{"start": 0, "end": 10}], g) == 1.0
    assert highlight_f1([{"start": 20, "end": 30}], g) == 0.0
    assert abs(highlight_f1([{"start": 0, "end": 5}], g) - 2 * 1 * 0.5 / 1.5) < 1e-9


def test_label_accuracy():
    assert label_accuracy([("a", "a"), ("b", "c")]) == 0.5
