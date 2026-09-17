#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Aug  6 11:39:44 2026

@author: x5l
"""

import os
import numpy as np
import xarray as xr
import calendar

# ==============================================================================
# Helper Functions (converted from readnc.pro, writedat.pro, writehdr.pro)
# ==============================================================================
def read_nc_var(nc_file, var_name):
    """
    Reads raw variable data along with its scale factor and add offset.
    Equivalent to readnc.pro with scale/offset attribute extraction.
    """
    var = nc_file.variables[var_name]
    
    # Read raw data array
    data = var[:].astype(np.float32)
    
    # Get fill value, scale factor, and add offset attributes (if present)
    fill_value = getattr(var, '_FillValue', -32767)
    scale_factor = getattr(var, 'scale_factor', 1.0)
    add_offset = getattr(var, 'add_offset', 0.0)
    
    # Process fill value -> convert to NaN
    data[data == fill_value] = np.nan
    
    # Apply scaling: scaled_value = raw_value * scale_factor + add_offset
    scaled_data = data * scale_factor + add_offset
    
    return scaled_data


def write_dat(outfile, data):
    """
    Writes array to binary float32 file (.dat).
    Equivalent to writedat.pro.
    """
    # Ensure float32 precision and write raw bytes
    data.astype(np.float32).tofile(outfile)


def write_hdr(hdrfile, ncol, nrow):
    """
    Writes ENVI header metadata file (.hdr).
    Equivalent to writehdr.pro.
    """
    content = (
        "ENVI\r\n"
        "description = {File Imported into ENVI.}\r\n"
        f"samples = {ncol}\r\n"
        f"lines   = {nrow}\r\n"
        "bands   = 1\r\n"
        "header offset = 0\r\n"
        "file type = ENVI Standard\r\n"
        "data type = 4\r\n"
        "interleave = bsq\r\n"
        "sensor type = Unknown\r\n"
        "byte order = 0\r\n"
        "x start = 1\r\n"
        "y start = 1\r\n"
        "band names = {WS}\r\n"
        "map info = {Geographic Lat/Lon, 1.0000, 1.0000, 89, 10, 0.25, 0.25, WGS-84, units=Degrees}\r\n"
        "wavelength units = Unknown\r\n"
    )
    with open(hdrfile, "wb") as f:
        f.write(content.encode("latin1"))

# ==============================================================================
# ----Main Processing Script (converted from Wind_ERA5_split2doys.pro)
# ============================================================================== 
year_start, year_end = 2022, 2025
mytime = "0600" #change
  
wind_dir = f"/Volumes/LaCie/SDSU_PhDwork/work0_Done/work7_Inni_Ce_Water_ERL/data/Wind_ERA5/{mytime}"
out_dir = f"/Volumes/LaCie/SDSU_PhDwork/work0_Done/work7_Inni_Ce_Water_ERL/data/Wind_ERA5/{mytime}/Wind_Speed_Direction"

# Loop through each year, loading its respective file
for year in range(year_start, year_end + 1):
    print(f"Processing Year: {year}")

    # 1. Format the file path for the specific year
    file_path = os.path.join(wind_dir, f"ERA5_Wind_{year}_UTC{mytime}.nc")
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}, skipping...")
        continue

    # 2. Open the NetCDF file for the current year
    with xr.open_dataset(file_path) as ds:
        u = ds['u'].squeeze() #squeeze: remove pressure dim
        v = ds['v'].squeeze()

    # Extract dimensions for the current file: [time, nrow, ncol]
    time_dim = 'valid_time' if 'valid_time' in ds.dims else 'time'         
    ntime = ds.sizes[time_dim]    
    nrow = ds.sizes['latitude']
    ncol = ds.sizes['longitude']    
    doy_start = 183 if calendar.isleap(year) else 182

    # Create output directory for the current year
    year_dir = os.path.join(out_dir, str(year))
    os.makedirs(year_dir, exist_ok=True)

    # 3. Process time slices for the current year
    for t in range(ntime):
    # for t in range(5):
        doy = doy_start + t
        doys = f"{doy:03d}"  # Format as 3-digit DOY (e.g., '001', '089', '182')

        u_slice = u.isel(**{time_dim: t}).values
        v_slice = v.isel(**{time_dim: t}).values

        # Vectorized Calculations
        # 1. Wind Speed (WS)
        ws = np.sqrt(u_slice**2 + v_slice**2)

        # 2. Azimuth (Wind direction from which wind originates, in degrees [0, 360))
        azimuth = (np.degrees(np.arctan2(u_slice, v_slice)) + 180.0) % 360.0

        # Output File Paths
        az_outfile = os.path.join(year_dir, f"ERA5_wind_{year}{doys}_azimuth.dat")
        az_hdrfile = os.path.join(year_dir, f"ERA5_wind_{year}{doys}_azimuth.hdr")

        ws_outfile = os.path.join(year_dir, f"ERA5_wind_{year}{doys}_WS.dat")
        ws_hdrfile = os.path.join(year_dir, f"ERA5_wind_{year}{doys}_WS.hdr")

        # Export binary (.dat) and header (.hdr) files
        write_dat(az_outfile, azimuth)
        write_hdr(az_hdrfile, ncol, nrow)

        write_dat(ws_outfile, ws)
        write_hdr(ws_hdrfile, ncol, nrow)



