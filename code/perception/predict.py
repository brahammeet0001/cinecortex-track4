"""Perception entry point with an explicit external-model plug-in boundary.

Set CINECORTEX_PERCEPTION_PLUGIN to ``module:function`` to call a team's
installed recognizer. The function receives ``(video_path, meta)`` and must
return a mapping with ``actions`` and optionally ``label`` / ``highlights``.
Without a plug-in, the deterministic motion-proposal fallback is used.
"""
from __future__ import annotations

import importlib
import os
import sys
from collections.abc import Mapping
from typing import Any

from perception.baseline import predict as fallback_predict


def _load_plugin():
    spec = os.environ.get("CINECORTEX_PERCEPTION_PLUGIN", "").strip()
    if not spec:
        return None
    if ":" not in spec:
        raise ValueError("CINECORTEX_PERCEPTION_PLUGIN must be module:function")
    module_name, function_name = spec.split(":", 1)
    module = importlib.import_module(module_name)
    fn = getattr(module, function_name)
    if not callable(fn):
        raise TypeError(f"Perception plug-in {spec!r} is not callable")
    return fn


def predict(video_path: str, meta: dict) -> dict[str, Any]:
    try:
        plugin = _load_plugin()
    except Exception as exc:
        print(f"WARNING: could not load perception plug-in: {exc}", file=sys.stderr)
        plugin = None
    if plugin is not None:
        try:
            result = plugin(video_path, meta)
            if not isinstance(result, Mapping):
                raise TypeError("plug-in must return a mapping")
            output = dict(result)
            output["perception_source"] = output.get("perception_source", "external_plugin")
            print(f"INFO: perception source={output['perception_source']}", file=sys.stderr)
            return output
        except Exception as exc:
            print(f"WARNING: perception plug-in failed; using fallback: {exc}", file=sys.stderr)
    print(
        "INFO: perception source=frame_difference_fallback; no semantic action model/checkpoint configured; actions=[]",
        file=sys.stderr,
    )
    return fallback_predict(video_path, meta)
