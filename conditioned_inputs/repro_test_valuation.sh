#!/bin/bash
# =====================================================================
# repro_test_valuation.sh
# Reproduction test: re-run ONLY the valuation path (no SDR) against the
# archived conditioned rasters, then diff the fresh integrated_country_gep.csv
# against the archived one.
#   PASS  -> repo reproduces the archived account (nothing to rewrite)
#   FLAG  -> numbers differ; offending countries printed; archive left untouched
#
# Usage:  bash repro_test_valuation.sh            # SES-11 (default)
#         bash repro_test_valuation.sh eps5        # EPS-5 sensitivity
# =====================================================================
set -euo pipefail
source ~/.bashrc; conda activate gep_InVEST     # or gep_erosion

SCEN=${1:-ses11}
case "$SCEN" in
  ses11) THRESH=11; RESDIR=ses11_headline ;;
  eps5)  THRESH=5;  RESDIR=eps5_sensitivity ;;
  *) echo "scenario must be ses11 or eps5"; exit 2 ;;
esac

ARCHIVE=/projects/standard/jajohns/shared/nfamara/erosion_global_gep_final

# Auto-detect the repo root (the dir containing global_invest/erosion/run_erosion.py)
# under the upload location. Prefer the revised repo if several copies exist.
BASE=/users/3/damph002/gep_runs_sdr_floods/sediment
RUN_PY=$(find "$BASE" -type f -path '*global_erosion_gep*/global_invest/erosion/run_erosion.py' 2>/dev/null | head -1)
[ -z "$RUN_PY" ] && RUN_PY=$(find "$BASE" -type f -path '*/global_invest/erosion/run_erosion.py' 2>/dev/null | head -1)
if [ -z "$RUN_PY" ]; then echo "ERROR: could not find run_erosion.py under $BASE"; exit 2; fi
REPO=$(dirname "$(dirname "$(dirname "$RUN_PY")")")
echo "### repo detected: $REPO"
TEST_OUT=/scratch.global/$USER/erosion_reprotest_${SCEN}
ARCHIVE_CSV=$ARCHIVE/results/$RESDIR/integrated_country_gep.csv

rm -rf "$TEST_OUT"; mkdir -p "$TEST_OUT"
cd "$REPO"
export PYTHONPATH="$REPO:${PYTHONPATH:-}"
export MPLBACKEND=Agg

# --- point the valuation at the archived conditioned rasters (QUICK, no SDR) ---
export GEP_EROSION_VAL_USLE_PATH=$ARCHIVE/sdr_outputs_conditioned/usle_conddem1km_2019.tif
export GEP_EROSION_VAL_AVOIDED_PATH=$ARCHIVE/sdr_outputs_conditioned/avoided_erosion_conddem1km_2019.tif
export GEP_EROSION_UPS_PATH=$ARCHIVE/inputs_conditioned/upstream/upstream_prevention_share_optF.tif
export GEP_EROSION_THRESH_HIGH=$THRESH
export GEP_EROSION_THRESH_LOW=2
export GEP_EROSION_ALL_TOUCHED=false
export GEP_EROSION_OUTPUT_DIR=$TEST_OUT          # FRESH -> skip-guard will not short-circuit
export GEP_EROSION_RUN_TAG=reprotest_${SCEN}

echo "### re-running VALUATION ONLY -> $TEST_OUT (threshold=$THRESH)"
python - <<'PY'
import hazelbean as hb
from global_invest.erosion import erosion_initialization, erosion_functions
from global_invest.erosion.run_erosion import set_erosion_paths
import os
p = hb.ProjectFlow()
p.project_name = "gep_erosion_reprotest"
p.project_dir = os.path.expanduser("~/gep_erosion_reprotest")
p.set_project_dir(p.project_dir)
erosion_initialization.add_erosion_tasks(p)   # registers tasks; we do NOT p.execute()
set_erosion_paths(p)
erosion_functions.configure_prevention_shares(p)   # Section B config from the env hooks
erosion_functions.integrate_and_write()            # valuation only -- no InVEST SDR
print("VALUATION DONE ->", erosion_functions.OUT_DIR)
PY

echo "### comparing $TEST_OUT/integrated_country_gep.csv  vs  $ARCHIVE_CSV"
python - "$TEST_OUT/integrated_country_gep.csv" "$ARCHIVE_CSV" <<'PY'
import sys, numpy as np, pandas as pd
new = pd.read_csv(sys.argv[1]).set_index("iso3").sort_index()
old = pd.read_csv(sys.argv[2]).set_index("iso3").sort_index()
cols = ["gep_const2019_usd_combined","gep_const2019_usd_onfarm","gep_const2019_usd_upstream"]
status = "PASS"; out = []
common = new.index.intersection(old.index)
only_new, only_old = new.index.difference(old.index), old.index.difference(new.index)
if len(only_new) or len(only_old):
    status = "FLAG"
    out.append(f"country set differs:  only-new={list(only_new)}  only-archive={list(only_old)}")
REL, ABS = 1e-6, 1.0   # tolerate <$1 and <1e-6 relative (float noise)
for c in cols:
    a = new.loc[common, c].astype(float); b = old.loc[common, c].astype(float)
    d = (a - b).abs(); rel = d / b.abs().replace(0, np.nan)
    bad = (d > ABS) & ((rel > REL) | rel.isna() & (d > ABS))
    if bad.any():
        status = "FLAG"
        worst = pd.DataFrame({"archive": b[bad], "rerun": a[bad], "abs_diff": d[bad]}) \
                  .sort_values("abs_diff", ascending=False).head(10)
        out.append(f"\n{c}: {int(bad.sum())} countries differ. Worst:\n{worst.to_string()}")
out.append("\n--- global totals (USD) ---")
for c in cols:
    out.append(f"{c:32s} rerun={new[c].sum():>18,.0f}  archive={old[c].sum():>18,.0f}  diff={new[c].sum()-old[c].sum():>14,.2f}")
print("\n".join(out))
print("\n==================  RESULT:", status, " ==================")
sys.exit(0 if status == "PASS" else 1)
PY
rc=$?
if [ $rc -eq 0 ]; then
  echo "PASS -> repo reproduces the archived $SCEN account. Archive left as-is (identical)."
else
  echo "FLAG -> rerun differs from the archive (see above). Archive NOT overwritten; investigate before trusting the repo."
fi
exit $rc
