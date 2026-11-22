"""Deterministic visual-activity baseline; not a semantic action recognizer.

It computes low-resolution frame-difference energy and proposes 4-second
candidate windows. It intentionally emits no verb/noun actions because motion
alone cannot identify those labels.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np

from selection.budget import select_highlights

SAMPLE_FPS = 2
WIDTH, HEIGHT = 64, 36
WINDOW_SECONDS = 4.0
STRIDE_SECONDS = 2.0


def motion_profile(video_path: str | Path) -> np.ndarray:
    """Decode a small grayscale motion trace using FFmpeg."""
    cmd = [
        "ffmpeg", "-nostdin", "-v", "error", "-i", str(video_path),
        "-vf", f"fps={SAMPLE_FPS},scale={WIDTH}:{HEIGHT},format=gray",
        "-f", "rawvideo", "-pix_fmt", "gray", "-",
    ]
    result = subprocess.run(cmd, capture_output=True, check=True)
    frame_bytes = WIDTH * HEIGHT
    usable = len(result.stdout) - (len(result.stdout) % frame_bytes)
    n_frames = usable // frame_bytes
    if n_frames == 0:
        return np.zeros(1, dtype=np.float32)
    frames = np.frombuffer(result.stdout[:usable], dtype=np.uint8)
    frames = frames.reshape(n_frames, HEIGHT, WIDTH).astype(np.float32)
    if n_frames == 1:
        return np.zeros(1, dtype=np.float32)
    diff = np.abs(np.diff(frames, axis=0)).mean(axis=(1, 2))
    return np.concatenate((np.zeros(1, dtype=np.float32), diff.astype(np.float32)))


def propose_windows(profile: np.ndarray, duration: float) -> list[dict[str, float]]:
    """Create overlapping 4s windows scored by robustly normalised motion."""
    if duration <= 0:
        return []
    window = min(WINDOW_SECONDS, duration)
    if window < 4.0 - 1e-6:
        # Manifest videos are expected to be longer; this keeps the function
        # well-defined for arbitrary short test clips.
        window = duration
    stride = STRIDE_SECONDS
    step = 1.0 / SAMPLE_FPS
    values = np.asarray(profile, dtype=np.float32).reshape(-1)
    if values.size == 0:
        values = np.zeros(1, dtype=np.float32)
    smooth = np.convolve(values, np.ones(3, dtype=np.float32) / 3.0, mode="same")
    window_bins = max(1, int(round(window / step)))
    stride_bins = max(1, int(round(stride / step)))

    raw_scores: list[tuple[float, float, float]] = []
    last_start = max(0, int(np.ceil((duration - window) / step)))
    starts = list(range(0, last_start + 1, stride_bins))
    if not starts or starts[-1] != last_start:
        starts.append(last_start)
    for start_bin in starts:
        start_sec = start_bin * step
        end_sec = min(duration, start_sec + window)
        if end_sec - start_sec < min(4.0, duration) - 1e-6:
            continue
        left = min(start_bin, max(0, smooth.size - 1))
        right = min(smooth.size, left + window_bins)
        chunk = smooth[left:right]
        if chunk.size == 0:
            value = 0.0
        else:
            # Mean + a modest upper-tail term rewards sustained activity
            # without letting a single abrupt camera shake dominate.
            value = float(0.75 * np.mean(chunk) + 0.25 * np.percentile(chunk, 75))
        raw_scores.append((start_sec, end_sec, value))

    if not raw_scores:
        return []
    score_values = np.asarray([row[2] for row in raw_scores], dtype=np.float32)
    lo, hi = float(np.percentile(score_values, 10)), float(np.percentile(score_values, 95))
    scale = hi - lo
    candidates = []
    for start, end, score in raw_scores:
        importance = 0.0 if scale <= 1e-8 else float(np.clip((score - lo) / scale, 0.0, 1.0))
        candidates.append({"start": start, "end": end, "importance": importance})
    return candidates


def predict(video_path: str, meta: dict) -> dict:
    duration = float(meta["duration_s"])
    try:
        profile = motion_profile(video_path)
    except Exception as exc:
        # A video may be probeable but not fully decodable. Keep the pipeline
        # explicit and deterministic rather than producing fabricated actions.
        print(f"WARNING: motion trace unavailable ({exc}); using neutral fallback", file=sys.stderr)
        profile = np.zeros(1, dtype=np.float32)
    candidates = propose_windows(profile, duration)
    highlights = select_highlights(candidates, duration)
    return {
        "label": "other",
        "label_score": 0.0,
        "actions": [],
        "highlights": highlights,
        "perception_source": "frame_difference_fallback",
    }
