import os
import numpy as np
import pandas as pd
import time

# Helper functions
def deg2km(deg):
    """Converts degrees to kilometers"""
    return deg * (6371.0087714 * np.pi / 180.0)


# not used in the new version 061
def frp_fun(frp, sample):
    """FRP calculation for AF data during 2002-2020."""
    j = sample + 1
    N = 1354  # number of pixels in each row of image swath
    Re = 6378.137  # km, radius of the earth
    h = 705  # km, altitude of MODIS satellite
    p = 1.0  # km, pixel nadir resolution

    r = Re + h
    s = p / h

    angle = -0.5 * N * s + 0.5 * s + (j - 1) * s
    tmp = np.sqrt((Re / r) ** 2 - (np.sin(angle)) ** 2)

    deta_s = Re * s * (np.cos(angle) / tmp - 1)
    deta_t = r * s * (np.cos(angle) - tmp)
    area = deta_s * deta_t  # km2

    return frp / area


def frp_fun2(frp, scan, track):
    """FRP calculation for AF data in 2021 (using scan and track size)."""
    area = scan * track  # km2
    return frp / area



# ---- Main Script 
latlon_dir = "/Volumes/LaCie/SDSU_PhDwork/work0_Done/work7_Inni_Ce_Water_ERL/data/LatLon/"
af_dir = "/Volumes/LaCie/SDSU_PhDwork/work0_Done/work7_Inni_Ce_Water_ERL/data/AF_Inni/2_rawdata_rm_dup/"
out_dir = "/Volumes/LaCie/SDSU_PhDwork/work0_Done/work7_Inni_Ce_Water_ERL/data/AF_Inni/3_AFdata_with_Tileloc/"
os.makedirs(out_dir, exist_ok=True)

products = ["MYD14", "MOD14"]
YEAR_START = 2015
YEAR_END = 2021
# years = list(range(YEAR_START, YEAR_END+1))
years = [2021]


# Define MODIS tiles to load
tile_names = [
    "h27v08",
    "h27v09",
    "h28v08",
    "h28v09",
    "h29v08",
    "h29v09",
    "h30v08",
    "h30v09",
    "h31v08",
    "h31v09",
    "h32v08",
    "h32v09",
]

# Read MODIS tile lat/lon CSV files into dictionaries
lat_dict = {}
lon_dict = {}

for t in tile_names:
    lat_dict[t] = np.loadtxt(
        os.path.join(latlon_dir, f"Lat_{t}_Central_degree.csv"), delimiter=","
    )
    lon_dict[t] = np.loadtxt(
        os.path.join(latlon_dir, f"Lon_{t}_Central_degree.csv"), delimiter=","
    )

# Loop over years
for year in years:  
    for product in products:    
        print(year, product)
        start_time = time.perf_counter()
        years_str = str(year)        
        
        version = "061"    
        af_file = os.path.join(
            af_dir, f"{years_str}_{product}_{version}_interscan_corrected_INDOESIA.csv"
        )
        out_file = os.path.join(
            out_dir, f"{years_str}_{product}_{version}_interscan_corrected_INDOESIA.csv"
        )
    
        # Read AF file
        af_data = pd.read_csv(af_file)
    
        # Initialize new columns
        af_data["Tiles"] = None
        af_data["AODj"] = np.nan
        af_data["AODi"] = np.nan
        af_data["Dis_m"] = np.nan
        af_data["FRPnew_MW"] = np.nan
    
        # Find Tiles, AODj, AODi, Dis_m for each row
        for i, row in af_data.iterrows():
        # for i, row in af_data.head(10).iterrows():  #test 5 rows
            z_lat = row["Latitude"]
            z_lon = row["Longitude"]
    
            if z_lat >= 0:
                tile_arr = [
                    "h27v08",
                    "h28v08",
                    "h29v08",
                    "h30v08",
                    "h31v08",
                    "h32v08",
                ]
            else:
                tile_arr = [
                    "h27v09",
                    "h28v09",
                    "h29v09",
                    "h30v09",
                    "h31v09",
                    "h32v09",
                ]
    
            for tile in tile_arr:
                lat = lat_dict[tile]
                lon = lon_dict[tile]
    
                err = (z_lat - lat) ** 2 + (z_lon - lon) ** 2
    
                # Find row (line) and column index of minimum error
                min_idx = np.unravel_index(np.argmin(err), err.shape)
                line_lat, col_lat = min_idx[0], min_idx[1]
    
                # In Python, 0-indexed values match MATLAB's (1-indexed - 1)
                aod_j = col_lat
                aod_i = line_lat
    
                if 0 < aod_j < 1199 and 0 < aod_i < 1199:
                    af_data.at[i, "Tiles"] = tile
                    af_data.at[i, "AODj"] = aod_j
                    af_data.at[i, "AODi"] = aod_i
                    af_data.at[i, "Dis_m"] = deg2km(err[line_lat, col_lat]) * 1000
    
        # version 061 only include scan and track    
        af_data["FRPnew_MW"] = frp_fun2(
            af_data["FRP.MW."], af_data["scan"], af_data["track"]
        )
    
        # Export to CSV
        af_data.to_csv(out_file, index=False)
        
        # running time
        end_time = time.perf_counter()
        elapsed_mins = (end_time - start_time) / 60  
        print(f"Completed in {elapsed_mins:.2f} minutes")
    
    
    
    
    
    
    
    
    
    
    
    