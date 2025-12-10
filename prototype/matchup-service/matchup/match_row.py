# matchup/match_row.py

"""
Per-row matchup logic (Subtask 5).

Given a single SeaBASSRecord and an L2Grid, apply:
  - spatial/time/flag filters (from filters.py)
  - either window-based aggregation or nearest-pixel extraction
  - return a dict of satellite-derived columns for that row
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Sequence

import numpy as np

from .seabass_parser import SeaBASSRecord
from .l2_loader import L2Grid
from .filters import (
    build_valid_pixel_mask,
    find_nearest_valid_pixel,
    haversine_distance_km,
)
from .aggregator import aggregate_values


def _compute_distance_metrics(
    seabass_rec: SeaBASSRecord,
    l2: L2Grid,
    rows: np.ndarray,
    cols: np.ndarray,
) -> Optional[float]:
    """
    Compute minimum great-circle distance (km) from the SeaBASS point
    to the set of selected pixel indices.

    Returns None if rows/cols are empty.
    """
    if rows.size == 0:
        return None

    lats = l2.lat[rows, cols]
    lons = l2.lon[rows, cols]

    dists = haversine_distance_km(
        seabass_rec.lat,
        seabass_rec.lon,
        lats,
        lons,
    )
    return float(np.min(dists))


def _compute_time_metrics(
    seabass_rec: SeaBASSRecord,
    l2: L2Grid,
    rows: np.ndarray,
    cols: np.ndarray,
) -> Optional[float]:
    """
    Compute minimum |Δt| in seconds between the SeaBASS time and the
    selected pixel times.

    Returns None if no time info is available or selection is empty.
    """
    if l2.time is None or rows.size == 0:
        return None

    time_arr = np.array(l2.time)

    # Case 1: per-pixel time with same shape as lat/lon
    if time_arr.shape == l2.lat.shape:
        try:
            pixel_times = time_arr[rows, cols].astype(np.float64)
        except Exception:
            return None
    # Case 2: 1D time array per line
    elif time_arr.ndim == 1 and l2.lat.ndim == 2 and time_arr.shape[0] == l2.lat.shape[0]:
        try:
            # Use row index to pick line times and broadcast to columns
            pixel_times = time_arr[rows].astype(np.float64)
        except Exception:
            return None
    else:
        # Any other time shape: ignore for prototype
        return None

    center_sec = seabass_rec.time.timestamp()
    diffs = np.abs(pixel_times - center_sec)

    # If 1D per-line, diffs is 1D; that’s fine – min still makes sense.
    return float(np.min(diffs))


def match_record_to_l2(
    seabass_rec: SeaBASSRecord,
    l2: L2Grid,
    variable_names: Sequence[str],
    max_distance_km: Optional[float],
    max_time_diff_sec: Optional[float],
    bad_flag_mask: Optional[int],
    mode: str = "window",
) -> Dict[str, Any]:
    """
    Perform a satellite matchup for a single SeaBASS record.

    Args:
        seabass_rec: In-situ measurement (lat, lon, time, depth, variables).
        l2: L2Grid for a single OB.DAAC L2 granule.
        variable_names: List of geophysical variable names to extract.
        max_distance_km: Max allowed distance from in-situ point.
        max_time_diff_sec: Max allowed |Δt| in seconds.
        bad_flag_mask: Bitmask of "bad" flags to reject (see filters.build_flag_mask).
        mode:
            "window"  → aggregate over all valid pixels in the window
            "nearest" → use only the nearest valid pixel

    Returns:
        Dict of satellite-derived columns keyed like:
            sat_<var>_mean
            sat_<var>_median
            sat_<var>_std
            sat_<var>_n
        plus some generic matchup metrics:
            matchup_min_distance_km
            matchup_min_dt_sec
    """
    result: Dict[str, Any] = {}

    variable_names = [v.strip() for v in variable_names if v and v.strip()]

    if mode not in ("window", "nearest"):
        mode = "window"

    if mode == "nearest":
        # Find a single nearest valid pixel
        idx = find_nearest_valid_pixel(
            l2=l2,
            seabass_rec=seabass_rec,
            max_distance_km=max_distance_km,
            max_time_diff_sec=max_time_diff_sec,
            bad_flag_mask=bad_flag_mask,
        )

        if idx is None:
            # No valid pixel: fill with None / 0 for all requested vars
            for var in variable_names:
                prefix = f"sat_{var}"
                result[f"{prefix}_mean"] = None
                result[f"{prefix}_median"] = None
                result[f"{prefix}_std"] = None
                result[f"{prefix}_n"] = 0
            result["matchup_min_distance_km"] = None
            result["matchup_min_dt_sec"] = None
            return result

        row, col = idx

        # Distance metric (single pixel)
        d_km = haversine_distance_km(
            seabass_rec.lat,
            seabass_rec.lon,
            l2.lat[row, col],
            l2.lon[row, col],
        )
        result["matchup_min_distance_km"] = float(d_km)

        # Time metric (single pixel)
        if l2.time is not None:
            time_arr = np.array(l2.time)
            try:
                if time_arr.shape == l2.lat.shape:
                    t_val = float(time_arr[row, col])
                elif time_arr.ndim == 1 and l2.lat.ndim == 2 and time_arr.shape[0] == l2.lat.shape[0]:
                    t_val = float(time_arr[row])
                else:
                    t_val = None
            except Exception:
                t_val = None

            if t_val is not None:
                dt = abs(t_val - seabass_rec.time.timestamp())
                result["matchup_min_dt_sec"] = float(dt)
            else:
                result["matchup_min_dt_sec"] = None
        else:
            result["matchup_min_dt_sec"] = None

        # Aggregated stats for each variable (single-pixel = degenerate window)
        for var in variable_names:
            arr = l2.variables.get(var)
            prefix = f"sat_{var}"
            if arr is None:
                # Variable missing in this file
                result[f"{prefix}_mean"] = None
                result[f"{prefix}_median"] = None
                result[f"{prefix}_std"] = None
                result[f"{prefix}_n"] = 0
                continue

            vals = np.asarray(arr[row, col:col + 1])  # 1-element slice
            stats = aggregate_values(vals)
            result[f"{prefix}_mean"] = stats["mean"]
            result[f"{prefix}_median"] = stats["median"]
            result[f"{prefix}_std"] = stats["std"]
            result[f"{prefix}_n"] = stats["count"]

        return result

    # --- mode == "window" ---------------------------------------------------

    mask = build_valid_pixel_mask(
        l2=l2,
        seabass_rec=seabass_rec,
        max_distance_km=max_distance_km,
        max_time_diff_sec=max_time_diff_sec,
        bad_flag_mask=bad_flag_mask,
    )

    rows, cols = np.where(mask)

    # Distance/time metrics (can be None if no pixels)
    result["matchup_min_distance_km"] = _compute_distance_metrics(
        seabass_rec, l2, rows, cols
    )
    result["matchup_min_dt_sec"] = _compute_time_metrics(
        seabass_rec, l2, rows, cols
    )

    # For each variable: aggregate window values (or return None/0)
    for var in variable_names:
        prefix = f"sat_{var}"
        arr = l2.variables.get(var)
        if arr is None:
            # Not present in this granule
            result[f"{prefix}_mean"] = None
            result[f"{prefix}_median"] = None
            result[f"{prefix}_std"] = None
            result[f"{prefix}_n"] = 0
            continue

        if rows.size == 0:
            # No valid pixels in window
            stats = aggregate_values([])  # empty
        else:
            vals = arr[rows, cols]
            stats = aggregate_values(vals)

        result[f"{prefix}_mean"] = stats["mean"]
        result[f"{prefix}_median"] = stats["median"]
        result[f"{prefix}_std"] = stats["std"]
        result[f"{prefix}_n"] = stats["count"]

    return result
