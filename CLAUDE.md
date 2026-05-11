# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Layout

This repo holds the analysis, design, and prototype for a Harmony-based "Find & Make Matchup" service for OB.DAAC / PACE ocean-color workflows. It is **not** a single Python package at the root.

- `docs/` — design notes, technical plans, mermaid diagrams. Read these for the big picture before changing service behavior.
- `harmony/` — the checked-in Harmony contract (`service-config.json`, `example-request.json`, `input-stac-item.json`, `stac-item-shape.md`). Treat these as the public interface contract.
- `prototype/matchup-service/` — **the active prototype**; nearly all development commands run from here.
- `prototype/matchup-service/matchup_engine.py` and `matchup_adapter.py` — older monolithic versions kept at the top level. The active code lives in the `harmony_service_example/` and `matchup/` packages described below; prefer those.

## Common Commands

Run from `prototype/matchup-service/`:

- First-time setup: `conda env create -n venv --file environment-dev.yml && conda activate venv` (per the prototype README). `make install` only *updates* an existing env via `conda env update`; it does not create one.
- `make test` — `pytest --ignore deps`.
- `make test-watch` — continuous run via `pytest-watch` (`ptw -c --ignore deps`).
- `make lint` — `flake8 harmony_service_example` (only that package is linted; max-line 99; ignores `F401`, `W503` per `.flake8`).
- `make build-image` — builds the Docker image via `bin/build-image`. Set `LOCAL_SVCLIB_DIR=../harmony-service-lib-py` to bake in a local checkout of the Harmony Service Library; otherwise the published version from PyPI is used.
- `make push-image` — tags and pushes to Amazon ECR via `bin/push-image` (uses `aws sts`/`aws ecr`; needs AWS creds and `AWS_DEFAULT_REGION`).
- `bin/harmony_service_example` — runs the built image locally with the cwd mounted; bind-mounts `../harmony-service-lib-py` if present.
- `python run_local_matchup.py --seabass IN.sb --l2 IN.nc --out OUT.sb --vars chlor_a,Rrs_443 --max-distance-km 5 --max-time-sec 10800 --mode {window|nearest}` — drive the engine without Harmony.

Single-test invocation: `pytest tests/test_bbox.py::test_<name>` from `prototype/matchup-service/`.

CI lives in two places: top-level `.github/workflows/py-compile.yml` only runs `python -m py_compile` over the active modules (syntax check, not a test runner — do not assume tests run in CI), and `prototype/matchup-service/.github/workflows/` (e.g. `publish-image.yml`) governs image publishing for the prototype. The prototype README also references a Bamboo CI job at `ci.earthdata.nasa.gov/browse/HARMONY-HG` running in the Earthdata environment.

## Docker-in-Docker Builds

`bin/build-image` honors a `.env` file with `DIND=true`, `PLATFORM=linux/amd64`, and `DOCKER_DAEMON_ADDR=host.docker.internal:2375` for dev-container scenarios. The Dockerfile installs deps from `environment.yml` into the conda base env and ENTRYPOINTs `python -m harmony_service_example`.

## Architecture: Adapter ↔ Engine Split

The design intentionally separates Harmony plumbing from matchup science. Preserve this split when editing.

- **Harmony adapter** — `prototype/matchup-service/harmony_service_example/transform.py` defines `HarmonyAdapter(BaseHarmonyAdapter)`. `__main__.py` wires it to `harmony_service_lib.run_cli`. The adapter:
  1. Receives a STAC item containing **both** the SeaBASS file and the paired L2 granule on the same item.
  2. Resolves assets by preferred keys `seabass` and `l2`, falling back to extension/media-type heuristics (`.sb`/`.txt`, `.nc`/`.nc4`, "seabass"/"netcdf" media types).
  3. Pulls variable list from `sources[].variables[].name` and numeric tuning from Harmony `extraArgs` (`max_distance_km`, `max_time_diff_sec`, `bad_flag_mask`, `mode`); see `_get_param` for the full lookup chain across Harmony message-shape variants.
  4. Downloads inputs, calls the engine, then `stage()`s the output and returns a new STAC item whose **only** asset is `data` (input assets are intentionally cleared).

- **Matchup engine** — `prototype/matchup-service/matchup/` is Harmony-agnostic and is the only thing `run_local_matchup.py` imports. Single public entry point: `matchup.orchestrator.append_satellite_to_seabass(seabass_path, l2_path, params, output_path)`. Internal modules:
  - `seabass_parser.py` — parses SeaBASS header (`/fields=`, `/units=`, `/delimiter=`, `/missing=`) and records.
  - `l2_loader.py` — loads OB.DAAC L2 NetCDF (lat/lon, requested vars, flags, optional per-pixel or per-scanline time). Falls back to `granule_datetime_utc` parsed from the filename pattern `.YYYYMMDDTHHMMSS.` when no time array exists.
  - `match_row.py` — per-record matching (`window` aggregates pixels within `max_distance_km`; `nearest` picks one pixel via squared lat/lon). Applies `bad_flag_mask` against `l2.flags` and a time-tolerance gate; returns `matchup_min_distance_km`, `matchup_min_dt_sec`, and `sat_<var>_{mean,median,std,n}`.
  - `filters.py`, `aggregator.py` — supporting filtering and aggregation primitives.
  - The orchestrator is **SeaBASS-centric**: row count is preserved, original header is rewritten only to update `/fields=` and `/units=`, and the original delimiter token (`comma`/`tab`/...) is mapped back to a real character before writing data lines.

When changing the input/output contract, update `harmony/service-config.json` and `harmony/stac-item-shape.md` together — they are the source of truth for downstream Harmony integration.

## Conventions

- Keep Harmony adapter concerns in `harmony_service_example/`, matchup science in `matchup/`. Don't import `harmony_service_lib` from inside `matchup/`.
- Tests live in `prototype/matchup-service/tests/` as `test_<behavior>.py`; reuse fixtures from `prototype/matchup-service/testdata/`.
- Commit subjects: short, sentence-case, imperative (e.g. `Implement initial make-matchup logic ...`).
- PRs follow `prototype/matchup-service/.github/pull_request_template.md`: include the **Jira issue ID**, a concise description, local test steps, and checklist updates for tests and docs.
- Don't commit AWS creds, `.env`, or large sample inputs; only small reproducible fixtures belong under `testdata/`.
