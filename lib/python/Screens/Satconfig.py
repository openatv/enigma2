from enigma import eDVBDB
from Screen import Screen
from Components.SystemInfo import SystemInfo
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigListScreen
from Components.MenuList import MenuList
from Components.NimManager import nimmanager
from Components.config import getConfigListEntry, config, ConfigNothing, ConfigSelection, updateConfigElement
from Screens.MessageBox import MessageBox

from time import mktime, localtime
from datetime import datetime

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
		nim = self.nimConfig
		list.append(getConfigListEntry(_("Longitude"), nim.longitude))
		list.append(getConfigListEntry(" ", nim.longitudeOrientation))
		list.append(getConfigListEntry(_("Latitude"), nim.latitude))
		list.append(getConfigListEntry(" ", nim.latitudeOrientation))
		if SystemInfo["CanMeasureFrontendInputPower"]:
			self.advancedPowerMeasurement = getConfigListEntry(_("Use Power Measurement"), nim.powerMeasurement)
			list.append(self.advancedPowerMeasurement)
			if nim.powerMeasurement.value:
				list.append(getConfigListEntry(_("Power threshold in mA"), nim.powerThreshold))
				self.turningSpeed = getConfigListEntry(_("Rotor turning speed"), nim.turningSpeed)
				list.append(self.turningSpeed)
				if nim.turningSpeed.value == "fast epoch":
					self.turnFastEpochBegin = getConfigListEntry(_("Begin time"), nim.fastTurningBegin)
					self.turnFastEpochEnd = getConfigListEntry(_("End time"), nim.fastTurningEnd)
					list.append(self.turnFastEpochBegin)
					list.append(self.turnFastEpochEnd)
		else:
			if nim.powerMeasurement.value:
				nim.powerMeasurement.value = False
				nim.powerMeasurement.save()
		
	def createConfigMode(self):
		choices = { "nothing": _("nothing connected"),
					"simple": _("simple"),
					"advanced": _("advanced")}
		#if len(nimmanager.getNimListOfType(nimmanager.getNimType(self.slotid), exception = x)) > 0:
		#	choices["equal"] = _("equal to")
		#	choices["satposdepends"] = _("second cable of motorized LNB")
		if len(nimmanager.canEqualTo(self.slotid)) > 0:
			choices["equal"] = _("equal to")
		if len(nimmanager.canDependOn(self.slotid)) > 0:
			choices["satposdepends"] = _("second cable of motorized LNB")
		if len(nimmanager.canConnectTo(self.slotid)) > 0:
			choices["loopthrough"] = _("loopthrough to")
		self.nim.config.configMode.setChoices(choices)
							
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
		self.turningSpeed = None
		self.turnFastEpochBegin = None
		self.turnFastEpochEnd = None
		self.uncommittedDiseqcCommand = None
		self.cableScanType = None
		self.have_advanced = False

		if self.nim.isCompatible("DVB-S"):
			self.configMode = getConfigListEntry(_("Configuration Mode"), self.nimConfig.configMode)
			self.list.append(self.configMode)

			if self.nimConfig.configMode.value == "simple":			#simple setup
				self.diseqcModeEntry = getConfigListEntry(_("DiSEqC Mode"), self.nimConfig.diseqcMode)
				self.list.append(self.diseqcModeEntry)
				if self.nimConfig.diseqcMode.value in ["single", "toneburst_a_b", "diseqc_a_b", "diseqc_a_b_c_d"]:
					self.createSimpleSetup(self.list, self.nimConfig.diseqcMode.value)
				if self.nimConfig.diseqcMode.value == "positioner":
					self.createPositionerSetup(self.list)
			elif self.nimConfig.configMode.value == "equal":
				choices = []
				nimlist = nimmanager.canEqualTo(self.nim.slot)
				for id in nimlist:
					#choices.append((str(id), str(chr(65 + id))))
					choices.append((str(id), nimmanager.getNimDescription(id)))
				self.nimConfig.connectedTo.setChoices(choices)
				#self.nimConfig.connectedTo = updateConfigElement(self.nimConfig.connectedTo, ConfigSelection(choices = choices))
				self.list.append(getConfigListEntry(_("Tuner"), self.nimConfig.connectedTo))
			elif self.nimConfig.configMode.value == "satposdepends":
				choices = []
				nimlist = nimmanager.canDependOn(self.nim.slot)
				for id in nimlist:
					#choices.append((str(id), str(chr(65 + id))))
					choices.append((str(id), nimmanager.getNimDescription(id)))
				self.nimConfig.connectedTo.setChoices(choices)
				#self.nimConfig.connectedTo = updateConfigElement(self.nimConfig.connectedTo, ConfigSelection(choices = choices))
				self.list.append(getConfigListEntry(_("Tuner"), self.nimConfig.connectedTo))
			elif self.nimConfig.configMode.value == "loopthrough":
				choices = []
				print "connectable to:", nimmanager.canConnectTo(self.slotid)
				connectable = nimmanager.canConnectTo(self.slotid) 
				for id in connectable:
					choices.append((str(id), nimmanager.getNimDescription(id)))
				self.nimConfig.connectedTo.setChoices(choices)
				#self.nimConfig.connectedTo = updateConfigElement(self.nimConfig.connectedTo, ConfigSelection(choices = choices))
				self.list.append(getConfigListEntry(_("Connected to"), self.nimConfig.connectedTo))
			elif self.nimConfig.configMode.value == "nothing":
				pass
			elif self.nimConfig.configMode.value == "advanced": # advanced
				# SATs
				self.advancedSatsEntry = getConfigListEntry(_("Satellite"), self.nimConfig.advanced.sats)
				self.list.append(self.advancedSatsEntry)
				cur_orb_pos = self.nimConfig.advanced.sats.orbital_position
				satlist = self.nimConfig.advanced.sat.keys()
				if cur_orb_pos is not None:
					if cur_orb_pos not in satlist:
						cur_orb_pos = satlist[0]
					currSat = self.nimConfig.advanced.sat[cur_orb_pos]
					self.fillListWithAdvancedSatEntrys(currSat)
				self.have_advanced = True
		elif self.nim.isCompatible("DVB-C"):
			self.configMode = getConfigListEntry(_("Configuration Mode"), self.nimConfig.configMode)
			self.list.append(self.configMode)
			if self.nimConfig.configMode.value == "enabled":
				self.cableScanType=getConfigListEntry(_("Used service scan type"), self.nimConfig.cable.scan_type)
				self.list.append(self.cableScanType)
				if self.nimConfig.cable.scan_type.value == "provider":
					self.list.append(getConfigListEntry(_("Provider to scan"), self.nimConfig.cable.scan_provider))
				else:
					if self.nimConfig.cable.scan_type.value == "bands":
						self.list.append(getConfigListEntry(_("Scan band EU VHF I"), self.nimConfig.cable.scan_band_EU_VHF_I))
						self.list.append(getConfigListEntry(_("Scan band EU MID"), self.nimConfig.cable.scan_band_EU_MID))
						self.list.append(getConfigListEntry(_("Scan band EU VHF III"), self.nimConfig.cable.scan_band_EU_VHF_III))
						self.list.append(getConfigListEntry(_("Scan band EU UHF IV"), self.nimConfig.cable.scan_band_EU_UHF_IV))
						self.list.append(getConfigListEntry(_("Scan band EU UHF V"), self.nimConfig.cable.scan_band_EU_UHF_V))
						self.list.append(getConfigListEntry(_("Scan band EU SUPER"), self.nimConfig.cable.scan_band_EU_SUPER))
						self.list.append(getConfigListEntry(_("Scan band EU HYPER"), self.nimConfig.cable.scan_band_EU_HYPER))
						self.list.append(getConfigListEntry(_("Scan band US LOW"), self.nimConfig.cable.scan_band_US_LOW))
						self.list.append(getConfigListEntry(_("Scan band US MID"), self.nimConfig.cable.scan_band_US_MID))
						self.list.append(getConfigListEntry(_("Scan band US HIGH"), self.nimConfig.cable.scan_band_US_HIGH))
						self.list.append(getConfigListEntry(_("Scan band US SUPER"), self.nimConfig.cable.scan_band_US_SUPER))
						self.list.append(getConfigListEntry(_("Scan band US HYPER"), self.nimConfig.cable.scan_band_US_HYPER))
					elif self.nimConfig.cable.scan_type.value == "steps":
						self.list.append(getConfigListEntry(_("Frequency scan step size(khz)"), self.nimConfig.cable.scan_frequency_steps))
					self.list.append(getConfigListEntry(_("Scan QAM16"), self.nimConfig.cable.scan_mod_qam16))
					self.list.append(getConfigListEntry(_("Scan QAM32"), self.nimConfig.cable.scan_mod_qam32))
					self.list.append(getConfigListEntry(_("Scan QAM64"), self.nimConfig.cable.scan_mod_qam64))
					self.list.append(getConfigListEntry(_("Scan QAM128"), self.nimConfig.cable.scan_mod_qam128))
					self.list.append(getConfigListEntry(_("Scan QAM256"), self.nimConfig.cable.scan_mod_qam256))
					self.list.append(getConfigListEntry(_("Scan SR6900"), self.nimConfig.cable.scan_sr_6900))
					self.list.append(getConfigListEntry(_("Scan SR6875"), self.nimConfig.cable.scan_sr_6875))
					self.list.append(getConfigListEntry(_("Scan additional SR"), self.nimConfig.cable.scan_sr_ext1))
					self.list.append(getConfigListEntry(_("Scan additional SR"), self.nimConfig.cable.scan_sr_ext2))
			self.have_advanced = False
		elif self.nim.isCompatible("DVB-T"):
			self.configMode = getConfigListEntry(_("Configuration Mode"), self.nimConfig.configMode)
			self.list.append(self.configMode)
			self.have_advanced = False
			if self.nimConfig.configMode.value == "enabled":
				self.list.append(getConfigListEntry(_("Terrestrial provider"), self.nimConfig.terrestrial))
				self.list.append(getConfigListEntry(_("Enable 5V for active antenna"), self.nimConfig.terrestrial_5V))
		else:
			self.have_advanced = False
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def newConfig(self):
		checkList = (self.configMode, self.diseqcModeEntry, self.advancedSatsEntry, \
			self.advancedLnbsEntry, self.advancedDiseqcMode, self.advancedUsalsEntry, \
			self.advancedLof, self.advancedPowerMeasurement, self.turningSpeed, \
			self.uncommittedDiseqcCommand, self.cableScanType)
		for x in checkList:
			if self["config"].getCurrent() == x:
				self.createSetup()

	def run(self):
		if self.have_advanced and self.nim.config_mode == "advanced":
			self.fillAdvancedList()
		for x in self.list:
			if x in [self.turnFastEpochBegin, self.turnFastEpochEnd]:
				# workaround for storing only hour*3600+min*60 value in configfile
				# not really needed.. just for cosmetics..
				tm = localtime(x[1].value)
				dt = datetime(1970, 1, 1, tm.tm_hour, tm.tm_min)
				x[1].value = int(mktime(dt.timetuple()))
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
					if currLnb.uncommittedDiseqcCommand.index:
						if currLnb.commandOrder.value == "ct":
							currLnb.commandOrder.value = "cut"
						elif currLnb.commandOrder.value == "tc":
							currLnb.commandOrder.value = "tcu"
					else:
						if currLnb.commandOrder.index & 1:
							currLnb.commandOrder.value = "tc"
						else:
							currLnb.commandOrder.value = "ct"
					self.list.append(getConfigListEntry(_("Command order"), currLnb.commandOrder))
					self.uncommittedDiseqcCommand = getConfigListEntry(_("Uncommitted DiSEqC command"), currLnb.uncommittedDiseqcCommand)
					self.list.append(self.uncommittedDiseqcCommand)
					self.list.append(getConfigListEntry(_("DiSEqC repeats"), currLnb.diseqcRepeats))
				if currLnb.diseqcMode.value == "1_2":
					self.list.append(getConfigListEntry(_("Longitude"), currLnb.longitude))
					self.list.append(getConfigListEntry(" ", currLnb.longitudeOrientation))
					self.list.append(getConfigListEntry(_("Latitude"), currLnb.latitude))
					self.list.append(getConfigListEntry(" ", currLnb.latitudeOrientation))
					if SystemInfo["CanMeasureFrontendInputPower"]:
						self.advancedPowerMeasurement = getConfigListEntry(_("Use Power Measurement"), currLnb.powerMeasurement)
						self.list.append(self.advancedPowerMeasurement)
						if currLnb.powerMeasurement.value:
							self.list.append(getConfigListEntry(_("Power threshold in mA"), currLnb.powerThreshold))
							self.turningSpeed = getConfigListEntry(_("Rotor turning speed"), currLnb.turningSpeed)
							self.list.append(self.turningSpeed)
							if currLnb.turningSpeed.value == "fast epoch":
								self.turnFastEpochBegin = getConfigListEntry(_("Begin time"), currLnb.fastTurningBegin)
								self.turnFastEpochEnd = getConfigListEntry(_("End time"), currLnb.fastTurningEnd)
								self.list.append(self.turnFastEpochBegin)
								self.list.append(self.turnFastEpochEnd)
					else:
						if currLnb.powerMeasurement.value:
							currLnb.powerMeasurement.value = False
							currLnb.powerMeasurement.save()
			self.advancedLof = getConfigListEntry(_("LOF"), currLnb.lof)
			self.list.append(self.advancedLof)
			if currLnb.lof.value == "user_defined":
				self.list.append(getConfigListEntry(_("LOF/L"), currLnb.lofl))
				self.list.append(getConfigListEntry(_("LOF/H"), currLnb.lofh))
				self.list.append(getConfigListEntry(_("Threshold"), currLnb.threshold))
