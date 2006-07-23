from Screen import Screen
from ServiceScan import *
from Components.config import *
from Components.ActionMap import NumberActionMap
from Components.ConfigList import ConfigList
from Components.NimManager import nimmanager
from Components.Label import Label
from Screens.MessageBox import MessageBox
from enigma import eDVBFrontendParametersSatellite, eComponentScan, eDVBSatelliteEquipmentControl, eDVBFrontendParametersTerrestrial

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

	for x in list:
		if x[0] == 1: #CABLE
			parm = eDVBFrontendParametersCable()
			parm.frequency = x[1]
			parm.symbol_rate = x[2]
			parm.modulation = x[3]
			parm.fec_inner = x[4]
			parm.inversion = 2 # AUTO
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


class ScanSetup(Screen):
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
			"left": self.keyLeft,
			"right": self.keyRight,
			"1": self.keyNumberGlobal,
			"2": self.keyNumberGlobal,
			"3": self.keyNumberGlobal,
			"4": self.keyNumberGlobal,
			"5": self.keyNumberGlobal,
			"6": self.keyNumberGlobal,
			"7": self.keyNumberGlobal,
			"8": self.keyNumberGlobal,
			"9": self.keyNumberGlobal,
			"0": self.keyNumberGlobal
		}, -1)
		
		self.statusTimer = eTimer()
		self.statusTimer.timeout.get().append(self.updateStatus)
		#self.statusTimer.start(5000, True)

		self.list = []
		self["config"] = ConfigList(self.list)
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
		print "ID: " + str(config.scan.nims.value)

		self.tunerEntry = getConfigListEntry(_("Tuner"), config.scan.nims)
		self.list.append(self.tunerEntry)
		
		self.typeOfScanEntry = None
		self.systemEntry = None
		if (nimmanager.getNimType(config.scan.nims.value) == nimmanager.nimType["DVB-S"]):
			self.typeOfScanEntry = getConfigListEntry(_("Type of scan"), config.scan.type)
			self.list.append(self.typeOfScanEntry)
		elif (nimmanager.getNimType(config.scan.nims.value) == nimmanager.nimType["DVB-C"]):
			self.typeOfScanEntry = getConfigListEntry(_("Type of scan"), config.scan.typecable)
			self.list.append(self.typeOfScanEntry)
		elif (nimmanager.getNimType(config.scan.nims.value) == nimmanager.nimType["DVB-T"]):
			self.typeOfScanEntry = getConfigListEntry(_("Type of scan"), config.scan.typeterrestrial)
			self.list.append(self.typeOfScanEntry)


		if (nimmanager.getNimType(config.scan.nims.value) == nimmanager.nimType["DVB-S"]):

			if currentConfigSelectionElement(config.scan.type) == "single_transponder":
				self.systemEntry = getConfigListEntry(_('Transpondertype'), config.scan.sat.system)
				self.list.append(self.systemEntry)
				self.list.append(getConfigListEntry(_('Satellite'), config.scan.satselection[config.scan.nims.value]))
				self.list.append(getConfigListEntry(_('Frequency'), config.scan.sat.frequency))
				self.list.append(getConfigListEntry(_('Inversion'), config.scan.sat.inversion))
				self.list.append(getConfigListEntry(_('Symbol Rate'), config.scan.sat.symbolrate))
				self.list.append(getConfigListEntry(_("Polarity"), config.scan.sat.polarization))
				if currentConfigSelectionElement(config.scan.sat.system) == "dvb-s":
					self.list.append(getConfigListEntry(_("FEC"), config.scan.sat.fec))
				elif currentConfigSelectionElement(config.scan.sat.system) == "dvb-s2":
					self.list.append(getConfigListEntry(_("FEC"), config.scan.sat.fec_s2))
					self.list.append(getConfigListEntry(_('Modulation'), config.scan.sat.modulation))
			elif currentConfigSelectionElement(config.scan.type) == "single_satellite":
				self.updateSatList()
				print config.scan.satselection[config.scan.nims.value]
				self.list.append(getConfigListEntry(_("Satellite"), config.scan.satselection[config.scan.nims.value]))
				self.list.append(getConfigListEntry(_("Clear before scan"), config.scan.clearallservices))
			elif currentConfigSelectionElement(config.scan.type) == "multisat":
				# if (norotor)
				tlist = []
				SatList = nimmanager.getSatListForNim(config.scan.nims.value)
				self.list.append(getConfigListEntry(_("Clear before scan"), config.scan.clearallservices))
				for x in SatList:
					if self.Satexists(tlist, x[1]) == 0:
						tlist.append(x[1])
						sat = configElement_nonSave(x[1], configSelection, 0, (("enable", _("Enable")), ("disable", _("Disable"))))
						configEntry = getConfigListEntry(nimmanager.getSatDescription(x[1]), sat)
						self.list.append(configEntry)
						self.multiscanlist.append(configEntry)
				# if (rotor):
    			   # for sat in nimmanager.satList:
				#	self.list.append(getConfigListEntry(sat[0], config.scan.scansat[sat[1]]))


		if (nimmanager.getNimType(config.scan.nims.value) == nimmanager.nimType["DVB-C"]):
			if currentConfigSelectionElement(config.scan.typecable) == "single_transponder":
				self.list.append(getConfigListEntry(_("Frequency"), config.scan.cab.frequency))
				self.list.append(getConfigListEntry(_("Inversion"), config.scan.cab.inversion))
				self.list.append(getConfigListEntry(_("Symbol Rate"), config.scan.cab.symbolrate))
				self.list.append(getConfigListEntry(_("Modulation"), config.scan.cab.modulation))
				self.list.append(getConfigListEntry(_("FEC"), config.scan.cab.fec))
				self.list.append(getConfigListEntry(_("Network scan"), config.scan.cab.networkScan))
			elif currentConfigSelectionElement(config.scan.typecable) == "complete":
				self.list.append(getConfigListEntry(_("Clear before scan"), config.scan.clearallservices))
				
		if (nimmanager.getNimType(config.scan.nims.value) == nimmanager.nimType["DVB-T"]):
			if currentConfigSelectionElement(config.scan.typeterrestrial) == "single_transponder":
				self.list.append(getConfigListEntry(_("Frequency"), config.scan.ter.frequency))
				self.list.append(getConfigListEntry(_("Network scan"), config.scan.ter.networkScan))
				self.list.append(getConfigListEntry(_("Inversion"), config.scan.ter.inversion))
				self.list.append(getConfigListEntry(_("Bandwidth"), config.scan.ter.bandwidth))
				self.list.append(getConfigListEntry(_("Code rate high"), config.scan.ter.fechigh))
				self.list.append(getConfigListEntry(_("Code rate low"), config.scan.ter.feclow))
				self.list.append(getConfigListEntry(_("Modulation"), config.scan.ter.modulation))
				self.list.append(getConfigListEntry(_("Transmission mode"), config.scan.ter.transmission))
				self.list.append(getConfigListEntry(_("Guard interval mode"), config.scan.ter.guard))
				self.list.append(getConfigListEntry(_("Hierarchy mode"), config.scan.ter.hierarchy))
			elif currentConfigSelectionElement(config.scan.typeterrestrial) == "complete":
				self.list.append(getConfigListEntry(_("Clear before scan"), config.scan.clearallservices))

