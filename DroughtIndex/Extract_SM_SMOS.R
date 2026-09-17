# get the daily SM averaged over Sumatra and Kalimatan
# lux on 05/22/2022
# lux on 07/27/2026
#----------------------------------------- functions -----------------------------------------#
### prepare environment
rm(list=ls())
graphics.off()

library(matrixStats)
library(ncdf4)
library(dplyr)
library(terra) # cannot use this with library(raster) together

#--------------------------------------------------
# Calculate monthly mean of Soil_Moisture without changing
# the original irregular/curvilinear grid
#--------------------------------------------------
calculate_monthly_mean_irregular <- function(filelist,
                                             sm_var = "Soil_Moisture") {
  if (length(filelist) == 0) {
    return(NULL)
  }
  
  sm_sum   <- NULL
  sm_count <- NULL
  ref_dim  <- NULL
  
  for (i in seq_along(filelist)) {
    # cat("  Reading", i, "of", length(filelist), ":",
    #     basename(filelist[i]), "\n")
    
    nc <- nc_open(filelist[i])
    sm_day <- ncvar_get(nc, sm_var)
    nc_close(nc)
    
    # ncvar_get normally converts the NetCDF fill value to NA.
    # This also removes any remaining non-finite values.
    sm_day[!is.finite(sm_day)] <- NA_real_
    
    if (is.null(sm_sum)) {
      ref_dim  <- dim(sm_day)
      sm_sum   <- array(0,  dim = ref_dim)
      sm_count <- array(0L, dim = ref_dim)
    }
    
    if (!identical(dim(sm_day), ref_dim)) {
      stop("Soil_Moisture dimensions differ in file: ",
           basename(filelist[i]))
    }
    
    valid <- !is.na(sm_day)
    sm_sum[valid]   <- sm_sum[valid] + sm_day[valid]
    sm_count[valid] <- sm_count[valid] + 1L
  }
  
  monthly_mean <- sm_sum / sm_count
  monthly_mean[sm_count == 0] <- NA_real_
  
  return(monthly_mean)
}


#--------------------------------------------------
# Average ASC and DES arrays while retaining values available
# from only one orbit
#--------------------------------------------------
average_ASC_DES <- function(monthly_ASC, monthly_DES) {
  if (is.null(monthly_ASC) && is.null(monthly_DES)) {
    return(NULL)
  }
  if (is.null(monthly_ASC)) {
    return(monthly_DES)
  }
  if (is.null(monthly_DES)) {
    return(monthly_ASC)
  }
  
  if (!identical(dim(monthly_ASC), dim(monthly_DES))) {
    stop("ASC and DES monthly arrays have different dimensions")
  }
  
  monthly_SM <- monthly_ASC
  
  both_valid <- !is.na(monthly_ASC) & !is.na(monthly_DES)
  only_DES   <-  is.na(monthly_ASC) & !is.na(monthly_DES)
  
  monthly_SM[both_valid] <-
    (monthly_ASC[both_valid] + monthly_DES[both_valid]) / 2
  monthly_SM[only_DES] <- monthly_DES[only_DES]
  
  return(monthly_SM)
}


#----------------------------------------- static -----------------------------------------#
### read polygon ID raster file
rasterfile <- '/Volumes/LaCie/SDSU_PhDwork/work0_Done/work7_Inni_Ce_Water_ERL/data/Class/Island_Polygon_new.tif'
raster <- rast(rasterfile)

### read peat raster file
rasterpeatfile <- '/Volumes/LaCie/SDSU_PhDwork/work0_Done/work7_Inni_Ce_Water_ERL/data/Class/Peat_new.tif'
rasterpeat <- rast(rasterpeatfile)

# Initialize
year.arr <- as.numeric()
month.arr <- as.numeric()
SM.avearr <- as.numeric()
SM_peat.avearr <- as.numeric()
SM_nonpeat.avearr <- as.numeric()


#----------------------------------------- dynamic -----------------------------------------#
### Directories
Indir <- "/Volumes/LaCie/SDSU_PhDwork/work10_Inni_Emission_Water/Data/SM_SMOS/"
Outdir <- "/Volumes/LaCie/SDSU_PhDwork/work10_Inni_Emission_Water/Data/SM_SMOS/"
ASC_dir <- file.path(Indir, "ASC")
DES_dir <- file.path(Indir, "DES")

### read SM geolocation file
SM.geofile <- paste(ASC_dir, "SM_RE07_MIR_CDF3SA_20150701T000000_20150701T235959_200_001_B.DBL.nc", sep="/")
nc <- nc_open(SM.geofile)
lat_vec <- ncvar_get(nc, "lat") #same for ASC and DES
lon_vec <- ncvar_get(nc, "lon")
# sm_tmp <- ncvar_get(nc, "Soil_Moisture")
grid_coords <- expand.grid(LONGITUDE = lon_vec, LATITUDE = lat_vec)
nc_close(nc)


