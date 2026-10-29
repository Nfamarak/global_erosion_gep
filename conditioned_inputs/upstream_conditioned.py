#!/usr/bin/env python3
"""
upstream_conditioned.py -- recompute the upstream prevention-share raster on a
HYDROLOGICALLY CONDITIONED flow network (HydroSHEDS / MERIT-Hydro), instead of
deriving D8 from the coarse unconditioned DEM.

This is "Option L": it fixes the drainage pathways Reviewer 2 flagged WITHOUT a
full global SDR re-run. It reuses the existing SDR erosion rasters (avoided /
potential, ~6.45 km), resamples them onto the conditioned flow grid, accumulates
them along the validated network, and writes a new upstream prevention share --
a drop-in replacement for upstream_prevention_share.tif.

Method (identical in form to the original, only the flow network changes):
    UPS = flow_accumulated(avoided) / flow_accumulated(potential)
Both accumulated on the SAME conditioned D8 network, so pixel area cancels and
the result is a 0-1 share. Since avoided + actual = potential (RKLS), this is the
manuscript's eq. (2a).

Pipeline:
    1. remap_flowdir.py : HydroSHEDS/ESRI dir -> pygeoprocessing D8 encoding.
    2. this script      : accumulate the erosion rasters on that network.
    3. (optional)       : resample the resulting share back to the analysis grid
                          (~6.45 km) to feed the existing valuation unchanged.

Usage:
    python -I upstream_conditioned.py \
        --flowdir   flowdir_pgp.tif \
        --avoided   avoided_erosion_2019_revised_feb_13.tif \
        --potential usle_2019_revised_feb_13.tif \
        --out       upstream_prevention_share_conditioned.tif \
        [--analysis-template usle_on_analysis_grid.tif]   # resample result to it

NOTE on potential vs actual: the original upstream accumulation divides by the
POTENTIAL (bare-soil, RKLS) erosion. If your file is 'usle' (actual) rather than
RKLS, pass potential = avoided + actual (they are algebraically equal). Confirm
which raster you have before running (see --potential-is-actual).

Requires: pygeoprocessing, rasterio, numpy
"""
import argparse, os, sys, tempfile
import numpy as np
try:
    import rasterio
    from rasterio.warp import reproject, Resampling
    import pygeoprocessing as pgp
    import pygeoprocessing.routing as routing
except ImportError as e:
    sys.exit(f"missing dependency ({e}). Needs pygeoprocessing, rasterio, numpy "
             "(use the same conda env as the SDR run, e.g. gep_InVEST).")


def resample_to(src_path, like_path, dst_path, resampling):
    """Resample src onto the grid of like_path (same CRS/transform/shape)."""
    with rasterio.open(like_path) as like:
        dst_crs, dst_t, W, H = like.crs, like.transform, like.width, like.height
    with rasterio.open(src_path) as src:
        ndv = src.nodata if src.nodata is not None else -9999.0
        dst = np.full((H, W), ndv, dtype="float32")
        reproject(source=rasterio.band(src, 1), destination=dst,
                  src_transform=src.transform, src_crs=src.crs, src_nodata=ndv,
                  dst_transform=dst_t, dst_crs=dst_crs, dst_nodata=ndv,
                  resampling=resampling, num_threads=4)
        prof = dict(driver="GTiff", height=H, width=W, count=1, dtype="float32",
                    crs=dst_crs, transform=dst_t, nodata=ndv, compress="deflate",
                    tiled=True, BIGTIFF="YES")
    with rasterio.open(dst_path, "w", **prof) as d:
        d.write(dst, 1)
    return dst_path, ndv