#		if (nimmanager.getNimType(config.scan.nims.value) == nimmanager.nimType["DVB-S"] and currentConfigSelectionElement(config.scan.type) == "single_transponder") or \
#			(nimmanager.getNimType(config.scan.nims.value) == nimmanager.nimType["DVB-C"] and currentConfigSelectionElement(config.scan.typecable) == "single_transponder") or \
#			(nimmanager.getNimType(config.scan.nims.value) == nimmanager.nimType["DVB-T"] and currentConfigSelectionElement(config.scan.typeterrestrial) == "single_transponder"):
#				self.configElementSNR = getConfigListEntry(_("SNR"), config.scan.snr)
#				self.list.append(self.configElementSNR)
#				self.configElementACG = getConfigListEntry(_("AGC"), config.scan.agc)
#				self.list.append(self.configElementACG)
#				self.configElementBER = getConfigListEntry(_("BER"), config.scan.ber)
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
			defaultSat = { "orbpos": 192, "system": 0, "frequency": [11836], "inversion": 2, "symbolrate": [27500], "polarization": 0, "fec": 0, "fec_s2": 8, "modulation": 0 }
			defaultCab = {"frequency": [466], "inversion": 2, "modulation": 2, "fec": 0, "symbolrate": [6900]}
			if frontendData is not None:
				if frontendData["tuner_type"] == "DVB-S":
					defaultSat["system"] = {"DVB-S": 0, "DVB-S2": 1}[frontendData["system"]]
					defaultSat["frequency"] = [int(frontendData["frequency"] / 1000)]
					defaultSat["inversion"] = {"INVERSION_OFF": 0, "INVERSION_ON": 1, "INVERSION_AUTO": 2}[frontendData["inversion"]]
					defaultSat["symbolrate"] = [int(frontendData["symbol_rate"] / 1000)]
					defaultSat["polarization"] = {"HORIZONTAL": 0, "VERTICAL": 1, "CIRCULAR_LEFT": 2, "CIRCULAR_RIGHT": 3, "UNKNOWN": 0}[frontendData["polarization"]]
					defaultSat["fec"] = {"DVB-S": {"FEC_AUTO": 0, "FEC_1_2": 1, "FEC_2_3": 2, "FEC_3_4": 3, "FEC_5_6": 4, "FEC_7_8": 5, "FEC_NONE": 6}, "DVB-S2": {"FEC_1_2": 0, "FEC_2_3": 1, "FEC_3_4": 2, "FEC_4_5": 3, "FEC_5_6": 4, "FEC_7_8": 5, "FEC_8_9": 6, "FEC_9_10": 7}}[frontendData["system"]][frontendData["fec_inner"]]
					defaultSat["modulation"] = {"QPSK": 0, "8PSK": 1}[frontendData["modulation"]]
					defaultSat["orbpos"] = frontendData["orbital_position"]
				elif frontendData["tuner_type"] == "DVB-C":
					defaultCab["frequency"] = [int(frontendData["frequency"] / 1000)]
					defaultCab["symbolrate"] = [int(frontendData["symbol_rate"] / 1000)]
					defaultSat["inversion"] = {"INVERSION_OFF": 0, "INVERSION_ON": 1, "INVERSION_AUTO": 2}[frontendData["inversion"]]
					defaultSat["fec"] = {"FEC_AUTO": 0, "FEC_1_2": 1, "FEC_2_3": 2, "FEC_3_4": 3, "FEC_5_6": 4, "FEC_7_8": 5, "FEC_8_9": 6, "FEC_NONE": 7}[frontendData["fec_inner"]]
					defaultSat["modulation"] = {"QAM_AUTO": 0, "QAM_16": 1, "QAM_16": 2, "QAM_32": 3, "QAM_64": 4, "QAM_128": 5, "QAM_256": 6}[frontendData["modulation"]]
										
			config.scan = ConfigSubsection()
			config.scan.sat = ConfigSubsection()
			config.scan.cab = ConfigSubsection()
			config.scan.ter = ConfigSubsection()

			config.scan.type = configElement_nonSave("config.scan.type", configSelection, 0, (("single_transponder", _("Single transponder")), ("single_satellite", _("Single satellite")), ("multisat", _("Multisat"))))
			config.scan.typecable = configElement_nonSave("config.scan.typecable", configSelection, 0, (("single_transponder", _("Single transponder")), ("complete", _("Complete"))))
			config.scan.typeterrestrial = configElement_nonSave("config.scan.typeterrestrial", configSelection, 0, (("single_transponder", _("Single transponder")), ("complete", _("Complete"))))
			config.scan.clearallservices = configElement_nonSave("config.scan.clearallservices", configSelection, 0, (("no", _("no")), ("yes", _("yes")), ("yes_hold_feeds", _("yes (keep feeds)"))))

			nimList = [ ]
			for nim in nimmanager.nimList():
				nimList.append(nim[0])
			#nimList.append("all")
			config.scan.nims = configElement_nonSave("config.scan.nims", configSelection, 0, nimList)
			
			# status
			config.scan.snr = configElement_nonSave("config.scan.snr", configSlider, 0, (1, 100))
			config.scan.snr.enabled = False
			config.scan.agc = configElement_nonSave("config.scan.agc", configSlider, 0, (1, 100))
			config.scan.agc.enabled = False
			config.scan.ber = configElement_nonSave("config.scan.ber", configSlider, 0, (1, 100))
			config.scan.ber.enabled = False

			# sat
			config.scan.sat.system = configElement_nonSave("config.scan.sat.system", configSelection, defaultSat["system"], (("dvb-s", _("DVB-S")), ("dvb-s2", _("DVB-S2"))))
			config.scan.sat.frequency = configElement_nonSave("config.scan.sat.frequency", configSequence, defaultSat["frequency"], configsequencearg.get("INTEGER", (1, 99999)))
			config.scan.sat.inversion = configElement_nonSave("config.scan.sat.inversion", configSelection, defaultSat["inversion"], (("off", _("off")), ("on", _("on")), ("auto", _("Auto"))))
			config.scan.sat.symbolrate = configElement_nonSave("config.scan.sat.symbolrate", configSequence, defaultSat["symbolrate"], configsequencearg.get("INTEGER", (1, 99999)))
			config.scan.sat.polarization = configElement_nonSave("config.scan.sat.polarization", configSelection, defaultSat["polarization"], (("horizontal", _("horizontal")), ("vertical", _("vertical")),  ("circular_left", _("circular left")), ("circular_right", _("circular right"))))
			config.scan.sat.fec = configElement_nonSave("config.scan.sat.fec", configSelection, defaultSat["fec"], (("auto", _("Auto")), ("1_2", "1/2"), ("2_3", "2/3"), ("3_4", "3/4"), ("5_6", "5/6"), ("7_8", "7/8"), ("none", _("None"))))
			config.scan.sat.fec_s2 = configElement_nonSave("config.scan.sat.fec_s2", configSelection, defaultSat["fec_s2"], (("1_2", "1/2"), ("2_3", "2/3"), ("3_4", "3/4"), ("3_5", "3/5"), ("4_5", "4/5"), ("5_6", "5/6"), ("7_8", "7/8"), ("8_9", "8/9"), ("9_10", "9/10")))
			config.scan.sat.modulation = configElement_nonSave("config.scan.sat.modulation", configSelection, defaultSat["modulation"], (("qpsk", "QPSK"), ("8psk", "8PSK")))
	
			# cable
			config.scan.cab.frequency = configElement_nonSave("config.scan.cab.frequency", configSequence, defaultCab["frequency"], configsequencearg.get("INTEGER", (50, 999)))
			config.scan.cab.inversion = configElement_nonSave("config.scan.cab.inversion", configSelection, defaultCab["inversion"], (("off", _("off")), ("on", _("on")), ("auto", _("Auto"))))
			config.scan.cab.modulation = configElement_nonSave("config.scan.cab.modulation", configSelection, defaultCab["modulation"], (("16qam", "16-QAM"), ("32qam", "32-QAM"), ("64qam", "64-QAM"), ("128qam", "128-QAM"), ("256qam", "256-QAM")))
			config.scan.cab.fec = configElement_nonSave("config.scan.cab.fec", configSelection, defaultCab["fec"], (("auto", _("Auto")), ("1_2", "1/2"), ("2_3", "2/3"), ("3_4", "3/4"), ("5_6", "5/6"), ("7_8", "7/8"), ("8_9", "8/9"), ("none", _("None"))))
			config.scan.cab.symbolrate = configElement_nonSave("config.scan.cab.symbolrate", configSequence, defaultCab["symbolrate"], configsequencearg.get("INTEGER", (1, 9999)))
			config.scan.cab.networkScan = configElement_nonSave("config.scan.cab.networkScan", configSelection, 0, (("no", _("no")), ("yes", _("yes"))))

			# terrestial
			config.scan.ter.frequency = configElement_nonSave("config.scan.ter.frequency", configSequence, [466], configsequencearg.get("INTEGER", (100, 900)))
			config.scan.ter.inversion = configElement_nonSave("config.scan.ter.inversion", configSelection, 2, (("off", _("off")), ("on", _("on")), ("auto", _("Auto"))))
			# WORKAROUND: we can't use BW-auto
			config.scan.ter.bandwidth = configElement_nonSave("config.scan.ter.bandwidth", configSelection, 0, (("8MHz", "8MHz"), ("7MHz", "7MHz"), ("6MHz", "6MHz")))
			#, ("auto", _("Auto"))))
			config.scan.ter.fechigh = configElement_nonSave("config.scan.ter.fechigh", configSelection, 5, (("1_2", "1/2"), ("2_3", "2/3"), ("3_4", "3/4"), ("5_6", "5/6"), ("7_8", "7/8"), ("auto", _("Auto"))))
			config.scan.ter.feclow = configElement_nonSave("config.scan.ter.feclow", configSelection, 5, (("1_2", "1/2"), ("2_3", "2/3"), ("3_4", "3/4"), ("5_6", "5/6"), ("7_8", "7/8"), ("auto", _("Auto"))))
			config.scan.ter.modulation = configElement_nonSave("config.scan.ter.modulation", configSelection, 3, (("qpsk", "QPSK"), ("qam16", "QAM16"), ("qam64", "QAM64"), ("auto", _("Auto"))))
			config.scan.ter.transmission = configElement_nonSave("config.scan.ter.transmission", configSelection, 2, (("2k", "2K"), ("8k", "8K"), ("auto", _("Auto"))))
			config.scan.ter.guard = configElement_nonSave("config.scan.ter.guard", configSelection, 4, (("1_32", "1/32"), ("1_16", "1/16"), ("1_8", "1/8"), ("1_4", "1/4"), ("auto", _("Auto"))))
			config.scan.ter.hierarchy = configElement_nonSave("config.scan.ter.hierarchy", configSelection, 4, (("none", _("None")), ("1", "1"), ("2", "2"), ("4", "4"), ("auto", _("Auto"))))
			config.scan.ter.networkScan = configElement_nonSave("config.scan.cab.networkScan", configSelection, 0, (("no", _("no")), ("yes", _("yes"))))

			config.scan.scansat = {}
			for sat in nimmanager.satList:
				#print sat[1]
				config.scan.scansat[sat[1]] = configElement_nonSave("config.scan.scansat[" + str(sat[1]) + "]", configSelection, 0, (("yes", _("yes")), ("no", _("no"))))

			config.scan.satselection = []
			slotid = 0
			for slot in nimmanager.nimslots:
				if (nimmanager.getNimType(slot.slotid) == nimmanager.nimType["DVB-S"]):
					print str(slot.slotid) + " : " + str(self.satList)
					config.scan.satselection.append(configElement_nonSave("config.scan.satselection[" + str(slot.slotid) + "]", configSatlist, defaultSat["orbpos"], self.satList[slot.slotid]))
				else:
					config.scan.satselection.append(None)
	def keyLeft(self):
		self["config"].handleKey(config.key["prevElement"])
		self.newConfig()

	def keyRight(self):
		self["config"].handleKey(config.key["nextElement"])
		self.newConfig()

	def updateStatus(self):
		print "updatestatus"

	def keyNumberGlobal(self, number):
		print "You pressed number " + str(number)
		if (self["config"].getCurrent()[1].parent.enabled == True):
			self["config"].handleKey(config.key[str(number)])

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
		if (nimmanager.getNimType(config.scan.nims.value) == nimmanager.nimType["DVB-S"]):
			if currentConfigSelectionElement(config.scan.type) == "single_transponder":
				l = len(self.satList)
				if l and l > config.scan.nims.value:
					nimsats=self.satList[config.scan.nims.value]
					l = len(config.scan.satselection)
					if l and l > config.scan.nims.value:
						selsatidx=config.scan.satselection[config.scan.nims.value].value
						l = len(nimsats)
						if l and l > selsatidx:
							orbpos=nimsats[selsatidx][1]
							if currentConfigSelectionElement(config.scan.sat.system) == "dvb-s":
								fec = currentConfigSelectionElement(config.scan.sat.fec)
							else:
								fec = currentConfigSelectionElement(config.scan.sat.fec_s2)
							self.addSatTransponder(tlist, config.scan.sat.frequency.value[0],
										config.scan.sat.symbolrate.value[0],
										config.scan.sat.polarization.value,
										fec,
										config.scan.sat.inversion.value,
										orbpos,
										config.scan.sat.system.value,
										config.scan.sat.modulation.value)
			elif currentConfigSelectionElement(config.scan.type) == "single_satellite":
				sat = self.satList[config.scan.nims.value][config.scan.satselection[config.scan.nims.value].value]
				getInitialTransponderList(tlist, int(sat[1]))
				flags |= eComponentScan.scanNetworkSearch
				tmp = currentConfigSelectionElement(config.scan.clearallservices)
				if tmp == "yes":
					flags |= eComponentScan.scanRemoveServices
				elif tmp == "yes_hold_feeds":
					flags |= eComponentScan.scanRemoveServices
					flags |= eComponentScan.scanDontRemoveFeeds
			elif currentConfigSelectionElement(config.scan.type) == "multisat":
				SatList = nimmanager.getSatListForNim(config.scan.nims.value)
				for x in self.multiscanlist:
					if x[1].parent.value == 0:
						print "   " + str(x[1].parent.configPath)
						getInitialTransponderList(tlist, x[1].parent.configPath)
				flags |= eComponentScan.scanNetworkSearch
				tmp = currentConfigSelectionElement(config.scan.clearallservices)
				if tmp == "yes":
					flags |= eComponentScan.scanRemoveServices
				elif tmp == "yes_hold_feeds":
					flags |= eComponentScan.scanRemoveServices
					flags |= eComponentScan.scanDontRemoveFeeds

		elif (nimmanager.getNimType(config.scan.nims.value) == nimmanager.nimType["DVB-C"]):
			if currentConfigSelectionElement(config.scan.typecable) == "single_transponder":
				fec = currentConfigSelectionElement(config.scan.cab.fec)
				self.addCabTransponder(tlist, config.scan.cab.frequency.value[0],
											  config.scan.cab.symbolrate.value[0],
											  config.scan.cab.modulation.value + 1,
											  fec,
											  config.scan.cab.inversion.value)
				if currentConfigSelectionElement(config.scan.cab.networkScan) == "yes":
					flags |= eComponentScan.scanNetworkSearch
			elif currentConfigSelectionElement(config.scan.typecable) == "complete":
				getInitialCableTransponderList(tlist, nimmanager.getCableDescription(config.scan.nims.value))
				flags |= eComponentScan.scanNetworkSearch
				tmp = currentConfigSelectionElement(config.scan.clearallservices)
				if tmp == "yes":
					flags |= eComponentScan.scanRemoveServices
				elif tmp == "yes_hold_feeds":
					flags |= eComponentScan.scanRemoveServices
					flags |= eComponentScan.scanDontRemoveFeeds

		elif (nimmanager.getNimType(config.scan.nims.value) == nimmanager.nimType["DVB-T"]):
			if currentConfigSelectionElement(config.scan.typeterrestrial) == "single_transponder":
				self.addTerTransponder(tlist,
						config.scan.ter.frequency.value[0] * 1000000,
						inversion = config.scan.ter.inversion.value,
						bandwidth = config.scan.ter.bandwidth.value,
						fechigh = config.scan.ter.fechigh.value,
						feclow = config.scan.ter.feclow.value,
						modulation = config.scan.ter.modulation.value,
						transmission = config.scan.ter.transmission.value,
						guard = config.scan.ter.guard.value,
						hierarchy = config.scan.ter.hierarchy.value)
				if currentConfigSelectionElement(config.scan.ter.networkScan) == "yes":
					flags |= eComponentScan.scanNetworkSearch
			elif currentConfigSelectionElement(config.scan.typeterrestrial) == "complete":
				getInitialTerrestrialTransponderList(tlist, nimmanager.getTerrestrialDescription(config.scan.nims.value))
				flags |= eComponentScan.scanNetworkSearch
				tmp = currentConfigSelectionElement(config.scan.clearallservices)
				if tmp == "yes":
					flags |= eComponentScan.scanRemoveServices
				elif tmp == "yes_hold_feeds":
					flags |= eComponentScan.scanRemoveServices
					flags |= eComponentScan.scanDontRemoveFeeds

		for x in self["config"].list:
			x[1].save()

		if len(tlist):
			feid = config.scan.nims.value
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

