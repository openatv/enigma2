import os

class RcModel:
	RCTYPE_DMM = 0
	RCTYPE_ET9X00 = 1
	RCTYPE_ET6X00 = 2
	RCTYPE_ET9500 = 3
	RCTYPE_VU = 4

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
			if len(model) == 6 and model[:2] == 'et':
				rc = self.readFile('/proc/stb/ir/rc/type')
				if rc == '4':
					self.currentRcType = self.RCTYPE_DMM
				elif rc == '5' or rc == '11':
					self.currentRcType = self.RCTYPE_ET9X00
				elif rc == '6':
					self.currentRcType = self.RCTYPE_DMM
				elif rc == '7':
					self.currentRcType = self.RCTYPE_ET6X00
				elif rc == '8':
					self.currentRcType = self.RCTYPE_VU
				elif rc == '9':
					self.currentRcType = self.RCTYPE_ET9500
		elif os.path.exists('/proc/stb/info/vumodel'):
			self.currentRcType = self.RCTYPE_VU

	def getRcLocation(self):
		if self.currentRcType == self.RCTYPE_ET9X00:
			return '/usr/share/enigma2/rc_models/et9x00/'
		elif self.currentRcType == self.RCTYPE_ET9500:
			return '/usr/share/enigma2/rc_models/et9500/'
		elif self.currentRcType == self.RCTYPE_ET6X00:
			return '/usr/share/enigma2/rc_models/et6x00/'
		elif self.currentRcType == self.RCTYPE_VU:
			return '/usr/share/enigma2/rc_models/vu/'

rc_model = RcModel()
