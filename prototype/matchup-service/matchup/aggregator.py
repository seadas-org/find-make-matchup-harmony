# matchup/aggregator.py

from __future__ import annotations

from typing import Dict, Any

import numpy as np


def aggregate_values(values) -> Dict[str, Any]:
    """
    Compute basic statistics over a 1D array-like of pixel values.

    Returns:
        {
            "mean": float | None,
            "median": float | None,
            "std": float | None,
            "count": int,
        }

    If there are no finite values, mean/median/std are None and count is 0.
    """
    arr = np.asarray(values, dtype=float).ravel()
    if arr.size == 0:
        return {"mean": None, "median": None, "std": None, "count": 0}

    valid = np.isfinite(arr)
    if not valid.any():
        return {"mean": None, "median": None, "std": None, "count": 0}

    v = arr[valid]
    count = int(v.size)
    mean = float(np.mean(v))
    median = float(np.median(v))
    std = float(np.std(v, ddof=1)) if count > 1 else 0.0

    return {
        "mean": mean,
        "median": median,
        "std": std,
        "count": count,
    }
