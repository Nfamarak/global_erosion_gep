#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_eu_comparison.py -- EU-27 GEP vs Panagos (2018) crop-productivity-loss comparison.

Consolidates two legacy notebooks into one script pointed at the conditioned-DEM
archive:
    - eu_gep_ses_eps_3_19_26.ipynb        (build EU-27 subset from integrated_country_gep.csv)
    - gep_jrc_Panagos_comparison.ipynb    (merge vs Panagos, ratios, Fig. 10 charts)

What it does
------------
1. Reads the SES-11 (headline) and EPS-5 (sensitivity) integrated_country_gep.csv
   from the archive results dirs.
2. Extracts the 27 EU member states, writes tidy wide/long/summary CSVs.
3. If the Panagos input CSV is present, converts its 2010-EUR crop-loss figures to
   2019 USD (EU HICP 1.18 x EUR->USD 1.12), merges against the EU-27 GEP, computes
   per-country and EU-total ratios/differences, and renders the comparison figures
   (grouped bars, GEP/Panagos ratio bars, Panagos-vs-GEP scatter) = manuscript Fig. 10.
   If the Panagos CSV is absent, it still produces the EU-27 GEP outputs plus a
   GEP-only EU bar chart, and prints how to supply the Panagos file.

Paths (override any with an env var of the same name)
-----------------------------------------------------
    GEP_ARCHIVE   default /projects/standard/jajohns/shared/nfamara/erosion_global_gep_final
    GEP_SES11_CSV default $GEP_ARCHIVE/results/ses11_headline/integrated_country_gep.csv
    GEP_EPS5_CSV  default $GEP_ARCHIVE/results/eps5_sensitivity/integrated_country_gep.csv
    PANAGOS_CSV   default $GEP_ARCHIVE/eu_comparison/inputs/Panagos_2018_crop_productivity_loss.csv
    EU_OUT_DIR    default $GEP_ARCHIVE/figures/eu_comparison

Panagos input schema (one row per EU country):
    Country, Crop_Productivity_Loss_million_euro_2010   (iso3 optional)

Usage
-----
    python make_eu_comparison.py
