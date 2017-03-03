import math
import commands
import sys
import time
import re
import numpy as np
import os

def pid(Tnom,Tfeed):
    """
    Tfeed = list of temperatures
    """
    fdd = open('/home/pi/pyscripts/piddata.txt','r')
    linel = fdd.readline()
    lsl = re.sub('r\s',' ',linel.strip()).split()
    K = float(lsl[0])
    linel = fdd.readline()
    lsl = re.sub('r\s',' ',linel.strip()).split()
    Ti = float(lsl[0])
    linel = fdd.readline()
    lsl = re.sub('r\s',' ',linel.strip()).split()
    T = float(lsl[0])
    fdd.close()
    dt = len(Tfeed)
    elist = [Tnom - Tfeed[k] for k in xrange(dt)]
    e = np.array(elist)
    t = np.array([k for k in xrange(dt)])
    de_dt = np.diff(e)
    integr = np.trapz(e)
    return -(K*np.average(e)+T*np.average(de_dt)+1/Ti*integr)

def read_T(dev):
    """
    Read temperatures from 1-wire bus.
    """
    
    path = '/sys/bus/w1/devices/28-00000%s/w1_slave' % dev
    fd = None
    while fd is None:
        try:
	    fd = open(path,'r')
	except (OSError, IOError):
	    fd = None
	    time.sleep(60.)
    line = fd.readline()
    line = fd.readline()
    ls = line.split()
    temp = ls[-1].split('=')[1]
    temperature = float(temp)/1000.
    fd.close()
    return temperature
    
def get_t(dt,dev):
    """
    Get the temperature for the last dt seconds.
    """
    dt = int(dt)
    T = []
    for k in xrange(dt):
        T.append(read_T(dev))
	time.sleep(1.)
    return T
   

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

def bytes(num):
    return hex(num >> 8), hex(num & 0xFF)

def deg2hex(deg):
    """
    Function that converts valve angle (0 - 90 deg) 
    to a hexadecimal value between 0x000 and 0xFFF 
    """
    if deg>90.:
        deg = 90.
    deg -= 0.001
    if deg<0.:
        deg = 0.0
    decim = int(math.floor(4096./90.*deg))
    
    chaddr ,daddr = bytes(decim) 
    return '%s %s' % (chaddr,daddr)
    
def position_valve(angle):
    """
    Function to open/close valve. 0 degrees means fully open valve.
    """
    # DAC is located on address 0x60
    MASK = '0x60'
    failure,output = commands.getstatusoutput("i2cset -y 1 %s %s b" % (MASK,deg2hex(angle)))
    if failure:
        sys.exit(1)
    else:
        return output

def regulate(datafile,starting_valve_pos):
    """
    This function opens/closes mixture valve according to whether the temperature
    is too high or too low.
    """
    # The valve will open from 90 degs to 0 degs in 120 sec. 
    # This means that one degree takes 4/3 sec.
    # The function will open/close in steps of 3/4 degrees,
    # which will then take 1 s.
    # 0 degrees position means that no mixture between feed and return is present
    # and 90 degrees position means that no heat is transfered to the radiators or the
    # floor heat system.


    w1_feedwater = '6984c87'
    
    cur_valve_pos = starting_valve_pos
    
    #logf = open('logf.txt','w')
    while True:
        execfile('/home/pi/pyscripts/reg_settings.py')
	temp = ''
        failure, output = commands.getstatusoutput("tail -%s %s" % (DELTA_T,datafile))
	if failure:
	    sys.exit(1)
        lines = output.split('\n')
	no_of_elems = len(re.sub('r\s',' ',lines[0].strip()).split())-2
	averages = np.zeros((1,no_of_elems))
	for line in lines:
	    ls = re.sub('r\s',' ',line.strip()).split()
	    for p in xrange(no_of_elems):
	        try:
		    averages[0,p] += float(ls[p+2])
		except (ValueError, IndexError):
		    pass
	averages = averages/float(DELTA_T)
	khl = averages[0,8]
	
	tank_ave = 0.25*(averages[0,0]+averages[0,1]+averages[0,9]+averages[0,11])
	feed_nom = out2fram(averages[0,15],(averages[0,12]+averages[0,16])/2.,UV_fact=UV_FACT,intemp_nom=INTEMP_NOM)
	feed = get_t(dt,w1_feedwater)
	if lines[-1][18]!=1:
	    STEP = pid(feed_nom,feed)
	else:
	    STEP = 0
	feed_ave = sum(feed)/(len(feed))
	temp += '%s %s Feed nom: %s\n'  % (str(ls[0]),str(ls[1]),str(feed_nom))	
	temp += '%s %s Feed ave: %s\n'  % (str(ls[0]),str(ls[1]),str(feed_ave))	
	#logf.write(temp)
	#logf.flush()
		
	if abs(feed_ave-feed_nom)>HYST:
	    while abs(feed_ave-feed_nom)>HYST:
		temp = ''
		if STEP>0:
		    check_val = 90. - cur_valve_pos - STEP
		else:
		    check_val = cur_valve_pos + STEP
		
		if check_val>0:
		    position_valve(cur_valve_pos+STEP)
		    time.sleep(120./90.*abs(STEP))
		    cur_valve_pos += STEP
		    temp += '%s %s Pos: %s\n'  % (str(ls[0]),str(ls[1]),str(cur_valve_pos))
		else:
		    if STEP<0:
		        cur_valve_pos = 0.0
		        position_valve(0.0)
		    else:
		        cur_valve_pos = 90.0
			position_valve(90.0)
		    temp += '%s %s Pos: %s\n'  % (str(ls[0]),str(ls[1]),str(cur_valve_pos))
		    break
		failure, output = commands.getstatusoutput("tail -%s %s" % (DELTA_T,datafile))
	        if failure:
	            sys.exit(1)
                lines = output.split('\n')
	        no_of_elems = len(re.sub('r\s',' ',lines[0].strip()).split())-2
	        averages = np.zeros((1,no_of_elems))
	        for line in lines:
	            ls = re.sub('r\s',' ',line.strip()).split()
	            for p in xrange(no_of_elems):
	                try:
			    averages[0,p] += float(ls[p+2])
			except (ValueError, IndexError):
			    pass
	        averages = averages/float(DELTA_T)
                tank_ave = 0.25*(averages[0,0]+averages[0,1]+averages[0,9]+averages[0,11])		
		feed_nom = out2fram(averages[0,15],(averages[0,12]+averages[0,16])/2.,UV_fact=UV_FACT,intemp_nom=INTEMP_NOM)
	        feed = get_t(dt,w1_feedwater)
		if lines[-1][18]!=1:
		    STEP = pid(feed_nom,feed)
	        else:
		    STEP = 0
		feed_ave = sum(feed)/(len(feed))
	        temp += '%s %s Feed nom: %s\n'  % (str(ls[0]),str(ls[1]),str(feed_nom))	
	        temp += '%s %s Feed ave: %s\n'  % (str(ls[0]),str(ls[1]),str(feed_ave))	
	        #logf.write(temp)
	        #logf.flush()
os.system('i2cset -y 1 0x60 0x00 0x00 b')
time.sleep(120.)
regulate('/home/pi/pyscripts/tlogg.txt',0.)
#print out2fram(-5.0,23.1)
#regulate('tlogg.txt',90.)
