from Screen import Screen
from ServiceScan import ServiceScan
from Components.config import config, ConfigSubsection, ConfigSelection, ConfigYesNo, ConfigInteger, getConfigListEntry, ConfigSlider, ConfigEnableDisable, integer_limits

from Components.ActionMap import NumberActionMap, ActionMap
from Components.ConfigList import ConfigListScreen
from Components.NimManager import nimmanager, getConfigSatlist
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Tools.HardwareInfo import HardwareInfo
from Screens.InfoBar import InfoBar
from Screens.MessageBox import MessageBox
from enigma import eTimer, eDVBFrontendParametersSatellite, eComponentScan, eDVBFrontendParametersTerrestrial, eDVBFrontendParametersCable, eDVBFrontendParametersATSC, eConsoleAppContainer, eDVBResourceManager, iDVBFrontend
from Components.Converter.ChannelNumbers import channelnumbers
from boxbranding import getMachineBrand

def buildTerTransponder(frequency,
		inversion=2, bandwidth = 7000000, fechigh = 6, feclow = 6,
		modulation = 2, transmission = 2, guard = 4,
		hierarchy = 4, system = 0, plp_id = 0):
#	print "freq", frequency, "inv", inversion, "bw", bandwidth, "fech", fechigh, "fecl", feclow, "mod", modulation, "tm", transmission, "guard", guard, "hierarchy", hierarchy
	parm = eDVBFrontendParametersTerrestrial()
	parm.frequency = frequency
	parm.inversion = inversion
	parm.bandwidth = bandwidth
	parm.code_rate_HP = fechigh
	parm.code_rate_LP = feclow
	parm.modulation = modulation
	parm.transmission_mode = transmission
	parm.guard_interval = guard
	parm.hierarchy = hierarchy
	parm.system = system
	parm.plp_id = plp_id
	return parm

def getInitialTransponderList(tlist, pos):
	list = nimmanager.getTransponders(pos)
	for x in list:
		if x[0] == 0:		#SAT
			parm = eDVBFrontendParametersSatellite()
			parm.frequency = x[1]
			parm.symbol_rate = x[2]
			parm.polarisation = x[3]
			parm.fec = x[4]
			parm.inversion = x[7]
			parm.orbital_position = pos
			parm.system = x[5]
			parm.modulation = x[6]
			parm.rolloff = x[8]
			parm.pilot = x[9]
			parm.is_id = x[10]
			parm.pls_mode = x[11]
			parm.pls_code = x[12]
			parm.t2mi_plp_id = x[13]
			tlist.append(parm)

def getInitialCableTransponderList(tlist, nim):
	list = nimmanager.getTranspondersCable(nim)
	for x in list:
		if x[0] == 1: #CABLE
			parm = eDVBFrontendParametersCable()
			parm.frequency = x[1]
			parm.symbol_rate = x[2]
			parm.modulation = x[3]
			parm.fec_inner = x[4]
			parm.inversion = x[5]
			parm.system = x[6]
			tlist.append(parm)

def getInitialTerrestrialTransponderList(tlist, region, skip_t2 = False):
	list = nimmanager.getTranspondersTerrestrial(region)

	#self.transponders[self.parsedTer].append((2,freq,bw,const,crh,crl,guard,transm,hierarchy,inv))

	#def buildTerTransponder(frequency, inversion = 2, bandwidth = 3, fechigh = 6, feclow = 6,
				#modulation = 2, transmission = 2, guard = 4, hierarchy = 4):

	for x in list:
		if x[0] == 2: #TERRESTRIAL
			if skip_t2 and x[10] == eDVBFrontendParametersTerrestrial.System_DVB_T2:
				# Should be searching on TerrestrialTransponderSearchSupport.
				continue
			parm = buildTerTransponder(x[1], x[9], x[2], x[4], x[5], x[3], x[7], x[6], x[8], x[10], x[11])
			tlist.append(parm)

def getInitialATSCTransponderList(tlist, nim):
	list = nimmanager.getTranspondersATSC(nim)
	for x in list:
		if x[0] == 3: #ATSC
			parm = eDVBFrontendParametersATSC()
			parm.frequency = x[1]
			parm.modulation = x[2]
			parm.inversion = x[3]
			parm.system = x[4]
			tlist.append(parm)

cable_bands = {
	"DVBC_BAND_EU_VHF_I" : 1 << 0,
	"DVBC_BAND_EU_MID" : 1 << 1,
	"DVBC_BAND_EU_VHF_III" : 1 << 2,
	"DVBC_BAND_EU_SUPER" : 1 << 3,
	"DVBC_BAND_EU_HYPER" : 1 << 4,
	"DVBC_BAND_EU_UHF_IV" : 1 << 5,
	"DVBC_BAND_EU_UHF_V" : 1 << 6,
	"DVBC_BAND_US_LO" : 1 << 7,
	"DVBC_BAND_US_MID" : 1 << 8,
	"DVBC_BAND_US_HI" : 1 << 9,
	"DVBC_BAND_US_SUPER" : 1 << 10,
	"DVBC_BAND_US_HYPER" : 1 << 11,
}

cable_autoscan_nimtype = {
'SSH108' : 'ssh108',
'TT3L10' : 'tt3l10',
'TURBO' : 'vuplus_turbo_c',
'TT2L08' : 'tt2l08',
'BCM3148' : 'bcm3148'
}

terrestrial_autoscan_nimtype = {
'SSH108' : 'ssh108_t2_scan',
'TT3L10' : 'tt3l10_t2_scan',
'TURBO' : 'vuplus_turbo_t',
'TT2L08' : 'tt2l08_t2_scan',
'BCM3466' : 'bcm3466'
}

dual_tuner_list = ('TT3L10', 'BCM3466')

def GetDeviceId(filter, nim_idx):
	tuners={}
	device_id = 0
	socket_id = 0
	for nim in nimmanager.nim_slots:
		name_token = nim.description.split(' ')
		name = name_token[-1][4:-1]
		if name == filter:
			if socket_id == nim_idx:
				break

			if device_id:	device_id = 0
			else:			device_id = 1
		socket_id += 1
	return device_id

def GetTerrestrial5VEnable(nim_idx):
       nim = nimmanager.nim_slots[nim_idx]
       return int(nim.config.dvbt.terrestrial_5V.value)

class CableTransponderSearchSupport:
#	def setCableTransponderSearchResult(self, tlist):
#		pass

#	def cableTransponderSearchFinished(self):
#		pass

	def __init__(self):
		pass

	def tryGetRawFrontend(self, feid, delsys = None):
		res_mgr = eDVBResourceManager.getInstance()
		if res_mgr:
			raw_channel = res_mgr.allocateRawChannel(self.feid)
			if raw_channel:
				frontend = raw_channel.getFrontend()
				if frontend:
					if delsys == 'DVB-C':
						frontend.changeType(iDVBFrontend.feCable)
					elif delsys in ('DVB-T','DVB-T2'):
						frontend.changeType(iDVBFrontend.feTerrestrial)
					elif delsys in ('DVB-S','DVB-S2'):
						frontend.changeType(iDVBFrontend.feSatellite)
					elif delsys == 'ATSC':
						frontend.changeType(iDVBFrontend.feATSC)
					frontend.closeFrontend() # immediate close...
					del frontend
					del raw_channel
					return True
		return False

	def cableTransponderSearchSessionClosed(self, *val):
		print "cableTransponderSearchSessionClosed, val", val
		self.cable_search_container.appClosed.remove(self.cableTransponderSearchClosed)
		self.cable_search_container.dataAvail.remove(self.getCableTransponderData)
		if val and len(val):
			if val[0]:
				self.setCableTransponderSearchResult(self.__tlist)
			else:
				self.cable_search_container.sendCtrlC()
				self.setCableTransponderSearchResult(None)
		self.cable_search_container = None
		self.cable_search_session = None
		self.__tlist = None
		self.cableTransponderSearchFinished()

	def cableTransponderSearchClosed(self, retval):
		print "cableTransponderSearch finished", retval
		self.cable_search_session.close(True)

	def getCableTransponderData(self, str):
		#prepend any remaining data from the previous call
		str = self.remainingdata + str
		#split in lines
		lines = str.split('\n')
		#'str' should end with '\n', so when splitting, the last line should be empty. If this is not the case, we received an incomplete line
		if len(lines[-1]):
			#remember this data for next time
			self.remainingdata = lines[-1]
			lines = lines[0:-1]
		else:
			self.remainingdata = ""

		for line in lines:
			data = line.split()
			if len(data):
				if data[0] == 'OK':
					print str
					parm = eDVBFrontendParametersCable()
					qam = { "QAM16" : parm.Modulation_QAM16,
						"QAM32" : parm.Modulation_QAM32,
						"QAM64" : parm.Modulation_QAM64,
						"QAM128" : parm.Modulation_QAM128,
						"QAM256" : parm.Modulation_QAM256,
						"QAM_AUTO" : parm.Modulation_Auto }
					inv = { "INVERSION_OFF" : parm.Inversion_Off,
						"INVERSION_ON" : parm.Inversion_On,
						"INVERSION_AUTO" : parm.Inversion_Unknown }
					fec = { "FEC_AUTO" : parm.FEC_Auto,
						"FEC_1_2" : parm.FEC_1_2,
						"FEC_2_3" : parm.FEC_2_3,
						"FEC_3_4" : parm.FEC_3_4,
						"FEC_5_6" : parm.FEC_5_6,
						"FEC_7_8" : parm.FEC_7_8,
						"FEC_8_9" : parm.FEC_8_9,
						"FEC_3_5" : parm.FEC_3_5,
						"FEC_4_5" : parm.FEC_4_5,
						"FEC_9_10" : parm.FEC_9_10,
						"FEC_NONE" : parm.FEC_None }
					parm.frequency = int(data[1])
					parm.symbol_rate = int(data[2])
					parm.fec_inner = fec[data[3]]
					parm.modulation = qam[data[4]]
					parm.inversion = inv[data[5]]
					self.__tlist.append(parm)
				tmpstr = _("Try to find used transponders in cable network.. please wait...")
				tmpstr += "\n\n"
				tmpstr += data[1].isdigit() and "%s MHz " % (int(data[1]) / 1000.) or data[1]
				tmpstr += data[0]
				self.cable_search_session["text"].setText(tmpstr)

	def startCableTransponderSearch(self, nim_idx):
		def GetCommand(nim_idx):
			global cable_autoscan_nimtype
			try:
				nim_name = nimmanager.getNimName(nim_idx)
				if nim_name is not None and nim_name != "":
					device_id = ""
					nim_name = nim_name.split(' ')[-1][4:-1]
					if nim_name == 'TT3L10':
						try:
							device_id = GetDeviceId('TT3L10', nim_idx)
							device_id = "--device=%s" % (device_id)
						except Exception, err:
							print "GetCommand ->", err
							device_id = "--device=0"
#						print nim_idx, nim_name, cable_autoscan_nimtype[nim_name], device_id
					command = "%s %s" % (cable_autoscan_nimtype[nim_name], device_id)
					return command
			except Exception, err:
				print "GetCommand ->", err
			return "tda1002x"

		if not self.tryGetRawFrontend(nim_idx, "DVB-C"):
			self.session.nav.stopService()
			if not self.tryGetRawFrontend(nim_idx, "DVB-C"):
				if self.session.pipshown:
					self.session.infobar.showPiP()
				if not self.tryGetRawFrontend(nim_idx, "DVB-C"):
					self.cableTransponderSearchFinished()
					return
		self.__tlist = [ ]
		self.remainingdata = ""
		self.cable_search_container = eConsoleAppContainer()
		self.cable_search_container.appClosed.append(self.cableTransponderSearchClosed)
		self.cable_search_container.dataAvail.append(self.getCableTransponderData)
		cableConfig = config.Nims[nim_idx].dvbc
		tunername = nimmanager.getNimName(nim_idx)
		try:
			bus = nimmanager.getI2CDevice(nim_idx)
			if bus is None:
				print "ERROR: could not get I2C device for nim", nim_idx, "for cable transponder search"
				bus = 2
		except:
			# older API
			if nim_idx < 2:
				if HardwareInfo().get_device_name() == "dm500hd":
					bus = 2
				else:
					bus = nim_idx
			else:
				if nim_idx == 2:
					bus = 2 # DM8000 first nim is /dev/i2c/2
				else:
					bus = 4 # DM8000 second num is /dev/i2c/4

		bin_name = None
		if tunername == "CXD1981":
			bin_name = "CXD1981"
			cmd = "cxd1978 --init --scan --verbose --wakeup --inv 2 --bus %d" % bus
		elif tunername == "ATBM781x":
			bin_name = "ATBM781x"
			cmd = "atbm781x --init --scan --verbose --wakeup --inv 2 --bus %d" % bus
		elif tunername.startswith("Sundtek"):
			bin_name = "mediaclient"
			cmd = "/opt/bin/mediaclient --blindscan %d" % nim_idx
		else:
			bin_name = GetCommand(nim_idx)
			cmd = "%(BIN_NAME)s --init --scan --verbose --wakeup --inv 2 --bus %(BUS)d" % {'BIN_NAME':bin_name, 'BUS':bus}

		if cableConfig.scan_type.value == "bands":
			cmd += " --scan-bands "
			bands = 0
			if cableConfig.scan_band_EU_VHF_I.value:
				bands |= cable_bands["DVBC_BAND_EU_VHF_I"]
			if cableConfig.scan_band_EU_MID.value:
				bands |= cable_bands["DVBC_BAND_EU_MID"]
			if cableConfig.scan_band_EU_VHF_III.value:
				bands |= cable_bands["DVBC_BAND_EU_VHF_III"]
			if cableConfig.scan_band_EU_UHF_IV.value:
				bands |= cable_bands["DVBC_BAND_EU_UHF_IV"]
			if cableConfig.scan_band_EU_UHF_V.value:
				bands |= cable_bands["DVBC_BAND_EU_UHF_V"]
			if cableConfig.scan_band_EU_SUPER.value:
				bands |= cable_bands["DVBC_BAND_EU_SUPER"]
			if cableConfig.scan_band_EU_HYPER.value:
				bands |= cable_bands["DVBC_BAND_EU_HYPER"]
			if cableConfig.scan_band_US_LOW.value:
				bands |= cable_bands["DVBC_BAND_US_LO"]
			if cableConfig.scan_band_US_MID.value:
				bands |= cable_bands["DVBC_BAND_US_MID"]
			if cableConfig.scan_band_US_HIGH.value:
				bands |= cable_bands["DVBC_BAND_US_HI"]
			if cableConfig.scan_band_US_SUPER.value:
				bands |= cable_bands["DVBC_BAND_US_SUPER"]
			if cableConfig.scan_band_US_HYPER.value:
				bands |= cable_bands["DVBC_BAND_US_HYPER"]
			cmd += str(bands)
		else:
			cmd += " --scan-stepsize "
			cmd += str(cableConfig.scan_frequency_steps.value)
		if cmd.startswith("atbm781x"):
			cmd += " --timeout 800"
		else:
			if cableConfig.scan_mod_qam16.value:
				cmd += " --mod 16"
			if cableConfig.scan_mod_qam32.value:
				cmd += " --mod 32"
			if cableConfig.scan_mod_qam64.value:
				cmd += " --mod 64"
			if cableConfig.scan_mod_qam128.value:
				cmd += " --mod 128"
			if cableConfig.scan_mod_qam256.value:
				cmd += " --mod 256"
			if cableConfig.scan_sr_6900.value:
				cmd += " --sr 6900000"
			if cableConfig.scan_sr_6875.value:
				cmd += " --sr 6875000"
			if cableConfig.scan_sr_ext1.value > 450:
				cmd += " --sr "
				cmd += str(cableConfig.scan_sr_ext1.value)
				cmd += "000"
			if cableConfig.scan_sr_ext2.value > 450:
				cmd += " --sr "
				cmd += str(cableConfig.scan_sr_ext2.value)
				cmd += "000"
		print bin_name, " CMD is", cmd

		self.cable_search_container.execute(cmd)
		tmpstr = _("Try to find used transponders in cable network.. please wait...")
		tmpstr += "\n\n..."
		self.cable_search_session = self.session.openWithCallback(self.cableTransponderSearchSessionClosed, MessageBox, tmpstr, MessageBox.TYPE_INFO)

