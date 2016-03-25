from boxbranding import *

hw_info = None

class HardwareInfo:
	device_name = _("unavailable")
	device_model = None
	device_version = ""
	device_revision = ""
	device_hdmi = False

	def __init__(self):
		global hw_info
		if hw_info is not None:
			return
		hw_info = self

		print "[HardwareInfo] Scanning hardware info"

		# Version
		try:
			self.device_version = open("/proc/stb/info/version").read().strip()
		except:
			pass

		# Revision
		try:
			self.device_revision = open("/proc/stb/info/board_revision").read().strip()
		except:
			pass

		# Name
		try:
			self.device_name = open("/proc/stb/info/model").read().strip()
		except:
			pass

		# Model
		try:
			self.device_model = open("/proc/stb/info/gbmodel").read().strip()
		except:
			pass

		if self.device_model is None:
			self.device_model = self.device_name

		# HDMI capbility
		if getMachineBuild() in ('gb7325', 'gb7358', 'gb7356', 'gb7362', 'gb7252', 'xc7362', 'hd2400'):
			self.device_hdmi = True
		else:
			self.device_hdmi = False

		print "Detected: " + self.get_device_string()


	def get_device_name(self):
		return hw_info.device_name

	def get_device_model(self):
		return hw_info.device_model

	def get_device_version(self):
		return hw_info.device_version

	def get_device_revision(self):
		return hw_info.device_revision

	def get_device_string(self):
		s = hw_info.device_model
		if hw_info.device_revision != "":
			s += " (" + hw_info.device_revision + "-" + hw_info.device_version + ")"
		elif hw_info.device_version != "":
			s += " (" + hw_info.device_version + ")"
		return s

	def has_hdmi(self):
		return hw_info.device_hdmi
