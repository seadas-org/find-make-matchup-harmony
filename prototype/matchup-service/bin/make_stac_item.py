import json
import pathlib
import sys

seabass = pathlib.Path(sys.argv[1]).resolve()
l2 = pathlib.Path(sys.argv[2]).resolve()
out = pathlib.Path(sys.argv[3])

item = {
    "type": "Feature",
    "stac_version": "1.0.0",
    "id": "matchup-input-local",
    "geometry": None,
    "bbox": None,
    "properties": {},
    "assets": {
        "seabass": {
            "href": seabass.as_uri(),
            "media_type": "text/plain",
            "roles": ["data"],
        },
        "l2": {
            "href": l2.as_uri(),
            "media_type": "application/x-netcdf",
            "roles": ["data"],
        },
    },
}

out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(item, indent=2))
print(f"Wrote {out}")