class TerrestrialTransponderSearchSupport:
#	def setTerrestrialTransponderSearchResult(self, tlist):
#		pass

#	def terrestrialTransponderSearchFinished(self):
#		pass

	def terrestrialTransponderSearchSessionClosed(self, *val):
		print "TerrestrialTransponderSearchSessionClosed, val", val
		self.terrestrial_search_container.appClosed.remove(self.terrestrialTransponderSearchClosed)
		self.terrestrial_search_container.dataAvail.remove(self.getTerrestrialTransponderData)
		if val and len(val):
			if val[0]:
				self.setTerrestrialTransponderSearchResult(self.__tlist)
			else:
				self.terrestrial_search_container.sendCtrlC()
				self.setTerrestrialTransponderSearchResult(None)
		self.terrestrial_search_container = None
		self.terrestrial_search_session = None
		self.__tlist = None
		self.terrestrialTransponderSearchFinished()

	def terrestrialTransponderSearchClosed(self, retval):
		self.setTerrestrialTransponderData()
		opt = self.terrestrialTransponderGetOpt()
		if opt is None:
			print "terrestrialTransponderSearch finished", retval
			self.terrestrial_search_session.close(True)
		else:
			(freq, bandWidth) = opt
			self.terrestrialTransponderSearch(freq, bandWidth)

	def getTerrestrialTransponderData(self, str):
		self.terrestrial_search_data += str

	def setTerrestrialTransponderData(self):
		print self.terrestrial_search_data
		data = self.terrestrial_search_data.split()
		if len(data):
#			print "[setTerrestrialTransponderData] data : ", data
			if data[0] == 'OK':
				# DVB-T : OK frequency bandwidth delivery system -1
				# DVB-T2 : OK frequency bandwidth delivery system number_of_plp plp_id0:plp_type0
				if data[3] == 1: # DVB-T
					parm = eDVBFrontendParametersTerrestrial()
					parm.frequency = int(data[1])
					parm.bandwidth = int(data[2])
					parm.inversion = parm.Inversion_Unknown
					parm.code_rate_HP = parm.FEC_Auto
					parm.code_rate_LP = parm.FEC_Auto
					parm.modulation = parm.Modulation_Auto
					parm.transmission_mode = parm.TransmissionMode_Auto
					parm.guard_interval = parm.GuardInterval_Auto
					parm.hierarchy = parm.Hierarchy_Auto
					parm.system = parm.System_DVB_T
					parm.plp_id = 0
					self.__tlist.append(parm)
				else:
					plp_list = data[5:]
					plp_num = int(data[4])
					if len(plp_list) > plp_num:
						plp_list = plp_list[:plp_num]
					for plp in plp_list:
						(plp_id, plp_type) = plp.split(':')
						if plp_type == '0': # common PLP:
							continue
						parm = eDVBFrontendParametersTerrestrial()
						parm.frequency = int(data[1])
						parm.bandwidth = self.terrestrialTransponderconvBandwidth_P(int(data[2]))
						parm.inversion = parm.Inversion_Unknown
						parm.code_rate_HP = parm.FEC_Auto
						parm.code_rate_LP = parm.FEC_Auto
						parm.modulation = parm.Modulation_Auto
						parm.transmission_mode = parm.TransmissionMode_Auto
						parm.guard_interval = parm.GuardInterval_Auto
						parm.hierarchy = parm.Hierarchy_Auto
						parm.system = parm.System_DVB_T2
						parm.plp_id = int(plp_id)
						self.__tlist.append(parm)

			tmpstr = _("Try to find used transponders in terrestrial network.. please wait...")
			tmpstr += "\n\n"
			tmpstr += data[1][:-3]
			tmpstr += " kHz "
			tmpstr += data[0]
			self.terrestrial_search_session["text"].setText(tmpstr)

	def terrestrialTransponderInitSearchList(self, searchList, region):
		tpList = nimmanager.getTranspondersTerrestrial(region)
		for x in tpList:
			if x[0] == 2: #TERRESTRIAL
				freq = x[1] # frequency
				bandWidth = self.terrestrialTransponderConvBandwidth_I(x[2]) # bandWidth
				parm = (freq, bandWidth)
				searchList.append(parm)

	def terrestrialTransponderConvBandwidth_I(self, _bandWidth):
		bandWidth = {
			eDVBFrontendParametersTerrestrial.Bandwidth_8MHz : 8000000,
			eDVBFrontendParametersTerrestrial.Bandwidth_7MHz : 7000000,
			eDVBFrontendParametersTerrestrial.Bandwidth_6MHz : 6000000,
			eDVBFrontendParametersTerrestrial.Bandwidth_5MHz : 5000000,
			eDVBFrontendParametersTerrestrial.Bandwidth_1_712MHz : 1712000,
			eDVBFrontendParametersTerrestrial.Bandwidth_10MHz : 10000000,
		}.get(_bandWidth, 8000000)
		return bandWidth

	def terrestrialTransponderconvBandwidth_P(self, _bandWidth):
		bandWidth = {
			8000000 : eDVBFrontendParametersTerrestrial.Bandwidth_8MHz,
			7000000 : eDVBFrontendParametersTerrestrial.Bandwidth_7MHz,
			6000000 : eDVBFrontendParametersTerrestrial.Bandwidth_6MHz,
			5000000 : eDVBFrontendParametersTerrestrial.Bandwidth_5MHz,
			1712000 : eDVBFrontendParametersTerrestrial.Bandwidth_1_712MHz,
			10000000 : eDVBFrontendParametersTerrestrial.Bandwidth_10MHz,
		}.get(_bandWidth, eDVBFrontendParametersTerrestrial.Bandwidth_8MHz)
		return bandWidth

	def terrestrialTransponderGetOpt(self):
		if len(self.terrestrial_search_list) > 0:
			return self.terrestrial_search_list.pop(0)
		else:
			return None

	def terrestrialTransponderGetCmd(self, nim_idx):
		global terrestrial_autoscan_nimtype
		try:
			nim_name = nimmanager.getNimName(nim_idx)
			if nim_name is not None and nim_name != "":
				device_id = ""
				nim_name = nim_name.split(' ')[-1][4:-1]
				if nim_name in dual_tuner_list:
					try:
						device_id = GetDeviceId(nim_name, nim_idx)
						device_id = "--device %s" % (device_id)
					except Exception, err:
						print "terrestrialTransponderGetCmd ->", err
						device_id = "--device 0"
#					print nim_idx, nim_name, terrestrial_autoscan_nimtype[nim_name], device_id
				command = "%s %s" % (terrestrial_autoscan_nimtype[nim_name], device_id)
				return command
		except Exception, err:
			print "terrestrialTransponderGetCmd ->", err
		return ""

	def startTerrestrialTransponderSearch(self, nim_idx, region):
		if not self.tryGetRawFrontend(nim_idx, "DVB-T"):
			self.session.nav.stopService()
			if not self.tryGetRawFrontend(nim_idx, "DVB-T"):
				if self.session.pipshown: # try to disable pip
					self.session.pipshown = False
					del self.session.pip
				if not self.tryGetRawFrontend(nim_idx, "DVB-T"):
					self.terrestrialTransponderSearchFinished()
					return
		self.__tlist = [ ]
		self.terrestrial_search_container = eConsoleAppContainer()
		self.terrestrial_search_container.appClosed.append(self.terrestrialTransponderSearchClosed)
		self.terrestrial_search_container.dataAvail.append(self.getTerrestrialTransponderData)

		self.terrestrial_search_binName = self.terrestrialTransponderGetCmd(nim_idx)

		self.terrestrial_search_bus = nimmanager.getI2CDevice(nim_idx)
		if self.terrestrial_search_bus is None:
#			print "ERROR: could not get I2C device for nim", nim_idx, "for terrestrial transponder search"
			self.terrestrial_search_bus = 2

		self.terrestrial_search_feid = nim_idx
		self.terrestrial_search_enable_5v = GetTerrestrial5VEnable(nim_idx)

		self.terrestrial_search_list = []
		self.terrestrialTransponderInitSearchList(self.terrestrial_search_list ,region)
		(freq, bandWidth) = self.terrestrialTransponderGetOpt()
		self.terrestrialTransponderSearch(freq, bandWidth)

		tmpstr = _("Try to find used transponders in terrestrial network.. please wait...")
		tmpstr += "\n\n..."
		self.terrestrial_search_session = self.session.openWithCallback(self.terrestrialTransponderSearchSessionClosed, MessageBox, tmpstr, MessageBox.TYPE_INFO)

	def terrestrialTransponderSearch(self, freq, bandWidth):
		self.terrestrial_search_data = ""
		cmd = "%s --freq %d --bw %d --bus %d --ds 2" % (self.terrestrial_search_binName, freq, bandWidth, self.terrestrial_search_bus)
		if self.terrestrial_search_enable_5v:
			cmd += " --feid %d --5v %d" % (self.terrestrial_search_feid, self.terrestrial_search_enable_5v)
		print "SCAN CMD : ",cmd
		self.terrestrial_search_container.execute(cmd)

class ConfigFrequency(ConfigInteger):
	def __init__(self, default, limits = integer_limits):
		self._value = None
		ConfigInteger.__init__(self, default, limits)

	def setValue(self, value):
		if self._value != [value]:
			self._value = [value]
			self.changed()

	value = property(ConfigInteger.getValue, setValue)

class ConfigChannel(ConfigInteger):
	def __init__(self, default, limits = integer_limits):
		self._value = None
		ConfigInteger.__init__(self, default, limits)

	def setValue(self, value):
		if self._value != [value]:
			self._value = [value]
			self.changed()

	value = property(ConfigInteger.getValue, setValue)