#			self.list.append(getConfigListEntry(_("12V Output"), currLnb.output_12v))
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
		old_configured_sats = nimmanager.getConfiguredSats()
		self.run()
		new_configured_sats = nimmanager.getConfiguredSats()
		self.unconfed_sats = old_configured_sats - new_configured_sats
		self.satpos_to_remove = None
		self.deleteConfirmed(False)

	def deleteConfirmed(self, confirmed):
		if confirmed:
			eDVBDB.getInstance().removeServices(-1, -1, -1, self.satpos_to_remove)

		if self.satpos_to_remove is not None:
			self.unconfed_sats.remove(self.satpos_to_remove)

		self.satpos_to_remove = None
		for orbpos in self.unconfed_sats:
			self.satpos_to_remove = orbpos
			orbpos = self.satpos_to_remove
			try:
				# why we need this cast?
				sat_name = str(nimmanager.getSatDescription(orbpos))
			except:
				if orbpos > 1800: # west
					orbpos = 3600 - orbpos
					h = _("W")
				else:
					h = _("E")
				sat_name = ("%d.%d" + h) % (orbpos / 10, orbpos % 10)
			self.session.openWithCallback(self.deleteConfirmed, MessageBox, _("Delete no more configured satellite\n%s?") %(sat_name))
			break
		if not self.satpos_to_remove:
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

		self.slotid = slotid
		self.nim = nimmanager.nim_slots[slotid]
		self.nimConfig = self.nim.config
		self.createConfigMode()
		self.createSetup()
		# safeAll is needed, so that keyCancel works properly
		self.saveAll()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.newConfig()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.newConfig()

class NimSelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		
		menu = [ ]
		for x in nimmanager.nim_slots:
			menu.append((x.friendly_full_description, x))

		self["nimlist"] = MenuList(menu)

		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"ok": self.okbuttonClick ,
			"cancel": self.close
		}, -2)

	def okbuttonClick(self):
		nim = self["nimlist"].getCurrent()
		nim = nim and nim[1]
		if nim is not None and not nim.empty:
			self.session.open(NimSetup, nim.slot)
