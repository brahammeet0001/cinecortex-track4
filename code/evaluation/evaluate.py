"""Score predictions against ground truth.

Usage (from repo root):
  PYTHONPATH=code python -m evaluation.evaluate --pred outputs/ --gt gt/ --out results.json

GT folder: one <video_id>.json per video, with:
  {"video_id": "P01_01", "duration": 312.4, "label": "cooking",            (label optional)
   "actions": [{"verb":"cut","noun":"onion","start":1.0,"end":3.0}],
   "important_segments": [{"start":10,"end":20}]}                          (optional)
Write a small converter from the EPIC / FPVSum annotation files into this format.
"""
import argparse
import json
from pathlib import Path

from .intervals import budget_ratio
from .metrics import action_coverage, action_map, highlight_f1, label_accuracy

WEIGHTS = {"action_map": 0.25, "coverage": 0.40, "highlight_f1": 0.25, "label_acc": 0.10}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred", required=True)
    ap.add_argument("--gt", required=True)
    ap.add_argument("--out", default="results.json")
    a = ap.parse_args()

    gts, preds, per_video = {}, {}, {}
    cov, f1s, labels = [], [], []
    for gf in sorted(Path(a.gt).glob("*.json")):
        g = json.load(open(gf))
        vid = g["video_id"]
        pf = Path(a.pred) / f"{vid}.json"
        if pf.exists():
            p = json.load(open(pf))
        else:
            print(f"WARNING: no prediction for {vid} (scored as empty)")
            p = {"label": "", "actions": [], "highlights": []}
        gts[vid], preds[vid] = g["actions"], p["actions"]
        raw, pen, missed = action_coverage(p["highlights"], g["actions"], g["duration"])
        cov.append(pen)
        row = {"coverage_raw": raw, "coverage_penalised": pen, "missed_pairs": missed,
               "budget_ratio": budget_ratio(p["highlights"], g["duration"])}
        if g.get("important_segments"):
            row["highlight_f1"] = highlight_f1(p["highlights"], g["important_segments"])
            f1s.append(row["highlight_f1"])
        if g.get("label"):
            labels.append((p.get("label"), g["label"]))
        per_video[vid] = row

    m, per_class = action_map(preds, gts)
    summary = {
        "action_map": m,
        "coverage": sum(cov) / len(cov) if cov else None,
        "highlight_f1": sum(f1s) / len(f1s) if f1s else None,
        "label_acc": label_accuracy(labels) if labels else None,
    }
    avail = {k: v for k, v in summary.items() if v is not None}
    wsum = sum(WEIGHTS[k] for k in avail)
    summary["weighted_score_available_components"] = (
        sum(WEIGHTS[k] * v for k, v in avail.items()) / wsum if wsum else 0.0
    )
    summary["videos_over_budget"] = [v for v, r in per_video.items() if r["budget_ratio"] > 0.155]
    print(json.dumps(summary, indent=2))
    json.dump({"summary": summary, "per_video": per_video,
               "per_class_ap": {f"{v}_{n}": ap_ for (v, n), ap_ in per_class.items()}},
              open(a.out, "w"), indent=2)
    print(f"saved -> {a.out}")


if __name__ == "__main__":
    main()
