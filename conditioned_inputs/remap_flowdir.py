#!/usr/bin/env python3
"""
remap_flowdir.py -- convert a HydroSHEDS / ESRI D8 flow-direction raster to the
pygeoprocessing.routing D8 encoding, so it can drive flow_accumulation_d8 directly.

HydroSHEDS 'dir' uses the ESRI power-of-two D8 convention:
    1=E  2=SE  4=S  8=SW  16=W  32=NW  64=N  128=NE
with special values: 0 = river mouth (outlet to ocean), -1 = inland sink,
247/255 = ocean / no-data (varies by product; check the raster's nodata).

pygeoprocessing.routing.flow_dir_d8 emits codes 0-7 (counter-clockwise from East):
    0=E 1=NE 2=N 3=NW 4=W 5=SW 6=S 7=SE
flow_accumulation_d8 expects exactly that encoding, so we remap and set every
sink / mouth / ocean / nodata cell to the output nodata (pygeoprocessing treats
nodata as a flow sink, which is what we want at outlets and coastlines).

Usage:
    python -I remap_flowdir.py --in hyd_dir_15s_8857.tif --out flowdir_pgp.tif
Requires: rasterio, numpy
"""
import argparse, sys
import numpy as np
try:
    import rasterio
except ImportError:
    sys.exit("pip install rasterio numpy")

# ESRI code -> pygeoprocessing code
ESRI_TO_PGP = {1:0, 128:1, 64:2, 32:3, 16:4, 8:5, 4:6, 2:7}
PGP_NODATA = 255

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sink-values", default="0,-1,247,255",
                    help="comma list of ESRI values to treat as sink/ocean/nodata")
    args = ap.parse_args()
    sinks = set(int(x) for x in args.sink_values.split(","))

    with rasterio.open(args.inp) as src:
        a = src.read(1)
        src_nodata = src.nodata
        prof = src.profile.copy()

    out = np.full(a.shape, PGP_NODATA, dtype=np.uint8)
    for esri, pgp in ESRI_TO_PGP.items():
        out[a == esri] = pgp
    # force sinks / ocean / nodata to PGP nodata
    for s in sinks:
        out[a == s] = PGP_NODATA
    if src_nodata is not None:
        out[a == src_nodata] = PGP_NODATA

    n_valid = int((out != PGP_NODATA).sum())
    n_total = out.size
    print(f"[remap] valid flow cells: {n_valid:,} / {n_total:,} "
          f"({100*n_valid/n_total:.1f}%)")
    codes, counts = np.unique(out, return_counts=True)
    print("[remap] pgp code histogram:", dict(zip(codes.tolist(), counts.tolist())))

    prof.update(dtype="uint8", nodata=PGP_NODATA, compress="deflate", tiled=True,
                BIGTIFF="YES")
    with rasterio.open(args.out, "w", **prof) as dst:
        dst.write(out, 1)
    print(f"[remap] wrote {args.out}")

if __name__ == "__main__":
    main()
