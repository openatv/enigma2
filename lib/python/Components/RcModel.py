from enigma import getBoxType
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
	RCTYPE_IQON = 15	
	RCTYPE_IXUSSONE = 16
	RCTYPE_IXUSSZERO = 17
	RCTYPE_ODINM7 = 18
	RCTYPE_ODINM9 = 19	
	RCTYPE_TM = 20
	RCTYPE_VU = 21	
	RCTYPE_VU2 = 22
	RCTYPE_XP1000 = 23


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
			if model == 'tmtwinoe' or model == 'tm2toe' or model == 'tmsingle' or model == 'tmnanooe':
				self.currentRcType = self.RCTYPE_TM
			elif model == 'ios100hd' or model == 'ios200hd' or model == 'ios300hd':
				self.currentRcType = self.RCTYPE_IQON
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
					self.currentRcType = self.RCTYPE_ET4X00
				elif rc == '14':
					self.currentRcType = self.RCTYPE_XP1000
			elif model == 'ebox5000' or model == 'ebox5100' or model == 'ebox7358':
				self.currentRcType = self.RCTYPE_EBOX5000					
			elif model == 'gigablue':
				self.currentRcType = self.RCTYPE_GB
			elif model == 'ini-3000':
				fp_version = str(getFPVersion())	
				if fp_version.startswith('1'):
					self.currentRcType = self.RCTYPE_INI0				
				else:
					self.currentRcType = self.RCTYPE_INI2
			elif model == 'ini-5000' or model == 'ini-7000' or model == 'ini-7012':
				self.currentRcType = self.RCTYPE_INI1
			elif model == 'ini-1000' or model == 'ini-5000R':
				self.currentRcType = self.RCTYPE_INI2
			elif model == 'ini-5000sv':
				self.currentRcType = self.RCTYPE_INI3			
			elif model == 'e3hd':
				self.currentRcType = self.RCTYPE_E3HD		
			elif model == 'odinm9':
				self.currentRcType = self.RCTYPE_ODINM9
			elif model == 'odinm7':
				self.currentRcType = self.RCTYPE_ODINM7
			elif model.startswith('Ixuss'):
				if getBoxType() == 'ixussone':
					self.currentRcType = self.RCTYPE_IXUSSONE
				elif getBoxType() == 'ixusszero':
					self.currentRcType = self.RCTYPE_IXUSSZERO
		elif os.path.exists('/proc/stb/info/vumodel'):
			model = self.readFile('/proc/stb/info/vumodel')
			if model == 'ultimo':
				self.currentRcType = self.RCTYPE_VU2
			else:
				self.currentRcType = self.RCTYPE_VU
		
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
		elif self.currentRcType == self.RCTYPE_INI2:
			return '/usr/share/enigma2/rc_models/ini3/'
		elif self.currentRcType == self.RCTYPE_IQON:
			return '/usr/share/enigma2/rc_models/iqon/'
		elif self.currentRcType == self.RCTYPE_IXUSSONE:
			return '/usr/share/enigma2/rc_models/ixussone/'
		elif self.currentRcType == self.RCTYPE_IXUSSZERO:
			return '/usr/share/enigma2/rc_models/ixusszero/'
		elif self.currentRcType == self.RCTYPE_ODINM9:
			return '/usr/share/enigma2/rc_models/odinm9/'
		elif self.currentRcType == self.RCTYPE_ODINM7:
			return '/usr/share/enigma2/rc_models/odinm7/'
		elif self.currentRcType == self.RCTYPE_TM:
			return '/usr/share/enigma2/rc_models/tm/'
		elif self.currentRcType == self.RCTYPE_VU:
			return '/usr/share/enigma2/rc_models/vu/'
		elif self.currentRcType == self.RCTYPE_VU2:
			return '/usr/share/enigma2/rc_models/vu2/'
		elif self.currentRcType == self.RCTYPE_XP1000:
			return '/usr/share/enigma2/rc_models/xp1000/'

rc_model = RcModel()
