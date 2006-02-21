def getFPVersion():
	from fcntl import ioctl
	try:
		fp = open("/dev/dbox/fp0")
		return ioctl(fp.fileno(),0)
	except IOError:
		return None
