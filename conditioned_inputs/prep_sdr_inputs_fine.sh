#!/bin/bash
# prep_sdr_inputs_fine.sh -- build aligned SDR inputs at a finer grid for Option F.
# Downsamples the HydroSHEDS 3s conditioned DEM and aligns K, R, LULC to one
# EPSG:8857 grid at PIX metres. Run on MSI in the gep_InVEST env (GDAL on PATH).
#
# Edit the paths + PIX, then: bash prep_sdr_inputs_fine.sh
set -euo pipefail

# ---- target grid ----
EPSG=8857
PIX=1000                      # metres. 1000 = ~1 km (pragmatic); 500 = stretch (very heavy)
XMIN=-17300000; XMAX=17300000; YMIN=-7000000; YMAX=8600000   # Equal Earth land bbox, snapped by -tap
BOUNDS="$XMIN $YMIN $XMAX $YMAX"
CREATE=(-co TILED=YES -co BIGTIFF=YES -co COMPRESS=DEFLATE -co NUM_THREADS=ALL_CPUS)

# ---- inputs (edit) ----
# Merge the conditioned DEM continents first, e.g.:
#   gdalbuildvrt cond_dem_3s.vrt /scratch.../hyd_*_con_3s.tif
COND_DEM_SRC=./cond_dem_3s.vrt                # HydroSHEDS 3s conditioned DEM (merged)
K_SRC=/projects/standard/jajohns/shared/sediment_gep/sediment_feb_2026/inputs_v2/sdr/erodibility_30s_reproj.tif
R_SRC=/projects/standard/jajohns/shared/sediment_gep/sediment_feb_2026/inputs_v2/sdr/erosivity_30s_reproj.tif
LULC_SRC=/projects/standard/jajohns/shared/sediment_gep/sediment_feb_2026/inputs_v2/sdr/lulc_esa_2019_int_reproj.tif
OUT=${OUT:-/scratch.global/$USER/erosion_optF_${PIX}m/aligned}; mkdir -p "$OUT"

warp () {  # warp <src> <dst> <resample>
  gdalwarp -t_srs EPSG:$EPSG -tr $PIX $PIX -te $BOUNDS -r "$3" -tap -overwrite \
    "${CREATE[@]}" "$1" "$2"
  echo "[warp] $(basename "$1") -> $(basename "$2") ($3)"
}

# Conditioned DEM: continuous -> bilinear (downsample 3s -> PIX keeps valley structure)
warp "$COND_DEM_SRC" "$OUT/dem_cond_${PIX}m_8857.tif" bilinear
# Erodibility / erosivity: continuous -> bilinear
warp "$K_SRC" "$OUT/erodibility_${PIX}m_8857.tif" bilinear
warp "$R_SRC" "$OUT/erosivity_${PIX}m_8857.tif"   bilinear
# Land cover: categorical -> mode (majority)
warp "$LULC_SRC" "$OUT/lulc_esa_2019_${PIX}m_8857.tif" mode

echo "done -> $OUT"
echo "Point run_erosion.py's p.erosion_dem_path / erodibility / erosivity / lulc at these,"
echo "set a fresh GEP_EROSION_*_OUTPUT_DIR + RUN_TAG, and submit as a LONG sbatch."
echo "Biophysical table and watersheds stay as-is."
