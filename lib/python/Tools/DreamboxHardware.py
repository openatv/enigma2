def getFPVersion():
	from fcntl import ioctl
	try:
		fp = open("/dev/dbox/fp0")
		return ioctl(fp.fileno(),0)
	except IOError:
		return None

def setFPWakeuptime(wutime):
	from fcntl import ioctl
	from struct import pack

	try:
		fp = open("/dev/dbox/fp0")
		ioctl(fp.fileno(), 6, pack('L', wutime)) # set wake up
	except IOError:
		pass	
