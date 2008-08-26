from fcntl import ioctl
from struct import pack, unpack

def getFPVersion():
	try:
		fp = open("/dev/dbox/fp0")
		return ioctl(fp.fileno(),0)
	except IOError:
		print "getFPVersion failed!"
		return None

def setFPWakeuptime(wutime):
	try:
		open("/proc/stb/fp/wakeup_time", "w").write(str(wutime))
	except IOError:
		try:
			fp = open("/dev/dbox/fp0")
			ioctl(fp.fileno(), 6, pack('L', wutime)) # set wake up
		except IOError:
			print "setFPWakeupTime failed!"

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

def getFPWasTimerWakeup():
	was_wakeup = False
	try:
		was_wakeup = int(open("/proc/stb/fp/was_timer_wakeup", "r").read()) and True or False
	except:
		try:
			fp = open("/dev/dbox/fp0")
			was_wakeup = unpack('B', ioctl(fp.fileno(), 9, ' '))[0] and True or False
		except IOError:
			print "wasTimerWakeup failed!"
	return was_wakeup

def clearFPWasTimerWakeup():
	try:
		open("/proc/stb/fp/was_timer_wakeup", "w").write('0')
	except:
		try:
			fp = open("/dev/dbox/fp0")
			ioctl(fp.fileno(), 10)
		except IOError:
			print "clearFPWasTimerWakeup failed!"
