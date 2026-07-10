import os
import hazelbean as hb

from global_invest.erosion import erosion_initialization

if __name__ == '__main__':

    # ProjectFlow object
    p = hb.ProjectFlow()
    p.project_name = 'gep_erosion'
    p.project_dir = os.path.join(os.path.expanduser('~'), 'Files', 'global_invest', 'projects', p.project_name)
    p.set_project_dir(p.project_dir)

    # Task tree
    erosion_initialization.add_erosion_tasks(p)

    # -------------------------------------------------------------------
    # Section A -- InVEST SDR run
    # Confirmed current location on Agate as of 2026-07-09.
    # -------------------------------------------------------------------
    p.erosion_sdr_root = "/projects/standard/jajohns/shared/sediment_gep/sediment_feb_2026"
    p.erosion_sdr_input_dir = os.path.join(p.erosion_sdr_root, "inputs_v2", "sdr")
    # jajohns group quota is full -- write SDR outputs to scratch instead.
    p.erosion_sdr_output_dir = "/scratch.global/damph002/erosion_full_run/sdr_output"
    p.erosion_biophysical_table_path = os.path.join(p.erosion_sdr_input_dir, "biophysical_esa_sdr_InVEST_Global_GEP_Feb_12_26_nkd.csv")
    p.erosion_dem_path = os.path.join(p.erosion_sdr_input_dir, "global_dem_reproj.tif")
    p.erosion_lulc_path = os.path.join(p.erosion_sdr_input_dir, "lulc_esa_2019_int_reproj.tif")
    p.erosion_erodibility_path = os.path.join(p.erosion_sdr_input_dir, "erodibility_30s_reproj.tif")
    p.erosion_erosivity_path = os.path.join(p.erosion_sdr_input_dir, "erosivity_30s_reproj.tif")
    p.erosion_watersheds_path = os.path.join(p.erosion_sdr_input_dir, "wshed_global_reproj_CLEAN_MERGED.gpkg")
    p.erosion_watersheds_sanitized_path = os.path.join(p.erosion_sdr_input_dir, "wshed_for_sdr_report_sanitized.gpkg")

    # -------------------------------------------------------------------
    # Sections B & C -- prevention-share GEP calculation + maps/figures
    # -------------------------------------------------------------------
    p.erosion_gep_root = "/projects/standard/jajohns/shared/sediment_gep/sediment_feb_2026"
    p.erosion_run_tag = "ses11_onfarm_upstream_combined_20260305"
    p.erosion_gep_input_dir = os.path.join(p.erosion_gep_root, "inputs_v2", "erosion_gep")
    # jajohns group quota is full -- write outputs to scratch instead.
    p.erosion_gep_output_dir = "/scratch.global/damph002/erosion_full_run/prevention_share_output"
    p.erosion_usle_path = os.path.join(p.erosion_gep_input_dir, "usle_2019_revised_feb_13.tif")
    p.erosion_avoided_erosion_path = os.path.join(p.erosion_gep_input_dir, "avoided_erosion_2019_revised_feb_13.tif")
    p.erosion_country_boundary_path = os.path.join(p.erosion_gep_input_dir, "country_boundary_r250_with_iso3.gpkg")

    p.results = {}

    hb.log('Created ProjectFlow object at ' + p.project_dir + '\n    from script ' + p.calling_script)
    p.execute()

    result = 'Done!'