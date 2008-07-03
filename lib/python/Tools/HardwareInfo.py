class HardwareInfo:
	def __init__(self):
		self.device = "unknown"
		file = open("/proc/stb/info/model", "r")
		self.device = file.readline().strip()
		
	def get_device_name(self):
		return self.device
	
	device_name = property(get_device_name)