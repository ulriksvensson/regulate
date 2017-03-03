# -*- coding: utf-8 -*-
global HYST,DELTA_T,INTEMP_NOM,UV_FACT,dt,DELAY_HI,DELAY_LO
HYST	     = 0.2	     # Trigger for valve movement
DELTA_T      = 10	     # Time step for moving averages
INTEMP_NOM   = 21.0	     # Nominal indoor temp
UV_FACT      = 3.0	     # UV-factor 
dt	     = 10	     # Number of seconds to average for feedwater
