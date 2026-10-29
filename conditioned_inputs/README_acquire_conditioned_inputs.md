# Acquiring conditioned inputs for the erosion/upstream re-run

Goal: replace the coarse, unconditioned DEM with a **hydrologically conditioned**
DEM / flow network so the D8 routing reproduces real drainage (the Danube/Elbe
problem Reviewer 2 raised), and (for a full re-run) bring erodibility, erosivity
and ESA land cover to a matching resolution.

> **None of this can be downloaded from the Claude cloud session** (locked network
> + registration walls), and the SDR re-run runs on MSI. Run the steps below on
> MSI (open-access files) or on your laptop → `scp` to MSI (registration-walled
> files). Where a direct URL is uncertain, the script says "verify on the page".

---

## Read this first — two very different levels of effort

**Option L (lighter, recommended first): re-route only, no SDR re-run.**
Keep your existing ~6.45 km SDR erosion rasters (avoided / potential). Recompute
only the **upstream attribution** on a conditioned flow network (HydroSHEDS 15" /
MERIT-Hydro), with the erosion weights disaggregated to that grid. This directly
fixes "incorrect drainage pathways" — the flow connections become correct — with
**only one new input (flow direction)** and **no multi-day global SDR re-run**.
It does not raise the *effective* resolution of the erosion values (still ~6.45 km),
but it answers R2's specific routing objection. Needs a code change in
`accumulate_upstream_prevention_share` (feed it HydroSHEDS flow direction instead
of `fill_pits → flow_dir_d8` on the coarse DEM).

**Option F (full re-run): everything at ~500 m.**
Re-run InVEST SDR globally at ~500 m on a conditioned DEM, with K/R/LULC at
matching resolution, then re-accumulate upstream and re-aggregate. Most defensible,
but **~166× the pixels of your 6.45 km run** → likely days of compute, memory-heavy,
and realistically second-revision-cycle scope. Acquire the full input set below.

Pick L first; escalate to F only if the team needs a quantitative upstream claim.

---

## Target analysis grid

- CRS: **EPSG:8857 (Equal Earth)** — unchanged.
- Pixel: **~500 m** (HydroSHEDS 15 arc-sec ≈ 463 m at the equator; use 500 m for a
  clean grid), vs the current 6,446.75 m. Set `p.erosion_solve_pixel_size_m = 500`.
- For Option L, you only re-grid the **flow direction**; keep erosion at 6.45 km
  and disaggregate inside the upstream routine.

---

## 1. Conditioned DEM / flow direction  (the critical input)

### 1a. HydroSHEDS 15 arc-sec  (~500 m, OPEN, no registration) — recommended
- Products: **Hydrologically Conditioned DEM** (`con`) and **Drainage Direction**
  (`dir`), 15 arc-sec, WGS84.
- Download: the HydroSHEDS **Core Downloads** page (hydrosheds.org) links to an
  open file server (`data.hydrosheds.org`). Global or per-continent zips, e.g.
  `hyd_glo_con_15s.zip`, `hyd_glo_dir_15s.zip` (or per-continent `hyd_af_*`, `hyd_as_*` …).
  Verify the exact filenames/paths on the page — see `download_hydrosheds.sh`.
- HydroSHEDS `dir` uses the ESRI D8 pow-of-two encoding (1,2,4,…,128). The
  upstream routine (pygeoprocessing) uses a different convention — remap on ingest
  (see the note in `align_inputs_to_grid.sh`).

### 1b. MERIT-Hydro 3 arc-sec  (~90 m, finer, REGISTRATION) — for Option F only
- Resolution 3 arc-sec (~90 m); layers include **flow direction** (int8),
  **hydrologically adjusted elevation** (float32), upstream area, HAND.
- Access: fill the Google Form at `hydro.iis.u-tokyo.ac.jp/~yamadai/MERIT_Hydro/`;
  a download password is emailed. Tiles are 5°×5° (6000×6000), packaged in
  30°×30° tars (e.g. `dir_n30w120.tar`). Download only the tars covering your
  land extent, untar, then mosaic + warp (`align_inputs_to_grid.sh`).
- 90 m global SDR is impractical without serious HPC; use MERIT only if routing
  on 500 m HydroSHEDS proves insufficient.

> Both are also Google Earth Engine assets (`WWF/HydroSHEDS/15CONDEM`,
> `WWF/HydroSHEDS/15DIR`, `MERIT/Hydro/v1_0_1`). If you have GEE access, exporting
> a clipped, reprojected raster from GEE is often easier than wrangling tiles.

## 2. Rainfall erosivity (R)  — Option F
- **GloREDa** global R-factor, ~1 km, from **ESDAC** (esdac.jrc.ec.europa.eu,
  "Global Rainfall Erosivity"). Short registration form → download link.
- ~1 km is coarser than 500 m but R varies smoothly; resample (bilinear) to the grid.

## 3. Soil erodibility (K)  — Option F
- **GloSEM K-factor** (~250 m, Borrelli/Panagos) from ESDAC, or derive K from
  **ISRIC SoilGrids** (openly downloadable via its WCS/COG endpoints). ESDAC needs
  the same registration.

## 4. ESA-CCI land cover 2019  — Option F
- You already have `lulc_esa_2019_int_reproj.tif` (300 m). For Option F just
  **resample to the 500 m grid with mode (majority)** — no new download. Native
  source if needed: Copernicus CDS / ESA CCI Land Cover viewer (registration).

---

## Pipeline wiring after acquisition

- Option L: point the upstream routine at the conditioned **flow-direction** raster
  (new `p.erosion_upstream_flowdir_path`) and skip `fill_pits/flow_dir_d8`.
- Option F: set `p.erosion_dem_path` → conditioned DEM, `p.erosion_erodibility_path`,
  `p.erosion_erosivity_path`, `p.erosion_lulc_path` → the 500 m aligned rasters, and
  `p.erosion_solve_pixel_size_m = 500`; then a fresh output dir and a full re-run.

See `align_inputs_to_grid.sh` for the reproject/align step and
`download_hydrosheds.sh` for the open download.
