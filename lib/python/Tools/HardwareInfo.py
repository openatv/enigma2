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
		
	def get_device_name(self):
		return self.device
	
	device_name = property(get_device_name)

