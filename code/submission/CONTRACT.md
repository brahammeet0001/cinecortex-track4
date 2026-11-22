# Track 04 submission output contract (organiser guide takes priority)

The provisional v0.1 format was superseded after inspecting
`data_manifest/TEAM_README.md` and the supplied examples. The inference
boundary now emits exactly this structure:

```json
{
  "team_id": "T07",
  "video_id": "P02_109",
  "duration_sec": 512.3,
  "label": {"name": "cooking", "score": 0.96},
  "actions": [
    {"segment": [12.4, 18.2], "verb": "open", "noun": "fridge", "score": 0.88}
  ],
  "highlights": [
    {"segment": [11.0, 19.5]}
  ]
}
```

Rules are defined by the supplied `data_manifest/TEAM_README.md`: supported
vocabulary, timestamps in seconds, action and label confidence in `[0, 1]`,
chronological non-overlapping highlights, a 4-second minimum highlight, and a
15% total highlight-duration target. Manifest duration is used in the output
when the probed media duration is within the stated ±0.5-second tolerance.

The original organiser `validate.py` is not present in the uploaded repository.
`code/evaluation/validate_official.py` is a locally implemented approximation,
not an official validator.
