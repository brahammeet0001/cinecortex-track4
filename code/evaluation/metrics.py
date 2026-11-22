"""Metrics for the OFFICIAL Track 04 schema (see TEAM_README.md in the student package).

Official scoring (from TEAM_README):
  Action mAP 25%      EPIC videos, `actions`, verb-noun overlap at tIoU 0.1..0.5
  Action coverage 40% EPIC videos, `highlights`, share of distinct GT action pairs captured,
                      soft length penalty above the 15% budget
  Highlight F1 25%    FPVSum videos, frame-level F1 vs top-15% consensus importance frames
  Label accuracy 10%  FPVSum videos, label.name
Highlight segments shorter than 4.0 s are ignored during scoring (per README).

ASSUMPTIONS (organisers did not publish exact formulas; change here if they do):
  - mAP: per verb-noun class AP (all-point interpolation), mean over classes, then over thresholds;
    predictions ranked by `score`.
  - coverage: a GT (verb, noun) pair is captured if >= `min_overlap` of one of its instances lies
    inside the scored highlights. Penalty factor = max(0, 1 - over / budget), linear.
  - F1: computed exactly on intervals (equals frame-level F1 in the limit of fine sampling).
"""
from .intervals import intersect_duration, merge_intervals, seg, tiou, union_duration

TIOU_THRESHOLDS = (0.1, 0.2, 0.3, 0.4, 0.5)
MIN_HIGHLIGHT_S = 4.0


def _pair(a):
    return (a["verb"], a["noun"])


def scored_highlights(highlights, min_len=MIN_HIGHLIGHT_S):
    """Segments that count for scoring (>= 4.0 s)."""
    return [seg(h) for h in highlights if seg(h)[1] - seg(h)[0] >= min_len - 1e-9]


def _average_precision(dets, n_gt, gt_by_vid, thr):
    if n_gt == 0:
        return None
    dets = sorted(dets, key=lambda d: -d[0])
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
    """preds/gts: {video_id: [{'segment':[s,e], 'verb','noun', ('score')}]} (EPIC videos)."""
    classes = {_pair(a) for acts in gts.values() for a in acts}
    per_class_all = {c: [] for c in classes}
    for thr in thresholds:
        for c in classes:
            gt_by_vid = {vid: [seg(a) for a in acts if _pair(a) == c] for vid, acts in gts.items()}
            n_gt = sum(len(v) for v in gt_by_vid.values())
            dets = [(a.get("score", 1.0), vid, *seg(a))
                    for vid, acts in preds.items() for a in acts if _pair(a) == c]
            ap = _average_precision(dets, n_gt, gt_by_vid, thr)
            if ap is not None:
                per_class_all[c].append(ap)
    per_class = {c: sum(v) / len(v) for c, v in per_class_all.items() if v}
    m = sum(per_class.values()) / len(per_class) if per_class else 0.0
    return m, per_class


def action_coverage(highlights, gt_actions, duration, budget=0.15, min_overlap=0.5):
    """(raw, penalised, missed_pairs) for ONE EPIC video."""
    hl = scored_highlights(highlights)
    by_pair = {}
    for a in gt_actions:
        by_pair.setdefault(_pair(a), []).append(seg(a))
    if not by_pair:
        return 0.0, 0.0, []
    captured, missed = 0, []
    for pair, insts in by_pair.items():
        ok = any((e - s) > 0 and intersect_duration(hl, [(s, e)]) / (e - s) >= min_overlap
                 for s, e in insts)
        if ok:
            captured += 1
        else:
            missed.append(pair)
    raw = captured / len(by_pair)
    ratio = union_duration([seg(h) for h in highlights]) / duration if duration > 0 else 0.0
    over = max(0.0, ratio - budget)
    factor = max(0.0, 1.0 - over / budget)
    return raw, raw * factor, missed


def highlight_f1(highlights, important_segments):
    """Frame-level F1 for ONE FPVSum video. important_segments = [[s, e], ...]."""
    p = merge_intervals(scored_highlights(highlights))
    g = merge_intervals([(float(s), float(e)) for s, e in important_segments])
    lp, lg = union_duration(p), union_duration(g)
    if lp == 0 or lg == 0:
        return 0.0
    inter = intersect_duration(p, g)
    prec, rec = inter / lp, inter / lg
    return 0.0 if prec + rec == 0 else 2 * prec * rec / (prec + rec)


def label_accuracy(pairs):
    """pairs = [(predicted label.name, gt label)]."""
    return sum(p == g for p, g in pairs) / len(pairs) if pairs else 0.0
