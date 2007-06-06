from Screen import Screen
from ServiceScan import *
from Components.config import config, ConfigSubsection, ConfigSelection, \
	ConfigYesNo, ConfigInteger, getConfigListEntry, ConfigSlider, ConfigSatlist, ConfigEnableDisable
from Components.ActionMap import NumberActionMap
from Components.ConfigList import ConfigList, ConfigListScreen
from Components.NimManager import nimmanager, getConfigSatlist
from Components.Label import Label
from Screens.MessageBox import MessageBox
from enigma import eTimer, eDVBFrontendParametersSatellite, eComponentScan, \
	eDVBSatelliteEquipmentControl, eDVBFrontendParametersTerrestrial, \
	eDVBFrontendParametersCable, eConsoleAppContainer, eDVBResourceManager

def buildTerTransponder(frequency, 
		inversion=2, bandwidth = 3, fechigh = 6, feclow = 6,
		modulation = 2, transmission = 2, guard = 4,
		hierarchy = 4):

#	print "freq", frequency, "inv", inversion, "bw", bandwidth, "fech", fechigh, "fecl", feclow, "mod", modulation, "tm", transmission, "guard", guard, "hierarchy", hierarchy

	# WARNING: normally, enums are working directly.
	# Don't copy this (very bad)!! Instead either fix swig (good) or
	# move this into a central place.
	Bw8MHz = 0
	Bw7MHz = 1
	Bw6MHz = 2
	#Bw5MHz = 3 #not implemented for e1 compatibilty
	BwAuto = 3
	
	f1_2 = 0
	f2_3 = 1
	f3_4 = 2
	f5_6 = 3
	f7_8 = 4
	fAuto = 5
	
	TM2k = 0
	TM8k = 1
	#TM4k = 2  #not implemented for e1 compatibilty
	TMAuto = 2
	
	GI_1_32 = 0
	GI_1_16 = 1
	GI_1_8 = 2
	GI_1_4 = 3
	GI_Auto = 4
	
	HNone = 0
	H1 = 1
	H2 = 2
	H4 = 3
	HAuto = 4

	QPSK = 0
	QAM16 = 1
	QAM64 = 2
	Auto = 3
	
	Off = 0
	On = 1
	Unknown = 2

	parm = eDVBFrontendParametersTerrestrial()

	parm.frequency = frequency

	parm.inversion = [Off, On, Unknown][inversion]
	parm.bandwidth = [Bw8MHz, Bw7MHz, Bw6MHz, BwAuto][bandwidth] # Bw5MHz unsupported
	parm.code_rate_HP = [f1_2, f2_3, f3_4, f5_6, f7_8, fAuto][fechigh]
	parm.code_rate_LP = [f1_2, f2_3, f3_4, f5_6, f7_8, fAuto][feclow]
	parm.modulation = [QPSK, QAM16, QAM64, Auto][modulation]
	parm.transmission_mode = [TM2k, TM8k, TMAuto][transmission] # TM4k unsupported
	parm.guard_interval = [GI_1_32, GI_1_16, GI_1_8, GI_1_4, GI_Auto][guard]
	parm.hierarchy = [HNone, H1, H2, H4, HAuto][hierarchy]
	
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
			parm.inversion = 2 # AUTO
			parm.orbital_position = pos
			parm.system = x[5]
			parm.modulation = x[6]
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
			parm.inversion = 2 # AUTO
			#print "frequency:", x[1]
			#print "symbol_rate:", x[2]
			#print "modulation:", x[3]
			#print "fec_inner:", x[4]
			#print "inversion:", 2
			tlist.append(parm)

def getInitialTerrestrialTransponderList(tlist, region):
	list = nimmanager.getTranspondersTerrestrial(region)

	#self.transponders[self.parsedTer].append((2,freq,bw,const,crh,crl,guard,transm,hierarchy,inv))

	#def buildTerTransponder(frequency, inversion = 2, bandwidth = 3, fechigh = 6, feclow = 6,
				#modulation = 2, transmission = 2, guard = 4, hierarchy = 4):

	for x in list:
		if x[0] == 2: #TERRESTRIAL
			parm = buildTerTransponder(x[1], x[9], x[2], x[4], x[5], x[3], x[7], x[6], x[8])
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

class CableTransponderSearchSupport:
#	def setCableTransponderSearchResult(self, tlist):
#		pass

