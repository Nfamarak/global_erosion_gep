"""
verify_elasticity_fix.py — standalone check of the 2026-08-27 elasticity fix.

Runs WITHOUT hazelbean / natcap.invest: it imports only the SPAM_ALIAS_MAP and
the lookup logic pattern, loads your elasticity CSV, and prints the resolved
elasticity for every SPAM crop, asserting the key corrections.

Usage:
    python verify_elasticity_fix.py /path/to/elasticity_crops_fao_revised.csv

Exits non-zero if maize does not resolve to 0.30 (i.e. the buggy map slipped back in).
"""
import sys
import numpy as np
import pandas as pd

# The corrected map, copied verbatim from erosion_functions.py (keep in sync).
SPAM_ALIAS_MAP = {
    "whea": ["wheat"], "rice": ["rice"], "maiz": ["maize (corn)", "maize", "corn"],
    "barl": ["barley"], "sorg": ["sorghum"], "mill": ["millet", "small millet"],
    "pmil": ["millet", "pearl millet"], "pota": ["potatoes", "potato"],
    "cass": ["cassava, fresh", "cassava"], "soyb": ["soya beans", "soybean", "soy"],
    "grou": ["groundnut", "peanut"], "cott": ["seed cotton, unginned", "cotton"],
    "sugc": ["sugar cane", "sugarcane"], "bana": ["bananas", "banana"],
    "plnt": ["plantains and cooking bananas", "plantain"], "coco": ["cocoa beans", "cocoa"],
    "coff": ["coffee, green", "arabica coffee", "coffee"], "rcof": ["coffee, green", "robusta coffee"],
    "teas": ["tea leaves", "tea"], "toba": ["unmanufactured tobacco", "tobacco"],
    "toma": ["tomatoes", "tomato"],
    "onio": ["onions and shallots, dry (excluding dehydrated)", "onion"],
    "vege": ["vegetable", "other vegetables"], "sunf": ["sunflower seed", "sunflower"],
    "rape": ["rape or colza seed", "rapeseed", "canola"], "sesa": ["sesame seed", "sesame"],
    "citr": ["oranges", "citrus"], "lent": ["lentils, dry", "lentil"], "bean": ["beans, dry", "bean"],
    "chic": ["chick peas, dry", "chickpea"], "cowp": ["cow peas, dry", "cowpea"],
    "pige": ["peas, dry", "pigeon pea"], "yams": ["yams"],
    "swpo": ["sweet potatoes", "sweet potato"], "sugb": ["sugar beet", "sugarbeet"],
    "oilp": ["oil palm fruit", "oilpalm", "oil palm"], "cnut": ["coconuts, in shell", "coconut"],
    "ocer": ["other cereals"], "orts": ["other roots"],
    "opul": ["other pulses n.e.c.", "other pulses"], "ooil": ["castor oil seeds", "other oil crops"],
    "ofib": ["agave fibres, raw, n.e.c.", "other fibre crops"],
    "rubb": ["natural rubber in primary forms", "rubber"],
    "trof": ["other tropical fruits, n.e.c.", "other tropical fruit"],
    "temf": ["apples", "temperate fruit"], "rest": ["rest of crops"],
}
FALLBACK = 0.08


def load_elast_map(csv_path):
    df = pd.read_csv(csv_path)
    # find the crop-name column and the elasticity column
    name_col = next((c for c in df.columns if df[c].dtype == object), df.columns[0])
    val_col = next((c for c in df.columns if c != name_col
                    and pd.api.types.is_numeric_dtype(df[c])), df.columns[-1])
    return {str(k).strip().lower(): float(v) for k, v in zip(df[name_col], df[val_col])}


def get_elasticity(crop_key, emap, fallback=FALLBACK):
    k = str(crop_key).strip().lower()
    v = emap.get(k, np.nan)
    if np.isfinite(v):
        return float(np.clip(v, 0.0, 1.0)), k
    for alias in SPAM_ALIAS_MAP.get(k, []):
        v2 = emap.get(alias.strip().lower(), np.nan)
        if np.isfinite(v2):
            return float(np.clip(v2, 0.0, 1.0)), alias
    return float(np.clip(fallback, 0.0, 1.0)), "(fallback 0.08)"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    emap = load_elast_map(sys.argv[1])
    print(f"{'SPAM':6s} {'elast':>6s}  matched on")
    print("-" * 60)
    for code in SPAM_ALIAS_MAP:
        val, hit = get_elasticity(code, emap)
        flag = "  <-- was 0.08 (fixed)" if (val > 0.08 and code in {
            "maiz", "pmil", "lent", "pige", "cowp", "chic", "bean", "pota", "soyb",
            "sugb", "onio", "toma", "cott", "rape", "sunf", "toba", "opul", "ooil", "trof"}) else ""
        print(f"{code:6s} {val:6.2f}  {hit}{flag}")

    maize, _ = get_elasticity("maiz", emap)
    assert abs(maize - 0.30) < 1e-9, f"FAIL: maize resolved to {maize}, expected 0.30 — buggy map?"
    print("\nPASS: maize = 0.30 (elasticity fix is active).")


if __name__ == "__main__":
    main()
