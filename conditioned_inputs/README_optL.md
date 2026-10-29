# Option L — re-route the upstream prevention share on a conditioned flow network

Fixes Reviewer 2's "incorrect drainage pathways" **without a full global SDR
re-run**. Reuses your existing ~6.45 km SDR erosion rasters; only the upstream
flow network changes (to HydroSHEDS, which is validated against observed
hydrography).

## Steps
1. **Get the flow direction.** HydroSHEDS Flow Direction raster (ESRI D8
   encoding: 1=E,2=SE,4=S,8=SW,16=W,32=NW,64=N,128=NE, 0=sink).
   - **For the global account: use HydroSHEDS v1 at 15 arc-sec (~500 m)** — tractable
     globally. (v2 is 1 arc-sec/~30 m; a global 30 m flow accumulation is a very
     heavy job — reserve v2 for the regional Danube/Elbe demonstration below.)
   - Reproject/snap it to your analysis grid with `align_inputs_to_grid.sh` (near).
2. **Remap the codes:** `python -I remap_flowdir.py --in flowdir_8857.tif --out flowdir_pgp.tif`
   (ESRI power-of-two → pygeoprocessing 0–7; sinks/ocean → nodata).
3. **Recompute the upstream share:**
   ```
   python -I upstream_conditioned.py \
     --flowdir flowdir_pgp.tif \
     --avoided avoided_erosion_2019_revised_feb_13.tif \
     --potential usle_2019_revised_feb_13.tif --potential-is-actual \
     --out upstream_prevention_share_conditioned.tif \
     --analysis-template <a raster on your ~6.45 km analysis grid>
   ```
   (`--potential-is-actual` because your file is USLE/actual; the script forms
   potential = avoided + actual, which equals RKLS.)
4. **Validate** the new network against HydroSHEDS RIV (river vectors) and
   **reproduce the Danube/Elbe cases** the reviewer sent — strongest evidence you
   fixed it. For this regional check, v2 30 m flow direction on just those basins
   is ideal.
5. **Re-run Section B only:** point `p.erosion_upstream_prevention_share_path` at
   `upstream_prevention_share_conditioned.tif` and re-run (fast — no SDR).

## Honest caveats
- The *effective* resolution of the erosion values is still ~6.45 km; this fixes
  the flow **connections**, not the erosion input resolution. That is exactly R2's
  routing objection, so it is the right fix for Path i / the reframed upstream
  claim — but it is not the full ~500 m re-run (Option F).
- Reprojecting a flow-direction raster across CRS is lossy. Prefer routing in the
  flow raster's native CRS if feasible, or keep the analysis pixel near the flow
  raster's native size and validate before trusting it.
- `upstream_conditioned.py` disaggregates the coarse erosion onto the fine flow
  grid with nearest resampling (preserves the t/ha/yr rate); because both numerator
  and denominator are accumulated the same way, pixel area cancels (eq. 2a holds).
