#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul 30 11:44:57 2026
Goal: merge csvfiles
@author: x5l
"""

import pandas as pd
from pathlib import Path

# ======================================
# Folder containing the daily CSV files
# ======================================
folder = Path("/Volumes/LaCie/SDSU_PhDwork/work10_Inni_Emission_Water/Data/SM_SMAP_L4")   

# Find all daily CSV files
csv_files = sorted(folder.glob("SM_SMAP_L4_*_months_07_08_09_10_11_monthly.csv"))

print(f"Found {len(csv_files)} daily files:")
for f in csv_files:
    print("  ", f.name)

# Read and merge
dfs = []
for f in csv_files:
    df = pd.read_csv(f)
    dfs.append(df)

merged_df = pd.concat(dfs, ignore_index=True)

# Save
output_file = folder / "SM_SMAP_L4_2020-2025_Jul-Nov_monthly.csv"
merged_df.to_csv(output_file, index=False)

print(f"\nMerged {len(csv_files)} files.")
print(f"Total rows: {len(merged_df):,}")
print(f"Saved to:\n{output_file}")