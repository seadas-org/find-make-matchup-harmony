# matchup/orchestrator.py

"""
File-level orchestration (Subtask 6).

This module wires together:
  - SeaBASS parser (seabass_parser.py)
  - L2 loader (l2_loader.py)
  - Filters & per-row matchup (filters.py, match_row.py)

Main entry point:

    append_satellite_to_seabass(
        seabass_path,
        l2_path,
        params,
        output_path
    )

It reads a SeaBASS file and an OB.DAAC L2 file, performs matchups for
each SeaBASS record, and writes an augmented SeaBASS-style file with
additional satellite-derived columns.
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

from .seabass_parser import (
    parse_seabass_file,
    SeaBASSData,
    SeaBASSRecord,
)
from .l2_loader import (
    load_l2_file,
    L2Grid,
)
from .match_row import match_record_to_l2


def _get_delimiter_from_header(header: Dict[str, Any]) -> str:
    token = header.get("delimiter", "tab").lower()
    if token in ("tab", "\\t"):
        return "\t"
    return token  # e.g., ","


def _build_new_field_names(
    original_fields: Sequence[str],
    variable_names: Sequence[str],
) -> List[str]:
    """
    Build the full list of output field names:
      original SeaBASS fields
      + matchup_min_distance_km
      + matchup_min_dt_sec
      + sat_<var>_mean/median/std/n for each var
    """
    new_fields = list(original_fields)

    # Generic matchup metrics
    metric_fields = ["matchup_min_distance_km", "matchup_min_dt_sec"]
    new_fields.extend(metric_fields)

    # Satellite statistics per variable
    for var in variable_names:
        var = var.strip()
        if not var:
            continue
        prefix = f"sat_{var}"
        new_fields.append(f"{prefix}_mean")
        new_fields.append(f"{prefix}_median")
        new_fields.append(f"{prefix}_std")
        new_fields.append(f"{prefix}_n")

    return new_fields


def _build_new_units(
    header: Dict[str, Any],
    original_fields: Sequence[str],
    new_fields: Sequence[str],
    variable_names: Sequence[str],
) -> List[str]:
    """
    Build the /units= list for the augmented file.

    For prototype purposes:
      - Existing fields keep their original units (if present)
      - matchup_min_distance_km -> "km"
      - matchup_min_dt_sec     -> "s"
      - sat_*_mean/median/std  -> "unknown"
      - sat_*_n                -> "1"
    """
    orig_units = header.get("units")

    if not orig_units or len(orig_units) != len(original_fields):
        # Fallback: create generic units for original fields
        orig_units = ["unknown"] * len(original_fields)

    new_units = list(orig_units)

    # We know how many metric + sat fields we are appending:
    extra_units: List[str] = []

    # 1) Generic metrics
    extra_units.append("km")  # matchup_min_distance_km
    extra_units.append("s")   # matchup_min_dt_sec

    # 2) Per-variable stats
    for var in variable_names:
        var = var.strip()
        if not var:
            continue
        # For now, stats units are unknown, counts are dimensionless
        extra_units.append("unknown")  # sat_var_mean
        extra_units.append("unknown")  # sat_var_median
        extra_units.append("unknown")  # sat_var_std
        extra_units.append("1")        # sat_var_n

    new_units.extend(extra_units)
    return new_units


def _format_value(
    value,
    missing_token: str,
    float_precision: int = 6,
) -> str:
    """
    Convert Python values to strings suitable for SeaBASS output.
    """
    if value is None:
        return missing_token

    if isinstance(value, float):
        if value != value:  # NaN
            return missing_token
        return f"{value:.{float_precision}g}"

    return str(value)


def _format_record_row(
    rec: SeaBASSRecord,
    sat_cols: Dict[str, Any],
    original_fields: Sequence[str],
    new_fields: Sequence[str],
    header: Dict[str, Any],
) -> List[str]:
    """
    Construct a full output row string list for one SeaBASSRecord,
    including the original fields (reconstructed) and new satellite
    columns (from sat_cols).
    """
    missing = header.get("missing", "NaN")

    # Precompute date/time strings
    date_str = rec.time.strftime("%Y-%m-%d")
    time_str = rec.time.strftime("%H:%M:%S")
    datetime_str = rec.time.strftime("%Y-%m-%dT%H:%M:%S")

    # 1) Original fields, in original order
    values: List[str] = []
    lower_fields = [f.lower() for f in original_fields]

    for field, lf in zip(original_fields, lower_fields):
        if lf == "lat":
            val = _format_value(rec.lat, missing)
        elif lf == "lon":
            val = _format_value(rec.lon, missing)
        elif lf == "date":
            val = date_str
        elif lf == "time":
            val = time_str
        elif lf == "datetime":
            val = datetime_str
        elif lf in ("depth", "z"):
            val = _format_value(rec.depth, missing)
        else:
            v = rec.variables.get(field)
            val = _format_value(v, missing)
        values.append(val)

    # 2) New fields (metric + sat stats) in the order they were built
    #    i.e., new_fields[len(original_fields):]
    for field in new_fields[len(original_fields):]:
        v = sat_cols.get(field)
        val = _format_value(v, missing)
        values.append(val)

    return values


def append_satellite_to_seabass(
    seabass_path: str,
    l2_path: str,
    params: Dict[str, Any],
    output_path: str,
) -> str:
    """
    Main orchestration entry point.

    Args:
        seabass_path: Input SeaBASS file.
        l2_path: OB.DAAC L2 granule.
        params: Dict of configuration options, e.g.:
            {
                "variables": ["chlor_a", "Rrs_443"],
                "max_distance_km": 5.0,
                "max_time_diff_sec": 3 * 3600,
                "bad_flag_mask": <int> or None,
                "mode": "window" or "nearest",
            }
        output_path: Where to write the augmented SeaBASS-style file.

    Returns:
        The output_path (for convenience).
    """
    seabass: SeaBASSData = parse_seabass_file(seabass_path)

    # Parameters with defaults
    variable_names = params.get("variables", [])
    max_distance_km = params.get("max_distance_km", 5.0)
    max_time_diff_sec = params.get("max_time_diff_sec", 3 * 3600)
    bad_flag_mask = params.get("bad_flag_mask")  # can be None
    mode = params.get("mode", "window")

    # Load L2 once
    l2: L2Grid = load_l2_file(
        path=l2_path,
        variable_names=variable_names,
    )

    original_fields = seabass.header["fields"]
    new_fields = _build_new_field_names(original_fields, variable_names)
    new_units = _build_new_units(
        header=seabass.header,
        original_fields=original_fields,
        new_fields=new_fields,
        variable_names=variable_names,
    )

    delimiter = _get_delimiter_from_header(seabass.header)
    missing = seabass.header.get("missing", "NaN")

    # Rewrite header lines with updated /fields= and /units=
    raw_header_lines = seabass.header.get("raw_header_lines", [])

    written_fields = False
    written_units = False
    header_out: List[str] = []

    for line in raw_header_lines:
        lower = line.lower()
        if lower.startswith("/fields="):
            header_out.append("/fields=" + ",".join(new_fields))
            written_fields = True
        elif lower.startswith("/units="):
            header_out.append("/units=" + ",".join(new_units))
            written_units = True
        else:
            header_out.append(line)

    # If, for some reason, original header lacked /fields or /units,
    # append them at the end.
    if not written_fields:
        header_out.append("/fields=" + ",".join(new_fields))
    if not written_units:
        header_out.append("/units=" + ",".join(new_units))

    # Write output file
    with open(output_path, "w") as out:
        # Header
        for line in header_out:
            out.write(line + "\n")

        # Data rows
        for rec in seabass.records:
            sat_cols = match_record_to_l2(
                seabass_rec=rec,
                l2=l2,
                variable_names=variable_names,
                max_distance_km=max_distance_km,
                max_time_diff_sec=max_time_diff_sec,
                bad_flag_mask=bad_flag_mask,
                mode=mode,
            )

            row_vals = _format_record_row(
                rec=rec,
                sat_cols=sat_cols,
                original_fields=original_fields,
                new_fields=new_fields,
                header=seabass.header,
            )

            out.write(delimiter.join(row_vals) + "\n")

    return output_path
