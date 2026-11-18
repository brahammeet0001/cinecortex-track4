"""Fallback baseline: frame-difference 'motion' score per time bin.
Not action detection. Gives valid highlights under the 15% budget."""
import subprocess

import numpy as np

SAMPLE_FPS = 2     # time bins of 0.5 s
W, H = 64, 36
BUDGET = 0.15


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
    return np.concatenate([[0.0], diffs])  # bin i covers [i/fps, (i+1)/fps)


def predict(video_path, meta):
    dur = meta["duration_s"]
    scores = motion_profile(video_path)
    n = len(scores)
    smooth = np.convolve(scores, np.ones(3) / 3, mode="same")
    k = int(BUDGET * dur * SAMPLE_FPS)          # floor, so we stay under 15%
    k = max(1, min(k, n))
    top = np.sort(np.argsort(smooth)[::-1][:k])
    peak = float(smooth.max()) or 1.0

    # merge adjacent bins into intervals
    highlights, start, prev = [], None, None
    for i in top:
        if start is None:
            start = prev = i
        elif i == prev + 1:
            prev = i
        else:
            highlights.append((start, prev))
            start = prev = i
    if start is not None:
        highlights.append((start, prev))

    out = []
    for a, b in highlights:
        s = a / SAMPLE_FPS
        e = min((b + 1) / SAMPLE_FPS, dur)
        if e > s:
            imp = float(smooth[a:b + 1].mean() / peak)
            out.append({"start": round(s, 3), "end": round(e, 3), "importance": round(imp, 3)})
    return {"label": "unknown", "actions": [], "highlights": out}
