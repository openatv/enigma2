from Screen import Screen
from ServiceScan import *
from Components.config import config, ConfigSubsection, ConfigSelection, ConfigYesNo, ConfigInteger, getConfigListEntry, ConfigSlider, ConfigSatlist, ConfigEnableDisable
from Components.ActionMap import NumberActionMap
from Components.ConfigList import ConfigList, ConfigListScreen
from Components.NimManager import nimmanager, getConfigSatlist
from Components.Label import Label
from Screens.MessageBox import MessageBox
from enigma import eTimer, eDVBFrontendParametersSatellite, eComponentScan, eDVBSatelliteEquipmentControl, eDVBFrontendParametersTerrestrial, eDVBFrontendParametersCable

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

def getInitialCableTransponderList(tlist, cable):
	list = nimmanager.getTranspondersCable(cable)

	symbolrates = [6900000, 6875000]
	modulations = [3, 5, 1, 2, 4] # QAM 64, 256, 16, 32, 128

	for x in list:
		if x[0] == 1: #CABLE
			for symbolrate in symbolrates:
				for modulation in modulations:
					parm = eDVBFrontendParametersCable()
					parm.frequency = x[1]
					parm.symbol_rate = symbolrate
					parm.modulation = modulation
					parm.fec_inner = 0
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


