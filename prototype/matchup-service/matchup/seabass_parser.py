from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import re


# -----------------------------
# Data structures
# -----------------------------

@dataclass(frozen=True)
class SeaBASSRecord:
    lat: float
    lon: float
    time: datetime
    depth: Optional[float]
    variables: Dict[str, Any]   # includes all other fields (strings or floats)


@dataclass
class SeaBASSData:
    header: Dict[str, Any]
    records: List[SeaBASSRecord]


# -----------------------------
# Helpers
# -----------------------------

def _strip_bom(s: str) -> str:
    # Rare but happens with some files
    return s.lstrip("\ufeff")


def _parse_kv_line(line: str) -> Optional[Tuple[str, str]]:
    """
    Parse a SeaBASS header kv line.
    Accepts:
      /fields=a,b,c
      fields=a,b,c
      /missing=-999
    Ignores comments.
    Returns: (key_lower, value_str) or None
    """
    s = line.strip()
    if not s or s.startswith("!"):
        return None

    # Remove one leading slash if present
    if s.startswith("/"):
        s = s[1:]

    if "=" not in s:
        return None

    key, val = s.split("=", 1)
    return key.strip().lower(), val.strip()


def _normalize_delimiter(token: Optional[str]) -> Optional[str]:
    if not token:
        return None
    t = token.strip().lower()
    if t in ("tab", r"\t", "\\t"):
        return "\t"
    if t in ("comma", ","):
        return ","
    if t in ("space", "spaces", "whitespace"):
        return " "  # special handling later
    # Some SeaBASS files literally put "tab" or "," etc.
    if t == "t":
        return "\t"
    return t  # might be unusual, but we try


def _detect_delimiter(sample_line: str) -> str:
    """
    Best-effort delimiter detection for the data section.
    Preference: tab, then comma, else whitespace.
    """
    if "\t" in sample_line:
        return "\t"
    if "," in sample_line:
        return ","
    return " "


def _is_missing(value_str: str, missing_token: Optional[str]) -> bool:
    s = value_str.strip()
    if s == "":
        return True
    if s.lower() == "nan":
        return True
    if missing_token is None:
        return False
    return s == str(missing_token).strip()


_float_re = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$")


def _to_number_or_string(value_str: str, missing_token: Optional[str]) -> Optional[Any]:
    """
    Convert to float if numeric, else keep string. Return None if missing.
    """
    if _is_missing(value_str, missing_token):
        return None
    s = value_str.strip()
    if _float_re.match(s):
        try:
            return float(s)
        except Exception:
            return s
    return s


def _parse_date(date_str: str) -> Optional[datetime]:
    """
    Supports:
      yyyymmdd
      yyyy-mm-dd
    Returns a date with tzinfo=UTC and time=00:00:00 (caller adds time).
    """
    s = date_str.strip()
    if not s:
        return None

    # yyyymmdd
    if re.fullmatch(r"\d{8}", s):
        y = int(s[0:4])
        m = int(s[4:6])
        d = int(s[6:8])
        return datetime(y, m, d, tzinfo=timezone.utc)

    # yyyy-mm-dd
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        y, m, d = s.split("-")
        return datetime(int(y), int(m), int(d), tzinfo=timezone.utc)

    return None


def _parse_time(time_str: str) -> Optional[Tuple[int, int, int]]:
    """
    Supports:
      hh:mm:ss
      hhmmss
      hh:mm
      hhmm
    Returns (H, M, S)
    """
    s = time_str.strip()
    if not s:
        return None

    if re.fullmatch(r"\d{2}:\d{2}:\d{2}", s):
        h, m, sec = s.split(":")
        return int(h), int(m), int(sec)

    if re.fullmatch(r"\d{6}", s):
        return int(s[0:2]), int(s[2:4]), int(s[4:6])

    if re.fullmatch(r"\d{2}:\d{2}", s):
        h, m = s.split(":")
        return int(h), int(m), 0

    if re.fullmatch(r"\d{4}", s):
        return int(s[0:2]), int(s[2:4]), 0

    return None


def _parse_datetime(dt_str: str) -> Optional[datetime]:
    """
    Handles a few common datetime formats:
      YYYY-MM-DDTHH:MM:SSZ
      YYYY-MM-DD HH:MM:SS
      YYYY-MM-DDTHH:MM:SS (assume UTC)
    """
    s = dt_str.strip()
    if not s:
        return None

    # Normalize trailing Z
    if s.endswith("Z"):
        s2 = s[:-1]
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(s2, fmt).replace(tzinfo=timezone.utc)
            except Exception:
                pass

    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except Exception:
            pass

    return None


def _combine_date_time(date_part: Optional[datetime], time_part: Optional[Tuple[int, int, int]]) -> Optional[datetime]:
    if date_part is None or time_part is None:
        return None
    h, m, s = time_part
    return datetime(date_part.year, date_part.month, date_part.day, h, m, s, tzinfo=timezone.utc)


# -----------------------------
# Main parser
# -----------------------------

