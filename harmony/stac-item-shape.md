# Adapter STAC Item Shape

The current adapter consumes one STAC `Feature` per matchup job item. That
feature must contain both the SeaBASS input and the paired L2 granule.

## Required Top-Level Fields

- `type`: must be `Feature`
- `stac_version`: tested with `1.0.0`
- `id`: unique identifier for the paired input item
- `assets`: object containing both input files

## Required Assets

- `assets.seabass`
  - `href`: downloadable SeaBASS file
  - accepted by explicit key, or by fallback `.sb` / `.txt` suffix or
    `media_type` containing `seabass`
- `assets.l2`
  - `href`: downloadable NetCDF L2 granule
  - accepted by explicit key, or by fallback `.nc` / `.nc4` suffix or
    `media_type` containing `netcdf`

## Recommended Asset Fields

- `title`
- `media_type`
- `roles`

## Parameter Mapping Used With This Item

- variable names: `sources[].variables[].name`
- `max_distance_km`: `extraArgs.max_distance_km`
- `max_time_diff_sec`: `extraArgs.max_time_diff_sec`
- `bad_flag_mask`: `extraArgs.bad_flag_mask`
- `mode`: `extraArgs.mode`

## Output Shape

The adapter clears the incoming assets and returns a new STAC item with:

- `assets.data.href`: staged output URL
- `assets.data.media_type`: request `format.mime` or default `text/plain`
- `assets.data.roles`: `["data"]`
