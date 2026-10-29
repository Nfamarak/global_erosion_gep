# Global Erosion GEP

A reproducible global account of the value of crop production that vegetation and
land cover protect from water-driven soil erosion, implemented as a Gross Ecosystem
Product (GEP) account aligned with SEEA Ecosystem Accounting. The account couples
InVEST SDR (RUSLE-based) erosion modelling with an on-farm and upstream prevention
share, and values the protected production using SPAM2020 production, FAOSTAT prices,
and crop-specific erosion-yield elasticities.

This repository accompanies the *Land Use Policy* manuscript **LUP-D-26-02970** and
reproduces the **revised (finer hydrologically conditioned-DEM) account**.

## Headline result (2019, revised run)

| Scenario | Severity threshold | Combined GEP | On-farm | Upstream | Countries |
|---|---|---|---|---|---|
| SES-11 (headline) | >= 11 t ha-1 yr-1 | **USD 44.5 billion / yr** | 35.3 | 35.4 | 171 |
| EPS-5 (sensitivity) | >= 5 t ha-1 yr-1 | **USD 80.1 billion / yr** | 63.2 | 63.6 | 174 |

All figures are 2019 constant USD; the combined headline is about 1.6% of global crop
gross production value.

## What is new in the revised run

The original account routed the upstream term on a coarse (~6.45 km) aggregated DEM.
Following review, the account is recomputed on a **hydrologically conditioned,
finer-resolution DEM (HydroSHEDS-conditioned, ~1 km)**, which resolves the
slope length and steepness that the coarse grid flattened. Modelled soil retention
rises about 2.2x and the combined account rises about 2.5x (from roughly USD 18
billion to USD 44.5 billion). The coarse-grid account is therefore a **conservative
lower bound**. The mechanism (RUSLE LS-factor sensitivity to DEM resolution) is
documented in the manuscript Supplementary Information.

## Repository layout

```
global_erosion_gep/
  global_invest/erosion/        core module: InVEST SDR + prevention-share valuation
    run_erosion.py              thin runner; all paths/knobs are env-configurable
    erosion_functions.py        SDR run, prevention shares, country valuation
    erosion_tasks.py            hazelbean task tree
    erosion_utils.py            helpers
    msi/                        example cluster launchers + preflight checks
  conditioned_inputs/           acquire + prepare the conditioned terrain
    download_hydrosheds.sh      HydroSHEDS conditioned DEM + direction grid
    download_con_dem_3s.sh      conditioned DEM continental tiles -> VRT
    align_inputs_to_grid.sh     reproject/align SDR inputs to the analysis grid
    prep_sdr_inputs_fine.sh     prepare the 1 km conditioned SDR inputs
    remap_flowdir.py            encode conditioned D8 flow direction
    upstream_conditioned.py     accumulate avoided/potential erosion -> upstream share
  sbatch/
    regen_upstream.sbatch       Stage 3 template (upstream on conditioned network)
    run_scenario.sbatch         Stages 2+4 template (SDR + valuation; one per scenario)
  figures/
    make_erosion_gep_figures.py publication figures (bars, scatter, heatmap, maps)
  validation/
    make_danube_elbe_figure_overlay.py   routing validation vs HydroRIVERS (SI Fig. S10)
  environment.yml  CITATION.cff  LICENSE
```

## Environment

```
conda env create -f environment.yml
conda activate gep_erosion
```
(If you already have the MSI `gep_InVEST` environment, use that instead.)
Key dependencies: `natcap.invest`, `hazelbean`, `pygeoprocessing`, `rasterio`,
`geopandas`, `rioxarray`, `pandas`, `numpy`, `matplotlib`, `mapclassify`.

## Pipeline (four stages)

1. **Acquire conditioned inputs** (`conditioned_inputs/`): download the HydroSHEDS
   conditioned DEM and 30 arc-sec flow-direction grid, then align the SDR inputs to
   the analysis grid.
2. **Run InVEST SDR on the conditioned inputs** (`sbatch/run_scenario.sbatch`). All
   four SDR inputs must be the 1 km conditioned/aligned layers on the same grid:
   `GEP_EROSION_DEM_PATH` (conditioned DEM), `GEP_EROSION_LULC_PATH`,
   `GEP_EROSION_ERODIBILITY_PATH`, `GEP_EROSION_EROSIVITY_PATH`. Produces the `usle`
   and `avoided_erosion` rasters.
3. **Regenerate the upstream prevention share** (`sbatch/regen_upstream.sbatch`):
   `remap_flowdir.py` encodes the conditioned D8 flow direction and
   `upstream_conditioned.py` accumulates avoided and potential erosion on that
   network to a 0..1 share, resampled to the analysis grid.
4. **Value the account** (`sbatch/run_scenario.sbatch`): the valuation reads the
   conditioned SDR rasters and the conditioned upstream share. Run once per scenario
   (`GEP_EROSION_THRESH_HIGH=11` for SES-11, `=5` for EPS-5). Each run must write to a
   **fresh** `GEP_EROSION_OUTPUT_DIR` (the valuation skips if `integrated_country_gep.csv`
   already exists).

