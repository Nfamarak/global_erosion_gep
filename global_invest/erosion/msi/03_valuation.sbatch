#!/bin/bash -l
#SBATCH --job-name=erosion_gep
#SBATCH --time=24:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=128g
#SBATCH --output=logs/erosion_gep_%j.out
#SBATCH --error=logs/erosion_gep_%j.err
#SBATCH --mail-type=END,FAIL
##SBATCH --mail-user=CHANGE_ME@example.edu     # uncomment + set to receive mail
#SBATCH --partition=CHANGE_ME

# =============================================================================
# Erosion soil-retention GEP -- REVISED (hydrologically conditioned-DEM) run.
#
# MSI launcher that runs the module end to end (SDR -> prevention-share
# valuation -> maps) via run_erosion.py. Input paths default to the consolidated
# archive (erosion_global_gep_final); change ARCHIVE to run elsewhere. For the
# clean, documented reproduction template see ../../../sbatch/run_scenario.sbatch
# (same ARCHIVE pattern, with quick/full modes).
#
# IMPORTANT: writes to a FRESH output dir + run tag so the valuation task does
# not skip on a stale integrated_country_gep.csv and hand back old numbers.
# =============================================================================

set -euo pipefail

# conda.sh references PS1, unset in a non-interactive shell and fatal under -u.
PS1=${PS1:-}
source "/common/software/install/migrated/anaconda/miniconda3_4.8.3-jupyter/etc/profile.d/conda.sh"
conda activate gep_InVEST
module unload python 2>/dev/null || true

# pyogrio validates GDAL_DATA at import and rejects what rasterio sets.
export GDAL_DATA="$CONDA_PREFIX/share/gdal"
export PROJ_LIB="$CONDA_PREFIX/share/proj"
export MPLBACKEND=Agg

# --- point Python at the dir CONTAINING global_invest/ (this repo root) -------
export PYTHONPATH="${EROSION_CODE_ROOT:-$SLURM_SUBMIT_DIR/../../..}:${PYTHONPATH:-}"

# --- REVISED conditioned-DEM inputs (default to the archive) ------------------
ARCHIVE=${ARCHIVE:-/projects/standard/jajohns/shared/nfamara/erosion_global_gep_final}
export GEP_EROSION_DEM_PATH=$ARCHIVE/inputs_conditioned/sdr/dem_cond_1000m_8857.tif
export GEP_EROSION_LULC_PATH=$ARCHIVE/inputs_conditioned/sdr/lulc_esa_2019_1000m_8857.tif
export GEP_EROSION_ERODIBILITY_PATH=$ARCHIVE/inputs_conditioned/sdr/erodibility_1000m_8857.tif
export GEP_EROSION_EROSIVITY_PATH=$ARCHIVE/inputs_conditioned/sdr/erosivity_1000m_8857.tif
export GEP_EROSION_VAL_USLE_PATH=$ARCHIVE/sdr_outputs_conditioned/usle_conddem1km_2019.tif
export GEP_EROSION_VAL_AVOIDED_PATH=$ARCHIVE/sdr_outputs_conditioned/avoided_erosion_conddem1km_2019.tif
export GEP_EROSION_UPS_PATH=$ARCHIVE/inputs_conditioned/upstream/upstream_prevention_share_optF.tif
export GEP_EROSION_THRESH_HIGH=${GEP_EROSION_THRESH_HIGH:-11}   # 11 = SES-11 (headline); 5 = EPS-5
export GEP_EROSION_THRESH_LOW=2
export GEP_EROSION_ALL_TOUCHED=false

# --- fresh outputs (edit to your scratch space) ------------------------------
STAMP=$(date +%Y%m%d)
SCRATCH=${SCRATCH:-/scratch.global/$USER}
export GEP_EROSION_RUN_TAG="${GEP_EROSION_RUN_TAG:-ses11_conditioned_${STAMP}}"
export GEP_EROSION_OUTPUT_DIR="${GEP_EROSION_OUTPUT_DIR:-$SCRATCH/erosion_conditioned_${STAMP}/prevention_share_output}"
export GEP_EROSION_SDR_OUTPUT_DIR="${GEP_EROSION_SDR_OUTPUT_DIR:-$SCRATCH/erosion_conditioned_${STAMP}/sdr_output}"
mkdir -p "$GEP_EROSION_OUTPUT_DIR"

echo "host        : $(hostname)"
echo "archive     : $ARCHIVE"
echo "run tag     : $GEP_EROSION_RUN_TAG"
echo "output dir  : $GEP_EROSION_OUTPUT_DIR"
echo "which python : $(which python)"

mkdir -p logs

# Pre-flight: verifies imports, inputs, the elasticity fix (maize=0.30), and a
# fresh output dir. Aborts the job before burning the queue slot if not ready.
srun python -m global_invest.erosion.msi.preflight

# Full run
srun python -m global_invest.erosion.run_erosion
