# Changelog

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

## Earlier
- Corrected crop erosion-yield elasticity handling (see
  `global_invest/erosion/CHANGELOG.md` and `verify_elasticity_fix.py`).
- Cell-centre boundary rasterization (`all_touched=false`) as the default rule.
