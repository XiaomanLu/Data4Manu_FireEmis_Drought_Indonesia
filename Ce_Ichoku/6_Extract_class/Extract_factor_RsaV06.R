# Goal: extract (peat, island, landcover, province, FRPnew2, month) for Rsa*.csv files
# Reference: https://gisday.wordpress.com/2014/03/24/extract-raster-values-from-points-using-r/comment-page-1/
# Date: 12/17/2020

rm(list=ls())
library(raster)
library(plyr)
library(dplyr) 
library(stringr)

####################### sub functions #######################
subset_safely <- function(x, index) {
  if (length(x) < index) {
    return(NA_character_)
  }
  x[[index]]
}
str_split_n <- function(string, pattern, n) {
  out <- str_split(string, pattern)
  vapply(out, subset_safely, character(1L), index = n)
}


####################### main function #######################
DIR = '/Volumes/LaCie/SDSU_PhDwork/work0_Done/work7_Inni_Ce_Water_ERL/data'
csvdir <- paste(DIR, "Rsa_v06_NewWD/", sep="/")
outdir <- csvdir

rasterfile1 <- paste(DIR, "Class", "Peat_new.tif", sep="/")
rasterfile2 <- paste(DIR, "Class", "Island_Polygon_new.tif", sep="/")
rasterfile3 <- paste(DIR, "Class", "MCD12Q1.A2013001.Land_Cover_Type_1.C051.dat", sep="/")
rasterfile4 <- paste(DIR, "Class", "Province_Polygon.tif", sep="/")
raster1 <- raster(rasterfile1)
raster2 <- raster(rasterfile2)
raster3 <- raster(rasterfile3)
raster4 <- raster(rasterfile4)

for (years in c(2003:2025)){
  # years <- 2002
  print(years)
  
  csvfile <- paste(csvdir, years, '_MAIAC_Rsa_FRP.csv', sep='')
  outfile <- paste(outdir, years, '_MAIAC_Rsa_FRP_Class.csv', sep='')
  
  x <- read.csv(csvfile, header=TRUE)
  coordinates(x) <- ~ Longitude + Latitude
  
  rasValue1 <- extract(raster1, x)
  rasValue2 <- extract(raster2, x)
  rasValue3 <- extract(raster3, x)
  rasValue4 <- extract(raster4, x)
  
  # extract class_factor: peat, island, landcover, province
  x$Peat <- rasValue1
  x$PolyID <- rasValue2
  x$LC <- rasValue3
  x$Province <- rasValue4
  
  # calculate month based on year and DOY
  datearr <- as.Date((x$DOY-1), origin=paste(years,'01','01',sep="-")) # note that R uses a 0 based index for dates only
  x$month <- as.numeric(str_split_n(datearr, "-", 2))
  
  # calculate FRPnew2_MW based on FRPnew_MW
  x$FRPnew2_MW <- x$FRPnew_MW*0.926625433055833^2
  
  # change peat class from NA to 0
  x$Peat[is.na(x$Peat)] <- 0
  
  # convert a spatial dataframe back to normal dataframe
  x <- as.data.frame(x)       
  write.table(x, outfile, sep=",", row.names = FALSE)
}

















