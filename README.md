# CineCorteX — Track 04: Action-Aware Video Summarization

This repository provides a deterministic inference pipeline for the Samsung PRISM
Hackathon 2026 Track 04 output contract. It writes one official-format JSON object
per input video and enforces temporal validity and the 15% highlight-union budget
whenever that budget is compatible with the required 4-second minimum highlight.

## Runtime requirements

- Python 3.10+
- `ffmpeg` and `ffprobe` on `PATH`
- NumPy (`pip install -r requirements.txt`)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
./run.sh <video.mp4> <out.json>
./run_batch.sh <videos_dir> outputs
python3 -m pytest -q
./check_all.sh [videos_dir] [outputs_dir]
```

Set the assigned team ID before inference. The repository examples use `T07`,
which is the default only to keep the starter command executable:

```bash
CINECORTEX_TEAM_ID=T07 ./run.sh video.mp4 outputs/video.json
```

The generated JSON uses exactly the organiser guide's six top-level fields:
`team_id`, `video_id`, `duration_sec`, `label`, `actions`, and `highlights`.
Actions and highlights use `segment: [start, end]`; the legacy provisional
`start`/`end` contract is no longer used at the submission boundary.

## Perception status — read before submission

No pretrained action-recognition checkpoint, trained temporal localizer, or raw
dataset video is included in the supplied repository. The built-in fallback is
therefore explicit and conservative:

- It extracts a low-resolution frame-difference trace with FFmpeg.
- It proposes and ranks 4-second windows for highlights under the 15% union
  duration budget (with a minimum-gap preference to reduce redundant adjacent
  clips).
- It does **not** infer semantic verb/noun actions. Its `actions` array is `[]`.
- For EPIC-KITCHENS-100, the video-level label is `cooking` because this
  challenge's EPIC split is cooking-only. This is dataset metadata, not a visual
  classification result. For FPVSum, the fallback label is `other` with score
  `0.0`; no visual category classifier is shipped.

Motion is not action recognition. The fallback highlights are visual-activity
proposals, not validated semantic highlights. No benchmark score or dataset
accuracy is claimed. See [`docs/MODEL_ASSESSMENT.md`](docs/MODEL_ASSESSMENT.md)
for why an available model name was not substituted for a compatible detector.

### Plug in a real recognizer

The pipeline supports an installed model as `module:function`:

```bash
CINECORTEX_PERCEPTION_PLUGIN=my_model.inference:predict ./run.sh video.mp4 out.json
```

The callable receives `(video_path, meta)`; `meta` includes `video_id`,
`duration_s`, `fps`, `width`, `height`, `codec`, `dataset`, and the manifest
duration where available. It should return a mapping similar to:

```python
{
    "label": {"name": "ski", "score": 0.82},
    "actions": [
        {"start": 12.4, "end": 18.2, "verb": "other", "noun": "other", "score": 0.73}
    ],
    "highlights": [
        {"start": 11.0, "end": 19.5, "importance": 0.91}
    ],
    "perception_source": "my_model_v1"
}
```

The adapter also accepts the official `segment: [start, end]` interval shape
for actions/highlights. Returned action classes are checked against
`data_manifest/supported_classes.json`; invalid intervals and confidence
values are removed, timestamps are clipped, and same-class duplicate/adjacent
proposals are conservatively merged. Different verb-noun pairs are never
merged just because their intervals overlap.

The plug-in must be importable in the isolated runtime and its checkpoints must
be made available by the submission package or the organiser's approved model
provisioning mechanism. A plug-in import/inference failure is logged and falls
back to the deterministic baseline; it is never silently reported as a model
prediction.

## Temporal and highlight policy

- Action timestamps are finite, clipped to media duration, vocabulary checked,
  confidence clamped to `[0, 1]`, sorted, de-duplicated, and deterministically
  merged only within the same verb-noun class.
- Highlight intervals are sorted and non-overlapping. The selector counts
  interval union, uses action-pair coverage as an additional utility when model
  actions exist, and avoids redundant neighbouring windows where possible.
- At least one 4-second highlight is required by the supplied challenge guide.
  For three manifest videos (`P03_26` 11.13s, `P26_30` 15.28s, `P28_23`
  25.16s), a 4-second minimum is mathematically larger than 15% of the video.
  The selector chooses the minimum 4-second interval in these cases; the
  organiser guide describes budget excess as a warning/soft penalty. The local
  validator reports it rather than hiding the conflict.
- Empty candidate sets produce a neutral opening interval of zero importance;
  it is not described as an important event.

## Validation and packaging

The organiser's `validate.py` is referenced by `data_manifest/TEAM_README.md`
but is absent from the uploaded ZIP. `code/evaluation/validate_official.py` is
an independent local approximation based on the supplied guide and examples; it
is **not** the organiser's official validator.

```bash
python3 code/evaluation/validate_official.py \
  --dir outputs \
  --manifest data_manifest/manifest.csv \
  --classes data_manifest/supported_classes.json
```

When all raw videos are available, run the full batch, then validate all 187
outputs and prepare the organiser-style archive:

```bash
./run_batch.sh /path/to/videos outputs
./make_package.sh T07
```

`make_package.sh` refuses to package an incomplete output directory, output
files that fail local validation, or a team ID mismatch. The raw EPIC-KITCHENS
and FPVSum videos are not in this repository. As a result, this checkout alone
cannot produce the required 187 evaluated outputs.

## Repository map

- `code/perception/`: motion fallback and recognizer plug-in boundary
- `code/temporal/`: action timestamp and class cleanup
- `code/selection/`: highlight interval union and budget selection
- `code/main.py`: inference orchestration and official JSON adapter
- `code/evaluation/validate_official.py`: local schema approximation
- `data_manifest/`: supplied class vocabulary and 187-video manifest
- `tests/`: unit and synthetic-video end-to-end tests
- `weights/`: intentionally empty unless the team adds approved checkpoints
