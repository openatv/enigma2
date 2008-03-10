SystemInfo = { }

#FIXMEE...
def getNumVideoDecoders():
	from Tools.Directories import fileExists
	idx = 0
	while fileExists("/dev/dvb/adapter0/video%d"%(idx), 'w'):
		idx += 1

SystemInfo["NumVideoDecoders"] = getNumVideoDecoders()
