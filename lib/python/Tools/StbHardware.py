from time import time, localtime, gmtime
from os import path
from fcntl import ioctl
from struct import pack, unpack
from Components.config import config
from boxbranding import getBoxType, getBrandOEM

def getFPVersion():
	ret = None
	try:
		if getBrandOEM() == "blackbox":
			file = open("/proc/stb/info/micomver", "r")
			ret = file.readline().strip()
			file.close()
		elif getBoxType() in ('dm7080','dm820','dm520','dm525','dm900','dm920'):
			ret = open("/proc/stb/fp/version", "r").read()
		else:	
			ret = long(open("/proc/stb/fp/version", "r").read())
	except IOError:
		try:
			fp = open("/dev/dbox/fp0")
			ret = ioctl(fp.fileno(),0)
		except IOError:
			print "getFPVersion failed!"
	return ret

def setFPWakeuptime(wutime):
	try:
		f = open("/proc/stb/fp/wakeup_time", "w")
		f.write(str(wutime))
		f.close()
	except IOError:
		try:
			fp = open("/dev/dbox/fp0")
			ioctl(fp.fileno(), 6, pack('L', wutime)) # set wake up
			fp.close()
		except IOError:
			print "setFPWakeupTime failed!"

def setRTCoffset():
	forsleep = (localtime(time()).tm_hour-gmtime(time()).tm_hour)*3600
	print "[RTC] set RTC offset to %s sec." % (forsleep)
	try:
		open("/proc/stb/fp/rtc_offset", "w").write(str(forsleep))
	except IOError:
		print "setRTCoffset failed!"

def setRTCtime(wutime):
        if path.exists("/proc/stb/fp/rtc_offset"):
		setRTCoffset()
	try:
		f = open("/proc/stb/fp/rtc", "w")
		f.write(str(wutime))
		f.close()
	except IOError:
		try:
			fp = open("/dev/dbox/fp0")
			ioctl(fp.fileno(), 0x101, pack('L', wutime)) # set wake up
			fp.close()
		except IOError:
			print "setRTCtime failed!"

def getFPWakeuptime():
	ret = 0
	try:
		f = open("/proc/stb/fp/wakeup_time", "r")
		ret = long(f.read())
		f.close()
	except IOError:
		try:
			fp = open("/dev/dbox/fp0")
			ret = unpack('L', ioctl(fp.fileno(), 5, '    '))[0] # get wakeuptime
			fp.close()
		except IOError:
			print "getFPWakeupTime failed!"
	return ret

wasTimerWakeup = None

def getFPWasTimerWakeup(check = False):
	global wasTimerWakeup
	isError = False
	if wasTimerWakeup is not None:
		if check:
			return wasTimerWakeup, isError
		return wasTimerWakeup
	wasTimerWakeup = False
	try:
		f = open("/proc/stb/fp/was_timer_wakeup", "r")
		file = f.read()
		f.close()
		wasTimerWakeup = int(file) and True or False
		f = open("/tmp/was_timer_wakeup.txt", "w")
		file = f.write(str(wasTimerWakeup))
		f.close()
	except:
		try:
			fp = open("/dev/dbox/fp0")
			wasTimerWakeup = unpack('B', ioctl(fp.fileno(), 9, ' '))[0] and True or False
			fp.close()
		except IOError:
			print "wasTimerWakeup failed!"
			isError = True

	if wasTimerWakeup:
		# clear hardware status
		clearFPWasTimerWakeup()
	if check:
		return wasTimerWakeup, isError
	return wasTimerWakeup

def clearFPWasTimerWakeup():
	try:
		f = open("/proc/stb/fp/was_timer_wakeup", "w")
		f.write('0')
		f.close()
	except:
		try:
			fp = open("/dev/dbox/fp0")
			ioctl(fp.fileno(), 10)
			fp.close()
		except IOError:
			print "clearFPWasTimerWakeup failed!"
