"""Highlight interval accounting and deterministic budget-aware selection."""
from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from typing import Any


def _num(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def union_intervals(intervals: Iterable[tuple[float, float]]) -> list[tuple[float, float]]:
    """Return sorted, merged intervals; invalid/empty intervals are ignored."""
    valid = []
    for start, end in intervals:
        if _num(start) and _num(end) and float(end) > float(start):
            valid.append((float(start), float(end)))
    valid.sort()
    out: list[list[float]] = []
    for start, end in valid:
        if not out or start > out[-1][1]:
            out.append([start, end])
        else:
            out[-1][1] = max(out[-1][1], end)
    return [(a, b) for a, b in out]


def union_duration(intervals: Iterable[tuple[float, float]]) -> float:
    """Total length of the union of intervals, in seconds."""
    return sum(end - start for start, end in union_intervals(intervals))


def budget_ratio(intervals: Iterable[tuple[float, float]], video_duration: float) -> float:
    if not _num(video_duration) or float(video_duration) <= 0:
        raise ValueError("video_duration must be finite and positive")
    return union_duration(intervals) / float(video_duration)


def within_budget(
    intervals: Iterable[tuple[float, float]],
    video_duration: float,
    limit: float = 0.15,
    tolerance: float = 0.0,
) -> bool:
    if not _num(limit) or not 0 <= float(limit) <= 1:
        raise ValueError("limit must be in [0, 1]")
    return budget_ratio(intervals, video_duration) <= float(limit) + float(tolerance)


def _candidate_interval(item: Mapping[str, Any]) -> tuple[float, float] | None:
    segment = item.get("segment")
    if isinstance(segment, (list, tuple)) and len(segment) == 2:
        start, end = segment
    else:
        start, end = item.get("start"), item.get("end")
    if not (_num(start) and _num(end)):
        return None
    return float(start), float(end)


def select_highlights(
    candidates: Iterable[Mapping[str, Any]] | None,
    video_duration: float,
    *,
    actions: Iterable[Mapping[str, Any]] | None = None,
    limit: float = 0.15,
    min_segment: float = 4.0,
    min_gap: float = 2.0,
) -> list[dict[str, float]]:
    """Select non-overlapping highlights, prioritising importance and action coverage.

    The selector does not lengthen arbitrary short proposals to make them pass.
    When ``limit * duration < min_segment``, the official minimum-segment and
    15% requirements are mathematically incompatible; one minimum-length
    segment is returned and the unavoidable budget overage is explicit.
    """
    if not _num(video_duration) or float(video_duration) <= 0:
        raise ValueError("video_duration must be finite and positive")
    if not _num(limit) or not 0 < float(limit) <= 1:
        raise ValueError("limit must be in (0, 1]")
    if not _num(min_segment) or float(min_segment) <= 0:
        raise ValueError("min_segment must be finite and positive")

    duration = float(video_duration)
    min_segment = min(float(min_segment), duration)
    budget = duration * float(limit)
    effective_budget = max(budget, min_segment)

    action_rows = []
    for action in actions or []:
        if not isinstance(action, Mapping):
            continue
        interval = _candidate_interval(action)
        pair = (action.get("verb"), action.get("noun"))
        if interval and isinstance(pair[0], str) and isinstance(pair[1], str):
            s, e = max(0.0, interval[0]), min(duration, interval[1])
            if e > s:
                action_rows.append((s, e, pair))
    all_pairs = {row[2] for row in action_rows}

    prepared = []
    for index, raw in enumerate(candidates or []):
        if not isinstance(raw, Mapping):
            continue
        interval = _candidate_interval(raw)
        if interval is None:
            continue
        start, end = max(0.0, interval[0]), min(duration, interval[1])
        if end - start + 1e-9 < min_segment:
            continue
        importance = raw.get("importance", raw.get("score", 0.0))
        if not _num(importance):
            importance = 0.0
        importance = max(0.0, min(1.0, float(importance)))
        covered = set()
        for a_start, a_end, pair in action_rows:
            overlap = max(0.0, min(end, a_end) - max(start, a_start))
            action_len = a_end - a_start
            if overlap > 0 and overlap / action_len >= 0.20:
                covered.add(pair)
        prepared.append({
            "start": start,
            "end": end,
            "importance": importance,
            "covered": covered,
            "index": index,
        })

    # Greedy marginal selection. Once an action pair is covered, selecting
    # another interval for that same pair receives no additional bonus.
    chosen: list[dict[str, Any]] = []
    chosen_pairs: set[tuple[str, str]] = set()
    remaining = list(prepared)
    while remaining:
        feasible = []
        for item in remaining:
            iv = (item["start"], item["end"])
            if any(iv[0] < h["end"] + min_gap and h["start"] < iv[1] + min_gap for h in chosen):
                continue
            trial = [(h["start"], h["end"]) for h in chosen] + [iv]
            if union_duration(trial) > effective_budget + 1e-7:
                continue
            new_pairs = item["covered"] - chosen_pairs
            coverage_bonus = (0.35 * len(new_pairs) / max(1, len(all_pairs))) if all_pairs else 0.0
            utility = item["importance"] + coverage_bonus
            feasible.append((utility, item["importance"], -item["start"], item, new_pairs))
        if not feasible:
            break
        _, _, _, best, new_pairs = max(feasible, key=lambda x: (x[0], x[1], x[2], -x[3]["index"]))
        chosen.append(best)
        chosen_pairs.update(new_pairs)
        remaining.remove(best)

    # A valid result requires one >=4s segment. With a truly empty proposal
    # set, return a neutral (zero-importance) opening interval rather than
    # asserting it contains an important event.
    if not chosen and duration > 0:
        chosen = [{"start": 0.0, "end": min(duration, min_segment), "importance": 0.0}]

    chosen.sort(key=lambda h: (h["start"], h["end"]))
    return [
        {"start": round(h["start"], 3), "end": round(h["end"], 3),
         "importance": round(float(h.get("importance", 0.0)), 4)}
        for h in chosen
    ]
