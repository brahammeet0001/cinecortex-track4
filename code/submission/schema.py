"""Converts internal predictions to the official Samsung PRISM output schema."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLASSES_PATH = ROOT / "data_manifest" / "supported_classes.json"


def _names(x):
    out = set()
    if isinstance(x, dict):
        for k, v in x.items():
            out.add(v if isinstance(v, str) else str(k))
    elif isinstance(x, list):
        for item in x:
            if isinstance(item, str):
                out.add(item)
            elif isinstance(item, dict):
                for key in ("name", "label", "verb", "noun", "class"):
                    if key in item:
                        out.add(str(item[key]))
                        break
    return out


def load_classes(path=None):
    """Returns (labels, verbs, nouns) as sets of strings."""
    p = Path(path) if path else CLASSES_PATH
    d = json.loads(p.read_text())

    def pick(needles, exclude=()):
        for k, v in d.items():
            kl = k.lower()
            if any(n in kl for n in needles) and not any(e in kl for e in exclude):
                return _names(v)
        return set()

    labels = pick(("label", "class", "categor"), exclude=("verb", "noun"))
    verbs = pick(("verb",))
    nouns = pick(("noun",))
    if not labels:
        raise RuntimeError(f"Could not read label names from {p}; check its structure")
    return labels, verbs, nouns


# ---------- highlight segments ----------

def _merge(ivs, gap):
    out = []
    for s, e, imp in sorted(ivs, key=lambda x: x[0]):
        if out and s <= out[-1][1] + gap:
            ps, pe, pi = out[-1]
            out[-1] = (ps, max(pe, e), max(pi, imp))
        else:
            out.append((s, e, imp))
    return out


def _total(ivs):
    return sum(e - s for s, e, _ in ivs)


def finalize_highlights(items, dur, budget=0.15, min_len=4.0, merge_gap=1.0):
    """items: [(start, end, importance)] -> sorted, non-overlapping segments,
    at least one >= min_len seconds, total <= budget * dur (small safety margin)."""
    cap = budget * dur - 0.05
    ivs = []
    for s, e, imp in items:
        s, e = max(0.0, float(s)), min(float(dur), float(e))
        if e - s > 1e-6:
            ivs.append((s, e, float(imp)))
    if not ivs or cap <= 0:
        return []
    ivs = _merge(ivs, 0.0)
    merged = _merge(ivs, merge_gap)
    if _total(merged) <= cap:
        ivs = merged
    if max(e - s for s, e, _ in ivs) < min_len:        # ensure one segment is long enough
        s, e, imp = max(ivs, key=lambda x: x[2])
        mid = (s + e) / 2
        ns = max(0.0, mid - min_len / 2)
        ne = ns + min_len
        if ne > dur:
            ne, ns = dur, max(0.0, dur - min_len)
        ivs = _merge(ivs + [(ns, ne, imp + 1.0)], 0.0)
    while _total(ivs) > cap and len(ivs) > 1:           # drop weakest, keep the longest
        anchor = max(ivs, key=lambda x: x[1] - x[0])
        drop = min((x for x in ivs if x is not anchor), key=lambda x: x[2])
        ivs = [x for x in ivs if x is not drop]
    if _total(ivs) > cap:
        s, e, imp = ivs[0]
        ivs = [(s, s + cap, imp)]
    return [(round(s, 3), round(e, 3), imp) for s, e, imp in sorted(ivs)]


# ---------- conversion ----------

def _seg(h):
    if "segment" in h:
        s, e = h["segment"]
    else:
        s, e = h["start"], h["end"]
    return float(s), float(e)


def to_official(meta, pred, classes, team_id):
    labels, verbs, nouns = classes
    dur = float(meta["duration_s"])

    lab = pred.get("label")
    if isinstance(lab, dict):
        name, score = lab.get("name"), float(lab.get("score", 0.0))
    else:
        name, score = lab, 0.0
    if name not in labels:                 # fallback guess until a classifier exists
        name, score = sorted(labels)[0], 0.0

    actions = []
    for a in pred.get("actions", []):
        try:
            s, e = _seg(a)
        except (KeyError, TypeError, ValueError):
            continue
        s, e = max(0.0, s), min(dur, e)
        if e <= s:
            continue
        v, n = a.get("verb"), a.get("noun")
        actions.append({
            "segment": [round(s, 3), round(e, 3)],
            "verb": v if v in verbs else "other",
            "noun": n if n in nouns else "other",
            "score": round(min(1.0, max(0.0, float(a.get("score", 0.0)))), 4),
        })

    items = []
    for h in pred.get("highlights", []):
        try:
            s, e = _seg(h)
        except (KeyError, TypeError, ValueError):
            continue
        items.append((s, e, float(h.get("importance", 0.5))))
    segs = finalize_highlights(items, dur)

    return {
        "team_id": team_id,
        "video_id": meta["video_id"],
        "duration_sec": round(dur, 3),
        "label": {"name": name, "score": round(min(1.0, max(0.0, score)), 4)},
        "actions": actions,
        "highlights": [{"segment": [s, e]} for s, e, _ in segs],
    }
