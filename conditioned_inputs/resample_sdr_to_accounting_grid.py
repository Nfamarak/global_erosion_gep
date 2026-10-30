#!/usr/bin/env python3
"""
resample_sdr_to_accounting_grid.py

Resample the conditioned-DEM SDR outputs (USLE actual erosion and avoided erosion,
produced at ~1 km on the HydroSHEDS-conditioned grid) onto the accounting grid used
by the valuation, so the valuation runs at the intended accounting resolution rather
than at the native SDR resolution.

The accounting grid is defined by a template raster -- the baseline erosion raster
`usle_2019_revised_feb_13.tif` -- which fixes the CRS, pixel size, extent and pixel
alignment. Confirmed grid: EPSG:3857 (Web Mercator), 6,446.75 m, 6217 x 3968. Pass
that raster as --template so the output grid is reproduced exactly.
NOTE: the valuation then reprojects these rasters to the equal-area Equal Earth
projection (EPSG:8857) before the per-pixel-area / tonnes conversion
(erosion_functions.py: ANALYSIS_EPSG = 8857), so the monetary account is area-correct
even though this stored/resampled grid is Web Mercator.

Resampling method: USLE and avoided erosion are INTENSIVE quantities (t ha-1 yr-1),
so they are resampled by AREA-WEIGHTED AVERAGE (rasterio Resampling.average). This is
the same convention the valuation enforces internally
(erosion_functions.py: RESAMPLE_USLE_AVOID = Resampling.average). Extensive quantities
such as harvested area would instead use Resampling.sum to conserve totals; this
script is only for the two intensive erosion rasters.

Pipeline position: run this AFTER the SDR model has produced the native 1 km outputs
and BEFORE the valuation (run_erosion.py / erosion_revalue_sdr.py). Point the
valuation's GEP_EROSION_VAL_USLE_PATH / GEP_EROSION_VAL_AVOIDED_PATH at the outputs.

Usage:
    python resample_sdr_to_accounting_grid.py \
        --template  .../inputs_v2/erosion_gep/usle_2019_revised_feb_13.tif \
        --usle-src  .../sdr_output/usle_conddem1km_native.tif \
        --avoided-src .../sdr_output/avoided_erosion_conddem1km_native.tif \
        --out-dir   .../sdr_on_accounting_grid

GDAL equivalent (per file; -tr/-te read from the template with gdalinfo):
    gdalwarp -t_srs <template CRS> -tr <xres> <yres> -te <xmin ymin xmax ymax> \
        -r average -tap -overwrite usle_conddem1km_native.tif usle_conddem1km_2019.tif
"""
import argparse
import os

import rioxarray as rxr
from rasterio.enums import Resampling


def resample_match(src_path, template_da, dst_path):
    da = rxr.open_rasterio(src_path, masked=True).squeeze()
    out = da.rio.reproject_match(template_da, resampling=Resampling.average)
    os.makedirs(os.path.dirname(dst_path) or ".", exist_ok=True)
    out.rio.to_raster(dst_path)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--template", required=True,
                    help="raster that defines the accounting grid "
                         "(usle_2019_revised_feb_13.tif): CRS, pixel size, extent, alignment")
    ap.add_argument("--usle-src", required=True, help="native ~1 km USLE actual-erosion raster")
    ap.add_argument("--avoided-src", required=True, help="native ~1 km avoided-erosion raster")
    ap.add_argument("--out-dir", required=True, help="output directory")
    ap.add_argument("--usle-name", default="usle_conddem1km_2019.tif")
    ap.add_argument("--avoided-name", default="avoided_erosion_conddem1km_2019.tif")
    args = ap.parse_args()

    tmpl = rxr.open_rasterio(args.template, masked=True).squeeze()
    print(f"accounting grid (from template): CRS={tmpl.rio.crs}  "
          f"res={tmpl.rio.resolution()}  shape={tuple(tmpl.shape)}")

    for label, src, name in [("USLE", args.usle_src, args.usle_name),
                             ("avoided", args.avoided_src, args.avoided_name)]:
        dst = os.path.join(args.out_dir, name)
        resample_match(src, tmpl, dst)
        print(f"[{label}] {src}  ->  {dst}   (Resampling.average)")

    print("done.")


if __name__ == "__main__":
    main()
