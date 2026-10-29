#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Publication figures for the global erosion-GEP account
(finer hydrologically conditioned-DEM run; SES-11 headline / EPS-5 sensitivity).

Replaces figures_feb5_2026.ipynb + maps_gep_feb5_2026.ipynb. All figures are saved
as PNG (300 dpi). Standard-figure style: plain-language axes/legends/colorbars,
no value labels on bars, CVD-safe (Okabe-Ito) palette, Equal Earth maps,
Fisher-Jenks bins, full World Bank FY2025 income classification.

Figures produced:
  A. Country charts  -> top-15 value, top-12 GDP-dependence, pathway stack,
                        pathway x threshold, value-vs-GDP scatter, country x crop heatmap
  B. Raster maps     -> combined prevention share, soil erosion (USLE), avoided erosion
  C. Choropleths     -> value (million US$), prevention share, GDP-dependence  [run on MSI]

USAGE:  python make_erosion_gep_figures.py     # edit CONFIG below
Set SCENARIO = "ses11" or "eps5".
"""
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib as mpl; mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm

# =========================== CONFIG — EDIT ===========================
# Reads the consolidated archive and writes figures into <ARCHIVE>/figures/.
SCENARIO   = "ses11"                       # "ses11" (headline) or "eps5" (sensitivity)
ARCHIVE    = Path("/projects/standard/jajohns/shared/nfamara/erosion_global_gep_final")
SCEN_DIR   = {"ses11":"ses11_headline","eps5":"eps5_sensitivity"}[SCENARIO]
PSDIR      = ARCHIVE / "results" / SCEN_DIR
CSV_SES    = ARCHIVE / "results" / "ses11_headline"   / "integrated_country_gep.csv"
CSV_EPS    = ARCHIVE / "results" / "eps5_sensitivity" / "integrated_country_gep.csv"
CROP_CSV   = PSDIR / "country_crop_protected_production_combined.csv"
PS_COMBINED= PSDIR / "ps_combined_union_cropland_severe.tif"
SDR_USLE   = ARCHIVE / "sdr_outputs_conditioned" / "usle_conddem1km_2019.tif"
SDR_AVOID  = ARCHIVE / "sdr_outputs_conditioned" / "avoided_erosion_conddem1km_2019.tif"
BOUNDARY_GPKG = ARCHIVE / "inputs_conditioned" / "valuation" / "country_boundary_r250_with_iso3.gpkg"
FIGDIR     = ARCHIVE / "figures"
# =====================================================================

FIGDIR.mkdir(parents=True, exist_ok=True)
mpl.rcParams.update({"figure.dpi":200,"savefig.dpi":300,"savefig.bbox":"tight","font.size":11,
    "axes.titlesize":12,"axes.titleweight":"bold","axes.labelsize":11,"axes.spines.top":False,
    "axes.spines.right":False,"axes.grid":True,"grid.color":"#E6E6E6","grid.linewidth":0.8,
    "axes.axisbelow":True,"xtick.labelsize":10,"ytick.labelsize":10,"legend.frameon":False,
    "font.family":"DejaVu Sans"})
C_CO,C_UP,C_WARM="#0072B2","#E69F00","#D55E00"
INC_C={"High income":"#0072B2","Upper middle income":"#009E73","Lower middle income":"#E69F00","Low income":"#D55E00"}

# ---- World Bank income classification, FY2025 (2023 GNI per capita, Atlas) ----
WB_INCOME = {
"High income":["ARE","ATG","AUS","AUT","BEL","BGR","BRB","BRN","CAN","CHE","CHL","CYP","CZE","DEU","DNK","ESP",
 "EST","FRA","GBR","GRC","GUY","HRV","HUN","IRL","ISR","ITA","JPN","KNA","KOR","LTU","LUX","LVA","MAC","MLT","NCL",
 "NLD","NOR","NZL","OMN","PAN","POL","PRI","PRT","ROU","RUS","SAU","SGP","SVK","SVN","SWE","TTO","URY","USA"],
"Upper middle income":["ALB","ARG","ARM","AZE","BIH","BLR","BLZ","BRA","CHN","COL","CRI","CUB","DMA","DOM","DZA",
 "ECU","FJI","GAB","GEO","GNQ","GRD","GTM","IDN","IRQ","JAM","KAZ","LBY","LCA","MDA","MEX","MKD","MNE","MYS","PER",
 "PRY","SLV","SRB","SUR","THA","TKM","TUR","VCT","ZAF"],
"Lower middle income":["AGO","BEN","BGD","BOL","BTN","CIV","CMR","COG","DJI","GHA","GIN","HND","HTI","IND","IRN",
 "JOR","KEN","KGZ","KHM","LAO","LBN","LKA","LSO","MAR","MMR","MNG","NGA","NIC","NPL","PAK","PHL","PNG","PSE","SEN",
 "SLB","STP","SWZ","TJK","TLS","TUN","TZA","UKR","UZB","VNM","VUT","ZMB","ZWE"],
"Low income":["AFG","BDI","BFA","CAF","COD","ETH","GMB","GNB","LBR","MDG","MLI","MOZ","MWI","NER","RWA","SDN",
 "SLE","SOM","SYR","TCD","TGO","UGA"],
}
INCOME={iso:grp for grp,lst in WB_INCOME.items() for iso in lst}
SPAM={"sugc":"Sugarcane","vege":"Vegetables","rice":"Rice","maiz":"Maize","pota":"Potato","trof":"Tropical fruit",
 "whea":"Wheat","cass":"Cassava","temf":"Temperate fruit","trmf":"Temperate fruit","oilp":"Oil palm","citr":"Citrus",
 "bana":"Banana","toma":"Tomato","sugb":"Sugar beet","swpo":"Sweet potato","barl":"Barley","cnut":"Coconut",
 "onio":"Onion","soyb":"Soybean","plnt":"Plantain","teas":"Tea","ocer":"Other cereals","orts":"Other roots",
 "rest":"Other crops","rape":"Rapeseed","grou":"Groundnut","sunf":"Sunflower","cott":"Cotton","acof":"Arabica coffee",
 "rcof":"Robusta coffee","coco":"Cocoa","bean":"Bean","chic":"Chickpea","cowp":"Cowpea","pige":"Pigeonpea",
 "lent":"Lentil","opul":"Other pulses","sorg":"Sorghum","pmil":"Pearl millet","smil":"Small millet","yams":"Yam",
 "toba":"Tobacco","rubb":"Rubber","sesa":"Sesame","ofib":"Other fibre crops"}

CC,ON,UP="gep_const2019_usd_combined","gep_const2019_usd_onfarm","gep_const2019_usd_upstream"
IUPS="gep_incremental_upstream_usd"   # combined = onfarm + incremental_upstream (exact)
GDPP,GDP,NAME,SHC="gdp_loss_pct_combined","gdp_const2019_2019","country_name","share_protected_production_combined"
B_B=1e9; LABEL={"ses11":"SES-11","eps5":"EPS-5"}; TAG=LABEL[SCENARIO]

def load(csv):
    d=pd.read_csv(csv); d["income"]=d["iso3"].map(INCOME); return d

# ================================ A. COUNTRY CHARTS ================================
def _barh(df,col,n,color,xlabel,title,path,div=1.0):
    d=df[df[col]>0].sort_values(col,ascending=False).head(n).iloc[::-1]
    fig,ax=plt.subplots(figsize=(7.2,0.42*len(d)+1.1))
    ax.barh(d[NAME].astype(str),d[col]/div,color=color,height=0.72); ax.grid(axis="y",visible=False)
    ax.set_xlabel(xlabel); ax.set_title(title); fig.savefig(path); plt.close(fig)

def country_charts(A,B):
    _barh(A,CC,15,C_CO,"Value protected (billion US$ per year)",
          f"Value of crop production protected from erosion (top countries, {TAG})",
          FIGDIR/f"fig_top15_value_protected_{SCENARIO}.png",B_B)
    _barh(A,GDPP,12,C_WARM,"Share of national GDP (%)",
          f"Economic dependence on erosion regulation (top countries, {TAG})",
          FIGDIR/f"fig_top12_gdp_dependence_{SCENARIO}.png")
    # stacked pathway: on-farm + ADDITIONAL from upstream = combined (exact)
    d=A[A[CC]>0].sort_values(CC,ascending=False).head(15).iloc[::-1]
    fig,ax=plt.subplots(figsize=(7.4,6.2))
    ax.barh(d[NAME].astype(str),d[ON]/B_B,color=C_CO,label="On-farm protection")
    ax.barh(d[NAME].astype(str),d[IUPS]/B_B,left=d[ON]/B_B,color=C_UP,label="Additional protection from upstream")
    ax.grid(axis="y",visible=False); ax.set_xlabel("Value protected (billion US$ per year)")
    ax.set_title(f"On-farm protection and the extra contribution from upstream (top countries, {TAG})")
    ax.legend(loc="lower right"); fig.savefig(FIGDIR/f"fig_pathway_stack_{SCENARIO}.png"); plt.close(fig)
    # pathway x threshold
    fig,ax=plt.subplots(figsize=(6.4,4.2)); cats=["On-farm","Upstream","Combined"]; x=np.arange(3); w=0.38
    s=[A[ON].sum()/B_B,A[UP].sum()/B_B,A[CC].sum()/B_B]; e=[B[ON].sum()/B_B,B[UP].sum()/B_B,B[CC].sum()/B_B]
    ax.bar(x-w/2,s,w,label="SES-11 (stricter threshold)",color=C_CO); ax.bar(x+w/2,e,w,label="EPS-5 (broader threshold)",color=C_UP)
    ax.set_xticks(x); ax.set_xticklabels(cats); ax.grid(axis="x",visible=False)
    ax.set_ylabel("Global value (billion US$ per year)"); ax.set_title("Protected value by pathway and erosion threshold")
    ax.legend(loc="upper left"); fig.savefig(FIGDIR/"fig_decomposition_threshold.png"); plt.close(fig)
    # value vs GDP, by income group
    d=A[(A[CC]>0)&(A[GDP]>0)].copy()
    fig,ax=plt.subplots(figsize=(7.2,5.5))
    for grp,color in INC_C.items():
        g=d[d["income"]==grp]
        if len(g): ax.scatter(g[GDP],g[CC],s=28,color=color,alpha=0.85,edgecolors="white",linewidths=0.4,label=grp)
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("National GDP, 2019 (US$, log scale)"); ax.set_ylabel("Value protected (US$, log scale)")
    ax.set_title(f"Protected value versus national GDP ({TAG})"); ax.grid(True,which="both",color="#EEEEEE")
    for _,r in d.sort_values(CC,ascending=False).head(6).iterrows():
        ax.annotate(str(r[NAME])[:16],(r[GDP],r[CC]),fontsize=7.5,color="#444",xytext=(4,3),textcoords="offset points")
    ax.legend(loc="lower right",fontsize=8.5,title="World Bank income group",title_fontsize=8.5)
    fig.savefig(FIGDIR/f"fig_value_vs_gdp_income_{SCENARIO}.png"); plt.close(fig)

def heatmap_country_crop(A):
    if not Path(CROP_CSV).exists(): print("skip heatmap (missing crop csv)"); return
    cr=pd.read_csv(CROP_CSV); cr=cr[cr["component"]=="combined"]
    topc=A.sort_values(CC,ascending=False).head(15)["iso3"].tolist()
    topk=cr.groupby("crop")["protected_production_tons"].sum().sort_values(ascending=False).head(12).index.tolist()
    piv=(cr[cr["ISO3"].isin(topc)&cr["crop"].isin(topk)]
         .pivot_table(index="ISO3",columns="crop",values="protected_production_tons",aggfunc="sum")
         .reindex(index=topc,columns=topk))
    nm=dict(zip(A["iso3"],A[NAME])); M=piv.values.astype(float); M[np.isnan(M)]=0; M[M<=0]=np.nan
    fig,ax=plt.subplots(figsize=(9.2,6.6))
    im=ax.imshow(M,aspect="auto",cmap="YlGnBu",norm=LogNorm(vmin=np.nanmin(M),vmax=np.nanmax(M)))
    ax.set_xticks(range(len(topk))); ax.set_xticklabels([SPAM.get(k,k) for k in topk],rotation=40,ha="right")
    ax.set_yticks(range(len(topc))); ax.set_yticklabels([str(nm.get(i,i))[:18] for i in topc]); ax.grid(False)
    ax.set_title(f"Protected crop production by country and crop ({TAG})")
    cb=fig.colorbar(im,ax=ax,fraction=0.03,pad=0.02); cb.set_label("Protected production (tonnes per year)")
    fig.savefig(FIGDIR/f"fig_heatmap_country_crop_{SCENARIO}.png"); plt.close(fig)

# ================================ B. RASTER MAPS ================================
def _read(path,maxpix=1600):
    import rasterio; from rasterio.enums import Resampling
    with rasterio.open(path) as ds:
        sc=max(ds.height/maxpix,ds.width/maxpix,1.0); oh,ow=int(ds.height/sc),int(ds.width/sc)
        arr=ds.read(1,out_shape=(oh,ow),resampling=Resampling.average).astype("float32"); nod=ds.nodata; b=ds.bounds
    m=np.ma.masked_invalid(arr)
    if nod is not None: m=np.ma.masked_equal(m,nod)
    return np.ma.masked_less_equal(m,0),b

def raster_maps():
    if Path(PS_COMBINED).exists():
        m,b=_read(PS_COMBINED)
        fig,ax=plt.subplots(figsize=(11,5.6)); cmap=plt.get_cmap("YlGnBu").copy(); cmap.set_bad("#F4F4F4")
        im=ax.imshow(m,extent=[b.left,b.right,b.bottom,b.top],cmap=cmap,vmin=0,vmax=1,interpolation="nearest")
        ax.set_axis_off(); ax.set_title(f"Share of erosion prevented on severe-erosion cropland ({TAG})")
        cb=fig.colorbar(im,ax=ax,fraction=0.025,pad=0.01); cb.set_label("Share of erosion prevented")
        cb.set_ticks([0,.25,.5,.75,1]); cb.ax.set_yticklabels(["0 (none)","0.25","0.50","0.75","1 (all)"])
        fig.savefig(FIGDIR/f"fig_map_prevention_share_{SCENARIO}.png",dpi=240); plt.close(fig)
    for path,title,cmap,out in [
        (SDR_USLE,"Modelled soil erosion on cropland (2019)","YlOrBr",FIGDIR/"fig_map_soil_erosion.png"),
        (SDR_AVOID,"Avoided erosion from vegetation (2019)","YlGn",FIGDIR/"fig_map_avoided_erosion.png")]:
        if not Path(path).exists(): print("skip raster (missing):",path); continue
        m,b=_read(path); ml=np.ma.log10(m)
        fig,ax=plt.subplots(figsize=(11,5.6)); cm=plt.get_cmap(cmap).copy(); cm.set_bad("#F4F4F4")
        im=ax.imshow(ml,extent=[b.left,b.right,b.bottom,b.top],cmap=cm,interpolation="nearest")
        ax.set_axis_off(); ax.set_title(title)
        cb=fig.colorbar(im,ax=ax,fraction=0.025,pad=0.01); cb.set_label("Soil erosion (tonnes per hectare per year)")
        tk=[0,1,2,3,4]; cb.set_ticks(tk); cb.ax.set_yticklabels([f"{10**t:,.0f}" for t in tk])
        fig.savefig(out,dpi=240); plt.close(fig)

# ================================ C. CHOROPLETHS (MSI) ================================
def choropleths():
    try:
        import geopandas as gpd, mapclassify  # noqa
    except Exception as e:
        print("geopandas/mapclassify not available -> skipping choropleths:",e); return
    df=pd.read_csv(CSV_SES if SCENARIO=="ses11" else CSV_EPS); g=gpd.read_file(BOUNDARY_GPKG)
    isoc=next((c for c in ["iso3","ISO3","iso_a3","adm0_a3","ADM0_A3"] if c in g.columns),g.columns[0])
    g=g.merge(df,left_on=isoc,right_on="iso3",how="left")
    try: g=g.to_crs("EPSG:8857")
    except Exception: pass
    def choro(col,title,legend_title,out,cmap="YlGnBu",k=6):
        gg=g.copy(); gg[col]=pd.to_numeric(gg[col],errors="coerce")
        fig,ax=plt.subplots(figsize=(12,6.2)); ax.set_axis_off()
        gg.boundary.plot(ax=ax,linewidth=0.15,color="#888",alpha=0.5)
        gg[gg[col].notna()].plot(column=col,ax=ax,legend=True,cmap=cmap,scheme="FisherJenks",k=k,
            legend_kwds={"loc":"lower left","fontsize":8,"title":legend_title,"title_fontsize":8,"fmt":"{:,.0f}"},
            missing_kwds={"color":"#F0F0F0"})
        ax.set_title(title); fig.savefig(out,dpi=240,bbox_inches="tight"); plt.close(fig)
    g["value_musd"]=pd.to_numeric(g[CC],errors="coerce")/1e6
    choro("value_musd",f"Value of crop production protected from erosion ({TAG})","Million US$ per year",
          FIGDIR/f"map_value_protected_{SCENARIO}.png")
    choro(SHC,f"Share of crop production protected ({TAG})","Share (0-1)",
          FIGDIR/f"map_share_protected_{SCENARIO}.png",cmap="YlGn")
    choro(GDPP,f"Economic dependence on erosion regulation ({TAG})","% of GDP",
          FIGDIR/f"map_gdp_dependence_{SCENARIO}.png",cmap="OrRd")

if __name__=="__main__":
    A=load(CSV_SES); B=load(CSV_EPS); primary=A if SCENARIO=="ses11" else B
    miss=sorted(set(primary[primary[CC]>0]["iso3"])-set(INCOME))
    if miss: print("WARNING unclassified countries (add to WB_INCOME):",miss)
    print(f"[A] country charts ({TAG})"); country_charts(primary,B); heatmap_country_crop(primary)
    print("[B] raster maps");            raster_maps()
    print("[C] choropleths");            choropleths()
    print("done -> all PNGs in",FIGDIR)
