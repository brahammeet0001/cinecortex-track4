# Output contract (v0.1, provisional until the official validate.py is checked)

One JSON per video, named `<video_id>.json`.

    {
      "video_id": "string, same as filename without .json",
      "label": "string, video-level category (check supported_classes.json)",
      "actions": [
        {"verb": "cut", "noun": "onion", "start": 12.4, "end": 15.85, "score": 0.82}
      ],
      "highlights": [
        {"start": 12.4, "end": 15.85, "importance": 0.91}
      ]
    }

Rules:
- All times are seconds (float), 0 <= start < end <= video duration.
- Union of highlight intervals must be <= 15% of the video duration.
- Overlaps count once.
- Changes to this file need agreement from all three members and a version bump.
