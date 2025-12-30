

# Reference Make-Matchup Test Case (MODIS SST)

This directory contains a verified reference case for the
**make-matchup** functionality of the Find & Make Matchup Harmony service.

## Inputs
- SeaBASS file:
  - `seabass_input.sb`
    (original: `VIIRS_2024_HPLC_NASA_R1.sb`)
- Satellite granule (not stored in this repo):
  - `AQUA_MODIS.20240520T191501.L2.SST.nc`

  The L2 file can be obtained from OB.DAAC:
  https://oceandata.sci.gsfc.nasa.gov/cmr/getfile/AQUA_MODIS.20240520T191501.L2.SST.nc

## Output
- `matchup_output.sb`
  - SeaBASS file with appended satellite matchup fields
  - Verified for spatial, temporal, and aggregation correctness

## Command used to generate the output

```bash
python run_local_matchup.py \
  --seabass testdata/seabass_files/VIIRS_2024_HPLC_NASA_R1.sb \
  --l2 testdata/l2_files/AQUA_MODIS.20240520T191501.L2.SST.nc \
  --out testdata/output/VIIRS_2024_HPLC_NASA_R1.AQUA_MODIS_20240520T191501.matchup.sb \
  --vars sst \
  --max-distance-km 5 \
  --max-time-sec 10800 \
  --mode window
```

```bash
 python run_local_matchup.py --seabass testdata\seabass_files\VIIRS_2024_HPLC_NASA_R1.sb --l2 testdata\l2_files\AQUA_MODIS.20240520T191501.L2.SST.nc --out testdata\output\VIIRS_2024_HPLC_NASA_R1.AQUA_MODIS_20240520T191501.matchup.sb --vars sst --max-distance-km 5 --max-time-sec 10800 --mode window
```

### Notes

The search (find) phase is assumed to be complete.

This test case exercises only the make-matchup logic.

Time difference is computed using granule reference time when per-pixel time is unavailable.