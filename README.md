# CineCorteX: Track 04, Action-Aware Video Summarization

First-person video in, per-video JSON out: localised actions, importance ranking
and a highlight selection of at most 15% of the original duration.

## Requirements
- Python 3.10+
- ffmpeg and ffprobe on PATH (macOS: `brew install ffmpeg`, Ubuntu: `apt install ffmpeg`)

## Setup

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

## Run one video

    ./run.sh <video.mp4> <out.json>

## Run a folder of videos

    ./run_batch.sh data/videos outputs

## Check outputs (local sanity check)

    python3 code/submission/check_output.py outputs data/videos

## Layout
- code/ingest/: probing and decoding (duration, fps, size)
- code/perception/: action proposals (Member B)
- code/temporal/: interval cleanup and merging (Member B)
- code/selection/: importance ranking and 15% budget selection
- code/evaluation/: metrics (Member C)
- code/submission/: output adapter and checker

## Conventions
- All internal times are in seconds (float).
- The highlight budget uses the union of intervals, so overlaps count once.

## Status
Work in progress. main.py currently uses a placeholder highlight, to be
replaced by the real pipeline.
## Pipeline behaviour
main.py tries, in order: perception.predict (Member B's model), then
perception.baseline (motion baseline, no action labels), then a placeholder.
Highlights are always trimmed to fit the 15% budget.

## Evaluation
See code/evaluation/ (evaluate.py, metrics.py) and tests/ (run: python3 -m pytest -q).

## Highlight video (optional)
    python3 code/submission/compile_highlights.py <video.mp4> <result.json> <out.mp4>
