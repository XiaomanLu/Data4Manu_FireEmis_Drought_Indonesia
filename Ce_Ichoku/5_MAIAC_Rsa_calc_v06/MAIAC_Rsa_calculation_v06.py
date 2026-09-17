import calendar
import time
import csv
import glob
import math
import os
import numpy as np
import pandas as pd
import rasterio
from pyhdf.SD import SD, SDC
from datetime import date
import warnings
warnings.filterwarnings('ignore')

# ==============================================================================
# USER CONFIGURATION SECTION
# ==============================================================================
# Processing years and months
YEAR_START = 2019
YEAR_END = 2025
MONTHS = [7, 8, 9, 10, 11]  # List of months to process (e.g., 1 to 12)
# MONTHS = [7]

# File Directories
BASE_DIR = "/Volumes/LaCie/SDSU_PhDwork/work0_Done/work7_Inni_Ce_Water_ERL/data"
WIND_DIR = os.path.join(BASE_DIR, "wind_ERA5")
AOD_DIR = os.path.join(BASE_DIR, "MAIAC_AOD_Inni") 
AF_DIR = os.path.join(BASE_DIR, "AF_Inni/3_AFdata_with_Tileloc") 
OUT_DIR = os.path.join(BASE_DIR, "Rsa_v06_NewWD_test")


# Spatial parameters
SPATIAL_RES = 926.62543  # Spatial resolution in meters
PIXEL_AREA = SPATIAL_RES * SPATIAL_RES  # Pixel area in m^2
BETA = 4.6  # Mass extinction efficiency in m^2/g
# ==============================================================================

def requested_doy_bounds(
    year: int,
    start_month: int = MONTHS[0],
    end_month: int = MONTHS[-1],
) -> tuple[int, int]:
    start_date = date(year, start_month, 1)

    end_day = calendar.monthrange(year, end_month)[1]
    end_date = date(year, end_month, end_day)

    start_doy = start_date.timetuple().tm_yday
    end_doy = end_date.timetuple().tm_yday

    return start_doy, end_doy


def qa_for_aod(qa_array):
    """Extract QA flags for Cloud Mask (QACM) and AOD Quality (QAAOD) from

    MAIAC MCD19A2 AOD_QA bitmask.
    """
    qa_uint = qa_array.astype(np.uint16)

    # Cloud Mask: Bits 0-2
    qacm = qa_uint & 0b0000000000000111

    # AOD QA: Bits 8-11
    qaaod = (qa_uint >> 8) & 0b0000000000001111

    # Apply fill value (254) where QA is zero
    qacm[qa_uint == 0] = 254
    qaaod[qa_uint == 0] = 254

    return qaaod, qacm


def l_calculation(x):
    """Calculates effective path length L in a 3x3 window based on wind angle x

    (radians).
    """
    a = 1.5 * SPATIAL_RES

    if (x <= np.pi / 4) or (x > np.pi * 7 / 4 and x <= np.pi * 2):
        return 1.0 * a / math.cos(x)
    elif np.pi / 4 < x <= np.pi * 3 / 4:
        return 1.0 * a / math.sin(x)
    elif np.pi * 3 / 4 < x <= np.pi * 5 / 4:
        return -1.0 * a / math.cos(x)
    elif np.pi * 5 / 4 < x <= np.pi * 7 / 4:
        return -1.0 * a / math.sin(x)
    return 0.0


def rate(smokemean, ws, L):
    """Calculates rate of smoke aerosol emission (Rsa in g/s)."""
    # Residence time T
    if ws > 1.0:
        T = 1.0 * L / ws
    else:
        T = 1e9

    if smokemean > 0.02:
        md = 0.001 * smokemean / BETA  # g/m^2 (0.001 is scale factor)
        msa = md * 4.0 * PIXEL_AREA
        rsa = msa / T  # g/s
    else:
        rsa = 0.0

    return rsa


