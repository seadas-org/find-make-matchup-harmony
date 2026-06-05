# Architecture (current code)

This is the demo-facing architecture map for the active prototype. It uses
the **current** module names; the older `docs/high_lelel_architecture.md`
and `docs/flow_chart.md` predate the `matchup/` package refactor.

## End-to-end view

```mermaid
flowchart LR
  Client[SeaDAS / notebooks / scripts]
  Harmony[Harmony orchestrator]
  Registry[DockerHub<br/>seadas/find-make-matchup-harmony:latest]

  Client -->|submit job| Harmony
  Harmony -->|pull image| Registry
  Harmony -->|STAC item + sources + extraArgs| Container

  subgraph Container[matchup-service container]
    direction TB
    Adapter[HarmonyAdapter.invoke<br/>harmony_service_example/transform.py]
    Engine[append_satellite_to_seabass<br/>matchup/orchestrator.py]
    Adapter -->|paired assets + params| Engine
    Engine -->|augmented SeaBASS| Adapter
  end

  Container -->|new STAC item<br/>asset 'data' = output .sb| Harmony
  Harmony -->|response| Client
```

## Inside the container — adapter ↔ engine split

```mermaid
flowchart TB
  subgraph adapter[harmony_service_example/ &mdash; Harmony plumbing]
    A1[process_item]
    A2[_pick_assets<br/>resolve seabass + l2 by<br/>key, suffix, media_type]
    A3[_get_param<br/>variables, max_distance_km,<br/>max_time_diff_sec, bad_flag_mask, mode]
    A4[download seabass + l2]
    A5[stage output as STAC asset 'data']
    A1 --> A2 --> A4 --> CALL
    A1 --> A3 --> CALL
    CALL[call engine] --> A5
  end

  subgraph engine[matchup/ &mdash; Harmony-agnostic]
    E0[orchestrator.append_satellite_to_seabass]
    E1[seabass_parser<br/>parses /fields, /units,<br/>/delimiter, /missing]
    E2[l2_loader<br/>loads lat/lon, vars, flags,<br/>per-pixel/scanline time]
    E3[match_row<br/>mode=window aggregates pixels<br/>within max_distance_km<br/>mode=nearest picks one pixel]
    E4[filters + aggregator<br/>bad_flag_mask, time gate,<br/>mean/median/std/n]
    E5[write augmented .sb<br/>rewrite /fields, /units<br/>preserve delimiter & row count]
    E0 --> E1 & E2 --> E3 --> E4 --> E5
  end

  CALL --> E0
```

**Why the split matters.** The engine has zero Harmony imports.
`run_local_matchup.py` drives the same engine from a CLI, a notebook can
import it directly, and a future non-Harmony service could reuse it. Only
the adapter knows about Harmony messages, STAC, staging, and the service
library.

## Input STAC item shape (what Harmony hands the adapter)

```jsonc
{
  "type": "Feature",
  "stac_version": "1.0.0",
  "id": "<paired-input-id>",
  "assets": {
    "seabass": { "href": "...", "type": "text/plain",        "roles": ["seabass"] },
    "l2":      { "href": "...", "type": "application/x-netcdf", "roles": ["l2"] }
  }
}
// plus Harmony-level:
//   sources[].variables[].name      -> requested satellite variables
//   extraArgs.max_distance_km       -> spatial window
//   extraArgs.max_time_diff_sec     -> temporal window
//   extraArgs.bad_flag_mask         -> integer mask against L2 flags
//   extraArgs.mode                  -> "window" | "nearest"
```

Asset resolution rules (see `_pick_assets`): prefer explicit keys
`seabass` / `l2`; fall back to filename suffix (`.sb`/`.txt`, `.nc`/`.nc4`)
or media-type containing `seabass` / `netcdf`.

## Output STAC item + SeaBASS contract

The adapter returns a fresh STAC item whose **only** asset is `data`
(input assets are intentionally cleared). The `data` asset is a SeaBASS
file with:

- **Same row count** as the input (SeaBASS-centric design).
- Original header preserved; only `/fields=` and `/units=` are rewritten.
- New columns appended per row:
  - `matchup_min_distance_km` &mdash; nearest matched pixel distance
  - `matchup_min_dt_sec` &mdash; nearest matched pixel time delta
  - For each requested variable `<v>`:
    `sat_<v>_mean`, `sat_<v>_median`, `sat_<v>_std`, `sat_<v>_n`

## Deployment pipeline

```mermaid
flowchart LR
  Dev[Developer push to main] --> GHA[GitHub Actions<br/>Publish Image to DockerHub]
  GHA -->|build prototype/matchup-service| DH[DockerHub<br/>seadas/find-make-matchup-harmony<br/>tags: latest, sha-&lt;commit&gt;]
  DH -->|public pull| Harmony[Harmony service registry<br/>service-image-tag/find-make-matchup-harmony]
  GHA2[GitHub Actions<br/>Python Syntax Check] -.->|runs in parallel| Dev
```

- Workflow: `.github/workflows/publish-image.yml`
- Auth: `DOCKERHUB_USERNAME` + `DOCKERHUB_TOKEN` repo secrets
- Tags emitted: `latest` (rolling on main), `sha-<long sha>` (immutable),
  and `<version>` on GitHub release publish.
- Bamboo `bin/deploy-service` PUTs the new tag at
  `<harmony-root>/service-image-tag/find-make-matchup-harmony` so the
  Harmony env picks up the new image &mdash; pending the matching entry
  in the Harmony service registry.
