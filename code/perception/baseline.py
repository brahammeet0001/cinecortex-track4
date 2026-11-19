"""Fallback baseline: frame-difference 'motion' score, selecting 4 s windows.
Not action detection. Returns internal format (start/end/importance)."""
import subprocess

import numpy as np

SAMPLE_FPS = 2        # time bins of 0.5 s
MIN_LEN = 4.0
W, H = 64, 36
BUDGET = 0.14         # below the hard 15% limit


def motion_profile(video_path):
    cmd = ["ffmpeg", "-loglevel", "error", "-i", str(video_path),
           "-vf", f"fps={SAMPLE_FPS},scale={W}:{H},format=gray",
           "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    arr = np.frombuffer(raw, dtype=np.uint8)
    n = len(arr) // (W * H)
    if n < 2:
        return np.zeros(max(n, 1))
    frames = arr[: n * W * H].reshape(n, H, W).astype(np.float32)
    diffs = np.abs(np.diff(frames, axis=0)).mean(axis=(1, 2))
    return np.concatenate([[0.0], diffs])


def predict(video_path, meta):
    dur = meta["duration_s"]
    scores = motion_profile(video_path)
    n = len(scores)
    win = max(1, min(int(MIN_LEN * SAMPLE_FPS), n))
    csum = np.concatenate([[0.0], np.cumsum(scores)])
    wscore = (csum[win:] - csum[:-win]) / win
    peak = float(wscore.max()) or 1.0
    order = np.argsort(wscore)[::-1]
    max_bins = int(BUDGET * dur * SAMPLE_FPS)

    taken = np.zeros(n, dtype=bool)
    chosen, used = [], 0
    for i in order:
        if used + win > max_bins:
            break
        if taken[i:i + win].any():
            continue
        taken[i:i + win] = True
        chosen.append(int(i))
        used += win
    if not chosen:
        chosen = [int(order[0])]

    highlights = []
    for i in sorted(chosen):
        s, e = i / SAMPLE_FPS, min((i + win) / SAMPLE_FPS, dur)
        highlights.append({"start": round(s, 3), "end": round(e, 3),
                           "importance": round(float(wscore[i]) / peak, 3)})
    return {"label": "unknown", "actions": [], "highlights": highlights}
