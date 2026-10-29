#!/bin/bash
# download_con_dem_3s.sh -- fetch HydroSHEDS v1 hydrologically CONDITIONED DEM (3s),
# the only resolution it is published at, as continental tiles, then merge to a VRT.
#
# URL pattern (verified 2026-10-27):
#   https://data.hydrosheds.org/file/hydrosheds-v1-con/<region>_con_3s.zip
#   regions: af as au eu na sa  (Africa, Asia, Australasia, Europe+MidEast, N+C America, S America)
#
# Usage:
#   bash download_con_dem_3s.sh                 # all six continents (~16.5 GB) -> global VRT
#   REGIONS="eu" bash download_con_dem_3s.sh    # one continent (smoke test)
set -euo pipefail

OUT=${1:-/scratch.global/$USER/hydrosheds_con_3s}
BASE="https://data.hydrosheds.org/file/hydrosheds-v1-con"
REGIONS=${REGIONS:-"af as au eu na sa"}

mkdir -p "$OUT" && cd "$OUT"

for r in $REGIONS; do
  f="${r}_con_3s.zip"
  echo "[dl] $BASE/$f"
  wget -c "$BASE/$f"
done

echo "[unzip]"
for z in *_con_3s.zip; do unzip -o "$z"; done

echo "[vrt] building merged conditioned-DEM VRT"
mapfile -t TIFS < <(find . -name '*_con_3s.tif' | sort)
if [[ ${#TIFS[@]} -eq 0 ]]; then
  echo "[FATAL] no *_con_3s.tif found after unzip -- check the zip contents."; exit 1
fi
gdalbuildvrt cond_dem_3s.vrt "${TIFS[@]}"

echo "done."
echo "Merged conditioned DEM VRT: $OUT/cond_dem_3s.vrt  (covers: $REGIONS)"
echo "Next: in prep_sdr_inputs_fine.sh set  COND_DEM_SRC=$OUT/cond_dem_3s.vrt  (PIX=1000),"
echo "then: bash prep_sdr_inputs_fine.sh"
