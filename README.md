# global_erosion_gep

> **Revised build — 1 km conditioned DEM + harmonized per-crop valuation.** The upstream
> term and the SDR run are computed on a HydroSHEDS-conditioned ~1 km DEM, and the headline
> account is valued with the common `crop_provision` per-crop values
> (`GEP_EROSION_VALUATION_MODE=percrop`). See the top-level **README.md** and **CHANGELOG.md**.

GEP (Global Ecosystem services and Products) erosion / sediment retention
service module, built on [hazelbean](https://github.com/jandrewjohnson/hazelbean)'s
`ProjectFlow` task-tree framework.

This code implements the analysis described in:

> Dampha, N.K. & Johnson, J. *A Global Gross Ecosystem Product account for
> nature's soil-retention services protecting crop production.*
> Department of Applied Economics, Natural Capital Alliance – The
> Earth-Economy Modelers (NatCap TEEMs), University of Minnesota.
> Submitted to Land Use Policy (manuscript LUP-D-26-02970).

## Purpose

Soil erosion by water damages cropland directly (on-farm yield loss) and
indirectly by degrading downstream water resources and infrastructure
fed by eroded watersheds. Vegetation and land cover regulate this by
stabilizing soils, reducing runoff energy, and limiting sediment
transport — a regulating ecosystem service this module quantifies as an
annual economic flow, consistent with SEEA-EA ecosystem accounting.

The headline result (SES-11, 2019 USD, 1 km conditioned-DEM biophysics with harmonized
per-crop valuation): soil-retention services protect an estimated **USD 59.9 billion/yr**
of global crop production across **169 countries**. The EPS-5 sensitivity (general
threshold 5 t·ha⁻¹·yr⁻¹) gives **USD 106.0 billion/yr** across 172 countries. Absolute
values concentrate in large agricultural economies (China, India, Indonesia); relative
dependence (share of GDP) is highest in low-income, agriculture-dependent economies.
Country coverage follows the common crop-provision account (Taiwan and Macao are
out-of-account, together <1% of the global total).

## File structure

Follows the `run / tasks / functions / initialize / utils` convention used
across GEP service modules:

```
erosion/
  run_erosion.py            # standalone entry point (sets p.erosion_* paths, calls p.execute())
  erosion_tasks.py           # ProjectFlow task wrappers, one per pipeline stage
  erosion_functions.py       # the actual science, in three sections (A/B/C below)
  erosion_initialization.py  # add_erosion_tasks(p) + task tree builders
  erosion_utils.py           # generic raster/plotting helpers shared across all three stages
  erosion_debug_ps.py        # standalone smoke test for Section B only (skips SDR)
```

## Pipeline overview

Three sequential stages, corresponding to `erosion_functions.py`'s Sections
A, B, and C. Equation numbers below match the manuscript.

### Section A — InVEST SDR run (biophysical erosion regulation)
Runs InVEST's Sediment Delivery Ratio (SDR) model globally — built on the
Revised Universal Soil Loss Equation (RUSLE) with sediment connectivity
and delivery routing — to produce, per pixel *i*:
- **`Actual_i`** — modelled-realized soil erosion under current land
  cover (t·ha⁻¹·yr⁻¹)
- **`Avoided_i`** — erosion avoided due to current vegetation/land cover
  vs. a degraded baseline (t·ha⁻¹·yr⁻¹)

Inputs: DEM, ESA land cover, erodibility and erosivity rasters, a
biophysical parameter table, and sanitized watershed boundaries.

> SDR is not a site-calibrated process-based erosion model — outputs are
> spatially consistent *indicators* of erosion regulation, not exact
> soil-loss predictions.

### Section B — Prevention-share valuation

**1. Severity threshold (which pixels count).** Rather than one global
cutoff, severity is defined per country *k*:

```
T_k = 2 t·ha⁻¹·yr⁻¹   if country area < 50,000 km² OR mean elevation < 250 m
T_k = 11 t·ha⁻¹·yr⁻¹  otherwise
```

A cropland pixel *p* is "severe" when `USLE_p > T_k`. This is the
**SES-11** (Severe Erosion Scenario) baseline used for headline results.
An **EPS-5** sensitivity scenario relaxes the general threshold to
5 t·ha⁻¹·yr⁻¹ (keeping the 2 t·ha⁻¹·yr⁻¹ small-area/low-elevation
threshold) to test robustness to the severity definition. The
country-conditioned rule matters: at a flat global cutoff, 80 small or
low-lying countries would be dropped entirely despite real erosion
vulnerability.

**2. On-farm prevention share** (eq. 1) — per severe pixel *i*:
```
PS_i^onfarm = Avoided_i / (Avoided_i + Actual_i)      if Actual_i > T_k
PS_i^onfarm = 0                                        otherwise
```
Bounded 0–1: approaches 1 where vegetation prevents nearly all potential
soil loss, 0 where erosion is largely unmitigated. (In code: this is the
`AE / (AE + USLE)` on-farm prevention-share raster.)

**3. Upstream prevention share** (eq. 2, 2a) — per pixel *j*, using D8
flow-routing weights `w_ij` over the hydrologically connected upstream
contributing area Ω(j):
```
UPS(j) = Σ_{i∈Ω(j)} Avoided_i · w_ij  /  Σ_{i∈Ω(j)} (Avoided_i + Actual_i) · w_ij
```
This represents cumulative upstream vegetation's regulation of the
erosive pressure *reaching* downstream cropland — not downstream
sediment deposition or water-quality benefits, which are out of scope
here. Precomputed prior to integration with crop production; evaluated
only within the severe-erosion domain.

**4. Combined effective prevention** (eq. 3) — a probabilistic union that
avoids double-counting two independent protective pathways:
```
PS_i^combined = 1 - (1 - PS_i^onfarm)(1 - PS_i^upstream)
```
Country-level combined totals are therefore **not** a simple sum of
on-farm + upstream — component means aren't directly additive because of
this union formulation.

**5. Crop production baseline** (eq. 4–5) — from SPAM2020 (42 crops,
~10 km resolution): `TotalProd_{c,i} = Yield_{c,i} × Area_{c,i}`,
aggregated to country totals across crops and pixels.

**6. Protected production** (eq. 6–8) — for each pathway
*m ∈ {onfarm, upstream, combined}*:
```
PP_{c,i}^m = PS_i^m × TotalProd_{c,i}
Share_k^m  = PP_k^m / TotalProd_k
```

**7. Elasticity-weighted shock share** (eq. 9) — crop-specific supply
elasticities `ε_c` (from Sartori et al. 2019) convert protected
*production* into protected *value*, since not all crops are equally
yield-sensitive to erosion:
```
Shock_k^m = Σ_c (PP_{c,k}^m · ε_c) / Σ_c TotalProd_{c,k}
```
(A small numerical floor prevents unstable near-zero values.)

**8. Monetary valuation / ERSV** (eq. 10) — two selectable modes, set by
`GEP_EROSION_VALUATION_MODE`:

- **`percrop`** (default, the harmonized headline) values each crop's protected
  production at its own crop value and sums to the national total, removing the
  within-country aggregation approximation:
  ```
  ERSV_k^m = Σ_c value_usd_{c,k} × Share_{c,k}^m × ε_c
  ```
  `value_usd` is the per-crop value from the common `crop_provision` table
  (`in_crop_provision_account` rows only, so byproducts/no-price items are
  excluded at source). FAO items map to SPAM crops via the FAO→SPAM
  correspondence CSV; a pooled FAO code (one item → several SPAM crops) has its
  value split across them by SPAM production tonnes.
- **`shock_x_gpv`** applies the national shock share to national crop Gross
  Production Value (FAOSTAT, constant 2019 USD):
  ```
  ERSV_k^m = GPV_k × Shock_k^m
  ```

The headline uses `percrop`; `shock_x_gpv` is retained as the national-aggregate
comparator (prior basis). See `CHANGELOG.md` for the method decomposition — the crop
corrections and the move to per-crop valuation — with the figures for each step.

Optionally normalized against national GDP (eq. 11, World Bank 2019) for
macroeconomic interpretation:
```
GDPShare_k^m = ERSV_k^m / GDP_k
```

### Section C — Maps & figures
Publication outputs from Section B's country-level results: global
choropleth maps of GEP (Fisher-Jenks classification), raster previews of
the prevention-share layers, top-N country bar charts, and the GEP-vs-GDP
scatter (log-log, colored by income group) showing that absolute value
scales with economy size while *relative* dependence is highest in
smaller agriculture-dependent economies.

## Configuration

Each section has a `configure_*(p)` function
(`configure_sdr`, `configure_prevention_shares`, `configure_maps`) that
overrides that section's module-level path/parameter constants from the
ProjectFlow object `p` before its driver function runs — including
`THRESH_LOW`/`THRESH_HIGH` (the `T_k` thresholds above),
`SMALL_COUNTRY_AREA_KM2`, and `LOW_ELEVATION_MEAN_M`. This is how
`run_erosion.py`'s `p.erosion_*` attributes reach the science code
without threading a config object through every function call — see the
design note at the top of `erosion_functions.py` for why this pattern was
chosen over refactoring the original notebooks' internals.

## Run configuration (environment hooks)

`run_erosion.py` resolves every path and knob from `GEP_EROSION_*` environment
variables, so a run needs no code edits. The main hooks:

| Variable | Purpose |
|---|---|
| `GEP_EROSION_TASK_TREE` | `full` (SDR→valuation→figures, default), `calculation`, `valuation` (valuation only, no SDR/figures), `value_from_shares` (re-value an existing shares table, no biophysics — seconds), or `results` |
| `GEP_EROSION_VALUATION_MODE` | `percrop` (default, harmonized headline) or `shock_x_gpv` |
| `GEP_EROSION_SHARES_LONG_CSV` | `value_from_shares`: an existing run's `country_crop_protected_production_long.csv` to re-value |
| `GEP_EROSION_BASELINE_INTEGRATED_CSV` | `value_from_shares`: that run's `integrated_country_gep.csv` (carries non-valuation context columns through) |
| `GEP_EROSION_VAL_USLE_PATH` / `GEP_EROSION_VAL_AVOIDED_PATH` | actual/avoided-erosion rasters the valuation reads (point at the conditioned-DEM SDR outputs) |
| `GEP_EROSION_UPS_PATH` | upstream prevention-share raster (conditioned flow network) |
| `GEP_EROSION_PERCROP_VALUE_CSV` / `GEP_EROSION_FAO_SPAM_CROSSWALK_CSV` | per-crop value table and FAO→SPAM correspondence (`percrop` mode) |
| `GEP_EROSION_THRESH_HIGH` / `GEP_EROSION_THRESH_LOW` | severity thresholds (SES-11: 11/2; EPS-5: 5/1) |
| `GEP_EROSION_DEM_PATH` / `GEP_EROSION_ELEVATION_PATH` | DEM for the SDR run / DEM for the country-elevation threshold rule |
| `GEP_EROSION_OUTPUT_DIR` | output directory — point at a **fresh** dir per run (the valuation skips if `integrated_country_gep.csv` already exists) |

Ready-to-use SLURM launchers are in `sbatch/`. A valuation-only re-run (no InVEST
SDR) uses `GEP_EROSION_TASK_TREE=valuation` and reads the existing conditioned SDR
outputs via the `VAL_USLE`/`VAL_AVOIDED`/`UPS` hooks.

To re-value a *completed* run without recomputing any biophysics — e.g. apply the
harmonized per-crop values to the finished 1 km prevention shares — use
`value_from_shares`, which reads that run's per-crop protected-production long table
and finishes in seconds (login-node safe, no SLURM):

```bash
GEP_EROSION_TASK_TREE=value_from_shares \
GEP_EROSION_VALUATION_MODE=percrop \
GEP_EROSION_SHARES_LONG_CSV=RESULTS/country_crop_protected_production_long.csv \
GEP_EROSION_BASELINE_INTEGRATED_CSV=RESULTS/integrated_country_gep.csv \
GEP_EROSION_PERCROP_VALUE_CSV=INPUTS/fao_values_2019_production_x_price.csv \
GEP_EROSION_FAO_SPAM_CROSSWALK_CSV=INPUTS/fao_item_spam2020_crop_correspondence.csv \
GEP_EROSION_OUTPUT_DIR=OUT/ses11_harmonized \
python -m global_invest.erosion.run_erosion
```

## Installation

`natcap.invest` (needed for Section A) must be installed via conda-forge,
not pip:
```bash
conda install -c conda-forge natcap.invest=3.17.2
```

`hazelbean` can be finicky to build — some PyPI releases have broken
metadata or Cython incompatibilities with modern Cython (3.x). If a plain
`pip install hazelbean` fails:
```bash
pip install "cython<3.0"
pip install hazelbean --no-build-isolation
```
If that still fails, download the source tarball directly from PyPI and
install from the unpacked directory (bypasses a metadata-version mismatch
bug present in several recent hazelbean releases):
```bash
mkdir -p /tmp/hazelbean_src && cd /tmp/hazelbean_src
curl -L -o hazelbean.tar.gz <tarball-url-from-pypi>
tar xzf hazelbean.tar.gz && cd hazelbean-*
pip install . --no-build-isolation
```

## Running

Full pipeline (SDR → prevention shares → maps):
```bash
python -m global_invest.erosion.run_erosion
```

Smoke-test just the prevention-share stage (skips the SDR run, using
already-computed USLE/avoided-erosion rasters):
```bash
python -m global_invest.erosion.erosion_debug_ps
```

Both scripts set project-level paths as attributes on a `ProjectFlow`
object (`p.erosion_*`) before executing — override these to point at your
actual data rather than editing the science code in
`erosion_functions.py`.

## MSI-specific setup notes

If running on MSI (or any HPC system that auto-loads default environment
modules at login), check `module list` after connecting — a default
Python module can shadow your intended conda environment's `PATH` entry
even after `conda activate <env>`. If `which python` doesn't point into
your env's own `bin/` directory after activating, add to `~/.bashrc`
(after the conda-init block):
```bash
module unload <default-module-name> 2>/dev/null
```

Global SDR runs and the crop-band aggregation step in Section B are
genuinely long-running (multiple hours) and memory-heavy — submit as an
`sbatch` batch job rather than an interactive session, and make sure the
batch script explicitly sources conda's shell init before activating an
environment:
```bash
source /path/to/conda/etc/profile.d/conda.sh
conda activate gep_InVEST
```
(a plain `conda activate` inside a non-interactive `sbatch` script will
silently fall through to the base environment otherwise).

## Known issues / TODO

- Several generic raster/plotting helpers in `erosion_utils.py` are likely
  shared with other GEP service modules — candidates for a future shared
  `global_invest.utils` or upstreaming into `hazelbean`.
