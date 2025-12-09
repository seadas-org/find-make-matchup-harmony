

### Technical Notes

* **Inputs**

  * **Primary:** L2 satellite NetCDF file(s) containing lat, lon, time, satellite variables (e.g., Rrs, reflectances), angles, and quality flags.
  * **Secondary:** Original SeaBASS ASCII file(s) with header block and data table, including at minimum `lat`, `lon`, and `time` (plus in-situ variables).

* **Core Logic**

  * For each SeaBASS record:

    * Find the nearest L2 pixel index `(i0, j0)` based on great-circle distance between SeaBASS `(lat, lon)` and L2 geolocation grids.
    * Define a pixel box centered on `(i0, j0)` with configurable **Box Size** (e.g., `5` → 5×5 pixels).
    * Extract the satellite variables and auxiliary fields (e.g., solar zenith angle, flags) within this box.
    * Apply **filtering criteria**, for example:

      * Max solar zenith angle,
      * Flag-based exclusion (invalid/masked pixels),
      * Minimum number of valid pixels in the box.
    * If criteria are not met, output fill/NaN values for that SeaBASS row’s satellite fields.
    * Otherwise, compute aggregated statistics (e.g., mean, standard deviation, valid count) for each requested satellite variable.

* **Output**

  * Preserve the original SeaBASS header and data rows.
  * Append new satellite-derived columns to each SeaBASS row (e.g., `sat_<var>_mean`, `sat_<var>_std`, `sat_<var>_nvalid`).
  * Add/update header metadata to document:

    * L2 input file(s),
    * box size,
    * filter thresholds,
    * list and meaning of appended satellite fields.

* **Harmony Integration**

  * Implement as a Harmony service using `harmony-service-example` as a base.
  * Harmony adapter:

    * Accepts L2 NetCDF and SeaBASS files as inputs plus configuration parameters (box size, filters, variable list).
    * Downloads inputs, runs the matchup logic, and stages the updated SeaBASS file.
    * Returns a STAC item referencing the updated SeaBASS file as the primary product.