### extract SM data
years <- as.character(2010:2023) 
months <- sprintf("%02d", 7:11)
# years  <- c("2015")
# months <- sprintf("%02d", 7)
for (year in years) {
  for (month in months) {
    # ## test
    # year <- "2015"
    # month <- "07"
    cat(year, month, "\n")
    
    ## get monthly mean for ASC
    pattern_ASC <- paste0(
      "^SM_.*_MIR_CDF3SA_",
      year,
      month,
      ".*\\.nc$"
    )
    filelist_ASC <- list.files(
      path       = ASC_dir,
      pattern    = pattern_ASC,
      full.names = TRUE
    )
    monthly_ASC <- calculate_monthly_mean_irregular(filelist_ASC)
    
    ## get monthly mean for DES
    pattern_DES <- paste0(
      "^SM_.*_MIR_CDF3SD_",
      year,
      month,
      ".*\\.nc$"
    )
    filelist_DES <- list.files(
      path       = DES_dir,
      pattern    = pattern_DES,
      full.names = TRUE
    )
    monthly_DES <- calculate_monthly_mean_irregular(filelist_DES)
    
    ## Average ascending and descending observations
    monthly_SM <- average_ASC_DES(monthly_ASC, monthly_DES)
    
    ## Create df: SM_day should be a numerical matrices.
    df <- data.frame(
      LONGITUDE = grid_coords$LONGITUDE,
      LATITUDE = grid_coords$LATITUDE,
      SM = as.vector(monthly_SM)
    )

    df <- na.omit(df)
    df <- df[(df$LATITUDE>-6 & df$LATITUDE<6) & (df$LONGITUDE>95 & df$LONGITUDE<120),]  #extract samples in Indonesia
    
    if (nrow(df) == 0) {
      next   # Skip to the next day in your loop
    }
    
    ### extract class
    # coordinates(df) <- ~ LONGITUDE + LATITUDE
    df_vect <- vect(df, geom = c("LONGITUDE", "LATITUDE"), crs = "EPSG:4326")
    # province class
    rasValue <- extract(raster, df_vect)
    df$PolyID <- rasValue[, 2] # column 1 is ID, column 2 is the raster value
    df$PolyID[is.na(df$PolyID)] <- 0
    # peat or non-peat class
    rasValue_peat <- extract(rasterpeat, df_vect)
    df$PeatID <- rasValue_peat[, 2] # column 1 is ID, column 2 is the raster value
    df$PeatID[is.na(df$PeatID)] <- 0
    df <- as.data.frame(df) #convert a spatial dataframe back to normal dataframe
    
    ### aggregate for specific region
    # across region
    df <- df[df$PolyID==1 | df$PolyID==3,] #extract samples in Sumatra and Kalimantan only
    SM.ave <- mean(df$SM) 
    # peatland
    df_peat <- df[df$PeatID==1,]
    SM_peat.ave <- mean(df_peat$SM)
    # non-peatland
    df_nonpeat <- df[df$PeatID==0,]
    SM_nonpeat.ave <- mean(df_nonpeat$SM)
    
    # append
    year.arr <- c(year.arr, year)
    month.arr <- c(month.arr, month)
    SM.avearr <- c(SM.avearr, SM.ave)
    SM_peat.avearr <- c(SM_peat.avearr, SM_peat.ave)
    SM_nonpeat.avearr <- c(SM_nonpeat.avearr, SM_nonpeat.ave)
  }#month
}#year


### export monthly data frame
df.export <- data.frame(Year=year.arr, Month=month.arr, 
                        SM_SMOS=SM.avearr, SM_SMOS_p1=SM_peat.avearr, SM_SMOS_p0=SM_nonpeat.avearr)
# write2csv
fOut <- paste(Outdir, "SM_SMOS_2010-2023_Jul-Nov_monthly.csv", sep="") 
write.csv(df.export, fOut, row.names=F)


### export yearly data frame (grouped by Year)
df.yearly <- df.export %>%
  group_by(Year) %>%
  summarise(
    SM_SMOS    = mean(SM_SMOS, na.rm = TRUE),
    SM_SMOS_p1 = mean(SM_SMOS_p1, na.rm = TRUE),
    SM_SMOS_p0 = mean(SM_SMOS_p0, na.rm = TRUE),
    .groups = "drop"
  )
# write2csv
fOut_yearly <- paste0(Outdir, "SM_SMOS_2010-2023_Jul-Nov_yearly.csv")
write.csv(df.yearly, fOut_yearly, row.names = FALSE)

















