# CineCorteX Track 04 — Member B delivery audit

## Initial repository audit

- Baseline test suite: **41 passed** before edits.
- Runtime available during implementation: Python 3.13.5, FFmpeg/FFprobe 7.1.5, NumPy 2.3.5.
- The original inference code emitted a provisional schema (`label` as a string,
  action/highlight `start` and `end`) rather than the six-field official example.
- The original motion baseline always returned `actions: []` and `label: "unknown"`;
  it did not localize semantic actions.
- The temporal package was empty.
- The original motion baseline could emit many sub-4-second highlight pieces.
- `code/submission/CONTRACT.md` was provisional and conflicted with
  `data_manifest/TEAM_README.md` and the supplied examples.
- `validate.py` (the organiser validator) is not in the ZIP. Only an independent
  repository-local approximation is available.
- No raw dataset videos, model architecture, trained checkpoint, or weights are
  included. `outputs/` contained two stale legacy-format test JSONs, not the
  required 187 manifest predictions.
- The ZIP contains no `.git` directory, branch name, or complete Git history.

## Implemented

- Added deterministic action cleaning in `code/temporal/`: clipping, finite
  timestamp/score checks, vocabulary enforcement, duplicate handling, same-class
  adjacency merging, deterministic sorting, and preservation of overlapping
  different classes.
- Added importance/action-coverage-aware highlight selection and interval-union
  budget accounting.
- Reworked motion proposals into 4-second candidate windows and explicit
  non-overlapping highlight selection.
- Added a `module:function` perception plug-in boundary for a compatible trained
  recognizer. The active path is logged; fallback never fabricates verb/noun
  predictions.
- Integrated the official six-field JSON schema in `code/main.py` and validate
  generated outputs locally before writing them.
- Updated the local checker, batch runner, complete-output packaging guard,
  README, contract, requirements, and tests.
- Added documentation of model feasibility and known submission blockers.
- Removed two stale legacy-format JSON files from `outputs/` so they cannot be
  mistaken for organiser-ready predictions.

## Verification performed

| Check | Result |
|---|---|
| Original test suite before edits | 41 passed |
| Final `python3 -m pytest -q` | **53 passed** |
| `./check_all.sh` without raw datasets | Unit tests pass; batch and output checks correctly skip because there are no source videos or JSON outputs; reports organiser `validate.py` absent |
| `./run.sh` on a synthetic 40-second MP4 | Generated official-format JSON; local validators passed |
| `./run_batch.sh` on a synthetic MP4 | 1 succeeded, 0 failed; local validator passed (non-manifest ID warning expected) |
| `bash -n` on run/check/package scripts | Passed |
| `python3 -m compileall -q code tests` | Passed |
| `./make_package.sh T07` | Correctly refused: 0 outputs present, 187 required |

## Remaining blockers / risks

1. **Semantic action perception is not implemented by the fallback.** The
   Action mAP (25%) and action-coverage (40%) metrics need a trained
   verb/noun temporal detector. The ZIP contains no compatible checkpoint.
2. **FPVSum label classification is not implemented by the fallback.** The
   fallback emits valid `other` with score `0.0`; the 10% label-accuracy metric
   needs a visual classifier.
3. Highlight proposals are based on low-resolution frame differences, not
   semantic importance. Highlight F1 is therefore unmeasured and likely limited.
4. The raw 138 EPIC-KITCHENS and 49 FPVSum challenge videos are absent, so no
   manifest-wide inference, benchmark evaluation, or 187-output package was
   produced.
5. The organiser `validate.py` is missing. The included validator is only a
   local approximation until the official script is supplied.
6. Three manifest durations (11.13s, 15.28s, 25.16s) make a 4.0s minimum
   highlight exceed 15% of duration. The guide describes budget excess as a
   warning/soft penalty, so the selector keeps the minimum 4s segment and the
   local validator reports the unavoidable overage.
7. The sample team ID `T07` is the executable default because both supplied
   examples use it. Set `CINECORTEX_TEAM_ID` to the actual assigned ID before
   generating the final outputs.

No dataset scores, action detections, official validation, or GitHub push are
claimed.
