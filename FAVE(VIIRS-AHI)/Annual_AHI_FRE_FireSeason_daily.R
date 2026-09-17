####################################################################
#	Sum fused-AHI-VIIRS FRE during fire seasons in Sumatra and Kalimantan 
# to compare with GFAS FRE 
#
#	XLU 10/26/2021
####################################################################

## prepare environment
rm(list=ls())
graphics.off()

library(TDPanalysis)

Indir <- "D:/work9_Inni_BBE/Data/AF/Himawari/WLF_L2_vbet/test8_ClearPerc5/9_Calc_FRE_DM_Emissions_CeVIIRS/"   #test8 is higher than test9 in 2015-10-20
Outdir <- 'D:/work10_Inni_Emission_Water/Figures/Fig1_Comp_GFAS_FAVE/'
setwd(Indir)

Yeararr <- as.numeric()
Montharr <- as.numeric()
Dayarr <- as.numeric()
FREp1arr <- as.numeric()
FREp0arr <- as.numeric()
countp1arr <- as.numeric()
countp0arr <- as.numeric()

files <- list.files(Indir, pattern=".csv")
# for (infile in files[c(1:5, 13:17, 25:29, 37:41, 49:53, 61:65)]){    #select fire seasons from test8
for (infile in files[c(1)]){                                      #test
  print(infile)
  Year <- substr(infile, 22,25)
  Month <- substr(infile, 26,27)
  
  data <- read.csv(infile, header=T, sep=",")
  data <- data[(data$PolyID==1 | data$PolyID==3),]
  
  datap1 <- data[data$Peat==1,]
  datap0 <- data[data$Peat==0,]
  
  # calculate daily fire count
  for (i in c(1:31)) {
    print(i)
    dayp1 <- datap1[datap1$Day==i,]
    dayp0 <- datap0[datap0$Day==i,]
    
    dayp1$uniqID <- paste(dayp1$Day, dayp1$Column, dayp1$Row, sep="_")
    dayp0$uniqID <- paste(dayp0$Day, dayp0$Column, dayp0$Row, sep="_")    #DOY and Hour/Minute are local variables, while month and day are UTC times!!!
    countp1 <- length( unique(dayp1$uniqID) )
    countp0 <- length( unique(dayp0$uniqID) )
    
    if ( (countp1 + countp0)>0 ) {
      # calculate daily FRE
      FREp1 <- sum(dayp1$FRE, na.rm=T) * 1e6  #MJ to J
      FREp0 <- sum(dayp0$FRE, na.rm=T) * 1e6
      
      Yeararr <- c(Yeararr, Year)
      Montharr <- c(Montharr, Month)
      Dayarr <- c(Dayarr, i)
      FREp1arr <- c(FREp1arr, FREp1)
      FREp0arr <- c(FREp0arr, FREp0)
      countp1arr <- c(countp1arr, countp1)
      countp0arr <- c(countp0arr, countp0)
    } #count>0; at least one fire
  }
  
  rm(data, datap1, datap0)
}


dfp1 <- data.frame(Year=Yeararr, Month=Montharr, Day=Dayarr, PeatID=rep("1",length(FREp1arr)), FAVE_FRE_J=FREp1arr, FAVE_FireCnt=countp1arr)  #J
dfp0 <- data.frame(Year=Yeararr, Month=Montharr, Day=Dayarr, PeatID=rep("0",length(FREp1arr)), FAVE_FRE_J=FREp0arr, FAVE_FireCnt=countp0arr)
df <- rbind(dfp1,dfp0)

# print(df)

fOut <- paste(Outdir, "FAVE_FRE_Count_Daily_FireSeason_SumaKali_Peat_Nonpeat_test.csv", sep="")
write.csv(df, fOut, row.names=F)













