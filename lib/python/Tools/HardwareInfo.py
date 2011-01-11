class HardwareInfo:
	device_name = None
	device_version = None

	def __init__(self):
		if HardwareInfo.device_name is not None:
#			print "using cached result"
			return

		HardwareInfo.device_name = "unknown"
		try:
			file = open("/proc/stb/info/model", "r")
			HardwareInfo.device_name = file.readline().strip()
			file.close()
			try:
				file = open("/proc/stb/info/version", "r")
				HardwareInfo.device_version = file.readline().strip()
				file.close()
			except:
				pass
		except:
			print "----------------"
			print "you should upgrade to new drivers for the hardware detection to work properly"
			print "----------------"
			print "fallback to detect hardware via /proc/cpuinfo!!"
			try:
				rd = open("/proc/cpuinfo", "r").read()
				if rd.find("Brcm4380 V4.2") != -1:
					HardwareInfo.device_name = "dm8000"
					print "dm8000 detected!"
				elif rd.find("Brcm7401 V0.0") != -1:
					HardwareInfo.device_name = "dm800"
					print "dm800 detected!"
				elif rd.find("MIPS 4KEc V4.8") != -1:
					HardwareInfo.device_name = "dm7025"
					print "dm7025 detected!"
			except:
				pass

	def get_device_name(self):
		return HardwareInfo.device_name

	def get_device_version(self):
		return HardwareInfo.device_version

	def has_hdmi(self):
		return (HardwareInfo.device_name == 'dm800se' or HardwareInfo.device_name == 'dm500hd' or (HardwareInfo.device_name == 'dm8000' and HardwareInfo.device_version != None))
