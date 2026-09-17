drawplot_peat <- function(x,outdir,years)
{
  mylist <- rm_sumoutlier(x, years)
  
  dfP1peat1 <- mylist[[1]]
  dfP1peat0 <- mylist[[2]]
  
  ###Plot Each Year
  jpeg(filename=paste(outdir, "TerAqu_", years,"_MAIAC_Rsa_FRP_Poly13_Legend.jpg",sep=""), width=7, height=3.6,units = 'in',res=300)
  par(mfrow=c(1,2))
  par(mar=c(4,3.5,1.5,0.1),xpd=FALSE,oma=c(0,0,0,3))
 
  plotSsum_vs_Fsum(dfP1peat1$FRPsumv,dfP1peat1$Rsasumv,strtoi(rownames(dfP1peat1)),"(a)","Peatland",1,1)
  plotSsum_vs_Fsum(dfP1peat0$FRPsumv,dfP1peat0$Rsasumv,strtoi(rownames(dfP1peat0)),"(b)","Non-peatland",1,1)
  
  ### Add vertical legend on the right
  addLegend()
  
  dev.off()
}


### add image legend
addLegend <- function() {
  
  par(
    fig = c(0, 1, 0, 1),
    oma = c(0, 0, 0, 0),
    mar = c(0, 0, 0, 0),
    new = TRUE
  )
  
  plot(
    0, 0,
    type = "n",
    bty = "n",
    xaxt = "n",
    yaxt = "n"
  )
  
  fields::image.plot(
    legend.only = TRUE,
    zlim = c(180, 340),
    col = cols,
    
    smallplot = c(0.94, 0.955, 0.23, 0.91),
    
    axis.args = list(
      at = seq(180, 340, by = 30),
      labels = seq(180, 340, by = 30),
      las = 0.5,
      cex.axis = 0.8,
      tck = -0.35,
      mgp = c(1.2, 0.2, 0)
    ),
    
    legend.args = list(
      text = "DOY",
      side = 3,
      line = 0.2,
      cex = 0.8
    )
  )
}






