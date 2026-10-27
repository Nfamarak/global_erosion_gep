"""
run_erosion.py -- thin runner for the erosion soil-retention GEP module.

Layout follows the global_invest service convention (cf. run_flood.py):
set_erosion_paths(p) centralises every p.erosion_* attribute the module reads,
resolved from environment variables with the original Agate paths as fallback,
so MSI sbatch runners and interactive runs share one definition of the layout.

Override for a corrected re-run WITHOUT editing code, e.g.:

    export GEP_EROSION_OUTPUT_DIR=/scratch.global/damph002/erosion_corrected_20260827
    export GEP_EROSION_RUN_TAG=ses11_corrected_elasticity_20260827
    python -m global_invest.erosion.run_erosion

Pointing GEP_EROSION_OUTPUT_DIR at a FRESH directory is important: the valuation
task skips when integrated_country_gep.csv already exists, so re-using the old
output dir would hand back the pre-fix (buggy-elasticity) numbers. See
CHANGELOG.md.
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
        "/scratch.global/damph002/erosion_full_run/sdr_output")
    p.erosion_biophysical_table_path = os.path.join(
        p.erosion_sdr_input_dir, "biophysical_esa_sdr_InVEST_Global_GEP_Feb_12_26_nkd.csv")
    p.erosion_dem_path = os.path.join(p.erosion_sdr_input_dir, "global_dem_reproj.tif")
    p.erosion_lulc_path = os.path.join(p.erosion_sdr_input_dir, "lulc_esa_2019_int_reproj.tif")
    p.erosion_erodibility_path = os.path.join(p.erosion_sdr_input_dir, "erodibility_30s_reproj.tif")
    p.erosion_erosivity_path = os.path.join(p.erosion_sdr_input_dir, "erosivity_30s_reproj.tif")
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
        "/scratch.global/damph002/erosion_full_run/prevention_share_output")
    p.erosion_usle_path = os.path.join(p.erosion_gep_input_dir, "usle_2019_revised_feb_13.tif")
    p.erosion_avoided_erosion_path = os.path.join(
        p.erosion_gep_input_dir, "avoided_erosion_2019_revised_feb_13.tif")
    p.erosion_country_boundary_path = os.path.join(
        p.erosion_gep_input_dir, "country_boundary_r250_with_iso3.gpkg")
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
