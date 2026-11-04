#!/usr/bin/env python3
"""
preflight_value_from_shares.py -- validate inputs for the value_from_shares run
BEFORE launching it. Pandas-only (no GDAL/InVEST/hazelbean); safe on a login node.

Checks, per scenario, that:
  - the per-crop protected-production long table exists and has the 7 required columns
    and all three components (onfarm/upstream/combined);
  - the baseline integrated_country_gep.csv exists (and reports its shock_x_gpv combined);
  - the shared per-crop value table exists, is BOM-safe readable, has iso3/item_code_fao/
    value_usd, and (if flagged) a non-empty in_crop_provision_account subset;
  - the FAO->SPAM correspondence exists and has a usable column pair;
  - the output directory is creatable/writable.

Usage:
  python preflight_value_from_shares.py \
      --arch /projects/standard/jajohns/shared/nfamara/erosion_global_gep_final \
      --scenarios ses11_headline eps5_sensitivity \
      --outbase /scratch.global/$USER/erosion_harmonized
Exit code 0 = all pass; 1 = at least one problem (printed).
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

OK, BAD = "  OK  ", "  !!  "
problems = []


def _read_csv_bom(p):
    return pd.read_csv(p, encoding="utf-8-sig", low_memory=False)


def _cols(df):
    return {c.strip().lstrip("﻿").lower() for c in df.columns}


def check_value_table(path: Path):
    if not path.is_file():
        problems.append(f"value table missing: {path}"); print(BAD, "value table MISSING:", path); return
    df = _read_csv_bom(path); cols = _cols(df)
    need = {"iso3", "item_code_fao", "value_usd"}
    miss = need - cols
    if miss:
        problems.append(f"value table missing cols {miss}"); print(BAD, "value table missing columns:", miss); return
    n = len(df)
    if "in_crop_provision_account" in cols:
        real = [c for c in df.columns if c.strip().lstrip("﻿").lower() == "in_crop_provision_account"][0]
        keep = df[real].astype(str).str.strip().str.lower().isin(["true", "1", "yes"]).sum()
        print(OK, f"value table: {n} rows, {keep} in_crop_provision_account=True  ({path.name})")
        if keep == 0:
            problems.append("value table has 0 in-account rows"); print(BAD, "  -> 0 in-account rows (nothing would be valued)")
    else:
        print(OK, f"value table: {n} rows (no in_crop_provision_account flag; all used)  ({path.name})")


def check_crosswalk(path: Path):
    if not path.is_file():
        problems.append(f"correspondence missing: {path}"); print(BAD, "correspondence MISSING:", path); return
    df = _read_csv_bom(path); cols = _cols(df)
    code = next((c for c in ("item_code_fao", "fao_item_code") if c in cols), None)
    spam = next((c for c in ("spam_crop", "spam2020_crop_label") if c in cols), None)
    if not (code and spam):
        problems.append("correspondence lacks usable column pair"); print(BAD, "correspondence lacks item-code/spam-crop columns; found:", sorted(cols)); return
    nrows = len(df)
    npool = 0
    try:
        real_code = [c for c in df.columns if c.strip().lstrip("﻿").lower() == code][0]
        npool = int((df.groupby(real_code).size() > 1).sum())
    except Exception:
        pass
    print(OK, f"correspondence: {nrows} rows via ({code}, {spam}); pooled FAO codes: {npool}  ({path.name})")


def check_shares_long(path: Path):
    if not path.is_file():
        problems.append(f"shares long missing: {path}"); print(BAD, "shares long MISSING:", path); return None
    df = pd.read_csv(path)
    need = {"component", "ISO3", "crop", "elasticity_used",
            "protected_production_tons", "total_production_tons", "share_protected_production"}
    miss = need - set(df.columns)
    if miss:
        problems.append(f"shares long missing cols {miss}"); print(BAD, "shares long missing columns:", miss); return None
    comps = set(df["component"].unique())
    need_comp = {"onfarm", "upstream", "combined"}
    if not need_comp <= comps:
        problems.append(f"shares long missing components {need_comp - comps}")
        print(BAD, "shares long missing components:", need_comp - comps)
    print(OK, f"shares long: {len(df)} rows, {df['ISO3'].nunique()} countries, {df['crop'].nunique()} crops, "
              f"components={sorted(comps)}  ({path.name})")
    return df


def check_baseline(path: Path):
    if not path.is_file():
        print(BAD, "baseline integrated MISSING (optional, context columns won't carry):", path)
        problems.append(f"baseline integrated missing: {path}"); return
    df = pd.read_csv(path)
    if "gep_const2019_usd_combined" in df.columns:
        tot = pd.to_numeric(df["gep_const2019_usd_combined"], errors="coerce").sum() / 1e9
        n = int((pd.to_numeric(df["gep_const2019_usd_combined"], errors="coerce") > 0).sum())
        print(OK, f"baseline integrated: shock_x_gpv combined = {tot:.3f} bn over {n} countries  ({path.name})")
    else:
        print(OK, f"baseline integrated present ({path.name})")


def check_outdir(path: Path):
    try:
        path.mkdir(parents=True, exist_ok=True)
        t = path / ".preflight_write_test"; t.write_text("ok"); t.unlink()
        print(OK, f"output dir writable: {path}")
    except Exception as e:
        problems.append(f"output dir not writable: {path} ({e})"); print(BAD, "output dir NOT writable:", path, e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arch", required=True)
    ap.add_argument("--scenarios", nargs="+", default=["ses11_headline", "eps5_sensitivity"])
    ap.add_argument("--outbase", default=None)
    args = ap.parse_args()
    arch = Path(args.arch)
    val = arch / "inputs_conditioned" / "valuation" / "fao_values_2019_production_x_price.csv"
    xw = arch / "inputs_conditioned" / "valuation" / "fao_item_spam2020_crop_correspondence.csv"

    print("== shared valuation inputs ==")
    check_value_table(val)
    check_crosswalk(xw)

    for s in args.scenarios:
        print(f"\n== scenario: {s} ==")
        rdir = arch / "results" / s
        check_shares_long(rdir / "country_crop_protected_production_long.csv")
        check_baseline(rdir / "integrated_country_gep.csv")
        if args.outbase:
            check_outdir(Path(args.outbase) / s)

    print("\n" + ("PREFLIGHT PASSED — safe to run value_from_shares"
                  if not problems else f"PREFLIGHT FOUND {len(problems)} PROBLEM(S):"))
    for p in problems:
        print("  -", p)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