def mymin(x, qaaod, qacm):
    """Finds minimum background AOD value satisfying quality control criteria."""
    valid_mask = (x >= 0) & (qaaod >= 0) & (qaaod <= 4) & (qacm == 1)
    valid_vals = x[valid_mask]
    bg_count = len(valid_vals)

    if bg_count > 0:
        bg_aod = float(np.min(valid_vals))
    else:
        bg_aod = 5000.0

    return bg_aod, bg_count


def mymean(x, qaaod, qacm):
    """Calculates mean smoke AOD value satisfying quality control criteria."""
    valid_mask = (x > 0) & (qaaod >= 0) & (qaaod <= 4) & (qacm == 1)
    valid_vals = x[valid_mask]
    fg_count = len(valid_vals)

    if fg_count > 0:
        smokemean = float(np.mean(valid_vals))
    else:
        smokemean = 0.0

    return smokemean, fg_count


def aod_cal(aod550, qaaod, qacm, j, i, kk, x):
    """Extracts foreground and background window values depending on wind angle

    x.

    Dimensions indexed as: [kk (orbit), i (row), j (column)].
    """
    if 0 <= x <= np.pi / 2:
        fg_coords = [(j, i), (j + 1, i), (j, i - 1), (j + 1, i - 1)]
        bg_coords = [
            (j - 1, i - 1),
            (j - 1, i),
            (j - 1, i + 1),
            (j, i + 1),
            (j + 1, i + 1),
        ]
    elif np.pi / 2 < x <= np.pi:
        fg_coords = [(j, i), (j + 1, i), (j, i + 1), (j + 1, i + 1)]
        bg_coords = [
            (j - 1, i - 1),
            (j - 1, i),
            (j - 1, i + 1),
            (j, i - 1),
            (j + 1, i - 1),
        ]
    elif np.pi < x <= np.pi * 3 / 2:
        fg_coords = [(j, i), (j - 1, i), (j - 1, i + 1), (j, i + 1)]
        bg_coords = [
            (j - 1, i - 1),
            (j, i - 1),
            (j + 1, i - 1),
            (j + 1, i),
            (j + 1, i + 1),
        ]
    elif np.pi * 3 / 2 < x <= np.pi * 2:
        fg_coords = [(j, i), (j - 1, i), (j, i - 1), (j - 1, i - 1)]
        bg_coords = [
            (j - 1, i + 1),
            (j, i + 1),
            (j + 1, i + 1),
            (j + 1, i),
            (j + 1, i - 1),
        ]
    else:
        fg_coords, bg_coords = [], []

    fg_aod = np.array([aod550[kk, c_i, c_j] for c_j, c_i in fg_coords])
    fg_qaaod = np.array([qaaod[kk, c_i, c_j] for c_j, c_i in fg_coords])
    fg_qacm = np.array([qacm[kk, c_i, c_j] for c_j, c_i in fg_coords])

    bg_aod = np.array([aod550[kk, c_i, c_j] for c_j, c_i in bg_coords])
    bg_qaaod = np.array([qaaod[kk, c_i, c_j] for c_j, c_i in bg_coords])
    bg_qacm = np.array([qacm[kk, c_i, c_j] for c_j, c_i in bg_coords])

    return fg_aod, fg_qaaod, fg_qacm, bg_aod, bg_qaaod, bg_qacm


def extract_pointval(raster_path, longitude, latitude):
    """Extracts pixel value from raster file at (longitude, latitude)."""
    try:
        with rasterio.open(raster_path) as src:
            vals = list(src.sample([(longitude, latitude)]))
            return float(vals[0][0])
    except Exception:
        return 0.0
    
