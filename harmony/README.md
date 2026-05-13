# Harmony Configurations and Example Jobs

This directory contains the checked-in Harmony contract for the active
`find-make-matchup-harmony` prototype.

Files in this directory:

- `service-config.json`: service identity, image, runtime parameters, and input/output contract.
- `example-request.json`: realistic Harmony data-operation payload for the current adapter.
- `input-stac-item.json`: exact paired-input STAC item shape expected by the adapter.
- `stac-item-shape.md`: short reference for required fields, optional fields, and fallback rules.

The current adapter is implemented in
`prototype/matchup-service/harmony_service_example/transform.py`.

Important constraints from that code:

- The adapter expects a single STAC item containing both the SeaBASS file and
  the L2 granule.
- Preferred asset keys are `seabass` and `l2`.
- Variable selection comes from `sources[].variables[].name`.
- Numeric tuning parameters are read from Harmony request `extraArgs`.
- Output is a staged SeaBASS file returned as STAC asset key `data`.
