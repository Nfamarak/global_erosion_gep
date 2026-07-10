"""
erosion_debug_ps.py — standalone smoke test for Section B
(on-farm + upstream prevention share GEP valuation), skipping
Section A (SDR) since usle_2019_revised_feb_13.tif and
avoided_erosion_2019_revised_feb_13.tif already exist.

Run on MSI from an interactive/compute node with the gep_InVEST env active:
    conda activate gep_InVEST
    python -m global_invest.erosion.erosion_debug_ps
"""
from global_invest.erosion import erosion_functions


class FakeP:
    pass


p = FakeP()

# Confirmed to exist on Agate as of this smoke test.
p.erosion_gep_root = "/projects/standard/jajohns/shared/sediment_gep/sediment_feb_2026"
p.erosion_run_tag = "ses11_onfarm_upstream_combined_20260305"
p.erosion_gep_input_dir = f"{p.erosion_gep_root}/inputs_v2/erosion_gep"

# USLE / avoided erosion: confirmed present at this exact path+filename.
p.erosion_usle_path = f"{p.erosion_gep_input_dir}/usle_2019_revised_feb_13.tif"
p.erosion_avoided_erosion_path = f"{p.erosion_gep_input_dir}/avoided_erosion_2019_revised_feb_13.tif"
p.erosion_country_boundary_path = f"{p.erosion_gep_input_dir}/country_boundary_r250_with_iso3.gpkg"

# TEMP: the jajohns group storage quota is completely full (100% of 1.15TB
# as of this test), so write this smoke test's output to scratch instead
# of the real shared output directory. Remove this override once the group
# quota issue is resolved.
p.erosion_gep_output_dir = "/scratch.global/damph002/erosion_test_output"

# NOTE: p.erosion_upstream_prevention_share_path defaults to
# {erosion_gep_root}/upstream_prevention_attribution_v3/upstream_prevention_share.tif
# inside configure_prevention_shares(). Confirmed present on Agate.

erosion_functions.configure_prevention_shares(p)
print("OUT_DIR will be:", erosion_functions.OUT_DIR)
print("USLE_PATH:", erosion_functions.USLE_PATH)
print("AVOID_PATH:", erosion_functions.AVOID_PATH)
print("UPS_PATH:", erosion_functions.UPS_PATH)

erosion_functions.integrate_and_write()