def convert_061_to_006(hhmm):
    """
    Convert MODIS Collection 6.1 acquisition time
    to the Collection 6 time.

    Examples
    --------
    147  -> 145
    323  -> 320
    1544 -> 1540
    1837 -> 1835
    659  -> 655
    1917 -> 1915
    208  -> 205
    1534 -> 1530
    """

    hour = hhmm // 100
    minute = hhmm % 100

    minute = (minute // 5) * 5

    return hour * 100 + minute


#---- main
# ==============================================================================
# MAIN PROCESSING CODE (Updated to match MAIAC_Rsa_calculation_v06.pro)
# ==============================================================================
os.makedirs(OUT_DIR, exist_ok=True)

for year in range(YEAR_START, YEAR_END + 1): 
    time_start = time.perf_counter()
    
    year_str = str(year)
    outfile = os.path.join(OUT_DIR, f"{year_str}_MAIAC_Rsa_FRP.csv")
    os.makedirs(os.path.dirname(outfile), exist_ok=True)  
    
    # CSV Header matching IDL printf line 
    header = [
        "Year",
        "DOY",
        "Sensor",
        "HHMM",
        "Tile",
        "Latitude",
        "Longitude",
        "AFConfidence",      
        "FRP",
        "Rsa",
        "CenterAOD",
        "CenterQAAOD",
        "bgAOD",
        "smokemean",
        "WS",
        "fgcount",
        "bgcount",
        "Dis_m",
        "FRPnew_MW",
    ]
    with open(outfile, "w", newline="") as f:
      writer = csv.writer(f)
      writer.writerow(header)
    
    start_doy, end_doy = requested_doy_bounds(year, MONTHS[0], MONTHS[-1]) 
    
    aod_files = sorted(glob.glob(os.path.join(AOD_DIR, year_str, "MCD19A2.A*")))  
    af_files = glob.glob(os.path.join(AF_DIR, f"{year}_M*D14_*_interscan_corrected_INDOESIA.csv"))
    
    for af_file in af_files:
        af_data_yr = pd.read_csv(af_file)        
    
        for idx, aod_file in enumerate(aod_files):
          base_name = os.path.basename(aod_file)
          tile1 = base_name[17:23]  # strmid(Afilename, 17, 6) [cite: 93]
          doynum = int(base_name[13:16])  # fix(strmid(Afilename, 13, 3)) [cite: 93]
      
          if start_doy <= doynum <= end_doy:
            doys = str(doynum)
            print(f"Processing Year {year}, DOY {doys}")
      
            sd = None
            try:
              sd = SD(aod_file, SDC.READ)
      
              # Retrieve Orbit_time_stamp attribute safely 
              all_attrs = sd.attributes()
              attr_data = all_attrs.get("Orbit_time_stamp")
      
              if attr_data is None:
                # Fallback to index 3 (equivalent to IDL HDF_SD_AttrInfo, FileID, 3) 
                _, _, _, attr_data = sd.attr(3).info()
      
              if isinstance(attr_data, bytes):
                attr_data = attr_data.decode("utf-8")
      
              orbits = attr_data.strip().split()
              orbit_no = len(orbits)
      
              # Read AOD550 dataset 
              sds_aod = sd.select("Optical_Depth_055")
              aod550 = sds_aod.get().astype(np.float32)
      
              # Handle Fill Values (-28672 -> NaN) [cite: 94-95]
              fill_mask = aod550 == -28672
              aod550[fill_mask] = np.nan
      
              # Read QA dataset [cite: 95]
              sds_qa = sd.select("AOD_QA")
              qa = sds_qa.get()
              qaaod, qacm = qa_for_aod(qa)
      
            except Exception as err:
              print(f"Error reading HDF file {aod_file}: {err}")
              continue
            finally:
              # Close HDF handle immediately after loading datasets 
              if sd is not None:
                sd.end() 
            
              
            ### AF data
            af_data = af_data_yr[af_data_yr.DOY == doynum] #subset for one day
            af_data[['AODj', 'AODi']] = af_data[['AODj', 'AODi']].fillna(0)     
              
            for _, row in af_data.iterrows():          
                start_time = row['HHMM'] 
                start_time = convert_061_to_006(start_time)
                latitude = float(row['Latitude'])  
                longitude = float(row['Longitude'])  
                # frp = row['FRP_MW_']                  
                frp = row.get('FRP_MW_') or row.get('FRP.MW.')                
                confidence = row['Confidence']           
                tile2 = str(row['Tiles'])            
                j = int(row['AODj'])  
                i = int(row['AODi'])  
                dis_m = row['Dis_m']  
                frpnew_mw = row['FRPnew_MW']           
              
                for kk in range(orbit_no):
                  orbit_name = orbits[kk]
                  doyd = int(orbit_name[4:7])  # strmid(Orbitname, 4, 3) 
                  sensor = orbit_name[11:12]  # strmid(Orbitname, 11, 1) 
                  orbit_hhmm = int(
                      orbit_name[7:11]
                  )  # strmid(Orbitname, 7, 4) [cite: 99]                  
                  # print(start_time, orbit_name, orbit_hhmm)
              
                  # Match overpass time and tile location [cite: 101]
                  if ((start_time == orbit_hhmm) and (tile1 == tile2) and (0 < j < 1199) and (0 < i < 1199)):
                    # Wind files setup [cite: 99-100]
                    sub_dir = "0300" if sensor == "T" else "0600"
                    ws_file = os.path.join(
                        WIND_DIR,
                        f"{sub_dir}/Wind_Speed_Direction/{year_str}/ERA5_wind_{base_name[9:16]}_WS.dat",
                    )
                    az_file = os.path.join(
                        WIND_DIR,
                        f"{sub_dir}/Wind_Speed_Direction/{year_str}/ERA5_wind_{base_name[9:16]}_azimuth.dat",
                    )
              
                    # Extract wind speed & direction [cite: 102]
                    ws = extract_pointval(ws_file, longitude, latitude)
                    az = extract_pointval(az_file, longitude, latitude)
              
                    # Extract scalar float values
                    ws_val = ws[0] if isinstance(ws, (list, np.ndarray)) else ws
                    az_val = az[0] if isinstance(az, (list, np.ndarray)) else az
              
                    # Degrees to radians conversion [cite: 102-103]
                    x = math.radians(az_val)
              
                    # Adjust direction from 'originated from' to 'originated to' [cite: 104]
                    if 0 <= x <= np.pi:
                      xto = x + np.pi
                    elif np.pi < x <= 2 * np.pi:
                      xto = x - np.pi
                    else:
                      xto = x
              
                    # Effective path length L [cite: 105]
                    l_val = l_calculation(xto)
              
                    # Extract AOD window arrays [cite: 106]
                    (
                        fg_aod,
                        fg_qaaod,
                        fg_qacm,
                        bg_aod,
                        bg_qaaod,
                        bg_qacm,
                    ) = aod_cal(aod550, qaaod, qacm, j, i, kk, xto)
              
                    # Calculate background & mean smoke AOD [cite: 107]
                    bg_aod_val, bgcount = mymin(bg_aod, bg_qaaod, bg_qacm)
                    smoke_aod = fg_aod.astype(np.int64) - bg_aod_val
                    smokemean, fgcount = mymean(smoke_aod, fg_qaaod, fg_qacm)
              
                    # Calculate emission rate Rsa [cite: 107]
                    rsa_val = rate(smokemean, ws_val, l_val)
                    if isinstance(rsa_val, (list, np.ndarray)):
                      rsa_val = rsa_val[0]
              
                    center_aod = aod550[kk, i, j]
                    center_qa_aod = qaaod[kk, i, j]
              
                    if rsa_val > 0:
                      out_row = [
                          year,
                          doyd,
                          sensor,
                          orbit_hhmm,
                          tile1,
                          latitude,
                          longitude,
                          confidence,                    
                          frp,
                          rsa_val,
                          center_aod,
                          center_qa_aod,
                          bg_aod_val,
                          smokemean,
                          ws_val,
                          fgcount,
                          bgcount,
                          dis_m,
                          frpnew_mw,
                      ]
              
                      with open(outfile, "a", newline="") as f_out:
                        writer = csv.writer(f_out)
                        writer.writerow(out_row)


    loop_time = (time.perf_counter() - time_start) / 60
    print(f"Iteration {year} finished in {loop_time:.2f} mins.")