class ScanSetup(ConfigListScreen, Screen, CableTransponderSearchSupport, TerrestrialTransponderSearchSupport):
	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Manual Scan"))

		self.finished_cb = None

		self.ter_channel_input = False
		self.ter_tnumber = None

		self.tunerEntry = None
		self.typeOfScanEntry = None
		self.typeOfInputEntry = None
		self.systemEntry = None
		self.modulationEntry = None
		self.preDefSatList = None
		self.TerrestrialTransponders = ConfigSelection(choices = [])

		self.TerrestrialRegionEntry = None
		self.TerrestrialRegion = None
		self.multiType = None
		self.preDefTransponders = ConfigSelection(choices = [])

		self.CableTransponders  = ConfigSelection(choices = [])
		self.ATSCTransponders  = ConfigSelection(choices = [])
		self.createConfig()

		self.session.postScanService = session.nav.getCurrentlyPlayingServiceOrGroup()

		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Scan"))

		self["actions"] = NumberActionMap(["SetupActions", "MenuActions", "ColorActions"],
		{
			"ok": self.keyGo,
			"save": self.keyGo,
			"cancel": self.keyCancel,
			"red": self.keyCancel,
			"green": self.keyGo,
			"menu": self.doCloseRecursive,
		}, -2)

		self.statusTimer = eTimer()
		self.statusTimer.callback.append(self.updateStatus)
		#self.statusTimer.start(5000, True)

		self.list = []
		ConfigListScreen.__init__(self, self.list)
		self["header"] = Label(_("Manual Scan"))
		if not self.scan_nims.value == "":
			self.createSetup()
			self["introduction"] = Label(_("Press OK to start the scan"))
		else:
			self["introduction"] = Label(_("Nothing to scan!\nPlease setup your tuner settings before you start a service scan."))

	def runAsync(self, finished_cb):
		self.finished_cb = finished_cb
		self.keyGo()

	def updateSatList(self):
		self.satList = []
		for slot in nimmanager.nim_slots:
			if slot.canBeCompatible("DVB-S"):
				self.satList.append(nimmanager.getSatListForNim(slot.slot))
			else:
				self.satList.append(None)

	def TunerTypeChanged(self):
		fe_id = int(self.scan_nims.value)
		multiType = config.Nims[fe_id].multiType
		slot = nimmanager.nim_slots[fe_id]
		print "dvb_api_version ",iDVBFrontend.dvb_api_version
		if eDVBResourceManager.getInstance().allocateRawChannel(fe_id) is None:
			self.session.nav.stopService()
			if eDVBResourceManager.getInstance().allocateRawChannel(fe_id) is None:
				print "type change failed"
				return
		frontend = eDVBResourceManager.getInstance().allocateRawChannel(fe_id).getFrontend()

		if slot.isMultiType():
			eDVBResourceManager.getInstance().setFrontendType(slot.frontend_id, "dummy", False) #to force a clear of m_delsys_whitelist
			types = slot.getMultiTypeList()
			for FeType in types.itervalues():
				if FeType in ("DVB-S", "DVB-S2", "DVB-S2X") and config.Nims[slot.slot].dvbs.configMode.value == "nothing":
					continue
				elif FeType in ("DVB-T", "DVB-T2") and config.Nims[slot.slot].dvbt.configMode.value == "nothing":
					continue
				elif FeType in ("DVB-C", "DVB-C2") and config.Nims[slot.slot].dvbc.configMode.value == "nothing":
					continue
				elif FeType in ("ATSC") and config.Nims[slot.slot].atsc.configMode.value == "nothing":
					continue
				eDVBResourceManager.getInstance().setFrontendType(slot.frontend_id, FeType, True)
		else:
			eDVBResourceManager.getInstance().setFrontendType(slot.frontend_id, slot.getType())

		system = multiType.getText()
#			if not path.exists("/proc/stb/frontend/%d/mode" % fe_id) and iDVBFrontend.dvb_api_version >= 5:
		print "api >=5 and new style tuner driver"
		if frontend:
			if system == 'DVB-C':
				ret = frontend.changeType(iDVBFrontend.feCable)
			elif system in ('DVB-T','DVB-T2'):
				ret = frontend.changeType(iDVBFrontend.feTerrestrial)
			elif system in ('DVB-S','DVB-S2'):
				ret = frontend.changeType(iDVBFrontend.feSatellite)
			elif system == 'ATSC':
				ret = frontend.changeType(iDVBFrontend.feATSC)
			else:
				ret = False
			if not ret:
				print "%d: tunerTypeChange to '%s' failed" %(fe_id, system)
			else:
				print "new system ",system
		else:
			print "%d: tunerTypeChange to '%s' failed (BUSY)" %(fe_id, multiType.getText())
