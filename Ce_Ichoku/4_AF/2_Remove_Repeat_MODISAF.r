##########################################
# remove scan-2-scan repeating detections
# for Aqua MODIS
#
# FLI@GScE.SDSU 5/10/2017
#######################################

## initial working space
rm(list=ls())
graphics.off()

## load libraries
library(raster)
library(sp)
library(fields)
library(geosphere)
library(sf)

## setup working directory
dirIn <- "/Volumes/LaCie/SDSU_PhDwork/work0_Done/work7_Inni_Ce_Water_ERL/data/AF_Inni/1_rawdata_before_dupcorrection/"
dirOut <- "/Volumes/LaCie/SDSU_PhDwork/work0_Done/work7_Inni_Ce_Water_ERL/data/AF_Inni/2_rawdata_rm_dup/"

years <- c(2003:2021)
products <- c("MOD14", "MYD14")

for (year in years) {
  for (product in products){
    cat(year, product, "\n")
    
    fInM <- paste(dirIn, year, "_", product, "_061.csv", sep="")
    dataM_All <- read.csv(fInM, header=T, sep=",")
    
    # extract Indonesia
    dataM_All <- dataM_All[(dataM_All$Latitude>=-11) & (dataM_All$Latitude<=10) & (dataM_All$Longitude>=89) & (dataM_All$Longitude<=153), ]
    
    # process 
    uniqDOYs <- unique(dataM_All$DOY)
    longitudesRanges <- c(-180,-25,65,180)
    count <- 0
    for(doy in uniqDOYs){
      # print(doy)
      dataMDay <- dataM_All[dataM_All$DOY==doy,]  
      
      for(j in 1:(length(longitudesRanges)-1)){
        dataM <- dataMDay[dataMDay$Longitude>longitudesRanges[j] & 	dataMDay$Longitude<=longitudesRanges[j+1],]
        
        if(nrow(dataM)>1){	
          # calculate along-scan and along-track pixel dimensions
          Re <- 6378.137
          h <- 705
          r <- Re + h
          s <- 0.0014184397
          vza_rad <- (dataM$Sample-676.5) * s	# degree to radians
          scanDim <- Re * s * ( cos(vza_rad)/((Re/r)^2 - sin(vza_rad)*sin(vza_rad ))^0.5 - 1)
          trackDim <- r * s * ( cos(vza_rad) - ((Re/r)^2 - sin(vza_rad)*sin(vza_rad ))^0.5 )
          
          # variables
          indRepeatAF <- as.numeric()
          RepeatFRP <- as.numeric()
          repeatingAFs <- as.numeric()
          
          # process row by row
          numRows <- nrow(dataM)
          for(j in 1:(numRows-1)){
            
            if(!(j %in% repeatingAFs)) {	#if a AF has not been recorded
              restRows <- (j+1):numRows
              pt1_df <- data.frame(lon=rep(dataM[j,]$Longitude, numRows-j), lat=rep(dataM[j,]$Latitude, numRows-j))
              pt2_df <- data.frame(lon=dataM[restRows,]$Longitude, lat=dataM[restRows,]$Latitude)
              distThreshold <- min(c(scanDim[j], trackDim[j])) - 0.2
              distances <- distGeo(pt1_df,pt2_df,a=6378.137, f=1/298.257223563)	# Geodesic distance in units: km
              
              # difference in observing time
              fltHHj <- floor(dataM[j,]$HHMM/100) +  (dataM[j,]$HHMM%%100)/60
              fltHHrest <- floor(dataM[restRows,]$HHMM/100) +  (dataM[restRows,]$HHMM%%100)/60
              difHH <- abs(fltHHrest-fltHHj)
              hhThreshold <- 0.25
              
              ind_matched_repeating <- restRows[which((distances < distThreshold) & (difHH<hhThreshold)) ]	# obtain the row number of the matched AF which has a distance less than 0.95 km from the jth point
              if(length(ind_matched_repeating)>0){
                indRepeatAF <- c(indRepeatAF, j)	# record the repeating AF
                avgFRP <- mean(c(dataM[j,]$FRP.MW., dataM[ind_matched_repeating,]$FRP.MW.))	
                RepeatFRP <- c(RepeatFRP, avgFRP)
                repeatingAFs <- c(repeatingAFs, j, ind_matched_repeating)
              }
            }
          }
          
          # remove repeating AF and assign a average FRP to the repeating AF
          ptMODIS_uniq <- dataM[!((1:numRows) %in% repeatingAFs),]
          ptMODIS_repAFsRemained <- dataM[((1:numRows) %in% indRepeatAF),]
          ptMODIS_repAFsRemained$FRP.MW. <- RepeatFRP
          tmp <- rbind(ptMODIS_uniq, ptMODIS_repAFsRemained)
          
          if(!count){
            ptMODIS_repRemoved <- tmp
          }else{		
            ptMODIS_repRemoved <- rbind(ptMODIS_repRemoved, tmp)
          }
          
          count <- count + 1
        }
      }
    }
    
    ## write results
    fOut <- paste(dirOut, year, "_", product, "_061_interscan_corrected_INDOESIA.csv", sep="")
    write.csv(ptMODIS_repRemoved, fOut, row.names=F)
  }#product
}#year



