#!/bin/bash
# align_inputs_to_grid.sh -- reproject/align acquired rasters to the analysis grid.
# Target: EPSG:8857 (Equal Earth), ~500 m pixels. Run on MSI (GDAL in the conda env).
#
# Produces grid-aligned inputs for the re-run. The DEM/flow-direction alignment is
# the critical piece (Option L and F); K/R/LULC are only needed for Option F.
#
# Usage: edit the paths below, then: bash align_inputs_to_grid.sh
set -euo pipefail

# ---- target grid ----
EPSG=8857
PIX=500                      # metres
# Land extent in EPSG:8857 metres (whole-globe land; tighten to your watersheds for speed).
# Equal Earth x in ~[-17.3e6, 17.3e6], y in ~[-8.6e6, 8.6e6]. Snap to PIX.
XMIN=-17300000; XMAX=17300000; YMIN=-7000000; YMAX=8600000
BOUNDS="$XMIN $YMIN $XMAX $YMAX"
CREATE=(-co TILED=YES -co BIGTIFF=YES -co COMPRESS=DEFLATE -co NUM_THREADS=ALL_CPUS)

# ---- inputs (edit) ----
HYD_CON=./hydrosheds_15s/hyd_glo_con_15s.tif     # conditioned DEM (Option L & F)
HYD_DIR=./hydrosheds_15s/hyd_glo_dir_15s.tif     # drainage direction (Option L)
R_FACTOR=./gloreda/GlobalR_factor.tif            # erosivity (Option F)
K_FACTOR=./glosem/Global_K_factor.tif            # erodibility (Option F)
LULC_ESA=./lulc_esa_2019_int_reproj.tif          # you already have this (Option F)
OUT=./aligned_500m; mkdir -p "$OUT"

warp () {  # warp <src> <dst> <resample>
  local src="$1" dst="$2" rs="$3"
  gdalwarp -t_srs EPSG:$EPSG -tr $PIX $PIX -te $BOUNDS -r "$rs" \
    -tap -overwrite "${CREATE[@]}" "$src" "$dst"
  echo "[warp] $src -> $dst ($rs)"
}

# --- DEM: continuous -> bilinear ---
warp "$HYD_CON" "$OUT/dem_con_500m_8857.tif" bilinear

# --- Flow direction: CATEGORICAL -> nearest ONLY (never bilinear/average) ---
# NOTE: HydroSHEDS 'dir' uses ESRI pow-of-two D8 (1,2,4,8,16,32,64,128; 0=sink, 255=ocean).
# pygeoprocessing.routing expects its own 0-7 D8 convention, so remap the codes
# AFTER warping (see remap_flowdir.py). Reprojecting a flow-direction raster across
# CRS is itself lossy; prefer routing in the DEM's native CRS, or keep PIX close to
# native (~500 m) and validate against HydroRIVERS before trusting it.
warp "$HYD_DIR" "$OUT/flowdir_500m_8857_esri.tif" near

# --- Option F only: K / R / LULC ---
[ -f "$R_FACTOR" ] && warp "$R_FACTOR" "$OUT/erosivity_500m_8857.tif"   bilinear || echo "[skip] R-factor"
[ -f "$K_FACTOR" ] && warp "$K_FACTOR" "$OUT/erodibility_500m_8857.tif" bilinear || echo "[skip] K-factor"
[ -f "$LULC_ESA" ] && warp "$LULC_ESA" "$OUT/lulc_esa_2019_500m_8857.tif" mode   || echo "[skip] LULC"

echo "done -> $OUT"
echo "Validate the flow network against observed hydrography (HydroRIVERS) before use,"
echo "and remap the flow-direction codes with remap_flowdir.py if feeding pygeoprocessing."
