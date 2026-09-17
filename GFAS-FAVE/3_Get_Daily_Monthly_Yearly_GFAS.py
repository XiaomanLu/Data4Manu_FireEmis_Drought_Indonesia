#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug  4 15:44:29 2026

@author: x5l
"""
import pandas as pd
from pathlib import Path

Califactor_TPM_scale_dict = {
    "daily": 1.72,
    "monthly": 1.88,
    "yearly": 1.92   
    }
Califactor_count_scale_dict = {
    "daily": 2.81,
    "monthly": 2.95,
    "yearly": 3.10  
    }


#----MAIN
Dir = Path("/Volumes/LaCie/SDSU_PhDwork/work10_Inni_Emission_Water/Data/GFASv12_FRP_Global")
in_dir = Dir / "1_Annual_eachObs_csv"

scales = ["daily", "monthly", "yearly"]
for myscale in scales:  
    # myscale = "yearly" 
    Outfile = Dir / f"GFAS-FAVE_FRE_TPM_2003_2025_{myscale}.csv"
    
    ### merge infiles
    csv_files = sorted(in_dir.glob("*_GFAS-FAVE_FRE_TPM_LC.csv")) 
    df_list = [pd.read_csv(f, encoding="latin1") for f in csv_files]
    df = pd.concat(df_list, ignore_index=True)
    
    
    ### Perform the grouping and sum up specified columns
    # min_count=1 ensures that if all values in a group for a column are NA, the sum remains NA instead of becoming 0
    if myscale == "daily":
        groupIDs = ["Year", "Month", "Day", "Peat"]
    elif myscale == "monthly":
        groupIDs = ["Year", "Month", "Peat"]
    elif myscale == "yearly":
        groupIDs = ["Year", "Peat"] 
    
    grouped_df = (
        df.groupby(groupIDs)[
            ["FRE_J", "GridArea_km2", "TPM_Gg"]
        ]
        .sum(min_count=1)
        .reset_index()
    )
    grouped_df["FireCount"] = df.groupby(groupIDs).size().values
    
    
    ### Calibration GFAS agains AHI_VIIRS (Calibration factor is from Fig. S7)
    grouped_df['Califactor_TPM'] = Califactor_TPM_scale_dict[myscale]
    grouped_df['Califactor_count'] = Califactor_count_scale_dict[myscale]      
    grouped_df['TPM_Gg_Calibrated'] = grouped_df['TPM_Gg'] * grouped_df['Califactor_TPM']
    grouped_df['FireCount_Calibrated'] = grouped_df['FireCount'] * grouped_df['Califactor_count']      
    
    ### Calculate Emission Intensity 
    grouped_df["Emis_Intensity_g/m2"] = (
        grouped_df["TPM_Gg_Calibrated"] / grouped_df["GridArea_km2"] * 1e3  #convert Gg/km2 to g/m2
    )
    
    ### Save to a new CSV file 
    grouped_df.to_csv(Outfile, index=False)
    
    
    
    
    
    