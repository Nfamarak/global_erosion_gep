"""
run_erosion.py -- thin runner for the erosion soil-retention GEP module.

Layout follows the global_invest service convention (cf. run_flood.py):
set_erosion_paths(p) centralises every p.erosion_* attribute the module reads,
resolved from environment variables with the original Agate paths as fallback,
so MSI sbatch runners and interactive runs share one definition of the layout.

Override every path/knob WITHOUT editing code via the GEP_EROSION_* env hooks.
For the revised (conditioned-DEM) run the recommended launchers are
sbatch/run_scenario.sbatch and the archive layout in the top-level README; a
minimal interactive example:

    export GEP_EROSION_OUTPUT_DIR=/scratch.global/$USER/erosion_conditioned_ses11
    export GEP_EROSION_RUN_TAG=ses11_conditioned
    python -m global_invest.erosion.run_erosion

Pointing GEP_EROSION_OUTPUT_DIR at a FRESH directory is important: the valuation
task skips when integrated_country_gep.csv already exists, so re-using an old
output dir would hand back the previous numbers. See CHANGELOG.md.

Boundary rasterization defaults to CELL-CENTRE (all_touched=False); set
GEP_EROSION_ALL_TOUCHED=true to restore the earlier all-touched behaviour.
"""
import os

import hazelbean as hb

from global_invest.erosion import erosion_initialization


def _env(name, default):
    return os.environ.get(name, default)


