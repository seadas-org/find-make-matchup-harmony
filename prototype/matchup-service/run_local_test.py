from matchup.orchestrator import append_satellite_to_seabass

params = {
    "variables": ["chlor_a"],
    "max_distance_km": 5.0,
    "max_time_diff_sec": 3 * 3600,
    "bad_flag_mask": None,
    "mode": "window",
}

append_satellite_to_seabass(
    seabass_path="input.sb",
    l2_path="input.nc",
    params=params,
    output_path="matchup.sb",
)
