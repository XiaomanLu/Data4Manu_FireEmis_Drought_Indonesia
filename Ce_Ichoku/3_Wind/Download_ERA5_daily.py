#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Aug  6 11:06:08 2026

@author: x5l
"""
#TIP: cp ~/.cdsapirc_cds_for_ERA5 ~/.cdsapirc in terminal before running this code. 
# Use ads to download GFAS: cp ~/.cdsapirc_ads_for_GFAS ~/.cdsapirc
# Use cds to download ERA5: cp ~/.cdsapirc_cds_for_ERA5 ~/.cdsapirc

#%% ERA5 Wind (25km)
# TIP: ERA5-Land does not provide pressure-level variables. ERA5-Land provides land-surface and near-surface variables such as 10 m winds.
from __future__ import annotations
import logging
from calendar import monthrange
from pathlib import Path
import cdsapi

# ============================================================
# USER SETTINGS
# ============================================================
START_YEAR = 2022
END_YEAR = 2025
MONTHS = [7, 8, 9, 10, 11]
PRESSURE_LEVEL_HPA = "925"
DOWNLOAD_TIME = "06:00" #options: ["03:00" and "06:00"]
AREA = [10, 89, -11, 153] # [North, West, South, East]

mytime = DOWNLOAD_TIME.replace(":", "")  # "03:00" -> "0300"
OUTDIR = Path(f"/Volumes/LaCie/SDSU_PhDwork/work0_Done/work7_Inni_Ce_Water_ERL/data/Wind_ERA5/{mytime}")
OVERWRITE = False

# ============================================================
# DATASET SETTINGS
# ============================================================
# ERA5-Land does not provide pressure-level variables.
# For 925-hPa winds, use ERA5 hourly pressure-level data.
DATASET = "reanalysis-era5-pressure-levels"
VARIABLES = [
    "u_component_of_wind",
    "v_component_of_wind",
]


# ============================================================
# DOWNLOAD ONE MONTH
# ============================================================
def download_year(
    client: cdsapi.Client,
    year: int,
) -> Path:
    """
    Download ERA5 925-hPa winds at one UTC hour for July-November.

    The resulting yearly NetCDF file contains one timestep per day
    at DOWNLOAD_TIME for all available days from July through November.
    """

    output_file = (
        OUTDIR
        / f"ERA5_Wind_{year}_UTC{mytime}.nc"
    )

    if output_file.exists() and not OVERWRITE:
        print(f"Skipping existing file: {output_file}")
        return output_file

    request = {
        "product_type": ["reanalysis"],
        "variable": VARIABLES,
        "pressure_level": [PRESSURE_LEVEL_HPA],
        "year": [str(year)],
        "month": MONTHS,
        
        # The CDS accepts this common day list for multiple months.
        # Dates that do not exist, such as November 31, are omitted.
        "day": [
            f"{day:02d}"
            for day in range(1, 32)
        ],

        "time": [DOWNLOAD_TIME],
        "area": AREA,
        "data_format": "netcdf",
        "download_format": "unarchived",
    }

    print(
        f"Downloading ERA5 winds for {year}: "
        f"July-November, "
        f"{PRESSURE_LEVEL_HPA} hPa, "
        f"{DOWNLOAD_TIME} UTC"
    )

    client.retrieve(
        DATASET,
        request,
        str(output_file),
    )

    if (
        not output_file.exists()
        or output_file.stat().st_size == 0
    ):
        raise RuntimeError(
            "Download finished, but the output file is "
            f"missing or empty: {output_file}"
        )

    print(f"Finished: {output_file}")
    return output_file


# ============================================================
# MAIN
# ============================================================
def main() -> None:
    if START_YEAR > END_YEAR:
        raise ValueError(
            "START_YEAR must be less than or equal to END_YEAR."
        )

    OUTDIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    client = cdsapi.Client()
    downloaded_files = []

    for year in range(START_YEAR, END_YEAR + 1):
        try:
            output_file = download_year(
                client=client,
                year=year,
            )
            downloaded_files.append(output_file)

        except Exception as error:
            print(f"Failed for {year}: {error}")

    print("\n" + "=" * 60)
    print("All requested downloads finished.")
    print(f"Number of yearly files: {len(downloaded_files)}")

    for output_file in downloaded_files:
        print(f"  {output_file}")


if __name__ == "__main__":
    main()




#%% (Not used) ERA5 Soil Moisture (25km)
# TIP: I used ERA5 Land SM and VPD (9km) from GEE directly
import os
import logging
logging.disable(logging.CRITICAL)
import cdsapi
import warnings
warnings.filterwarnings("ignore")
from calendar import monthrange
client = cdsapi.Client()

years = list(range(2022, 2026))
months = ["07", "08", "09", "10", "11"]

dataset = "derived-era5-single-levels-daily-statistics"
outdir = '/Volumes/LaCie/SDSU_PhDwork/work10_Inni_Emission_Water/Data/SM_ERA5/raw/'

for year in years:
    for month in months:    
        print(f"Downloading {year}-{month}...")
    
        num_days = monthrange(int(year), int(month))[1]
        days = [f"{d:02d}" for d in range(1, num_days + 1)]
        outfile = outdir + f"ERA5_SM2_{year}_{month}_daily.nc"
        
        if not os.path.exists(outfile):
            request = {
                "product_type": "reanalysis",
                "variable": [
                    "volumetric_soil_water_layer_2"
                ],
                "year": year,
                "month": month,
                "day": days,
                "daily_statistic": "daily_mean",
                "time_zone": "utc+00:00",
                "frequency": "1_hourly",
                "area": [6, 95, -6, 120],
                "data_format": "netcdf",
            }
        
            try:
                client.retrieve(dataset, request, outfile)
                print("Finished")    
            except Exception as e:
                print("Failed")
                print(e)

print("=" * 60)
print("All downloads completed.")









