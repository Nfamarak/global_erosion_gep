#!/bin/bash
# download_hydrosheds.sh  --  fetch HydroSHEDS 15 arc-sec conditioned DEM + flow direction.
# Run on MSI (open network) or your laptop. HydroSHEDS v1 core products are open access.
#
# IMPORTANT: verify the exact file URLs on the HydroSHEDS Core Downloads page
# (https://www.hydrosheds.org/hydrosheds-core-downloads) before running -- the file
# server layout under data.hydrosheds.org is occasionally reorganized. The names
# below follow the standard v1 convention: hyd_<region>_<layer>_15s.zip
#   region: glo (global) | af as au eu na sa (continents)
#   layer : con (conditioned DEM) | dir (drainage direction)
set -euo pipefail

OUT=${1:-./hydrosheds_15s}
mkdir -p "$OUT" && cd "$OUT"

BASE="https://data.hydrosheds.org/file/hydrosheds-v1-con"   # conditioned DEM
BASE_DIR="https://data.hydrosheds.org/file/hydrosheds-v1-dir"  # drainage direction

# Global (large). For a land-only run, per-continent zips are smaller -- swap 'glo'
# for the continents you need (af as au eu na sa) and loop.
FILES_CON=( "hyd_glo_con_15s.zip" )
FILES_DIR=( "hyd_glo_dir_15s.zip" )

dl () {  # dl <base> <file>
  local url="$1/$2"
  echo "[dl] $url"
  if command -v wget >/dev/null; then wget -c "$url";
  else curl -L -O "$url"; fi
}

for f in "${FILES_CON[@]}"; do dl "$BASE" "$f"; done
for f in "${FILES_DIR[@]}"; do dl "$BASE_DIR" "$f"; done

echo "[unzip]"
for z in *.zip; do unzip -o "$z"; done

echo "done. Conditioned DEM (*_con_15s.tif) and flow direction (*_dir_15s.tif) are in $OUT"
echo "Next: align_inputs_to_grid.sh to reproject/snap to the EPSG:8857 ~500 m grid."
