"""
preflight.py -- run this BEFORE submitting the erosion GEP run.

Checks every import, input path, and code version the module needs, verifies
the 2026-08-27 elasticity fix is live (maize resolves to 0.30, not 0.08), and
warns if the output dir already holds an integrated_country_gep.csv (which would
make the valuation task SKIP and return the pre-fix numbers). Costs seconds;
saves a queue slot.

    conda activate gep_InVEST
    python -m global_invest.erosion.msi.preflight

Exit code 0 if ready, 1 otherwise.
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

OK, WARN, BAD = "  [OK]  ", "  [WARN]", "  [FAIL]"
problems, warnings_ = [], []


def check(label, path, required=True):
    p = Path(path)
    if p.exists():
        if p.is_file():
            print(f"{OK} {label}: {p}  ({p.stat().st_size/1e6:,.1f} MB)")
        else:
            print(f"{OK} {label}: {p}  ({sum(1 for _ in p.iterdir())} entries)")
        return True
    (problems if required else warnings_).append(label)
    print(f"{BAD if required else WARN} {label}: {'MISSING' if required else 'missing (optional)'}  {p}")
    return False


print("=" * 78)
print("EROSION GEP PREFLIGHT")
print("=" * 78)

# --------------------------------------------------------------- imports ---
print("\n--- imports ---")
try:
    import rasterio, geopandas, shapely, matplotlib
    print(f"{OK} numpy {np.__version__} / pandas {pd.__version__}")
    print(f"{OK} rasterio {rasterio.__version__} / geopandas {geopandas.__version__}")
except Exception as e:
    print(f"{BAD} core geospatial stack: {e}")
    sys.exit(1)

for mod in ("hazelbean", "natcap.invest"):
    try:
        __import__(mod)
        print(f"{OK} {mod}")
    except Exception as e:
        # natcap.invest is only needed for Section A (SDR); valuation-only runs
        # do not import it.
        print(f"{WARN} {mod} not importable ({e}); needed only for the SDR step")
        warnings_.append(mod)

try:
    from global_invest.erosion import erosion_functions as ef
    print(f"{OK} global_invest.erosion imported from {Path(ef.__file__).parent}")
except Exception as e:
    print(f"{BAD} cannot import global_invest.erosion: {e}")
    print("      check PYTHONPATH points at the dir CONTAINING global_invest/")
    sys.exit(1)

# ------------------------------------------------------- module structure ---
print("\n--- module files ---")
pkg = Path(ef.__file__).parent
for f in ("erosion_utils.py", "erosion_tasks.py", "erosion_initialization.py",
          "run_erosion.py", "verify_elasticity_fix.py"):
    check(f, pkg / f)

# --------------------------------------------- THE FIX: elasticity mapping --
print("\n" + "=" * 78)
print("ELASTICITY FIX CHECK (2026-08-27)")
print("=" * 78)
maiz_alias = ef.SPAM_ALIAS_MAP.get("maiz", [])
if "maize (corn)" in [a.lower() for a in maiz_alias]:
    print(f"{OK} corrected alias map present: maiz -> {maiz_alias}")
else:
    print(f"{BAD} BUGGY alias map: maiz -> {maiz_alias} (expected 'maize (corn)' first)")
    problems.append("elasticity alias map")

GEP_ROOT = os.environ.get(
    "GEP_EROSION_GEP_ROOT",
    "/projects/standard/jajohns/shared/sediment_gep/sediment_feb_2026")
ELAST_CSV = Path(os.environ.get(
    "GEP_EROSION_ELASTICITY_CSV",
    Path(GEP_ROOT) / "inputs_v2" / "erosion_gep" / "elasticity_crops_fao_revised.csv"))
if check("elasticity table", ELAST_CSV):
    df = pd.read_csv(ELAST_CSV)
    name_col = next((c for c in df.columns if df[c].dtype == object), df.columns[0])
    val_col = next((c for c in df.columns if c != name_col
                    and pd.api.types.is_numeric_dtype(df[c])), df.columns[-1])
    emap = {str(k).strip().lower(): float(v) for k, v in zip(df[name_col], df[val_col])}

    def resolve(code, fb=0.08):
        for a in ef.SPAM_ALIAS_MAP.get(code, []):
            v = emap.get(a.strip().lower(), np.nan)
            if np.isfinite(v):
                return float(np.clip(v, 0, 1))
        return fb
    maize = resolve("maiz")
    print(f"       maize resolves to {maize:.2f} "
          f"({'OK' if abs(maize - 0.30) < 1e-9 else 'WRONG -- expected 0.30'})")
    if abs(maize - 0.30) > 1e-9:
        problems.append("maize elasticity != 0.30")

# ------------------------------------------------------------------ inputs ---
IN = Path(GEP_ROOT) / "inputs_v2" / "erosion_gep"
SDR_IN = Path(os.environ.get(
    "GEP_EROSION_SDR_ROOT", GEP_ROOT)) / "inputs_v2" / "sdr"
print(f"\n--- inputs (env hooks override the baseline fallbacks) ---")
# Valuation rasters: conditioned SDR outputs when the env hooks are set, else baseline.
check("USLE raster (valuation)",
      Path(os.environ.get("GEP_EROSION_VAL_USLE_PATH", IN / "usle_2019_revised_feb_13.tif")))
check("avoided-erosion raster (valuation)",
      Path(os.environ.get("GEP_EROSION_VAL_AVOIDED_PATH", IN / "avoided_erosion_2019_revised_feb_13.tif")))
check("country boundary", IN / "country_boundary_r250_with_iso3.gpkg")
check("SPAM band map", IN / "spam2020_bandmap.csv")
check("FAO GPV", IN / "faostat_gpv_2019_iso3.csv")
check("FAO prices (fallback)", IN / "faostat_prices_2019_completed_revised.csv")
check("World Bank GDP", IN / "worldbank_gdp_2019.csv")
# SDR inputs: conditioned 1 km layers when the env hooks are set, else baseline.
check("DEM (SDR)",
      Path(os.environ.get("GEP_EROSION_DEM_PATH", SDR_IN / "global_dem_reproj.tif")))
check("LULC (SDR)",
      Path(os.environ.get("GEP_EROSION_LULC_PATH", SDR_IN / "lulc_esa_2019_int_reproj.tif")))
check("erodibility (SDR)",
      Path(os.environ.get("GEP_EROSION_ERODIBILITY_PATH", SDR_IN / "erodibility_30s_reproj.tif")))
check("erosivity (SDR)",
      Path(os.environ.get("GEP_EROSION_EROSIVITY_PATH", SDR_IN / "erosivity_30s_reproj.tif")))
_ups = os.environ.get("GEP_EROSION_UPS_PATH", "")
if _ups:
    check("upstream prevention share", Path(_ups))

# ---------------------------------------------- fresh-output-dir guard ------
print("\n" + "=" * 78)
print("OUTPUT DIR FRESHNESS (avoids the skip-guard returning stale numbers)")
print("=" * 78)
OUT = Path(os.environ.get(
    "GEP_EROSION_OUTPUT_DIR",
    f"/scratch.global/{os.environ.get('USER', 'user')}/erosion_conditioned/prevention_share_output"))
stale = OUT / "integrated_country_gep.csv"
print(f"output dir : {OUT}")
if stale.exists():
    print(f"{BAD} {stale.name} ALREADY EXISTS -- the valuation task will SKIP and")
    print("       return the previous (pre-fix) numbers. Point GEP_EROSION_OUTPUT_DIR")
    print("       at a fresh directory, or move this file aside, before running.")
    problems.append("stale output dir")
else:
    print(f"{OK} no stale integrated_country_gep.csv -- valuation will recompute")

# ----------------------------------------------------------------- verdict --
print("\n" + "=" * 78)
if problems:
    print(f"NOT READY -- {len(problems)} blocking problem(s): {', '.join(problems)}")
    sys.exit(1)
print("READY.")
if warnings_:
    print(f"({len(warnings_)} warning(s): {', '.join(warnings_)})")
sys.exit(0)