def parse_seabass_file(path: str) -> SeaBASSData:
    """
    Parse a SeaBASS .sb file into header + list of records.

    Requirements for records:
      - lat and lon must be present in /fields
      - datetime must be derivable from:
          * a 'datetime' field, OR
          * a 'date' + 'time' field, OR
          * (fallback) date/time from header keys like start_date/start_time (rare)

    Everything else is preserved in SeaBASSRecord.variables.
    """
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        raw_lines = [_strip_bom(ln.rstrip("\n")) for ln in f]

    header: Dict[str, Any] = {"raw_header_lines": []}
    data_lines: List[str] = []

    in_header = False
    header_done = False

    # Collect all kv pairs too (useful later)
    header_kv: Dict[str, str] = {}

    for line in raw_lines:
        s = line.strip()

        if not in_header:
            if s.lower() == "/begin_header":
                in_header = True
                header["raw_header_lines"].append(line)
            continue

        if in_header and not header_done:
            header["raw_header_lines"].append(line)

            if s.lower() == "/end_header":
                header_done = True
                continue

            kv = _parse_kv_line(line)
            if kv is None:
                continue
            key, val = kv
            header_kv[key] = val

            if key == "fields":
                header["fields"] = [v.strip() for v in val.split(",") if v.strip()]
            elif key == "units":
                header["units"] = [v.strip() for v in val.split(",")]
            elif key == "missing":
                header["missing"] = val
            elif key == "delimiter":
                header["delimiter"] = val.lower()

            continue

        # After header
        if header_done:
            if not s or s.startswith("!"):
                continue
            data_lines.append(line)

    header["kv"] = header_kv

    fields: List[str] = header.get("fields") or []
    if not fields:
        raise ValueError("SeaBASS header missing /fields= definition")

    # Determine delimiter
    delim_token = header.get("delimiter")
    delimiter = _normalize_delimiter(delim_token)

    if delimiter is None:
        # detect from first non-empty data line
        if not data_lines:
            raise ValueError("SeaBASS file has no data lines after /end_header")
        delimiter = _detect_delimiter(data_lines[0])

    missing_token = header.get("missing")

    # Build field index map (case-insensitive)
    fields_lc = [f.strip() for f in fields]
    idx: Dict[str, int] = {name.lower(): i for i, name in enumerate(fields_lc)}

    def get_field(row: List[str], key: str) -> Optional[str]:
        i = idx.get(key.lower())
        if i is None or i >= len(row):
            return None
        return row[i]

    # Identify how to parse time for each row
    has_datetime = "datetime" in idx
    has_date = "date" in idx
    has_time = "time" in idx

    # Fallback header date/time (rare but some forms exist)
    header_date = _parse_date(header_kv.get("start_date", "")) or _parse_date(header_kv.get("date", ""))
    header_time = _parse_time(header_kv.get("start_time", "")) or _parse_time(header_kv.get("time", ""))

    records: List[SeaBASSRecord] = []

    # Prepare data splitting
    for line in data_lines:
        if delimiter == " ":
            parts = line.split()  # any whitespace
        else:
            parts = [p.strip() for p in line.split(delimiter)]

        if len(parts) < 2:
            continue

        # lat/lon are required for matchup
        lat_s = get_field(parts, "lat")
        lon_s = get_field(parts, "lon")
        if lat_s is None or lon_s is None:
            # Some files use "latitude"/"longitude" but your example uses lat/lon.
            lat_s = lat_s or get_field(parts, "latitude")
            lon_s = lon_s or get_field(parts, "longitude")

        if lat_s is None or lon_s is None:
            # Skip rows without coordinates
            continue

        lat_v = _to_number_or_string(lat_s, missing_token)
        lon_v = _to_number_or_string(lon_s, missing_token)
        if lat_v is None or lon_v is None:
            continue
        try:
            lat = float(lat_v)
            lon = float(lon_v)
        except Exception:
            continue

        # Depth (optional)
        depth = None
        depth_s = get_field(parts, "depth") or get_field(parts, "z")
        if depth_s is not None:
            d = _to_number_or_string(depth_s, missing_token)
            if isinstance(d, (int, float)):
                depth = float(d)

        # Datetime
        dt: Optional[datetime] = None
        if has_datetime:
            dt = _parse_datetime(get_field(parts, "datetime") or "")
        if dt is None and has_date and has_time:
            d0 = _parse_date(get_field(parts, "date") or "")
            t0 = _parse_time(get_field(parts, "time") or "")
            dt = _combine_date_time(d0, t0)
        if dt is None and header_date and header_time:
            dt = _combine_date_time(header_date, header_time)

        if dt is None:
            # Skip rows we cannot time-locate
            continue

        # Variables: keep everything else (including strings like station/bottle)
        variables: Dict[str, Any] = {}
        for name, i in idx.items():
            # Use original field name case from header for output keys
            field_name = fields_lc[i]
            if i >= len(parts):
                variables[field_name] = None
                continue
            raw = parts[i]
            variables[field_name] = _to_number_or_string(raw, missing_token)

        # Ensure we don’t duplicate core attributes needlessly
        # (But leaving them in variables is okay; engine uses rec.lat/lon/time anyway)
        records.append(
            SeaBASSRecord(
                lat=lat,
                lon=lon,
                time=dt,
                depth=depth,
                variables=variables,
            )
        )

    return SeaBASSData(header=header, records=records)
