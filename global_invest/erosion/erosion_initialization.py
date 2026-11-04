import hazelbean as hb

from global_invest.erosion import erosion_tasks


def add_erosion_tasks(p):
    """
    Standard entry point (per the global_invest convention: each
    service module exposes at least one add_<service>_tasks(p)) for
    building the full erosion / sediment retention task tree:
    InVEST SDR -> prevention-share GEP valuation -> maps & figures.
    This is what run_erosion.py calls by default.
    """
    return build_erosion_task_tree(p)


def build_erosion_task_tree(p):
    """Build the default task tree for erosion: SDR run, GEP calculation, then reporting maps/figures."""
    p.task_run_invest_sdr = p.add_task(erosion_tasks.task_run_invest_sdr)
    p.task_compute_prevention_shares = p.add_task(erosion_tasks.task_compute_prevention_shares)
    p.task_generate_maps_and_figures = p.add_task(erosion_tasks.task_generate_maps_and_figures)
    return p


def build_erosion_calculation_task_tree(p):
    """Calculation-only variant: SDR run + prevention-share GEP calculation, no maps/figures."""
    p.task_run_invest_sdr = p.add_task(erosion_tasks.task_run_invest_sdr)
    p.task_compute_prevention_shares = p.add_task(erosion_tasks.task_compute_prevention_shares)
    return p


def build_erosion_valuation_task_tree(p):
    """Valuation-only variant: prevention-share GEP valuation from EXISTING (conditioned)
    SDR outputs, with NO InVEST SDR run and no maps/figures. Used to re-run the monetary
    layer alone; the biophysical USLE / avoided-erosion rasters are read from
    GEP_EROSION_VAL_USLE_PATH / GEP_EROSION_VAL_AVOIDED_PATH. Writes integrated_country_gep.csv."""
    p.task_compute_prevention_shares = p.add_task(erosion_tasks.task_compute_prevention_shares)
    return p


def build_erosion_results_task_tree(p):
    """Results-only variant: just render maps/figures from an existing prevention-share run."""
    p.task_generate_maps_and_figures = p.add_task(erosion_tasks.task_generate_maps_and_figures)
    return p


def build_erosion_value_from_shares_task_tree(p):
    """Valuation-only from an EXISTING run's per-crop protected-production long table:
    no InVEST SDR, no biophysical prevention-share recompute, no figures. Reads
    GEP_EROSION_SHARES_LONG_CSV and re-values it under the current VALUATION_MODE,
    writing integrated_country_gep.csv. Runs in seconds."""
    p.task_value_from_shares = p.add_task(erosion_tasks.task_value_from_shares)
    return p


# Selector so run_erosion.py can pick a tree via the GEP_EROSION_TASK_TREE env knob.
TASK_TREE_BUILDERS = {
    "full": build_erosion_task_tree,                 # SDR + valuation + figures (default)
    "calculation": build_erosion_calculation_task_tree,  # SDR + valuation, no figures
    "valuation": build_erosion_valuation_task_tree,  # valuation only (no SDR, no figures)
    "value_from_shares": build_erosion_value_from_shares_task_tree,  # re-value existing shares (no biophysics)
    "results": build_erosion_results_task_tree,      # figures only
}


def add_erosion_tasks_for_tree(p, tree="full"):
    """Build whichever task tree `tree` names (default 'full'). Unknown names fall back
    to the full tree. Keeps run_erosion.py's selection logic in the module, per the
    global_invest convention."""
    builder = TASK_TREE_BUILDERS.get(str(tree).strip().lower(), build_erosion_task_tree)
    return builder(p)