#	def cableTransponderSearchFinished(self):
#		pass

	def tryGetRawFrontend(self, feid):
		res_mgr = eDVBResourceManager.getInstance()
		if res_mgr:
			raw_channel = res_mgr.allocateRawChannel(self.feid)
			if raw_channel:
				frontend = raw_channel.getFrontend()
				if frontend:
					del frontend
					del raw_channel
					return True
		return False

	def cableTransponderSearchSessionClosed(self, *val):
		print "cableTransponderSearchSessionClosed, val", val
		self.cable_search_container = None
		self.cable_search_session = None
		if val and len(val) and val[0]:
			self.setCableTransponderSearchResult(self.__tlist)
		self.__tlist = None
		self.cableTransponderSearchFinished()

	def cableTransponderSearchClosed(self, retval):
		print "cableTransponderSearch finished", retval
		self.cable_search_session.close(True)

	def getCableTransponderData(self, str):
		data = str.split()
		if len(data):
			if data[0] == 'OK':
				print str
				qam = { "QAM16" : 1, "QAM32" : 2, "QAM64" : 3, "QAM128" : 4, "QAM256" : 5 }
				inv = { "INVERSION_OFF" : 0, "INVERSION_ON" : 1 }
				fec = { "FEC_AUTO" : 0, "FEC_1_2" : 1, "FEC_2_3" : 2, "FEC_3_4" : 3, "FEC_5_6": 4, "FEC_7_8" : 5, "FEC_8_9" : 6, "FEC_NONE" : 15 }
				parm = eDVBFrontendParametersCable()
				parm.frequency = int(data[1])
				parm.symbol_rate = int(data[2])
				parm.fec_inner = fec[data[3]]
				parm.modulation = qam[data[4]]
				parm.inversion = inv[data[5]]
				self.__tlist.append(parm)
		tmpstr = _("Try to find used Transponders in cable network.. please wait...")
		tmpstr += "\n\n"
		tmpstr += data[1]
		tmpstr += " kHz "
		tmpstr += data[0]
		self.cable_search_session["text"].setText(tmpstr)

	def startCableTransponderSearch(self, nim_idx):
		if not self.tryGetRawFrontend(nim_idx):
			self.session.nav.stopService()
			if not self.tryGetRawFrontend(nim_idx):
				if self.session.pipshown: # try to disable pip
					self.session.pipshown = False
					del self.session.pip
				if not self.tryGetRawFrontend(nim_idx):
					self.cableTransponderSearchFinished()
					return
		self.__tlist = [ ]
		self.cable_search_container = eConsoleAppContainer()
		self.cable_search_container.appClosed.get().append(self.cableTransponderSearchClosed)
		self.cable_search_container.dataAvail.get().append(self.getCableTransponderData)
		cableConfig = config.Nims[nim_idx].cable
		cmd = "tda1002x --init --scan --verbose --wakeup --inv 2 --bus "
		#FIXMEEEEEE hardcoded i2c devices for dm7025 and dm8000
		if nim_idx < 2:
			cmd += str(nim_idx)
		else:
			if nim_idx == 2:
				cmd += "2" # first nim socket on DM8000 use /dev/i2c/2
			else:
				cmd += "4" # second nim socket on DM8000 use /dev/i2c/4
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
		print "TDA1002x CMD is", cmd

		self.cable_search_container.execute(cmd)
		tmpstr = _("Try to find used transponders in cable network.. please wait...")
		tmpstr += "\n\n..."
		self.cable_search_session = self.session.openWithCallback(self.cableTransponderSearchSessionClosed, MessageBox, tmpstr, MessageBox.TYPE_INFO)

