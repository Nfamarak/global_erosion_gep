#!/usr/bin/env python3
"""
verify_cropfix_gep.py  (run on MSI, gep_InVEST env)

Fast check that the three code fixes reproduce the independently recomputed
$52.660 bn WITHOUT a full valuation rerun. The biophysical shock shares are unchanged,
so combined GEP scales with the crop-GPV base:

    gep_new = gep_old x (crop_gpv_new / crop_gpv_old)

crop_gpv_new comes from the FIXED erosion_functions (FAOSTAT group-2041 crop filter +
price de-duplication); crop_gpv_old and gep_old come from the released SES-11 result.

    python verify_cropfix_gep.py \
      --repo     <path to the repo with the FIXED erosion_functions.py> \
      --gpv      .../inputs_v2/erosion_gep/faostat_gpv_2019_iso3.csv \
      --prices   .../inputs_v2/erosion_gep/faostat_prices_2019_completed_revised.csv \
      --released .../results/ses11_headline/integrated_country_gep.csv
"""
import argparse
import sys
from pathlib import Path
import numpy as np
import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="repo root containing the FIXED global_invest/erosion")
    ap.add_argument("--gpv", required=True)
    ap.add_argument("--prices", required=True)
    ap.add_argument("--released", required=True, help="released SES-11 integrated_country_gep.csv")
    ap.add_argument("--target", type=float, default=52.660, help="expected new combined total ($bn)")
    a = ap.parse_args()

    sys.path.insert(0, a.repo)
    from global_invest.erosion.erosion_functions import load_fao_gpv_iso3_const2019_with_fallback

    # new crop GPV per iso3 (fixed crop filter + price dedup)
    fao_new = load_fao_gpv_iso3_const2019_with_fallback(Path(a.gpv), Path(a.prices), base_year=2019)
    fao_new = fao_new.rename(columns={"crop_gpv_const2019_2019": "crop_gpv_new"})[["iso3", "crop_gpv_new"]]

    rel = pd.read_csv(a.released)
    rel["iso3"] = rel["iso3"].astype(str)
    fao_new["iso3"] = fao_new["iso3"].astype(str)
    m = rel.merge(fao_new, on="iso3", how="left")

    gpv_old = pd.to_numeric(m["crop_gpv_const2019_2019"], errors="coerce")
    ratio = m["crop_gpv_new"] / gpv_old.replace(0, np.nan)   # unchanged where ratio NaN

    for comp in ["combined", "onfarm", "upstream"]:
        col = f"gep_const2019_usd_{comp}"
        if col in m.columns:
            m[f"{col}_new"] = pd.to_numeric(m[col], errors="coerce") * ratio
            old_t = pd.to_numeric(m[col], errors="coerce").sum() / 1e9
            new_t = m[f"{col}_new"].sum() / 1e9
            print(f"{comp:9s}: old ${old_t:7.3f} bn  ->  new ${new_t:7.3f} bn")

    new_comb = m["gep_const2019_usd_combined_new"].sum() / 1e9
    print("-" * 52)
    print(f"SES-11 combined (new): ${new_comb:.3f} bn   target ${a.target:.3f} bn   "
          f"{'PASS' if abs(new_comb - a.target) < 0.05 else 'CHECK'}")
    # show the biggest movers
    m["delta"] = (m["gep_const2019_usd_combined_new"].fillna(0)
                  - pd.to_numeric(m["gep_const2019_usd_combined"], errors="coerce").fillna(0)) / 1e9
    big = m.reindex(m["delta"].abs().sort_values(ascending=False).index).head(10)
    print("\nlargest per-country changes (combined, $bn):")
    for _, r in big.iterrows():
        print(f"   {r['iso3']:4s}  {r['delta']:+.3f}")


if __name__ == "__main__":
    main()