class ScanSetup(ConfigListScreen, Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		self.updateSatList()
		self.service = session.nav.getCurrentService()
		self.feinfo = None
		frontendData = None
		if self.service is not None:
			self.feinfo = self.service.frontendInfo()
			frontendData = self.feinfo and self.feinfo.getFrontendData(True)
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
		for slot in nimmanager.nimslots:
			if (nimmanager.getNimType(slot.slotid) == nimmanager.nimType["DVB-S"]):
				self.satList.append(nimmanager.getSatListForNim(slot.slotid))
			else:
				self.satList.append(None)
				
	def createSetup(self):
		self.list = []
		self.multiscanlist = []
		print "ID: ", self.scan_nims.index

		self.tunerEntry = getConfigListEntry(_("Tuner"), self.scan_nims)
		self.list.append(self.tunerEntry)
		
		self.typeOfScanEntry = None
		self.systemEntry = None
		if nimmanager.getNimType(self.scan_nims.index) == nimmanager.nimType["DVB-S"]:
			self.typeOfScanEntry = getConfigListEntry(_("Type of scan"), self.scan_type)
			self.list.append(self.typeOfScanEntry)
		elif nimmanager.getNimType(self.scan_nims.index) == nimmanager.nimType["DVB-C"]:
			self.typeOfScanEntry = getConfigListEntry(_("Type of scan"), self.scan_typecable)
			self.list.append(self.typeOfScanEntry)
		elif nimmanager.getNimType(self.scan_nims.index) == nimmanager.nimType["DVB-T"]:
			self.typeOfScanEntry = getConfigListEntry(_("Type of scan"), self.scan_typeterrestrial)
			self.list.append(self.typeOfScanEntry)

		if nimmanager.getNimType(self.scan_nims.index) == nimmanager.nimType["DVB-S"]:

			if self.scan_type.value == "single_transponder":
				self.systemEntry = getConfigListEntry(_('Transpondertype'), self.scan_sat.system)
				self.list.append(self.systemEntry)
				self.list.append(getConfigListEntry(_('Satellite'), self.scan_satselection[self.scan_nims.index]))
				self.list.append(getConfigListEntry(_('Frequency'), self.scan_sat.frequency))
				self.list.append(getConfigListEntry(_('Inversion'), self.scan_sat.inversion))
				self.list.append(getConfigListEntry(_('Symbol Rate'), self.scan_sat.symbolrate))
				self.list.append(getConfigListEntry(_("Polarity"), self.scan_sat.polarization))
				if self.scan_sat.system.value == "dvb-s":
					self.list.append(getConfigListEntry(_("FEC"), self.scan_sat.fec))
				elif self.scan_sat.system.value == "dvb-s2":
					self.list.append(getConfigListEntry(_("FEC"), self.scan_sat.fec_s2))
					self.list.append(getConfigListEntry(_('Modulation'), self.scan_sat.modulation))
			elif self.scan_type.value == "single_satellite":
				self.updateSatList()
				print self.scan_satselection[self.scan_nims.index]
				self.list.append(getConfigListEntry(_("Satellite"), self.scan_satselection[self.scan_nims.index]))
				self.list.append(getConfigListEntry(_("Clear before scan"), self.scan_clearallservices))
			elif self.scan_type.value == "multisat":
				# if (norotor)
				tlist = []
				SatList = nimmanager.getSatListForNim(self.scan_nims.index)
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


		if nimmanager.getNimType(self.scan_nims.index) == nimmanager.nimType["DVB-C"]:
			if self.scan_typecable.value == "single_transponder":
				self.list.append(getConfigListEntry(_("Frequency"), self.scan_cab.frequency))
				self.list.append(getConfigListEntry(_("Inversion"), self.scan_cab.inversion))
				self.list.append(getConfigListEntry(_("Symbol Rate"), self.scan_cab.symbolrate))
				self.list.append(getConfigListEntry(_("Modulation"), self.scan_cab.modulation))
				self.list.append(getConfigListEntry(_("FEC"), self.scan_cab.fec))
				self.list.append(getConfigListEntry(_("Network scan"), self.scan_cab.networkScan))
			elif self.scan_typecable.value == "complete":
				self.list.append(getConfigListEntry(_("Clear before scan"), self.scan_clearallservices))
				
		if nimmanager.getNimType(self.scan_nims.index) == nimmanager.nimType["DVB-T"]:
			if self.scan_typeterrestrial.value == "single_transponder":
				self.list.append(getConfigListEntry(_("Frequency"), self.scan_ter.frequency))
				self.list.append(getConfigListEntry(_("Network scan"), self.scan_ter.networkScan))
				self.list.append(getConfigListEntry(_("Inversion"), self.scan_ter.inversion))
				self.list.append(getConfigListEntry(_("Bandwidth"), self.scan_ter.bandwidth))
				self.list.append(getConfigListEntry(_("Code rate high"), self.scan_ter.fechigh))
				self.list.append(getConfigListEntry(_("Code rate low"), self.scan_ter.feclow))
				self.list.append(getConfigListEntry(_("Modulation"), self.scan_ter.modulation))
				self.list.append(getConfigListEntry(_("Transmission mode"), self.scan_ter.transmission))
				self.list.append(getConfigListEntry(_("Guard interval mode"), self.scan_ter.guard))
				self.list.append(getConfigListEntry(_("Hierarchy mode"), self.scan_ter.hierarchy))
			elif self.scan_typeterrestrial.value == "complete":
				self.list.append(getConfigListEntry(_("Clear before scan"), self.scan_clearallservices))

#		if (nimmanager.getNimType(self.scan_nims.index) == nimmanager.nimType["DVB-S"] and self.scan_type.type == "single_transponder") or \
#			(nimmanager.getNimType(self.scan_nims.index) == nimmanager.nimType["DVB-C"] and self.scan_typecable.type == "single_transponder") or \
#			(nimmanager.getNimType(self.scan_nims.index) == nimmanager.nimType["DVB-T"] and self.scan_typeterrestrial.type == "single_transponder"):
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
		print self["config"].getCurrent()
		if self["config"].getCurrent() == self.typeOfScanEntry:
			self.createSetup()
		elif self["config"].getCurrent() == self.tunerEntry:
			self.createSetup()
		elif self["config"].getCurrent() == self.systemEntry:
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
				if frontendData["tuner_type"] == "DVB-S":
					defaultSat["system"] = {"DVB-S": "dvb-s", "DVB-S2": "dvb-s2"}[frontendData["system"]]
					defaultSat["frequency"] = int(frontendData["frequency"] / 1000)
					defaultSat["inversion"] = {"INVERSION_OFF": "off", "INVERSION_ON": "on", "INVERSION_AUTO": "auto"}[frontendData["inversion"]]
					defaultSat["symbolrate"] = int(frontendData["symbol_rate"] / 1000)
					defaultSat["polarization"] = {"HORIZONTAL": "horizontal", "VERTICAL": "vertical", "CIRCULAR_LEFT": "circular_left", "CIRCULAR_RIGHT": "circular_right", "UNKNOWN": None}[frontendData["polarization"]]
					defaultSat["fec"] = {"DVB-S": {"FEC_AUTO": "auto", "FEC_1_2": "1_2", "FEC_2_3": "2_3", "FEC_3_4": "3_4", "FEC_5_6": "5_6", "FEC_7_8": "7_8", "FEC_NONE": "none"}, "DVB-S2": {"FEC_1_2": "1_2", "FEC_2_3": "2_3", "FEC_3_4": "3_4", "FEC_4_5": "4_5", "FEC_5_6": "5_6", "FEC_7_8": "7_8", "FEC_8_9": "8_9", "FEC_9_10": "9_10"}}[frontendData["system"]][frontendData["fec_inner"]]
					defaultSat["modulation"] = {"QPSK": "qpsk", "8PSK": "8psk"}[frontendData["modulation"]]
					defaultSat["orbpos"] = frontendData["orbital_position"]
				elif frontendData["tuner_type"] == "DVB-C":
					defaultCab["frequency"] = int(frontendData["frequency"] / 1000)
					defaultCab["symbolrate"] = int(frontendData["symbol_rate"] / 1000)
					defaultCab["inversion"] = {"INVERSION_OFF": "off", "INVERSION_ON": "on", "INVERSION_AUTO": "auto"}[frontendData["inversion"]]
					defaultCab["fec"] = {"FEC_AUTO": "auto", "FEC_1_2": "1_2", "FEC_2_3": "2_3", "FEC_3_4": "3_4", "FEC_5_6": "5_6", "FEC_7_8": "7_8", "FEC_8_9": "8_9", "FEC_NONE": "none"}[frontendData["fec_inner"]]
					defaultCab["modulation"] = {"QAM_AUTO": "auto", "QAM_16": "16qam", "QAM_32": "32qam", "QAM_64": "64qam", "QAM_128": "128qam", "QAM_256": "256qam"}[frontendData["modulation"]]

			self.scan_sat = ConfigSubsection()
			self.scan_cab = ConfigSubsection()
			self.scan_ter = ConfigSubsection()

			self.scan_type = ConfigSelection(default = "single_transponder", choices = [("single_transponder", _("Single transponder")), ("single_satellite", _("Single satellite")), ("multisat", _("Multisat"))])
			self.scan_typecable = ConfigSelection(default = "single_transponder", choices = [("single_transponder", _("Single transponder")), ("complete", _("Complete"))])
			self.scan_typeterrestrial = ConfigSelection(default = "single_transponder", choices = [("single_transponder", _("Single transponder")), ("complete", _("Complete"))])
			self.scan_clearallservices = ConfigSelection(default = "no", choices = [("no", _("no")), ("yes", _("yes")), ("yes_hold_feeds", _("yes (keep feeds)"))])

			nimList = [ ]
			for nim in nimmanager.nimList():
				nimList.append(nim[0])
			#nimList.append("all")
			self.scan_nims = ConfigSelection(choices = nimList)
			
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
			self.scan_cab.networkScan = ConfigYesNo(default = False)

			# terrestial
			self.scan_ter.frequency = ConfigInteger(default = 466, limits = (100, 999))
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
			self.scan_ter.networkScan = ConfigYesNo(default = False)

			self.scan_scansat = {}
			for sat in nimmanager.satList:
				#print sat[1]
				self.scan_scansat[sat[0]] = ConfigYesNo(default = False)

			self.scan_satselection = []
			slotid = 0
			for slot in nimmanager.nimslots:
				if (nimmanager.getNimType(slot.slotid) == nimmanager.nimType["DVB-S"]):
					print str(slot.slotid) + " : " + str(self.satList)
					self.scan_satselection.append(getConfigSatlist(defaultSat["orbpos"],self.satList[slot.slotid]))
				else:
					self.scan_satselection.append(None)

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
		flags = 0
		if nimmanager.getNimType(self.scan_nims.index) == nimmanager.nimType["DVB-S"]:
			if self.scan_type.value == "single_transponder":
				l = len(self.satList)
				if l and l > self.scan_nims.index:
					nimsats=self.satList[self.scan_nims.index]
					l = len(self.scan_satselection)
					if l and l > self.scan_nims.index:
						selsatidx=self.scan_satselection[self.scan_nims.index].index
						l = len(nimsats)
						if l and l > selsatidx:
							orbpos=nimsats[selsatidx][0]
							if self.scan_sat.system.value == "dvb-s":
								fec = self.scan_sat.fec.value
							else:
								fec = self.scan_sat.fec_s2.value
							self.addSatTransponder(tlist, self.scan_sat.frequency.value,
										self.scan_sat.symbolrate.value,
										self.scan_sat.polarization.index,
										fec,
										self.scan_sat.inversion.index,
										orbpos,
										self.scan_sat.system.index,
										self.scan_sat.modulation.index)
			elif self.scan_type.value == "single_satellite":
				sat = self.satList[self.scan_nims.index][self.scan_satselection[self.scan_nims.index].index]
				getInitialTransponderList(tlist, sat[0])
				if sat[2] & 1:
					flags |= eComponentScan.scanNetworkSearch
				tmp = self.scan_clearallservices.value
				if tmp == "yes":
					flags |= eComponentScan.scanRemoveServices
				elif tmp == "yes_hold_feeds":
					flags |= eComponentScan.scanRemoveServices
					flags |= eComponentScan.scanDontRemoveFeeds
			elif self.scan_type.value == "multisat":
				SatList = nimmanager.getSatListForNim(self.scan_nims.index)
				for x in self.multiscanlist:
					if x[1].value:
						print "   " + str(x[0])
						getInitialTransponderList(tlist, x[0])
				flags |= eComponentScan.scanNetworkSearch
				tmp = self.scan_clearallservices.value
				if tmp == "yes":
					flags |= eComponentScan.scanRemoveServices
				elif tmp == "yes_hold_feeds":
					flags |= eComponentScan.scanRemoveServices
					flags |= eComponentScan.scanDontRemoveFeeds

		elif (nimmanager.getNimType(self.scan_nims.index) == nimmanager.nimType["DVB-C"]):
			if self.scan_typecable.value == "single_transponder":
				fec = self.scan_cab.fec.value
				self.addCabTransponder(tlist, self.scan_cab.frequency.value,
											  self.scan_cab.symbolrate.value,
											  self.scan_cab.modulation.index + 1,
											  fec,
											  self.scan_cab.inversion.index)
				if self.scan_cab.networkScan.value:
					flags |= eComponentScan.scanNetworkSearch
			elif self.scan_typecable.value == "complete":
				getInitialCableTransponderList(tlist, nimmanager.getCableDescription(self.scan_nims.index))
				flags |= eComponentScan.scanNetworkSearch
				tmp = self.scan_clearallservices
				if tmp == "yes":
					flags |= eComponentScan.scanRemoveServices
				elif tmp == "yes_hold_feeds":
					flags |= eComponentScan.scanRemoveServices
					flags |= eComponentScan.scanDontRemoveFeeds

		elif (nimmanager.getNimType(self.scan_nims.index) == nimmanager.nimType["DVB-T"]):
			if self.scan_typeterrestrial.value == "single_transponder":
				self.addTerTransponder(tlist,
						self.scan_ter.frequency.value * 1000000,
						inversion = self.scan_ter.inversion.index,
						bandwidth = self.scan_ter.bandwidth.index,
						fechigh = self.scan_ter.fechigh.index,
						feclow = self.scan_ter.feclow.index,
						modulation = self.scan_ter.modulation.index,
						transmission = self.scan_ter.transmission.index,
						guard = self.scan_ter.guard.index,
						hierarchy = self.scan_ter.hierarchy.index)
				if self.scan_ter.networkScan.value:
					flags |= eComponentScan.scanNetworkSearch
			elif self.scan_typeterrestrial.value == "complete":
				getInitialTerrestrialTransponderList(tlist, nimmanager.getTerrestrialDescription(self.scan_nims.index))
				flags |= eComponentScan.scanNetworkSearch
				tmp = self.scan_clearallservices.value
				if tmp == "yes":
					flags |= eComponentScan.scanRemoveServices
				elif tmp == "yes_hold_feeds":
					flags |= eComponentScan.scanRemoveServices
					flags |= eComponentScan.scanDontRemoveFeeds

		for x in self["config"].list:
			x[1].save()

		if len(tlist):
			feid = self.scan_nims.index
			# flags |= eComponentScan.scanSearchBAT
			self.session.openWithCallback(self.doNothing, ServiceScan, [{"transponders": tlist, "feid": feid, "flags": flags}])
		else:
			self.session.open(MessageBox, _("Nothing to scan!\nPlease setup your tuner settings before you start a service scan."), MessageBox.TYPE_ERROR)

	def doNothing(self):
		pass

	def keyCancel(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close()

class ScanSimple(ConfigListScreen, Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		self["actions"] = ActionMap(["SetupActions"],
		{
			"ok": self.keyGo,
			"cancel": self.keyCancel,
		}, -2)

		self.list = []
		tlist = []

		nimcount = nimmanager.getNimSocketCount()
		if nimcount > 0:
			nimtype = nimmanager.getNimType(0)
			scan_possible=True
			self.scan_clearallservices = ConfigSelection(default = "yes", choices = [("no", _("no")), ("yes", _("yes")), ("yes_hold_feeds", _("yes (keep feeds)"))])
			self.list.append(getConfigListEntry(_("Clear before scan"), self.scan_clearallservices))
			nim = ConfigYesNo(default = True)
			nim.nim_index = 0
			if nimtype == nimmanager.nimType["DVB-S"] and not len(nimmanager.getSatListForNim(0)):
				scan_possible=False
			if nimtype == nimmanager.nimType["empty/unknown"]:
				scan_possible = False
			if scan_possible:
				self.list.append(getConfigListEntry(_("Scan NIM") + " 0 (" + nimmanager.getNimTypeName(0) + ")", nim))

		if nimcount > 1 and self.ScanNimTwoNeeded():
			nim = ConfigYesNo(default = True)
			nim.nim_index = 1
			self.list.append(getConfigListEntry(_("Scan NIM") + " 1 (" + nimmanager.getNimTypeName(1) + ")", nim))

		ConfigListScreen.__init__(self, self.list)
		self["header"] = Label(_("Automatic Scan"))
		self["footer"] = Label(_("Press OK to scan"))

	def run(self):
		self.keyGo()

	def keyGo(self):
		scanList = []
		if nimmanager.getNimType(0) == nimmanager.nimType["DVB-S"] and nimmanager.getNimType(0) == nimmanager.getNimType(1):
			sec = eDVBSatelliteEquipmentControl.getInstance()
			if sec is not None:
				exclusive_satellites = sec.get_exclusive_satellites(0,1)
			else:
				exclusive_satellites = [0,0]
			print "exclusive satellites", exclusive_satellites
			two_sat_tuners = True
		else:
			two_sat_tuners = False

		for (x, c) in self.list[1:]:
			slotid = c.nim_index
			print "Scan Tuner", slotid, "-", c.value
			if c.value:
				scanPossible = False
				trustNit = False
				tlist = [ ]
				if nimmanager.getNimType(slotid) == nimmanager.nimType["DVB-S"]:
					print "is sat"
					if two_sat_tuners:
						if slotid > 0:
							idx = exclusive_satellites[0]+1
						else:
							idx = 0
						exclusive_nim_sats = exclusive_satellites[idx+1:idx+1+exclusive_satellites[idx]]
						print "exclusive_nim_sats", exclusive_nim_sats
					SatList = nimmanager.getSatListForNim(slotid)
					for sat in SatList:
						if not two_sat_tuners or (sat[0] in exclusive_nim_sats or slotid == 0):
							scanPossible = True
							print sat
							getInitialTransponderList(tlist, sat[0])
				elif nimmanager.getNimType(slotid) == nimmanager.nimType["DVB-C"]:
					scanPossible = True
					getInitialCableTransponderList(tlist, nimmanager.getCableDescription(slotid))
					if nimmanager.getCableTrustNit(slotid):
						trustNit = True
				elif nimmanager.getNimType(slotid) == nimmanager.nimType["DVB-T"]:
					scanPossible = True
					getInitialTerrestrialTransponderList(tlist, nimmanager.getTerrestrialDescription(slotid))
				else:
					assert False

				if scanPossible:
					flags=eComponentScan.scanNetworkSearch
					if trustNit:
						flags |= eComponentScan.clearToScanOnFirstNIT
					tmp = self.scan_clearallservices.value
					if tmp == "yes":
						flags |= eComponentScan.scanRemoveServices
					elif tmp == "yes_hold_feeds":
						flags |= eComponentScan.scanRemoveServices
						flags |= eComponentScan.scanDontRemoveFeeds
					scanList.append({"transponders": tlist, "feid": slotid, "flags": flags})
		if len(scanList):
			self.session.openWithCallback(self.doNothing, ServiceScan, scanList = scanList)
		else:
			self.session.open(MessageBox, _("Nothing to scan!\nPlease setup your tuner settings before you start a service scan."), MessageBox.TYPE_ERROR)

	def doNothing(self):
		pass

	def keyCancel(self):
		self.close()

	def Satexists(self, tlist, pos):
		for x in tlist:
			if x == pos:
				return 1
		return 0

	def ScanNimTwoNeeded(self):
		if nimmanager.getNimType(1) == nimmanager.nimType["empty/unknown"]:
			return False
		if nimmanager.getNimType(0) != nimmanager.getNimType(1):
			return True
		if nimmanager.getNimType(0) == nimmanager.nimType["DVB-S"]: #two dvb-s nims
			if nimmanager.getNimConfigMode(1) in ["loopthrough", "satposdepends", "equal", "nothing"]:
				return False
			sec = eDVBSatelliteEquipmentControl.getInstance()
			if sec is not None:
				exclusive_satellites = sec.get_exclusive_satellites(0,1)
				if len(exclusive_satellites) == 2:
					return False
				idx = exclusive_satellites[0]+1
				exclusive_nim_sats = exclusive_satellites[idx+1:idx+1+exclusive_satellites[idx]]
				if len(exclusive_nim_sats):
					return True
		return False # two -C or two -T tuners

