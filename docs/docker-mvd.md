# Make Matchup – Docker MVD (Minimal Viable Deployment)

This note documents the minimal Docker setup needed to run the Make Matchup reference case inside a container.

## Build

From `prototype/matchup-service/`:

```powershell
docker build -f Dockerfile.mvd -t make-matchup:dev .

```

## Run (reference case)

Run from `prototype/matchup-service/` so the testdata/ mount works as expected:

```powershell
docker run --rm -it `
  -v ${PWD}\testdata:/home/testdata `
  --entrypoint micromamba `
  make-matchup:dev `
  run -n base python run_local_matchup.py `
    --seabass testdata/seabass_files/VIIRS_2024_HPLC_NASA_R1.sb `
    --l2 testdata/l2_files/AQUA_MODIS.20240520T191501.L2.SST.nc `
    --out testdata/output/docker.matchup.sb `
    --vars sst `
    --max-distance-km 5 `
    --max-time-sec 10800 `
    --mode window

```
### Reference inputs

SeaBASS:

`testdata/seabass_files/VIIRS_2024_HPLC_NASA_R1.sb
`

Satellite L2:

`testdata/l2_files/AQUA_MODIS.20240520T191501.L2.SST.nc
`

Expected output

Output file written to:

`testdata/output/docker.matchup.sb`


Quick sanity checks

Confirm matchup fields were appended:

`Select-String -Path .\testdata\output\docker.matchup.sb -Pattern "^/fields="
`

Confirm at least one row has sat_sst_n > 0 (non-empty satellite stats):

`Select-String -Path .\testdata\output\docker.matchup.sb -Pattern ",[0-9]+$" | Select-Object -First 10
`


