# matchup/match_row.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple, Any

import numpy as np

from matchup.l2_loader import L2Grid
from matchup.seabass_parser import SeaBASSRecord


# ----------------------------
# Utilities
# ----------------------------

def haversine_km(lat1, lon1, lat2, lon2) -> np.ndarray:
    """
    Vectorized haversine distance.
    lat/lon in degrees. Returns km.
    """
    R = 6371.0
    lat1r = np.deg2rad(lat1)
    lon1r = np.deg2rad(lon1)
    lat2r = np.deg2rad(lat2)
    lon2r = np.deg2rad(lon2)
    dlat = lat2r - lat1r
    dlon = lon2r - lon1r
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1r) * np.cos(lat2r) * np.sin(dlon / 2.0) ** 2
    return 2.0 * R * np.arcsin(np.sqrt(a))


def _compute_min_distance_km(seabass_rec: SeaBASSRecord, l2: L2Grid, rows: np.ndarray, cols: np.ndarray) -> Optional[float]:
    if rows.size == 0:
        return None
    lat = l2.lat[rows, cols].astype("float64")
    lon = l2.lon[rows, cols].astype("float64")
    d = haversine_km(seabass_rec.lat, seabass_rec.lon, lat, lon)
    d = d[np.isfinite(d)]
    if d.size == 0:
        return None
    return float(np.min(d))


def _compute_time_metrics_from_l2_time(
    seabass_rec: SeaBASSRecord,
    l2: L2Grid,
    rows: np.ndarray,
    cols: np.ndarray,
) -> Optional[float]:
    """
    Compute min |Δt| using l2.time if available.

    Supports:
      - per-pixel time: shape == l2.lat.shape
      - per-line time:  1D array with length == number of rows in l2.lat
    Assumes l2.time values are epoch seconds (float).
    """
    if rows.size == 0 or l2.time is None:
        return None

    try:
        time_arr = np.asarray(l2.time, dtype="float64")
    except Exception:
        return None

    center_sec = float(seabass_rec.time.timestamp())

    # Case 1: per-pixel
    if time_arr.shape == l2.lat.shape:
        pixel_times = time_arr[rows, cols]
    # Case 2: per-scanline/per-row
    elif time_arr.ndim == 1 and time_arr.shape[0] == l2.lat.shape[0]:
        pixel_times = time_arr[rows]
    else:
        return None

    diffs = np.abs(pixel_times - center_sec)
    diffs = diffs[np.isfinite(diffs)]
    if diffs.size == 0:
        return None
    return float(np.min(diffs))


def _compute_min_dt_sec(
    seabass_rec: SeaBASSRecord,
    l2: L2Grid,
    rows: np.ndarray,
    cols: np.ndarray,
) -> Optional[float]:
    """
    Compute min |Δt| in seconds.
    Prefer l2.time if available; otherwise fall back to l2.granule_datetime_utc.
    """
    # 1) Prefer per-pixel/per-line time if present
    dt = _compute_time_metrics_from_l2_time(seabass_rec, l2, rows, cols)
    if dt is not None:
        return dt

    # 2) Fallback: granule reference time parsed from filename
    gdt = getattr(l2, "granule_datetime_utc", None)
    if gdt is not None:
        try:
            return float(abs(gdt.timestamp() - seabass_rec.time.timestamp()))
        except Exception:
            return None

    return None


def _apply_flag_mask(flags: np.ndarray, bad_flag_mask: int) -> np.ndarray:
    """
    Returns boolean array True where pixel is GOOD (i.e., no bad flags set).
    flags is uint bitmask array; bad_flag_mask is int.
    """
    return (flags & np.uint32(bad_flag_mask)) == 0


