#!/bin/bash
#SBATCH --job-name=erosion_upstream
#SBATCH --time=06:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=128G                 # flow accumulation on the ~1 km grid is memory-heavy
#SBATCH --partition=CHANGE_ME
#SBATCH --output=upstream_%j.out
#SBATCH --error=upstream_%j.err
# ---------------------------------------------------------------------------
# Stage 3: regenerate the UPSTREAM prevention share on the hydrologically
# conditioned flow network (replaces the coarse-routing upstream term).
#
# NOTE: the archive already ships the finished product
#   inputs_conditioned/upstream/upstream_prevention_share_optF.tif
# so this stage is only needed for a FULL from-scratch reproduction. The one
# input it needs that is NOT in the archive is the raw HydroSHEDS 30s direction
# grid (hyd_glo_dir_30s.tif) -- see shared_inputs_REFERENCE.md.
#
# Paths default to the archive; change ARCHIVE / REPO / HYD_DIR / out dir only.
# ---------------------------------------------------------------------------
set -euo pipefail
source ~/.bashrc; conda activate gep_erosion
export TMPDIR=CHANGE_ME_scratch_with_space; mkdir -p "$TMPDIR"

ARCHIVE=/projects/standard/jajohns/shared/nfamara/erosion_global_gep_final
REPO=CHANGE_ME_repo
PY=$(which python)
AQ=$REPO/conditioned_inputs
SDR_OUT=$ARCHIVE/sdr_outputs_conditioned                 # holds usle_*.tif + avoided_erosion_*.tif
TEMPLATE=$ARCHIVE/inputs_conditioned/sdr/dem_cond_1000m_8857.tif   # analysis-grid template
HYD_DIR=CHANGE_ME/hyd_glo_dir_30s.tif                    # raw HydroSHEDS 30s direction grid (referenced)
cd CHANGE_ME_output_dir

# (a) encode conditioned D8 flow direction from the HydroSHEDS 30s direction grid
$PY -I $AQ/remap_flowdir.py --in "$HYD_DIR" --out flowdir_pgp.tif
# (b) accumulate avoided / potential erosion on the conditioned network -> 0..1 share
$PY -I $AQ/upstream_conditioned.py --flowdir flowdir_pgp.tif \
    --avoided   "$SDR_OUT/avoided_erosion_conddem1km_2019.tif" \
    --potential "$SDR_OUT/usle_conddem1km_2019.tif" --potential-is-actual \
    --out       upstream_prevention_share.tif \
    --analysis-template "$TEMPLATE"
echo "wrote upstream_prevention_share.tif"
