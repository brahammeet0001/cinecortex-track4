def union_duration(intervals):
    """Total length of the union of (start, end) intervals, in seconds."""
    ivs = sorted((s, e) for s, e in intervals if e > s)
    total, cur_s, cur_e = 0.0, None, None
    for s, e in ivs:
        if cur_e is None or s > cur_e:
            if cur_e is not None:
                total += cur_e - cur_s
            cur_s, cur_e = s, e
        else:
            cur_e = max(cur_e, e)
    if cur_e is not None:
        total += cur_e - cur_s
    return total


def budget_ratio(intervals, video_duration):
    return union_duration(intervals) / video_duration


def within_budget(intervals, video_duration, limit=0.15, tolerance=0.0):
    return budget_ratio(intervals, video_duration) <= limit + tolerance
