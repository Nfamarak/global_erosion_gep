#!/usr/bin/env python3
"""
dem_to_flowdir.py -- derive a pygeoprocessing D8 flow-direction raster from a
HYDROLOGICALLY CONDITIONED DEM (HydroSHEDS v1 'con', 3 arc-sec / ~90 m).

Because the DEM is already conditioned (pits filled, valleys carved to match real
drainage), running fill_pits -> flow_dir_d8 on it reproduces the true river
network -- this is the step that fixes Reviewer 2's "incorrect drainage pathways".
The output feeds upstream_conditioned.py directly (no remap_flowdir.py needed on
this path -- remap is only for an externally-supplied ESRI flow-direction raster).

Resolution / compute note:
  Native 3 arc-sec (~90 m) routing is accurate but heavy. For the GLOBAL account,
  pass --downsample N to route at ~N*90 m (e.g. --downsample 5 -> ~450 m), which
  keeps the conditioned valley structure while making the global run tractable.
  For the Danube/Elbe DEMONSTRATION, clip the DEM to those basins first and route
  at native 90 m (small area, no downsample).

Usage:
    # regional demo, native 90 m (clip DEM to the basin first with gdalwarp -cutline)
    python -I dem_to_flowdir.py --dem hyd_eu_con_3s.tif --out flowdir_pgp_eu.tif

    # global/continental, ~450 m for tractability
    python -I dem_to_flowdir.py --dem hyd_eu_con_3s.tif --out flowdir_pgp_eu.tif --downsample 5

Then:
    python -I upstream_conditioned.py --flowdir flowdir_pgp_eu.tif \
        --avoided <avoided.tif> --potential <usle.tif> --potential-is-actual \
        --out upstream_prevention_share_conditioned.tif \
        --analysis-template <raster on your 6.45 km grid>

Requires: pygeoprocessing, rasterio, numpy (same conda env as the SDR run).
"""
import argparse, os, sys, tempfile
try:
    import rasterio
    from rasterio.enums import Resampling
    import pygeoprocessing.routing as routing
except ImportError as e:
    sys.exit(f"missing dependency ({e}); use the gep_InVEST env.")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dem", required=True, help="conditioned DEM GeoTIFF (HydroSHEDS 'con')")
    ap.add_argument("--out", required=True, help="output pygeoprocessing D8 flow-direction raster")
    ap.add_argument("--downsample", type=int, default=1,
                    help="integer factor to coarsen the DEM before routing (1 = native ~90 m)")
    ap.add_argument("--workdir", default=None)
    args = ap.parse_args()
    work = args.workdir or tempfile.mkdtemp(prefix="dem2fd_")
    os.makedirs(work, exist_ok=True)

    dem = args.dem
    if args.downsample > 1:
        # average-downsample the conditioned DEM (keeps valley structure better than nearest)
        ds = os.path.join(work, "dem_ds.tif")
        with rasterio.open(args.dem) as src:
            W = max(1, src.width // args.downsample)
            H = max(1, src.height // args.downsample)
            data = src.read(1, out_shape=(H, W), resampling=Resampling.average)
            t = src.transform * src.transform.scale(src.width / W, src.height / H)
            prof = src.profile.copy()
            prof.update(width=W, height=H, transform=t, compress="deflate",
                        tiled=True, BIGTIFF="YES")
        with rasterio.open(ds, "w", **prof) as d:
            d.write(data, 1)
        dem = ds
        print(f"[downsample] {args.downsample}x -> {W}x{H}")

    filled = os.path.join(work, "filled.tif")
    print("[fill_pits]")
    routing.fill_pits((dem, 1), filled)
    print("[flow_dir_d8] -> pygeoprocessing encoding")
    routing.flow_dir_d8((filled, 1), args.out)
    print(f"[done] wrote {args.out}")
    print("Feed this to upstream_conditioned.py (skip remap_flowdir.py on the DEM path).")


if __name__ == "__main__":
    main()
