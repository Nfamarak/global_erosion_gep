# Changelog

## Revision — harmonized per-crop valuation (2026-11)
- New valuation mode `GEP_EROSION_VALUATION_MODE=percrop` aligns the erosion
  account with the common GTAP-InVEST `crop_provision` per-crop values and removes
  the within-country tonnes-weighted aggregation approximation. Default behaviour
  (`shock_x_gpv`) is unchanged. See `global_invest/erosion/CHANGELOG.md` for the
  full specification (value table, FAO->SPAM correspondence, pooled-code split,
  `in_crop_provision_account` byproduct exclusion).
- `run_erosion.py` gains `GEP_EROSION_TASK_TREE` (full | calculation | **valuation** |
  **value_from_shares** | results) so the valuation can be re-run without re-running InVEST
  SDR — and `value_from_shares` re-values a completed run's per-crop shares in seconds
  (no biophysical recompute at all) — plus
  `GEP_EROSION_PERCROP_VALUE_CSV`, `GEP_EROSION_FAO_SPAM_CROSSWALK_CSV`, and
  `GEP_EROSION_ELEVATION_PATH` hooks. Launchers added under `sbatch/`
  (`rerun_cropfix_valonly.sbatch`, `rerun_allcorrections_valonly.sbatch`).
- Loaders are BOM-safe (`utf-8-sig`) so a BOM in the correspondence/value CSV no
  longer triggers a silent fallback to the embedded crosswalk.

## Revised run — finer hydrologically conditioned DEM (2026-10)
- The account is recomputed on a hydrologically conditioned ~1 km DEM
  (HydroSHEDS-conditioned) in place of the coarse ~6.45 km aggregated routing.
  Modelled soil retention rises ~2.2x; combined SES-11 rises from ~USD 18 billion
  to USD 44.5 billion, EPS-5 to USD 80.1 billion; 171 countries (SES-11). The
  coarse-grid account is a conservative lower bound. See manuscript SI
  (DEM-resolution sensitivity).
- `run_erosion.py`: added environment hooks so the revised run needs no code edits:
  - `GEP_EROSION_DEM_PATH` -- DEM for the SDR run (point at the conditioned DEM)
  - `GEP_EROSION_VAL_USLE_PATH` / `GEP_EROSION_VAL_AVOIDED_PATH` -- valuation now
    reads the conditioned SDR outputs rather than the baseline SDR (this fixes the
    "valuation reads Feb SDR" coupling noted in the handover)
  - `GEP_EROSION_UPS_PATH` -- upstream prevention share from the conditioned network
  - `GEP_EROSION_THRESH_HIGH` / `GEP_EROSION_THRESH_LOW` -- scenario thresholds
    (SES-11 high=11, EPS-5 high=5, low=2)
- Added `conditioned_inputs/` (HydroSHEDS acquisition, `remap_flowdir.py`,
  `upstream_conditioned.py`), `sbatch/` templates, `figures/make_erosion_gep_figures.py`,
  and `validation/` (Danube/Elbe routing check vs HydroRIVERS, SI Fig. S10).
- Added `conditioned_inputs/resample_sdr_to_accounting_grid.py` and documented it as
  pipeline stage 3. The InVEST SDR runs at ~1 km but the account is tallied on the
  ~6.45 km equal-area accounting grid defined by `usle_2019_revised_feb_13.tif`; this
  step area-average-resamples (`Resampling.average`, correct for intensive t ha-1 yr-1
  rasters) the `usle`/`avoided_erosion` outputs onto that template before valuation.
  Previously this resampling was only an un-committed manual pre-step (the MSI
  `sdr_on_feb_grid/` outputs), so a clone could silently value at native ~1 km; the
  valuation's own internal reproject keeps native resolution, so this explicit stage
  is required to reproduce the headline grid.

## Earlier
- Corrected crop erosion-yield elasticity handling (see
  `global_invest/erosion/CHANGELOG.md` and `verify_elasticity_fix.py`).
- Cell-centre boundary rasterization (`all_touched=false`) as the default rule.
