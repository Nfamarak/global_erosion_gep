#!/bin/bash
#SBATCH --job-name=erosion_harmonized
#SBATCH --time=24:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --output=erosion_harmonized_%x_%j.out
#SBATCH --error=erosion_harmonized_%x_%j.err
# ---------------------------------------------------------------------------
# Harmonized per-crop valuation, valuation-only, into a FRESH results folder.
# run_erosion.py (TASK_TREE=valuation, VALUATION_MODE=percrop) computes:
#   ERSV_k = sum_c value_usd[c,k] x share_protected[c,k] x elasticity[c]
# using the common crop_provision per-crop values mapped to SPAM crops, the
# per-crop elasticities, and the conditioned SDR biophysical shares. No InVEST
# SDR run; writes to a separate output folder.
#
#   sbatch --partition=msismall rerun_allcorrections_valonly.sbatch ses11
#   sbatch --partition=msismall rerun_allcorrections_valonly.sbatch eps5
# ---------------------------------------------------------------------------
set -eo pipefail
source ~/.bashrc; conda activate gep_InVEST

SCEN=${1:-ses11}
ARCHIVE=/projects/standard/jajohns/shared/nfamara/erosion_global_gep_final
case "$SCEN" in
  ses11) HIGH=11; LOW=2; TAG=ses11_harmonized ;;
  eps5)  HIGH=5;  LOW=1; TAG=eps5_harmonized  ;;
  *) echo "scenario must be ses11 or eps5"; exit 2 ;;
esac
# crop-fix run (for a biophysical-share equality guard; optional)
CROPFIX_INTEGRATED=${CROPFIX_INTEGRATED:-/scratch.global/$USER/erosion_cropfix/${SCEN}_cropfix/integrated_country_gep.csv}

REPO=/users/3/damph002/gep_runs_sdr_floods/sediment/global_erosion_gep_repo_revised_2026-10-29/global_erosion_gep
cd "$REPO"
export PYTHONUNBUFFERED=1
export PYTHONPATH="$REPO:${PYTHONPATH:-}"
export TMPDIR=/scratch.global/$USER/erosion_harmonized/tmp_$TAG; rm -rf "$TMPDIR"; mkdir -p "$TMPDIR"

# inputs root = consolidated archive (symlinks expose inputs_v2/erosion_gep + inputs_v2/sdr)
export GEP_EROSION_GEP_ROOT=$ARCHIVE
# conditioned SDR outputs (valuation reads these; NO SDR recompute) + conditioned upstream
export GEP_EROSION_VAL_USLE_PATH=$ARCHIVE/sdr_outputs_conditioned/usle_conddem1km_2019.tif
export GEP_EROSION_VAL_AVOIDED_PATH=$ARCHIVE/sdr_outputs_conditioned/avoided_erosion_conddem1km_2019.tif
export GEP_EROSION_UPS_PATH=$ARCHIVE/inputs_conditioned/upstream/upstream_prevention_share_optF.tif
# ---- all corrections: harmonized per-crop valuation ----
export GEP_EROSION_TASK_TREE=valuation
export GEP_EROSION_VALUATION_MODE=percrop
# common crop_provision value table (in_crop_provision_account rows used) + correspondence
export GEP_EROSION_PERCROP_VALUE_CSV=$ARCHIVE/inputs_conditioned/valuation/fao_values_2019_production_x_price.csv
export GEP_EROSION_FAO_SPAM_CROSSWALK_CSV=$ARCHIVE/inputs_conditioned/valuation/fao_item_spam2020_crop_correspondence.csv
# account settings
export GEP_EROSION_ALL_TOUCHED=false
export GEP_EROSION_THRESH_HIGH=$HIGH
export GEP_EROSION_THRESH_LOW=$LOW
# FRESH, SEPARATE output + hazelbean project dir
export GEP_EROSION_OUTPUT_DIR=/scratch.global/$USER/erosion_harmonized/$TAG; rm -rf "$GEP_EROSION_OUTPUT_DIR"; mkdir -p "$GEP_EROSION_OUTPUT_DIR"
export GEP_EROSION_PROJECT_DIR=/scratch.global/$USER/erosion_harmonized/proj_$TAG; rm -rf "$GEP_EROSION_PROJECT_DIR"; mkdir -p "$GEP_EROSION_PROJECT_DIR"
export GEP_EROSION_RUN_TAG=$TAG

echo "### scenario=$SCEN HIGH=$HIGH LOW=$LOW  TASK_TREE=valuation  VALUATION_MODE=percrop (all corrections)"
echo -n "### percrop branch present (expect 1): "; grep -c 'if VALUATION_MODE == "percrop":' "$REPO/global_invest/erosion/erosion_functions.py"
echo -n "### per-crop value table rows: "; wc -l < "$GEP_EROSION_PERCROP_VALUE_CSV"

python -m global_invest.erosion.run_erosion

CSV=$GEP_EROSION_OUTPUT_DIR/integrated_country_gep.csv
echo "### result CSV: $CSV"
CROPFIX_INTEGRATED="$CROPFIX_INTEGRATED" python - "$CSV" <<'PY'
import os, sys, pandas as pd, numpy as np
d = pd.read_csv(sys.argv[1])
for c in ["gep_const2019_usd_combined","gep_const2019_usd_onfarm","gep_const2019_usd_upstream"]:
    if c in d.columns:
        print(f"{c:34s} {pd.to_numeric(d[c],errors='coerce').sum()/1e9:10.3f} bn")
comb = pd.to_numeric(d["gep_const2019_usd_combined"], errors="coerce")
print("countries with combined GEP > 0 :", int((comb>0).sum()))
print("countries with missing (NaN) GEP:", int(comb.isna().sum()))
# biophysical guard: protected-production shares must match the crop-fix run (valuation-only change)
cf = os.environ.get("CROPFIX_INTEGRATED","").strip(); col="share_protected_production_combined"
if cf and os.path.exists(cf) and col in d.columns:
    r = pd.read_csv(cf)
    if col in r.columns:
        m=(d[["iso3",col]].rename(columns={col:"new"})
           .merge(r[["iso3",col]].rename(columns={col:"old"}),on="iso3",how="inner"))
        diff=(pd.to_numeric(m["new"],errors="coerce")-pd.to_numeric(m["old"],errors="coerce")).abs()
        print(f"\nbiophysical share vs crop-fix: max|Delta|={diff.max():.3e} over {len(m)} countries -> "
              + ("BIOPHYSICS UNCHANGED" if diff.max()<1e-6 else "CHECK (shares moved)"))
    else: print("\n[biophysical guard skipped] col not in crop-fix CSV")
else:
    print(f"\n[biophysical guard skipped] set CROPFIX_INTEGRATED to the crop-fix integrated_country_gep.csv (got '{cf}')")
PY
echo "DONE $SCEN -> $CSV"
