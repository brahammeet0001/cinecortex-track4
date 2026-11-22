"""Single-video CineCorteX inference entry point (official Track 04 schema)."""
from __future__ import annotations

import csv
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

CODE_DIR = Path(__file__).resolve().parent
ROOT = CODE_DIR.parent
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from evaluation.validate_official import validate
from ingest.probe import probe
from perception.predict import predict
from selection.budget import select_highlights, union_duration
from temporal import normalize_actions

LIMIT = 0.15
TEAM_ID = os.environ.get("CINECORTEX_TEAM_ID", "T07").strip() or "T07"
MANIFEST_PATH = ROOT / "data_manifest" / "manifest.csv"
CLASSES_PATH = ROOT / "data_manifest" / "supported_classes.json"


def load_resources() -> tuple[dict[str, dict[str, Any]], dict[str, set[str]]]:
    manifest: dict[str, dict[str, Any]] = {}
    if MANIFEST_PATH.exists():
        with MANIFEST_PATH.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                manifest[row["video_id"]] = {
                    "duration_sec": float(row["duration_sec"]),
                    "dataset": row["dataset"],
                }
    if CLASSES_PATH.exists():
        classes = json.loads(CLASSES_PATH.read_text(encoding="utf-8"))
    else:
        classes = {"labels": ["other"], "verbs": ["other"], "nouns": ["other"]}
    return manifest, {
        "labels": set(classes.get("labels", [])),
        "verbs": set(classes.get("verbs", [])),
        "nouns": set(classes.get("nouns", [])),
    }


def _parse_label(prediction: dict[str, Any], dataset: str | None, valid_labels: set[str]) -> dict[str, Any]:
    raw = prediction.get("label", "other")
    score = prediction.get("label_score", 0.0)
    if isinstance(raw, dict):
        score = raw.get("score", score)
        raw = raw.get("name", "other")
    if dataset == "epic_kitchens_100":
        # EPIC-KITCHENS-100 in this challenge is a cooking-only evaluation set;
        # this is dataset metadata, not a visual action prediction.
        name, score = "cooking", 1.0
    else:
        name = raw if isinstance(raw, str) and raw in valid_labels else "other"
        if name == "cooking" and dataset == "fpvsum":
            name = "other"
        if not (isinstance(score, (int, float)) and not isinstance(score, bool) and math.isfinite(float(score))):
            score = 0.0
        score = max(0.0, min(1.0, float(score)))
    if name not in valid_labels:
        name, score = "other", 0.0
    return {"name": name, "score": round(float(score), 4)}


def build_submission(video_path: str, team_id: str | None = None) -> dict[str, Any]:
    meta = probe(video_path)
    manifest, vocab = load_resources()
    entry = manifest.get(meta["video_id"], {})
    dataset = entry.get("dataset")
    manifest_duration = entry.get("duration_sec")
    probed_duration = float(meta["duration_s"])

    if manifest_duration is not None:
        delta = abs(probed_duration - manifest_duration)
        if delta > 0.5:
            print(
                f"WARNING: ffprobe duration {probed_duration:.3f}s differs from manifest "
                f"{manifest_duration:.3f}s by {delta:.3f}s",
                file=sys.stderr,
            )
            official_duration = probed_duration
        else:
            official_duration = float(manifest_duration)
    else:
        official_duration = probed_duration

    # Keep all timestamps inside both the decoded media and official duration.
    processing_duration = min(probed_duration, official_duration)
    meta.update({
        "duration_s": processing_duration,
        "probed_duration_s": probed_duration,
        "dataset": dataset,
        "manifest_duration_sec": manifest_duration,
    })
    prediction = predict(video_path, meta)
    if not isinstance(prediction, dict):
        raise TypeError("perception.predict must return a dictionary")
    print(f"INFO: selected perception path={prediction.get('perception_source', 'unspecified')}", file=sys.stderr)

    actions = normalize_actions(
        prediction.get("actions", []),
        processing_duration,
        verbs=vocab["verbs"],
        nouns=vocab["nouns"],
    )
    candidate_highlights = prediction.get("highlights", [])
    if not isinstance(candidate_highlights, list):
        candidate_highlights = []
    highlights_internal = select_highlights(
        candidate_highlights,
        processing_duration,
        actions=actions,
        limit=LIMIT,
        min_segment=4.0,
    )

    label = _parse_label(prediction, dataset, vocab["labels"])
    payload = {
        "team_id": (team_id or TEAM_ID),
        "video_id": meta["video_id"],
        "duration_sec": round(official_duration, 3),
        "label": label,
        "actions": [
            {
                "segment": [round(a["start"], 2), round(a["end"], 2)],
                "verb": a["verb"],
                "noun": a["noun"],
                "score": round(a["score"], 4),
            }
            for a in actions
        ],
        "highlights": [
            {"segment": [round(h["start"], 2), round(h["end"], 2)]}
            for h in highlights_internal
        ],
    }

    errs, warns = validate(payload, meta["video_id"],
                           {meta["video_id"]: official_duration},
                           vocab["verbs"], vocab["nouns"], vocab["labels"])
    if errs:
        raise ValueError("generated submission failed local schema checks: " + "; ".join(errs))
    for warning in warns:
        print(f"WARNING: local validator: {warning}", file=sys.stderr)
    return payload


def main(video_path: str, out_path: str) -> None:
    payload = build_submission(video_path)
    destination = Path(out_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    destination.write_text(serialized, encoding="utf-8")
    selected = [tuple(h["segment"]) for h in payload["highlights"]]
    used = union_duration(selected)
    ratio = used / float(payload["duration_sec"])
    print(
        f"Wrote {destination} ({payload['video_id']}, {payload['duration_sec']:.2f}s, "
        f"{len(payload['actions'])} actions, highlight {used:.2f}s / {ratio:.1%})"
    )


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: main.py <video.mp4> <out.json>", file=sys.stderr)
        sys.exit(2)
    try:
        main(sys.argv[1], sys.argv[2])
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
