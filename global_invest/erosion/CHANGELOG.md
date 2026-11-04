# CHANGELOG

## 2026-11-04 — Valuation-from-shares task tree (`GEP_EROSION_TASK_TREE=value_from_shares`)

Re-value a completed run without recomputing the biophysical layer. The new task tree
reads an existing run's `country_crop_protected_production_long.csv` and values each
component (onfarm/upstream/combined) with the **same** `compute_country_gep_from_country_crop`
the full pipeline uses, so results are identical to a valuation re-run on those shares —
but it finishes in seconds instead of hours (no InVEST SDR, no prevention-share recompute).
Inputs: `GEP_EROSION_SHARES_LONG_CSV` (required) and optional `GEP_EROSION_BASELINE_INTEGRATED_CSV`
(carries non-valuation context columns through). Honours `GEP_EROSION_VALUATION_MODE`
(`percrop` for the harmonized values). Wired via `erosion_tasks.task_value_from_shares`
and `erosion_functions.integrate_and_write_from_shares`. A preflight that validates all
inputs (existence, schema, components, writable output) is in `msi/preflight_value_from_shares.py`.

**Authoritative harmonized results (percrop, on the 1 km conditioned shares):**

| Scenario | Harmonized `percrop` (headline) | Countries (>0) |
|---|---|---|
| SES-11 (headline) | **59.913 bn** | 169 |
| EPS-5 (sensitivity) | **106.012 bn** | 172 |

**Method decomposition (combined, 2019 USD) — so the comparator is not confused with the
pre-correction basis:**

| Basis | SES-11 | EPS-5 |
|---|---|---|
| `shock_x_gpv`, national-aggregate, **pre-crop-fix** (archived/submitted) | 44.478 bn | 80.140 bn |
| `shock_x_gpv`, national-aggregate, **with crop-fixes** (current code) | 52.660 bn¹ | not separately recomputed |
| `percrop`, per-crop harmonized (**headline**) | 59.913 bn | 106.012 bn |

¹ SES-11 crop-fixed national-aggregate independently reproduced (C. port + `verify_cropfix_gep.py`).
Running the current code in `shock_x_gpv` mode reproduces this, not the 44.478 figure. The pure
effect of per-crop valuation (holding the crop-fixes constant) is 52.66 → 59.9 bn.

SES-11 decomposition: on-farm 47.883, upstream 48.038, combined 59.913 bn (2019 USD).
Country coverage is 169/172 (vs 171/174 under `shock_x_gpv`): Taiwan (TWN) and Macao (MAC)
are not valued because the common `crop_provision` value table flags all their rows
out-of-account (`in_crop_provision_account=false`); together <1% of the global total. The
harmonized account therefore mirrors the common crop-provision account's country coverage.

The default valuation mode is now **`percrop`** (was `shock_x_gpv`); `shock_x_gpv` remains
selectable as the prior basis / robustness comparator.

## 2026-11-03 — Harmonized per-crop valuation mode (`GEP_EROSION_VALUATION_MODE=percrop`)

New valuation mode that aligns erosion with the common GTAP-InVEST `crop_provision`
pipeline and removes the within-country aggregation approximation. Default behaviour is
unchanged (`shock_x_gpv`).

- **`run_erosion.py`** reads `GEP_EROSION_TASK_TREE` (full | calculation | **valuation** |
  results) and `GEP_EROSION_VALUATION_MODE` (`shock_x_gpv` default | `percrop`). The
  `valuation` tree runs the prevention-share + valuation step only (no InVEST SDR, no
  figures), reading the conditioned `VAL_USLE`/`VAL_AVOIDED` rasters.
- **`percrop`** computes `ERSV_k = Σ_c value_usd[c,k] × share_protected[c,k] × elasticity[c]`,
  where `value_usd` is the per-crop crop value (current-2019 USD, production × price) from the
  common crop_provision table (`fao_values_2019_production_x_price.csv`), keeping only rows
  flagged `in_crop_provision_account` (so byproducts/no-price items — cotton seed, palm kernels —
  are excluded at source). FAO items map to SPAM via the shared correspondence
  (`fao_item_spam2020_crop_correspondence.csv`; `GEP_EROSION_FAO_SPAM_CROSSWALK_CSV`), which may
  map one FAO code to several SPAM crops (pooled, e.g. millet → mill+pmil, coffee → coff+rcof);
  pooled value is split across those crops by SPAM production tonnes. The embedded
  `CROP_ITEM_CODE_TO_SPAM` is a fallback if the correspondence CSV is absent. Set the value table
  with `GEP_EROSION_PERCROP_VALUE_CSV`.
- This supersedes the erosion-GPV crop-selection / price-dedup fixes below (crop selection,
  prices, and currency handling now come from the common FAO pipeline); the corrected per-crop
  elasticities and the biophysical shares are unchanged, so it is a valuation-only re-run.
