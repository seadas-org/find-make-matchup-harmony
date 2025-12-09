
##  Technical plan

Implementation sketch for the core engine (independent of Harmony):

### Inputs

* **L2 file(s)**: NetCDF, with:

  * `latitude(y, x)`, `longitude(y, x)`, `time(y, x)` (or granule-level time),
  * satellite variables (e.g., Rrs, reflectances, etc.),
  * optional angles and flags.

* **SeaBASS file(s)**: ASCII, with:

  * header section (`/begin_header` …),
  * data table with `lat`, `lon`, `time` (and other in-situ variables).

* **Config parameters**:

  * `box_size_pixels` (odd integer: 3, 5, 7, …),
  * `max_sza` (deg),
  * `min_valid_sat_pixels`,
  * `satellite_variables` list,
  * any required flags / mask rules.

### Steps

1. **Parse SeaBASS file**

   * Read header (preserve as text).
   * Read data table into a DataFrame (SeaBASS columns → DataFrame columns).
   * Identify columns for lat, lon, time.

2. **Open L2 NetCDF**

   * Use xarray or netCDF4.
   * Extract lat/lon grids and satellite variables.
   * If needed, compute pixel indices for nearest neighbor:

     * For each SeaBASS point, find `(i, j)` such that distance(lat_s, lon_s, lat[i,j], lon[i,j]) is minimal.

3. **For each SeaBASS row**

   * Determine nearest pixel index `(i0, j0)`.
   * Define box:

     * half = (box_size_pixels - 1) // 2
       → `i_min = i0 - half`, `i_max = i0 + half`, similarly for `j`.
     * Clip to L2 bounds.
   * Extract subarray for each satellite variable and any auxiliary variables (e.g., SZA).
   * Apply **filtering**:

     * Mask pixels with bad flags.
     * Mask pixels with solar zenith angle > `max_sza`.
   * Count valid pixels.

     * If `count_valid < min_valid_sat_pixels`, mark SeaBASS row as “no matchup” for that variable (e.g., fill value / NaN).
   * Otherwise compute:

     * mean, median, std, valid pixel count, etc.
   * Store these aggregated values in new columns for that SeaBASS row:

     * e.g., `sat_Rrs_443_mean`, `sat_Rrs_443_std`, `sat_Rrs_443_nvalid`.

4. **Update SeaBASS header**

   * Add/extend `/:` metadata lines describing:

     * L2 file(s) used,
     * box size,
     * filter thresholds,
     * list of appended fields and their meaning/units.

5. **Write updated SeaBASS file**

   * Re-write header.
   * Write data lines with **all original columns + appended satellite columns**.
   * This updated file becomes the **output product** of the service.

---
