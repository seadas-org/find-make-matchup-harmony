#!/usr/bin/env python3
"""
Simple local driver for the matchup engine.

Usage example (from terminal or PyCharm parameters):

    python run_local_matchup.py \
        --seabass path/to/input.sb \
        --l2 path/to/L2_file.nc \
        --out path/to/output_matchup.sb \
        --vars chlor_a,Rrs_443 \
        --max-distance-km 5 \
        --max-time-sec 10800 \
        --mode window
"""

import argparse
from typing import List

from matchup.orchestrator import append_satellite_to_seabass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run local satellite matchup using the matchup engine."
    )

    parser.add_argument(
        "--seabass",
        required=True,
        help="Path to input SeaBASS file (.sb).",
    )
    parser.add_argument(
        "--l2",
        required=True,
        help="Path to input OB.DAAC L2 file (NetCDF-4).",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Path to output augmented SeaBASS file.",
    )

    parser.add_argument(
        "--vars",
        default="",
        help="Comma-separated list of L2 variable names (e.g., 'chlor_a,Rrs_443').",
    )
    parser.add_argument(
        "--max-distance-km",
        type=float,
        default=5.0,
        help="Maximum distance (km) from in situ point to satellite pixel.",
    )
    parser.add_argument(
        "--max-time-sec",
        type=float,
        default=3 * 3600,
        help="Maximum |Δt| in seconds between in situ and satellite.",
    )
    parser.add_argument(
        "--bad-flag-mask",
        type=int,
        default=None,
        help="Integer bitmask of bad flags to reject (optional).",
    )
    parser.add_argument(
        "--mode",
        choices=["window", "nearest"],
        default="window",
        help="Matchup mode: 'window' (aggregate) or 'nearest' (single pixel).",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Parse variable list
    vars_list: List[str] = []
    if args.vars:
        vars_list = [v.strip() for v in args.vars.split(",") if v.strip()]

    params = {
        "variables": vars_list,
        "max_distance_km": args.max_distance_km,
        "max_time_diff_sec": args.max_time_sec,
        "bad_flag_mask": args.bad_flag_mask,
        "mode": args.mode,
    }

    print("Running local matchup with parameters:")
    print(f"  SeaBASS: {args.seabass}")
    print(f"  L2     : {args.l2}")
    print(f"  Out    : {args.out}")
    print(f"  Vars   : {vars_list}")
    print(f"  max_distance_km : {args.max_distance_km}")
    print(f"  max_time_sec    : {args.max_time_sec}")
    print(f"  bad_flag_mask   : {args.bad_flag_mask}")
    print(f"  mode            : {args.mode}")

    output_path = append_satellite_to_seabass(
        seabass_path=args.seabass,
        l2_path=args.l2,
        params=params,
        output_path=args.out,
    )

    print(f"\n✅ Matchup complete. Output written to:\n  {output_path}")


if __name__ == "__main__":
    main()
