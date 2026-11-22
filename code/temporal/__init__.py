"""Deterministic cleanup for temporal action predictions.

The module accepts either internal ``start``/``end`` intervals or official
``segment: [start, end]`` intervals and always returns the internal form:
``{start, end, verb, noun, score}``.
"""
from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from typing import Any


def _finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _interval(item: Mapping[str, Any]) -> tuple[float, float] | None:
    segment = item.get("segment")
    if isinstance(segment, (list, tuple)) and len(segment) == 2:
        start, end = segment
    else:
        start, end = item.get("start"), item.get("end")
    if not (_finite_number(start) and _finite_number(end)):
        return None
    return float(start), float(end)


def _overlap_ratio(a: tuple[float, float], b: tuple[float, float]) -> float:
    inter = max(0.0, min(a[1], b[1]) - max(a[0], b[0]))
    denom = min(a[1] - a[0], b[1] - b[0])
    return inter / denom if denom > 0 else 0.0


def normalize_actions(
    predictions: Iterable[Mapping[str, Any]] | None,
    duration: float,
    *,
    verbs: set[str] | None = None,
    nouns: set[str] | None = None,
    min_duration: float = 0.10,
    merge_gap: float = 0.15,
    duplicate_overlap: float = 0.85,
    max_actions: int = 2000,
) -> list[dict[str, Any]]:
    """Validate, clip, de-duplicate and conservatively merge action intervals.

    Only actions with the same verb-noun pair can be merged. Distinct classes
    are retained even when their temporal intervals overlap.
    """
    if not _finite_number(duration) or float(duration) <= 0:
        raise ValueError("duration must be a finite positive number")
    duration = float(duration)
    if predictions is None:
        return []

    clean: list[dict[str, Any]] = []
    for raw in predictions:
        if not isinstance(raw, Mapping):
            continue
        interval = _interval(raw)
        verb, noun = raw.get("verb"), raw.get("noun")
        score = raw.get("score", 0.0)
        if interval is None or not isinstance(verb, str) or not isinstance(noun, str):
            continue
        verb, noun = verb.strip(), noun.strip()
        if not verb or not noun:
            continue
        if verbs is not None and verb not in verbs:
            continue
        if nouns is not None and noun not in nouns:
            continue
        if not _finite_number(score):
            continue

        start = max(0.0, min(duration, interval[0]))
        end = max(0.0, min(duration, interval[1]))
        if end - start < min_duration:
            continue
        clean.append({
            "start": start,
            "end": end,
            "verb": verb,
            "noun": noun,
            "score": max(0.0, min(1.0, float(score))),
        })

    # Sort deterministically, preferring higher-confidence duplicates.
    clean.sort(key=lambda a: (a["verb"], a["noun"], a["start"], a["end"], -a["score"]))
    merged: list[dict[str, Any]] = []
    for action in clean:
        previous = merged[-1] if merged else None
        same_class = previous is not None and (
            previous["verb"], previous["noun"]
        ) == (action["verb"], action["noun"])
        gap = action["start"] - previous["end"] if same_class else math.inf
        duplicate = same_class and _overlap_ratio(
            (previous["start"], previous["end"]),
            (action["start"], action["end"]),
        ) >= duplicate_overlap
        if same_class and (gap <= merge_gap or duplicate):
            previous["start"] = min(previous["start"], action["start"])
            previous["end"] = max(previous["end"], action["end"])
            previous["score"] = max(previous["score"], action["score"])
        else:
            merged.append(dict(action))

    merged.sort(key=lambda a: (a["start"], a["end"], a["verb"], a["noun"], -a["score"]))
    return [
        {
            **a,
            "start": round(a["start"], 3),
            "end": round(a["end"], 3),
            "score": round(a["score"], 4),
        }
        for a in merged[:max_actions]
    ]


__all__ = ["normalize_actions"]
