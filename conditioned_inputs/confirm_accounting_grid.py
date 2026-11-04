#!/usr/bin/env python3
"""
confirm_accounting_grid.py

Confirms (1) the authoritative accounting grid, (2) that the archived SDR-on-grid
outputs sit on that grid, and (3) that AREA-AVERAGE resampling is what produced them.

Run in the gep_InVEST env (rasterio + rioxarray + numpy).

    python confirm_accounting_grid.py \
        --template      .../inputs_v2/erosion_gep/usle_2019_revised_feb_13.tif \
        --archived-usle .../erosion_optF_1km/sdr_on_feb_grid/usle_conddem1km_2019.tif \
        --archived-avoided .../erosion_optF_1km/sdr_on_feb_grid/avoided_erosion_conddem1km_2019.tif \
        [--native-usle  .../sdr_output/usle_conddem1km_native.tif] \
        [--native-avoided .../sdr_output/avoided_erosion_conddem1km_native.tif]

The --native-* args are optional; give them to run the strongest check (reproduce the
archived file from the native 1 km output by averaging, then diff).
"""
import argparse
import numpy as np
import rasterio
import rioxarray as rxr
from rasterio.enums import Resampling


def grid_specs(path):
    with rasterio.open(path) as ds:
        epsg = ds.crs.to_epsg() if ds.crs else None
        return dict(path=path, crs=str(ds.crs), epsg=epsg, width=ds.width, height=ds.height,
                    res=(abs(ds.transform.a), abs(ds.transform.e)),
                    bounds=tuple(round(v, 2) for v in ds.bounds),
                    transform=ds.transform)


def same_grid(a, b, res_tol=1e-6):
    return (a["crs"] == b["crs"] and a["width"] == b["width"] and a["height"] == b["height"]
            and abs(a["res"][0] - b["res"][0]) < res_tol and abs(a["res"][1] - b["res"][1]) < res_tol
            and a["transform"].almost_equals(b["transform"], precision=1e-6))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True)
    ap.add_argument("--archived-usle", required=True)
    ap.add_argument("--archived-avoided", required=True)
    ap.add_argument("--native-usle")
    ap.add_argument("--native-avoided")
    a = ap.parse_args()

    # 1) authoritative grid
    t = grid_specs(a.template)
    print("=" * 64)
    print("ACCOUNTING GRID (template =", a.template.split("/")[-1], ")")
    print(f"  CRS            : {t['crs']}  (EPSG:{t['epsg']})")
    print(f"  pixel size     : {t['res'][0]:.3f} x {t['res'][1]:.3f} (CRS units)")
    print(f"  dimensions     : {t['width']} x {t['height']}")
    print(f"  bounds         : {t['bounds']}")
    print("=" * 64)

    # 2) archived outputs on that grid?
    for label, p in [("USLE", a.archived_usle), ("avoided", a.archived_avoided)]:
        g = grid_specs(p)
        ok = same_grid(t, g)
        print(f"[grid] archived {label:8s}: EPSG:{g['epsg']} {g['width']}x{g['height']} "
              f"res={g['res'][0]:.3f} -> {'MATCH' if ok else 'MISMATCH'}")

    # 3) reproduce archived from native by AVERAGE, then diff
    pairs = [("USLE", a.native_usle, a.archived_usle),
             ("avoided", a.native_avoided, a.archived_avoided)]
    any_native = False
    tmpl = rxr.open_rasterio(a.template, masked=True).squeeze()
    for label, nat, arch in pairs:
        if not nat:
            continue
        any_native = True
        repro = rxr.open_rasterio(nat, masked=True).squeeze().rio.reproject_match(
            tmpl, resampling=Resampling.average)
        archd = rxr.open_rasterio(arch, masked=True).squeeze()
        r = repro.values.astype("float64"); x = archd.values.astype("float64")
        m = np.isfinite(r) & np.isfinite(x)
        diff = np.abs(r[m] - x[m])
        denom = np.maximum(np.abs(x[m]), 1e-9)
        rel = diff / denom
        corr = np.corrcoef(r[m], x[m])[0, 1] if m.sum() > 1 else float("nan")
        verdict = "PASS (average reproduces archived)" if (np.nanmax(diff) < 1e-3 or np.nanmedian(rel) < 1e-4) \
                  else "CHECK (differs - archived may use a different method)"
        print(f"[method] {label:8s}: n={m.sum():,}  max|diff|={np.nanmax(diff):.3e}  "
              f"median rel={np.nanmedian(rel):.3e}  corr={corr:.6f}  -> {verdict}")
    if not any_native:
        print("[method] skipped (no --native-* given). Grid checks above still confirm the CRS/resolution.")


if __name__ == "__main__":
    main()