class ScanSimple(Screen):
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

		for x in self.list:
			slotid = x[1].parent.configPath
			print "Scan Tuner", slotid, "-", currentConfigSelectionElement(x[1].parent)
			if currentConfigSelectionElement(x[1].parent) == "yes":
				scanPossible = False
				tlist = [ ]
				if nimmanager.getNimType(x[1].parent.configPath) == nimmanager.nimType["DVB-S"]:
					if two_sat_tuners:
						if slotid > 0:
							idx = exclusive_satellites[0]+1
						else:
							idx = 0
						exclusive_nim_sats = exclusive_satellites[idx+1:idx+1+exclusive_satellites[idx]]
						print "exclusive_nim_sats", exclusive_nim_sats
					SatList = nimmanager.getSatListForNim(slotid)
					for sat in SatList:
						if not two_sat_tuners or (sat[1] in exclusive_nim_sats or slotid == 0):
							scanPossible = True
							print sat
							getInitialTransponderList(tlist, sat[1])
				elif nimmanager.getNimType(x[1].parent.configPath) == nimmanager.nimType["DVB-C"]:
					scanPossible = True
					getInitialCableTransponderList(tlist, nimmanager.getCableDescription(slotid))
				elif nimmanager.getNimType(x[1].parent.configPath) == nimmanager.nimType["DVB-T"]:
					scanPossible = True
					getInitialTerrestrialTransponderList(tlist, nimmanager.getTerrestrialDescription(slotid))
				if scanPossible:
					flags=eComponentScan.scanNetworkSearch
					tmp = currentConfigSelectionElement(config.scan.clearallservices)
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

	def keyLeft(self):
		self["config"].handleKey(config.key["prevElement"])

	def keyRight(self):
		self["config"].handleKey(config.key["nextElement"])

	def Satexists(self, tlist, pos):
		for x in tlist:
			if x == pos:
				return 1
		return 0

	def ScanNimTwoNeeded(self):
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

	def __init__(self, session):
		Screen.__init__(self, session)

		self["actions"] = ActionMap(["SetupActions"],
		{
			"ok": self.keyGo,
			"cancel": self.keyCancel,
			"left": self.keyLeft,
			"right": self.keyRight,
		}, -1)

		self.list = []
		tlist = []

		nimcount = nimmanager.getNimSocketCount()
		if nimcount > 0:
			nimtype = nimmanager.getNimType(0)
			scan_possible=True
			config.scan = ConfigSubsection()
			config.scan.clearallservices = configElement_nonSave("config.scan.clearallservices", configSelection, 0, (("no", _("no")), ("yes", _("yes")), ("yes_hold_feeds", _("yes (keep feeds)"))))
			self.list.append(getConfigListEntry(_("Clear before scan"), config.scan.clearallservices))
			nim = configElement_nonSave(0, configSelection, 0, (("yes", _("yes")), ("no", _("no"))))
			if nimtype == nimmanager.nimType["DVB-S"] and not len(nimmanager.getSatListForNim(0)):
				scan_possible=False
			if scan_possible:
				self.list.append(getConfigListEntry(_("Scan NIM") + " 0 (" + nimmanager.getNimTypeName(0) + ")", nim))
	
		if nimcount > 1 and self.ScanNimTwoNeeded():
			nim = configElement_nonSave(1, configSelection, 0, (("yes", _("yes")), ("no", _("no"))))
			self.list.append(getConfigListEntry(_("Scan NIM") + " 1 (" + nimmanager.getNimTypeName(1) + ")", nim))

		self["config"] = ConfigList(self.list)
		self["header"] = Label(_("Automatic Scan"))
		self["footer"] = Label(_("Press OK to scan"))
