#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Aug  9 22:39:56 2026

@author: x5l
"""
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import pearsonr
from pathlib import Path
import matplotlib.dates as mdates
import matplotlib.colors as mcolors

scale = "monthly"

DIR = '/Volumes/LaCie/SDSU_PhDwork/work10_Inni_Emission_Water/Data'
Out_file = (
    Path(DIR)
    / ".."
    / "Code_and_Figures/Figures"
    / "FigS_SM_Compare_2003-2025"
    / f"SM_Compare_2003-2025_{scale}.png"
).resolve()

# read SM files
SMOS_file = DIR + f'/SM_SMOS/SM_SMOS_2010_2023_Jul-Nov_{scale}.csv' #SM_SMOS
SMAPL4_file = DIR + f'/SM_SMAP_L4/SM_SMAP_L4_2015-2025_Jul-Nov_{scale}.csv'
ERA5Land_file = DIR + f'/SM_ERA5_LAND/SM_ERA5_LAND_2003-2025_Jul-Nov_{scale}.csv'
df_SMOS = pd.read_csv(SMOS_file)
df_SMAPL4 = pd.read_csv(SMAPL4_file)
df_ERA5L = pd.read_csv(ERA5Land_file)


# ============================================================
# CREATE DATE column
# ============================================================
def add_date_column(df):
    df = df.copy()
    
    if scale=="monthly":
        df["Date"] = pd.to_datetime(
            dict(
                year=df["Year"],
                month=df["Month"],
                day=1
            )
        )
    else:
        df["Date"] = pd.to_datetime(
            dict(
                year=df["Year"],
                month=1,
                day=1
            )
        )

    return df.sort_values("Date")

df_SMOS = add_date_column(df_SMOS)
df_SMAPL4 = add_date_column(df_SMAPL4)
df_ERA5L = add_date_column(df_ERA5L)


# ============================================================
# FORMAT P VALUE
# ============================================================
def format_pvalue(p):
    if p < 0.001:
        return "p<0.001"
    elif p < 0.01:
        return "p<0.01"
    elif p < 0.05:
        return "p<0.05"
    else:
        return f"p={p:.3f}"


# ============================================================
# Calcualte Correlation
# ============================================================
def calculate_corr_overlaptime(df_SMOS, df_SMAPL4, df_ERA5L):
    # ============================================================
    # MERGE THREE PRODUCTS
    # Only months/years available in ALL three products are retained
    # ============================================================
    df_overlap = (
        df_SMOS[["Date", "SM_SMOS"]]
        .merge(
            df_SMAPL4[["Date", "SM_SMAP_L4"]],
            on="Date",
            how="inner"
        )
        .merge(
            df_ERA5L[["Date", "SM_ERA5_LAND"]],
            on="Date",
            how="inner"
        )
        .dropna()
        .sort_values("Date")
    )
    
    
    # ============================================================
    # CALCULATE PEARSON CORRELATIONS
    # ============================================================
    r_ERA5L_SMOS, p_ERA5L_SMOS = pearsonr(
        df_overlap["SM_ERA5_LAND"],
        df_overlap["SM_SMOS"]
    )
    
    r_SMAPL4_SMOS, p_SMAPL4_SMOS = pearsonr(
        df_overlap["SM_SMAP_L4"],
        df_overlap["SM_SMOS"]
    )
    
    
    print("\nOverlap period:")
    print(
        df_overlap["Date"].min().strftime("%Y-%m"),
        "to",
        df_overlap["Date"].max().strftime("%Y-%m")
    )
    
    print(f"Number of overlapping months: {len(df_overlap)}")
    
    print("\nPearson correlations:")
    print(
        f"ERA5-Land vs SMOS: "
        f"r = {r_ERA5L_SMOS:.3f}, "
        f"{format_pvalue(p_ERA5L_SMOS)}"
    )
    
    print(
        f"SMAP L4 vs SMOS:  "
        f"r = {r_SMAPL4_SMOS:.3f}, "
        f"{format_pvalue(p_SMAPL4_SMOS)}"
    )
    
    return r_ERA5L_SMOS, p_ERA5L_SMOS, r_SMAPL4_SMOS, p_SMAPL4_SMOS
r_ERA5L_SMOS, p_ERA5L_SMOS, r_SMAPL4_SMOS, p_SMAPL4_SMOS = calculate_corr_overlaptime(df_SMOS, df_SMAPL4, df_ERA5L)



# ============================================================
# PLOT TIME SERIES
# ============================================================
fig, ax = plt.subplots(figsize=(7.5, 3))
myalpha = 0.8

# SMOS
ax.plot(
    df_SMOS["Date"],
    df_SMOS["SM_SMOS"],
    linestyle="dotted",
    color="gray",
    linewidth=1,
    marker="o",
    markersize=5,
    markeredgecolor="darkorange",    
    markerfacecolor=mcolors.to_rgba("moccasin", alpha=myalpha),
    markeredgewidth=1.2,
    label="SMOS"
)

# SMAP L4
ax.plot(
    df_SMAPL4["Date"],
    df_SMAPL4["SM_SMAP_L4"],
    linestyle="dotted",
    color="gray",
    linewidth=1,
    marker="o",
    markersize=5,
    markeredgecolor="dodgerblue",
    markerfacecolor=mcolors.to_rgba("lightskyblue", alpha=myalpha),   
    markeredgewidth=1.2,
    label="SMAP L4"
)

# ERA5 Land
ax.plot(
    df_ERA5L["Date"],
    df_ERA5L["SM_ERA5_LAND"],    
    linestyle="dotted",
    color="gray",
    linewidth=1,
    marker="o",
    markersize=5,
    markeredgecolor="firebrick",    
    markerfacecolor=mcolors.to_rgba("lightcoral", alpha=myalpha),
    markeredgewidth=1.2,
    label="ERA5 Land"
)

# ============================================================
# ADD CORRELATION TEXT
# ============================================================
text_corr = (
    f"ERA5-Land vs SMOS: "
    f"r = {r_ERA5L_SMOS:.2f}, "
    f"{format_pvalue(p_ERA5L_SMOS)}\n"
    f"SMAP L4 vs SMOS: "
    f"r = {r_SMAPL4_SMOS:.2f}, "
    f"{format_pvalue(p_SMAPL4_SMOS)}"
)

ax.text(
    0.02,
    0.14,
    text_corr,
    transform=ax.transAxes,
    ha="left",
    va="top",
    fontsize=8,
    bbox=dict(
        facecolor="white",
        alpha=0.8,
        edgecolor="none"
    )
)


# ============================================================
# FIGURE SETTINGS
# ============================================================
ax.set_xlim(pd.Timestamp("2002-06-01"), pd.Timestamp("2026-06-01"))
ax.set_ylim(0.15, 0.5)

ax.set_xlabel("Year", fontsize=10)
ax.set_ylabel("Soil moisture (m³/m³)", fontsize=10)

# Set 2-year tick interval and smaller tick labels
ticks = pd.date_range("2003-01-01", "2025-12-31", freq="2YS")
ax.set_xticks(ticks)
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

ax.tick_params(axis="both", labelsize=8)
plt.setp(ax.get_xticklabels(), rotation=0, ha="center")

ax.legend(
    loc="upper left",
    # frameon=False,
    ncol=3, 
    fontsize=8    
)

plt.tight_layout()

# ============================================================
# SAVE FIGURE
# ============================================================
plt.savefig(
    Out_file,
    dpi=300,
    bbox_inches="tight"
)

plt.show()

