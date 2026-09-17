/***************************************************** Readme (2026-08-06) ****************************************************/
### Steps to re-process all data using MODIS version 061 (lux at ornl).
0. Download csv during 2003-2025: https://firms2.modaps.eosdis.nasa.gov/download/ (access by 2026-08-05) (rawdata_before_dupcorrection; coverage: Use Map (89, 10, 153, -11)).
1. Reprocess downloaded csv; Code: AF_reprocess.R
2. remove duplication for csv (rawdata_rm_dup); Code: Remove_Repeat_MODISAF.R
3. Add MODIS tile location (AFdata_with_Tileloc); Code: AF_location_on_MAIACAOD_map.py 



/***************************************************** Readme (before 2026) ****************************************************/
### data sources 
1. Raw AF data in 2021-now is downloaded in txt/csv file by lux.
2. Raw AF data in 2002-2020 is downloaded in *.nc file and read into txt by lif (Fangjun Li)
These two kinds of files have different column names.

### data coverage 
1. The data coverage in 2020 is SouthEast Asia.
2. The data coverage in 2021 is Indonesia (89, 10, 153, -11), and the csv file of which is downloaded from https://earthdata.nasa.gov/earth-observation-data/near-real-time/firms/active-fire-data (DL_FIRE_M-C61_259454_2021_MODIS)  (access by 2022).

### data process 
1. The duplication-corrected data during 2002-2019 are from lif.
2. The duplication-corrected data during 2020-* are downloaded and processed by lux. 


