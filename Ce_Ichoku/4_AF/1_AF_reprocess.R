# reprocess raw MODIS data downloaded from https://earthdata.nasa.gov/earth-observation-data/near-real-time/firms/active-fire-data

## initial working space
rm(list=ls())
graphics.off()

library(TDPanalysis)
library(dplyr)

DIR <-  '/Volumes/LaCie/SDSU_PhDwork/work0_Done/work7_Inni_Ce_Water_ERL/data/AF_Inni/1_rawdata_before_dupcorrection/'
Indir <- paste(DIR, "DL_FIRE_M-C61_41804_2003-2021_MODIS/", sep="")
Outdir <- DIR

# ### for two csv inputs
# arcdata <- read.csv(paste(Indir, "fire_archive_M-C61_259454.csv", sep=""), header=T)  # archive data
# arcdata <- arcdata[, -c(15)]   #remove the last column to match nrt data
# nrtdata <- read.csv(paste(Indir, "fire_nrt_M-C61_259454.csv", sep=""), header=T)      # near-real-time data
# Indata <- rbind(arcdata, nrtdata)

### for one csv input
Indata <- read.csv(paste(Indir, "fire_archive_M-C61_41804.csv", sep=""), header=T)      # near-real-time data

# convert date to year and doy
Indata$Year <- substr(Indata$acq_date, 1, 4)
tmp.month <- substr(Indata$acq_date, 6, 7)
tmp.day <- substr(Indata$acq_date, 9, 10)
tmp.date <- paste(tmp.day, tmp.month, Indata$Year, sep="/")
Indata$DOY <- date.to.DOY(dates=tmp.date) 

# rename column name to match data in 2002-2020
oldnames <- c("latitude", "longitude", "acq_time", "satellite", "confidence", "version", "frp")
newnames <- c("Latitude", "Longitude", "HHMM", "Satellite", "Confidence", "Collection", "FRP(MW)")
colnames(Indata)[which(colnames(Indata) %in% oldnames )] <- newnames

# convert character to num
Indata$Year <- as.numeric(Indata$Year)

# reorder column orders
Indata <- select(Indata, Year, DOY, HHMM, Latitude, Longitude, "FRP(MW)", 
                  brightness, scan, track, acq_date, Satellite, instrument, Confidence, Collection, bright_t31, daynight)

# separate Terra and Aqua
data.Terra <- Indata[Indata$Satellite == "Terra",]
data.Aqua <- Indata[Indata$Satellite == "Aqua",]

# write results by year
for (year in 2003:2021) {
  print(year)
  
  # 1. Added comma after filter condition for correct row subsetting
  data.Terra.yr <- data.Terra[data.Terra$Year == year, ]
  data.Aqua.yr  <- data.Aqua[data.Aqua$Year == year, ]
  
  # 2. Construct output file paths
  fout.Terra <- file.path(Outdir, paste0(year, "_MOD14_061.csv"))
  fout.Aqua  <- file.path(Outdir, paste0(year, "_MYD14_061.csv"))
  
  # 3. Export to CSV
  write.csv(data.Terra.yr, fout.Terra, row.names = FALSE)
  write.csv(data.Aqua.yr,  fout.Aqua,  row.names = FALSE)
}




















