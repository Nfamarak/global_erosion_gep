# global_erosion_gep

GEP (Global Ecosystem services and Products) erosion / sediment retention
service module, built on [hazelbean](https://github.com/jandrewjohnson/hazelbean)'s
`ProjectFlow` task-tree framework.

**Standalone working copy** while awaiting write access to
`NatCapTEEMs/global_invest_dev`, where this will ultimately live as
`global_invest/erosion/`.

This code implements the analysis described in:

> Dampha, N.K. & Johnson, J. *A Global Gross Ecosystem Product account for
> nature's soil-retention services protecting crop production.*
> Department of Applied Economics, Natural Capital Alliance – The
> Earth-Economy Modelers (NatCap TEEMs), University of Minnesota.
> Manuscript in preparation for Nature Sustainability.

## Purpose

Soil erosion by water damages cropland directly (on-farm yield loss) and
indirectly by degrading downstream water resources and infrastructure
fed by eroded watersheds. Vegetation and land cover regulate this by
stabilizing soils, reducing runoff energy, and limiting sediment
transport — a regulating ecosystem service this module quantifies as an
annual economic flow, consistent with SEEA-EA ecosystem accounting.

The headline result (SES-11 baseline, 2019 USD, 164 countries):
soil-retention services protect an estimated **USD 14.6–29.1 billion/yr**
of global crop production (**~0.52–1.04%** of global crop production
value). Absolute values concentrate in large agricultural economies
(China, India, Indonesia); relative dependence (share of GDP) is highest
in low-income, agriculture-dependent economies (Sierra Leone, Burundi,
Liberia — each exceeding 2% of GDP).

## File structure

Follows the `run / tasks / functions / initialize / utils` convention used
across GEP service modules (per Justin Johnson's 2026-07-07 email):

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

**8. Monetary valuation / GEP** (eq. 10) — applying the shock share to
national crop Gross Production Value (FAOSTAT, constant 2019 USD):
```
GEP_k^m = GPV_k × Shock_k^m
```
Optionally normalized against national GDP (eq. 11, World Bank 2019) for
macroeconomic interpretation:
```
GDPShare_k^m = GEP_k^m / GDP_k
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

## Known data-path quirks

The three original research notebooks this module was built from
hardcoded paths inconsistently:

- **Two different roots.** Section A's SDR run and Sections B/C's
  prevention-share valuation were originally pointed at different
  directories. `run_erosion.py` now points both at the same confirmed
  current location on MSI's Agate cluster
  (`/projects/standard/jajohns/shared/sediment_gep/sediment_feb_2026`),
  but Section B's `usle_path`/`avoided_erosion_path` still default to
  pre-computed files rather than Section A's fresh output — wire these
  together for a true end-to-end run once both stages share one project
  layout.
- **`RUN_TAG` mismatch.** The original maps notebook read from an
  `eps5_...`-tagged output directory that didn't match the
  `ses11_...`-tagged directory the prevention-share notebook actually
  wrote to. `configure_maps()` now defaults to `ses11`; confirm this is
  the run you want mapped before trusting Section C's output.

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

- Wire Section A's SDR output directory into Section B's
  USLE/avoided-erosion input paths for a true end-to-end run.
- Confirm the `ses11` vs `eps5` run-tag mismatch against whichever run is
  actually current before trusting Section C's maps.
- Consider surfacing `EPS-5` as a selectable scenario (not just SES-11)
  in `configure_prevention_shares(p)`, since the manuscript reports it as
  a formal sensitivity analysis, not just an alternate default.
- Several generic raster/plotting helpers in `erosion_utils.py` are
  likely duplicated across other GEP contributors' code — candidates for
  a future shared `global_invest.utils` or upstreaming into `hazelbean`.
