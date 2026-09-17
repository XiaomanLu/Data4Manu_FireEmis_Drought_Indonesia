###################################################################################
#	Extract GFAS fire observations at each grid (0.1x0.1 degree) to draw FRE/TPM map
# for Sumatra and Kalimatan during annual fire seasons  
#
#	XLU 10/26/2021
###################################################################################
### prepare environment
rm(list=ls())
graphics.off()
library(ncdf4)
require(HiClimR)
library(raster)

### parameters to calculate GridArea
radius <- 6371.1     # km
pi <- 3.1415926/180.0
dlan <- 0.1         # degree
dlon <- 0.1       # degree
unitConst <- 1000.0*1000.0*24*60*60 #  daily*km2 to second*m2
# flag <- 0

Indir <- "/Volumes/LaCie/SDSU_PhDwork/work10_Inni_Emission_Water/Data/GFASv12_FRP_Global/0_Rawdata_nc_fireseason/"
outdir <- "/Volumes/LaCie/SDSU_PhDwork/work10_Inni_Emission_Water/Data/GFASv12_FRP_Global/1_Annual_eachObs_csv/"
setwd(Indir)
rasterfile1 <- '/Volumes/LaCie/SDSU_PhDwork/work0_Done/work7_Inni_Ce_Water_ERL/data/Class/Peat_new.tif'
rasterfile2 <- '/Volumes/LaCie/SDSU_PhDwork/work0_Done/work7_Inni_Ce_Water_ERL/data/Class/Island_Polygon_new.tif'
# Cefile <- '/Volumes/LaCie/SDSU_PhDwork/work10_Inni_Emission_Water/Figures/FigS89_Ce_Merge_Year&Region/Ce.csv'
Cefile = paste(
  "/Volumes/LaCie/SDSU_PhDwork/work0_Done/work7_Inni_Ce_Water_ERL/",
  "figures/Fig5_Fig8_FigS1_Rsa_FRP_Scatterplot/",
  "work10_Rsa_FRP_Scatterplot_2002_2020_Eachyear_MergeRegion/",
  "Eachyear2_NewWD_rmOutlier/version_006/",
  "Ce_Annual_Merged_Sumatra_Kalimatan_v006_Filled.csv", sep="")

# read raster data
raster1 <- raster(rasterfile1)
raster2 <- raster(rasterfile2)

# read Ce
Ce <- read.csv(Cefile)

for (yr in c(2003:2019)) {   
  # yr <- 2010
  print(yr)
  flag <- 0
  
  ncfiles <- Sys.glob(paste(Indir, yr, '*.nc', sep=""))
  for (subfile in ncfiles) { #each month
    # subfile <- ncfiles[1]
    print(subfile)
    filename <- substr(basename(subfile), 1, 6)
    month <- substr(basename(subfile), 5, 6)
    
    # read data
    ncdata <- nc_open(subfile)
    frp <- ncvar_get(ncdata, "frpfire")
    lat <- ncvar_get(ncdata, "latitude")
    lon <- ncvar_get(ncdata, "longitude")
    nc_close(ncdata)
    
    # work with data
    latlon.matrix <- grid2D(lon=lon, lat=lat)
    lon.array <- latlon.matrix$lon
    lat.array <- latlon.matrix$lat
    days <- dim(frp)[3]  #time dimension
    
    # daily frp in Inni
    for (i in c(1:days)) {
      # i <- 1
      frp.slice <- frp[, , i]     #unit: MW/m2/s
      frp.array <- t(frp.slice)
      
      # create df in Inni
      df <- as.data.frame(cbind(as.vector(lon.array), as.vector(lat.array), as.vector(frp.array)))
      names(df) <- c("LONGITUDE", "LATITUDE", "frpflux")
      df <- df[df$frpflux>1e-13 & (df$LATITUDE>-6 & df$LATITUDE<6) & (df$LONGITUDE>95 & df$LONGITUDE<120),]  #extract samples in Sumatra and Kalimantan only
      
      if (nrow(df)>0) {
        # calculate FRE
        df$GridArea_km2 <- radius*(dlon*pi)*cos(df$LATITUDE*pi)*radius*(dlan*pi) #km2
        df$FRE_J <- df$frpflux * df$GridArea_km2 * unitConst  # Unit: J;  J = W/m2/second * (second*m2)
        
        # extract class
        coordinates(df) <- ~ LONGITUDE + LATITUDE
        rasValue1 <- extract(raster1, df)
        rasValue2 <- extract(raster2, df)
        df$Peat <- rasValue1
        df$PolyID <- rasValue2
        df$Peat[is.na(df$Peat)] <- 0
        df$PolyID[is.na(df$PolyID)] <- 0
        df <- as.data.frame(df) # convert a spatial dataframe back to normal dataframe
        df$Year <- rep(yr, nrow(df))
        df$Month <- rep(month, nrow(df))
        df$Day <- rep(i, nrow(df))
        
        # extract FRE for specific region
        df <- df[df$PolyID==1 | df$PolyID==3,] #extract samples in Sumatra and Kalimantan only
        
        # Merge data for each year
        if (flag==0){
          dfMerge <- df
          flag <- 1
        } else {
          dfMerge <- rbind(dfMerge, df)
        } #flag
        
      } #nrow(df)>0
    } #i
  }#subfile
  
  ### compute TPM
  # initialize
  dfMerge$Ce <- rep(NA, nrow(dfMerge))
  dfMerge$TPM_Gg <- rep(NA, nrow(dfMerge))
  # link Ce
  Ce$UniqID <- paste(Ce$year, Ce$peatID, sep="_")
  dfMerge$UniqID <- paste(dfMerge$Year, dfMerge$Peat, sep="_")
  dfMerge$Ce <- Ce$Ce_filled[match(dfMerge$UniqID, Ce$UniqID)]            #unit: g/MJ
  #calculate TPM
  dfMerge$TPM_Gg <- dfMerge$FRE_J * dfMerge$Ce * 1e-6 * 1e-9              #J to MJ; g to Gg
  
  ### adjust columns
  cols_to_keep <- c("Year", "Month", "Day", 
                    "PolyID", "Peat", "LATITUDE", "LONGITUDE", "GridArea_km2",
                    "frpflux", "FRE_J", "Ce", "TPM_Gg")
  dfMerge_subset <- dfMerge[, cols_to_keep]
  
  ### write2csv
  fOut <- paste(outdir, yr, "_Inni_GFAS-FAVE_FRE_TPM_LC.csv", sep="")
  write.csv(dfMerge_subset, fOut, row.names=F)
  
}#yr





























