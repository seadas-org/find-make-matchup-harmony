import os
import shutil
from tempfile import mkdtemp

from harmony_service_lib import BaseHarmonyAdapter
from harmony_service_lib.util import (
    generate_output_filename,
    download,
    HarmonyException,
    stage,
)
from pystac import Asset

from matchup.orchestrator import append_satellite_to_seabass


def _as_var_names(vars_from_source):
    """Harmony variables can be objects with .name or plain strings."""
    if not vars_from_source:
        return []
    out = []
    for v in vars_from_source:
        out.append(getattr(v, "name", v))
    return out


def _pick_assets(item):
    """
    Heuristic to locate the SeaBASS and L2 assets within a STAC item.

    Expected (prototype assumptions):
      - one asset is SeaBASS-like: .sb/.txt
      - one asset is L2 NetCDF: .nc/.nc4
    """
    assets = list(item.assets.values())

    def is_seabass(a: Asset):
        href = (a.href or "").lower()
        mt = (a.media_type or "").lower()
        return href.endswith(".sb") or href.endswith(".txt") or ("seabass" in mt)

    def is_l2(a: Asset):
        href = (a.href or "").lower()
        mt = (a.media_type or "").lower()
        return href.endswith(".nc") or href.endswith(".nc4") or ("netcdf" in mt)

    seabass_asset = next((a for a in assets if is_seabass(a)), None)
    l2_asset = next((a for a in assets if is_l2(a)), None)

    return seabass_asset, l2_asset


def _get_param(message, name, default):
    """
    Best-effort parameter lookup. Harmony message shapes vary a bit by version.
    We check common places and fall back to default.
    """
    # Some Harmony message versions expose a dict-like "params" or "parameters"
    for attr in ("params", "parameters", "user_parameters", "extra_args", "extraArgs"):
        d = getattr(message, attr, None)
        if isinstance(d, dict) and name in d:
            return d[name]
    # Some versions expose "request" or similar nested dict
    req = getattr(message, "request", None)
    if isinstance(req, dict) and name in req:
        return req[name]
    return default


class HarmonyAdapter(BaseHarmonyAdapter):
    """
    Matchup service Harmony adapter.
    Downloads SeaBASS + L2 inputs, runs the matchup engine, stages output.
    """

    def process_item(self, item, source):
        logger = self.logger
        message = self.message

        result = item.clone()
        result.assets = {}

        output_dir = mkdtemp()
        try:
            seabass_asset, l2_asset = _pick_assets(item)

            if seabass_asset is None or l2_asset is None:
                raise HarmonyException(
                    "Could not find both SeaBASS (.sb/.txt) and L2 NetCDF (.nc/.nc4) assets "
                    "in the input STAC item. Please ensure the item includes both."
                )

            seabass_path = download(
                seabass_asset.href,
                output_dir,
                logger=logger,
                access_token=message.accessToken,
            )
            l2_path = download(
                l2_asset.href,
                output_dir,
                logger=logger,
                access_token=message.accessToken,
            )

            # Params: variable list comes from Harmony variables selection
            var_names = _as_var_names(getattr(source, "variables", None))

            params = {
                "variables": var_names,
                "max_distance_km": float(_get_param(message, "max_distance_km", 5.0)),
                "max_time_diff_sec": float(_get_param(message, "max_time_diff_sec", 3 * 3600)),
                "bad_flag_mask": _get_param(message, "bad_flag_mask", None),
                "mode": _get_param(message, "mode", "window"),
            }

            # Output filename strategy
            operations = dict(variable_subset=source.variables)
            basename = os.path.basename(
                generate_output_filename(seabass_asset.href, **operations)
            )
            output_filename = f"{basename}.sb"
            output_path = os.path.join(output_dir, output_filename)

            logger.info(f"SeaBASS input: {seabass_path}")
            logger.info(f"L2 input: {l2_path}")
            logger.info(f"Output: {output_path}")
            logger.info(f"Params: {params}")

            append_satellite_to_seabass(
                seabass_path=seabass_path,
                l2_path=l2_path,
                params=params,
                output_path=output_path,
            )

            # Stage the output back to Harmony
            mime = getattr(message.format, "mime", None) or "text/plain"
            url = stage(
                output_path,
                output_filename,
                mime,
                location=message.stagingLocation,
                logger=logger,
            )

            result.assets["data"] = Asset(
                url,
                title=output_filename,
                media_type=mime,
                roles=["data"],
            )

            return result

        finally:
            shutil.rmtree(output_dir)
