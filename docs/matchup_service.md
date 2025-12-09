### Matchup Service (MAKE Phase)

#### Goal

The Matchup Service performs the MAKE phase of the workflow by **appending satellite observations from L2 files to the original in-situ measurements in SeaBASS files**. The SeaBASS file remains the “spine” of the matchup product: each in-situ record is preserved, and satellite-derived statistics are added as new columns.

This design is **SeaBASS-centric**: the primary deliverable is an updated SeaBASS file that is immediately usable for validation analyses (scatter plots, Bland-Altman, etc.).

#### Inputs

- **L2 satellite NetCDF file(s)**  
  - Ocean color L2 products with lat/lon grids, radiometric or derived variables (e.g., Rrs), angles (e.g., solar zenith), and quality flags.
- **Original SeaBASS ASCII file(s)**  
  - Standard SeaBASS header and data table, including at minimum `lat`, `lon`, time (or date/time components), and in-situ variables of interest.
- **Matchup configuration parameters (via Harmony job params)**, including:
  - `box_size_pixels` (e.g., 5 → 5×5 pixel box)
  - `max_sza_deg` (maximum allowed solar zenith angle)
  - `min_valid_pixels` (minimum number of valid satellite pixels required for a matchup)
  - `satellite_variables` (list of L2 fields to aggregate and append)

#### High-Level Process

For each SeaBASS file:

1. **Parse SeaBASS header and data**
   - Read and preserve all header lines.
   - Parse `/fields` (and optionally `/units`) to construct a data table (pandas DataFrame).

2. **Open corresponding L2 satellite file(s)**
   - Load L2 NetCDF via xarray.
   - Access latitude/longitude grids, satellite variables, angles, and flags.

3. **Per-row matchup (SeaBASS-centric)**
   For each in-situ record (row) in the SeaBASS table:
   - Find the **nearest L2 pixel** to the SeaBASS latitude/longitude using great-circle distance.
   - Define a **pixel box** centered on that pixel with size `box_size_pixels × box_size_pixels`, clipped to L2 array bounds.
   - Extract satellite variables and auxiliary fields (e.g., solar zenith angle, flags) within that box.
   - Apply **matchup exclusion criteria**:
     - Discard pixels with solar zenith angle > `max_sza_deg` (if configured).
     - Apply L2 flag-based masking (e.g., invalid or suspect pixels).
     - Require at least `min_valid_pixels` valid pixels in the box.
   - If criteria are not met:
     - Mark the row as having no valid satellite matchup (NaN or fill values in satellite fields).
   - Otherwise:
     - Compute aggregated statistics for each requested satellite variable (e.g., mean, standard deviation, valid-pixel count).

4. **Append satellite statistics to SeaBASS**
   - For each SeaBASS row, append satellite-derived fields such as:
     - `sat_<var>_mean`
     - `sat_<var>_std`
     - `sat_<var>_nvalid`
   - The number of rows in the output SeaBASS file is identical to the original file; only columns are added.

5. **Update SeaBASS metadata and write output**
   - Preserve original header content.
   - Add or update header metadata describing:
     - L2 source file(s)
     - Box size used
     - Filtering thresholds (e.g., max SZA, min valid pixels)
     - List and meaning of added satellite fields
   - Write updated SeaBASS file (ASCII) with the new columns.

#### Output

- **Primary product:** Updated SeaBASS file(s) with satellite matchup fields appended as additional columns.
- **Characteristics:**
  - SeaBASS format preserved, including header.
  - Same number of rows as the original in-situ file(s).
  - Additional satellite-derived variables and statistics per row.

###  Matchup Service Implementation Details

The Matchup Service is implemented in two main components:

- **Matchup Engine (`matchup_engine.py`)**
  - Implements SeaBASS parsing (`parse_seabass`).
  - Implements L2 loading and geolocation helpers (`load_l2_dataset`, `find_nearest_pixel`, `extract_box_indices`).
  - Implements pixel filtering and aggregation (`apply_pixel_filters`, `aggregate_satellite_stats`).
  - Implements per-row matchup logic (`matchup_row_with_l2`).
  - Implements file-level orchestration:
    - Reads a SeaBASS file and one or more L2 files.
    - Loops over SeaBASS rows, computes satellite statistics, appends new columns.
    - Writes an updated SeaBASS file.

- **Harmony Adapter (`matchup_adapter.py`)**
  - Extends the Harmony Python service template (`harmony-service-example`).
  - Responsibilities:
    - Interpret Harmony job parameters (box size, filters, satellite variable list).
    - Download L2 NetCDF and SeaBASS inputs referenced in the job STAC.
    - Invoke the matchup engine (`append_satellite_to_seabass`) with the local file paths and configuration.
    - Stage the updated SeaBASS file to the configured output location.
    - Construct and return an output STAC Item that references the updated SeaBASS file as the primary product.

In this design, the engine is **Harmony-agnostic** and can be called from the command line or tests, while the adapter handles all Harmony-specific concerns (STAC, downloads, staging).

#### Inputs/Outputs summary

| Service / Phase       | Inputs                                        | Outputs                                         | Notes                                      |
|-----------------------|-----------------------------------------------|-------------------------------------------------|--------------------------------------------|
| Matchup Service (MAKE)| L2 satellite NetCDF file(s); SeaBASS file(s) | Updated SeaBASS file(s) with satellite columns | SeaBASS-centric: in-situ rows + sat stats. |


