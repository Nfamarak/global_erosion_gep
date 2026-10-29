#!/bin/bash
#SBATCH --job-name=erosion_gep
#SBATCH --time=14:00:00
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --partition=CHANGE_ME
#SBATCH --output=erosion_gep_%j.out
#SBATCH --error=erosion_gep_%j.err
# ---------------------------------------------------------------------------
# Stages 2 + 4: run InVEST SDR on the conditioned inputs and value the account.
# Run once per severity scenario:
#   SES-11 (HEADLINE)         -> GEP_EROSION_THRESH_HIGH=11
#   EPS-5  (sensitivity only) -> GEP_EROSION_THRESH_HIGH=5
#
# Paths default to the consolidated archive (erosion_global_gep_final). To run
# against your own locations, change ARCHIVE (and REPO/TMPDIR/OUTPUT_DIR) only.
#
# TWO REPRODUCTION MODES:
#   QUICK (value only, default): VAL_USLE/VAL_AVOIDED point at the archived
#     conditioned SDR outputs, so InVEST SDR is NOT recomputed -- reproduces the
#     country account directly.
#   FULL: comment out the two VAL_* exports and set a fresh GEP_EROSION_SDR_OUTPUT_DIR;
#     InVEST SDR then regenerates usle/avoided from inputs_conditioned/sdr/ first.
# ---------------------------------------------------------------------------
set -euo pipefail
source ~/.bashrc; conda activate gep_erosion       # or your existing gep_InVEST env

ARCHIVE=/projects/standard/jajohns/shared/nfamara/erosion_global_gep_final
REPO=CHANGE_ME_repo                                 # the cloned repo (holds the python module)
cd "$REPO"
export PYTHONUNBUFFERED=1
export TMPDIR=CHANGE_ME_scratch_with_space; mkdir -p "$TMPDIR"

# --- SDR inputs: the 1 km conditioned/aligned layers (same grid) ---
export GEP_EROSION_DEM_PATH=$ARCHIVE/inputs_conditioned/sdr/dem_cond_1000m_8857.tif
export GEP_EROSION_LULC_PATH=$ARCHIVE/inputs_conditioned/sdr/lulc_esa_2019_1000m_8857.tif
export GEP_EROSION_ERODIBILITY_PATH=$ARCHIVE/inputs_conditioned/sdr/erodibility_1000m_8857.tif
export GEP_EROSION_EROSIVITY_PATH=$ARCHIVE/inputs_conditioned/sdr/erosivity_1000m_8857.tif
export GEP_EROSION_SDR_OUTPUT_DIR=$TMPDIR/conditioned_sdr_outputs   # used only in FULL mode

# --- valuation inputs: archived conditioned SDR outputs (QUICK mode) ---
#     comment these two out for FULL mode (regenerate SDR from the inputs above)
export GEP_EROSION_VAL_USLE_PATH=$ARCHIVE/sdr_outputs_conditioned/usle_conddem1km_2019.tif
export GEP_EROSION_VAL_AVOIDED_PATH=$ARCHIVE/sdr_outputs_conditioned/avoided_erosion_conddem1km_2019.tif
export GEP_EROSION_UPS_PATH=$ARCHIVE/inputs_conditioned/upstream/upstream_prevention_share_optF.tif

# --- scenario / account settings ---
export GEP_EROSION_ALL_TOUCHED=false                 # cell-centre boundary rule
export GEP_EROSION_THRESH_HIGH=11                    # 11 = SES-11 (headline); 5 = EPS-5
export GEP_EROSION_THRESH_LOW=2
export GEP_EROSION_OUTPUT_DIR=CHANGE_ME_fresh_output_dir_per_scenario  # MUST be fresh per run
export GEP_EROSION_RUN_TAG=ses11_conditioned

python -m global_invest.erosion.run_erosion
echo "DONE -> $GEP_EROSION_OUTPUT_DIR/integrated_country_gep.csv"
