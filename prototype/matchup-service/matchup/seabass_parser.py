# matchup/seabass_parser.py

from dataclasses import dataclass
from typing import Dict, Any, List
import datetime


@dataclass
class SeaBASSRecord:
    lat: float
    lon: float
    time: datetime.datetime
    depth: float | None
    variables: Dict[str, Any]


@dataclass
class SeaBASSData:
    header: Dict[str, Any]
    records: List[SeaBASSRecord]


def _parse_datetime(date_str: str, time_str: str | None = None) -> datetime.datetime:
    date_str = date_str.strip()

    # ISO-like with 'T'
    if "T" in date_str and time_str is None:
        try:
            return datetime.datetime.fromisoformat(date_str)
        except Exception:
            pass

    # If only one string, try split
    if time_str is None:
        parts = date_str.split()
        if len(parts) == 2:
            date_str, time_str = parts[0], parts[1]

    if time_str is None:
        raise ValueError(f"Unrecognized SeaBASS datetime format: '{date_str}'")

    time_str = time_str.strip()

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.datetime.strptime(f"{date_str} {time_str}", fmt)
        except Exception:
            continue

    raise ValueError(f"Cannot parse SeaBASS date/time: '{date_str} {time_str}'")


def parse_seabass_file(path: str) -> SeaBASSData:
    """
    Simplified SeaBASS parser for the prototype.
    """
    header: Dict[str, Any] = {}
    header_lines: list[str] = []
    data_lines: list[str] = []

    with open(path, "r") as f:
        lines = [line.rstrip("\n\r") for line in f]

    in_header = True
    for line in lines:
        stripped = line.strip()
        if in_header and stripped.startswith("/"):
            header_lines.append(stripped)
        else:
            in_header = False
            if stripped != "":
                data_lines.append(stripped)

    # --- header ---
    for h in header_lines:
        lower = h.lower()
        if lower.startswith("/fields="):
            header["fields"] = [v.strip() for v in h.split("=", 1)[1].split(",")]
        elif lower.startswith("/units="):
            header["units"] = [v.strip() for v in h.split("=", 1)[1].split(",")]
        elif lower.startswith("/missing="):
            header["missing"] = h.split("=", 1)[1].strip()
        elif lower.startswith("/delimiter="):
            header["delimiter"] = h.split("=", 1)[1].strip()

    if "fields" not in header:
        raise ValueError("SeaBASS header missing /fields= definition")

    delimiter_token = header.get("delimiter", "tab").lower()
    if delimiter_token in ("tab", "\\t"):
        delimiter = "\t"
    else:
        delimiter = delimiter_token  # assume literal, e.g., ','

    missing_value = header.get("missing", "NaN")
    fields = header["fields"]

    # --- data ---
    records: list[SeaBASSRecord] = []

    for line in data_lines:
        parts = line.split(delimiter)
        if len(parts) != len(fields):
            continue

        row = dict(zip(fields, parts))

        # lat / lon
        try:
            lat = float(row.get("lat"))
            lon = float(row.get("lon"))
        except (TypeError, ValueError):
            continue

        # time
        if "date" in row and "time" in row:
            ts = _parse_datetime(row["date"], row["time"])
        elif "datetime" in row:
            ts = _parse_datetime(row["datetime"])
        else:
            raise ValueError("SeaBASS row missing date/time or datetime field")

        # depth
        depth_val = None
        for depth_key in ("depth", "z"):
            if depth_key in row:
                try:
                    depth_val = float(row[depth_key])
                except (TypeError, ValueError):
                    depth_val = None
                break

        # variables
        variables: Dict[str, Any] = {}
        skip = {"lat", "lon", "date", "time", "datetime", "depth", "z"}

        for k, v in row.items():
            if k.lower() in skip:
                continue
            if v == missing_value:
                variables[k] = None
            else:
                try:
                    variables[k] = float(v)
                except ValueError:
                    variables[k] = v

        records.append(
            SeaBASSRecord(
                lat=lat,
                lon=lon,
                time=ts,
                depth=depth_val,
                variables=variables,
            )
        )

    header["raw_header_lines"] = header_lines

    return SeaBASSData(header=header, records=records)