Then build figures with `figures/make_erosion_gep_figures.py`.

## Reproduce from the consolidated archive (fastest)

All inputs, conditioned SDR outputs, results, figures, and the exact job scripts are
consolidated on MSI at:

```
/projects/standard/jajohns/shared/nfamara/erosion_global_gep_final/
  inputs_conditioned/{sdr,valuation,upstream}/   SDR + valuation + upstream inputs
  sdr_outputs_conditioned/                       conditioned usle + avoided_erosion
  results/{ses11_headline,eps5_sensitivity,ses11_receiving_excluded}/
  figures/                                       publication figures
  provenance/                                    the sbatch + python actually run
```

`sbatch/run_scenario.sbatch` and `figures/make_erosion_gep_figures.py` already
default to this layout via a single `ARCHIVE` variable, so on MSI you only set the
repo path and submit. Two modes: **quick** (default) values the account directly from
the archived conditioned SDR outputs; **full** regenerates InVEST SDR from
`inputs_conditioned/sdr/` first (see the comments in `run_scenario.sbatch`). To run
elsewhere, change the one `ARCHIVE=` line.

## Configuration (environment variables)

`run_erosion.py` resolves every path and knob from environment variables, with the
baseline paths as fallback, so no code editing is needed.

| Variable | Meaning | Revised-run value |
|---|---|---|
| `GEP_EROSION_DEM_PATH` | DEM for the SDR run | conditioned ~1 km DEM |
| `GEP_EROSION_LULC_PATH` | land cover for the SDR run | 1 km aligned ESA-CCI 2019 |
| `GEP_EROSION_ERODIBILITY_PATH` | soil erodibility (K) raster | 1 km aligned |
| `GEP_EROSION_EROSIVITY_PATH` | rainfall erosivity (R) raster | 1 km aligned |
| `GEP_EROSION_SDR_OUTPUT_DIR` | where SDR writes outputs | your scratch dir |
| `GEP_EROSION_VAL_USLE_PATH` | actual-erosion raster for valuation | conditioned SDR `usle` |
| `GEP_EROSION_VAL_AVOIDED_PATH` | avoided-erosion raster for valuation | conditioned SDR `avoided` |
| `GEP_EROSION_UPS_PATH` | upstream prevention-share raster | from Stage 3 |
| `GEP_EROSION_THRESH_HIGH` | severe-erosion threshold (t/ha/yr) | 11 (SES-11) or 5 (EPS-5) |
| `GEP_EROSION_THRESH_LOW` | low threshold for small/low-elevation countries | 2 |
| `GEP_EROSION_ALL_TOUCHED` | boundary rasterization rule | false (cell-centre) |
| `GEP_EROSION_OUTPUT_DIR` | output directory (use a fresh one per run) | your scratch dir |
| `GEP_EROSION_RUN_TAG` | run label | e.g. `ses11_conditioned` |

Pointing `GEP_EROSION_VAL_USLE_PATH` / `GEP_EROSION_VAL_AVOIDED_PATH` at the
conditioned SDR outputs is what makes the valuation reflect the finer run rather
than the baseline SDR.

## Key output

`integrated_country_gep.csv` (one row per country), with the decomposed account:
`gep_const2019_usd_{onfarm,upstream,combined}`,
`share_protected_production_{onfarm,upstream,combined}`,
`gdp_loss_pct_{onfarm,upstream,combined}`, plus crop gross production value and GDP.
The combined prevention share is the probabilistic union of the two pathways
(`combined = 1 - (1 - onfarm)(1 - upstream)`), so it is an upper-envelope summary
rather than an additive total; `gep_incremental_upstream_usd` gives the additive
split (`combined = onfarm + incremental_upstream`).

## Figures

`python figures/make_erosion_gep_figures.py` (edit the `CONFIG` block; set
`SCENARIO = "ses11"` or `"eps5"`). Writes PNGs: top-country value and
GDP-dependence bars, the on-farm/upstream pathway stack, the pathway-by-threshold
decomposition, the value-vs-GDP scatter by World Bank income group, the
country-by-crop heatmap, the prevention-share and SDR raster maps, and the country
choropleths. `validation/make_danube_elbe_figure_overlay.py` reproduces the
Danube/Elbe routing validation against HydroRIVERS (SI Fig. S10).

## Data availability

The account draws on public datasets: HydroSHEDS (terrain and flow network),
ESA-CCI Land Cover 2019, SPAM2020 (IFPRI) crop production, FAOSTAT production values
and prices, and World Bank GDP. Large prepared inputs (aligned rasters, boundary
GeoPackage) are available from the authors on request. The released code is archived
at Zenodo; see `CITATION.cff` for the DOI.

## Citation

Please cite both the software (Zenodo DOI in `CITATION.cff`) and the article
(Dampha and Johnson, *Land Use Policy*, LUP-D-26-02970).

## License

MIT (see `LICENSE`).

## Contact

Nfamara K. Dampha, Natural Capital Alliance (NatCap TEEMs), University of Minnesota.
