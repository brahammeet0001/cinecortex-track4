# Output contract v1.0 (official Samsung PRISM schema)

One file per video: `<video_id>.json`. Invalid JSON scores zero for that video.

    {
      "team_id": "string",
      "video_id": "string, same as filename without .json",
      "duration_sec": 123.4,
      "label": {"name": "<one of the 16 labels in supported_classes.json>", "score": 0.0},
      "actions": [
        {"segment": [12.4, 15.85], "verb": "cut", "noun": "onion", "score": 0.82}
      ],
      "highlights": [
        {"segment": [10.0, 16.0]}
      ]
    }

Rules
- Verbs and nouns come from supported_classes.json ("other" is allowed).
- duration_sec within 0.5 s of manifest.csv.
- Highlights: sorted, non-overlapping, at least one >= 4.0 s, total <= 15% of duration.
- No hardcoded video IDs anywhere in the code.

Internal format (what perception/predict.py returns; converted by code/submission/schema.py)

    {"label": "<name>" or {"name": ..., "score": ...},
     "actions": [{"verb","noun","start","end","score"}],
     "highlights": [{"start","end","importance"}]}
