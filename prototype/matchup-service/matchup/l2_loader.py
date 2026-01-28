# matchup/l2_loader.py

from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Sequence

import re
from datetime import datetime, timezone

import numpy as np
from netCDF4 import Dataset


@dataclass
class L2Grid:
    lat: np.ndarray
    lon: np.ndarray
    variables: Dict[str, np.ndarray]
    flags: Optional[np.ndarray]
    time: Optional[np.ndarray]
    # Fallback time when per-pixel/per-scanline time is not available:
    granule_datetime_utc: Optional[datetime] = None


def parse_granule_datetime_from_filename(path: str) -> Optional[datetime]:
    """
    Extract YYYYMMDDTHHMMSS from common OB.DAAC L2 filenames.
    Example: AQUA_MODIS.20240520T191501.L2.SST.nc -> 2024-05-20 19:15:01Z
    """
    m = re.search(r"\.(\d{8})T(\d{6})\.", path)
    if not m:
        return None
    dt = datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S")
    return dt.replace(tzinfo=timezone.utc)


def _get_group(ds: Dataset, name: str):
    """
    Try to get a named group, fall back to root if missing.
    """
    return ds.groups.get(name, ds)


def load_l2_file(
    path: str,
    variable_names: Iterable[str],
    flags_candidate_names: Optional[Sequence[str]] = None,
) -> L2Grid:
    """
    Load a modern OB.DAAC L2 NetCDF-4 file.

    Notes on time:
      - Some L2 files do not include per-pixel or per-scanline time arrays.
      - We therefore always parse a granule reference datetime from the filename
        (granule_datetime_utc) as a reliable fallback for matchup_min_dt_sec.
    """
    if flags_candidate_names is None:
        flags_candidate_names = ["l2_flags", "flags", "l2_flags_1"]

    ds = Dataset(path, "r")

    nav = _get_group(ds, "navigation_data")
    geo = _get_group(ds, "geophysical_data")

    lat = np.array(nav.variables["latitude"][:], copy=True)
    lon = np.array(nav.variables["longitude"][:], copy=True)

    # optional per-pixel or per-scanline time (rare/non-standard across sensors/products)
    time_array = None
    for cand in ("time", "utctime", "scan_time"):
        if cand in nav.variables:
            time_array = np.array(nav.variables[cand][:], copy=True)
            break
        if cand in geo.variables:
            time_array = np.array(geo.variables[cand][:], copy=True)
            break

    variables: Dict[str, np.ndarray] = {}
    for vname in variable_names:
        vname = vname.strip()
        if not vname:
            continue
        if vname not in geo.variables:
            continue  # prototype: silently skip
        variables[vname] = np.array(geo.variables[vname][:], copy=True)

    flags_array = None
    for cand in flags_candidate_names:
        if cand in geo.variables:
            flags_array = np.array(geo.variables[cand][:], copy=True).astype(np.uint32)
            break

    ds.close()

    granule_dt = parse_granule_datetime_from_filename(path)

    return L2Grid(
        lat=lat,
        lon=lon,
        variables=variables,
        flags=flags_array,
        time=time_array,
        granule_datetime_utc=granule_dt,
    )


def normalize_variable_list(
    requested_vars: Iterable[str],
    available_vars: Iterable[str],
) -> list[str]:
    requested_set = {v.strip() for v in requested_vars if v.strip()}
    available_set = set(available_vars)
    return sorted(requested_set & available_set)
