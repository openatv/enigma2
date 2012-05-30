from fcntl import ioctl
from struct import pack, unpack
from Components.config import config

def getFPVersion():
	ret = None
	try:
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
		open("/proc/stb/fp/wakeup_time", "w").write(str(wutime))
	except IOError:
		try:
			fp = open("/dev/dbox/fp0")
			ioctl(fp.fileno(), 6, pack('L', wutime)) # set wake up
		except IOError:
			print "setFPWakeupTime failed!"

def setRTCtime(wutime):
	try:
		open("/proc/stb/fp/rtc", "w").write(str(wutime))
	except IOError:
		try:
			fp = open("/dev/dbox/fp0")
			ioctl(fp.fileno(), 0x101, pack('L', wutime)) # set wake up
		except IOError:
			print "setRTCtime failed!"

def getFPWakeuptime():
	ret = 0
	try:
		ret = long(open("/proc/stb/fp/wakeup_time", "r").read())
	except IOError:
		try:
			fp = open("/dev/dbox/fp0")
			ret = unpack('L', ioctl(fp.fileno(), 5, '    '))[0] # get wakeuptime
		except IOError:
			print "getFPWakeupTime failed!"
	return ret

wasTimerWakeup = None

def getFPWasTimerWakeup():
	global wasTimerWakeup
	if wasTimerWakeup is not None:
		return wasTimerWakeup
	wasTimerWakeup = False
	try:
		wasTimerWakeup = int(open("/proc/stb/fp/was_timer_wakeup", "r").read()) and True or False
	except:
		try:
			fp = open("/dev/dbox/fp0")
			wasTimerWakeup = unpack('B', ioctl(fp.fileno(), 9, ' '))[0] and True or False
		except IOError:
			print "wasTimerWakeup failed!"

	if config.misc.boxtype.value == 'gb800se' or config.misc.boxtype.value == 'gb800solo' or config.misc.boxtype.value == 'gb800ue':
		if not wasTimerWakeup:
			from os import path, system
			from time import time, strftime, localtime
			if path.isfile("/var/.was_wakeup_timer"):
				system("echo wakeuptime=%s, current time=%s > /tmp/wakeup.txt" %(strftime("%d/%m/%Y %H:%M",localtime(config.misc.wakeUpTime.value)), strftime("%H:%M",localtime(time()))))
				if (config.misc.wakeUpTime.value - time()) < 300:
					wasTimerWakeup = True
	
	if wasTimerWakeup:
		# clear hardware status
		clearFPWasTimerWakeup()
	return wasTimerWakeup

def clearFPWasTimerWakeup():
	try:
		open("/proc/stb/fp/was_timer_wakeup", "w").write('0')
	except:
		try:
			fp = open("/dev/dbox/fp0")
			ioctl(fp.fileno(), 10)
		except IOError:
			print "clearFPWasTimerWakeup failed!"

	if config.misc.boxtype.value == 'gb800se' or config.misc.boxtype.value == 'gb800solo' or config.misc.boxtype.value == 'gb800ue':
		from os import path, system
		if path.isfile("/var/.was_wakeup_timer"):
			system("rm -f /var/.was_wakeup_timer")
