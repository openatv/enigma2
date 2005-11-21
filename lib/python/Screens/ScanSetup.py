from Screen import Screen
from ServiceScan import *
from Components.config import *
from Components.ActionMap import NumberActionMap
from Components.ConfigList import ConfigList
from Components.config import config
from Components.config import getConfigListEntry
from Components.NimManager import nimmanager
from Components.Label import Label
from enigma import eDVBFrontendParametersSatellite, eComponentScan

def getInitialTransponderList(tlist, pos):
	print pos
	list = nimmanager.getTransponders(pos)

	for x in list:
		if x[0] == 0:		#SAT
			parm = eDVBFrontendParametersSatellite()
			parm.frequency = x[1]
			parm.symbol_rate = x[2]
			parm.polarisation = x[3] # eDVBFrontendParametersSatellite.Polarisation.Vertical
			#parm.fec = x[4]			# eDVBFrontendParametersSatellite.FEC.f3_4;
			parm.fec = 6					# AUTO
			#parm.inversion = 1 	#eDVBFrontendParametersSatellite.Inversion.Off;
			parm.inversion = 2 		#AUTO
			parm.orbital_position = pos
			tlist.append(parm)

class ScanSetup(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		self.updateSatList()
		self.createConfig()


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

		self.list = []
		self["config"] = ConfigList(self.list)
		self.createSetup()

		self["introduction"] = Label("Press OK to start the scan")

	def updateSatList(self):
		self.satList = []
		for slot in nimmanager.nimslots:
			if (nimmanager.getNimType(slot.slotid) == nimmanager.nimType["DVB-S"]):
				self.satList.append(nimmanager.getSatListForNim(slot.slotid))

	def createSetup(self):
		self.list = []

		self.list.append(getConfigListEntry(_("Tuner"), config.scan.nims))
		
		if (nimmanager.getNimType(config.scan.nims.value) == nimmanager.nimType["DVB-S"]):
			self.list.append(getConfigListEntry(_("Type of scan"), config.scan.type))
		elif (nimmanager.getNimType(config.scan.nims.value) == nimmanager.nimType["DVB-C"]):
			self.list.append(getConfigListEntry(_("Type of scan"), config.scan.typecable))
		elif (nimmanager.getNimType(config.scan.nims.value) == nimmanager.nimType["DVB-T"]):
			self.list.append(getConfigListEntry(_("Type of scan"), config.scan.typeterrestrial))


		if (nimmanager.getNimType(config.scan.nims.value) == nimmanager.nimType["DVB-S"]):
			if (config.scan.type.value == 0): # single transponder scan
				self.list.append(getConfigListEntry(_('Satellite'), config.scan.satselection[config.scan.nims.value]))
				self.list.append(getConfigListEntry(_('Frequency'), config.scan.sat.frequency))
				self.list.append(getConfigListEntry(_('Inversion'), config.scan.sat.inversion))
				self.list.append(getConfigListEntry(_('Symbolrate'), config.scan.sat.symbolrate))
				self.list.append(getConfigListEntry("Polarity", config.scan.sat.polarization))
				self.list.append(getConfigListEntry("FEC", config.scan.sat.fec))
			if (config.scan.type.value == 1): # single satellite scan
				self.updateSatList()
				print config.scan.satselection[config.scan.nims.value]
				self.list.append(getConfigListEntry("Satellite", config.scan.satselection[config.scan.nims.value]))
			if (config.scan.type.value == 2): # multi sat scan
				# if (norotor)
				tlist = []
				SatList = nimmanager.getSatListForNim(config.scan.nims.value)
	
				for x in SatList:
					if self.Satexists(tlist, x[1]) == 0:
						tlist.append(x[1])
						sat = configElement_nonSave(x[1], configSelection, 0, ("Enable", "Disable"))
						self.list.append(getConfigListEntry(nimmanager.getSatDescription(x[1]), sat))
	
				# if (rotor):
    			   # for sat in nimmanager.satList:
				#	self.list.append(getConfigListEntry(sat[0], config.scan.scansat[sat[1]]))


		if (nimmanager.getNimType(config.scan.nims.value) == nimmanager.nimType["DVB-C"]):
			if (config.scan.typecable.value == 0): # single transponder
				self.list.append(getConfigListEntry("Frequency", config.scan.cab.frequency))
				self.list.append(getConfigListEntry("Inversion", config.scan.cab.inversion))
				self.list.append(getConfigListEntry("Symbolrate", config.scan.cab.symbolrate))
				self.list.append(getConfigListEntry("Modulation", config.scan.cab.modulation))
				self.list.append(getConfigListEntry("FEC", config.scan.cab.fec))
			if (config.scan.typecable.value == 1): # complete
				pass
	
				
		if (nimmanager.getNimType(config.scan.nims.value) == nimmanager.nimType["DVB-T"]):
			if (config.scan.typeterrestrial.value == 0): # single transponder
				self.list.append(getConfigListEntry("Frequency", config.scan.ter.frequency))
				self.list.append(getConfigListEntry("Inversion", config.scan.ter.inversion))
				self.list.append(getConfigListEntry("Bandwidth", config.scan.ter.bandwidth))
				self.list.append(getConfigListEntry("Code rate high", config.scan.ter.fechigh))
				self.list.append(getConfigListEntry("Code rate low", config.scan.ter.feclow))
				self.list.append(getConfigListEntry("Modulation", config.scan.ter.modulation))
				self.list.append(getConfigListEntry("Transmission mode", config.scan.ter.transmission))
				self.list.append(getConfigListEntry("Guard interval mode", config.scan.ter.guard))
				self.list.append(getConfigListEntry("Hierarchy mode", config.scan.ter.hierarchy))
			if (config.scan.typeterrestrial.value == 1): # complete
				pass




		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def Satexists(self, tlist, pos):
		for x in tlist:
			if x == pos:
				return 1
		return 0

	def newConfig(self):
		print self["config"].getCurrent()
		if self["config"].getCurrent()[0] == _("Type of scan"):
			self.createSetup()
		if self["config"].getCurrent()[0] == _("Tuner"):
			self.createSetup()

	def createConfig(self):
			config.scan = ConfigSubsection()
			config.scan.sat = ConfigSubsection()
			config.scan.cab = ConfigSubsection()
			config.scan.ter = ConfigSubsection()

			config.scan.type = configElement_nonSave("config.scan.type", configSelection, 0, ("Single transponder", "Single satellite", "Multisat"))
			config.scan.typecable = configElement_nonSave("config.scan.typecable", configSelection, 0, ("Single transponder", "Complete"))
			config.scan.typeterrestrial = configElement_nonSave("config.scan.typeterrestrial", configSelection, 0, ("Single transponder", "Complete"))

			nimList = [ ]
			for nim in nimmanager.nimList():
				nimList.append(nim[0])
			nimList.append("all")
			config.scan.nims = configElement_nonSave("config.scan.nims", configSelection, 0, nimList)

			# sat
			config.scan.sat.frequency = configElement_nonSave("config.scan.sat.frequency", configSequence, [11836], configsequencearg.get("INTEGER", (10000, 14000)))
			config.scan.sat.inversion = configElement_nonSave("config.scan.sat.inversion", configSelection, 2, ("on", "off", "auto"))
			config.scan.sat.symbolrate = configElement_nonSave("config.scan.sat.symbolrate", configSequence, [27500], configsequencearg.get("INTEGER", (1, 30000)))
			config.scan.sat.polarization = configElement_nonSave("config.scan.sat.polarization", configSelection, 0, ("horizontal", "vertical",  "circular left", "circular right"))
			config.scan.sat.fec = configElement_nonSave("config.scan.sat.fec", configSelection, 7, ("None", "1/2", "2/3", "3/4", "5/6", "7/8", "auto"))


			# cable
			config.scan.cab.frequency = configElement_nonSave("config.scan.cab.frequency", configSequence, [466], configsequencearg.get("INTEGER", (10000, 14000)))
			config.scan.cab.inversion = configElement_nonSave("config.scan.cab.inversion", configSelection, 0, ("auto", "off", "on"))
			config.scan.cab.modulation = configElement_nonSave("config.scan.cab.modulation", configSelection, 0, ("Auto", "16-QAM", "32-QAM", "64-QAM", "128-QAM", "256-QAM"))
			config.scan.cab.fec = configElement_nonSave("config.scan.cab.fec", configSelection, 0, ("Auto", "1/2", "2/3", "3/4", "4/5", "5/6", "7/8", "8/9"))
			config.scan.cab.symbolrate = configElement_nonSave("config.scan.cab.symbolrate", configSequence, [6900], configsequencearg.get("INTEGER", (1, 30000)))

			# terrestial
			config.scan.ter.frequency = configElement_nonSave("config.scan.ter.frequency", configSequence, [466], configsequencearg.get("INTEGER", (10000, 14000)))
			config.scan.ter.inversion = configElement_nonSave("config.scan.ter.inversion", configSelection, 0, ("auto", "off", "on"))
			config.scan.ter.bandwidth = configElement_nonSave("config.scan.ter.bandwidth", configSelection, 0, ("Auto", "6 MHz", "7MHz", "8MHz"))
			config.scan.ter.fechigh = configElement_nonSave("config.scan.ter.fechigh", configSelection, 0, ("Auto", "1/2", "2/3", "3/4", "4/5", "5/6", "7/8", "8/9"))
			config.scan.ter.feclow = configElement_nonSave("config.scan.ter.feclow", configSelection, 0, ("Auto", "1/2", "2/3", "3/4", "4/5", "5/6", "7/8", "8/9"))
			config.scan.ter.modulation = configElement_nonSave("config.scan.ter.modulation", configSelection, 0, ("Auto", "16-QAM", "32-QAM", "64-QAM", "128-QAM", "256-QAM"))
			config.scan.ter.transmission = configElement_nonSave("config.scan.ter.transmission", configSelection, 0, ("Auto", "2K", "8K"))
			config.scan.ter.guard = configElement_nonSave("config.scan.ter.guard", configSelection, 0, ("Auto", "1/4", "1/8", "1/16", "1/32"))
			config.scan.ter.hierarchy = configElement_nonSave("config.scan.ter.hierarchy", configSelection, 0, ("Auto", "1", "2", "4"))

			config.scan.scansat = {}
			for sat in nimmanager.satList:
				#print sat[1]
				config.scan.scansat[sat[1]] = configElement_nonSave("config.scan.scansat[" + str(sat[1]) + "]", configSelection, 0, ("yes", "no"))

			config.scan.satselection = []
			slotid = 0
			for slot in nimmanager.nimslots:
				if (nimmanager.getNimType(slot.slotid) == nimmanager.nimType["DVB-S"]):
					config.scan.satselection.append(configElement_nonSave("config.scan.satselection[" + str(slot.slotid) + "]", configSatlist, 0, self.satList[slot.slotid]))

	def keyLeft(self):
		self["config"].handleKey(config.key["prevElement"])
		self.newConfig()

	def keyRight(self):
		self["config"].handleKey(config.key["nextElement"])
		self.newConfig()

	def keyNumberGlobal(self, number):
		print "You pressed number " + str(number)
		if (self["config"].getCurrent()[1].parent.enabled == True):
			self["config"].handleKey(config.key[str(number)])

	def addSatTransponder(self, tlist, frequency, symbol_rate, polarisation, fec, inversion, orbital_position):
		print "Add Sat: frequ: " + str(frequency) + " symbol: " + str(symbol_rate) + " pol: " + str(polarisation) + " fec: " + str(fec) + " inversion: " + str(inversion)
		print "orbpos: " + str(orbital_position)
		parm = eDVBFrontendParametersSatellite()
		parm.frequency = frequency * 1000
		parm.symbol_rate = symbol_rate * 1000
		parm.polarisation = polarisation # eDVBFrontendParametersSatellite.Polarisation.Verti	
		parm.fec = fec			# eDVBFrontendParametersSatellite.FEC.f3_4;
		#parm.fec = 6					# AUTO
		parm.inversion = inversion 	#eDVBFrontendParametersSatellite.Inversion.Off;
		#parm.inversion = 2 		#AUTO
		parm.orbital_position = int(orbital_position)
		tlist.append(parm)

	# FIXME use correct parameters
	def addCabTransponder(self, tlist, frequency, symbol_rate, polarisation, fec, inversion, orbital_position):
		print "Add Sat: frequ: " + str(frequency) + " symbol: " + str(symbol_rate) + " pol: " + str(polarisation) + " fec: " + str(fec) + " inversion: " + str(inversion)
		print "orbpos: " + str(orbital_position)
		parm = eDVBFrontendParametersCable()
		parm.frequency = frequency * 1000
		parm.symbol_rate = symbol_rate * 1000
		parm.polarisation = polarisation # eDVBFrontendParametersSatellite.Polarisation.Verti	
		parm.fec = fec			# eDVBFrontendParametersSatellite.FEC.f3_4;
		#parm.fec = 6					# AUTO
		parm.inversion = inversion 	#eDVBFrontendParametersSatellite.Inversion.Off;
		#parm.inversion = 2 		#AUTO
		parm.orbital_position = int(orbital_position)
		tlist.append(parm)

	# FIXME use correct parameters
	def addTerTransponder(self, tlist, frequency, symbol_rate, polarisation, fec, inversion, orbital_position):
		print "Add Sat: frequ: " + str(frequency) + " symbol: " + str(symbol_rate) + " pol: " + str(polarisation) + " fec: " + str(fec) + " inversion: " + str(inversion)
		print "orbpos: " + str(orbital_position)
		parm = eDVBFrontendParametersTerrestrial()
		parm.frequency = frequency * 1000
		parm.symbol_rate = symbol_rate * 1000
		parm.polarisation = polarisation # eDVBFrontendParametersSatellite.Polarisation.Verti	
		parm.fec = fec			# eDVBFrontendParametersSatellite.FEC.f3_4;
		#parm.fec = 6					# AUTO
		parm.inversion = inversion 	#eDVBFrontendParametersSatellite.Inversion.Off;
		#parm.inversion = 2 		#AUTO
		parm.orbital_position = int(orbital_position)
		tlist.append(parm)

	def keyGo(self):
		tlist = []
		flags = 0
		if (config.scan.type.value == 0): # single transponder scan
			if (nimmanager.getNimType(config.scan.nims.value) == nimmanager.nimType["DVB-S"]):
				self.addSatTransponder(tlist, config.scan.sat.frequency.value[0],
											  config.scan.sat.symbolrate.value[0],
											  config.scan.sat.polarization.value,
											  config.scan.sat.fec.value,
											  config.scan.sat.inversion.value,
											  self.satList[config.scan.nims.value][config.scan.satselection[config.scan.nims.value].value][1])
			if (nimmanager.getNimType(config.scan.nims.value) == nimmanager.nimType["DVB-C"]):
				self.addCabTransponder(tlist, config.scan.cab.frequency.value[0],
											  config.scan.cab.symbolrate.value[0],
											  config.scan.cab.polarization.value,
											  config.scan.cab.fec.value,
											  config.scan.cab.inversion.value,
											  self.satList[config.scan.nims.value][config.scan.satselection[config.scan.nims.value].value][1])
			if (nimmanager.getNimType(config.scan.nims.value) == nimmanager.nimType["DVB-T"]):
				self.addTerTransponder(tlist, config.scan.sat.frequency.value[0],
											  config.scan.sat.symbolrate.value[0],
											  config.scan.sat.polarization.value,
											  config.scan.sat.fec.value,
											  config.scan.sat.inversion.value,
											  self.satList[config.scan.nims.value][config.scan.satselection[config.scan.nims.value].value][1])

		if (config.scan.type.value == 1): # single sat scan
			getInitialTransponderList(tlist, int(self.satList[config.scan.nims.value][config.scan.satselection[config.scan.nims.value].value][1]))
			flags |= eComponentScan.scanNetworkSearch

		if (config.scan.type.value == 2): # multi sat scan
			SatList = nimmanager.getSatListForNim(config.scan.nims.value)

			for x in self.list:
				if x[1].parent.value == 0:
					print "   " + str(x[1].parent.configPath)
					getInitialTransponderList(tlist, x[1].parent.configPath)
			flags |= eComponentScan.scanNetworkSearch

		for x in self["config"].list:
			x[1].save()

		feid = config.scan.nims.value
		# flags |= eComponentScan.scanSearchBAT
		self.session.openWithCallback(self.keyCancel, ServiceScan, tlist, feid, flags)

		#self.close()

	def keyCancel(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close()

class ScanSimple(Screen):

	def keyOK(self):
		print "start scan for sats:"
		tlist = [ ]
		for x in self.list:
			if x[1].parent.value == 0:
				print "   " + str(x[1].parent.configPath)
				getInitialTransponderList(tlist, x[1].parent.configPath)

		feid = 0 # FIXME
		self.session.openWithCallback(self.keyCancel, ServiceScan, tlist, feid, eComponentScan.scanNetworkSearch)

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

	def __init__(self, session):
		Screen.__init__(self, session)

		self["actions"] = ActionMap(["SetupActions"],
		{
			"ok": self.keyOK,
			"cancel": self.keyCancel,
			"left": self.keyLeft,
			"right": self.keyRight,
		}, -1)

		self.list = []
		tlist = []

		SatList = nimmanager.getConfiguredSats()

		for x in SatList:
			if self.Satexists(tlist, x) == 0:
				tlist.append(x)
				sat = configElement_nonSave(x, configSelection, 0, ("Enable", "Disable"))
				self.list.append(getConfigListEntry(nimmanager.getSatDescription(x), sat))

		self["config"] = ConfigList(self.list)
		self["header"] = Label("Automatic Scan")
		self["footer"] = Label("Press OK to scan")
