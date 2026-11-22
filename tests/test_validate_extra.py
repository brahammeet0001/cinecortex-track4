import copy

from evaluation.validate_extra import check

GOOD = {
    "team_id": "team_alpha", "video_id": "P02_109", "duration_sec": 512.3,
    "label": {"name": "cooking", "score": 0.96},
    "actions": [{"segment": [12.4, 18.2], "verb": "open", "noun": "fridge", "score": 0.88}],
    "highlights": [{"segment": [11.0, 19.5]}, {"segment": [45.2, 53.0]}],
}


def bad(**kw):
    d = copy.deepcopy(GOOD)
    d.update(kw)
    return d


def errs(d, stem="P02_109", md=None):
    return check(d, stem, md)[0]


def test_readme_example_is_valid():
    assert errs(GOOD, md=512.3) == []


def test_missing_key():
    d = copy.deepcopy(GOOD)
    del d["team_id"]
    assert any("team_id" in e for e in errs(d))


def test_old_flat_schema_is_rejected():
    old = {"video_id": "v", "label": "x", "actions": [{"verb": "a", "noun": "b", "start": 1, "end": 2}],
           "highlights": [{"start": 0, "end": 5, "importance": 0.9}]}
    assert errs(old, "v")


def test_filename_and_manifest_duration():
    assert any("filename" in e for e in errs(GOOD, stem="other"))
    assert any("manifest" in e for e in errs(GOOD, md=600.0))
    assert errs(GOOD, md=512.0) == []  # within +-0.5


def test_segment_rules():
    assert errs(bad(actions=[{"segment": [5, 2], "verb": "a", "noun": "b", "score": 0.5}]))
    assert errs(bad(actions=[{"segment": [0, 9999], "verb": "a", "noun": "b", "score": 0.5}]))
    assert errs(bad(actions=[{"segment": [1, 2], "verb": "a", "noun": "b", "score": 1.5}]))


def test_highlights_overlap_sorted_and_min_length():
    assert any("overlap" in e for e in errs(bad(highlights=[{"segment": [0, 10]}, {"segment": [5, 15]}])))
    assert any("sorted" in e for e in errs(bad(highlights=[{"segment": [20, 30]}, {"segment": [0, 10]}])))
    assert any("4.0" in e for e in errs(bad(highlights=[{"segment": [0, 3]}])))
    assert errs(bad(highlights=[]))


def test_budget_is_a_warning_not_an_error():
    d = bad(duration_sec=100.0, highlights=[{"segment": [0, 30]}])
    e, w = check(d, "P02_109")
    assert e == [] and any("15%" in x for x in w)


def test_label_vocab():
    v = {"labels": {"cooking", "ski"}, "verbs": None, "nouns": None}
    assert errs(GOOD) == []
    assert any("supported" in e for e in check(bad(label={"name": "chess", "score": 0.5}), "P02_109", None, v)[0])