#		self.createConfig()
		self.createSetup()

	def createSetup(self):
		self.list = []
		self.multiscanlist = []
		index_to_scan = int(self.scan_nims.value)
		print "ID: ", index_to_scan

		self.tunerEntry = getConfigListEntry(_("Tuner"), self.scan_nims)
		self.list.append(self.tunerEntry)

		if self.scan_nims == [ ]:
			return

		self.typeOfScanEntry = None
		self.typeOfInputEntry = None
		self.systemEntry = None
		self.modulationEntry = None
		self.preDefSatList = None
		self.TerrestrialRegionEntry = None
		self.multiType = None
		self.t2mi_Entry = None
		nim = nimmanager.nim_slots[index_to_scan]

		if nim.isMultiType():
			multiType = config.Nims[index_to_scan].multiType
			choices = "("
			for x in multiType.choices.choices:
				choices += x[1]
				choices += ", "
			choices = choices[:-2] + ")"
			self.multiType = getConfigListEntry(_("Tuner type %s")%(choices), multiType)
			self.list.append(self.multiType)

		if nim.isCompatible("DVB-S") and nim.config.dvbs.configMode.value == "nothing":
			self.setConfigList()
			return
		elif nim.isCompatible("DVB-C") and nim.config.dvbc.configMode.value == "nothing":
			self.setConfigList()
			return
		elif nim.isCompatible("DVB-T") and nim.config.dvbt.configMode.value == "nothing":
			self.setConfigList()
			return
		elif nim.isCompatible("ATSC") and nim.config.atsc.configMode.value == "nothing":
			self.setConfigList()
			return

		if nim.isCompatible("DVB-S"):
			self.typeOfScanEntry = getConfigListEntry(_("Type of scan"), self.scan_type)
			self.list.append(self.typeOfScanEntry)
		elif nim.isCompatible("DVB-C"):
			if config.Nims[index_to_scan].dvbc.scan_type.value != "provider": # only show predefined transponder if in provider mode
				if self.scan_typecable.value == "predefined_transponder":
					self.scan_typecable.value = self.cable_toggle[self.last_scan_typecable]
			self.last_scan_typecable = self.scan_typecable.value
			self.typeOfScanEntry = getConfigListEntry(_("Type of scan"), self.scan_typecable)
			self.list.append(self.typeOfScanEntry)
		elif nim.isCompatible("DVB-T"):
			self.typeOfScanEntry = getConfigListEntry(_("Type of scan"), self.scan_typeterrestrial)
			self.list.append(self.typeOfScanEntry)
			if self.scan_typeterrestrial.value == "single_transponder":
				self.typeOfInputEntry = getConfigListEntry(_("Use frequency or channel"), self.scan_input_as)
				if self.ter_channel_input:
					self.list.append(self.typeOfInputEntry)
				else:
					self.scan_input_as.value = self.scan_input_as.choices[0]
		elif nim.isCompatible("ATSC"):
			self.typeOfScanEntry = getConfigListEntry(_("Type of scan"), self.scan_typeatsc)
			self.list.append(self.typeOfScanEntry)

		self.scan_networkScan.value = False
		if nim.isCompatible("DVB-S"):
			if self.scan_type.value == "single_transponder":
				self.updateSatList()
				if nim.isCompatible("DVB-S2"):
					self.systemEntry = getConfigListEntry(_('System'), self.scan_sat.system)
					self.list.append(self.systemEntry)
				else:
					# downgrade to dvb-s, in case a -s2 config was active
					self.scan_sat.system.value = eDVBFrontendParametersSatellite.System_DVB_S
				self.list.append(getConfigListEntry(_('Satellite'), self.scan_satselection[index_to_scan]))
				self.list.append(getConfigListEntry(_('Frequency'), self.scan_sat.frequency))
				self.list.append(getConfigListEntry(_('Inversion'), self.scan_sat.inversion))
				self.list.append(getConfigListEntry(_('Symbol rate'), self.scan_sat.symbolrate))
				self.list.append(getConfigListEntry(_('Polarization'), self.scan_sat.polarization))
				if self.scan_sat.system.value == eDVBFrontendParametersSatellite.System_DVB_S:
					self.list.append(getConfigListEntry(_("FEC"), self.scan_sat.fec))
				elif self.scan_sat.system.value == eDVBFrontendParametersSatellite.System_DVB_S2:
					self.list.append(getConfigListEntry(_("FEC"), self.scan_sat.fec_s2))
					self.modulationEntry = getConfigListEntry(_('Modulation'), self.scan_sat.modulation)
					self.list.append(self.modulationEntry)
					self.list.append(getConfigListEntry(_('Roll-off'), self.scan_sat.rolloff))
					self.list.append(getConfigListEntry(_('Pilot'), self.scan_sat.pilot))
					if nim.isMultistream():
						self.list.append(getConfigListEntry(_('Input Stream ID'), self.scan_sat.is_id))
						self.list.append(getConfigListEntry(_('PLS Mode'), self.scan_sat.pls_mode))
						self.list.append(getConfigListEntry(_('PLS Code'), self.scan_sat.pls_code))
					self.t2mi_Entry = getConfigListEntry(_('T2MI'), self.scan_sat.t2mi)
					self.list.append(self.t2mi_Entry)
					if self.scan_sat.t2mi.value == "on":
						self.list.append(getConfigListEntry( _('T2MI PID'), self.scan_sat.t2mi_pid))
						self.list.append(getConfigListEntry( _('T2MI PLP ID'), self.scan_sat.t2mi_plp))
			elif self.scan_type.value == "predefined_transponder" and self.satList[index_to_scan]:
				self.updateSatList()
				self.preDefSatList = getConfigListEntry(_('Satellite'), self.scan_satselection[index_to_scan])
				self.list.append(self.preDefSatList)
				sat = self.satList[index_to_scan][self.scan_satselection[index_to_scan].index]
				self.predefinedTranspondersList(sat[0])
				self.list.append(getConfigListEntry(_('Transponder'), self.preDefTransponders))

			elif self.scan_type.value == "single_satellite":
				self.updateSatList()
				print self.scan_satselection[index_to_scan]
				self.list.append(getConfigListEntry(_("Satellite"), self.scan_satselection[index_to_scan]))
				self.scan_networkScan.value = True
			elif "multisat" in self.scan_type.value:
				tlist = []
				SatList = nimmanager.getSatListForNim(index_to_scan)
				for x in SatList:
					if self.Satexists(tlist, x[0]) == 0:
						tlist.append(x[0])
						sat = ConfigEnableDisable(default = "_yes" in self.scan_type.value and True or False)
						configEntry = getConfigListEntry(nimmanager.getSatDescription(x[0]), sat)
						self.list.append(configEntry)
						self.multiscanlist.append((x[0], sat))
				self.scan_networkScan.value = True
		elif nim.isCompatible("DVB-C"):
			if self.scan_typecable.value == "single_transponder":
				self.list.append(getConfigListEntry(_("Frequency"), self.scan_cab.frequency))
				self.list.append(getConfigListEntry(_("Inversion"), self.scan_cab.inversion))
				self.list.append(getConfigListEntry(_("Symbol rate"), self.scan_cab.symbolrate))
				self.list.append(getConfigListEntry(_("Modulation"), self.scan_cab.modulation))
				self.list.append(getConfigListEntry(_("FEC"), self.scan_cab.fec))
			elif self.scan_typecable.value == "predefined_transponder":
				self.predefinedCabTranspondersList()
				self.list.append(getConfigListEntry(_('Transponder'), self.CableTransponders))
				self.CableTransponders.value = self.CableTransponders.value
			if config.Nims[index_to_scan].dvbc.scan_networkid.value:
				self.networkid = config.Nims[index_to_scan].dvbc.scan_networkid.value
				self.scan_networkScan.value = True
		elif nim.isCompatible("DVB-T"):
			if self.scan_typeterrestrial.value == "single_transponder":
				if nim.isCompatible("DVB-T2"):
					self.systemEntry = getConfigListEntry(_('System'), self.scan_ter.system)
					self.list.append(self.systemEntry)
				else:
					self.scan_ter.system.value = eDVBFrontendParametersTerrestrial.System_DVB_T
				if self.ter_channel_input and self.scan_input_as.value == "channel":
					self.scan_ter.frequency.value = channelnumbers.channel2frequency(self.scan_ter.channel.value, self.ter_tnumber)/1000
					self.list.append(getConfigListEntry(_("Channel"), self.scan_ter.channel))
				else:
					channel = channelnumbers.getChannelNumber(self.scan_ter.frequency.value*1000, self.ter_tnumber)
					if channel:
						self.scan_ter.channel.value = int(channel.replace("+","").replace("-",""))
					self.list.append(getConfigListEntry(_("Frequency"), self.scan_ter.frequency))
				self.list.append(getConfigListEntry(_("Inversion"), self.scan_ter.inversion))
				self.list.append(getConfigListEntry(_("Bandwidth"), self.scan_ter.bandwidth))
				self.list.append(getConfigListEntry(_("Code rate HP"), self.scan_ter.fechigh))
				self.list.append(getConfigListEntry(_("Code rate LP"), self.scan_ter.feclow))
				self.list.append(getConfigListEntry(_("Modulation"), self.scan_ter.modulation))
				self.list.append(getConfigListEntry(_("Transmission mode"), self.scan_ter.transmission))
				self.list.append(getConfigListEntry(_("Guard interval"), self.scan_ter.guard))
				self.list.append(getConfigListEntry(_("Hierarchy info"), self.scan_ter.hierarchy))
				if self.scan_ter.system.value == eDVBFrontendParametersTerrestrial.System_DVB_T2:
					self.list.append(getConfigListEntry(_('PLP ID'), self.scan_ter.plp_id))
			elif self.scan_typeterrestrial.value == "predefined_transponder":
				self.TerrestrialRegion = self.terrestrial_nims_regions[index_to_scan]
				self.TerrestrialRegionEntry = getConfigListEntry(_('Region'), self.TerrestrialRegion)
				self.list.append(self.TerrestrialRegionEntry)
				self.predefinedTerrTranspondersList()
				self.list.append(getConfigListEntry(_('Transponder'), self.TerrestrialTransponders))
				self.TerrestrialTransponders.value = self.TerrestrialTransponders.value
			elif self.scan_typeterrestrial.value == "complete":
				self.TerrestrialRegion = self.terrestrial_nims_regions[index_to_scan]
				self.TerrestrialRegionEntry = getConfigListEntry(_('Region'), self.TerrestrialRegion)
				self.list.append(self.TerrestrialRegionEntry)
		elif nim.isCompatible("ATSC"):
			if self.scan_typeatsc.value == "single_transponder":
				self.systemEntry = getConfigListEntry(_("System"), self.scan_ats.system)
				self.list.append(self.systemEntry)
				self.list.append(getConfigListEntry(_("Frequency"), self.scan_ats.frequency))
				self.list.append(getConfigListEntry(_("Inversion"), self.scan_ats.inversion))
				self.list.append(getConfigListEntry(_("Modulation"), self.scan_ats.modulation))
			elif self.scan_typeatsc.value == "predefined_transponder":
				#FIXME add region
				self.predefinedATSCTranspondersList()
				self.list.append(getConfigListEntry(_('Transponder'), self.ATSCTransponders))
			elif self.scan_typeatsc.value == "complete":
				pass #FIXME
		self.list.append(getConfigListEntry(_("Network scan"), self.scan_networkScan))
		self.list.append(getConfigListEntry(_("Clear before scan"), self.scan_clearallservices))
		self.list.append(getConfigListEntry(_("Only free scan"), self.scan_onlyfree))
		self.setConfigList()

	def setConfigList(self):
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def Satexists(self, tlist, pos):
		for x in tlist:
			if x == pos:
				return 1
		return 0

	def newConfig(self):
		cur = self["config"].getCurrent()
		print "cur is", cur
		print type(cur)
		if cur is not None:
			if cur == self.multiType:
				self.TunerTypeChanged()
			if cur in (
				self.typeOfScanEntry,
				self.typeOfInputEntry,
				self.tunerEntry,
				self.systemEntry,
				self.preDefSatList,
				self.TerrestrialRegionEntry,
				self.multiType,
				self.modulationEntry):
					self.createSetup()
			elif cur == self.t2mi_Entry:
				if self.scan_sat.t2mi.value == "on":
					if self.t2mi_pid_memory == 0:
						self.t2mi_pid_memory = 4096;
					self.scan_sat.t2mi_pid.value = self.t2mi_pid_memory
					self.scan_sat.t2mi_plp.value = self.t2mi_plp_memory
				else:
					self.t2mi_pid_memory = self.scan_sat.t2mi_pid.value
					self.t2mi_plp_memory = self.scan_sat.t2mi_plp.value
					self.scan_sat.t2mi_pid.value = 0
					self.scan_sat.t2mi_plp.value = 0
					
				self.createSetup()
			elif len(cur) > 1:
				if cur[1] in(
				self.scan_ter.bandwidth,
				self.scan_sat.frequency,
				self.scan_sat.inversion, self.scan_sat.symbolrate,
				self.scan_sat.polarization, self.scan_sat.fec, self.scan_sat.pilot,
				self.scan_sat.fec_s2, self.scan_sat.fec, self.scan_sat.modulation,
				self.scan_sat.rolloff, self.scan_sat.system,
				self.scan_ter.channel, self.scan_ter.frequency, self.scan_ter.inversion,
				self.scan_ter.bandwidth, self.scan_ter.fechigh, self.scan_ter.feclow,
				self.scan_ter.modulation, self.scan_ter.transmission,
				self.scan_ter.guard, self.scan_ter.hierarchy, self.scan_ter.plp_id,
				self.scan_cab.frequency, self.scan_cab.inversion, self.scan_cab.symbolrate,
				self.scan_cab.modulation, self.scan_cab.fec,
				self.scan_ats.frequency, self.scan_ats.inversion, self.scan_ats.modulation,
				self.scan_ats.system,
				self.preDefTransponders, self.CableTransponders, self.TerrestrialTransponders, self.ATSCTransponders
				):
					self.createSetup()
			else:
				pass

	def createConfig(self):
		self.service = self.session.nav.getCurrentService()
		self.feinfo = None
		self.networkid = 0
		frontendData = None
		if self.service is not None:
			self.feinfo = self.service.frontendInfo()
			frontendData = self.feinfo and self.feinfo.getAll(True)
		del self.feinfo
		del self.service
		self.updateSatList()
		defaultSat = {
			"orbpos": 192,
			"system": eDVBFrontendParametersSatellite.System_DVB_S,
			"frequency": 11836,
			"inversion": eDVBFrontendParametersSatellite.Inversion_Unknown,
			"symbolrate": 27500,
			"polarization": eDVBFrontendParametersSatellite.Polarisation_Horizontal,
			"fec": eDVBFrontendParametersSatellite.FEC_Auto,
			"fec_s2": eDVBFrontendParametersSatellite.FEC_9_10,
			"modulation": eDVBFrontendParametersSatellite.Modulation_QPSK,
			"is_id": eDVBFrontendParametersSatellite.No_Stream_Id_Filter,
			"pls_mode": eDVBFrontendParametersSatellite.PLS_Gold,
			"pls_code": 0,
			"t2mi_plp_id": eDVBFrontendParametersSatellite.No_T2MI_PLP_Id }
		defaultCab = {
			"frequency": 466,
			"inversion": eDVBFrontendParametersCable.Inversion_Unknown,
			"modulation": eDVBFrontendParametersCable.Modulation_QAM64,
			"fec": eDVBFrontendParametersCable.FEC_Auto,
			"symbolrate": 6900,
			"system": eDVBFrontendParametersCable.System_DVB_C_ANNEX_A }
		defaultTer = {
			"frequency" : 474000,
			"inversion" : eDVBFrontendParametersTerrestrial.Inversion_Unknown,
			"bandwidth" : 8000000,
			"fechigh" : eDVBFrontendParametersTerrestrial.FEC_Auto,
			"feclow" : eDVBFrontendParametersTerrestrial.FEC_Auto,
			"modulation" : eDVBFrontendParametersTerrestrial.Modulation_Auto,
			"transmission_mode" : eDVBFrontendParametersTerrestrial.TransmissionMode_Auto,
			"guard_interval" : eDVBFrontendParametersTerrestrial.GuardInterval_Auto,
			"hierarchy": eDVBFrontendParametersTerrestrial.Hierarchy_Auto,
			"system": eDVBFrontendParametersTerrestrial.System_DVB_T,
			"plp_id": 0 }
		defaultATSC = {
			"frequency" : 474000,
			"inversion" : eDVBFrontendParametersATSC.Inversion_Unknown,
			"modulation" : eDVBFrontendParametersATSC.Modulation_Auto,
			"system": eDVBFrontendParametersATSC.System_ATSC }

		if frontendData is not None:
			ttype = frontendData.get("tuner_type", "UNKNOWN")
			if ttype == "DVB-S":
				defaultSat["system"] = frontendData.get("system", eDVBFrontendParametersSatellite.System_DVB_S)
				defaultSat["frequency"] = frontendData.get("frequency", 0) / 1000
				defaultSat["inversion"] = frontendData.get("inversion", eDVBFrontendParametersSatellite.Inversion_Unknown)
				defaultSat["symbolrate"] = frontendData.get("symbol_rate", 0) / 1000
				defaultSat["polarization"] = frontendData.get("polarization", eDVBFrontendParametersSatellite.Polarisation_Horizontal)
				if defaultSat["system"] == eDVBFrontendParametersSatellite.System_DVB_S2:
					defaultSat["fec_s2"] = frontendData.get("fec_inner", eDVBFrontendParametersSatellite.FEC_Auto)
					defaultSat["rolloff"] = frontendData.get("rolloff", eDVBFrontendParametersSatellite.RollOff_alpha_0_35)
					defaultSat["pilot"] = frontendData.get("pilot", eDVBFrontendParametersSatellite.Pilot_Unknown)
					defaultSat["is_id"] = frontendData.get("is_id", eDVBFrontendParametersSatellite.No_Stream_Id_Filter)
					defaultSat["pls_mode"] = frontendData.get("pls_mode", eDVBFrontendParametersSatellite.PLS_Gold)
					defaultSat["pls_code"] = frontendData.get("pls_code", 0)
					defaultSat["t2mi_plp_id"] = frontendData.get("t2mi_plp_id", eDVBFrontendParametersSatellite.No_T2MI_PLP_Id)
				else:
					defaultSat["fec"] = frontendData.get("fec_inner", eDVBFrontendParametersSatellite.FEC_Auto)
				defaultSat["modulation"] = frontendData.get("modulation", eDVBFrontendParametersSatellite.Modulation_QPSK)
				defaultSat["orbpos"] = frontendData.get("orbital_position", 0)
			elif ttype == "DVB-C":
				defaultCab["frequency"] = frontendData.get("frequency", 0) / 1000
				defaultCab["symbolrate"] = frontendData.get("symbol_rate", 0) / 1000
				defaultCab["inversion"] = frontendData.get("inversion", eDVBFrontendParametersCable.Inversion_Unknown)
				defaultCab["fec"] = frontendData.get("fec_inner", eDVBFrontendParametersCable.FEC_Auto)
				defaultCab["modulation"] = frontendData.get("modulation", eDVBFrontendParametersCable.Modulation_QAM16)
				defaultCab["system"] = frontendData.get("system", eDVBFrontendParametersCable.System_DVB_C_ANNEX_A)
			elif ttype == "DVB-T":
				defaultTer["frequency"] = frontendData.get("frequency", 47400000) / 1000
				defaultTer["inversion"] = frontendData.get("inversion", eDVBFrontendParametersTerrestrial.Inversion_Unknown)
				defaultTer["bandwidth"] = frontendData.get("bandwidth", 8000000)
				defaultTer["fechigh"] = frontendData.get("code_rate_hp", eDVBFrontendParametersTerrestrial.FEC_Auto)
				defaultTer["feclow"] = frontendData.get("code_rate_lp", eDVBFrontendParametersTerrestrial.FEC_Auto)
				defaultTer["modulation"] = frontendData.get("constellation", eDVBFrontendParametersTerrestrial.Modulation_Auto)
				defaultTer["transmission_mode"] = frontendData.get("transmission_mode", eDVBFrontendParametersTerrestrial.TransmissionMode_Auto)
				defaultTer["guard_interval"] = frontendData.get("guard_interval", eDVBFrontendParametersTerrestrial.GuardInterval_Auto)
				defaultTer["hierarchy"] = frontendData.get("hierarchy_information", eDVBFrontendParametersTerrestrial.Hierarchy_Auto)
				defaultTer["system"] = frontendData.get("system", eDVBFrontendParametersTerrestrial.System_DVB_T)
				defaultTer["plp_id"] = frontendData.get("plp_id", 0)
			elif ttype == "ATSC":
				defaultATSC["frequency"] = frontendData.get("frequency", 47400000) / 1000
				defaultATSC["inversion"] = frontendData.get("inversion", eDVBFrontendParametersATSC.Inversion_Unknown)
				defaultATSC["modulation"] = frontendData.get("modulation", eDVBFrontendParametersATSC.Modulation_Auto)
				defaultATSC["system"] = frontendData.get("system", eDVBFrontendParametersATSC.System_ATSC)

		self.scan_sat = ConfigSubsection()
		self.scan_cab = ConfigSubsection()
		self.scan_ter = ConfigSubsection()
		self.scan_ats = ConfigSubsection()

		nim_list = []
		# collect all nims which are *not* set to "nothing"
		for n in nimmanager.nim_slots:
			dvbs = (n.canBeCompatible("DVB-S") and (n.config.dvbs.configMode.value != "nothing" and True or False))
			dvbc = (n.canBeCompatible("DVB-C") and (n.config.dvbc.configMode.value != "nothing" and True or False))
			dvbt = (n.canBeCompatible("DVB-T") and (n.config.dvbt.configMode.value != "nothing" and True or False))
			atsc = (n.canBeCompatible("ATSC") and (n.config.atsc.configMode.value != "nothing" and True or False))

			if (dvbc or dvbt or atsc):
				nim_list.append((str(n.slot), n.friendly_full_description))
			elif dvbs:
				if n.canBeCompatible("DVB-S") and len(nimmanager.getSatListForNim(n.slot)) < 1: # empty setup
					continue
				if n.canBeCompatible("DVB-S") and n.config.dvbs.configMode.value in ("loopthrough", "satposdepends"):
					root_id = nimmanager.sec.getRoot(n.slot_id, int(n.config.dvbs.connectedTo.value))
					if n.type == nimmanager.nim_slots[root_id].type: # check if connected from a DVB-S to DVB-S2 Nim or vice versa
						continue
				nim_list.append((str(n.slot), n.friendly_full_description))

		self.scan_nims = ConfigSelection(choices = nim_list)
		if frontendData is not None and len(nim_list) > 0:
			self.scan_nims.setValue(str(frontendData.get("tuner_number", nim_list[0][0])))

		for slot in nimmanager.nim_slots:
			if slot.canBeCompatible("DVB-T"):
				self.ter_tnumber = slot.slot
		if self.ter_tnumber is not None:
			self.ter_channel_input = channelnumbers.supportedChannels(self.ter_tnumber)

		# status
		self.scan_snr = ConfigSlider()
		self.scan_snr.enabled = False
		self.scan_agc = ConfigSlider()
		self.scan_agc.enabled = False
		self.scan_ber = ConfigSlider()
		self.scan_ber.enabled = False

		# sat
		self.scan_sat.system = ConfigSelection(default = defaultSat["system"], choices = [
			(eDVBFrontendParametersSatellite.System_DVB_S, _("DVB-S")),
			(eDVBFrontendParametersSatellite.System_DVB_S2, _("DVB-S2"))])
		self.scan_sat.frequency = ConfigInteger(default = defaultSat["frequency"], limits = (1, 99999))
		self.scan_sat.inversion = ConfigSelection(default = defaultSat["inversion"], choices = [
			(eDVBFrontendParametersSatellite.Inversion_Off, _("Off")),
			(eDVBFrontendParametersSatellite.Inversion_On, _("On")),
			(eDVBFrontendParametersSatellite.Inversion_Unknown, _("Auto"))])
		self.scan_sat.symbolrate = ConfigInteger(default = defaultSat["symbolrate"], limits = (1, 99999))
		self.scan_sat.polarization = ConfigSelection(default = defaultSat["polarization"], choices = [
			(eDVBFrontendParametersSatellite.Polarisation_Horizontal, _("horizontal")),
			(eDVBFrontendParametersSatellite.Polarisation_Vertical, _("vertical")),
			(eDVBFrontendParametersSatellite.Polarisation_CircularLeft, _("circular left")),
			(eDVBFrontendParametersSatellite.Polarisation_CircularRight, _("circular right"))])
		self.scan_sat.fec = ConfigSelection(default = defaultSat["fec"], choices = [
			(eDVBFrontendParametersSatellite.FEC_Auto, _("Auto")),
			(eDVBFrontendParametersSatellite.FEC_1_2, "1/2"),
			(eDVBFrontendParametersSatellite.FEC_2_3, "2/3"),
			(eDVBFrontendParametersSatellite.FEC_3_4, "3/4"),
			(eDVBFrontendParametersSatellite.FEC_5_6, "5/6"),
			(eDVBFrontendParametersSatellite.FEC_7_8, "7/8"),
			(eDVBFrontendParametersSatellite.FEC_None, _("None"))])
		self.scan_sat.fec_s2 = ConfigSelection(default = defaultSat["fec_s2"], choices = [
			(eDVBFrontendParametersSatellite.FEC_1_2, "1/2"),
			(eDVBFrontendParametersSatellite.FEC_2_3, "2/3"),
			(eDVBFrontendParametersSatellite.FEC_3_4, "3/4"),
			(eDVBFrontendParametersSatellite.FEC_3_5, "3/5"),
			(eDVBFrontendParametersSatellite.FEC_4_5, "4/5"),
			(eDVBFrontendParametersSatellite.FEC_5_6, "5/6"),
			(eDVBFrontendParametersSatellite.FEC_7_8, "7/8"),
			(eDVBFrontendParametersSatellite.FEC_8_9, "8/9"),
			(eDVBFrontendParametersSatellite.FEC_9_10, "9/10")])
		self.scan_sat.modulation = ConfigSelection(default = defaultSat["modulation"], choices = [
			(eDVBFrontendParametersSatellite.Modulation_QPSK, "QPSK"),
			(eDVBFrontendParametersSatellite.Modulation_8PSK, "8PSK"),
			(eDVBFrontendParametersSatellite.Modulation_16APSK, "16APSK"),
			(eDVBFrontendParametersSatellite.Modulation_32APSK, "32APSK")])
		self.scan_sat.rolloff = ConfigSelection(default = defaultSat.get("rolloff", eDVBFrontendParametersSatellite.RollOff_alpha_0_35), choices = [
			(eDVBFrontendParametersSatellite.RollOff_alpha_0_35, "0.35"),
			(eDVBFrontendParametersSatellite.RollOff_alpha_0_25, "0.25"),
			(eDVBFrontendParametersSatellite.RollOff_alpha_0_20, "0.20"),
			(eDVBFrontendParametersSatellite.RollOff_auto, _("Auto"))])
		self.scan_sat.pilot = ConfigSelection(default = defaultSat.get("pilot", eDVBFrontendParametersSatellite.Pilot_Unknown), choices = [
			(eDVBFrontendParametersSatellite.Pilot_Off, _("Off")),
			(eDVBFrontendParametersSatellite.Pilot_On, _("On")),
			(eDVBFrontendParametersSatellite.Pilot_Unknown, _("Auto"))])
		self.scan_sat.is_id = ConfigInteger(default = defaultSat["is_id"], limits = (eDVBFrontendParametersSatellite.No_Stream_Id_Filter, 255))
		self.scan_sat.pls_mode = ConfigSelection(default = defaultSat["pls_mode"], choices = [
			(eDVBFrontendParametersSatellite.PLS_Root, _("Root")),
			(eDVBFrontendParametersSatellite.PLS_Gold, _("Gold")),
			(eDVBFrontendParametersSatellite.PLS_Combo, _("Combo"))])
		self.scan_sat.pls_code = ConfigInteger(default = defaultSat.get("pls_code",0), limits = (0, 262142))
		if defaultSat.get("t2mi_plp_id",eDVBFrontendParametersSatellite.No_T2MI_PLP_Id) != eDVBFrontendParametersSatellite.No_T2MI_PLP_Id and defaultSat.get("t2mi_plp_id",eDVBFrontendParametersSatellite.No_T2MI_PLP_Id) != 0:
			self.scan_sat.t2mi  = ConfigSelection(default = "on", choices = [("on", _("On")),("off", _("Off"))])
			self.scan_sat.t2mi_pid = ConfigInteger(default = ((defaultSat.get("t2mi_plp_id",eDVBFrontendParametersSatellite.No_T2MI_PLP_Id)>>16)&0x1fff), limits = (0, 8192))
			self.scan_sat.t2mi_plp = ConfigInteger(default = ((defaultSat.get("t2mi_plp_id",eDVBFrontendParametersSatellite.No_T2MI_PLP_Id))&0xff), limits = (0, 255))
		else:
			self.scan_sat.t2mi  = ConfigSelection(default = "off", choices = [("on", _("On")),("off", _("Off"))])
			self.scan_sat.t2mi_pid = ConfigInteger(default = 0, limits = (0, 8192))
			self.scan_sat.t2mi_plp = ConfigInteger(default = 0, limits = (0, 255))
		
		self.t2mi_pid_memory = self.scan_sat.t2mi_pid.value
		self.t2mi_plp_memory = self.scan_sat.t2mi_plp.value

		# cable
		self.scan_cab.frequency = ConfigInteger(default = defaultCab["frequency"], limits = (50, 999))
		self.scan_cab.inversion = ConfigSelection(default = defaultCab["inversion"], choices = [
			(eDVBFrontendParametersCable.Inversion_Off, _("Off")),
			(eDVBFrontendParametersCable.Inversion_On, _("On")),
			(eDVBFrontendParametersCable.Inversion_Unknown, _("Auto"))])
		self.scan_cab.modulation = ConfigSelection(default = defaultCab["modulation"], choices = [
			(eDVBFrontendParametersCable.Modulation_QAM16, "16-QAM"),
			(eDVBFrontendParametersCable.Modulation_QAM32, "32-QAM"),
			(eDVBFrontendParametersCable.Modulation_QAM64, "64-QAM"),
			(eDVBFrontendParametersCable.Modulation_QAM128, "128-QAM"),
			(eDVBFrontendParametersCable.Modulation_QAM256, "256-QAM")])
		self.scan_cab.fec = ConfigSelection(default = defaultCab["fec"], choices = [
			(eDVBFrontendParametersCable.FEC_Auto, _("Auto")),
			(eDVBFrontendParametersCable.FEC_1_2, "1/2"),
			(eDVBFrontendParametersCable.FEC_2_3, "2/3"),
			(eDVBFrontendParametersCable.FEC_3_4, "3/4"),
			(eDVBFrontendParametersCable.FEC_5_6, "5/6"),
			(eDVBFrontendParametersCable.FEC_7_8, "7/8"),
			(eDVBFrontendParametersCable.FEC_8_9, "8/9"),
			(eDVBFrontendParametersCable.FEC_3_5, "3/5"),
			(eDVBFrontendParametersCable.FEC_4_5, "4/5"),
			(eDVBFrontendParametersCable.FEC_9_10, "9/10"),
			(eDVBFrontendParametersCable.FEC_None, _("None"))])
		self.scan_cab.symbolrate = ConfigInteger(default = defaultCab["symbolrate"], limits = (1, 99999))
		self.scan_cab.system = ConfigSelection(default = defaultCab["system"], choices = [
			(eDVBFrontendParametersCable.System_DVB_C_ANNEX_A, _("DVB-C")),
			(eDVBFrontendParametersCable.System_DVB_C_ANNEX_C, _("DVB-C ANNEX C"))])

		# terrestial
		self.scan_ter.frequency = ConfigFrequency(default = defaultTer["frequency"], limits = (50000, 999000))
		self.scan_ter.channel = ConfigChannel(default = 21, limits = (1, 99))
		self.scan_ter.inversion = ConfigSelection(default = defaultTer["inversion"], choices = [
			(eDVBFrontendParametersTerrestrial.Inversion_Off, _("Off")),
			(eDVBFrontendParametersTerrestrial.Inversion_On, _("On")),
			(eDVBFrontendParametersTerrestrial.Inversion_Unknown, _("Auto"))])
		# WORKAROUND: we can't use BW-auto
		self.scan_ter.bandwidth = ConfigSelection(default = defaultTer["bandwidth"], choices = [
			(1712000, "1.712MHz"),
			(5000000, "5MHz"),
			(6000000, "6MHz"),
			(7000000, "7MHz"),
			(8000000, "8MHz"),
			(10000000, "10MHz")
			])
		#, (eDVBFrontendParametersTerrestrial.Bandwidth_Auto, _("Auto"))))
		self.scan_ter.fechigh = ConfigSelection(default = defaultTer["fechigh"], choices = [
			(eDVBFrontendParametersTerrestrial.FEC_1_2, "1/2"),
			(eDVBFrontendParametersTerrestrial.FEC_2_3, "2/3"),
			(eDVBFrontendParametersTerrestrial.FEC_3_4, "3/4"),
			(eDVBFrontendParametersTerrestrial.FEC_5_6, "5/6"),
			(eDVBFrontendParametersTerrestrial.FEC_6_7, "6/7"),
			(eDVBFrontendParametersTerrestrial.FEC_7_8, "7/8"),
			(eDVBFrontendParametersTerrestrial.FEC_8_9, "8/9"),
			(eDVBFrontendParametersTerrestrial.FEC_Auto, _("Auto"))])
		self.scan_ter.feclow = ConfigSelection(default = defaultTer["feclow"], choices = [
			(eDVBFrontendParametersTerrestrial.FEC_1_2, "1/2"),
			(eDVBFrontendParametersTerrestrial.FEC_2_3, "2/3"),
			(eDVBFrontendParametersTerrestrial.FEC_3_4, "3/4"),
			(eDVBFrontendParametersTerrestrial.FEC_5_6, "5/6"),
			(eDVBFrontendParametersTerrestrial.FEC_6_7, "6/7"),
			(eDVBFrontendParametersTerrestrial.FEC_7_8, "7/8"),
			(eDVBFrontendParametersTerrestrial.FEC_8_9, "8/9"),
			(eDVBFrontendParametersTerrestrial.FEC_Auto, _("Auto"))])
		self.scan_ter.modulation = ConfigSelection(default = defaultTer["modulation"], choices = [
			(eDVBFrontendParametersTerrestrial.Modulation_QPSK, "QPSK"),
			(eDVBFrontendParametersTerrestrial.Modulation_QAM16, "QAM16"),
			(eDVBFrontendParametersTerrestrial.Modulation_QAM64, "QAM64"),
			(eDVBFrontendParametersTerrestrial.Modulation_QAM256, "QAM256"),
			(eDVBFrontendParametersTerrestrial.Modulation_Auto, _("Auto"))])
		self.scan_ter.transmission = ConfigSelection(default = defaultTer["transmission_mode"], choices = [
			(eDVBFrontendParametersTerrestrial.TransmissionMode_1k, "1K"),
			(eDVBFrontendParametersTerrestrial.TransmissionMode_2k, "2K"),
			(eDVBFrontendParametersTerrestrial.TransmissionMode_4k, "4K"),
			(eDVBFrontendParametersTerrestrial.TransmissionMode_8k, "8K"),
			(eDVBFrontendParametersTerrestrial.TransmissionMode_16k, "16K"),
			(eDVBFrontendParametersTerrestrial.TransmissionMode_32k, "32K"),
			(eDVBFrontendParametersTerrestrial.TransmissionMode_Auto, _("Auto"))])
		self.scan_ter.guard = ConfigSelection(default = defaultTer["guard_interval"], choices = [
			(eDVBFrontendParametersTerrestrial.GuardInterval_1_32, "1/32"),
			(eDVBFrontendParametersTerrestrial.GuardInterval_1_16, "1/16"),
			(eDVBFrontendParametersTerrestrial.GuardInterval_1_8, "1/8"),
			(eDVBFrontendParametersTerrestrial.GuardInterval_1_4, "1/4"),
			(eDVBFrontendParametersTerrestrial.GuardInterval_1_128, "1/128"),
			(eDVBFrontendParametersTerrestrial.GuardInterval_19_128, "19/128"),
			(eDVBFrontendParametersTerrestrial.GuardInterval_19_256, "19/256"),
			(eDVBFrontendParametersTerrestrial.GuardInterval_Auto, _("Auto"))])
		self.scan_ter.hierarchy = ConfigSelection(default = defaultTer["hierarchy"], choices = [
			(eDVBFrontendParametersTerrestrial.Hierarchy_None, _("None")),
			(eDVBFrontendParametersTerrestrial.Hierarchy_1, "1"),
			(eDVBFrontendParametersTerrestrial.Hierarchy_2, "2"),
			(eDVBFrontendParametersTerrestrial.Hierarchy_4, "4"),
			(eDVBFrontendParametersTerrestrial.Hierarchy_Auto, _("Auto"))])
		self.scan_ter.system = ConfigSelection(default = defaultTer["system"], choices = [
			(eDVBFrontendParametersTerrestrial.System_DVB_T, _("DVB-T")),
			(eDVBFrontendParametersTerrestrial.System_DVB_T2, _("DVB-T2"))])
		self.scan_ter.plp_id = ConfigInteger(default = defaultTer["plp_id"], limits = (0, 255))

		# ATSC
		self.scan_ats.frequency = ConfigInteger(default = defaultATSC["frequency"], limits = (50000, 999000))
		self.scan_ats.inversion = ConfigSelection(default = defaultATSC["inversion"], choices = [
			(eDVBFrontendParametersATSC.Inversion_Off, _("Off")),
			(eDVBFrontendParametersATSC.Inversion_On, _("On")),
			(eDVBFrontendParametersATSC.Inversion_Unknown, _("Auto"))])
		self.scan_ats.modulation = ConfigSelection(default = defaultATSC["modulation"], choices = [
			(eDVBFrontendParametersATSC.Modulation_Auto, _("Auto")),
			(eDVBFrontendParametersATSC.Modulation_QAM16, "QAM16"),
			(eDVBFrontendParametersATSC.Modulation_QAM32, "QAM32"),
			(eDVBFrontendParametersATSC.Modulation_QAM64, "QAM64"),
			(eDVBFrontendParametersATSC.Modulation_QAM128, "QAM128"),
			(eDVBFrontendParametersATSC.Modulation_QAM256, "QAM256"),
			(eDVBFrontendParametersATSC.Modulation_VSB_8, "8VSB"),
			(eDVBFrontendParametersATSC.Modulation_VSB_16, "16VSB")])
		self.scan_ats.system = ConfigSelection(default = defaultATSC["system"], choices = [
			(eDVBFrontendParametersATSC.System_ATSC, _("ATSC")),
			(eDVBFrontendParametersATSC.System_DVB_C_ANNEX_B, _("DVB-C ANNEX B"))])

		self.scan_scansat = {}
		for sat in nimmanager.satList:
			#print sat[1]
			self.scan_scansat[sat[0]] = ConfigYesNo(default = False)

		self.scan_satselection = []
		for slot in nimmanager.nim_slots:
			if slot.canBeCompatible("DVB-S"):
				self.scan_satselection.append(getConfigSatlist(defaultSat["orbpos"], self.satList[slot.slot]))
			else:
				self.scan_satselection.append(None)

		self.terrestrial_nims_regions = []
		for slot in nimmanager.nim_slots:
			if slot.canBeCompatible("DVB-T"):
				self.terrestrial_nims_regions.append(self.getTerrestrialRegionsList(slot.slot))
			else:
				self.terrestrial_nims_regions.append(None)

		if frontendData is not None and ttype == "DVB-S" and self.predefinedTranspondersList(defaultSat["orbpos"]) is not None:
			defaultSatSearchType = "predefined_transponder"
		else:
			defaultSatSearchType = "single_transponder"
		if frontendData is not None and ttype == "DVB-T" and self.predefinedTerrTranspondersList() is not None:
			defaultTerrSearchType = "predefined_transponder"
		else:
			defaultTerrSearchType = "single_transponder"

		if frontendData is not None and ttype == "DVB-C" and self.predefinedCabTranspondersList() is not None:
			defaultCabSearchType = "predefined_transponder"
		else:
			defaultCabSearchType = "single_transponder"

		if frontendData is not None and ttype == "ATSC" and self.predefinedATSCTranspondersList() is not None:
			defaultATSCSearchType = "predefined_transponder"
		else:
			defaultATSCSearchType = "single_transponder"

		self.scan_type = ConfigSelection(default = defaultSatSearchType, choices = [("single_transponder", _("User defined transponder")), ("predefined_transponder", _("Predefined transponder")), ("single_satellite", _("Single satellite")), ("multisat", _("Multisat")), ("multisat_yes", _("Multisat all select"))])
		self.scan_typecable = ConfigSelection(default = defaultCabSearchType, choices = [("single_transponder", _("User defined transponder")), ("predefined_transponder", _("Predefined transponder")), ("complete", _("Complete"))])
		self.last_scan_typecable = "single_transponder"
		self.cable_toggle = {"single_transponder":"complete", "complete":"single_transponder"}
		self.scan_typeterrestrial = ConfigSelection(default = defaultTerrSearchType, choices = [("single_transponder", _("User defined transponder")), ("predefined_transponder", _("Predefined transponder")), ("complete", _("Complete"))])
		self.scan_typeatsc = ConfigSelection(default = defaultATSCSearchType, choices = [("single_transponder", _("User defined transponder")), ("predefined_transponder", _("Predefined transponder")), ("complete", _("Complete"))])
		self.scan_input_as = ConfigSelection(default = "channel", choices = [("frequency", _("Frequency")), ("channel", _("Channel"))])
		self.scan_clearallservices = ConfigSelection(default = "no", choices = [("no", _("no")), ("yes", _("yes")), ("yes_hold_feeds", _("yes (keep feeds)"))])
		self.scan_onlyfree = ConfigYesNo(default = False)
		self.scan_networkScan = ConfigYesNo(default = False)

		for x in (
			self.scan_sat.frequency,
			self.scan_sat.inversion,
			self.scan_sat.symbolrate,
			self.scan_sat.polarization,
			self.scan_sat.fec,
			self.scan_sat.pilot,
			self.scan_sat.fec_s2,
			self.scan_sat.fec,
			self.scan_sat.modulation,
			self.scan_sat.rolloff,
			self.scan_sat.system,
			self.preDefTransponders,

			self.scan_ter.channel,
			self.scan_ter.frequency,
			self.scan_ter.inversion,
			self.scan_ter.bandwidth,
			self.scan_ter.fechigh,
			self.scan_ter.feclow,
			self.scan_ter.modulation,
			self.scan_ter.transmission,
			self.scan_ter.guard,
			self.scan_ter.hierarchy,
			self.scan_ter.plp_id,
			self.scan_ter.system,
			self.scan_typeterrestrial,
			self.TerrestrialRegion,
			self.TerrestrialTransponders,

			self.scan_cab.frequency,
			self.scan_cab.inversion,
			self.scan_cab.symbolrate,
			self.scan_cab.modulation,
			self.scan_cab.fec,
			self.CableTransponders,

			self.scan_ats.frequency,
			self.scan_ats.inversion,
			self.scan_ats.modulation,
			self.scan_ats.system,
			self.ATSCTransponders
			):
			if x is not None:
				x.addNotifier(self.TriggeredByConfigElement, initial_call = False)
		return True

	def TriggeredByConfigElement(self, configElement):
		self.scan_ter.channel.removeNotifier(self.TriggeredByConfigElement)
		self.scan_ter.frequency.removeNotifier(self.TriggeredByConfigElement)
		self.TerrestrialTransponders.removeNotifier(self.TriggeredByConfigElement)
		self.CableTransponders.removeNotifier(self.TriggeredByConfigElement)
		self.createSetup()
		self.scan_ter.channel.addNotifier(self.TriggeredByConfigElement, initial_call = False)
		self.scan_ter.frequency.addNotifier(self.TriggeredByConfigElement, initial_call = False)
		self.TerrestrialTransponders.addNotifier(self.TriggeredByConfigElement, initial_call = False)
		self.CableTransponders.addNotifier(self.TriggeredByConfigElement, initial_call = False)

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.newConfig()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.newConfig()

	def handleKeyFileCallback(self, answer):
		ConfigListScreen.handleKeyFileCallback(self, answer)
		self.newConfig()

	def updateStatus(self):
		print "updatestatus"

	def addSatTransponder(self, tlist, frequency, symbol_rate, polarisation, fec, inversion, orbital_position, system, modulation, rolloff, pilot, is_id, pls_mode, pls_code, t2mi_plp_id):
		print "Add Sat: frequ: " + str(frequency) + " symbol: " + str(symbol_rate) + " pol: " + str(polarisation) + " fec: " + str(fec) + " inversion: " + str(inversion) + " modulation: " + str(modulation) + " system: " + str(system) + " rolloff" + str(rolloff) + " pilot" + str(pilot) + " is_id" + str(is_id) + " pls_mode" + str(pls_mode) + " pls_code" + str(pls_code) + " t2mi_plp_id" + str(t2mi_plp_id)
		print "orbpos: " + str(orbital_position)
		parm = eDVBFrontendParametersSatellite()
		parm.modulation = modulation
		parm.system = system
		parm.frequency = frequency * 1000
		parm.symbol_rate = symbol_rate * 1000
		parm.polarisation = polarisation
		parm.fec = fec
		parm.inversion = inversion
		parm.orbital_position = orbital_position
		parm.rolloff = rolloff
		parm.pilot = pilot
		parm.is_id = is_id
		parm.pls_mode = pls_mode
		parm.pls_code = pls_code
		parm.t2mi_plp_id = t2mi_plp_id
		tlist.append(parm)

	def addCabTransponder(self, tlist, frequency, symbol_rate, modulation, fec, inversion):
		print "Add Cab: frequ: " + str(frequency) + " symbol: " + str(symbol_rate) + " pol: " + str(modulation) + " fec: " + str(fec) + " inversion: " + str(inversion)
		parm = eDVBFrontendParametersCable()
		parm.frequency = frequency
		parm.symbol_rate = symbol_rate
		parm.modulation = modulation
		parm.fec_inner = fec
		parm.inversion = inversion
		tlist.append(parm)

	def addTerTransponder(self, tlist, *args, **kwargs):
		tlist.append(buildTerTransponder(*args, **kwargs))

	def addATSCTransponder(self, tlist, frequency, modulation, inversion, system):
		print "Add ATSC frequency: %s inversion: %s modulation: %s system: %s" % (frequency, modulation, inversion, system)
		parm = eDVBFrontendParametersATSC()
		parm.frequency = frequency
		parm.inversion = inversion
		parm.modulation = modulation
		parm.system = system
		tlist.append(parm)

	def keyGo(self):
		infoBarInstance = InfoBar.instance
		if infoBarInstance:
			infoBarInstance.checkTimeshiftRunning(self.keyGoCheckTimeshiftCallback)
		else:
			self.keyGoCheckTimeshiftCallback(True)

	def keyGoCheckTimeshiftCallback(self, answer):
		START_SCAN = 0
		SEARCH_CABLE_TRANSPONDERS = 1
		SEARCH_TERRESTRIAL2_TRANSPONDERS = 2
		if not answer or self.scan_nims.value == "":
			return
		tlist = []
		flags = 0
		removeAll = True
		action = START_SCAN
		index_to_scan = int(self.scan_nims.value)

		if self.scan_nims == [ ]:
			self.session.open(MessageBox, _("No tuner is enabled!\nPlease setup your tuner settings before you start a service scan."), MessageBox.TYPE_ERROR)
			return

		nim = nimmanager.nim_slots[index_to_scan]
		print "nim", nim.slot
		if nim.isCompatible("DVB-S"):
			print "is compatible with DVB-S"
			if "multisat" in self.scan_type.value:
				SatList = nimmanager.getSatListForNim(index_to_scan)
				for x in self.multiscanlist:
					if x[1].value:
						print "   " + str(x[0])
						getInitialTransponderList(tlist, x[0])
			else:
				# these lists are generated for each tuner, so this has work.
				assert len(self.satList) > index_to_scan
				assert len(self.scan_satselection) > index_to_scan

				nimsats = self.satList[index_to_scan]
				selsatidx = self.scan_satselection[index_to_scan].index
				if len(nimsats):
					orbpos = nimsats[selsatidx][0]
					if self.scan_type.value == "single_transponder":
						# however, the satList itself could be empty. in that case, "index" is 0 (for "None").
						if self.scan_sat.system.value == eDVBFrontendParametersSatellite.System_DVB_S:
							fec = self.scan_sat.fec.value
						else:
							fec = self.scan_sat.fec_s2.value
						print "add sat transponder"

						if self.scan_sat.t2mi_pid.value > 0 and self.scan_sat.t2mi_plp.value >= 0:
							t2mi_plp_id = (self.scan_sat.t2mi_pid.value<<16)|self.scan_sat.t2mi_plp.value
						else:
							t2mi_plp_id = eDVBFrontendParametersSatellite.No_T2MI_PLP_Id
							
						self.addSatTransponder(tlist, self.scan_sat.frequency.value,
									self.scan_sat.symbolrate.value,
									self.scan_sat.polarization.value,
									fec,
									self.scan_sat.inversion.value,
									orbpos,
									self.scan_sat.system.value,
									self.scan_sat.modulation.value,
									self.scan_sat.rolloff.value,
									self.scan_sat.pilot.value,
									self.scan_sat.is_id.value,
									self.scan_sat.pls_mode.value,
									self.scan_sat.pls_code.value,
									t2mi_plp_id)
					elif self.scan_type.value == "predefined_transponder":
						tps = nimmanager.getTransponders(orbpos)
						if len(tps) and len(tps) > self.preDefTransponders.index:
							tp = tps[self.preDefTransponders.index]
							self.addSatTransponder(tlist, tp[1] / 1000, tp[2] / 1000, tp[3], tp[4], tp[7], orbpos, tp[5], tp[6], tp[8], tp[9], tp[10], tp[11], tp[12], tp[13])
					elif self.scan_type.value == "single_satellite":
						getInitialTransponderList(tlist, orbpos)

				if self.scan_type.value == "single_transponder" or self.scan_type.value == "predefined_transponder":
					removeAll = False

		elif nim.isCompatible("DVB-C"):
			if self.scan_typecable.value == "single_transponder":
				self.addCabTransponder(tlist, self.scan_cab.frequency.value*1000,
											  self.scan_cab.symbolrate.value*1000,
											  self.scan_cab.modulation.value,
											  self.scan_cab.fec.value,
											  self.scan_cab.inversion.value)
				removeAll = False
			elif self.scan_typecable.value == "predefined_transponder":
				tps = nimmanager.getTranspondersCable(index_to_scan)
				if len(tps) and len(tps) > self.CableTransponders.index :
					tp = tps[self.CableTransponders.index]
					# 0 transponder type, 1 freq, 2 sym, 3 mod, 4 fec, 5 inv, 6 sys
					self.addCabTransponder(tlist, tp[1], tp[2], tp[3], tp[4], tp[5])
				removeAll = False
			elif self.scan_typecable.value == "complete":
				if config.Nims[index_to_scan].dvbc.scan_type.value == "provider":
					getInitialCableTransponderList(tlist, index_to_scan)
				elif nimmanager.nim_slots[index_to_scan].supportsBlindScan():
					flags |= eComponentScan.scanBlindSearch
					self.addCabTransponder(tlist, 73000,
												  (866000 - 73000) / 1000,
												  eDVBFrontendParametersCable.Modulation_Auto,
												  eDVBFrontendParametersCable.FEC_Auto,
												  eDVBFrontendParametersCable.Inversion_Unknown)
					removeAll = False
				else:
					action = SEARCH_CABLE_TRANSPONDERS

		elif nim.isCompatible("DVB-T"):
			if self.scan_typeterrestrial.value == "single_transponder":
				if self.scan_input_as.value == "channel":
					frequency = channelnumbers.channel2frequency(self.scan_ter.channel.value, self.ter_tnumber)
				else:
					frequency = self.scan_ter.frequency.value * 1000
				self.addTerTransponder(tlist,
						frequency,
						inversion = self.scan_ter.inversion.value,
						bandwidth = self.scan_ter.bandwidth.value,
						fechigh = self.scan_ter.fechigh.value,
						feclow = self.scan_ter.feclow.value,
						modulation = self.scan_ter.modulation.value,
						transmission = self.scan_ter.transmission.value,
						guard = self.scan_ter.guard.value,
						hierarchy = self.scan_ter.hierarchy.value,
						system = self.scan_ter.system.value,
						plp_id = self.scan_ter.plp_id.value)
				removeAll = False
			elif self.scan_typeterrestrial.value == "predefined_transponder":
				if self.TerrestrialTransponders is not None:
					region = self.terrestrial_nims_regions[index_to_scan].value
					tps = nimmanager.getTranspondersTerrestrial(region)
					if len(tps) and len(tps) > self.TerrestrialTransponders.index :
						tp = tps[self.TerrestrialTransponders.index]
						tlist.append(buildTerTransponder(tp[1], tp[9], tp[2], tp[4], tp[5], tp[3], tp[7], tp[6], tp[8], tp[10], tp[11]))
				removeAll = False
			elif self.scan_typeterrestrial.value == "complete":
				skip_t2 = False
				if getMachineBrand() in ('Vu+'):
					skip_t2 = True
					if nim.canBeCompatible("DVB-T2"):
						scan_util = len(self.terrestrialTransponderGetCmd(nim.slot)) and True or False
						if scan_util:
							action = SEARCH_TERRESTRIAL2_TRANSPONDERS
						else:
							skip_t2 = False
				getInitialTerrestrialTransponderList(tlist, self.TerrestrialRegion.value, skip_t2)

		elif nim.isCompatible("ATSC"):
			if self.scan_typeatsc.value == "single_transponder":
				self.addATSCTransponder(tlist,
						frequency = self.scan_ats.frequency.value * 1000,
						modulation = self.scan_ats.modulation.value,
						inversion = self.scan_ats.inversion.value,
						system = self.scan_ats.system.value)
				removeAll = False
			elif self.scan_typeatsc.value == "predefined_transponder":
				tps = nimmanager.getTranspondersATSC(index_to_scan)
				if tps and len(tps) > self.ATSCTransponders.index:
					tp = tps[self.ATSCTransponders.index]
					self.addATSCTransponder(tlist, tp[1], tp[2], tp[3], tp[4])
				removeAll = False
			elif self.scan_typeatsc.value == "complete":
				getInitialATSCTransponderList(tlist, index_to_scan)

		flags |= self.scan_networkScan.value and eComponentScan.scanNetworkSearch or 0

		tmp = self.scan_clearallservices.value
		if tmp == "yes":
			flags |= eComponentScan.scanRemoveServices
		elif tmp == "yes_hold_feeds":
			flags |= eComponentScan.scanRemoveServices
			flags |= eComponentScan.scanDontRemoveFeeds

		if tmp != "no" and not removeAll:
			flags |= eComponentScan.scanDontRemoveUnscanned

		if self.scan_onlyfree.value:
			flags |= eComponentScan.scanOnlyFree

		for x in self["config"].list:
			x[1].save()

		if action == START_SCAN:
			self.startScan(tlist, flags, index_to_scan, self.networkid)
		elif action == SEARCH_CABLE_TRANSPONDERS:
			self.flags = flags
			self.feid = index_to_scan
			self.tlist = []
			self.startCableTransponderSearch(self.feid)
		elif action == SEARCH_TERRESTRIAL2_TRANSPONDERS:
			self.flags = flags
			self.feid = index_to_scan
			self.tlist = tlist
			self.startTerrestrialTransponderSearch(self.feid, nimmanager.getTerrestrialDescription(self.feid))

	def setCableTransponderSearchResult(self, tlist):
		self.tlist = tlist

	def cableTransponderSearchFinished(self):
		if self.tlist is None:
			self.tlist = []
		else:
			self.startScan(self.tlist, self.flags, self.feid)

	def setTerrestrialTransponderSearchResult(self, tlist):
		if tlist is not None:
			self.tlist.extend(tlist)

	def terrestrialTransponderSearchFinished(self):
		if self.tlist is None:
			self.tlist = []
		else:
			self.startScan(self.tlist, self.flags, self.feid)

	def predefinedTranspondersList(self, orbpos):
		default = None
		if orbpos is not None:
			list = []
			if self.scan_sat.system.value == eDVBFrontendParametersSatellite.System_DVB_S2:
				fec = self.scan_sat.fec_s2.value
			else:
				fec = self.scan_sat.fec.value

			if self.scan_sat.t2mi_pid.value > 0 and self.scan_sat.t2mi_plp.value >= 0:
				t2mi_plp_id = (self.scan_sat.t2mi_pid.value<<16)|self.scan_sat.t2mi_plp.value
			else:
				t2mi_plp_id = eDVBFrontendParametersSatellite.No_T2MI_PLP_Id
			
			compare = [
				0, # DVB type
				self.scan_sat.frequency.value*1000,  # 1
				self.scan_sat.symbolrate.value*1000, # 2
				self.scan_sat.polarization.value,    # 3
				fec,                                 # 4
				self.scan_sat.system.value,          # 5
				self.scan_sat.modulation.value,      # 6
				self.scan_sat.inversion.value,       # 7
				self.scan_sat.rolloff.value,         # 8
				self.scan_sat.pilot.value,           # 9
				self.scan_sat.is_id.value,           # 10
				self.scan_sat.pls_mode.value,        # 11
				self.scan_sat.pls_code.value,        # 12
				t2mi_plp_id      # 13
				# tsid
				# onid
			]
			i = 0
			tps = nimmanager.getTransponders(orbpos)
			for tp in tps:
				if tp[0] == 0:
					if default is None and self.compareTransponders(tp, compare):
						default = str(i)
					list.append((str(i), self.humanReadableTransponder(tp)))
					i += 1
			if self.preDefTransponders is None:
				self.preDefTransponders = ConfigSelection(choices = list, default = default)
			else:
				self.preDefTransponders.setChoices(choices = list, default = default)

		return default

	def humanReadableTransponder(self, tp):
		if tp[3] in range (4) and tp[4] in range (11):
			pol_list = ['H','V','L','R']
			fec_list = ['Auto','1/2','2/3','3/4','5/6','7/8','8/9','3/5','4/5','9/10','None']
			tp_text = str(tp[1] / 1000) + " " + pol_list[tp[3]] + " " + str(tp[2] / 1000) + " " + fec_list[tp[4]]
			if tp[5] == eDVBFrontendParametersSatellite.System_DVB_S2:
				if tp[10] > eDVBFrontendParametersSatellite.No_Stream_Id_Filter:
					tp_text = ("%s MIS %d") % (tp_text, tp[10])
				if tp[12] > 0:
					tp_text = ("%s Gold %d") % (tp_text, tp[12])
				if tp[13] > eDVBFrontendParametersSatellite.No_T2MI_PLP_Id:
					tp_text = ("%s T2MI %d") % (tp_text, tp[13])
			return tp_text
		return _("Invalid transponder data")

	def compareTransponders(self, tp, compare):
		frequencyTolerance = 2000 #2 MHz
		symbolRateTolerance = 10
		return abs(tp[1] - compare[1]) <= frequencyTolerance and abs(tp[2] - compare[2]) <= symbolRateTolerance and tp[3] == compare[3] and (not tp[4] or tp[4] == compare[4]) and (tp[5] == eDVBFrontendParametersSatellite.System_DVB_S or tp[10] == -1 or tp[10] == compare[10] or tp[13] == compare[13])

	def predefinedTerrTranspondersList(self):
		default = None
		list = []
		compare = [2, self.scan_ter.frequency.value*1000]
		i = 0
		index_to_scan = int(self.scan_nims.value)
		channels = channelnumbers.supportedChannels(index_to_scan)
		region = self.terrestrial_nims_regions[index_to_scan].value
		tps = nimmanager.getTranspondersTerrestrial(region)
		for tp in tps:
			if tp[0] == 2: #TERRESTRIAL
				channel = ''
				if channels:
					channel = _(' (Channel %s)') % (channelnumbers.getChannelNumber(tp[1], index_to_scan))
				if default is None and self.compareTerrTransponders(tp, compare):
					default = str(i)
				list.append((str(i), '%s MHz %s' % (str(tp[1] / 1000000), channel)))
				i += 1
				print "channel", channel
		if self.TerrestrialTransponders is None:
			self.TerrestrialTransponders = ConfigSelection(choices = list, default = default)
		else:
			self.TerrestrialTransponders.setChoices(choices = list, default = default)
		return default

	def compareTerrTransponders(self, tp, compare):
		frequencyTolerance = 1000000 #1 MHz
		return abs(tp[1] - compare[1]) <= frequencyTolerance

	def getTerrestrialRegionsList(self, index_to_scan = None):
		default = None
		list = []
		if index_to_scan is None:
			index_to_scan = int(self.scan_nims.value)
		defaultRegionForNIM = nimmanager.getTerrestrialDescription(index_to_scan)
		for r in nimmanager.terrestrialsList:
			if default is None and r[0] == defaultRegionForNIM:
				default = r[0]
			list.append((r[0], r[0][:46]))
		return ConfigSelection(choices = list, default = default)

	def predefinedCabTranspondersList(self):
		default = None
		list = []
		# 0 transponder type, 1 freq, 2 sym, 3 mod, 4 fec, 5 inv, 6 sys
		compare = [1, self.scan_cab.frequency.value*1000, self.scan_cab.symbolrate.value*1000, self.scan_cab.modulation.value, self.scan_cab.fec.value, self.scan_cab.inversion.value, self.scan_cab.system.value]
		i = 0
		index_to_scan = int(self.scan_nims.value)
		tps = nimmanager.getTranspondersCable(index_to_scan)
		for tp in tps:
			if tp[0] == 1: #CABLE
				if default is None and self.compareCabTransponders(tp, compare):
					default = str(i)
				list.append((str(i), self.humanReadableCabTransponder(tp)))
				i += 1
		if self.CableTransponders is None:
			self.CableTransponders = ConfigSelection(choices = list, default = default)
		else:
			self.CableTransponders.setChoices(choices = list, default = default)
		return default

	def humanReadableCabTransponder(self, tp):
		if tp[3] in range (7) and (tp[4] in range (10) or tp[4] == 15):
			mod_list = ['Auto', '16-QAM','32-QAM','64-QAM','128-QAM', '256-QAM', 'Auto']
			fec_list = {0:"Auto", 1:'1/2', 2:'2/3', 3:'3/4', 4:'5/6', 5:'7/8', 6:'8/9', 7:'3/5', 8:'4/5', 9:'9/10', 15:'None'}
