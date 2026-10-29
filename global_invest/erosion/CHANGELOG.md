# CHANGELOG

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
