import time
from enigma import eDVBLocalTimeHandler

org_time = time.time
time_difference = eDVBLocalTimeHandler.getInstance().difference()

def myTime():
	global time_difference
	t = org_time()
	t += time_difference
	return t

def timeChangedCallback():
	global time_difference
	time_difference = eDVBLocalTimeHandler.getInstance().difference()

eDVBLocalTimeHandler.getInstance().m_timeUpdated.get().append(timeChangedCallback)
time.time = myTime