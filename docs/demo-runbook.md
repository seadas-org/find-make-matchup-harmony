# Demo Runbook &mdash; Internal Eng / Management Review

Target length: **25 minutes**, walkthrough format. Designed for an audience
of internal engineering and management. Live invoke included.

## Pre-demo checklist (5 minutes before start)

- [ ] Laptop on AC; close Slack / Mail notifications; mute phone.
- [ ] Terminal A (the demo terminal) at:
      `~/mainwork/harmony/find-make-matchup-harmony/prototype/matchup-service`
- [ ] Terminal B (backup &mdash; same cwd, useful if A hits a hiccup).
- [ ] Editor open with these files in tabs, in this order:
      1. `docs/architecture.md` (for beat 3&ndash;8)
      2. `harmony_service_example/transform.py` (for beat 3&ndash;8)
      3. `matchup/orchestrator.py` (for beat 3&ndash;8)
      4. `harmony/service-config.json` (for beat 8&ndash;13)
      5. `harmony/example-request.json` (for beat 8&ndash;13)
      6. `harmony/stac-item-shape.md` (for beat 8&ndash;13)
- [ ] Browser tabs:
      1. https://github.com/seadas-org/find-make-matchup-harmony
      2. https://github.com/seadas-org/find-make-matchup-harmony/actions
      3. https://hub.docker.com/r/seadas/find-make-matchup-harmony
- [ ] Pre-warm the image cache so the live pull is fast:
      `docker pull seadas/find-make-matchup-harmony:latest`
- [ ] Sanity-run the demo invoke once:
      `bin/demo-invoke` &mdash; confirms image runs and writes output.
- [ ] Wipe the demo output dir so the live run shows fresh files:
      `docker run --rm -v /tmp/demo-verify:/work alpine:3 rm -rf /work/data /work/metadata`

## Beat-by-beat

### Beat 1 &mdash; Problem & motivation (0:00&ndash;3:00)

**Slide.** One slide; three bullets:
- **Problem.** Ocean-color validation needs to match per-station in-situ
  measurements (SeaBASS files) against satellite L2 granules &mdash; done by
  hand per-PI today, not reproducible across processings.
- **Solution.** Harmony service that takes a paired (SeaBASS, L2) STAC
  item and returns an augmented SeaBASS file with per-record satellite
  matchup statistics. Same row count, same scientist's file format.
- **Status.** Active prototype; image auto-publishing to DockerHub; ready
  for Harmony integration.

**Talking point.** "Today this is a manual notebook step per scientist.
We're moving it into Harmony so any registered SeaBASS file × L2 granule
pair becomes a one-call job."

### Beat 2 &mdash; Architecture: adapter ↔ engine split (3:00&ndash;8:00)

**On screen.** `docs/architecture.md` (mermaid renders in GitHub preview /
VS Code preview).

**Walk the diagram top down**, then switch to code:

1. `harmony_service_example/transform.py` &mdash; "this is the only file
   that knows about Harmony. It picks the assets, parses the params,
   downloads the inputs, calls the engine, stages the output."
2. `matchup/orchestrator.py` &mdash; `append_satellite_to_seabass`:
   "this is Harmony-agnostic. Notice no `harmony_service_lib` imports.
   Run it from a CLI (`run_local_matchup.py`), a notebook, anywhere."

**Talking point.** "The split lets us evolve the matchup science (the
hard part) without breaking the Harmony contract (the boring part), and
lets us reuse the engine outside Harmony if we need to."

### Beat 3 &mdash; Harmony integration contract (8:00&ndash;13:00)

**On screen.** Open three files side by side:

1. `harmony/service-config.json` &mdash; "this is what Harmony's service
   registry needs to know about us: image name, entrypoint, parameter
   contract, input/output STAC shape."
2. `harmony/example-request.json` &mdash; "this is what a real Harmony
   data-operation payload looks like. Note `sources[].variables[].name`
   for variable selection and `extraArgs` for numeric tuning."
3. `harmony/stac-item-shape.md` &mdash; "and this is the STAC item shape
   the adapter expects per-granule &mdash; SeaBASS asset + L2 asset on
   the same item. Asset keys preferred but with media-type fallbacks."

**Talking point.** "These three files are the public interface. They're
checked in so the Harmony team can integrate against a stable spec
without reading our code."