- **Impact (indicative, submitted-era shares):** adopting the common per-crop values is the
  dominant effect (~+31% to combined GEP), per-crop aggregation adds ~+9% (combined ~+39%),
  with large country redistribution toward high-value, high-erosion-shock economies. Rerun
  both scenarios for the authoritative totals on current shares; keep results in a separate
  `*_harmonized` folder from the `shock_x_gpv` crop-fix results.

## 2026-11-03 — Valuation corrections (crop selection, price dedup, missing-as-NaN)

Three fixes in `erosion_functions.py`, identified during an independent reproduction
of the valuation. They touch only the monetary valuation layer; the biophysical
prevention and shock shares are unchanged.

1. **Crop selection.** `_filter_crops_only` now selects the FAOSTAT **"Crops"
   aggregate (item group 2041)** by item code (`CROP_ITEM_CODES_2041`, 143 items in the
   QV input), replacing a substring name filter that (a) missed 64 crop items and
   (b) wrongly matched *Meat of goat* / *Raw milk of goats* via the `oat` token.
   See `crop_item_codes_2041.csv`.
2. **Duplicate price rows.** `prices.drop_duplicates()` before the fallback price
   averages (the input has 80 fully identical rows: 52 CHE + 28 SRB).
3. **Missing vs zero.** GEP no longer coerces a missing crop GPV to $0
   (`crop_gpv * shock`, no `fillna(0)`), so ten territories (AND, GUF, GLP, XKX, LIE,
   MTQ, MCO, SMR, ESH, ALA) report missing rather than zero. No effect on the total.

**Headline impact:** SES-11 combined moves from **$44.478 bn → ~$52.660 bn**
(crop selection +$8.242 bn, price dedup −$0.061 bn); EPS-5 rises proportionally.
Rerun the valuation for both scenarios; `verify_cropfix_gep.py` reproduces the SES-11
total from the existing shares as a fast pre-check.

## 2026-08-27 — Corrected build (elasticity name-matching fix)

### What changed
`erosion_functions.py` → `SPAM_ALIAS_MAP` now lists the **exact FAOSTAT item
name first** for every crop, with the previous short names kept as backups.

**Why.** The elasticity table (`elasticity_crops_fao_revised.csv`) is keyed on
FAOSTAT item names (e.g. `"Maize (corn)"`, `"Potatoes"`, `"Sugar cane"`), but the
old alias list used short names (`"maize"`, `"potato"`, `"sugarcane"`). When a
name did not match, `get_elasticity_for_crop()` silently returned the 0.08
fallback. In the submitted run this affected **19 of 46 crops** — most
importantly **maize**, which ran at 0.08 instead of its true **0.30**.

No other logic changed. The severity thresholds (11 / 2 t ha⁻¹ yr⁻¹, 50 000 km²,
250 m), the on-farm / upstream / combined prevention shares, the union formula,
the production-weighted shock, the MIN_SHOCK_FLOOR, and the GPV/GDP valuation are
all identical to the submitted pipeline.

### Crops whose elasticity changes (old → corrected)

| ε 0.08 → 0.30 | ε 0.08 → 0.15 |
|---|---|
| maize, pearl millet, dry bean, chickpea, cowpea, pigeon pea, lentil | potato, soybean, sugar beet, onion, tomato, cotton, rapeseed, sunflower, tobacco, other pulses, other oil crops, other tropical fruit |

The other 27 crops are unchanged. Groundnut, vegetables, sugarcane, cassava,
banana, coconut, sweet potato, and the SPAM catch-alls (other cereals / other
roots / rest of crops) legitimately remain at 0.08 — the elasticity table has no
higher value for them.

### Expected results impact (SES-11, combined) — verify by re-running
Recomputation from the archived per-crop shares (the old path reproduces the
submitted $14.588 B exactly, so the delta is clean):

| Quantity | Submitted (buggy) | Corrected |
|---|---|---|
| Global combined GEP | $14.59 B | **$18.09 B (+24%)** |
| China | $2.97 B | $3.61 B (+22%) |
| India | $1.10 B | $1.34 B (+22%) |
| Indonesia | $0.85 B | $1.03 B (+21%) |
| Ethiopia | $0.78 B | $1.12 B (+43%) |
| Burundi (% GDP) | 3.01% | 4.02% |
| Sierra Leone (% GDP) | 4.25% | 4.30% |

The qualitative story is unchanged (value concentrates in large economies;
relative dependence peaks in low-income states; top rankings barely reorder), but
the headline total, the abstract range, several country values, and Figs. 5–6
change. Update the manuscript, SI, and figures from the authoritative re-run.

### How to verify the fix before the full run
```bash
python verify_elasticity_fix.py /path/to/elasticity_crops_fao_revised.csv
# asserts maize resolves to 0.30 and prints the full old→new table; no hazelbean needed
```

### Provenance
- Bug identified and fixed in a parallel refactor (C. — "Set A"); this build
  applies that fix to the standalone pipeline ("Set B") that produced the
  submitted results, changing only the alias map.
- Recommended follow-up (not applied here, does not affect the r250 run): adopt
  Set A's per-country area aggregation before the small-country threshold test
  (matters only if the boundary file changes from r250 to a split-territory file
  such as r264), and port Set A's unit tests.