class ScanSetup(ConfigListScreen, Screen, CableTransponderSearchSupport):
	def __init__(self, session):
		Screen.__init__(self, session)

		self.updateSatList()
		self.service = session.nav.getCurrentService()
		self.feinfo = None
		frontendData = None
		if self.service is not None:
			self.feinfo = self.service.frontendInfo()
			frontendData = self.feinfo and self.feinfo.getAll(True)
		
		self.createConfig(frontendData)

		del self.feinfo
		del self.service

		self["actions"] = NumberActionMap(["SetupActions"],
		{
			"ok": self.keyGo,
			"cancel": self.keyCancel,
		}, -2)

		self.statusTimer = eTimer()
		self.statusTimer.timeout.get().append(self.updateStatus)
		#self.statusTimer.start(5000, True)

		self.list = []
		ConfigListScreen.__init__(self, self.list)
		self.createSetup()

		self["introduction"] = Label(_("Press OK to start the scan"))

	def run(self):
		self.keyGo()

	def updateSatList(self):
		self.satList = []
		for slot in nimmanager.nim_slots:
			if slot.isCompatible("DVB-S"):
				self.satList.append(nimmanager.getSatListForNim(slot.slot))
			else:
				self.satList.append(None)

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
		self.systemEntry = None
		nim = nimmanager.nim_slots[index_to_scan]
		if nim.isCompatible("DVB-S"):
			self.typeOfScanEntry = getConfigListEntry(_("Type of scan"), self.scan_type)
			self.list.append(self.typeOfScanEntry)
		elif nim.isCompatible("DVB-C"):
			self.typeOfScanEntry = getConfigListEntry(_("Type of scan"), self.scan_typecable)
			self.list.append(self.typeOfScanEntry)
		elif nim.isCompatible("DVB-T"):
			self.typeOfScanEntry = getConfigListEntry(_("Type of scan"), self.scan_typeterrestrial)
			self.list.append(self.typeOfScanEntry)

		if nim.isCompatible("DVB-S"):
			if self.scan_type.value == "single_transponder":
				self.updateSatList()
				if nim.isCompatible("DVB-S2"):
					self.systemEntry = getConfigListEntry(_('System'), self.scan_sat.system)
					self.list.append(self.systemEntry)
				else:
					# downgrade to dvb-s, in case a -s2 config was active
					self.scan_sat.system.value = "dvb-s"
				self.list.append(getConfigListEntry(_('Satellite'), self.scan_satselection[index_to_scan]))
				self.list.append(getConfigListEntry(_('Frequency'), self.scan_sat.frequency))
				self.list.append(getConfigListEntry(_('Inversion'), self.scan_sat.inversion))
				self.list.append(getConfigListEntry(_('Symbol Rate'), self.scan_sat.symbolrate))
				self.list.append(getConfigListEntry(_("Polarity"), self.scan_sat.polarization))
				if self.scan_sat.system.value == "dvb-s":
					self.list.append(getConfigListEntry(_("FEC"), self.scan_sat.fec))
				elif self.scan_sat.system.value == "dvb-s2":
					self.list.append(getConfigListEntry(_("FEC"), self.scan_sat.fec_s2))
					self.list.append(getConfigListEntry(_('Modulation'), self.scan_sat.modulation))
				self.list.append(getConfigListEntry(_("Network scan"), self.scan_networkScan))
			elif self.scan_type.value == "single_satellite":
				self.updateSatList()
				print self.scan_satselection[index_to_scan]
				self.list.append(getConfigListEntry(_("Satellite"), self.scan_satselection[index_to_scan]))
				self.list.append(getConfigListEntry(_("Clear before scan"), self.scan_clearallservices))
			elif self.scan_type.value == "multisat":
				# if (norotor)
				tlist = []
				SatList = nimmanager.getSatListForNim(index_to_scan)
				self.list.append(getConfigListEntry(_("Clear before scan"), self.scan_clearallservices))
				for x in SatList:
					if self.Satexists(tlist, x[0]) == 0:
						tlist.append(x[0])
						sat = ConfigEnableDisable(default = True)
						configEntry = getConfigListEntry(nimmanager.getSatDescription(x[0]), sat)
						self.list.append(configEntry)
						self.multiscanlist.append((x[0], sat))
				# if (rotor):
    			   # for sat in nimmanager.satList:
				#	self.list.append(getConfigListEntry(sat[1], self.scan_scansat[sat[0]]))
		elif nim.isCompatible("DVB-C"):
			if self.scan_typecable.value == "single_transponder":
				self.list.append(getConfigListEntry(_("Frequency"), self.scan_cab.frequency))
				self.list.append(getConfigListEntry(_("Inversions"), self.scan_cab.inversion))
				self.list.append(getConfigListEntry(_("Symbol Rate"), self.scan_cab.symbolrate))
				self.list.append(getConfigListEntry(_("Modulation"), self.scan_cab.modulation))
				self.list.append(getConfigListEntry(_("FEC"), self.scan_cab.fec))
				self.list.append(getConfigListEntry(_("Network scan"), self.scan_networkScan))
			elif self.scan_typecable.value == "complete":
				self.list.append(getConfigListEntry(_("Clear before scan"), self.scan_clearallservices))
		elif nim.isCompatible("DVB-T"):
			if self.scan_typeterrestrial.value == "single_transponder":
				self.list.append(getConfigListEntry(_("Frequency"), self.scan_ter.frequency))
				self.list.append(getConfigListEntry(_("Inversion"), self.scan_ter.inversion))
				self.list.append(getConfigListEntry(_("Bandwidth"), self.scan_ter.bandwidth))
				self.list.append(getConfigListEntry(_("Code rate high"), self.scan_ter.fechigh))
				self.list.append(getConfigListEntry(_("Code rate low"), self.scan_ter.feclow))
				self.list.append(getConfigListEntry(_("Modulation"), self.scan_ter.modulation))
				self.list.append(getConfigListEntry(_("Transmission mode"), self.scan_ter.transmission))
				self.list.append(getConfigListEntry(_("Guard interval mode"), self.scan_ter.guard))
				self.list.append(getConfigListEntry(_("Hierarchy mode"), self.scan_ter.hierarchy))
				self.list.append(getConfigListEntry(_("Network scan"), self.scan_networkScan))
			elif self.scan_typeterrestrial.value == "complete":
				self.list.append(getConfigListEntry(_("Clear before scan"), self.scan_clearallservices))