#			print str(tp[1]/1000) + " MHz " + fec_list[tp[4]] + " " + str(tp[2]/1000) + " " + mod_list[tp[3]]
			return str(tp[1]/1000) + " MHz " + fec_list[tp[4]] + " " + str(tp[2]/1000) + " " + mod_list[tp[3]]
		return _("Invalid transponder data")

	def compareCabTransponders(self, tp, compare):
		frequencyTolerance = 1000000 #1 MHz
		symbolRateTolerance = 10
		return abs(tp[1] - compare[1]) <= frequencyTolerance and abs(tp[2] - compare[2]) <= symbolRateTolerance and tp[3] == compare[3] and (not tp[4] or tp[4] == compare[4])

	def predefinedATSCTranspondersList(self):
		default = None
		list = []
		index_to_scan = int(self.scan_nims.value)
		tps = nimmanager.getTranspondersATSC(index_to_scan)
		for i, tp in enumerate(tps):
			if tp[0] == 3: #ATSC
				list.append((str(i), '%s MHz' % (str(tp[1] / 1000000))))
		if self.ATSCTransponders is None:
			self.ATSCTransponders = ConfigSelection(choices = list, default = default)
		else:
			self.ATSCTransponders.setChoices(choices = list, default = default)
		return default

	def startScan(self, tlist, flags, feid, networkid = 0):
		if len(tlist):
			# flags |= eComponentScan.scanSearchBAT
			if self.finished_cb:
				self.session.openWithCallback(self.finished_cb, ServiceScan, [{"transponders": tlist, "feid": feid, "flags": flags, "networkid": networkid}])
			else:
				self.session.openWithCallback(self.startScanCallback, ServiceScan, [{"transponders": tlist, "feid": feid, "flags": flags, "networkid": networkid}])
		else:
			if self.finished_cb:
				self.session.openWithCallback(self.finished_cb, MessageBox, _("Nothing to scan!\nPlease setup your tuner settings before you start a service scan."), MessageBox.TYPE_ERROR)
			else:
				self.session.open(MessageBox, _("Nothing to scan!\nPlease setup your tuner settings before you start a service scan."), MessageBox.TYPE_ERROR)

	def startScanCallback(self, answer=True):
		if answer:
			self.doCloseRecursive()

	def keyCancel(self):
		self.session.nav.playService(self.session.postScanService)
		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def doCloseRecursive(self):
		self.session.nav.playService(self.session.postScanService)
		self.closeRecursive()

