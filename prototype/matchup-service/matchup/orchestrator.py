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

def _delimiter_char(delim_token: str | None) -> str:
    """
    SeaBASS header often uses tokens like 'comma' or 'tab'. Data lines must use actual characters.
    """
    if not delim_token:
        return ","  # safe default

    t = delim_token.strip().lower()

    if t in ("comma", ","):
        return ","
    if t in ("tab", r"\t", "\\t"):
        return "\t"
    if t in ("space", "spaces", "whitespace", " "):
        return " "

    # If user put an actual delimiter char in header, accept it
    if len(t) == 1:
        return t

    # fallback
    return ","


def _format_value(value: Any, missing_token: str, float_precision: int = 10) -> str:
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


def _format_original_field(field: str, rec, header: Dict[str, Any]) -> str:
    """
    Format original SeaBASS fields with SeaBASS-friendly conventions:
      - date: yyyymmdd
      - time: HH:MM:SS
      - datetime (if present): ISO-like without timezone suffix
      - lat/lon: decimal degrees (reasonable precision)
    """
    missing = str(header.get("missing", "NaN"))
    lf = field.lower()

    if lf == "date":
        return rec.time.strftime("%Y%m%d")
    if lf == "time":
        return rec.time.strftime("%H:%M:%S")
    if lf == "datetime":
        return rec.time.strftime("%Y-%m-%dT%H:%M:%S")
    if lf == "lat":
        return f"{rec.lat:.6f}".rstrip("0").rstrip(".")
    if lf == "lon":
        return f"{rec.lon:.6f}".rstrip("0").rstrip(".")
    if lf in ("depth", "z"):
        return _format_value(rec.depth, missing)

    v = rec.variables.get(field)
    return _format_value(v, missing)


def _format_record_row(
    rec,
    sat_cols: Dict[str, Any],
    original_fields: Sequence[str],
    new_fields: Sequence[str],
    header: Dict[str, Any],
) -> List[str]:
    """
    Construct full output row values list (original fields + appended matchup fields).
    """
    missing = str(header.get("missing", "NaN"))

    values: List[str] = []

    # 1) Original fields in the original order
    for field in original_fields:
        values.append(_format_original_field(field, rec, header))

    # 2) New appended fields in the order new_fields[len(original_fields):]
    for field in new_fields[len(original_fields):]:
        values.append(_format_value(sat_cols.get(field), missing))

    return values

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

    # IMPORTANT: header stores token like "comma" but data needs actual char ","
    delim_char = _delimiter_char(seabass.header.get("delimiter"))

    # Rewrite header lines with updated /fields= and /units=
    raw_header_lines = seabass.header.get("raw_header_lines", [])

    written_fields = False
    written_units = False
    header_out: List[str] = []

    for line in raw_header_lines:
        lower = line.strip().lower()
        if lower.startswith("/fields=") or lower.startswith("fields="):
            header_out.append("/fields=" + ",".join(new_fields))
            written_fields = True
        elif lower.startswith("/units=") or lower.startswith("units="):
            header_out.append("/units=" + ",".join(new_units))
            written_units = True
        else:
            header_out.append(line)

    if not written_fields:
        header_out.append("/fields=" + ",".join(new_fields))
    if not written_units:
        header_out.append("/units=" + ",".join(new_units))

    # Ensure output directory exists
    import os
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # Write output file
    with open(output_path, "w", encoding="utf-8", newline="\n") as out:
        # Header
        for line in header_out:
            out.write(line.rstrip("\n") + "\n")

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

            # Use correct delimiter CHARACTER here ("," not "comma")
            out.write(delim_char.join(row_vals) + "\n")
    return output_path