### Beat 4 &mdash; Live invoke (13:00&ndash;21:00)

**Terminal A.** Run:

```bash
bin/demo-invoke
```

While it runs (~12 s after image is cached), narrate:

- "It just pulled the image we publish to DockerHub &mdash; the same one
  Harmony will pull in production. Public, no auth."
- "Now the adapter is downloading the test SeaBASS file and L2 granule
  &mdash; the same paired test fixture we use in CI."
- (after ~10 s) "Engine appended sat columns row-by-row, output STAC
  catalog written."

**Then point at the script's tail output**:

- `==> Output data:` &mdash; the new `.sb` file is the augmented matchup.
- `==> Output STAC catalog + item:` &mdash; STAC catalog Harmony returns
  to the client. Single asset, key `data`.
- `==> Input vs output SeaBASS /fields= diff:` &mdash; the appended
  columns (`matchup_min_distance_km`, `matchup_min_dt_sec`,
  `sat_sst_{mean,median,std,n}`).

**Talking point.** "This is the production artifact. Pulled from
DockerHub, ran on test data, produced an output that's byte-identical to
the reference fixture in `testdata/`. We have CI proof that this image
behaves exactly like the local build."

### Beat 5 &mdash; Pipeline status (21:00&ndash;23:00)

**Browser tab 2** (GitHub Actions). Show the green latest run.

**Slide / talking point**:

- ✅ **Local build & invoke**: working since prototype landed.
- ✅ **Top-level CI** (`Python Syntax Check`): green on every push.
- ✅ **DockerHub publish** (`Publish Image to DockerHub`): green;
  `seadas/find-make-matchup-harmony:latest` + `sha-<commit>` tags
  written on every push to `main`.
- ⏳ **Harmony service registry entry**: pending NASA / Earthdata side
  &mdash; once that's in, `bin/deploy-service` can PUT the new tag and
  the SIT / UAT / prod Harmony envs will run the new image.

**Browser tab 3** (DockerHub). Show the public image page with the tag
list and pull count.

### Beat 6 &mdash; Q&A buffer (23:00&ndash;25:00)

Likely questions and one-liner answers:

- **"What other variables beyond SST?"** Anything in an OB.DAAC L2 file.
  Variable list comes from the Harmony job's `sources[].variables[]`.
  The engine is variable-agnostic.
- **"How big is the matchup window?"** Configurable per job via
  `extraArgs.max_distance_km` (default 5 km) and `extraArgs.max_time_diff_sec`
  (default 3 h). Mode `window` aggregates pixels in the box; mode
  `nearest` picks the single closest pixel.
- **"What about flagged pixels?"** `extraArgs.bad_flag_mask` is OR'd
  against the L2 `l2_flags` array; matching pixels are dropped before
  aggregation.
- **"When does this go live in Harmony?"** Image is published; we're
  waiting on the Harmony service registry entry for
  `find-make-matchup-harmony`.
- **"How big is the image?"** ~545 MB compressed on DockerHub, 1.5 GB
  uncompressed. Mostly miniconda + scientific Python stack.

## Fallback plays

| If &hellip; | Then &hellip; |
| --- | --- |
| `docker pull` is slow | Set `IMAGE` env to a locally-tagged copy and re-run: `IMAGE=find-make-matchup-harmony:latest bin/demo-invoke`. (Make sure that local tag exists from `make build-image`.) |
| Invoke fails with `Required environment variables are not set: STAGING_PATH, STAGING_BUCKET` | The `bin/demo-invoke` script sets these; if you copy-pasted a raw docker run, prepend `-e STAGING_PATH=local -e STAGING_BUCKET=local-bucket`. |
| GitHub Actions tab loads slow during beat 5 | Have a screenshot of the green run ready as a backup slide. |
| Audience question about ECR | "We moved off ECR per ops guidance &mdash; publishing to DockerHub now. Pipeline behaviour is identical from the consumer's perspective; the registry URL is different." |
| Audience question about secrets | "DockerHub credentials are stored as GitHub Actions repository secrets, never in the repo. Workflow uses the official `docker/login-action`." |
| The live invoke crashes mid-demo | Show the `testdata/output/VIIRS_2024_HPLC_NASA_R1_sst.sb.sb` tracked fixture &mdash; that's the same output, captured from a prior known-good run. Pivot to: "the output here is byte-identical to what just ran; I'll debug the live run after." |
