import serial
from xbee import ZigBee
import commands
import time
import matplotlib.pyplot as mpl
import numpy as np
import re
from datetime import datetime
import RPi.GPIO as GPIO
import MySQLdb 

def read_T(dev):
    """
    Read temperatures from 1-wire bus.
    """
    path = '/sys/bus/w1/devices/28-00000%s/w1_slave' % dev
    fd = open(path,'r')
    line = fd.readline()
    line = fd.readline()
    ls = line.split()
    temp = ls[-1].split('=')[1]
    temperature = float(temp)/1000.
    fd.close()
    return temperature

def write_logf(logf):
    """
    Function for generating log file.
    """
    devs = ['6962005','698376f','6983b64','6983fc4','698420a','6984389','6984c87','6984f6d','6985306','69863a6','698b03d','698cb08','6984dc5','696246e','6984996']
    desc = ['Topp tank 1','Botten tank 1','Kallvatten','Kamin CL','Golvv. retur','Radiator retur','Radiator framl.','Varmvatten','Kamin HL','Topp tank 2','Golvv. framl.','Botten tank 2','Inomhus nere','Huvud ret.','Huvud framl.']
    ser = serial.Serial('/dev/ttyUSB0',9600)
    xbee = ZigBee(ser)
    
    # Set up GPIO pin 17 as input
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(17,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)
    
    # SQL database
    db = MySQLdb.connect("localhost", "monitor", "Frodo12%", "heatlog")
    curs = db.cursor()
    
    fdut = open(logf,'a')
    #fdut.write('Time:\t\tTT1:\tBT1:\tKV:\tKCL:\tGoR:\tRaR:\tRaF:\tVV:\tKHL:\tTT2:\tGoF:\tBT2:\tInD:\tMFW:\tMRT:\tUTE:\tUPPE:\tHW_ON:\n')
    old_temps = {}
    exception = None
    
    while True:
        temps = {}
        packet = xbee.wait_read_frame()
	outfound = False
	upfound = False
	if packet:
	    if packet['source_addr']=='\xc4\xf4':
	        val1 = packet['samples'][0]['adc-2'] # ADC channel 2. Outside
		outfound = True
		packet = xbee.wait_read_frame()
		if packet:
		    if packet['source_addr']=='\x86\xb2':
		        val2 = packet['samples'][0]['adc-0'] # ADC channel 0. Upstairs
		        upfound = True
	    if packet['source_addr']=='\x86\xb2':
	        val2 = packet['samples'][0]['adc-0'] # ADC channel 0. Upstairs
	        upfound = True
	        packet = xbee.wait_read_frame()
		if packet:
		    if packet['source_addr']=='\xc4\xf4':
		        val1 = packet['samples'][0]['adc-2'] # ADC channel 2. Outside
		        outfound = True
	    # Maximum input voltage on XBee ADC is 1.2 V. 
	    # This corresponds to (10-bit ADC) 1024.
	    # TMP36 is specified to output 750 mV at 25 degrees C.
	    # The scaling is 10 mV/deg.
	    if upfound and outfound:
	        mV1 = (1200.*(float(val1)))/1024. 
	        temp1 = mV1/10. - 50.
                temps['out'] = temp1
	        mV2 = (1200.*(float(val2)))/1024. 
	        temp2 = mV2/10. - 50. -2. # Correct 2 degrees due to TMP36 error compared to 1-wire
                temps['upstairs'] = temp2
	        k = 0
	        for dev in devs:
	            try:
		        temps[desc[k]] = read_T(dev)
		        old_temps[desc[k]] = read_T(dev)
		        exception = None
	            except IOError: 
		        temps[desc[k]] = old_temps[desc[k]]
		        exception = '*%s*' % dev
		    k += 1
	        strin = ''
	        strin += '%s\t' % time.strftime("%y%m%d %H:%M")
	        k = 0
	        for dev in devs:
	            strin += '%5.3f\t' % temps[desc[k]]
		    with db:
		        curs.execute("INSERT INTO tempdat values(CURRENT_DATE(), NOW(), \"%s\", %.3f)" % (devs[k],float(temps[desc[k]])))
	            k += 1
	        strin += '%5.3f\t' % temps['out']
	        strin += '%5.3f\t' % temps['upstairs']
		with db:
		    curs.execute("INSERT INTO tempdat values(CURRENT_DATE(), NOW(), \"%s\", %.3f)" % ('out',float(temps['out'])))
		    curs.execute("INSERT INTO tempdat values(CURRENT_DATE(), NOW(), \"%s\", %.3f)" % ('upstairs',float(temps['upstairs'])))
		if GPIO.input(17):
		    with db:
		        curs.execute("INSERT INTO tempdat values(CURRENT_DATE(), NOW(), \"%s\", %d)" % ('HWON',1))
		    strin += '1\t' 
		else:
		    with db:
		        curs.execute("INSERT INTO tempdat values(CURRENT_DATE(), NOW(), \"%s\", %d)" % ('HWON',0))
		    strin += '0\t'
	        if exception is not None:
		    with db:
		        curs.execute("INSERT INTO tempdat values(CURRENT_DATE(), NOW(), \"%s\",\"%s\")" % ('ERROR',exception))
	            strin += '%s\t' % exception
	        strin += '\n'
	        fdut.write(strin)
	        # Flush file buffer
	        fdut.flush()

 
write_logf('/home/pi/pyscripts/tlogg.txt')  
