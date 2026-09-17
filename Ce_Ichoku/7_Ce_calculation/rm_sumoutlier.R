## rm sum outlier function for eachyear2

rm_sumoutlier <- function(x, years){
  
  #### Aqua and Terra data
  P1peat1 <- x[(x$PolyID==1 | x$PolyID==3) & x$Peat==1,]
  P1peat0 <- x[(x$PolyID==1 | x$PolyID==3) & x$Peat==0,]
  dfP1peat1 <- sumfun_Rsa_FRP(P1peat1)
  dfP1peat0 <- sumfun_Rsa_FRP(P1peat0)
  
  # # # ## remove outliers for 'Eachyear2'
  if (years == 2002) {
    dfP1peat1 <- dfP1peat1[!(dfP1peat1$FRPsumv > 15*100),]
    dfP1peat0 <- dfP1peat0[!(dfP1peat0$FRPsumv > 200*10^2),]
  }

  if (years == 2003) {
    dfP1peat1 <- dfP1peat1[!(dfP1peat1$Rsasumv > 80*10^2),]
    # dfP1peat0 <- dfP1peat0[!(dfP1peat0$Rsasumv > 300*10^2),]
  }

  if (years == 2005) {
    dfP1peat0 <- dfP1peat0[!(dfP1peat0$FRPsumv > 10*10^2 & dfP1peat0$Rsasumv < 50*10^2),]
  }

  if (years == 2007) {
    dfP1peat1 <- dfP1peat1[!(dfP1peat1$Rsasumv > 42*10^2),]
  }

  if (years == 2008) {
    dfP1peat1 <- dfP1peat1[!(dfP1peat1$FRPsumv > 10*10^2),]
    dfP1peat0 <- dfP1peat0[!(dfP1peat0$Rsasumv > 500*10^2),]
  }

  if (years == 2010) {
    dfP1peat0 <- dfP1peat0[!(dfP1peat0$FRPsumv > 15*10^2),]
  }

  if (years == 2011){
    dfP1peat0 <- dfP1peat0[!(dfP1peat0$Rsasumv > 300*10^2),]
  }

  if (years == 2015){
    dfP1peat1 <- dfP1peat1[!(dfP1peat1$Rsasumv>1000*10^2 | (dfP1peat1$Rsasumv<50*10^2 & dfP1peat1$FRPsumv > 10*10^2)),]
  }

  if(years == 2017){
    dfP1peat0 <- dfP1peat0[!(dfP1peat0$FRPsumv>10*10^2 | dfP1peat0$Rsasumv>60*10^2),]
  }

  if(years == 2019){
    dfP1peat0 <- dfP1peat0[!(dfP1peat0$FRPsumv>40*10^2 | dfP1peat0$Rsasumv>1500*10^2),]
  }

  if(years == 2020){
    dfP1peat0 <- dfP1peat0[!(dfP1peat0$Rsasumv>5*10^2),]
  }

  if(years == 2024){
    dfP1peat0 <- dfP1peat0[!(dfP1peat0$Rsasumv>60*10^2),]
  }
  
  # return a list
  mylist <- list(dfP1peat1, dfP1peat0)
  
}


