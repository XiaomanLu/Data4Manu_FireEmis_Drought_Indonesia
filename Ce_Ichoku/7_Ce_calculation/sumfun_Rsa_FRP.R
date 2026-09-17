# sum FRP and Rsa for every day in seleccted datasets (e.g. PolyID==3 and peat==1)
sumfun_Rsa_FRP <- function(indata){
  
  # ######## Unique Year DOY (for dry year plot)
  # indata$YearDOY <- paste(indata$Year, indata$DOY, sep='')
  # Rsasumv <- tapply(indata$Rsa, indata$YearDOY, sum)
  # FRPsumv <-tapply(indata$FRPnew2_MW, indata$YearDOY, sum)
  
  
  ######## Unique DOY
  Rsasumv <- tapply(indata$Rsa, indata$DOY, sum, na.rm=TRUE)
  FRPsumv <-tapply(indata$FRPnew2_MW, indata$DOY, sum, na.rm=TRUE)
  
  
  df <- as.data.frame(cbind(Rsasumv, FRPsumv))
  
  # remove NA rows
  # df <- na.omit(df)
  
  return(df)
}