"""

from pathlib import Path
from datetime import datetime
import os
import re

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# =============================================================================
# 0) CONFIG (env-overridable; defaults point at the conditioned-DEM archive)
# =============================================================================
ARCHIVE = Path(os.environ.get(
    "GEP_ARCHIVE",
    "/projects/standard/jajohns/shared/nfamara/erosion_global_gep_final"))

SES11_CSV = Path(os.environ.get(
    "GEP_SES11_CSV", ARCHIVE / "results" / "ses11_headline" / "integrated_country_gep.csv"))
EPS5_CSV = Path(os.environ.get(
    "GEP_EPS5_CSV", ARCHIVE / "results" / "eps5_sensitivity" / "integrated_country_gep.csv"))

PANAGOS_CSV = Path(os.environ.get(
    "PANAGOS_CSV", ARCHIVE / "eu_comparison" / "inputs" / "Panagos_2018_crop_productivity_loss.csv"))

OUT_DIR = Path(os.environ.get("EU_OUT_DIR", ARCHIVE / "figures" / "eu_comparison"))
FIG_DIR = OUT_DIR / "figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

# Price/currency conversion for Panagos 2010 EUR -> 2019 USD.
# (Replace with authoritative values if the reviewers request a specific index.)
EU_HICP_2010_TO_2019 = float(os.environ.get("EU_HICP_2010_TO_2019", "1.18"))
EUR_TO_USD_2019 = float(os.environ.get("EUR_TO_USD_2019", "1.12"))

# Colourblind-safe (Okabe-Ito): Panagos=blue, SES-11=orange, EPS-5=green.
C_PAN, C_SES, C_EPS = "#0072B2", "#E69F00", "#009E73"

EU27_ORDER = [
    "AUT", "BEL", "BGR", "HRV", "CYP", "CZE", "DNK", "EST", "FIN",
    "FRA", "DEU", "GRC", "HUN", "IRL", "ITA", "LVA", "LTU", "LUX",
    "MLT", "NLD", "POL", "PRT", "ROU", "SVK", "SVN", "ESP", "SWE",
]
EU27_ISO3 = set(EU27_ORDER)
AGGREGATE_ISO3 = {"GLOBAL", "WORLD", "EU", "EU27", "EU-27", "E27", "EUR", "ALL"}

ISO3_TO_COUNTRY = {
    "AUT": "Austria", "BEL": "Belgium", "BGR": "Bulgaria", "HRV": "Croatia",
    "CYP": "Cyprus", "CZE": "Czechia", "DNK": "Denmark", "EST": "Estonia",
    "FIN": "Finland", "FRA": "France", "DEU": "Germany", "GRC": "Greece",
    "HUN": "Hungary", "IRL": "Ireland", "ITA": "Italy", "LVA": "Latvia",
    "LTU": "Lithuania", "LUX": "Luxembourg", "MLT": "Malta", "NLD": "Netherlands",
    "POL": "Poland", "PRT": "Portugal", "ROU": "Romania", "SVK": "Slovakia",
    "SVN": "Slovenia", "ESP": "Spain", "SWE": "Sweden",
}
COUNTRY_TO_ISO3 = {v: k for k, v in ISO3_TO_COUNTRY.items()}
COUNTRY_TO_ISO3.update({"Czech Republic": "CZE", "The Netherlands": "NLD"})

# =============================================================================
# 1) HELPERS
# =============================================================================
def normalize_col(col):
    return re.sub(r"[^a-z0-9]+", "", str(col).strip().lower())


def clean_numeric(s):
    """Coerce messy currency strings like '$14,587,878,207.01 ' to float."""
    if pd.api.types.is_numeric_dtype(s):
        return pd.to_numeric(s, errors="coerce")
    s = s.astype(str).str.strip()
    for ch in (",", "$", "%"):
        s = s.str.replace(ch, "", regex=False)
    s = s.str.replace(r"[^\d\.\-eE+]", "", regex=True)
    s = s.replace({"": np.nan, "nan": np.nan, "None": np.nan})
    return pd.to_numeric(s, errors="coerce")


def find_col(df, candidates, required=False):
    norm_map = {normalize_col(c): c for c in df.columns}
    for cand in candidates:
        cn = normalize_col(cand)
        if cn in norm_map:
            return norm_map[cn]
    for cand in candidates:
        cn = normalize_col(cand)
        for en, orig in norm_map.items():
            if cn in en or en in cn:
                return orig
    if required:
        raise KeyError(f"Missing column. Tried {candidates}; have {list(df.columns)}")
    return None


def std_country_name(x):
    if pd.isna(x):
        return np.nan
    x = str(x).strip()
    return x.replace("Czech Republic", "Czechia").replace("The Netherlands", "Netherlands")


def sort_eu27(df, iso_col="iso3"):
    out = df.copy()
    order = {iso: i for i, iso in enumerate(EU27_ORDER)}
    out["_o"] = out[iso_col].map(order).fillna(999)
    sec = "Country" if "Country" in out.columns else iso_col
    return out.sort_values(["_o", sec]).drop(columns="_o")


# =============================================================================
# 2) BUILD EU-27 GEP SUBSET FROM THE ARCHIVE
# =============================================================================
def load_scenario(csv_path, scenario):
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing {scenario} input: {csv_path}")
    df = pd.read_csv(csv_path)

    iso_src = find_col(df, ["iso3", "country_iso3", "adm0_a3", "iso_a3"], required=True)
    name_src = find_col(df, ["country_name", "country", "name", "admin"], required=False)
    cc = find_col(df, ["gep_const2019_usd_combined", "combined_gep_usd", "gep_combined"], required=True)
    on = find_col(df, ["gep_const2019_usd_onfarm", "onfarm_gep_usd", "gep_onfarm"], required=False)
    up = find_col(df, ["gep_const2019_usd_upstream", "upstream_gep_usd", "gep_upstream"], required=False)
    gpv = find_col(df, ["crop_gpv_const2019_2019", "crop_gpv_usd", "gpv"], required=False)

    out = pd.DataFrame()
    out["iso3"] = df[iso_src].astype(str).str.upper().str.strip()
    out["country"] = (df[name_src].map(std_country_name) if name_src
                      else out["iso3"].map(ISO3_TO_COUNTRY))
    out["gep_combined_usd"] = clean_numeric(df[cc])
    if on:
        out["gep_onfarm_usd"] = clean_numeric(df[on])
    if up:
        out["gep_upstream_usd"] = clean_numeric(df[up])
    if gpv:
        out["crop_gpv_usd"] = clean_numeric(df[gpv])

    # drop aggregate rows, keep EU-27
    out = out[~out["iso3"].isin(AGGREGATE_ISO3)]
    eu = out[out["iso3"].isin(EU27_ISO3)].copy()
    eu["country"] = eu["country"].fillna(eu["iso3"].map(ISO3_TO_COUNTRY))
    eu = sort_eu27(eu)
    eu["scenario"] = scenario
    if eu["iso3"].nunique() != 27:
        print(f"  WARNING: {scenario} has {eu['iso3'].nunique()}/27 EU countries present")
    return eu


def build_eu_gep():
    ses = load_scenario(SES11_CSV, "SES11")
    eps = load_scenario(EPS5_CSV, "EPS5")

    # long
    long_df = pd.concat([ses, eps], ignore_index=True).sort_values(["iso3", "scenario"])
    long_df.to_csv(OUT_DIR / "EU27_GEP_both_scenarios_long.csv", index=False)

    # wide (merge SES/EPS on iso3)
    def tag(df, t):
        cols = {c: f"{c}_{t}" for c in df.columns if c not in ("iso3", "country", "scenario")}
        return df.drop(columns="scenario").rename(columns=cols)
    wide = tag(ses, "SES11").merge(
        tag(eps, "EPS5").drop(columns="country"), on="iso3", how="outer")
    wide = sort_eu27(wide)
    wide.to_csv(OUT_DIR / "EU27_GEP_both_scenarios_wide.csv", index=False)

    # summary
    def total(df, col):
        return float(df[col].sum()) if col in df.columns else np.nan
    summary = pd.DataFrame([
        {"scenario": "SES11", "n_countries": ses["iso3"].nunique(),
         "combined_gep_usd_sum": total(ses, "gep_combined_usd"),
         "onfarm_gep_usd_sum": total(ses, "gep_onfarm_usd"),
         "upstream_gep_usd_sum": total(ses, "gep_upstream_usd"),
         "crop_gpv_usd_sum": total(ses, "crop_gpv_usd")},
        {"scenario": "EPS5", "n_countries": eps["iso3"].nunique(),
         "combined_gep_usd_sum": total(eps, "gep_combined_usd"),
         "onfarm_gep_usd_sum": total(eps, "gep_onfarm_usd"),
         "upstream_gep_usd_sum": total(eps, "gep_upstream_usd"),
         "crop_gpv_usd_sum": total(eps, "crop_gpv_usd")},
    ])
    summary.to_csv(OUT_DIR / "EU27_GEP_summary_by_scenario.csv", index=False)

    # compact comparison frame used downstream (million USD)
    comp = wide[["iso3", "country"]].copy()
    comp["GEP_SES11_million_USD_2019"] = clean_numeric(wide["gep_combined_usd_SES11"]) / 1e6
    comp["GEP_EPS5_million_USD_2019"] = clean_numeric(wide["gep_combined_usd_EPS5"]) / 1e6
    comp = comp.rename(columns={"country": "Country"})
    comp["Country"] = comp["Country"].map(std_country_name)
    return comp, summary


# =============================================================================
# 3) PANAGOS MERGE (optional)
# =============================================================================
def load_panagos():
    pan = pd.read_csv(PANAGOS_CSV)
    name_col = find_col(pan, ["Country", "country", "country_name"], required=True)
    iso_col = find_col(pan, ["iso3", "ISO3"], required=False)
    loss_col = find_col(pan, ["Crop_Productivity_Loss_million_euro_2010",
                              "crop_productivity_loss_million_euro_2010"], required=True)
    pan[name_col] = pan[name_col].map(std_country_name)
    if iso_col is None:
        pan["iso3"] = pan[name_col].map(COUNTRY_TO_ISO3)
    else:
        pan["iso3"] = pan[iso_col].astype(str).str.upper().str.strip()
        bad = pan["iso3"].isin(["", "NAN", "NONE", "NA"])
        pan.loc[bad, "iso3"] = pan.loc[bad, name_col].map(COUNTRY_TO_ISO3)
    pan["loss_meur_2010"] = clean_numeric(pan[loss_col])
    pan["Panagos_million_USD_2019"] = pan["loss_meur_2010"] * EU_HICP_2010_TO_2019 * EUR_TO_USD_2019
    return pan[["iso3", "loss_meur_2010", "Panagos_million_USD_2019"]]


def merge_and_summarize(comp, pan):
    df = comp.merge(pan, on="iso3", how="outer")
    df["Country"] = df["Country"].fillna(df["iso3"].map(ISO3_TO_COUNTRY))
    den = df["Panagos_million_USD_2019"].replace(0, np.nan)
    df["SES11_to_Panagos_ratio"] = df["GEP_SES11_million_USD_2019"] / den
    df["EPS5_to_Panagos_ratio"] = df["GEP_EPS5_million_USD_2019"] / den
    df["SES11_minus_Panagos_million_USD_2019"] = df["GEP_SES11_million_USD_2019"] - df["Panagos_million_USD_2019"]
    df["EPS5_minus_Panagos_million_USD_2019"] = df["GEP_EPS5_million_USD_2019"] - df["Panagos_million_USD_2019"]
    df = sort_eu27(df)
    df.to_csv(OUT_DIR / "EU_Panagos_vs_GEP_SES11_EPS5.csv", index=False)

    tot = {k: float(df[k].sum()) for k in
           ["Panagos_million_USD_2019", "GEP_SES11_million_USD_2019", "GEP_EPS5_million_USD_2019"]}
    summ = pd.DataFrame([{
        "Panagos_total_million_USD_2019": tot["Panagos_million_USD_2019"],
        "GEP_SES11_total_million_USD_2019": tot["GEP_SES11_million_USD_2019"],
        "GEP_EPS5_total_million_USD_2019": tot["GEP_EPS5_million_USD_2019"],
        "SES11_to_Panagos_ratio_total": tot["GEP_SES11_million_USD_2019"] / tot["Panagos_million_USD_2019"]
            if tot["Panagos_million_USD_2019"] else np.nan,
        "EPS5_to_Panagos_ratio_total": tot["GEP_EPS5_million_USD_2019"] / tot["Panagos_million_USD_2019"]
            if tot["Panagos_million_USD_2019"] else np.nan,
        "EU_HICP_2010_TO_2019": EU_HICP_2010_TO_2019,
        "EUR_TO_USD_2019": EUR_TO_USD_2019,
        "run_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }])
    summ.to_csv(OUT_DIR / "EU_totals_summary_Panagos_vs_GEP.csv", index=False)
    return df, summ


# =============================================================================
# 4) FIGURES
# =============================================================================
def _grouped_bar(df, panagos, title, outfile, topn=None):
    d = df.copy()
    if panagos:
        d = d.dropna(subset=["Panagos_million_USD_2019"])
        d = d[d["Panagos_million_USD_2019"] > 0].sort_values("Panagos_million_USD_2019", ascending=False)
    else:
        d = d.sort_values("GEP_EPS5_million_USD_2019", ascending=False)
    if topn:
        d = d.head(topn)
    x = np.arange(len(d))
    labels = d["Country"].astype(str).tolist()
    fig, ax = plt.subplots(figsize=(max(10, 0.55 * len(d) + 3), 6))
    if panagos:
        w = 0.28
        ax.bar(x - w, d["Panagos_million_USD_2019"], w, label="Panagos loss", color=C_PAN)
        ax.bar(x, d["GEP_SES11_million_USD_2019"].fillna(0), w, label="Erosion-regulation service value (SES-11)", color=C_SES)
        ax.bar(x + w, d["GEP_EPS5_million_USD_2019"].fillna(0), w, label="Erosion-regulation service value (EPS-5)", color=C_EPS)
    else:
        w = 0.4
        ax.bar(x - w / 2, d["GEP_SES11_million_USD_2019"].fillna(0), w, label="Erosion-regulation service value (SES-11)", color=C_SES)
        ax.bar(x + w / 2, d["GEP_EPS5_million_USD_2019"].fillna(0), w, label="Erosion-regulation service value (EPS-5)", color=C_EPS)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=60, ha="right")
    ax.set_ylabel("Million USD (2019)")
    ax.set_title(title)
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(outfile, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return outfile


def _ratio_bar(df, outfile, topn=None):
    d = df.dropna(subset=["Panagos_million_USD_2019"])
    d = d[d["Panagos_million_USD_2019"] > 0].sort_values("Panagos_million_USD_2019", ascending=False)
    if topn:
        d = d.head(topn)
    x = np.arange(len(d))
    w = 0.4
    fig, ax = plt.subplots(figsize=(max(10, 0.55 * len(d) + 3), 6))
    ax.bar(x - w / 2, d["SES11_to_Panagos_ratio"].fillna(0), w, label="SES-11 / Panagos", color=C_SES)
    ax.bar(x + w / 2, d["EPS5_to_Panagos_ratio"].fillna(0), w, label="EPS-5 / Panagos", color=C_EPS)
    ax.axhline(1.0, ls="--", lw=1, color="#555555")
    ax.set_xticks(x)
    ax.set_xticklabels(d["Country"].astype(str).tolist(), rotation=60, ha="right")
    ax.set_ylabel("Service value / Panagos ratio")
    ax.set_title("EU-27: GEP-to-Panagos ratio (dashed = parity)")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(outfile, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return outfile


def _pearson(x, y):
    if len(x) < 2:
        return np.nan
    return float(np.corrcoef(x, y)[0, 1])


def _spearman(x, y):
    if len(x) < 2:
        return np.nan
    rx = pd.Series(x).rank().to_numpy()
    ry = pd.Series(y).rank().to_numpy()
    return float(np.corrcoef(rx, ry)[0, 1])


def _scatter(df, outfile):
    """Correlation scatter: Panagos loss (x) vs SES-11 GEP (y), OLS fit + r, R2, rho."""
    d = df.dropna(subset=["Panagos_million_USD_2019", "GEP_SES11_million_USD_2019"])
    d = d[d["Panagos_million_USD_2019"] > 0]
    x = d["Panagos_million_USD_2019"].to_numpy(float)
    y = d["GEP_SES11_million_USD_2019"].to_numpy(float)

    r = _pearson(x, y)
    rho = _spearman(x, y)
    r2 = r * r
    slope, intercept = np.polyfit(x, y, 1)      # OLS y = slope*x + intercept
    xs = np.linspace(0, x.max() * 1.05, 100)

    fig, ax = plt.subplots(figsize=(7.8, 7.4))
    ax.scatter(x, y, s=55, color=C_SES, edgecolor="white", linewidth=0.6, zorder=3)
    ax.plot(xs, slope * xs + intercept, color=C_PAN, lw=2,
            label=f"OLS fit: y = {slope:.2f}x + {intercept:.0f}")
    ax.plot(xs, xs, ls="--", lw=1, color="#999999", label="1:1 line")

    for _, row in d.sort_values("Panagos_million_USD_2019", ascending=False).head(10).iterrows():
        ax.annotate(row["Country"],
                    (row["Panagos_million_USD_2019"], row["GEP_SES11_million_USD_2019"]),
                    textcoords="offset points", xytext=(6, 3), fontsize=8)

    stat = (f"n = {len(d)}\n"
            f"Pearson r = {r:.3f}\n"
            f"R² = {r2:.3f}\n"
            f"Spearman ρ = {rho:.3f}")
    ax.text(0.03, 0.97, stat, transform=ax.transAxes, va="top", ha="left",
            fontsize=10, family="monospace",
            bbox=dict(boxstyle="round,pad=0.5", fc="#f7f7f7", ec="#cccccc"))

    ax.set_xlabel("Panagos (2018) erosion crop-loss — million USD (2019)")
    ax.set_ylabel("Erosion-regulation service value, SES-11 — million USD (2019)")
    ax.set_title("EU-27: Panagos loss vs erosion-regulation service value")
    ax.legend(frameon=False, loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    fig.tight_layout()
    fig.savefig(outfile, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return outfile


def _fig10_country(df, outfile):
    """Primary Fig. 10: per-country ranked grouped bars (Panagos / SES-11 / EPS-5)."""
    from matplotlib.ticker import FuncFormatter
    d = df.dropna(subset=["Panagos_million_USD_2019"]).sort_values(
        "Panagos_million_USD_2019", ascending=True)
    y = np.arange(len(d))
    hh = 0.40
    tot = {k: float(df[k].sum()) for k in
           ["Panagos_million_USD_2019", "GEP_SES11_million_USD_2019", "GEP_EPS5_million_USD_2019"]}
    fig, ax = plt.subplots(figsize=(9.2, 11))
    ax.barh(y + hh / 2, d["Panagos_million_USD_2019"], hh, color=C_PAN, label="Panagos (2018) erosion crop-loss")
    ax.barh(y - hh / 2, d["GEP_SES11_million_USD_2019"], hh, color=C_SES, label="Erosion-regulation service value (SES-11)")
    ax.set_yticks(y)
    ax.set_yticklabels(d["Country"])
    ax.set_xlabel("Million USD (2019)")
    ax.set_title("EU-27: erosion-regulation service value vs Panagos (2018) erosion crop-loss, by country",
                 fontsize=12, pad=12)
    ax.legend(frameon=False, loc="lower right", fontsize=10)
    ax.spines[["top", "right"]].set_visible(False)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.grid(axis="x", color="#e6e6e6", lw=0.8)
    ax.set_axisbelow(True)
    ax.margins(y=0.01)
    r_ses = tot["GEP_SES11_million_USD_2019"] / tot["Panagos_million_USD_2019"]
    txt = (f"EU-27 totals ($M, 2019)\n"
           f"Panagos:  {tot['Panagos_million_USD_2019']:,.0f}\n"
           f"SES-11:   {tot['GEP_SES11_million_USD_2019']:,.0f}  ({r_ses:.2f}x)")
    ax.text(0.97, 0.50, txt, transform=ax.transAxes, ha="right", va="center",
            fontsize=9.5, family="monospace",
            bbox=dict(boxstyle="round,pad=0.5", fc="#f7f7f7", ec="#cccccc"))
    fig.tight_layout()
    fig.savefig(outfile, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return outfile


def _fig10_panagos_topn(df, outfile, n=15):
    """Fig 10 (focused): top-n EU countries by Panagos loss, SES-11 vs Panagos only."""
    from matplotlib.ticker import FuncFormatter
    d = df.dropna(subset=["Panagos_million_USD_2019"]).sort_values(
        "Panagos_million_USD_2019", ascending=False).head(n).sort_values(
        "Panagos_million_USD_2019", ascending=True)
    y = np.arange(len(d))
    hh = 0.40
    fig, ax = plt.subplots(figsize=(9.0, 8.4))
    ax.barh(y + hh / 2, d["Panagos_million_USD_2019"], hh, color=C_PAN,
            label="Panagos (2018) erosion crop-loss")
    ax.barh(y - hh / 2, d["GEP_SES11_million_USD_2019"], hh, color=C_SES,
            label="Erosion-regulation service value (SES-11)")
    ax.set_yticks(y)
    ax.set_yticklabels(d["Country"])
    ax.set_xlabel("Million USD (2019)")
    ax.set_title(f"Top {n} EU countries by Panagos erosion crop-loss:\n"
                 f"erosion-regulation service value (SES-11) vs Panagos (2018)", fontsize=12, pad=10)
    ax.legend(frameon=False, loc="lower right", fontsize=10)
    ax.spines[["top", "right"]].set_visible(False)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.grid(axis="x", color="#e6e6e6", lw=0.8)
    ax.set_axisbelow(True)
    ax.margins(y=0.01)
    tp = float(d["Panagos_million_USD_2019"].sum())
    ts = float(d["GEP_SES11_million_USD_2019"].sum())
    ax.text(0.97, 0.40, f"Shown-set totals ($M)\nPanagos: {tp:,.0f}\n"
            f"SES-11:  {ts:,.0f}  ({ts/tp:.2f}x)", transform=ax.transAxes,
            ha="right", va="center", fontsize=9.5, family="monospace",
            bbox=dict(boxstyle="round,pad=0.5", fc="#f7f7f7", ec="#cccccc"))
    fig.tight_layout()
    fig.savefig(outfile, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return outfile


def _fig10_diverging(df, outfile):
    """Companion: SES-11 minus Panagos per country (who exceeds / falls short)."""
    d = df.dropna(subset=["Panagos_million_USD_2019"]).copy()
    d["diff"] = d["GEP_SES11_million_USD_2019"] - d["Panagos_million_USD_2019"]
    d = d.sort_values("diff")
    colors = [C_EPS if v >= 0 else C_PAN for v in d["diff"]]
    fig, ax = plt.subplots(figsize=(8.5, 10))
    ax.barh(d["Country"], d["diff"], color=colors)
    ax.axvline(0, color="#333333", lw=0.8)
    ax.set_xlabel("SES-11 service value minus Panagos loss  (Million USD, 2019)")
    ax.set_title("Where erosion-regulation service value exceeds (green) vs falls short of (blue) Panagos",
                 fontsize=12, pad=10)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="x", color="#e6e6e6", lw=0.8)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(outfile, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return outfile


def make_figures(df, have_panagos):
    outs = []
    if have_panagos:
        # Primary manuscript Figure 10 (focused top-15, SES-11 vs Panagos only)
        outs.append(_fig10_panagos_topn(df, FIG_DIR / "Fig10_panagos_top15_SES11.png", n=15))
        # Full EU-27 variant (SES-11 vs Panagos, all countries with a Panagos value)
        outs.append(_fig10_country(df, FIG_DIR / "Fig10_EU27_country_comparison.png"))
        outs.append(_fig10_diverging(df, FIG_DIR / "Fig10b_EU27_diverging.png"))
        outs.append(_grouped_bar(df, True, "EU-27: Panagos loss vs erosion-regulation service value",
                                 FIG_DIR / "EU27_bar_all_Panagos_vs_GEP.png"))
        outs.append(_grouped_bar(df, True, "EU-27: Panagos loss vs service value (top 15 by Panagos)",
                                 FIG_DIR / "EU27_bar_top15_Panagos_vs_GEP.png", topn=15))
        outs.append(_ratio_bar(df, FIG_DIR / "EU27_ratio_all_GEP_to_Panagos.png"))
        outs.append(_ratio_bar(df, FIG_DIR / "EU27_ratio_top15_GEP_to_Panagos.png", topn=15))
        outs.append(_scatter(df, FIG_DIR / "EU27_scatter_Panagos_vs_GEP.png"))
    else:
        outs.append(_grouped_bar(df, False, "EU-27: erosion-regulation service value (SES-11 vs EPS-5)",
                                 FIG_DIR / "EU27_bar_GEP_SES11_vs_EPS5.png"))
    return outs


# =============================================================================
# 5) RUN
# =============================================================================
def main():
    print("=" * 60)
    print("EU-27 COMPARISON  (conditioned-DEM archive)")
    print("=" * 60)
    print(f"SES-11 : {SES11_CSV}")
    print(f"EPS-5  : {EPS5_CSV}")
    print(f"out    : {OUT_DIR}\n")

    comp, gep_summary = build_eu_gep()
    print("EU-27 GEP totals (million USD, 2019):")
    for _, r in gep_summary.iterrows():
        print(f"  {r['scenario']:6s} combined={r['combined_gep_usd_sum']/1e6:10,.1f}  "
              f"(n={int(r['n_countries'])})")

    have_panagos = PANAGOS_CSV.exists()
    if have_panagos:
        pan = load_panagos()
        merged, summ = merge_and_summarize(comp, pan)
        print("\nPanagos comparison (EU-27 totals, million USD 2019):")
        print(f"  Panagos loss : {summ.loc[0,'Panagos_total_million_USD_2019']:12,.1f}")
        print(f"  GEP SES-11   : {summ.loc[0,'GEP_SES11_total_million_USD_2019']:12,.1f}"
              f"   ({summ.loc[0,'SES11_to_Panagos_ratio_total']:.2f}x Panagos)")
        print(f"  GEP EPS-5    : {summ.loc[0,'GEP_EPS5_total_million_USD_2019']:12,.1f}"
              f"   ({summ.loc[0,'EPS5_to_Panagos_ratio_total']:.2f}x Panagos)")
        figs = make_figures(merged, True)
    else:
        print(f"\nNOTE: Panagos input not found at {PANAGOS_CSV}")
        print("      -> wrote EU-27 GEP CSVs + GEP-only bar chart; add the Panagos CSV")
        print("         (columns: Country, Crop_Productivity_Loss_million_euro_2010)")
        print("         to that path (or set $PANAGOS_CSV) and re-run for Fig. 10.")
        figs = make_figures(comp, False)

    print("\nFigures written:")
    for f in figs:
        print("  -", f)
    print("\nDone.")


if __name__ == "__main__":
    main()
