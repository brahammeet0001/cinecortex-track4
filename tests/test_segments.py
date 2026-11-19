import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
from submission.schema import finalize_highlights


def test_many_short_become_valid():
    items = [(i * 10.0, i * 10.0 + 0.5, 0.5 + i / 100) for i in range(20)]
    segs = finalize_highlights(items, 200.0)
    assert sum(e - s for s, e, _ in segs) <= 0.15 * 200
    assert max(e - s for s, e, _ in segs) >= 4.0
    assert all(segs[i][1] <= segs[i + 1][0] for i in range(len(segs) - 1))


def test_overlaps_merge():
    segs = finalize_highlights([(0, 5, 1.0), (3, 8, 0.5)], 100.0)
    assert [(s, e) for s, e, _ in segs] == [(0.0, 8.0)]
