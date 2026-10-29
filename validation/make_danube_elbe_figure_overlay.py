#!/usr/bin/env python3
"""Danube/Elbe conditioned-network + observed-river (HydroRIVERS) validation overlay."""
import argparse, os, subprocess, tempfile
import numpy as np
if not hasattr(np, "in1d"):
    np.in1d = np.isin
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
import fiona
from pysheds.grid import Grid

ap = argparse.ArgumentParser()
ap.add_argument("--flowdir", required=True)
ap.add_argument("--rivers", required=True, help="HydroRIVERS shapefile")
ap.add_argument("--out", required=True)
ap.add_argument("--min-dis", type=float, default=50.0, help="min DIS_AV_CMS (m3/s) drawn")
ap.add_argument("--bbox", default="6 42 30 55")
a = ap.parse_args()
W, S, E, N = [float(x) for x in a.bbox.split()]

wd = tempfile.mkdtemp(prefix="de_")
clip = os.path.join(wd, "flowdir_clip.tif")
subprocess.run(["gdalwarp", "-t_srs", "EPSG:4326", "-te", str(W), str(S), str(E), str(N),
                "-r", "near", "-overwrite", a.flowdir, clip],
               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

g = Grid.from_raster(clip)
fd = g.read_raster(clip)
acc = np.asarray(g.accumulation(fd, dirmap=(64, 128, 1, 2, 4, 8, 16, 32))).astype(float)

thr = 200
with np.errstate(divide="ignore", invalid="ignore"):
    riv = np.where(acc > thr, np.log10(acc), np.nan)
cmap = LinearSegmentedColormap.from_list("r", ["#6baed6", "#3182bd", "#08519c", "#08306b"])

fig, axes = plt.subplots(1, 2, figsize=(16, 5.6), dpi=170)
for ax in axes:
    ax.set_facecolor("#f4f1ea")
    ax.imshow(riv, extent=[W, E, S, N], origin="upper", cmap=cmap,
              interpolation="nearest", vmin=np.log10(thr), vmax=5.6)
    ax.set_xlim(W, E); ax.set_ylim(S, N)
    ax.set_xlabel("Longitude (deg E)", fontsize=9)
    ax.set_ylabel("Latitude (deg N)", fontsize=9)
    ax.tick_params(labelsize=8)
axes[0].set_title("Conditioned network (HydroSHEDS, 30 arc-sec)", fontsize=12, fontweight="bold")
axes[1].set_title("Validation: conditioned network + observed rivers", fontsize=12, fontweight="bold")

n = 0
with fiona.open(a.rivers) as src:
    for f in src.filter(bbox=(W, S, E, N)):
        p = f.properties if hasattr(f, "properties") else f["properties"]
        d = p.get("DIS_AV_CMS") or 0
        if d < a.min_dis:
            continue
        geom = f.geometry if hasattr(f, "geometry") else f["geometry"]
        gt = geom.type if hasattr(geom, "type") else geom["type"]
        co = geom.coordinates if hasattr(geom, "coordinates") else geom["coordinates"]
        parts = co if gt == "MultiLineString" else [co]
        lw = min(1.8, 0.3 + 0.3 * np.log10(max(d, 1)))
        for part in parts:
            axes[1].plot([c[0] for c in part], [c[1] for c in part],
                         color="#e6550d", lw=lw, alpha=0.85, solid_capstyle="round", zorder=5)
            n += 1
axes[1].legend([Line2D([0], [0], color="#e6550d", lw=2)],
               ["Observed rivers (HydroRIVERS)"], loc="lower left", fontsize=8, framealpha=0.85)
print("overlaid", n, "river segments")

for ax in axes:
    ax.annotate("DANUBE", (20.0, 44.1), color="#08306b", fontsize=12, fontweight="bold",
                ha="center", bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.75))
    ax.annotate("Elbe", (12.3, 52.3), color="#08306b", fontsize=10, fontweight="bold",
                ha="center", bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.75))
plt.subplots_adjust(left=0.05, right=0.99, top=0.9, bottom=0.11, wspace=0.12)
fig.savefig(a.out, dpi=180)
print("wrote", a.out)
