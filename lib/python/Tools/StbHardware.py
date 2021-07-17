from fcntl import ioctl
from os.path import exists, isfile
from struct import pack, unpack
from time import time, localtime, gmtime
from boxbranding import getBoxType, getBrandOEM
from Tools.Directories import fileReadLine, fileWriteLine

MODULE_NAME = __name__.split(".")[-1]
wasTimerWakeup = None


def getFPVersion():
	version = None
	try:
		if getBrandOEM() == "blackbox" and isfile("/proc/stb/info/micomver"):
			version = fileReadLine("/proc/stb/info/micomver", source=MODULE_NAME)
		elif getBoxType() in ('dm7080', 'dm820', 'dm520', 'dm525', 'dm900', 'dm920'):
			version = open("/proc/stb/fp/version", "r").read()
		else:
			version = int(open("/proc/stb/fp/version", "r").read())
	except IOError:
		try:
			with open("/dev/dbox/fp0") as fd:
				version = ioctl(fd.fileno(), 0)
		except (IOError, OSError) as err:
			print("[StbHardware] Error %d: Unable to access '/dev/dbox/fp0', getFPVersion failed!  (%s)" % (err.errno, err.strerror))
	return version


def setFPWakeuptime(wutime):
	if not fileWriteLine("/proc/stb/fp/wakeup_time", str(wutime), source=MODULE_NAME):
		try:
			with open("/dev/dbox/fp0") as fd:
				ioctl(fd.fileno(), 6, pack('L', wutime))  # Set wake up time.
		except (IOError, OSError) as err:
			print("[StbHardware] Error %d: Unable to write to '/dev/dbox/fp0', setFPWakeuptime failed!  (%s)" % (err.errno, err.strerror))


def setRTCoffset():
	forsleep = (localtime(time()).tm_hour - gmtime(time()).tm_hour) * 3600
	if fileWriteLine("/proc/stb/fp/rtc_offset", str(forsleep), source=MODULE_NAME):
		print("[StbHardware] Set RTC offset to %s sec." % forsleep)
	else:
		print("[StbHardware] Error: Write to '/proc/stb/fp/rtc_offset' failed!")


def setRTCtime(wutime):
	if exists("/proc/stb/fp/rtc_offset"):
		setRTCoffset()
	if not fileWriteLine("/proc/stb/fp/rtc", str(wutime), source=MODULE_NAME):
		try:
			with open("/dev/dbox/fp0") as fd:
				ioctl(fd.fileno(), 0x101, pack('L', wutime))  # Set time.
		except (IOError, OSError) as err:
			print("[StbHardware] Error %d: Unable to write to '/dev/dbox/fp0', setRTCtime failed!  (%s)" % (err.errno, err.strerror))


def getFPWakeuptime():
	wakeup = fileReadLine("/proc/stb/fp/wakeup_time", source=MODULE_NAME)
	if wakeup is None:
		try:
			with open("/dev/dbox/fp0") as fd:
				wakeup = unpack('L', ioctl(fd.fileno(), 5, '    '))[0]  # Get wakeup time.
		except (IOError, OSError) as err:
			wakeup = 0
			print("[StbHardware] Error %d: Unable to read '/dev/dbox/fp0', getFPWakeuptime failed!  (%s)" % (err.errno, err.strerror))
	return int(wakeup)


def getFPWasTimerWakeup(check=False):
	global wasTimerWakeup
	isError = False
	if wasTimerWakeup is not None:
		if check:
			return wasTimerWakeup, isError
		return wasTimerWakeup
	wasTimerWakeup = fileReadLine("/proc/stb/fp/was_timer_wakeup", source=MODULE_NAME)
	if wasTimerWakeup is not None:
		wasTimerWakeup = int(wasTimerWakeup) and True or False
		if not fileWriteLine("/tmp/was_timer_wakeup.txt", str(wasTimerWakeup), source=MODULE_NAME):
			try:
				with open("/dev/dbox/fp0") as fd:
					wasTimerWakeup = unpack('B', ioctl(fd.fileno(), 9, ' '))[0] and True or False
			except (IOError, OSError) as err:
				isError = True
				print("[StbHardware] Error %d: Unable to read '/dev/dbox/fp0', getFPWasTimerWakeup failed!  (%s)" % (err.errno, err.strerror))
	else:
		wasTimerWakeup = False
	if wasTimerWakeup:
		clearFPWasTimerWakeup()  # Clear hardware status.
	if check:
		return wasTimerWakeup, isError
	return wasTimerWakeup


def clearFPWasTimerWakeup():
	if not fileWriteLine("/proc/stb/fp/was_timer_wakeup", "0", source=MODULE_NAME):
		try:
			with open("/dev/dbox/fp0") as fd:
				ioctl(fd.fileno(), 10)
		except (IOError, OSError) as err:
			print("[StbHardware] Error %d: Unable to update '/dev/dbox/fp0', clearFPWasTimerWakeup failed!  (%s)" % (err.errno, err.strerror))
