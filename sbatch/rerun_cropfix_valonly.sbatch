#!/bin/bash
#SBATCH --job-name=erosion_valonly
#SBATCH --time=02:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --output=erosion_valonly_%x_%j.out
#SBATCH --error=erosion_valonly_%x_%j.err
# ---------------------------------------------------------------------------
# VALUATION-ONLY crop-fix rerun. Runs ONLY task_compute_prevention_shares
# (reads conditioned VAL_USLE/VAL_AVOIDED + archive inputs); InVEST SDR is
# NOT run. Each scenario gets its OWN project dir + output dir (the shared
# defaults are what made the earlier full-SDR jobs collide).
#
#   sbatch --partition=msismall rerun_cropfix_valonly.sbatch ses11
#   sbatch --partition=msismall rerun_cropfix_valonly.sbatch eps5
# ---------------------------------------------------------------------------
set -eo pipefail
source ~/.bashrc; conda activate gep_InVEST

SCEN=${1:-ses11}
ARCHIVE=/projects/standard/jajohns/shared/nfamara/erosion_global_gep_final
case "$SCEN" in
  ses11) HIGH=11; LOW=2; TAG=ses11_cropfix; EXPECT=52.660
         RELEASED=${RELEASED:-$ARCHIVE/results/ses11_headline/integrated_country_gep.csv} ;;
  eps5)  HIGH=5;  LOW=1; TAG=eps5_cropfix;  EXPECT=""
         RELEASED=${RELEASED:-$ARCHIVE/results/eps5_sensitivity/integrated_country_gep.csv} ;;
  *) echo "scenario must be ses11 or eps5"; exit 2 ;;
esac

REPO=/users/3/damph002/gep_runs_sdr_floods/sediment/global_erosion_gep_repo_revised_2026-10-29/global_erosion_gep
cd "$REPO"
export PYTHONUNBUFFERED=1
export PYTHONPATH="$REPO:${PYTHONPATH:-}"
export TMPDIR=/scratch.global/$USER/erosion_cropfix/tmp_$TAG; rm -rf "$TMPDIR"; mkdir -p "$TMPDIR"

# inputs root = consolidated archive (symlinks expose inputs_v2/erosion_gep + inputs_v2/sdr)
export GEP_EROSION_GEP_ROOT=$ARCHIVE
# conditioned SDR outputs (valuation reads these; NO SDR recompute) + conditioned upstream
export GEP_EROSION_VAL_USLE_PATH=$ARCHIVE/sdr_outputs_conditioned/usle_conddem1km_2019.tif
export GEP_EROSION_VAL_AVOIDED_PATH=$ARCHIVE/sdr_outputs_conditioned/avoided_erosion_conddem1km_2019.tif
export GEP_EROSION_UPS_PATH=$ARCHIVE/inputs_conditioned/upstream/upstream_prevention_share_optF.tif
# valuation-only task tree (no InVEST SDR, no figures) -- the in-module standard knob
export GEP_EROSION_TASK_TREE=valuation
# account settings
export GEP_EROSION_ALL_TOUCHED=false
export GEP_EROSION_THRESH_HIGH=$HIGH
export GEP_EROSION_THRESH_LOW=$LOW
# PER-SCENARIO output + hazelbean project dir (fresh -> forces recompute, no collision)
export GEP_EROSION_OUTPUT_DIR=/scratch.global/$USER/erosion_cropfix/$TAG; rm -rf "$GEP_EROSION_OUTPUT_DIR"; mkdir -p "$GEP_EROSION_OUTPUT_DIR"
export GEP_EROSION_PROJECT_DIR=/scratch.global/$USER/erosion_cropfix/proj_$TAG; rm -rf "$GEP_EROSION_PROJECT_DIR"; mkdir -p "$GEP_EROSION_PROJECT_DIR"
export GEP_EROSION_RUN_TAG=$TAG

echo "### scenario=$SCEN  HIGH=$HIGH LOW=$LOW  TASK_TREE=$GEP_EROSION_TASK_TREE (no SDR)"
echo -n "### fixed-code check (expect 2): "; grep -c CROP_ITEM_CODES_2041 "$REPO/global_invest/erosion/erosion_functions.py"

python -m global_invest.erosion.run_erosion

CSV=$GEP_EROSION_OUTPUT_DIR/integrated_country_gep.csv
echo "### result CSV: $CSV"
EXPECT="$EXPECT" RELEASED="$RELEASED" python - "$CSV" <<'PY'
import os, sys, pandas as pd, numpy as np
d = pd.read_csv(sys.argv[1])
for c in ["gep_const2019_usd_combined","gep_const2019_usd_onfarm","gep_const2019_usd_upstream"]:
    if c in d.columns:
        print(f"{c:34s} {pd.to_numeric(d[c],errors='coerce').sum()/1e9:10.3f} bn")
comb = pd.to_numeric(d["gep_const2019_usd_combined"], errors="coerce")
print("countries with combined GEP > 0 :", int((comb>0).sum()))
print("countries with missing (NaN) GEP:", int(comb.isna().sum()))
exp = os.environ.get("EXPECT","").strip()
if exp:
    t = comb.sum()/1e9
    print(f"combined total = {t:.3f} bn   expected {exp}   {'PASS' if abs(t-float(exp))<0.05 else 'CHECK'}")
rel_path = os.environ.get("RELEASED","").strip(); share_col="erosion_shock_share"
if rel_path and os.path.exists(rel_path) and share_col in d.columns:
    r = pd.read_csv(rel_path)
    if share_col in r.columns:
        m=(d[["iso3",share_col]].rename(columns={share_col:"new"})
           .merge(r[["iso3",share_col]].rename(columns={share_col:"old"}),on="iso3",how="outer"))
        diff=(pd.to_numeric(m["new"],errors="coerce")-pd.to_numeric(m["old"],errors="coerce")).abs()
        nmax=diff.max(); off=m.loc[diff>1e-9,"iso3"].tolist()
        print(f"\nshock-share reproduction vs {rel_path}")
        print(f"  max |Delta shock_share| = {nmax:.3e}   differing(>1e-9): {len(off)}")
        print("  SHARES REPRODUCED (biophysical layer unchanged)" if nmax<1e-6 else f"  CHECK -- shares moved: {off[:15]}")
    else: print(f"\n[share check skipped] '{share_col}' not in released CSV")
else: print(f"\n[share check skipped] set RELEASED=<released integrated_country_gep.csv> (got '{rel_path}')")
PY
echo "DONE $SCEN -> $CSV"
