import os

class RcModel:
	RCTYPE_DMM = 0
	RCTYPE_ET9X00 = 1
	RCTYPE_ET6X00 = 2
	RCTYPE_VU = 3
	RCTYPE_GB = 4
	RCTYPE_INI3000 = 5
	RCTYPE_INI7000 = 6
	RCTYPE_ODIN = 7
	RCTYPE_ET9500 = 8

	def __init__(self):
		self.currentRcType = self.RCTYPE_DMM
		self.readRcTypeFromProc()

	def rcIsDefault(self):
		if self.currentRcType != self.RCTYPE_DMM:
			return False
		return True

	def readFile(self, target):
		fp = open(target, 'r')
		out = fp.read()
		fp.close()
		return out.split()[0]

	def readRcTypeFromProc(self):
		if os.path.exists('/proc/stb/info/boxtype'):
			model = self.readFile('/proc/stb/info/boxtype')
			if model == 'et9500' or model == 'et9200' or model == 'et9000' or model == 'et5000' or model == 'et6000' or model == 'et9x00' or model == 'et5x00' or model == 'et6x00':
				rc = self.readFile('/proc/stb/ir/rc/type')
				if rc == '4':
					self.currentRcType = self.RCTYPE_DMM
				elif rc == '5' and model == 'et9200':
					self.currentRcType = self.RCTYPE_ODIN
				elif rc == '5':
					self.currentRcType = self.RCTYPE_ET9X00
				elif rc == '6':
					self.currentRcType = self.RCTYPE_DMM
				elif rc == '7':
					self.currentRcType = self.RCTYPE_ET6X00
				elif rc == '8':
					self.currentRcType = self.RCTYPE_VU
				elif rc == '9' or rc == '11':
					self.currentRcType = self.RCTYPE_ET9500
			elif model == 'gigablue':
				self.currentRcType = self.RCTYPE_GB
			elif model == 'ini-3000':
				self.currentRcType = self.RCTYPE_INI3000
			elif model == 'ini-5000' or model == 'ini-7000':
				self.currentRcType = self.RCTYPE_INI7000	
		elif os.path.exists('/proc/stb/info/vumodel'):
			self.currentRcType = self.RCTYPE_VU

	def getRcLocation(self):
		if self.currentRcType == self.RCTYPE_ET9X00:
			return '/usr/share/enigma2/rc_models/et9x00/'
		elif self.currentRcType == self.RCTYPE_ET6X00:
			return '/usr/share/enigma2/rc_models/et6x00/'
		elif self.currentRcType == self.RCTYPE_ET9500:
			return '/usr/share/enigma2/rc_models/et9500/'	
		elif self.currentRcType == self.RCTYPE_VU:
			return '/usr/share/enigma2/rc_models/vu/'
		elif self.currentRcType == self.RCTYPE_GB:
			return '/usr/share/enigma2/rc_models/gb/'
		elif self.currentRcType == self.RCTYPE_INI3000:
			return '/usr/share/enigma2/rc_models/ini3000/'
		elif self.currentRcType == self.RCTYPE_INI7000:
			return '/usr/share/enigma2/rc_models/ini7000/'
		elif self.currentRcType == self.RCTYPE_ODIN:
			return '/usr/share/enigma2/rc_models/odin/'		

rc_model = RcModel()
