class HardwareInfo:
	def __init__(self):
		self.device = "unknown"
		try:
			file = open("/proc/stb/info/model", "r")
			self.device = file.readline().strip()
			file.close()
		except:
			print "----------------"
			print "you should upgrade to new drivers for the hardware detection to work properly"
			print "----------------"
			print "fallback to detect hardware via /proc/cpuinfo!!"
			try:
				rd = open("/proc/cpuinfo", "r").read()
				if rd.find("Brcm4380 V4.2") != -1:
					self.device = "dm8000"
					print "dm8000 detected!"
				elif rd.find("Brcm7401 V0.0") != -1:
					self.device = "dm800"
					print "dm800 detected!"
				elif rd.find("MIPS 4KEc V4.8") != -1:
					self.device = "dm7025"
					print "dm7025 detected!"
			except:
				pass

	def get_device_name(self):
		return self.device
	
	device_name = property(get_device_name)

