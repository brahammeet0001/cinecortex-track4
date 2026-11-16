"""Metrics following the Track 04 slides.

ASSUMPTIONS (confirm with organisers, change here if their definition differs):
  - Action mAP: per verb-noun class AP, averaged over classes, then over tIoU 0.1..0.5.
    Predictions without a 'score' keep file order (score = 1.0 for all).
  - Action coverage: a GT (verb, noun) pair counts as captured if at least `min_overlap`
    of one of its instances lies inside the highlights. Soft penalty if budget exceeded.
  - Highlight F1: frame-level F1 computed exactly on intervals (same as frame-level
    in the limit of fine sampling).
"""
from .intervals import intersect_duration, merge_intervals, tiou, union_duration

TIOU_THRESHOLDS = (0.1, 0.2, 0.3, 0.4, 0.5)


def _pair(a):
    return (a["verb"], a["noun"])


def _average_precision(dets, n_gt, gt_by_vid, thr):
    """dets: list of (score, vid, start, end) for ONE class."""
    if n_gt == 0:
        return None
    dets = sorted(dets, key=lambda d: -d[0])  # stable: ties keep input order
    used = {vid: [False] * len(g) for vid, g in gt_by_vid.items()}
    tp = []
    for score, vid, s, e in dets:
        best, best_j = 0.0, -1
        for j, (gs, ge) in enumerate(gt_by_vid.get(vid, [])):
            if used[vid][j]:
                continue
            v = tiou((s, e), (gs, ge))
            if v > best:
                best, best_j = v, j
        if best >= thr and best_j >= 0:
            used[vid][best_j] = True
            tp.append(1)
        else:
            tp.append(0)
    cum_tp = cum_fp = 0
    rec, prec = [], []
    for t in tp:
        cum_tp += t
        cum_fp += 1 - t
        rec.append(cum_tp / n_gt)
        prec.append(cum_tp / (cum_tp + cum_fp))
    mrec = [0.0] + rec + [1.0]
    mpre = [0.0] + prec + [0.0]
    for i in range(len(mpre) - 2, -1, -1):
        mpre[i] = max(mpre[i], mpre[i + 1])
    return sum((mrec[i] - mrec[i - 1]) * mpre[i] for i in range(1, len(mrec)))


def action_map(preds, gts, thresholds=TIOU_THRESHOLDS):
    """preds/gts: {video_id: [ {verb,noun,start,end,(score)} ]}.
    Returns (mAP, {class: AP averaged over thresholds})."""
    classes = {_pair(a) for acts in gts.values() for a in acts}
    per_class_all = {c: [] for c in classes}
    for thr in thresholds:
        for c in classes:
            gt_by_vid = {
                vid: [(a["start"], a["end"]) for a in acts if _pair(a) == c]
                for vid, acts in gts.items()
            }
            n_gt = sum(len(v) for v in gt_by_vid.values())
            dets = [
                (a.get("score", 1.0), vid, a["start"], a["end"])
                for vid, acts in preds.items()
                for a in acts
                if _pair(a) == c
            ]
            ap = _average_precision(dets, n_gt, gt_by_vid, thr)
            if ap is not None:
                per_class_all[c].append(ap)
    per_class = {c: sum(v) / len(v) for c, v in per_class_all.items() if v}
    m = sum(per_class.values()) / len(per_class) if per_class else 0.0
    return m, per_class


def action_coverage(highlights, gt_actions, duration, budget=0.15, min_overlap=0.5):
    """Returns (raw_coverage, penalised_coverage, missed_pairs) for ONE video."""
    hl = [(h["start"], h["end"]) for h in highlights]
    by_pair = {}
    for a in gt_actions:
        by_pair.setdefault(_pair(a), []).append((a["start"], a["end"]))
    if not by_pair:
        return 0.0, 0.0, []
    captured, missed = 0, []
    for pair, insts in by_pair.items():
        ok = any(
            (e - s) > 0 and intersect_duration(hl, [(s, e)]) / (e - s) >= min_overlap
            for s, e in insts
        )
        if ok:
            captured += 1
        else:
            missed.append(pair)
    raw = captured / len(by_pair)
    ratio = union_duration(hl) / duration if duration > 0 else 0.0
    over = max(0.0, ratio - budget)
    factor = max(0.0, 1.0 - over / budget)  # linear soft penalty (assumption)
    return raw, raw * factor, missed


def highlight_f1(highlights, important_segments):
    """Frame-level F1 vs consensus important segments (lists of {'start','end'})."""
    p = merge_intervals([(h["start"], h["end"]) for h in highlights])
    g = merge_intervals([(h["start"], h["end"]) for h in important_segments])
    lp, lg = union_duration(p), union_duration(g)
    if lp == 0 or lg == 0:
        return 0.0
    inter = intersect_duration(p, g)
    prec, rec = inter / lp, inter / lg
    return 0.0 if prec + rec == 0 else 2 * prec * rec / (prec + rec)


def label_accuracy(pairs):
    """pairs: list of (predicted_label, gt_label)."""
    return sum(p == g for p, g in pairs) / len(pairs) if pairs else 0.0