#		if (nim.isCompatible("DVB-S") and self.scan_type.type == "single_transponder") or \
#			(nim.isCompatbile("DVB-C") and self.scan_typecable.type == "single_transponder") or \
#			(nim.isCompatible("DVB-T") and self.scan_typeterrestrial.type == "single_transponder"):
#				self.configElementSNR = getConfigListEntry(_("SNR"), self.scan_snr)
#				self.list.append(self.configElementSNR)
#				self.configElementACG = getConfigListEntry(_("AGC"), self.scan_agc)
#				self.list.append(self.configElementACG)
#				self.configElementBER = getConfigListEntry(_("BER"), self.scan_ber)
#				self.list.append(self.configElementBER)
#				self.statusTimer.start(500, False)
#		else:
#			self.statusTimer.stop()

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
		if cur == self.typeOfScanEntry or \
			cur == self.tunerEntry or \
			cur == self.systemEntry:
			self.createSetup()

	def createConfig(self, frontendData):
							   #("Type", frontendData["system"], TYPE_TEXT),
					   #("Modulation", frontendData["modulation"], TYPE_TEXT),
					   #("Orbital position", frontendData["orbital_position"], TYPE_VALUE_DEC),
					   #("Frequency", frontendData["frequency"], TYPE_VALUE_DEC),
					   #("Symbolrate", frontendData["symbol_rate"], TYPE_VALUE_DEC),
					   #("Polarization", frontendData["polarization"], TYPE_TEXT),
					   #("Inversion", frontendData["inversion"], TYPE_TEXT),
					   #("FEC inner", frontendData["fec_inner"], TYPE_TEXT),
				   		#)
		#elif frontendData["tuner_type"] == "DVB-C":
			#return ( ("NIM", ['A', 'B', 'C', 'D'][frontendData["tuner_number"]], TYPE_TEXT),
					   #("Type", frontendData["tuner_type"], TYPE_TEXT),
					   #("Frequency", frontendData["frequency"], TYPE_VALUE_DEC),
					   #("Symbolrate", frontendData["symbol_rate"], TYPE_VALUE_DEC),
					   #("Modulation", frontendData["modulation"], TYPE_TEXT),
					   #("Inversion", frontendData["inversion"], TYPE_TEXT),
			#		   ("FEC inner", frontendData["fec_inner"], TYPE_TEXT),
				   		#)
		#elif frontendData["tuner_type"] == "DVB-T":
			#return ( ("NIM", ['A', 'B', 'C', 'D'][frontendData["tuner_number"]], TYPE_TEXT),
					   #("Type", frontendData["tuner_type"], TYPE_TEXT),
					   #("Frequency", frontendData["frequency"], TYPE_VALUE_DEC),
					   #("Inversion", frontendData["inversion"], TYPE_TEXT),
					   #("Bandwidth", frontendData["bandwidth"], TYPE_VALUE_DEC),
					   #("CodeRateLP", frontendData["code_rate_lp"], TYPE_TEXT),
					   #("CodeRateHP", frontendData["code_rate_hp"], TYPE_TEXT),
					   #("Constellation", frontendData["constellation"], TYPE_TEXT),
					   #("Transmission Mode", frontendData["transmission_mode"], TYPE_TEXT),
					   #("Guard Interval", frontendData["guard_interval"], TYPE_TEXT),
					   #("Hierarchy Inform.", frontendData["hierarchy_information"], TYPE_TEXT),
			defaultSat = { "orbpos": 192, "system": "dvb-s", "frequency": 11836, "inversion": "auto", "symbolrate": 27500, "polarization": "horizontal", "fec": "auto", "fec_s2": "9_10", "modulation": "qpsk" }
			defaultCab = {"frequency": 466, "inversion": "auto", "modulation": "64qam", "fec": "auto", "symbolrate": 6900}
			if frontendData is not None:
				ttype = frontendData.get("tuner_type", "UNKNOWN")
				if ttype == "DVB-S":
					defaultSat["system"] = {"DVB-S": "dvb-s", "DVB-S2": "dvb-s2"}[frontendData.get("system", "DVB-S")]
					defaultSat["frequency"] = int(frontendData.get("frequency", 0) / 1000)
					defaultSat["inversion"] = {"INVERSION_OFF": "off", "INVERSION_ON": "on", "INVERSION_AUTO": "auto"}[frontendData.get("inversion", "INVERSION_AUTO")]
					defaultSat["symbolrate"] = int(frontendData.get("symbol_rate", 0) / 1000)
					defaultSat["polarization"] = {"HORIZONTAL": "horizontal", "VERTICAL": "vertical", "CIRCULAR_LEFT": "circular_left", "CIRCULAR_RIGHT": "circular_right", "UNKNOWN": None}[frontendData.get("polarization", "HORIZONTAL")]
					
					if frontendData.get("system", "DVB-S") == "DVB-S2":
						defaultSat["fec_s2"] = {"FEC_1_2": "1_2", "FEC_2_3": "2_3", "FEC_3_4": "3_4", "FEC_4_5": "4_5", "FEC_5_6": "5_6", "FEC_7_8": "7_8", "FEC_8_9": "8_9", "FEC_9_10": "9_10"} \
											[frontendData.get("fec_inner", "FEC_AUTO")]
					else:
						defaultSat["fec"] = {"FEC_AUTO": "auto", "FEC_1_2": "1_2", "FEC_2_3": "2_3", "FEC_3_4": "3_4", "FEC_5_6": "5_6", "FEC_7_8": "7_8", "FEC_NONE": "none"} \
							[frontendData.get("fec_inner", "FEC_AUTO")]

					defaultSat["modulation"] = {"QPSK": "qpsk", "8PSK": "8psk"}[frontendData.get("modulation", "QPSK")]
					defaultSat["orbpos"] = frontendData.get("orbital_position", 0)
				elif ttype == "DVB-C":
					defaultCab["frequency"] = int(frontendData.get("frequency", 0) / 1000)
					defaultCab["symbolrate"] = int(frontendData.get("symbol_rate", 0) / 1000)
					defaultCab["inversion"] = {"INVERSION_OFF": "off", "INVERSION_ON": "on", "INVERSION_AUTO": "auto"}[frontendData.get("inversion", "INVERSION_AUTO")]
					defaultCab["fec"] = {"FEC_AUTO": "auto", "FEC_1_2": "1_2", "FEC_2_3": "2_3", "FEC_3_4": "3_4", "FEC_5_6": "5_6", "FEC_7_8": "7_8", "FEC_8_9": "8_9", "FEC_NONE": "none"}[frontendData.get("fec_inner", "FEC_AUTO")]
					defaultCab["modulation"] = {"QAM_AUTO": "auto", "QAM_16": "16qam", "QAM_32": "32qam", "QAM_64": "64qam", "QAM_128": "128qam", "QAM_256": "256qam"}[frontendData.get("modulation", "QAM_16")]

			self.scan_sat = ConfigSubsection()
			self.scan_cab = ConfigSubsection()
			self.scan_ter = ConfigSubsection()

			self.scan_type = ConfigSelection(default = "single_transponder", choices = [("single_transponder", _("Single transponder")), ("single_satellite", _("Single satellite")), ("multisat", _("Multisat"))])
			self.scan_typecable = ConfigSelection(default = "single_transponder", choices = [("single_transponder", _("Single transponder")), ("complete", _("Complete"))])
			self.scan_typeterrestrial = ConfigSelection(default = "single_transponder", choices = [("single_transponder", _("Single transponder")), ("complete", _("Complete"))])
			self.scan_clearallservices = ConfigSelection(default = "no", choices = [("no", _("no")), ("yes", _("yes")), ("yes_hold_feeds", _("yes (keep feeds)"))])
			self.scan_networkScan = ConfigYesNo(default = False)

			nim_list = []
			# collect all nims which are *not* set to "nothing"
			for n in nimmanager.nim_slots:
				if n.config_mode != "nothing":
					nim_list.append((str(n.slot), n.friendly_full_description))

			self.scan_nims = ConfigSelection(choices = nim_list)

			# status
			self.scan_snr = ConfigSlider()
			self.scan_snr.enabled = False
			self.scan_agc = ConfigSlider()
			self.scan_agc.enabled = False
			self.scan_ber = ConfigSlider()
			self.scan_ber.enabled = False

			# sat
			self.scan_sat.system = ConfigSelection(default = defaultSat["system"], choices = [("dvb-s", _("DVB-S")), ("dvb-s2", _("DVB-S2"))])
			self.scan_sat.frequency = ConfigInteger(default = defaultSat["frequency"], limits = (1, 99999))
			self.scan_sat.inversion = ConfigSelection(default = defaultSat["inversion"], choices = [("off", _("off")), ("on", _("on")), ("auto", _("Auto"))])
			self.scan_sat.symbolrate = ConfigInteger(default = defaultSat["symbolrate"], limits = (1, 99999))
			self.scan_sat.polarization = ConfigSelection(default = defaultSat["polarization"], choices = [("horizontal", _("horizontal")), ("vertical", _("vertical")),  ("circular_left", _("circular left")), ("circular_right", _("circular right"))])
			self.scan_sat.fec = ConfigSelection(default = defaultSat["fec"], choices = [("auto", _("Auto")), ("1_2", "1/2"), ("2_3", "2/3"), ("3_4", "3/4"), ("5_6", "5/6"), ("7_8", "7/8"), ("none", _("None"))])
			self.scan_sat.fec_s2 = ConfigSelection(default = defaultSat["fec_s2"], choices = [("1_2", "1/2"), ("2_3", "2/3"), ("3_4", "3/4"), ("3_5", "3/5"), ("4_5", "4/5"), ("5_6", "5/6"), ("7_8", "7/8"), ("8_9", "8/9"), ("9_10", "9/10")])
			self.scan_sat.modulation = ConfigSelection(default = defaultSat["modulation"], choices = [("qpsk", "QPSK"), ("8psk", "8PSK")])

			# cable
			self.scan_cab.frequency = ConfigInteger(default = defaultCab["frequency"], limits = (50, 999))
			self.scan_cab.inversion = ConfigSelection(default = defaultCab["inversion"], choices = [("off", _("off")), ("on", _("on")), ("auto", _("Auto"))])
			self.scan_cab.modulation = ConfigSelection(default = defaultCab["modulation"], choices = [("16qam", "16-QAM"), ("32qam", "32-QAM"), ("64qam", "64-QAM"), ("128qam", "128-QAM"), ("256qam", "256-QAM")])
			self.scan_cab.fec = ConfigSelection(default = defaultCab["fec"], choices = [("auto", _("Auto")), ("1_2", "1/2"), ("2_3", "2/3"), ("3_4", "3/4"), ("5_6", "5/6"), ("7_8", "7/8"), ("8_9", "8/9"), ("none", _("None"))])
			self.scan_cab.symbolrate = ConfigInteger(default = defaultCab["symbolrate"], limits = (1, 99999))

			# terrestial
			self.scan_ter.frequency = ConfigInteger(default = 466000, limits = (50000, 999000))
			self.scan_ter.inversion = ConfigSelection(default = "auto", choices = [("off", _("off")), ("on", _("on")), ("auto", _("Auto"))])
			# WORKAROUND: we can't use BW-auto
			self.scan_ter.bandwidth = ConfigSelection(default = "8MHz", choices = [("8MHz", "8MHz"), ("7MHz", "7MHz"), ("6MHz", "6MHz")])
			#, ("auto", _("Auto"))))
			self.scan_ter.fechigh = ConfigSelection(default = "auto", choices = [("1_2", "1/2"), ("2_3", "2/3"), ("3_4", "3/4"), ("5_6", "5/6"), ("7_8", "7/8"), ("auto", _("Auto"))])
			self.scan_ter.feclow = ConfigSelection(default = "auto", choices = [("1_2", "1/2"), ("2_3", "2/3"), ("3_4", "3/4"), ("5_6", "5/6"), ("7_8", "7/8"), ("auto", _("Auto"))])
			self.scan_ter.modulation = ConfigSelection(default = "auto", choices = [("qpsk", "QPSK"), ("qam16", "QAM16"), ("qam64", "QAM64"), ("auto", _("Auto"))])
			self.scan_ter.transmission = ConfigSelection(default = "auto", choices = [("2k", "2K"), ("8k", "8K"), ("auto", _("Auto"))])
			self.scan_ter.guard = ConfigSelection(default = "auto", choices = [("1_32", "1/32"), ("1_16", "1/16"), ("1_8", "1/8"), ("1_4", "1/4"), ("auto", _("Auto"))])
			self.scan_ter.hierarchy = ConfigSelection(default = "auto", choices = [("none", _("None")), ("1", "1"), ("2", "2"), ("4", "4"), ("auto", _("Auto"))])

			self.scan_scansat = {}
			for sat in nimmanager.satList:
				#print sat[1]
				self.scan_scansat[sat[0]] = ConfigYesNo(default = False)

			self.scan_satselection = []
			for slot in nimmanager.nim_slots:
				if slot.isCompatible("DVB-S"):
					self.scan_satselection.append(getConfigSatlist(int(defaultSat["orbpos"]), self.satList[slot.slot]))
				else:
					self.scan_satselection.append(None)

			return True

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.newConfig()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.newConfig()

	def updateStatus(self):
		print "updatestatus"

	fecmap = { "auto": 0,
			   "1_2": 1,
			   "2_3": 2,
			   "3_4": 3,
			   "5_6": 4,
			   "7_8": 5,
			   "8_9": 6,
			   "3_5": 7,
			   "4_5": 8,
			   "9_10": 9,
			   "none": 15
			   }

	def addSatTransponder(self, tlist, frequency, symbol_rate, polarisation, fec, inversion, orbital_position, system, modulation):
		print "Add Sat: frequ: " + str(frequency) + " symbol: " + str(symbol_rate) + " pol: " + str(polarisation) + " fec: " + str(self.fecmap[fec]) + " inversion: " + str(inversion) + " modulation: " + str(modulation) + " system: " + str(system)
		print "orbpos: " + str(orbital_position)
		parm = eDVBFrontendParametersSatellite()
		if modulation == 1:
			parm.modulation = 2 # eDVBFrontendParametersSatellite.Modulation.8PSK
		else:
			parm.modulation = 1 # eDVBFrontendParametersSatellite.Modulation.QPSK
		parm.system = system
		parm.frequency = frequency * 1000
		parm.symbol_rate = symbol_rate * 1000
		parm.polarisation = polarisation
		parm.fec = self.fecmap[fec]
		parm.inversion = inversion
		parm.orbital_position = int(orbital_position)
		tlist.append(parm)

	def addCabTransponder(self, tlist, frequency, symbol_rate, modulation, fec, inversion):
		print "Add Cab: frequ: " + str(frequency) + " symbol: " + str(symbol_rate) + " pol: " + str(modulation) + " fec: " + str(fec) + " inversion: " + str(inversion)
		parm = eDVBFrontendParametersCable()
		parm.frequency = frequency * 1000
		parm.symbol_rate = symbol_rate * 1000
		parm.modulation = modulation
		parm.fec = self.fecmap[fec]
		parm.inversion = inversion
		tlist.append(parm)

	def addTerTransponder(self, tlist, *args, **kwargs):
		tlist.append(buildTerTransponder(*args, **kwargs))

	def keyGo(self):
		tlist = []
		flags = None
		extFlags = True
		
		startScan = True
		index_to_scan = int(self.scan_nims.value)
		
		if self.scan_nims == [ ]:
			self.session.open(MessageBox, _("No tuner is enabled!\nPlease setup your tuner settings before you start a service scan."), MessageBox.TYPE_ERROR)
			return

		nim = nimmanager.nim_slots[index_to_scan]
		print "nim", nim.slot
		if nim.isCompatible("DVB-S"):
			print "is compatible with DVB-S"
			if self.scan_type.value == "single_transponder":
				# these lists are generated for each tuner, so this has work.
				assert len(self.satList) > index_to_scan
				assert len(self.scan_satselection) > index_to_scan
				
				nimsats = self.satList[index_to_scan]
				selsatidx = self.scan_satselection[index_to_scan].index

				# however, the satList itself could be empty. in that case, "index" is 0 (for "None").
				if len(nimsats):
					orbpos = nimsats[selsatidx][0]
					if self.scan_sat.system.value == "dvb-s":
						fec = self.scan_sat.fec.value
					else:
						fec = self.scan_sat.fec_s2.value
					print "add sat transponder"
					self.addSatTransponder(tlist, self.scan_sat.frequency.value,
								self.scan_sat.symbolrate.value,
								self.scan_sat.polarization.index,
								fec,
								self.scan_sat.inversion.index,
								orbpos,
								self.scan_sat.system.index,
								self.scan_sat.modulation.index)
				flags = self.scan_networkScan.value and eComponentScan.scanNetworkSearch or 0
				extFlags = False
			elif self.scan_type.value == "single_satellite":
				sat = self.satList[index_to_scan][self.scan_satselection[index_to_scan].index]
				getInitialTransponderList(tlist, sat[0])
			elif self.scan_type.value == "multisat":
				SatList = nimmanager.getSatListForNim(index_to_scan)
				for x in self.multiscanlist:
					if x[1].value:
						print "   " + str(x[0])
						getInitialTransponderList(tlist, x[0])

		elif nim.isCompatible("DVB-C"):
			if self.scan_typecable.value == "single_transponder":
				fec = self.scan_cab.fec.value
				self.addCabTransponder(tlist, self.scan_cab.frequency.value,
											  self.scan_cab.symbolrate.value,
											  self.scan_cab.modulation.index + 1,
											  fec,
											  self.scan_cab.inversion.index)
				flags = self.scan_networkScan.value and eComponentScan.scanNetworkSearch or 0
				extFlags = False
			elif self.scan_typecable.value == "complete":
				if config.Nims[index_to_scan].cable.scan_type.value == "provider":
					getInitialCableTransponderList(tlist, index_to_scan)
				else:
					startScan = False

		elif nim.isCompatible("DVB-T"):
			if self.scan_typeterrestrial.value == "single_transponder":
				self.addTerTransponder(tlist,
						self.scan_ter.frequency.value * 1000,
						inversion = self.scan_ter.inversion.index,
						bandwidth = self.scan_ter.bandwidth.index,
						fechigh = self.scan_ter.fechigh.index,
						feclow = self.scan_ter.feclow.index,
						modulation = self.scan_ter.modulation.index,
						transmission = self.scan_ter.transmission.index,
						guard = self.scan_ter.guard.index,
						hierarchy = self.scan_ter.hierarchy.index)
				flags = self.scan_networkScan.value and eComponentScan.scanNetworkSearch or 0
				extFlags = False
			elif self.scan_typeterrestrial.value == "complete":
				getInitialTerrestrialTransponderList(tlist, nimmanager.getTerrestrialDescription(index_to_scan))

		if flags is None:
			flags = eComponentScan.scanNetworkSearch

		if extFlags:
			tmp = self.scan_clearallservices.value
			if tmp == "yes":
				flags |= eComponentScan.scanRemoveServices
			elif tmp == "yes_hold_feeds":
				flags |= eComponentScan.scanRemoveServices
				flags |= eComponentScan.scanDontRemoveFeeds

		for x in self["config"].list:
			x[1].save()

		if startScan:
			self.startScan(tlist, flags, index_to_scan)
		else:
			self.flags = flags
			self.feid = index_to_scan
			self.tlist = []
			self.startCableTransponderSearch(self.feid)

	def setCableTransponderSearchResult(self, tlist):
		self.tlist = tlist

	def cableTransponderSearchFinished(self):
		self.startScan(self.tlist, self.flags, self.feid)

	def startScan(self, tlist, flags, feid):
		if len(tlist):
			# flags |= eComponentScan.scanSearchBAT
			self.session.open(ServiceScan, [{"transponders": tlist, "feid": feid, "flags": flags}])
		else:
			self.session.open(MessageBox, _("Nothing to scan!\nPlease setup your tuner settings before you start a service scan."), MessageBox.TYPE_ERROR)

	def keyCancel(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close()

class ScanSimple(ConfigListScreen, Screen, CableTransponderSearchSupport):
	def getNetworksForNim(self, nim):
		if nim.isCompatible("DVB-S"):
			networks = nimmanager.getSatListForNim(nim.slot)
# the original code took "loopthrough" etc. into account. Do we need this?
#			if nimmanager.getNimConfigMode(1) in ["loopthrough", "satposdepends", "equal", "nothing"]:
#				return False
#			sec = eDVBSatelliteEquipmentControl.getInstance()
#			if sec is not None:
#				exclusive_satellites = sec.get_exclusive_satellites(0,1)
#				if len(exclusive_satellites) == 2:
#					return False
#				idx = exclusive_satellites[0]+1
#				exclusive_nim_sats = exclusive_satellites[idx+1:idx+1+exclusive_satellites[idx]]
#				if len(exclusive_nim_sats):
#					return True
		elif not nim.empty:
			networks = [ nim.type ] # "DVB-C" or "DVB-T". TODO: seperate networks for different C/T tuners, if we want to support that.
		else:
			# empty tuners provide no networks.
			networks = [ ]
		return networks

	def __init__(self, session):
		Screen.__init__(self, session)

		self["actions"] = ActionMap(["SetupActions"],
		{
			"ok": self.keyGo,
			"cancel": self.keyCancel,
		}, -2)

		self.list = []
		tlist = []

		known_networks = [ ]
		nims_to_scan = [ ]

		for nim in nimmanager.nim_slots:
			# collect networks provided by this tuner

			need_scan = False
			networks = self.getNetworksForNim(nim)
			
			print "nim %d provides" % nim.slot, networks
			print "known:", known_networks

			# we only need to scan on the first tuner which provides a network.
			# this gives the first tuner for each network priority for scanning.
			for x in networks:
				if x not in known_networks:
					need_scan = True
					print x, "not in ", known_networks
					known_networks.append(x)

			if need_scan:
				nims_to_scan.append(nim)

		# we save the config elements to use them on keyGo
		self.nim_enable = [ ]

		if len(nims_to_scan):
			self.scan_clearallservices = ConfigSelection(default = "yes", choices = [("no", _("no")), ("yes", _("yes")), ("yes_hold_feeds", _("yes (keep feeds)"))])
			self.list.append(getConfigListEntry(_("Clear before scan"), self.scan_clearallservices))

			for nim in nims_to_scan:
				nimconfig = ConfigYesNo(default = True)
				nimconfig.nim_index = nim.slot
				self.nim_enable.append(nimconfig)
				self.list.append(getConfigListEntry(_("Scan ") + nim.slot_name + " (" + nim.friendly_type + ")", nimconfig))

		ConfigListScreen.__init__(self, self.list)
		self["header"] = Label(_("Automatic Scan"))
		self["footer"] = Label(_("Press OK to scan"))

	def run(self):
		self.keyGo()

	def keyGo(self):
		self.scanList = []
		self.known_networks = set()
		self.nim_iter=0
		self.buildTransponderList()

	def buildTransponderList(self): # this method is called multiple times because of asynchronous stuff
		print "buildTransponderList"
		APPEND_NOW = 0
		SEARCH_CABLE_TRANSPONDERS = 1
		action = APPEND_NOW

		n = self.nim_iter < len(self.nim_enable) and self.nim_enable[self.nim_iter] or None
		self.nim_iter += 1
		if n:
			if n.value: # check if nim is enabled
				flags = 0
				nim = nimmanager.nim_slots[n.nim_index]
				networks = set(self.getNetworksForNim(nim))

				# don't scan anything twice
				networks.discard(self.known_networks)

				tlist = [ ]
				if nim.isCompatible("DVB-S"):
					# get initial transponders for each satellite to be scanned
					for sat in networks:
						getInitialTransponderList(tlist, sat[0])
				elif nim.isCompatible("DVB-C"):
					if config.Nims[nim.slot].cable.scan_type.value == "provider":
						getInitialCableTransponderList(tlist, nim.slot)
					else:
						action = SEARCH_CABLE_TRANSPONDERS
				elif nim.isCompatible("DVB-T"):
					getInitialTerrestrialTransponderList(tlist, nimmanager.getTerrestrialDescription(nim.slot))
				else:
					assert False

				flags |= eComponentScan.scanNetworkSearch #FIXMEEE.. use flags from cables / satellites / terrestrial.xml
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
					self.startCableTransponderSearch(nim.slot)
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
			self.session.open(ServiceScan, scanList = scanList)
		else:
			self.session.open(MessageBox, _("Nothing to scan!\nPlease setup your tuner settings before you start a service scan."), MessageBox.TYPE_ERROR)

	def setCableTransponderSearchResult(self, tlist):
		self.scanList.append({"transponders": tlist, "feid": self.feid, "flags": self.flags})

	def cableTransponderSearchFinished(self):
		self.buildTransponderList()

	def keyCancel(self):
		self.close()

	def Satexists(self, tlist, pos):
		for x in tlist:
			if x == pos:
				return 1
		return 0

