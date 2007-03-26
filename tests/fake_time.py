import time

real_time = None
time_offset = 0

def setRealtime():
	global real_time
	real_time = time.time

def setIdealtime():
	global real_time
	real_time = lambda: 0

def setTime(now):
	global time_offset
	time_offset = real_time() - now

setIdealtime()
setTime(0)

def my_time():
	return real_time() - time_offset

time.time = my_time

def my_sleep(sleep):
	global time_offset
	time_offset -= sleep
	print "(faking %f seconds)" % sleep

time.sleep = my_sleep
