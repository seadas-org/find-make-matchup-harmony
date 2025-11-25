omponent Mapping: OB.DAAC Logic → Harmony Services

This document maps the major steps of the existing “Find and Make Matchup”
workflow (e.g., `fd_matchup.py` and SeaDAS integration) to proposed Harmony
components and services.

This table will evolve as the analysis progresses.

| Logical Step (OB.DAAC)        | Current Tool / Logic              | Harmony Equivalent / Replacement                   | Notes |
|-------------------------------|-----------------------------------|----------------------------------------------------|-------|
| Discover primary granules     | CMR queries in `fd_matchup.py`   | Harmony Search / CMR Search                        |       |
| Discover secondary granules   | Time-window CMR queries          | Harmony Search with temporal constraints           |       |
| Spatial subsetting            | Local subset logic                | HOSS spatial subsetting (region/point/track)       |       |
| Temporal subsetting           | Local time filtering              | HOSS temporal subsetting                           |       |
| Variable subsetting           | Local variable selection          | HOSS variable selection                            |       |
| Matchup computation           | `fd_matchup.py` / local Python    | **New custom Harmony matchup container**           |       |
| Interpolation / aggregation   | Local Python / compiled code      | Implemented inside the matchup container           |       |
| Output: CSV                   | `fd_matchup.py` CSV export        | Inside container or via TRT CSV service (optional) |       |
| Output: NetCDF                | Local tools (if applicable)       | Implemented inside the container or future service |       |
| STAC metadata                 | Not currently produced            | Harmony output STAC                                |       |

As you learn more details about `fd_matchup.py` and related tools, expand the
"Current Tool / Logic" and "Notes" columns, and add new rows as needed.