def set_erosion_paths(p):
    # -------------------------------------------------------------------
    # Section A -- InVEST SDR run
    # Confirmed current location on Agate as of 2026-07-09.
    # -------------------------------------------------------------------
    p.erosion_sdr_root = _env(
        "GEP_EROSION_SDR_ROOT",
        "/projects/standard/jajohns/shared/sediment_gep/sediment_feb_2026")
    p.erosion_sdr_input_dir = os.path.join(p.erosion_sdr_root, "inputs_v2", "sdr")
    # jajohns group quota is full -- write SDR outputs to scratch by default.
    p.erosion_sdr_output_dir = _env(
        "GEP_EROSION_SDR_OUTPUT_DIR",
        f"/scratch.global/{os.environ.get('USER', 'user')}/erosion_full_run/sdr_output")
    p.erosion_biophysical_table_path = os.path.join(
        p.erosion_sdr_input_dir, "biophysical_esa_sdr_InVEST_Global_GEP_Feb_12_26_nkd.csv")
    # DEM for the InVEST SDR run. For the revised (finer) run, point this at the
    # hydrologically conditioned DEM via GEP_EROSION_DEM_PATH.
    p.erosion_dem_path = _env(
        "GEP_EROSION_DEM_PATH",
        os.path.join(p.erosion_sdr_input_dir, "global_dem_reproj.tif"))
    # SDR inputs. For the REVISED finer run these must be the 1 km layers aligned to
    # the same grid as GEP_EROSION_DEM_PATH (see conditioned_inputs/prep_sdr_inputs_fine.sh);
    # set them via their env hooks. Defaults are the ~6.45 km baseline layers.
    p.erosion_lulc_path = _env("GEP_EROSION_LULC_PATH",
        os.path.join(p.erosion_sdr_input_dir, "lulc_esa_2019_int_reproj.tif"))
    p.erosion_erodibility_path = _env("GEP_EROSION_ERODIBILITY_PATH",
        os.path.join(p.erosion_sdr_input_dir, "erodibility_30s_reproj.tif"))
    p.erosion_erosivity_path = _env("GEP_EROSION_EROSIVITY_PATH",
        os.path.join(p.erosion_sdr_input_dir, "erosivity_30s_reproj.tif"))
    p.erosion_watersheds_path = os.path.join(
        p.erosion_sdr_input_dir, "wshed_global_reproj_CLEAN_MERGED.gpkg")
    p.erosion_watersheds_sanitized_path = os.path.join(
        p.erosion_sdr_input_dir, "wshed_for_sdr_report_sanitized.gpkg")

    # -------------------------------------------------------------------
    # Sections B & C -- prevention-share GEP calculation + maps/figures
    # -------------------------------------------------------------------
    p.erosion_gep_root = _env(
        "GEP_EROSION_GEP_ROOT",
        "/projects/standard/jajohns/shared/sediment_gep/sediment_feb_2026")
    p.erosion_run_tag = _env(
        "GEP_EROSION_RUN_TAG", "ses11_onfarm_upstream_combined_20260305")
    p.erosion_gep_input_dir = os.path.join(p.erosion_gep_root, "inputs_v2", "erosion_gep")
    # jajohns group quota is full -- write outputs to scratch by default.
    # Point GEP_EROSION_OUTPUT_DIR at a FRESH dir for the corrected re-run.
    p.erosion_gep_output_dir = _env(
        "GEP_EROSION_OUTPUT_DIR",
        f"/scratch.global/{os.environ.get('USER', 'user')}/erosion_full_run/prevention_share_output")
    # Valuation inputs (actual + avoided erosion rasters). For the REVISED finer run,
    # point these at the conditioned-DEM SDR outputs resampled to the analysis grid,
    # via GEP_EROSION_VAL_USLE_PATH / GEP_EROSION_VAL_AVOIDED_PATH. Default is the
    # ~6.45 km baseline SDR. (This is the knob that fixes the handover "valuation
    # reads Feb SDR" issue -- see CHANGELOG / README.)
    p.erosion_usle_path = _env(
        "GEP_EROSION_VAL_USLE_PATH",
        os.path.join(p.erosion_gep_input_dir, "usle_2019_revised_feb_13.tif"))
    p.erosion_avoided_erosion_path = _env(
        "GEP_EROSION_VAL_AVOIDED_PATH",
        os.path.join(p.erosion_gep_input_dir, "avoided_erosion_2019_revised_feb_13.tif"))
    p.erosion_country_boundary_path = os.path.join(
        p.erosion_gep_input_dir, "country_boundary_r250_with_iso3.gpkg")

    # Boundary rasterization rule. Cell-centre (all_touched=False) reproduces
    # the reconciled cell-centre run (~$18.24B, 161 countries); all-touched (True) was
    # the earlier default (~$18.09B, 162). Env-overridable: set
    # GEP_EROSION_ALL_TOUCHED=true to restore all-touched.
    p.erosion_rasterize_all_touched = _env(
        "GEP_EROSION_ALL_TOUCHED", "false").strip().lower() in ("1", "true", "yes")

    # Upstream prevention-share raster. For the revised run, point at the share
    # regenerated on the hydrologically conditioned flow network, via
    # GEP_EROSION_UPS_PATH (see conditioned_inputs/upstream_conditioned.py).
    _ups = _env("GEP_EROSION_UPS_PATH", "")
    if _ups:
        p.erosion_upstream_prevention_share_path = _ups

    # Severity thresholds (t/ha/yr). SES-11 headline: high=11; EPS-5 sensitivity: high=5.
    # Low threshold (small/low-elevation countries): 2.
    p.erosion_threshold_high_t_ha_yr = float(_env("GEP_EROSION_THRESH_HIGH", "11"))
    p.erosion_threshold_low_t_ha_yr = float(_env("GEP_EROSION_THRESH_LOW", "2"))
    return p


if __name__ == "__main__":
    # ProjectFlow object
    p = hb.ProjectFlow()
    p.project_name = "gep_erosion"
    p.project_dir = _env(
        "GEP_EROSION_PROJECT_DIR",
        os.path.join(os.path.expanduser("~"), "Files", "global_invest", "projects", p.project_name))
    p.set_project_dir(p.project_dir)

    # Task tree
    erosion_initialization.add_erosion_tasks(p)

    # Paths (env-overridable, Agate fallbacks)
    set_erosion_paths(p)

    p.results = {}

    hb.log("Created ProjectFlow object at " + p.project_dir + "\n    from script " + p.calling_script)
    p.execute()

    result = "Done!"
