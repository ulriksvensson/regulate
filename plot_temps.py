import commands
import time
import matplotlib.pyplot as mpl
import numpy as np
import re
from datetime import datetime

def out2fram(outtemp,intemp,UV_fact=3.0,intemp_nom=21.0):
    """
    Function that calculates temperature corresponding to outdoor temp.
    """
    # Temperature curve 6 from CZ manual
    # Polynomial fit made in LibreOffice Calc
    # The feedwater temperature gets corrected (decreased)
    # by a factor multiplied by the difference between 
    # actual indoor temperature and nominal indoor temperature.
    corr = UV_fact*(intemp - intemp_nom)
    return -0.0026463536*outtemp**2 - 0.8582267732*outtemp + 35.8255494505 - corr


def plot_temps(dt,logf,ma=1):
    """
    Function for plotting logged temperatures over the interval dt (minutes).
    """
    no_samples = dt
    failure,output = commands.getstatusoutput("tail -%s %s > tempdata.txt" % (int(no_samples),logf))
    fd = open('tempdata.txt','r')
    k = 0
    data = np.zeros((no_samples,19))
    times = []
    while True:
        line = fd.readline()
        if not line:
            break
        ls = re.sub('r\s',' ',line.strip()).split()
	l = 0
	timestr = '%s %s' %(ls[0],ls[1])
	times.append(datetime.strptime(timestr,"%y%m%d %H:%M"))
	for elem in ls[2:]:
	    try:
	        data[k,l] = float(ls[l+2])
		l += 1
	    except ValueError:
	        pass
	    
	data[k,l] = out2fram(data[k,15],(data[k,12]+data[k,16])/2.,UV_fact=3.0,intemp_nom=21.0)
	k += 1
    tankmedel = (data[:,0]+data[:,1]+data[:,9]+data[:,11])/4.
    
    x = np.array([t for t in times])
    intemp = (data[:,12]+data[:,16])/2.
    uttemp = data[:,15]
    feed_nom = data[:,18]
    feed     = data[:,6]
    if ma>0:
        intemp_new  = []
        uttemp_new = []
	x_new       = []
	feed_nom_new = []
	feed_new = []
        for kk in xrange(len(intemp.tolist())-ma):
	    intemp_new.append(sum(intemp.tolist()[kk:kk+ma])/ma)
	    uttemp_new.append(sum(uttemp.tolist()[kk:kk+ma])/ma)
	    feed_nom_new.append(sum(feed_nom.tolist()[kk:kk+ma])/ma)
	    feed_new.append(sum(feed.tolist()[kk:kk+ma])/ma)
	    x_new.append(x[kk])
	intemp = intemp_new
	uttemp = uttemp_new
	feed_nom = feed_nom_new
	feed = feed_new
	x = x_new
    feed_nom_hi = [elem+0.2 for elem in feed_nom]
    feed_nom_lo = [elem-0.2 for elem in feed_nom]
    mpl.plot(x,feed_nom_lo,'ro')
    mpl.plot(x,feed_nom_hi,'b*')
    mpl.plot(x,feed,'bx')
    mpl.plot(x,feed_nom,'k*')
    mpl.show()
    #mpl.savefig('in_out.png')
    
   
def plot_im(dt,logf,ma,tsleep):
    while True:
        plot_temps(dt,logf,ma)
        time.sleep(tsleep) 

plot_temps(1200,'tlogg.txt',10)
