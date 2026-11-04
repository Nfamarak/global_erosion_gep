import os
import hazelbean as hb

from global_invest.erosion import erosion_functions


def task_run_invest_sdr(p):
    """
    Task wrapper for Section A: run InVEST SDR to produce the sediment
    delivery / erosion rasters (USLE, avoided erosion) that Section B
    consumes. Originally step1_sdr_invest_run.ipynb.
    """
    erosion_functions.configure_sdr(p)
    p.erosion_sdr_args, p.erosion_sdr_file_registry = erosion_functions.run_invest_sdr()
    return True


def task_compute_prevention_shares(p):
    """
    Task wrapper for Section B: combine on-farm (AE/(AE+USLE)) and
    upstream prevention shares into the union-of-protection PS_combined,
    then compute country-crop protected production and the GEP valuation
    (onfarm / upstream / combined). Originally Combine_PS_SES11_3_3_2026.ipynb.
    Writes integrated_country_gep.csv and the PS rasters that
    task_generate_maps_and_figures() maps.
    """
    erosion_functions.configure_prevention_shares(p)

    service_results = p.results.setdefault('erosion', {})
    service_results['integrated_country_gep'] = os.path.join(
        erosion_functions.OUT_DIR, "integrated_country_gep.csv")

    if hb.path_all_exist([service_results['integrated_country_gep']]):
        hb.log("integrated_country_gep.csv already exists. Skipping prevention-share calculation for erosion.")
    else:
        erosion_functions.integrate_and_write()

    return True


def task_value_from_shares(p):
    """
    Valuation-only from an EXISTING run's per-crop protected-production long table,
    with no InVEST SDR run and no biophysical prevention-share recompute. Reuses the
    same compute_country_gep_from_country_crop() as task_compute_prevention_shares, so
    the monetary account matches a full valuation run on those shares. Reads
    GEP_EROSION_SHARES_LONG_CSV (+ optional GEP_EROSION_BASELINE_INTEGRATED_CSV for
    context columns); writes integrated_country_gep.csv to the output dir. Seconds, not
    hours -- use it to re-value a completed run under a different VALUATION_MODE/value table.
    """
    erosion_functions.configure_prevention_shares(p)

    service_results = p.results.setdefault('erosion', {})
    service_results['integrated_country_gep'] = os.path.join(
        erosion_functions.OUT_DIR, "integrated_country_gep.csv")

    erosion_functions.integrate_and_write_from_shares()
    return True


def task_generate_maps_and_figures(p):
    """
    Task wrapper for Section C: publication-ready choropleths, raster
    previews, and supporting charts built from
    task_compute_prevention_shares()'s outputs. Originally
    combined_maps_figures_SES_final_3_5_26.ipynb.
    """
    erosion_functions.configure_maps(p)
    erosion_functions.generate_all_maps_and_figures()
    return True
