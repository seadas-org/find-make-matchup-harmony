# matchup/filters.py

"""
Pixel-level filtering utilities for the matchup engine.

Responsibilities (Subtask 3):
  - Spatial filtering  (max distance from in situ location)
  - Temporal filtering (max time difference)
  - Flag-based filtering (reject pixels with bad flags)
  - Convenience helpers to get valid masks / indices

This module is intentionally stateless and operates on L2Grid
objects (from l2_loader.py) and simple scalar parameters.
"""

from __future__ import annotations

import numpy as np
from typing import Optional, Tuple

from .l2_loader import L2Grid
from .seabass_parser import SeaBASSRecord


# --- basic geodesy helpers -------------------------------------------------


def haversine_distance_km(
    lat1_deg: float,
    lon1_deg: float,
    lat2_deg: np.ndarray,
    lon2_deg: np.ndarray,
    radius_km: float = 6371.0,
) -> np.ndarray:
    """
    Compute great-circle distance (km) between a single point
    (lat1_deg, lon1_deg) and arrays of points (lat2_deg, lon2_deg).

    All inputs are in degrees. Output is same shape as lat2_deg/lon2_deg.
    """
    lat1 = np.deg2rad(lat1_deg)
    lon1 = np.deg2rad(lon1_deg)
    lat2 = np.deg2rad(lat2_deg)
    lon2 = np.deg2rad(lon2_deg)

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    sin_dlat = np.sin(dlat / 2.0)
    sin_dlon = np.sin(dlon / 2.0)

    a = sin_dlat**2 + np.cos(lat1) * np.cos(lat2) * sin_dlon**2
    c = 2.0 * np.arcsin(np.minimum(1.0, np.sqrt(a)))

    return radius_km * c


# --- individual masks ------------------------------------------------------


def build_spatial_mask(
    l2: L2Grid,
    center_lat: float,
    center_lon: float,
    max_distance_km: Optional[float],
) -> np.ndarray:
    """
    Build a boolean mask selecting pixels within max_distance_km
    of the (center_lat, center_lon) point.

    If max_distance_km is None or <= 0, returns an all-True mask.
    """
    shape = l2.lat.shape
    mask = np.ones(shape, dtype=bool)

    if max_distance_km is None or max_distance_km <= 0:
        return mask

    distances = haversine_distance_km(center_lat, center_lon, l2.lat, l2.lon)
    mask &= distances <= max_distance_km
    return mask


def build_time_mask(
    l2: L2Grid,
    center_time,
    max_time_diff_sec: Optional[float],
) -> np.ndarray:
    """
    Build a boolean mask selecting pixels whose time is within
    max_time_diff_sec of center_time.

    Assumptions / behavior:
      - If l2.time is None: returns an all-True mask.
      - If max_time_diff_sec is None or <= 0: returns all-True.
      - If l2.time has the same shape as lat/lon: uses elementwise diffs.
      - If l2.time is 1D and lat/lon are 2D: attempts simple broadcasting
        (e.g., time per line); otherwise, falls back to all-True.

    This is a prototype: we keep things simple and robust rather than
    handling every possible exotic time layout.
    """
    shape = l2.lat.shape
    mask = np.ones(shape, dtype=bool)

    if l2.time is None or center_time is None:
        return mask

    if max_time_diff_sec is None or max_time_diff_sec <= 0:
        return mask

    time_arr = np.array(l2.time)

    # Case 1: same shape as lat/lon
    if time_arr.shape == shape:
        # We assume 'center_time' is a Python datetime; convert to seconds
        center_sec = center_time.timestamp()
        # Convert to seconds; if already numeric, this is a no-op assuming units are seconds
        # For prototype, assume numeric time is already seconds since some epoch.
        try:
            arr_sec = time_arr.astype(np.float64)
        except Exception:
            # If not numeric, bail out to all-True
            return mask

        diffs = np.abs(arr_sec - center_sec)
        mask &= diffs <= max_time_diff_sec
        return mask

    # Case 2: 1D time, 2D lat/lon (e.g., per-line time)
    if time_arr.ndim == 1 and l2.lat.ndim == 2:
        nlines = time_arr.shape[0]
        if l2.lat.shape[0] == nlines:
            center_sec = center_time.timestamp()
            try:
                arr_sec = time_arr.astype(np.float64)
            except Exception:
                return mask
            diffs_1d = np.abs(arr_sec - center_sec)
            # Broadcast along columns
            diffs_2d = np.repeat(diffs_1d[:, np.newaxis], l2.lat.shape[1], axis=1)
            mask &= diffs_2d <= max_time_diff_sec
            return mask

    # Any other shape mismatch: we skip time filtering for now
    return mask


