from evaluation.validate_extra import check

GOOD = {"video_id": "v1", "label": "x",
        "actions": [{"verb": "cut", "noun": "onion", "start": 1.0, "end": 2.0}],
        "highlights": [{"start": 0, "end": 10, "importance": 0.9}]}


def test_good():
    assert check(GOOD, "v1", 100) == []


def test_missing_key():
    bad = dict(GOOD); del bad["label"]
    assert any("label" in e for e in check(bad))


def test_start_after_end_and_filename():
    bad = dict(GOOD, actions=[{"verb": "a", "noun": "b", "start": 5, "end": 2}])
    assert check(bad, "v1", 100)
    assert any("filename" in e for e in check(GOOD, "other", 100))


def test_budget_exceeded():
    bad = dict(GOOD, highlights=[{"start": 0, "end": 20, "importance": 0.5}])
    assert any("15%" in e for e in check(bad, "v1", 100))


def test_beyond_duration():
    bad = dict(GOOD, highlights=[{"start": 0, "end": 10, "importance": 0.5}])
    assert any("beyond" in e for e in check(bad, "v1", 5))
