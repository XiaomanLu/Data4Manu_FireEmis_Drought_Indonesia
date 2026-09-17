# Function: convert MODIS tiles in Indonesia from Sinsoidal to Geographical (degree) projection
# Date: 20200728

library(raster)
library(MODISTools)
rm(list=ls())

Sindir <- 'D:/work7_Inni_emission/data/MODIS_MAIAC_AOD_US/'
Outdir <- Sindir

# Inni:
# tilesarr <- c("h27v08","h27v09","h28v08","h28v09","h29v08","h29v09","h30v08","h30v09","h31v08","h31v09","h32v08","h32v09")

# US:
tilesarr <- c("h08v04", "h09v04", "h10v04", "h11v04", "h12v04", "h13v04", "h08v05", "h09v05", "h10v05", "h11v05", "h12v05", "h08v06", "h09v06", "h10v06")


for (tile in tilesarr) {
  # tile <- "h30v13" 
  
  # Read tile csv file
  Latfile <- paste(Sindir,'Lat_',tile,'_Central.csv',sep="")
  Lonfile <- paste(Sindir,'Lon_',tile,'_Central.csv',sep="")
  
  Latdata <- read.table(Latfile, sep=',', header=FALSE)
  Londata <- read.csv(Lonfile, sep=',', header=FALSE)
  
  #convert dataframe to matrix
  Latm <- data.matrix(Latdata,rownames.force = NA)
  Lonm <- data.matrix(Londata,rownames.force = NA)
  
  # change lat/lon matrix dimensions from 1200*1200 to 1*1440000 by cols.
  Latv<-as.vector(Latm)
  Lonv<-as.vector(Lonm)
  
  # Convert lat/lon data from sinusoidal to degree
  lon_lat <- sin_to_ll(Lonv,Latv)
  
  lon.degree <- as.vector(t(lon_lat[1]))
  lat.degree <- as.vector(t(lon_lat[2]))
  
  lon.degree.matrix <- matrix(lon.degree,nrow=1200)
  lat.degree.matrix <- matrix(lat.degree,nrow=1200)
  
  outlonfile <- paste(Outdir,'Lon_',tile,'_Central_degree.csv',sep="")
  outlatfile <- paste(Outdir,'Lat_',tile,'_Central_degree.csv',sep="")
  
  # export lat/lon degree data to matrix in csv file
  write.table(lon.degree.matrix, outlonfile, row.names=FALSE, col.names=FALSE, sep=",")
  write.table(lat.degree.matrix, outlatfile, row.names=FALSE, col.names=FALSE, sep=",")
  
}

