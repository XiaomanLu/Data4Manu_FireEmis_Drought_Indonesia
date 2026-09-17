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
FREp1arr <- as.numeric()
FREp0arr <- as.numeric()
countp1arr <- as.numeric()
countp0arr <- as.numeric()

files <- list.files(Indir, pattern=".csv")
for (infile in files[c(1:5, 13:17, 25:29, 37:41, 49:53, 61:65)]){    #select fire seasons from test8
# for (infile in files[c(65)]){                                      #test
  print(infile)
  Year <- substr(infile, 22,25)
  Month <- substr(infile, 26,27)
  
  data <- read.csv(infile, header=T, sep=",")
  data <- data[(data$PolyID==1 | data$PolyID==3),]
  
  datap1 <- data[data$Peat==1,]
  datap0 <- data[data$Peat==0,]
  
  # calculate monthly fire count
  datap1$uniqID <- paste(datap1$Day, datap1$Column, datap1$Row, sep="_")  #Month and Day are UTC times; DOY is local time
  datap0$uniqID <- paste(datap0$Day, datap0$Column, datap0$Row, sep="_")
  countp1 <- length( unique(datap1$uniqID) )
  countp0 <- length( unique(datap0$uniqID) )
  
  # calculate monthly FRE
  FREp1 <- sum(datap1$FRE, na.rm=T) * 1e6  #MJ to J
  FREp0 <- sum(datap0$FRE, na.rm=T) * 1e6
  
  Yeararr <- c(Yeararr, Year)
  Montharr <- c(Montharr, Month)
  FREp1arr <- c(FREp1arr, FREp1)
  FREp0arr <- c(FREp0arr, FREp0)
  countp1arr <- c(countp1arr, countp1)
  countp0arr <- c(countp0arr, countp0)
  
  rm(data, datap1, datap0)
}

dfp1 <- data.frame(Year=Yeararr, Month=Montharr, PeatID=rep("1",length(FREp1arr)), FAVE_FRE_J=FREp1arr, FAVE_FireCnt=countp1arr)  #J
dfp0 <- data.frame(Year=Yeararr, Month=Montharr, PeatID=rep("0",length(FREp1arr)), FAVE_FRE_J=FREp0arr, FAVE_FireCnt=countp0arr)
df <- rbind(dfp1,dfp0)

# print(df)

fOut <- paste(Outdir, "FAVE_FRE_Count_Monthly_FireSeason_SumaKali_Peat_Nonpeat_NewUTC.csv", sep="")
write.csv(df, fOut, row.names=F)







#################### Based on statictical daily data (cannot seperate peat and non-peat) ####################
# data.Suma <- read.csv("Daily_FRE_DM_EMIS_Sumatra_NewWD_rmrepeat_Test9.csv", header=T)
# data.Kali <- read.csv("Daily_FRE_DM_EMIS_Kalimantan_NewWD_rmrepeat_Test9.csv", header=T)
# data.Merge <- rbind(data.Suma, data.Kali)
# 
# # extract FRE column
# data <- data.Merge[,1:3]
# data <- na.omit(data)
# data$Month <- as.numeric( substr(as.Date(data$DOY-1, origin = paste(data$Year, "01", "01", sep="-")), 6, 7) )
# 
# 
# # extract fire season (Jul - Nov)
# data <- data[data$Month>=7 & data$Month<=11,]
# data$FRE <- data$FRE * 1e6 * 1e6  # 10^6 MJ to MJ; and then to J
# 
# # sum for each year/month
# data.agg <- aggregate(FRE ~ Year+Month, data=data, FUN = sum)
# 
# fOut <- paste(Outdir, "FAVE_FRE_monthly_FireSeason_Suma_Kali_Peat.csv", sep="")
# write.csv(data.agg, fOut, row.names=F)





