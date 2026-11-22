# AI Disclosure

## AI tools used
- Claude (Anthropic) was used by Member A (Brahammeet) for planning the work, writing and
  debugging shell scripts (batch runner, check_all.sh, packaging), drafting the output-schema
  converter, the local output checker, unit tests and README sections, and step-by-step
  troubleshooting of git, Docker and command-line errors. Member A ran and tested this code.
- Member B used AI tools to help implement the action cleanup, highlight selection, official-schema integration, tests and documentation. Member B ran and tested this code.
- Claude (Anthropic) was used by Member C for evaluation code, the package checker, tests, the presentation and demo-script drafts. Member C ran and tested this code.

## Models used by the pipeline
- No pretrained or external model is used. Perception is a frame-difference motion heuristic built with FFmpeg and NumPy.
- No training data was used. EPIC-KITCHENS-100 videos were only used to test the pipeline locally. No ground truth is copied or hardcoded.

## What humans did
- Reviewed and ran all AI-assisted code, wrote and ran tests, and validated outputs with
  code/evaluation/validate_official.py and the local checks.
- Chose the architecture, the fallback order and the handling of the 15% and 4 s highlight rules.
- Tested from a clean clone.

## Limits
- AI-assisted code may contain errors our tests do not cover. Known limitations are in README.md.
