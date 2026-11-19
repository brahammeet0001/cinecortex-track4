"""Score predictions (official Track 04 JSON) against ground truth.

Usage (from repo root):
  PYTHONPATH=code python -m evaluation.evaluate --pred outputs/ --gt gt/ \
      --manifest data_manifest/manifest.csv --out results.json

--pred: folder of <video_id>.json in the OFFICIAL output schema
        (segment: [start, end], label: {"name", "score"}).
--gt:   folder of <video_id>.json in our internal GT format, one per video:
  {"video_id": "P01_01", "duration": 312.4, "label": "cooking",
   "actions": [{"verb": "cut", "noun": "onion", "start": 1.0, "end": 3.0}],
   "important_segments": [{"start": 10, "end": 20}]}      (FPVSum only)

Per the README: action mAP and action coverage are scored on EPIC-KITCHENS-100
videos only; highlight F1 and label accuracy on FPVSum videos only.
Highlights shorter than 4.0 s are ignored in scoring.
"""
import argparse
import csv
import json
from pathlib import Path

from .metrics import action_coverage, action_map, highlight_f1, label_accuracy

WEIGHTS = {"action_map": 0.25, "coverage": 0.40, "highlight_f1": 0.25, "label_acc": 0.10}
MIN_HL = 4.0
EPIC = "epic_kitchens_100"
FPV = "fpvsum"


def load_manifest(path):
    if not path:
        return {}
    with open(path) as f:
        return {r["video_id"]: r["dataset"] for r in csv.DictReader(f)}


def dataset_of(vid, g, manifest):
    if vid in manifest:
        return manifest[vid]
    return FPV if g.get("important_segments") else EPIC


def to_internal(p):
    """Official prediction JSON -> internal format used by metrics.py."""
    acts, hls = [], []
    for a in p.get("actions") or []:
        seg = a.get("segment")
        if isinstance(seg, list) and len(seg) == 2:
            acts.append({"verb": a.get("verb"), "noun": a.get("noun"),
                         "start": float(seg[0]), "end": float(seg[1]),
                         "score": a.get("score", 1.0)})
    for h in p.get("highlights") or []:
        seg = h.get("segment") if isinstance(h, dict) else None
        if isinstance(seg, list) and len(seg) == 2:
            hls.append({"start": float(seg[0]), "end": float(seg[1])})
    lab = p.get("label")
    name = lab.get("name") if isinstance(lab, dict) else lab
    return {"label": name, "actions": acts, "highlights": hls}


def scoring_highlights(hls):
    """Highlights shorter than MIN_HL seconds are ignored in scoring."""
    return [h for h in hls if h["end"] - h["start"] >= MIN_HL]


def total_ratio(hls, duration):
    """Union length of all submitted highlights divided by duration."""
    ivs = sorted((h["start"], h["end"]) for h in hls if h["end"] > h["start"])
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
    return total / duration if duration > 0 else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", required=True)
    ap.add_argument("--gt", required=True)
    ap.add_argument("--manifest", default=None)
    ap.add_argument("--out", default="results.json")
    a = ap.parse_args()
    manifest = load_manifest(a.manifest)

    gts, preds, per_video = {}, {}, {}
    cov, f1s, labels = [], [], []
    for gf in sorted(Path(a.gt).glob("*.json")):
        g = json.load(open(gf))
        vid = g["video_id"]
        ds = dataset_of(vid, g, manifest)
        pf = Path(a.pred) / f"{vid}.json"
        p = {"label": None, "actions": [], "highlights": []}
        if pf.exists():
            try:
                p = to_internal(json.load(open(pf)))
            except Exception as ex:
                print(f"WARNING: invalid prediction for {vid} ({ex}); scored as empty")
        else:
            print(f"WARNING: no prediction for {vid} (scored as empty)")
        hl = scoring_highlights(p["highlights"])
        dur = g["duration"]
        row = {"dataset": ds, "budget_ratio": total_ratio(p["highlights"], dur)}
        if ds == EPIC:
            gt_actions = g.get("actions", [])
            gts[vid], preds[vid] = gt_actions, p["actions"]
            raw, pen, missed = action_coverage(hl, gt_actions, dur)
            cov.append(pen)
            row.update({"coverage_raw": raw, "coverage_penalised": pen,
                        "missed_pairs": missed})
        else:
            if g.get("important_segments"):
                row["highlight_f1"] = highlight_f1(hl, g["important_segments"])
                f1s.append(row["highlight_f1"])
            if g.get("label"):
                labels.append((p["label"], g["label"]))
                row["label_ok"] = p["label"] == g["label"]
        per_video[vid] = row

    m, per_class = action_map(preds, gts) if gts else (None, {})
    summary = {
        "n_epic": len(gts),
        "n_fpvsum": sum(1 for r in per_video.values() if r["dataset"] != EPIC),
        "action_map": m,
        "coverage": sum(cov) / len(cov) if cov else None,
        "highlight_f1": sum(f1s) / len(f1s) if f1s else None,
        "label_acc": label_accuracy(labels) if labels else None,
    }
    avail = {k: v for k, v in summary.items() if k in WEIGHTS and v is not None}
    wsum = sum(WEIGHTS[k] for k in avail)
    summary["weighted_score_available_components"] = (
        sum(WEIGHTS[k] * v for k, v in avail.items()) / wsum if wsum else 0.0
    )
    summary["videos_over_budget"] = [v for v, r in per_video.items() if r["budget_ratio"] > 0.155]
    print(json.dumps(summary, indent=2))
    with open(a.out, "w") as f:
        json.dump({"summary": summary, "per_video": per_video,
                   "per_class_ap": {f"{v}_{n}": ap_ for (v, n), ap_ in per_class.items()}},
                  f, indent=2)
    print(f"saved -> {a.out}")


if __name__ == "__main__":
    main()
