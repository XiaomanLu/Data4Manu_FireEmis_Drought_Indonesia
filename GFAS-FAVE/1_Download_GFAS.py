#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug  4 22:35:47 2026

@author: x5l
"""

from __future__ import annotations
import calendar
import time
from datetime import date
from pathlib import Path
import cdsapi 
#TIP: cp ~/.cdsapirc_ads_for_GFAS ~/.cdsapirc in terminal before running this code. 
# Use ads to download GFAS: cp ~/.cdsapirc_ads_for_GFAS ~/.cdsapirc
# Use cds to download ERA5: cp ~/.cdsapirc_cds_for_ERA5 ~/.cdsapirc


# ============================================================
# USER SETTINGS
# ============================================================
# NOTE: it takes ~1mins to download daily data in each month.
START_DATE = date(2021, 11, 1)
END_DATE = date(2025, 11, 30)
KEEP_MONTHS = [7, 8, 9, 10, 11]

VARIABLES = [
    # "wildfire_radiative_power",
    
]

OUTPUT_DIR = Path(    
    "/Volumes/LaCie/SDSU_PhDwork/"
    # "work10_Inni_Emission_Water/Data/GFASv12_FRP_Global/0_Rawdata_nc_fireseason"
    "/work0_Done/work9_Inni_BBE_RSE/Data/Figures/Figure11_Evaluate_PM25_by_OtherInventories/GFAS_v12_PM25_flux"
)

OVERWRITE = False
MAX_RETRIES = 3
RETRY_SECONDS = 30


# ============================================================
# DATE HELPERS
# ============================================================
def iter_months(start_date: date, end_date: date):
    """Yield year and month pairs intersecting the requested period."""
    year = start_date.year
    month = start_date.month

    while (year, month) <= (end_date.year, end_date.month):
        yield year, month

        month += 1
        if month == 13:
            month = 1
            year += 1


def month_date_range(
    year: int,
    month: int,
    start_date: date,
    end_date: date,
) -> tuple[date, date]:
    """Return the requested portion of a calendar month."""
    first_day = date(year, month, 1)
    last_day = date(year, month, calendar.monthrange(year, month)[1])

    request_start = max(first_day, start_date)
    request_end = min(last_day, end_date)

    return request_start, request_end


# ============================================================
# DOWNLOAD
# ============================================================
def download_gfas_month(
    client: cdsapi.Client,
    year: int,
    month: int,
    start_date: date,
    end_date: date,
) -> Path:
    """Download one month of daily GFAS data into one NetCDF file."""
    request_start, request_end = month_date_range(
        year=year,
        month=month,
        start_date=start_date,
        end_date=end_date,
    )

    output_file = OUTPUT_DIR / f"{year}{month:02d}.nc"

    if output_file.exists() and not OVERWRITE:
        print(f"Skipping existing file: {output_file}")
        return output_file

    request = {
        "variable": VARIABLES,
        "date": [
            f"{request_start.isoformat()}/{request_end.isoformat()}"
        ],
        "data_format": "netcdf",
    }

    print(
        f"Downloading {request_start.isoformat()} through "
        f"{request_end.isoformat()} -> {output_file.name}"
    )

    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            client.retrieve(
                "cams-global-fire-emissions-gfas",
                request,
                str(output_file),
            )

            if not output_file.exists() or output_file.stat().st_size == 0:
                raise RuntimeError(
                    f"Downloaded file is missing or empty: {output_file}"
                )

            print(
                f"Completed: {output_file.name} "
                f"({output_file.stat().st_size / 1024**2:.1f} MB)"
            )
            return output_file

        except Exception as error:
            last_error = error
            print(
                f"Attempt {attempt}/{MAX_RETRIES} failed for "
                f"{year}-{month:02d}: {error}"
            )

            if output_file.exists():
                output_file.unlink()

            if attempt < MAX_RETRIES:
                time.sleep(RETRY_SECONDS)

    raise RuntimeError(
        f"Failed to download {year}-{month:02d} after "
        f"{MAX_RETRIES} attempts."
    ) from last_error


def main():
    if START_DATE > END_DATE:
        raise ValueError("START_DATE must be on or before END_DATE.")

    # This ADS version ends on 3 December 2025.
    dataset_end = date(2025, 12, 3)
    if END_DATE > dataset_end:
        raise ValueError(
            "The ADS GFAS v1.2 dataset ends on 2025-12-03. "
            "Use the newer ECMWF Data Portal product for later dates."
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    client = cdsapi.Client()
    downloaded_files = []

    for year, month in iter_months(START_DATE, END_DATE):
        if month not in KEEP_MONTHS:
            continue
        print(year, month)

        output_file = download_gfas_month(
            client=client,
            year=year,
            month=month,
            start_date=START_DATE,
            end_date=END_DATE,
        )
        downloaded_files.append(output_file)

    print("\nFinished downloading GFAS data.")
    print(f"Number of monthly files: {len(downloaded_files)}")

    for output_file in downloaded_files:
        print(f"  {output_file}")


if __name__ == "__main__":
    main()
    
    
    
    
    
    
    