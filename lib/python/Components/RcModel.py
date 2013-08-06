from enigma import getBoxType
from Tools.StbHardware import getFPVersion
import os

class RcModel:
	RCTYPE_AZBOXHD = 0
	RCTYPE_AZBOXELITE = 1
	RCTYPE_AZBOXME = 2
	RCTYPE_DMM = 3
	RCTYPE_DMM1 = 4
	RCTYPE_DMM2 = 5
	RCTYPE_E3HD = 6
	RCTYPE_EBOX5000 = 7
	RCTYPE_ET4X00 = 8
	RCTYPE_ET6X00 = 9
	RCTYPE_ET6500 = 10
	RCTYPE_ET9X00 = 11
	RCTYPE_ET9500 = 12
	RCTYPE_GB = 13
	RCTYPE_INI0 = 14
	RCTYPE_INI1 = 15
	RCTYPE_INI2 = 16
	RCTYPE_INI3 = 17
	RCTYPE_IQON = 18
	RCTYPE_IXUSSONE = 19
	RCTYPE_IXUSSZERO = 20
	RCTYPE_ODINM6 = 21	
	RCTYPE_ODINM7 = 22
	RCTYPE_ODINM9 = 23
	RCTYPE_TM = 24
	RCTYPE_VU = 25
	RCTYPE_VU2 = 26
	RCTYPE_XP1000 = 27


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
		if os.path.exists('/proc/stb/info/azmodel'):
			f = open("/proc/stb/info/model",'r')
			model = f.readline().strip()
			f.close()
			if model == "premium" or model == "premium+":
				self.currentRcType = self.RCTYPE_AZBOXHD
			elif model == "elite" or model == "ultra":
				self.currentRcType = self.RCTYPE_AZBOXELITE
			elif model == "me" or model == "minime":
				self.currentRcType = self.RCTYPE_AZBOXME
		elif os.path.exists('/proc/stb/info/hwmodel'):
			model = self.readFile('/proc/stb/info/hwmodel')
			if model == 'tmtwinoe' or model == 'tm2toe' or model == 'tmsingle' or model == 'tmnanooe':
				self.currentRcType = self.RCTYPE_TM
			elif model == 'ios100hd' or model == 'ios200hd' or model == 'ios300hd':
				self.currentRcType = self.RCTYPE_IQON
		elif getBoxType() == 'dm8000':
				self.currentRcType = self.RCTYPE_DMM
		elif getBoxType() == 'dm7020hd' or getBoxType() == 'dm7020hdv2' or getBoxType() == 'dm800sev2' or getBoxType() == 'dm500hdv2':
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
			elif model == 'ini-5000' or model == 'ini-7000' or model == 'ini-7012' or model== 'ini-9000':
				self.currentRcType = self.RCTYPE_INI1
			elif model == 'ini-1000' or model == 'ini-1000ru' or model == 'ini-5000ru' or model== 'ini-9000ru':
				self.currentRcType = self.RCTYPE_INI2
			elif model == 'ini-1000de' or model == 'ini-1000sv' or model == 'ini-5000sv':
				self.currentRcType = self.RCTYPE_INI3
			elif getBoxType() == 'odinm6':
				self.currentRcType = self.RCTYPE_ODINM6
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
		if self.currentRcType == self.RCTYPE_AZBOXHD:
			return '/usr/share/enigma2/rc_models/azboxhd/'
		elif self.currentRcType == self.RCTYPE_AZBOXELITE:
			return '/usr/share/enigma2/rc_models/azboxelite/'
		elif self.currentRcType == self.RCTYPE_AZBOXME:
			return '/usr/share/enigma2/rc_models/azboxme/'	
		elif self.currentRcType == self.RCTYPE_DMM:
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
		elif self.currentRcType == self.RCTYPE_IQON:
			return '/usr/share/enigma2/rc_models/iqon/'
		elif self.currentRcType == self.RCTYPE_IXUSSONE:
			return '/usr/share/enigma2/rc_models/ixussone/'
		elif self.currentRcType == self.RCTYPE_IXUSSZERO:
			return '/usr/share/enigma2/rc_models/ixusszero/'
		elif self.currentRcType == self.RCTYPE_ODINM6:
			return '/usr/share/enigma2/rc_models/odinm6/'
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
		elif self.currentRcType == self.RCTYPE_XP1000:
			return '/usr/share/enigma2/rc_models/xp1000/'

rc_model = RcModel()
