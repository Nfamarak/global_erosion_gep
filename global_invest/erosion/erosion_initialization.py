import hazelbean as hb

from global_invest.erosion import erosion_tasks


def add_erosion_tasks(p):
    """
    Standard entry point (per Justin's global_invest convention: each
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


def build_erosion_results_task_tree(p):
    """Results-only variant: just render maps/figures from an existing prevention-share run."""
    p.task_generate_maps_and_figures = p.add_task(erosion_tasks.task_generate_maps_and_figures)
    return p
