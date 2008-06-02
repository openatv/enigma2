from enigma import eDVBResourceManager

SystemInfo = { }

#FIXMEE...
def getNumVideoDecoders():
	from Tools.Directories import fileExists
	idx = 0
	while fileExists("/dev/dvb/adapter0/video%d"%(idx), 'w'):
		idx += 1
	return idx

SystemInfo["NumVideoDecoders"] = getNumVideoDecoders()
SystemInfo["CanMeasureFrontendInputPower"] = eDVBResourceManager.getInstance().canMeasureFrontendInputPower()
