## Date: 20200721
## Author: Xiaoman Lu@GSCE
## Goal: Get the coordinate matrix of MODIS tiles 

## Notes about MODIS Metadata: https://lpdaac.usgs.gov/data/get-started-data/collection-overview/missions/modis-overview/
#The UpperLeftPointMtrs is in projection coordinates, and identifies the very upper left corner of the upper left pixel of the image data
#The LowerRightMtrs identifies the very lower right corner of the lower right pixel of the image data. These projection coordinates are the only metadata that accurately reflect the extreme corners of the gridded image
#There are additional BOUNDINGRECTANGLE and GRINGPOINT fields within the metadata, which represent the latitude and longitude coordinates of the geographic tile corresponding to the data


import numpy as np
from pyhdf.SD import SD, SDC
import re
import csv,os
import glob 

cwd = r'D:\work7_Inni_emission\data\MODIS_MAIAC_AOD_US'
os.chdir(cwd)

for file_name in glob.glob('MCD19A2.A*.h*v*.*.hdf'):
    # file_name = 'MCD19A2.A2004335.h27v08.006.2018027234952.hdf'
    print(file_name)
    MODIStile = file_name.split('.')[2] 
    htile = int(MODIStile[1:3])
    vtile = int(MODIStile[4:6])
    
    ### Open file
    file = SD(file_name, SDC.READ)
    
    ### read global attributes
    attr = file.attributes(full=1)
    attNames = attr.keys()
    StructMeta = attr["StructMetadata.0"][0]
    ss = StructMeta.split("\n")
    UpperLeftstring = ss[7]
    LowerRightstring = ss[8]
    
    # getting UpperLeft lat/lon numbers from string  
    ULtemp = re.findall(r'\d+', UpperLeftstring) 
    ULres = list(map(int, ULtemp)) 
    ULlat = ULres[2]+ULres[3]/pow(10,len(str(ULtemp[3])))
    ULlon = ULres[0]+ULres[1]/pow(10,len(str(ULtemp[1])))
    
    #getting LowerRight lat/lon numbers from string
    LRtemp = re.findall(r'\d+', LowerRightstring) 
    LRres = list(map(int, LRtemp))           
    LRlat = LRres[2]+LRres[3]/pow(10,len(str(LRres[3])))
    LRlon = LRres[0]+LRres[1]/pow(10,len(str(LRres[1])))
    
    if vtile >= 9:
        ULlat = -ULlat
        LRlat = -LRlat 
        
    if htile <= 17:
        ULlon = -ULlon
        LRlon = -LRlon
    
    ### define modis tile lat/lon matrix
    # define origin and end point of the raster
    ox,oy = [ULlon,ULlat]
    ex,ey = [LRlon,LRlat]
    
    # define columns and rows
    cols = 1200
    rows = 1200
    
    # define pixel width and height
    pw = (LRlon-ULlon)/cols
    ph = (ULlat-LRlat)/rows
    
    # create 1D arrays with the coordinates of each axis (shifted to the center)
    x = np.arange(ox, ex, pw) + pw/2
    y = np.arange(ey, oy, ph) + ph/2
    
    # create 1D arrays with the coordinates of each axis (shifted to upperleft)
    #x = np.arange(ox, ex, pw) 
    #y = np.arange(ey, oy, ph) + ph
    
    # create the 2D coordinates arrays
    xx, yy = np.meshgrid(x, y)
    
    # flip yy so coordinates are descending and not ascending
    yy = np.flip(yy)
    
    # write to *.csv files
    Latoutfile = 'Lat_'+MODIStile+'_Central.csv'     # yy in Sinusoidal projection
    Lonoutfile = 'Lon_'+MODIStile+'_Central.csv' # xx in Sinusoidal projection
    
    myFile = open(Latoutfile, 'w', newline='')
    with myFile:
       writer = csv.writer(myFile)
       writer.writerows(yy)
       
    myFile2 = open(Lonoutfile, 'w', newline='')
    with myFile2:
       writer2 = csv.writer(myFile2)
       writer2.writerows(xx)









