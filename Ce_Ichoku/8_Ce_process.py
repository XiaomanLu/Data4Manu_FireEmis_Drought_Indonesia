import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


# ============================================================
# FILES
# ============================================================
Ce_DIR = (
    "/Volumes/LaCie/SDSU_PhDwork/work0_Done/work7_Inni_Ce_Water_ERL/"
    "figures/Fig5_Fig8_FigS1_Rsa_FRP_Scatterplot/"
    "work10_Rsa_FRP_Scatterplot_2002_2020_Eachyear_MergeRegion/"
    "Eachyear2_NewWD_rmOutlier/version_006/"
)
Cefile = Ce_DIR + "Ce_Annual_Merged_Sumatra_Kalimatan_v006.xlsx"
Outfile = Ce_DIR + "Ce_Annual_Merged_Sumatra_Kalimatan_v006_Filled.csv"

ERA5Land_file = (
    "/Volumes/LaCie/SDSU_PhDwork/work10_Inni_Emission_Water/Data" +
    "/SM_ERA5_LAND/SM_ERA5_LAND_2003-2025_Jul-Nov_yearly.csv"
)


# ============================================================
# READ DATA
# ============================================================
df_Ce = pd.read_excel(Cefile)
df_SM = pd.read_csv(ERA5Land_file)


# ============================================================
# SET Ce TO NaN IF p > 0.01
# ============================================================
df_Ce.loc[df_Ce["pvalue"] > 0.01, "beta1"] = np.nan


# ============================================================
# MERGE Ce AND SOIL MOISTURE BY YEAR
# ============================================================
df = df_Ce.merge(
    df_SM,
    left_on="year",
    right_on="Year",
    how="left"
)


# Select corresponding SM:
# peatID = 1 -> peatland
# peatID = 0 -> non-peatland
df["SM"] = np.where(
    df["peatID"] == 1,
    df["SM_ERA5_LAND_p1"],
    df["SM_ERA5_LAND_p0"]
)


# ============================================================
# SCATTER PLOT Ce AND SM (before filled)
# ============================================================
fig, ax = plt.subplots(figsize=(6, 5))

for peatID, label in [
    (0, "Non-peatland"),
    (1, "Peatland")
]:
    temp = df[
        (df["peatID"] == peatID) &
        df["beta1"].notna() &
        df["SM"].notna()
    ]

    ax.scatter(
        temp["SM"],
        temp["beta1"],
        label=label
    )

ax.set_xlabel(r"Soil moisture (m$^3$ m$^{-3}$)")
ax.set_ylabel("Ce")
ax.legend(frameon=False)

plt.tight_layout()
plt.show()


# ============================================================
# FILL NaN Ce USING YEAR WITH CLOSEST SOIL MOISTURE
# ============================================================
df["Ce_filled"] = df["beta1"]
df["Ce_source_year"] = np.nan

for peatID in [0, 1]:
    
    # Valid years that can be used as donors
    valid = df[
        (df["peatID"] == peatID) &
        df["beta1"].notna() &
        df["SM"].notna()
    ]

    # Years with missing Ce
    missing = df[
        (df["peatID"] == peatID) &
        df["beta1"].isna() &
        df["SM"].notna()
    ]

    for idx in missing.index:

        target_SM = df.loc[idx, "SM"]

        # Find year with closest SM
        closest_idx = (
            (valid["SM"] - target_SM)
            .abs()
            .idxmin()
        )

        # Fill Ce
        df.loc[idx, "Ce_filled"] = valid.loc[
            closest_idx, "beta1"
        ]

        # Record which year was used
        df.loc[idx, "Ce_source_year"] = valid.loc[
            closest_idx, "year"
        ]


# ============================================================
# CHECK FILLED VALUES
# ============================================================
Outdf = df[
    [
        "year",
        "Regionname",
        "peatID",
        "SM",
        "beta1",
        "Ce_filled",
        "Ce_source_year"
    ]
]
print(Outdf)

# Save to CSV
Outdf.to_csv(Outfile, index=False)
print(f"Saved to: {Outfile}")


# ============================================================
# SCATTER PLOT Ce AND SM (after filled)
# ============================================================
fig, ax = plt.subplots(figsize=(6, 5))

for peatID, label in [
    (0, "Non-peatland"),
    (1, "Peatland")
]:
    temp = df[
        (df["peatID"] == peatID) &
        df["Ce_filled"].notna() &
        df["SM"].notna()
    ]

    ax.scatter(
        temp["SM"],
        temp["Ce_filled"],
        label=label
    )

ax.set_xlabel(r"Soil moisture (m$^3$ m$^{-3}$)")
ax.set_ylabel("Ce")
ax.legend(frameon=False)

plt.tight_layout()
plt.show()




