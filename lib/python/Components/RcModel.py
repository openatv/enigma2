from boxbranding import getBoxType, getMachineName
from Tools.StbHardware import getFPVersion
import os

class RcModel:
	RCTYPE_DMM = 0
	RCTYPE_DMM1 = 1
	RCTYPE_DMM2 = 2
	RCTYPE_E3HD = 3
	RCTYPE_EBOX5000 = 4
	RCTYPE_ET4X00 = 5
	RCTYPE_ET6X00 = 6
	RCTYPE_ET6500 = 7
	RCTYPE_ET9X00 = 8
	RCTYPE_ET9500 = 9
	RCTYPE_GB = 10
	RCTYPE_INI0 = 11
	RCTYPE_INI1 = 12
	RCTYPE_INI2 = 13
	RCTYPE_INI3 = 14
	RCTYPE_INI4 = 15
	RCTYPE_IQON = 16
	RCTYPE_IXUSSONE = 17
	RCTYPE_IXUSSZERO = 18
	RCTYPE_ODINM7 = 19
	RCTYPE_ODINM9 = 20
	RCTYPE_TM = 21
	RCTYPE_VU = 22
	RCTYPE_VU2 = 23
	RCTYPE_VU3 = 24
	RCTYPE_XP1000 = 25


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
		if getBoxType() == 'dm8000':
			self.currentRcType = self.RCTYPE_DMM
		elif getBoxType() == 'dm7020hd' or getBoxType() == 'dm7020hdv2' or getBoxType() == 'dm800sev2' or getBoxType() == 'dm500hdv2':
			self.currentRcType = self.RCTYPE_DMM2
		elif getBoxType() == 'dm800' or getBoxType() == 'dm800se' or getBoxType() == 'dm500hd':
			self.currentRcType = self.RCTYPE_DMM1
		elif getBoxType() == 'ebox5000':
			self.currentRcType = self.RCTYPE_EBOX5000
		elif getBoxType().startswith('et'):
			model = self.readFile('/proc/stb/info/boxtype')
			rc = self.readFile('/proc/stb/ir/rc/type')
			if rc == '5':
				self.currentRcType = self.RCTYPE_ET9X00
			elif rc == '7':
				self.currentRcType = self.RCTYPE_ET6X00
			elif rc == '9' and model == 'et9500':
				self.currentRcType = self.RCTYPE_ET9500
			elif rc == '9' and model == 'et6500':
				self.currentRcType = self.RCTYPE_ET6500
			elif rc == '11' and model == 'et9200':
				self.currentRcType = self.RCTYPE_ET9500
			elif rc == '11' and model == 'et9000':
				self.currentRcType = self.RCTYPE_ET9X00
			elif rc == '13' and model == 'et4000':
				self.currentRcType = self.RCTYPE_ET4X00
		elif getBoxType().startswith('gb'):
			self.currentRcType = self.RCTYPE_GB
		elif getBoxType().startswith('iqon'):
			self.currentRcType = self.RCTYPE_IQON
		elif getBoxType() == 'ixussone':
			self.currentRcType = self.RCTYPE_IXUSSONE
		elif getBoxType() == 'ixusszero':
			self.currentRcType = self.RCTYPE_IXUSSZERO
		elif getBoxType().startswith('odin'):
			model = self.readFile('/proc/stb/info/boxtype')
			if model == 'odinm7':
				self.currentRcType = self.RCTYPE_ODINM7
			elif model == 'odinm9':
				self.currentRcType = self.RCTYPE_ODINM9
		elif getBoxType().startswith('tm'):
			self.currentRcType = self.RCTYPE_TM
		elif getBoxType().startswith('mb'):
			self.currentRcType = self.RCTYPE_INI3
		elif getBoxType().startswith('venton') or getBoxType().startswith('ini'):
			model = self.readFile('/proc/stb/info/boxtype')
			if model == 'ini-1000' or model == 'ini-1000ru' or model == 'ini-5000ru' or model == 'ini-9000ru':
				self.currentRcType = self.RCTYPE_INI2
			elif model == 'ini-1000sv' or model == 'ini-5000sv' or model == 'ini-9000sv':
				self.currentRcType = self.RCTYPE_INI3
			elif model == 'ini-1000de' or model == 'ini-9000de':
				self.currentRcType = self.RCTYPE_INI4
			elif model == 'ini-3000':
				fp_version = str(getFPVersion())
				if fp_version.startswith('1'):
					self.currentRcType = self.RCTYPE_INI0
				else:
					self.currentRcType = self.RCTYPE_INI2
			elif model == 'ini-5000' or model == 'ini-7000' or model == 'ini-7012' or model == 'ini-9000':
				self.currentRcType = self.RCTYPE_INI1
			elif model == 'e3hd':
				self.currentRcType = self.RCTYPE_E3HD
		elif getBoxType().startswith('vu'):
			if getBoxType() == 'vuultimo':
				self.currentRcType = self.RCTYPE_VU2
			elif getBoxType() == 'vuduo2':
				self.currentRcType = self.RCTYPE_VU3
			else:
				self.currentRcType = self.RCTYPE_VU
		elif getBoxType().startswith('xp'):
			self.currentRcType = self.RCTYPE_XP1000

	def getRcLocation(self):
		if self.currentRcType == self.RCTYPE_DMM:
			return '/usr/share/enigma2/rc_models/dmm0/'
		elif self.currentRcType == self.RCTYPE_DMM1:
			return '/usr/share/enigma2/rc_models/dmm1/'
		elif self.currentRcType == self.RCTYPE_DMM2:
			return '/usr/share/enigma2/rc_models/dmm2/'
		elif self.currentRcType == self.RCTYPE_E3HD:
			return '/usr/share/enigma2/rc_models/e3hd/'	
		elif self.currentRcType == self.RCTYPE_EBOX5000:
			return '/usr/share/enigma2/rc_models/ebox5000/'
		elif self.currentRcType == self.RCTYPE_ET4X00:
			return '/usr/share/enigma2/rc_models/et4x00/'
		elif self.currentRcType == self.RCTYPE_ET6X00:
			return '/usr/share/enigma2/rc_models/et6x00/'
		elif self.currentRcType == self.RCTYPE_ET6500:
			return '/usr/share/enigma2/rc_models/et6500/'
		elif self.currentRcType == self.RCTYPE_ET9X00:
			return '/usr/share/enigma2/rc_models/et9x00/'
		elif self.currentRcType == self.RCTYPE_ET9500:
			return '/usr/share/enigma2/rc_models/et9500/'
		elif self.currentRcType == self.RCTYPE_GB:
			return '/usr/share/enigma2/rc_models/gb/'
		elif self.currentRcType == self.RCTYPE_INI0:
			return '/usr/share/enigma2/rc_models/ini0/'
		elif self.currentRcType == self.RCTYPE_INI1:
			return '/usr/share/enigma2/rc_models/ini1/'
		elif self.currentRcType == self.RCTYPE_INI2:
			return '/usr/share/enigma2/rc_models/ini2/'
		elif self.currentRcType == self.RCTYPE_INI3:
			return '/usr/share/enigma2/rc_models/ini3/'
		elif self.currentRcType == self.RCTYPE_INI4:
			return '/usr/share/enigma2/rc_models/ini4/'
		elif self.currentRcType == self.RCTYPE_IQON:
			return '/usr/share/enigma2/rc_models/iqon/'
		elif self.currentRcType == self.RCTYPE_ODINM7:
			return '/usr/share/enigma2/rc_models/odinm7/'
		elif self.currentRcType == self.RCTYPE_ODINM9:
			return '/usr/share/enigma2/rc_models/odinm9/'
		elif self.currentRcType == self.RCTYPE_TM:
			return '/usr/share/enigma2/rc_models/tm/'
		elif self.currentRcType == self.RCTYPE_VU:
			return '/usr/share/enigma2/rc_models/vu/'
		elif self.currentRcType == self.RCTYPE_VU2:
			return '/usr/share/enigma2/rc_models/vu2/'
		elif self.currentRcType == self.RCTYPE_VU3:
			return '/usr/share/enigma2/rc_models/vu3/'
		elif self.currentRcType == self.RCTYPE_XP1000:
			return '/usr/share/enigma2/rc_models/xp1000/'

rc_model = RcModel()