class ScanSimple(ConfigListScreen, Screen, CableTransponderSearchSupport, TerrestrialTransponderSearchSupport):
	def getNetworksForNim(self, nim):
		networks = [ ]
		if nim.canBeCompatible("DVB-S") and nim.config.dvbs.configMode.value != "nothing":
			networks += nimmanager.getSatListForNim(nim.slot)
		if nim.canBeCompatible("DVB-T") and nim.config.dvbt.configMode.value != "nothing":
			networks += [nimmanager.getTerrestrialDescription(nim.slot)]
		if nim.canBeCompatible("DVB-C") and nim.config.dvbc.configMode.value != "nothing":
			networks += [ nimmanager.getCableDescription(nim.slot)]
		#if nim.canBeCompatible("ATSC") and nim.config.atsc.configMode.value != "nothing":
		#	networks += [ nimmanager.getATSCDescription(nim.slot)]
		#if not nim.empty and not (nim.canBeCompatible("DVB-S") or nim.canBeCompatible("DVB-C") or nim.canBeCompatible("DVB-S") or nim.canBeCompatible("ATSC")):
		if not nim.empty and not (nim.canBeCompatible("DVB-S") or nim.canBeCompatible("DVB-C") or nim.canBeCompatible("DVB-S")):
			print"unsupported nim type %s" % nim.type
			networks += [nim.type]

		return networks

	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("Automatic Scan"))

		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Scan"))

		self["actions"] = ActionMap(["SetupActions", "MenuActions", "ColorActions"],
		{
			"ok": self.keyGo,
			"save": self.keyGo,
			"cancel": self.keyCancel,
			"menu": self.doCloseRecursive,
			"red": self.keyCancel,
			"green": self.keyGo,
		}, -2)

		self.session.postScanService = session.nav.getCurrentlyPlayingServiceOrGroup()

		self.list = []
		tlist = []

		known_networks = [ ]
		nims_to_scan = set()
		self.finished_cb = None

		#collect networks
		networks = { }
		for nim in nimmanager.nim_slots:

			if nim.canBeCompatible("DVB-S") and nim.config.dvbs.configMode.value != "nothing":
				new_network =  nimmanager.getSatListForNim(nim.slot)
				known = networks.get("DVB-S", set())
				known2 = networks.get("DVB-S2", set())
				for x in new_network:
					nims_to_scan.add(nim)
					if nim.canBeCompatible("DVB-S2"):
						known2.add(x)
					else:
						known.add(x)
				networks.update({"DVB-S2": known2})
				networks.update({"DVB-S": known})

			if nim.canBeCompatible("DVB-T") and nim.config.dvbt.configMode.value != "nothing":
				new_network = [nimmanager.getTerrestrialDescription(nim.slot)]
				known = networks.get("DVB-T", set())
				known2 = networks.get("DVB-T2", set())
				for x in new_network:
					nims_to_scan.add(nim)
					if nim.canBeCompatible("DVB-T2"):
						known2.add(x)
					else:
						known.add(x)
				networks.update({"DVB-T2": known2})
				networks.update({"DVB-T": known})

			if nim.canBeCompatible("DVB-C") and nim.config.dvbc.configMode.value != "nothing":
				new_network = [nimmanager.getCableDescription(nim.slot)]
				known = networks.get("DVB-C", set())
				known2 = networks.get("DVB-C2", set())
				for x in new_network:
					nims_to_scan.add(nim)
					if nim.canBeCompatible("DVB-C2"):
						known2.add(x)
					else:
						known.add(x)
				networks.update({"DVB-C2": known2})
				networks.update({"DVB-C": known})

			if nim.canBeCompatible("ATSC") and nim.config.atsc.configMode.value != "nothing":
				new_network = [nimmanager.getATSCDescription(nim.slot)]
				known = networks.get("ATSC", set())
				for x in new_network:
					nims_to_scan.add(nim)
					known.add(x)
				networks.update({"ATSC": known})

