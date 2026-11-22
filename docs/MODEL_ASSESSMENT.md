# Model feasibility assessment

## What was checked

The submitted ZIP contains no model configuration, model source, checkpoint,
weight file, or dataset video. The runtime initially provides FFmpeg and NumPy;
there is no repository-specific trained inference stack. A model architecture
name alone would not make the submission reproducible.

## Candidate directions

| Candidate | What it can contribute | Why it was not wired as the default detector |
|---|---|---|
| EPIC-KITCHENS ActionFormer-style detection | A suitable temporal detection formulation: separate verb and noun detection heads over clip features, with boundary regression | Requires a compatible feature backbone, EPIC-trained weights/configuration, preprocessing, and checkpoint files. None are in the ZIP. The EPIC challenge report describes this two-head feature + ActionFormer route; it is not a drop-in generic classifier. |
| RepLAI EPIC-KITCHENS checkpoints | Egocentric representation/action recognition; public project lists EPIC-KITCHENS verb/noun recognition checkpoints | Recognition scores for a supplied clip do not, by themselves, provide action start/end boundaries. Rebuilding temporal detection around those features would require additional trained components and evaluation data. |
| HD-EPIC VideoMAE | Egocentric short-clip recognition for verbs/objects | HD-EPIC uses a different label space (the cited release describes 30 verbs and 50 object classes for its clip task); it does not directly cover this repository's 98 verbs/301 nouns or provide full-video temporal boundaries. |

## Decision

The repository ships a transparent frame-difference proposal fallback and a
`CINECORTEX_PERCEPTION_PLUGIN=module:function` interface. This provides a
reproducible end-to-end executable and keeps the action/localization boundary
replaceable. It does **not** claim a semantic action detector or a benchmark
score. The missing compatible checkpoint and trained boundary model remain the
main scoring blocker for Action mAP (25%) and action coverage (40%).

## References

- EPIC-KITCHENS 2022 challenge report, *Detecting Egocentric Actions with
  ActionFormer*: https://epic-kitchens.github.io/Reports/EPIC-KITCHENS-Challenges-2022-Report.pdf
- RepLAI project and its listed EPIC-KITCHENS checkpoints:
  https://github.com/HimangiM/RepLAI
- HD-EPIC CVPR 2025 paper:
  https://openaccess.thecvf.com/content/CVPR2025/papers/Perrett_HD-EPIC_A_Highly-Detailed_Egocentric_Video_Dataset_CVPR_2025_paper.pdf
- EPIC-KITCHENS-100 annotations / detection task guidance:
  https://github.com/epic-kitchens/epic-kitchens-100-annotations
