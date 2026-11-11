"""Strict report JSON: numerical undefined values become null, never NaN tokens."""
import json
import math
import numpy as np


def json_safe(value):
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, np.generic):
        return json_safe(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def dumps(value, **kwargs):
    return json.dumps(json_safe(value), allow_nan=False, **kwargs)