def nonneg_weight(src_path, dst_path):
    """Weight raster for flow accumulation: nodata/negatives -> 0 (not routed as mass)."""
    with rasterio.open(src_path) as s:
        a = s.read(1).astype("float64"); ndv = s.nodata
        prof = s.profile.copy()
    a = np.where(np.isfinite(a) & (a != ndv) & (np.abs(a) < 1e30), np.maximum(a, 0.0), 0.0)
    prof.update(dtype="float32", nodata=-1.0, compress="deflate", tiled=True, BIGTIFF="YES")
    with rasterio.open(dst_path, "w", **prof) as d:
        d.write(a.astype("float32"), 1)
    return dst_path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--flowdir", required=True, help="pygeoprocessing-encoded D8 (from remap_flowdir.py)")
    ap.add_argument("--avoided", required=True)
    ap.add_argument("--potential", required=True, help="potential/RKLS erosion (bare soil)")
    ap.add_argument("--potential-is-actual", action="store_true",
                    help="set if --potential is ACTUAL (USLE); then potential = avoided + actual")
    ap.add_argument("--out", required=True)
    ap.add_argument("--analysis-template", default=None,
                    help="optional raster whose grid the final share is resampled to (~6.45 km)")
    ap.add_argument("--workdir", default=None)
    args = ap.parse_args()

    work = args.workdir or tempfile.mkdtemp(prefix="ups_cond_")
    os.makedirs(work, exist_ok=True)
    print("[work]", work)

    fd = args.flowdir
    # 1. erosion rasters -> onto the flow grid (nearest preserves the rate; grids differ)
    print("[resample] erosion rasters onto conditioned flow grid")
    avo_g, _ = resample_to(args.avoided, fd, os.path.join(work, "avo_on_fd.tif"), Resampling.nearest)
    pot_g, _ = resample_to(args.potential, fd, os.path.join(work, "pot_on_fd.tif"), Resampling.nearest)

    if args.potential_is_actual:
        # potential = avoided + actual
        with rasterio.open(avo_g) as A, rasterio.open(pot_g) as P:
            a = A.read(1).astype("float64"); p = P.read(1).astype("float64"); prof = P.profile
        p = np.where(np.isfinite(a) & np.isfinite(p), np.maximum(a, 0) + np.maximum(p, 0), p)
        with rasterio.open(pot_g, "w", **prof) as d:
            d.write(p.astype("float32"), 1)

    # 2. weights (nonneg) + flow accumulation on the conditioned network
    print("[accumulate] flow_accumulation_d8 on conditioned network")
    avo_w = nonneg_weight(avo_g, os.path.join(work, "avo_w.tif"))
    pot_w = nonneg_weight(pot_g, os.path.join(work, "pot_w.tif"))
    acc_avo = os.path.join(work, "acc_avo.tif"); acc_pot = os.path.join(work, "acc_pot.tif")
    routing.flow_accumulation_d8((fd, 1), acc_avo, weight_raster_path_band=(avo_w, 1))
    routing.flow_accumulation_d8((fd, 1), acc_pot, weight_raster_path_band=(pot_w, 1))

    # 3. share = acc_avoided / acc_potential, clipped to [0,1]
    print("[share] UPS = acc_avoided / acc_potential")
    with rasterio.open(acc_avo) as A, rasterio.open(acc_pot) as P:
        na = A.read(1).astype("float64"); np_ = P.read(1).astype("float64"); prof = A.profile
    with np.errstate(divide="ignore", invalid="ignore"):
        share = np.where(np_ > 0, na / np_, 0.0)
    share = np.clip(np.where(np.isfinite(share), share, 0.0), 0.0, 1.0).astype("float32")
    share_path = os.path.join(work, "ups_share_fine.tif")
    prof.update(dtype="float32", nodata=-9999.0, compress="deflate", tiled=True, BIGTIFF="YES")
    with rasterio.open(share_path, "w", **prof) as d:
        d.write(share, 1)

    # 4. optional: resample the share to the analysis grid for the existing valuation
    if args.analysis_template:
        print("[resample] share -> analysis grid (mean)")
        resample_to(share_path, args.analysis_template, args.out, Resampling.average)
    else:
        os.replace(share_path, args.out)
    print(f"[done] wrote {args.out}")
    print("Next: validate against HydroRIVERS, reproduce the Danube/Elbe cases, then "
          "point p.erosion_upstream_prevention_share_path at this file and re-run Section B only.")

if __name__ == "__main__":
    main()