def _subset_window_indices(
    seabass_rec: SeaBASSRecord,
    l2: L2Grid,
    max_distance_km: float,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Select all pixels within a radius of seabass point.
    Returns (rows, cols) index arrays.
    """
    d = haversine_km(seabass_rec.lat, seabass_rec.lon, l2.lat.astype("float64"), l2.lon.astype("float64"))
    mask = np.isfinite(d) & (d <= max_distance_km)
    rows, cols = np.where(mask)
    return rows, cols


def _subset_nearest_indices(
    seabass_rec: SeaBASSRecord,
    l2: L2Grid,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Find nearest pixel by squared distance in lat/lon space (fast, good enough for prototype).
    """
    dist2 = (l2.lat.astype("float64") - seabass_rec.lat) ** 2 + (l2.lon.astype("float64") - seabass_rec.lon) ** 2
    i, j = np.unravel_index(np.nanargmin(dist2), dist2.shape)
    return np.array([i], dtype=int), np.array([j], dtype=int)


def _aggregate(values: np.ndarray) -> Dict[str, Any]:
    """
    Aggregate numeric values (expects 1D array of finite floats).
    """
    if values.size == 0:
        return {"mean": None, "median": None, "std": None, "n": 0}

    # ddof=0: population std
    return {
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "std": float(np.std(values, ddof=0)),
        "n": int(values.size),
    }


# ----------------------------
# Main per-row matcher
# ----------------------------

def match_record_to_l2(
    seabass_rec: SeaBASSRecord,
    l2: L2Grid,
    variable_names: Sequence[str],
    max_distance_km: float,
    max_time_diff_sec: float,
    bad_flag_mask: Optional[int] = None,
    mode: str = "window",
) -> Dict[str, Any]:
    """
    Match one SeaBASS record against one L2 granule and return computed matchup columns.
    """
    result: Dict[str, Any] = {
        "matchup_min_distance_km": None,
        "matchup_min_dt_sec": None,
    }

    if mode not in ("window", "nearest"):
        raise ValueError(f"Unsupported mode: {mode}")

    # Select pixels
    if mode == "nearest":
        rows, cols = _subset_nearest_indices(seabass_rec, l2)
    else:
        rows, cols = _subset_window_indices(seabass_rec, l2, max_distance_km)

    if rows.size == 0:
        # No spatial candidates
        for v in variable_names:
            result[f"sat_{v}_mean"] = None
            result[f"sat_{v}_median"] = None
            result[f"sat_{v}_std"] = None
            result[f"sat_{v}_n"] = 0
        return result

    # Time tolerance filter (if we can compute dt)
    dt_min = _compute_min_dt_sec(seabass_rec, l2, rows, cols)
    if dt_min is not None and dt_min > max_time_diff_sec:
        # Too far in time; treat as no match
        for v in variable_names:
            result[f"sat_{v}_mean"] = None
            result[f"sat_{v}_median"] = None
            result[f"sat_{v}_std"] = None
            result[f"sat_{v}_n"] = 0
        # still record dt_min for debugging if you want:
        result["matchup_min_dt_sec"] = dt_min
        # and distance:
        result["matchup_min_distance_km"] = _compute_min_distance_km(seabass_rec, l2, rows, cols)
        return result

    # Apply flag filter if available
    if bad_flag_mask is not None and l2.flags is not None:
        good = _apply_flag_mask(l2.flags[rows, cols].astype(np.uint32), int(bad_flag_mask))
        rows = rows[good]
        cols = cols[good]
        if rows.size == 0:
            for v in variable_names:
                result[f"sat_{v}_mean"] = None
                result[f"sat_{v}_median"] = None
                result[f"sat_{v}_std"] = None
                result[f"sat_{v}_n"] = 0
            return result

    # Record metrics
    result["matchup_min_distance_km"] = _compute_min_distance_km(seabass_rec, l2, rows, cols)
    result["matchup_min_dt_sec"] = _compute_min_dt_sec(seabass_rec, l2, rows, cols)

    # Aggregate each requested variable
    for v in variable_names:
        arr = l2.variables.get(v)
        if arr is None:
            result[f"sat_{v}_mean"] = None
            result[f"sat_{v}_median"] = None
            result[f"sat_{v}_std"] = None
            result[f"sat_{v}_n"] = 0
            continue

        vals = arr[rows, cols].astype("float64")
        vals = vals[np.isfinite(vals)]
        stats = _aggregate(vals)

        result[f"sat_{v}_mean"] = stats["mean"]
        result[f"sat_{v}_median"] = stats["median"]
        result[f"sat_{v}_std"] = stats["std"]
        result[f"sat_{v}_n"] = stats["n"]

    return result
