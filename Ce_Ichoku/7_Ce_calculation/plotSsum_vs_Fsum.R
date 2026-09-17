# function used to plot Ssum vs. Fsum
plotSsum_vs_Fsum <- function(Fsum,Ssum,DOY,graphID,regionname,idx,idy){
  
  if (length(Fsum) != 0)
  {
    Fsum_final <- Fsum[Fsum>0] * 1e-2
    Ssum_final <- Ssum[Fsum>0] * 1e-2
  } else
  {
    Fsum_final <- 1
    Ssum_final <- 1
    DOY <- 1
  }
  
  xlim_max <- max(Fsum_final)
  ylim_max <- max(Ssum_final)
  Fsum_axis <- 1.1*xlim_max
  Ssum_axis <- 1.1*ylim_max
  
  if( (length(Fsum_final)>0) && (length(Ssum_final)>0)){
    
    ### Regression
    ft1 <- lm(Ssum_final ~ Fsum_final-1)
    fitted_conf1 <- predict(ft1,interval="confidence")	# 95% confidence interval
    #fitted_pred1 <- predict(ft1,interval="prediction")	# 95% prediction interval
    
    beta1 <- sprintf("%.2f", coef(ft1)[1]);
    rSquare <- sprintf("%.2f", summary(ft1)$r.squared)
    SdError <- sprintf("%.2f", coef(summary(ft1))[, "Std. Error"])
    Nsample <- length(Fsum_final)
    tmp <- anova(ft1)$'Pr(>F)'[1];
    pValue = case_when(
      tmp<0.001 ~ 0.001,
      tmp<0.01  ~ 0.01,
      tmp<0.05  ~ 0.05,
      tmp<=0.1  ~ 0.1,
      tmp>0.1   ~ 0.5)
    
    exp_model <- eval(bquote(expression(y == "("~.(beta1)~"\u00b1"~.(SdError)~")"~"x")))
    # exp_model <- paste("y = (", eval(beta1), "\u00b1", eval(SdError), ")x", sep="")  # another way but = is not the same shown on plot
    exp_rsquare <- eval(bquote(expression(r^2==.(rSquare))))
    exp_pvalue <-  eval(bquote(expression(p < .(pValue) )))
    exp_samples <- eval(bquote(expression(n==.(Nsample) )))
    
    
    ### Plot
    # Base plot
    plot(Fsum_axis, Ssum_axis, 
         pch=16, col='transparent', 
         xlim=c(0,Fsum_axis),ylim=c(0,Ssum_axis),		
         main = paste(graphID, regionname, sep=" "),
         cex=1.1,
         axes = FALSE,
         xlab='',ylab='')
    
    axis(1,cex.axis=1.0)	
    axis(2,cex.axis=1.0)
    # Add X-Y lables  
    textx<-expression(R[tFRP]~(10^2 ~ MW))
    texty<-expression(R[tsa]~(10^2 ~ g/s)) 
    if (idx == 1)    {mtext(side=1, textx, cex=0.9,line=2.8)}
    if (idy == 1)    {mtext(side=2, texty, cex=0.9,line=2.0)} 
    
    if (Nsample>=5){
      # Add confidence level
      newx <- seq(0, Fsum_axis*1.2, length.out=Nsample)
      preds <- predict(ft1, newdata = data.frame(Fsum_final=newx),interval='confidence')
      polygon(c(rev(newx), newx), c(rev(preds[ ,3]), preds[ ,2]), col='grey90',border=NA)
      lines(newx, preds[ ,3], lty = 2, col = 'black')
      lines(newx, preds[ ,2], lty = 2, col = 'black')
      
      # Add legend
      legend("topleft",inset=c(-.05,-.03), c(exp_model,exp_rsquare,exp_pvalue,exp_samples),bty = "n",cex=1.1,merge=FALSE)
      
      # print value for analyzes
      if (regionname=="Peatland"){
        peatID = 1
      } else {
        peatID = 0
      }
      print(c(year, regionname, as.numeric(peatID),
              as.numeric(beta1), as.numeric(SdError),
              summary(ft1)$r.squared, pValue, Nsample))
    }
    
    # Add scatter points
    points(Fsum_final, Ssum_final, pch=21, col='black', bg=cols[DOY-180])
    
    box(which = "plot", lty = 1, lwd=1)
  }
  
  ### Add regression line
  # abline(a=0,b=1,col=8,lty=2,lwd=1.4) # 1:1 line
  abline(ft1,col="black",lwd=1.5,lty=1) 
  
}