def build_flag_mask(
    l2: L2Grid,
    bad_flag_mask: Optional[int],
) -> np.ndarray:
    """
    Build a boolean mask selecting pixels that are "good" according
    to a flag bitmask.

    Args:
        bad_flag_mask:
            Integer whose set bits indicate *bad* conditions to reject.
            Pixels with (flags & bad_flag_mask) != 0 will be excluded.
            If bad_flag_mask is None or 0, or l2.flags is None, returns all-True.

    Returns:
        Boolean array of same shape as lat/lon indicating "good" pixels.
    """
    shape = l2.lat.shape
    mask = np.ones(shape, dtype=bool)

    if l2.flags is None or not bad_flag_mask:
        return mask

    flags_arr = np.array(l2.flags)
    if flags_arr.shape != shape:
        # Shape mismatch; for prototype, don't try to be clever
        return mask

    bad = (flags_arr & np.uint32(bad_flag_mask)) != 0
    mask &= ~bad
    return mask


# --- combined helpers ------------------------------------------------------


def build_valid_pixel_mask(
    l2: L2Grid,
    seabass_rec: SeaBASSRecord,
    max_distance_km: Optional[float],
    max_time_diff_sec: Optional[float],
    bad_flag_mask: Optional[int],
) -> np.ndarray:
    """
    Build a combined boolean mask of valid pixels for a single
    SeaBASS record, using spatial, temporal, and flag criteria.

    Args:
        l2: L2Grid loaded from a single OB.DAAC L2 granule.
        seabass_rec: in situ measurement (lat, lon, time, depth etc.).
        max_distance_km: maximum great-circle distance in km.
        max_time_diff_sec: maximum allowed |Δt| in seconds.
        bad_flag_mask: bitmask of "bad" flags to reject.

    Returns:
        Boolean numpy array, same shape as l2.lat/lon.
    """
    spatial = build_spatial_mask(
        l2, seabass_rec.lat, seabass_rec.lon, max_distance_km
    )

    temporal = build_time_mask(
        l2, seabass_rec.time, max_time_diff_sec
    )

    flags = build_flag_mask(
        l2, bad_flag_mask
    )

    mask = spatial & temporal & flags
    return mask


def get_valid_pixel_indices(mask: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Convenience wrapper around np.where(mask) that documents intent.

    Returns:
        (row_indices, col_indices) for True entries in the mask.
    """
    return np.where(mask)


def find_nearest_valid_pixel(
    l2: L2Grid,
    seabass_rec: SeaBASSRecord,
    max_distance_km: Optional[float],
    max_time_diff_sec: Optional[float],
    bad_flag_mask: Optional[int],
) -> Optional[Tuple[int, int]]:
    """
    Find the (row, col) index of the nearest pixel that satisfies
    all filters (distance, time, flags). Returns None if no valid
    pixel remains.

    Note:
        This is a prototype implementation and is not optimized for
        performance on very large swaths. It computes distances only
        for pixels that pass the basic mask.
    """
    mask = build_valid_pixel_mask(
        l2=l2,
        seabass_rec=seabass_rec,
        max_distance_km=max_distance_km,
        max_time_diff_sec=max_time_diff_sec,
        bad_flag_mask=bad_flag_mask,
    )

    if not mask.any():
        return None

    # Indices of valid pixels
    rows, cols = np.where(mask)

    # Compute distances only for these
    lats = l2.lat[rows, cols]
    lons = l2.lon[rows, cols]

    dists = haversine_distance_km(
        seabass_rec.lat,
        seabass_rec.lon,
        lats,
        lons,
    )

    idx_min = int(np.argmin(dists))
    return int(rows[idx_min]), int(cols[idx_min])
