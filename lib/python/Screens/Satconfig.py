from Screen import Screen
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigList, ConfigListScreen
from Components.MenuList import MenuList
from Components.NimManager import nimmanager
from Components.config import getConfigListEntry, config, ConfigNothing

class NimSetup(Screen, ConfigListScreen):
	def createSimpleSetup(self, list, mode):
		if mode == "single":
			list.append(getConfigListEntry(_("Satellite"), self.nimConfig.diseqcA))
		else:
			list.append(getConfigListEntry(_("Port A"), self.nimConfig.diseqcA))

		if mode in ["toneburst_a_b", "diseqc_a_b", "diseqc_a_b_c_d"]:
			list.append(getConfigListEntry(_("Port B"), self.nimConfig.diseqcB))
			if mode == "diseqc_a_b_c_d":
				list.append(getConfigListEntry(_("Port C"), self.nimConfig.diseqcC))
				list.append(getConfigListEntry(_("Port D"), self.nimConfig.diseqcD))

	def createPositionerSetup(self, list):
#		list.append(getConfigListEntry(_("Positioner mode"), self.nimConfig.positionerMode))
#		if self.nimConfig.positionerMode.value == "usals": # USALS
		list.append(getConfigListEntry(_("Longitude"), self.nimConfig.longitude))
		list.append(getConfigListEntry(" ", self.nimConfig.longitudeOrientation))
		list.append(getConfigListEntry(_("Latitude"), self.nimConfig.latitude))
		list.append(getConfigListEntry(" ", self.nimConfig.latitudeOrientation))
