# install.packages(plotrix)
library(ggplot2)
library(fields)
library(plotrix)
library(dplyr)
library(RColorBrewer)

rm(list=ls())
graphics.off()

## source subfunctions
sourcedir <- '/Volumes/LaCie/SDSU_PhDwork/work10_Inni_Emission_Water/Code/Ce_Ichoku/7_Ce_calculation/'
# call in order 
source(paste(sourcedir, 'drawplot_peat.R', sep=""))  #draw for peatland and non-peatland seperately
source(paste(sourcedir, 'rm_sumoutlier.R', sep=""))  #remove outlier of specific scatter
source(paste(sourcedir, 'sumfun_Rsa_FRP.R', sep="")) #sum Rsa and FRP from each observation to daily
source(paste(sourcedir, 'plotSsum_vs_Fsum.R', sep="")) #Plot daily Rsa ~ FRP

##################################### Main function###################################
Rsadir = "/Volumes/LaCie/SDSU_PhDwork/work0_Done/work7_Inni_Ce_Water_ERL/data/Rsa_v06_NewWD/"
outdir <- paste("/Volumes/LaCie/SDSU_PhDwork/work0_Done/work7_Inni_Ce_Water_ERL/figures/Fig5_Fig8_FigS1_Rsa_FRP_Scatterplot/",
                "work10_Rsa_FRP_Scatterplot_2002_2020_Eachyear_MergeRegion/Eachyear2_NewWD_rmOutlier/", sep="")
# outdir <- "/Volumes/LaCie/SDSU_PhDwork/work10_Inni_Emission_Water/Data/Ce/" #tmp


## Colors: put here as it is used by multiple functions.
specCols <- c("red","orange","yellow","green","blue")
colPal <- colorRampPalette((specCols))
cols <- colPal(161)   # Doy period: 182-334

## Plot
for (year in c(2003:2025)){
  # print(year)
  years <- toString(year)
  
  x <- read.csv(paste(Rsadir, years,"_MAIAC_Rsa_FRP_Class.csv",sep=""),header=TRUE)
 
  #### Eachyear2 -- filter2 (less filter)
  x <- x[x$WS>=2,]
  x <- x[x$smokemean>=20,]
  x <- x[x$Rsa>1,]
  x <- x[x$Dis_m<=10 | is.na(x$Dis_m),]
  
  drawplot_peat(x,outdir,years)
}











