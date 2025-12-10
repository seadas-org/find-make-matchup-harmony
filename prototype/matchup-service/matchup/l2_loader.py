# matchup/l2_loader.py

from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Sequence

import numpy as np
from netCDF4 import Dataset


@dataclass
class L2Grid:
    lat: np.ndarray
    lon: np.ndarray
    variables: Dict[str, np.ndarray]
    flags: Optional[np.ndarray]
    time: Optional[np.ndarray]


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
    """
    if flags_candidate_names is None:
        flags_candidate_names = ["l2_flags", "flags", "l2_flags_1"]

    ds = Dataset(path, "r")

    nav = _get_group(ds, "navigation_data")
    geo = _get_group(ds, "geophysical_data")

    lat = np.array(nav.variables["latitude"][:], copy=True)
    lon = np.array(nav.variables["longitude"][:], copy=True)

    # optional time
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
            flags_array = (
                np.array(geo.variables[cand][:], copy=True).astype(np.uint32)
            )
            break

    ds.close()

    return L2Grid(
        lat=lat,
        lon=lon,
        variables=variables,
        flags=flags_array,
        time=time_array,
    )


def normalize_variable_list(
    requested_vars: Iterable[str],
    available_vars: Iterable[str],
) -> list[str]:
    requested_set = {v.strip() for v in requested_vars if v.strip()}
    available_set = set(available_vars)
    return sorted(requested_set & available_set)
