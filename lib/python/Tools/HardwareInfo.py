from Components.SystemInfo import BoxInfo


class HardwareInfo:
	device_name = None
	device_version = None

	def __init__(self):
		if HardwareInfo.device_name is not None:
#			print "using cached result"
			return

		HardwareInfo.device_name = "unknown"
		try:
			file = open("/proc/stb/info/model")
			HardwareInfo.device_name = file.readline().strip()
			file.close()
			if BoxInfo.getItem("brand") == "dags":
				HardwareInfo.device_name = "dm800se"
			try:
				file = open("/proc/stb/info/version")
				HardwareInfo.device_version = file.readline().strip()
				file.close()
			except OSError:
				pass
		except Exception:
			print("----------------")
			print("you should upgrade to new drivers for the hardware detection to work properly")
			print("----------------")
			print("fallback to detect hardware via /proc/cpuinfo!!")
			try:
				rd = open("/proc/cpuinfo").read()
				if "Brcm4380 V4.2" in rd:
					HardwareInfo.device_name = "dm8000"
					print("dm8000 detected!")
				elif "Brcm7401 V0.0" in rd:
					HardwareInfo.device_name = "dm800"
					print("dm800 detected!")
			except Exception:
				pass

	def get_device_name(self):
		return HardwareInfo.device_name

	def get_device_version(self):
		return HardwareInfo.device_version

	def get_device_model(self):
		return BoxInfo.getItem("machinebuild")

	def get_vu_device_name(self):
		return BoxInfo.getItem("machinebuild")

	def get_friendly_name(self):
		return BoxInfo.getItem("displaymodel")

	def linux_kernel(self):
		try:
			return open("/proc/version").read().split(' ', 4)[2].split('-', 2)[0]
		except Exception:
			return "unknown"
