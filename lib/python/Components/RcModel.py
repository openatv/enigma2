from enigma import getBoxType
import os

class RcModel:
	RCTYPE_DMM = 0
	RCTYPE_ET9X00 = 1
	RCTYPE_ET6X00 = 2
	RCTYPE_ET9500 = 3
	RCTYPE_VU = 4
	RCTYPE_GB = 5
	RCTYPE_INI3000 = 6
	RCTYPE_INI5000 = 7
	RCTYPE_INI7000 = 8
	RCTYPE_ODINM9 = 9
	RCTYPE_TM = 10
	RCTYPE_ET6500 = 11
	RCTYPE_ET4000 = 12
	RCTYPE_XP1000 = 13
	RCTYPE_DMM1 = 14
	RCTYPE_DMM2 = 15
	RCTYPE_VU2 = 16
	RCTYPE_ICLASSM7 = 17
	RCTYPE_INI5000R = 18
	RCTYPE_INI1000 = 19
	RCTYPE_IXUSSONE = 20

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
		if os.path.exists('/proc/stb/info/hwmodel'):
			model = self.readFile('/proc/stb/info/hwmodel')
			if model == 'tmtwinoe' or model == 'tm2toe' or model == 'tmsingle':
				self.currentRcType = self.RCTYPE_TM
		elif os.path.exists('/proc/stb/info/vumodel'):
			model = self.readFile('/proc/stb/info/vumodel')
			if model == 'ultimo':
				self.currentRcType = self.RCTYPE_VU2
			else:
				self.currentRcType = self.RCTYPE_VU
		elif getBoxType() == 'dm8000':
				self.currentRcType = self.RCTYPE_DMM
		elif getBoxType() == 'dm7020hd':
				self.currentRcType = self.RCTYPE_DMM2
		elif getBoxType() == 'dm800' or getBoxType() == 'dm800se' or getBoxType() == 'dm500hd':
				self.currentRcType = self.RCTYPE_DMM1
		elif os.path.exists('/proc/stb/info/boxtype'):
			model = self.readFile('/proc/stb/info/boxtype')
			if model.startswith('et') or model.startswith('xp'):
				rc = self.readFile('/proc/stb/ir/rc/type')
				if rc == '3':
					self.currentRcType = self.RCTYPE_ODINM9
				if rc == '4':
					self.currentRcType = self.RCTYPE_DMM
				elif rc == '5':
					self.currentRcType = self.RCTYPE_ET9X00
				elif rc == '6':
					self.currentRcType = self.RCTYPE_DMM
				elif rc == '7':
					self.currentRcType = self.RCTYPE_ET6X00
				elif rc == '8':
					self.currentRcType = self.RCTYPE_VU
				elif rc == '9' and model == 'et9500':
					self.currentRcType = self.RCTYPE_ET9500
				elif rc == '9' and model == 'et6500':
					self.currentRcType = self.RCTYPE_ET6500
				elif rc == '11' and model == 'et9200':
					self.currentRcType = self.RCTYPE_ET9500
				elif rc == '11' and model == 'et9000':
					self.currentRcType = self.RCTYPE_ET9x00
				elif rc == '13' and model == 'et4000':
					self.currentRcType = self.RCTYPE_ET4000
				elif rc == '14':
					self.currentRcType = self.RCTYPE_XP1000
			elif model == 'gigablue':
				self.currentRcType = self.RCTYPE_GB
			elif model == 'ini-1000':
				self.currentRcType = self.RCTYPE_INI1000				
			elif model == 'ini-3000':
				self.currentRcType = self.RCTYPE_INI3000
			elif model == 'ini-5000':
				self.currentRcType = self.RCTYPE_INI5000
			elif model == 'ini-5000R':
				self.currentRcType = self.RCTYPE_INI5000R				
			elif model == 'ini-7000' or model == 'ini-7012':
				self.currentRcType = self.RCTYPE_INI7000
			elif model == 'odinm9':
				self.currentRcType = self.RCTYPE_ODINM9
			elif model == 'PlaySmartBox':
				self.currentRcType = self.RCTYPE_ICLASSM7
			elif model.startswith('Ixuss'):
				self.currentRcType = self.RCTYPE_IXUSSONE	


	def getRcLocation(self):
		if self.currentRcType == self.RCTYPE_DMM:
			return '/usr/share/enigma2/rc_models/dmm0/'
		elif self.currentRcType == self.RCTYPE_DMM1:
			return '/usr/share/enigma2/rc_models/dmm1/'
		elif self.currentRcType == self.RCTYPE_DMM2:
			return '/usr/share/enigma2/rc_models/dmm2/'
		elif self.currentRcType == self.RCTYPE_ET4000:
			return '/usr/share/enigma2/rc_models/et4000/'
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
		elif self.currentRcType == self.RCTYPE_INI1000:
			return '/usr/share/enigma2/rc_models/ini7000/'			
		elif self.currentRcType == self.RCTYPE_INI3000:
			return '/usr/share/enigma2/rc_models/ini3000/'
		elif self.currentRcType == self.RCTYPE_INI5000:
			return '/usr/share/enigma2/rc_models/ini5000/'
		elif self.currentRcType == self.RCTYPE_INI5000R:
			return '/usr/share/enigma2/rc_models/ini5000r/'			
		elif self.currentRcType == self.RCTYPE_INI7000:
			return '/usr/share/enigma2/rc_models/ini7000/'
		elif self.currentRcType == self.RCTYPE_ODINM9:
			return '/usr/share/enigma2/rc_models/odinm9/'
		elif self.currentRcType == self.RCTYPE_ICLASSM7:
			return '/usr/share/enigma2/rc_models/iclassm7/'
		elif self.currentRcType == self.RCTYPE_IXUSSONE:
			return '/usr/share/enigma2/rc_models/ixussone/'			
		elif self.currentRcType == self.RCTYPE_TM:
			return '/usr/share/enigma2/rc_models/tm/'
		elif self.currentRcType == self.RCTYPE_VU:
			return '/usr/share/enigma2/rc_models/vu/'
		elif self.currentRcType == self.RCTYPE_VU2:
			return '/usr/share/enigma2/rc_models/vu2/'
		elif self.currentRcType == self.RCTYPE_XP1000:
			return '/usr/share/enigma2/rc_models/xp1000/'
rc_model = RcModel()