#		elif self.nimConfig.positionerMode.value == "manual": # manual
#			pass

	def createSetup(self):
		print "Creating setup"
		self.list = [ ]

		self.configMode = None
		self.diseqcModeEntry = None
		self.advancedSatsEntry = None
		self.advancedLnbsEntry = None
		self.advancedDiseqcMode = None
		self.advancedUsalsEntry = None
		self.advancedLof = None
		self.advancedPowerMeasurement = None
		
		self.nim_type = nimmanager.getNimType(self.nim.slotid)

		if self.nim_type == nimmanager.nimType["DVB-S"]:
			self.configMode = getConfigListEntry(_("Configuration Mode"), self.nimConfig.configMode)
			self.list.append(self.configMode)
			
			if self.nimConfig.configMode.value == "simple":			#simple setup
				self.diseqcModeEntry = getConfigListEntry(_("DiSEqC Mode"), self.nimConfig.diseqcMode)
				self.list.append(self.diseqcModeEntry)
				if self.nimConfig.diseqcMode.value in ["single", "toneburst_a_b", "diseqc_a_b", "diseqc_a_b_c_d"]:
					self.createSimpleSetup(self.list, self.nimConfig.diseqcMode.value)
				if self.nimConfig.diseqcMode.value == "positioner":
					self.createPositionerSetup(self.list)
			elif self.nimConfig.configMode.value in ["loopthrough", "satposdepends", "nothing", "equal"]:
				pass
			elif self.nimConfig.configMode.value == "advanced": # advanced
				# SATs
				self.advancedSatsEntry = getConfigListEntry(_("Satellite"), self.nimConfig.advanced.sats)
				self.list.append(self.advancedSatsEntry)
				print "blub", self.nimConfig.advanced.sat
				currSat = self.nimConfig.advanced.sat[self.nimConfig.advanced.sats.orbital_position]
				self.fillListWithAdvancedSatEntrys(currSat)
			self.have_advanced = True
		elif self.nim_type == nimmanager.nimType["DVB-C"]:
			self.list.append(getConfigListEntry(_("Cable provider"), self.nimConfig.cable))
			self.have_advanced = False
		elif self.nim_type == nimmanager.nimType["DVB-T"]:
			self.have_advanced = False
			self.list.append(getConfigListEntry(_("Terrestrial provider"), self.nimConfig.terrestrial))
			self.list.append(getConfigListEntry(_("Enable 5V for active antenna"), self.nimConfig.terrestrial_5V))
		else:
			self.have_advanced = False

		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def newConfig(self):
		checkList = (self.configMode, self.diseqcModeEntry, self.advancedSatsEntry, self.advancedLnbsEntry, self.advancedDiseqcMode, self.advancedUsalsEntry, self.advancedLof, self.advancedPowerMeasurement)
		for x in checkList:
			if self["config"].getCurrent() == x:
				self.createSetup()

	def run(self):
		if self.have_advanced and config.Nims[self.nim.slotid].configMode.value == "advanced":
			self.fillAdvancedList()
		for x in self["config"].list:
			x[1].save()
		nimmanager.sec.update()

	def fillListWithAdvancedSatEntrys(self, Sat):
		currLnb = self.nimConfig.advanced.lnb[int(Sat.lnb.value)]
		
		if isinstance(currLnb, ConfigNothing):
			currLnb = None

		self.list.append(getConfigListEntry(_("Voltage mode"), Sat.voltage))
		self.list.append(getConfigListEntry(_("Tone mode"), Sat.tonemode))
		if currLnb and currLnb.diseqcMode.value == "1_2":
			self.advancedUsalsEntry = getConfigListEntry(_("Use usals for this sat"), Sat.usals)
			self.list.append(self.advancedUsalsEntry)
			if not Sat.usals.value:
				self.list.append(getConfigListEntry(_("Stored position"), Sat.rotorposition))

		# LNBs
		self.advancedLnbsEntry = getConfigListEntry(_("LNB"), Sat.lnb)
		self.list.append(self.advancedLnbsEntry)
		if currLnb:
			self.advancedDiseqcMode = getConfigListEntry(_("DiSEqC mode"), currLnb.diseqcMode)
			self.list.append(self.advancedDiseqcMode)
			if currLnb.diseqcMode.value != "none":
				self.list.append(getConfigListEntry(_("Toneburst"), currLnb.toneburst))
				self.list.append(getConfigListEntry(_("Committed DiSEqC command"), currLnb.commitedDiseqcCommand))
				self.list.append(getConfigListEntry(_("Fast DiSEqC"), currLnb.fastDiseqc))
				self.list.append(getConfigListEntry(_("Sequence repeat"), currLnb.sequenceRepeat))
				if currLnb.diseqcMode.value == "1_0":
					self.list.append(getConfigListEntry(_("Command order"), currLnb.commandOrder1_0))
				else:
					self.list.append(getConfigListEntry(_("Command order"), currLnb.commandOrder))
					self.list.append(getConfigListEntry(_("Uncommitted DiSEqC command"), currLnb.uncommittedDiseqcCommand))
					self.list.append(getConfigListEntry(_("DiSEqC repeats"), currLnb.diseqcRepeats))
				if currLnb.diseqcMode.value == "1_2":
					self.list.append(getConfigListEntry(_("Longitude"), currLnb.longitude))
					self.list.append(getConfigListEntry(" ", currLnb.longitudeOrientation))
					self.list.append(getConfigListEntry(_("Latitude"), currLnb.latitude))
					self.list.append(getConfigListEntry(" ", currLnb.latitudeOrientation))
					self.advancedPowerMeasurement = getConfigListEntry("Use Power Measurement", currLnb.powerMeasurement)
					self.list.append(self.advancedPowerMeasurement)
					if currLnb.powerMeasurement.value == "yes":
						self.list.append(getConfigListEntry("Power Threshold in mA", currLnb.powerThreshold))
			self.advancedLof = getConfigListEntry(_("LOF"), currLnb.lof)
			self.list.append(self.advancedLof)
			if currLnb.lof.value == "user_defined":
				self.list.append(getConfigListEntry(_("LOF/L"), currLnb.lofl))
				self.list.append(getConfigListEntry(_("LOF/H"), currLnb.lofh))
				self.list.append(getConfigListEntry(_("Threshold"), currLnb.threshold))
			self.list.append(getConfigListEntry(_("12V Output"), currLnb.output_12v))
			self.list.append(getConfigListEntry(_("Increased voltage"), currLnb.increased_voltage))

	def fillAdvancedList(self):
		self.list = [ ]
		self.configMode = getConfigListEntry(_("Configuration Mode"), self.nimConfig.configMode)
		self.list.append(self.configMode)
		self.advancedSatsEntry = getConfigListEntry(_("Satellite"), self.nimConfig.advanced.sats)
		self.list.append(self.advancedSatsEntry)
		for x in nimmanager.satList:
			Sat = self.nimConfig.advanced.sat[x[0]]
			self.fillListWithAdvancedSatEntrys(Sat)
		self["config"].list = self.list

	def keySave(self):
		self.run()
		self.close()

	def keyCancel(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def __init__(self, session, slotid):
		Screen.__init__(self, session)
		self.list = [ ]

		ConfigListScreen.__init__(self, self.list)

		self["actions"] = ActionMap(["SetupActions"],
		{
			"ok": self.keySave,
			"cancel": self.keyCancel,
		}, -2)

		self.nim = nimmanager.nimList()[slotid][1]
		self.nimConfig = config.Nims[self.nim.slotid]
		self.createSetup()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.newConfig()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.newConfig()

class NimSelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)

		self["nimlist"] = MenuList(nimmanager.nimList())

		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"ok": self.okbuttonClick ,
			"cancel": self.close
		}, -2)

	def okbuttonClick(self):
		selection = self["nimlist"].getCurrent()
		if selection[1].nimType != -1:	#unknown/empty
			self.session.open(NimSetup, selection[1].slotid)
	