#			if not nim.empty and not (nim.canBeCompatible("DVB-S") or nim.canBeCompatible("DVB-C") or nim.canBeCompatible("DVB-S")):
#				print"unsupported nim type %s" % nim.type
#				networks += [nim.type]

		known = networks.get("DVB-S", set()) - networks.get("DVB-S2", set())
		networks.update({"DVB-S": known})
		known = networks.get("DVB-T", set()) - networks.get("DVB-T2", set())
		networks.update({"DVB-T": known})
		known = networks.get("DVB-C", set()) - networks.get("DVB-C2", set())
		networks.update({"DVB-C": known})
		known = networks.get("ATSC", set())
		networks.update({"ATSC": known})

		# we save the config elements to use them on keyGo
		self.nim_enable = [ ]

		if len(nims_to_scan):
			self.scan_networkScan = ConfigYesNo(default = True)
			self.scan_clearallservices = ConfigSelection(default = "yes", choices = [("no", _("no")), ("yes", _("yes")), ("yes_hold_feeds", _("yes (keep feeds)"))])
			self.list.append(getConfigListEntry(_("Network scan"), self.scan_networkScan))
			self.list.append(getConfigListEntry(_("Clear before scan"), self.scan_clearallservices))

			#assign nims
			tag_dvbc_default = tag_dvbt_default = tag_dvbs_default = tag_atsc_default = True
			for item in networks.iteritems():
				req_type = item[0]
				for req_network in item[1]:
					for nim in nimmanager.nim_slots:
						tag_dvbc = tag_dvbt = tag_dvbs = tag_atsc = False
						if not nim.canBeCompatible(req_type):
							continue
						if req_type in ("DVB-S", "DVB-S2") and nim.config.dvbs.configMode.value != "nothing" and not tag_dvbs:
							if req_network in nimmanager.getSatListForNim(nim.slot):
								tag_dvbs = True
								nimconfig = ConfigYesNo(default = tag_dvbs_default)
								if tag_dvbs_default == True:
									tag_dvbs_default = False
								nimconfig.nim_index = nim.slot
								nimconfig.network = req_network
								nimconfig.nim_type = "DVB-S"
								self.nim_enable.append(nimconfig)
								self.list.append(getConfigListEntry(_("Scan ") + nim.slot_name + " (DVB-S) " + req_network[1], nimconfig))
								break;
						elif req_type in ("DVB-C", "DVB-C2") and nim.config.dvbc.configMode.value != "nothing"and not tag_dvbc:
							if req_network in nimmanager.getCableDescription(nim.slot):
								tag_dvbc = True
								nimconfig = ConfigYesNo(default = tag_dvbc_default)
								if tag_dvbc_default == True:
									tag_dvbc_default = False
								nimconfig.nim_index = nim.slot
								nimconfig.network = req_network
								nimconfig.nim_type = "DVB-C"
								self.nim_enable.append(nimconfig)
								self.list.append(getConfigListEntry(_("Scan ") + nim.slot_name + " (DVB-C) " + req_network[:45], nimconfig))
								break;
						elif req_type in ("DVB-T", "DVB-T2") and nim.config.dvbt.configMode.value != "nothing" and not tag_dvbt:
							if req_network in nimmanager.getTerrestrialDescription(nim.slot):
								tag_dvbt = True
								nimconfig = ConfigYesNo(default = tag_dvbt_default)
								if tag_dvbt_default == True:
									tag_dvbt_default = False
								nimconfig.nim_index = nim.slot
								nimconfig.network = req_network
								nimconfig.nim_type = "DVB-T"
								self.nim_enable.append(nimconfig)
								self.list.append(getConfigListEntry(_("Scan ") + nim.slot_name + " (DVB-T) " + req_network[:45], nimconfig))
								break;
						elif req_type in ("ATSC") and nim.config.atsc.configMode.value != "nothing" and not tag_atsc:
							if req_network in nimmanager.getATSCDescription(nim.slot):
								tag_atsc = True
								nimconfig = ConfigYesNo(default = tag_atsc_default)
								if tag_atsc_default == True:
									tag_atsc_default = False
								nimconfig.nim_index = nim.slot
								nimconfig.network = req_network
								nimconfig.nim_type = "ATSC"
								self.nim_enable.append(nimconfig)
								self.list.append(getConfigListEntry(_("Scan ") + nim.slot_name + " (ATSC) " + req_network[:45], nimconfig))
								break;
		self.list.sort()
		ConfigListScreen.__init__(self, self.list)
		self["header"] = Label(_("Automatic scan"))
		self["footer"] = Label(_("Press OK to scan"))

	def runAsync(self, finished_cb):
		self.finished_cb = finished_cb
		self.keyGo()

	def keyGo(self):
		InfoBarInstance = InfoBar.instance
		if InfoBarInstance:
			InfoBarInstance.checkTimeshiftRunning(self.keyGoCheckTimeshiftCallback)
		else:
			self.keyGoCheckTimeshiftCallback(True)

	def keyGoCheckTimeshiftCallback(self, answer):
		if answer:
			self.scanList = []
			self.known_networks = set()
			self.nim_iter=0
			self.buildTransponderList()

	def buildTransponderList(self): # this method is called multiple times because of asynchronous stuff
		APPEND_NOW = 0
		SEARCH_CABLE_TRANSPONDERS = 1
		SEARCH_TERRESTRIAL2_TRANSPONDERS = 2
		action = APPEND_NOW

		n = self.nim_iter < len(self.nim_enable) and self.nim_enable[self.nim_iter] or None
		self.nim_iter += 1
		if n:
			if n.value: # check if nim is enabled
				flags = 0
				nim = nimmanager.nim_slots[n.nim_index]
				tlist = [ ]
				if n.nim_type == "DVB-S":
					getInitialTransponderList(tlist, n.network[0])
				elif n.nim_type == "DVB-C":
					networkid = 0
					if config.Nims[nim.slot].dvbc.scan_type.value == "provider":
						getInitialCableTransponderList(tlist, nim.slot)
					else:
						action = SEARCH_CABLE_TRANSPONDERS
						networkid = config.Nims[nim.slot].dvbc.scan_networkid.value
				elif n.nim_type == "DVB-T":
					skip_t2 = False
					if getMachineBrand() in ('Vu+'):
						skip_t2 = True
						if nim.canBeCompatible("DVB-T2"):
							scan_util = len(self.terrestrialTransponderGetCmd(nim.slot)) and True or False
							if scan_util:
								action = SEARCH_TERRESTRIAL2_TRANSPONDERS
							else:
								skip_t2 = False
					getInitialTerrestrialTransponderList(tlist, n.network, skip_t2)
				if n.nim_type == "ATSC":
					getInitialATSCTransponderList(tlist, nim.slot)
				else:
					assert False

				flags = self.scan_networkScan.value and eComponentScan.scanNetworkSearch or 0
				tmp = self.scan_clearallservices.value
				if tmp == "yes":
					flags |= eComponentScan.scanRemoveServices
				elif tmp == "yes_hold_feeds":
					flags |= eComponentScan.scanRemoveServices
					flags |= eComponentScan.scanDontRemoveFeeds

				if action == APPEND_NOW:
					self.scanList.append({"transponders": tlist, "feid": nim.slot, "flags": flags})
				elif action == SEARCH_CABLE_TRANSPONDERS:
					self.flags = flags
					self.feid = nim.slot
					self.networkid = networkid
					self.startCableTransponderSearch(nim.slot)
					return
				elif action == SEARCH_TERRESTRIAL2_TRANSPONDERS:
					self.tlist = tlist
					self.flags = flags
					self.feid = nim.slot
					self.startTerrestrialTransponderSearch(nim.slot, n.network)
					return
				else:
					assert False

			self.buildTransponderList() # recursive call of this function !!!
			return
		# when we are here, then the recursion is finished and all enabled nims are checked
		# so we now start the real transponder scan
		self.startScan(self.scanList)

	def startScan(self, scanList):
		if len(scanList):
			if self.finished_cb:
				self.session.openWithCallback(self.finished_cb, ServiceScan, scanList = scanList)
			else:
				self.session.open(ServiceScan, scanList = scanList)
		else:
			if self.finished_cb:
				self.session.openWithCallback(self.finished_cb, MessageBox, _("Nothing to scan!\nPlease setup your tuner settings before you start a service scan."), MessageBox.TYPE_ERROR)
			else:
				self.session.open(MessageBox, _("Nothing to scan!\nPlease setup your tuner settings before you start a service scan."), MessageBox.TYPE_ERROR)

	def setCableTransponderSearchResult(self, tlist):
		if tlist is not None:
			self.scanList.append({"transponders": tlist, "feid": self.feid, "flags": self.flags})

	def cableTransponderSearchFinished(self):
		self.buildTransponderList()

	def setTerrestrialTransponderSearchResult(self, tlist):
		if tlist is not None:
			self.tlist.extend(tlist)
		if self.tlist is not None:
			self.scanList.append({"transponders": self.tlist, "feid": self.feid, "flags": self.flags})

	def terrestrialTransponderSearchFinished(self):
		self.buildTransponderList()

	def keyCancel(self):
		self.session.nav.playService(self.session.postScanService)
		self.close()

	def doCloseRecursive(self):
		self.session.nav.playService(self.session.postScanService)
		self.closeRecursive()

	def Satexists(self, tlist, pos):
		for x in tlist:
			if x == pos:
				return 1
		return 0
