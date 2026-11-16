"""Interval helpers. All times are seconds (float). Intervals are half-open [start, end)."""


def merge_intervals(iv):
    """Merge overlapping/touching intervals. Input: iterable of (start, end)."""
    iv = sorted((float(s), float(e)) for s, e in iv if e > s)
    out = []
    for s, e in iv:
        if out and s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return [(s, e) for s, e in out]


def union_duration(iv):
    """Total length of the union (overlaps counted once)."""
    return sum(e - s for s, e in merge_intervals(iv))


def intersect_duration(a, b):
    """Length of the intersection of two interval lists."""
    a, b = merge_intervals(a), merge_intervals(b)
    i = j = 0
    total = 0.0
    while i < len(a) and j < len(b):
        lo = max(a[i][0], b[j][0])
        hi = min(a[i][1], b[j][1])
        if hi > lo:
            total += hi - lo
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return total


def tiou(a, b):
    """Temporal IoU of two single intervals (start, end)."""
    inter = max(0.0, min(a[1], b[1]) - max(a[0], b[0]))
    union = (a[1] - a[0]) + (b[1] - b[0]) - inter
    return inter / union if union > 0 else 0.0


def budget_ratio(highlights, duration):
    """Selected footage / source duration. `highlights` = list of {'start','end'}."""
    if duration <= 0:
        return 0.0
    return union_duration([(h["start"], h["end"]) for h in highlights]) / duration
