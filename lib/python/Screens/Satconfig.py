from enigma import eDVBDB, getLinkedSlotID, eDVBResourceManager
from Screens.Screen import Screen
from Components.SystemInfo import SystemInfo
from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigListScreen
from Components.NimManager import nimmanager
from Components.Button import Button
from Components.Label import Label
from Components.SelectionList import SelectionList, SelectionEntryComponent
from Components.config import getConfigListEntry, config, ConfigNothing, ConfigYesNo, configfile, NoSave, ConfigSelection
from Components.Sources.StaticText import StaticText
from Components.Sources.List import List
from Screens.MessageBox import MessageBox
from Screens.ChoiceBox import ChoiceBox
from Screens.ServiceStopScreen import ServiceStopScreen
from Screens.AutoDiseqc import AutoDiseqc
from Tools.BoundFunction import boundFunction
from Tools.Directories import fileExists

from boxbranding import getImageType
from time import mktime, localtime, time
from datetime import datetime

class NimSetup(Screen, ConfigListScreen, ServiceStopScreen):
	def createSimpleSetup(self, list, mode):
		nim = self.nimConfig

		if mode == "single":
			self.singleSatEntry = getConfigListEntry(_("Satellite"), nim.diseqcA)
			list.append(self.singleSatEntry)
			if nim.diseqcA.value in ("360", "560"):
				list.append(getConfigListEntry(_("Use circular LNB"), nim.simpleDiSEqCSetCircularLNB))
			list.append(getConfigListEntry(_("Send DiSEqC"), nim.simpleSingleSendDiSEqC))
		else:
			list.append(getConfigListEntry(_("Port A"), nim.diseqcA))

		if mode in ("toneburst_a_b", "diseqc_a_b", "diseqc_a_b_c_d"):
			list.append(getConfigListEntry(_("Port B"), nim.diseqcB))
			if mode == "diseqc_a_b_c_d":
				list.append(getConfigListEntry(_("Port C"), nim.diseqcC))
				list.append(getConfigListEntry(_("Port D"), nim.diseqcD))
			if mode != "toneburst_a_b":
				list.append(getConfigListEntry(_("Set voltage and 22KHz"), nim.simpleDiSEqCSetVoltageTone))
				list.append(getConfigListEntry(_("Send DiSEqC only on satellite change"), nim.simpleDiSEqCOnlyOnSatChange))

	def createPositionerSetup(self, list):
		nim = self.nimConfig
		if nim.diseqcMode.value == "positioner_select":
			self.selectSatsEntry = getConfigListEntry(_("Press OK to select satellites"), self.nimConfig.pressOKtoList)
			list.append(self.selectSatsEntry)
		list.append(getConfigListEntry(_("Longitude"), nim.longitude))
		list.append(getConfigListEntry(" ", nim.longitudeOrientation))
		list.append(getConfigListEntry(_("Latitude"), nim.latitude))
		list.append(getConfigListEntry(" ", nim.latitudeOrientation))
		if SystemInfo["CanMeasureFrontendInputPower"]:
			self.advancedPowerMeasurement = getConfigListEntry(_("Use power measurement"), nim.powerMeasurement)
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
		if not hasattr(self, 'additionalMotorOptions'):
			self.additionalMotorOptions = NoSave(ConfigYesNo(False))
		self.showAdditionalMotorOptions = getConfigListEntry(_("Extra motor options"), self.additionalMotorOptions)
		self.list.append(self.showAdditionalMotorOptions)
		if self.additionalMotorOptions.value:
			self.list.append(getConfigListEntry("   " + _("Horizontal turning speed") + " [" + chr(176) + "/sec]", nim.turningspeedH))
			self.list.append(getConfigListEntry("   " + _("Vertical turning speed") + " [" + chr(176) + "/sec]", nim.turningspeedV))
			self.list.append(getConfigListEntry("   " + _("Turning step size") + " [" + chr(176) + "]", nim.tuningstepsize))
			self.list.append(getConfigListEntry("   " + _("Max memory positions"), nim.rotorPositions))

	def createConfigMode(self):
		if self.nim.isCompatible("DVB-S"):
			choices = {"nothing": _("Not configured"),
						"simple": _("Simple"),
						"advanced": _("Advanced")}
			if len(nimmanager.canEqualTo(self.slotid)) > 0:
				choices["equal"] = _("Equal to")
			if len(nimmanager.canDependOn(self.slotid)) > 0:
				choices["satposdepends"] = _("Second cable of motorized LNB")
			if len(nimmanager.canConnectTo(self.slotid)) > 0:
				choices["loopthrough"] = _("Loop through from")
			if self.nim.isFBCLink():
				choices = { "nothing": _("FBC automatic"), "advanced": _("FBC SCR (Unicable/JESS)")}
			self.nimConfig.configMode.setChoices(choices, self.nim.isFBCLink() and "nothing" or "simple")

	def createSetup(self):
		print "[Satconfig] Creating setup"
		self.list = [ ]

		self.multiType = None
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
		self.toneburst = None
		self.committedDiseqcCommand = None
		self.uncommittedDiseqcCommand = None
		self.commandOrder = None
		self.cableScanType = None
		self.cableConfigScanDetails = None
		self.have_advanced = False
		self.advancedUnicable = None
		self.advancedFormat = None
		self.advancedPosition = None
		self.advancedType = None
		self.advancedManufacturer = None
		self.advancedSCR = None
		self.advancedConnected = None
		self.showAdditionalMotorOptions = None
		self.selectSatsEntry = None
		self.advancedSelectSatsEntry = None
		self.singleSatEntry = None
		self.toneamplitude = None
		self.scpc = None
		self.forcelnbpower = None
		self.forcetoneburst = None
		self.terrestrialRegionsEntry = None
		self.cableRegionsEntry = None
		
		if not hasattr(self, "terrestrialCountriesEntry"):
			self.terrestrialCountriesEntry = None
		if not hasattr(self, "cableCountriesEntry"):
			self.cableCountriesEntry = None

		if self.nim.isMultiType():
			multiType = self.nimConfig.multiType
			self.multiType = getConfigListEntry(_("Tuner type"), multiType)
			self.list.append(self.multiType)

		if self.nim.isCompatible("DVB-S"):
			self.configMode = getConfigListEntry(_("Configuration mode"), self.nimConfig.configMode)
			self.list.append(self.configMode)

			if self.nimConfig.configMode.value == "simple":			#simple setup
				self.diseqcModeEntry = getConfigListEntry(pgettext("Satellite configuration mode", "Mode"), self.nimConfig.diseqcMode)
				self.list.append(self.diseqcModeEntry)
				if self.nimConfig.diseqcMode.value in ("single", "toneburst_a_b", "diseqc_a_b", "diseqc_a_b_c_d"):
					self.createSimpleSetup(self.list, self.nimConfig.diseqcMode.value)
				if self.nimConfig.diseqcMode.value in ("positioner", "positioner_select"):
					self.createPositionerSetup(self.list)
			elif self.nimConfig.configMode.value == "equal":
				choices = []
				nimlist = nimmanager.canEqualTo(self.nim.slot)
				for id in nimlist:
					choices.append((str(id), nimmanager.getNimDescription(id)))
				self.nimConfig.connectedTo.setChoices(choices)
				self.list.append(getConfigListEntry(_("Tuner"), self.nimConfig.connectedTo))
			elif self.nimConfig.configMode.value == "satposdepends":
				choices = []
				nimlist = nimmanager.canDependOn(self.nim.slot)
				for id in nimlist:
					choices.append((str(id), nimmanager.getNimDescription(id)))
				self.nimConfig.connectedTo.setChoices(choices)
				self.list.append(getConfigListEntry(_("Tuner"), self.nimConfig.connectedTo))
			elif self.nimConfig.configMode.value == "loopthrough":
				choices = []
				print "[Satconfig] connectable to:", nimmanager.canConnectTo(self.slotid)
				connectable = nimmanager.canConnectTo(self.slotid)
				for id in connectable:
					choices.append((str(id), nimmanager.getNimDescription(id)))
				self.nimConfig.connectedTo.setChoices(choices)
				self.list.append(getConfigListEntry(_("Connected to"), self.nimConfig.connectedTo))
			elif self.nimConfig.configMode.value == "nothing":
				pass
			elif self.nimConfig.configMode.value == "advanced": # advanced
				# SATs
				self.advancedSatsEntry = getConfigListEntry(_("Satellite"), self.nimConfig.advanced.sats)
				self.list.append(self.advancedSatsEntry)
				current_config_sats = self.nimConfig.advanced.sats.value
				if current_config_sats in ("3605", "3606"):
					self.advancedSelectSatsEntry = getConfigListEntry(_("Press OK to select satellites"), self.nimConfig.pressOKtoList)
					self.list.append(self.advancedSelectSatsEntry)
					self.fillListWithAdvancedSatEntrys(self.nimConfig.advanced.sat[int(current_config_sats)])
				else:
					cur_orb_pos = self.nimConfig.advanced.sats.orbital_position
					satlist = self.nimConfig.advanced.sat.keys()
					if cur_orb_pos is not None:
						if cur_orb_pos not in satlist:
							cur_orb_pos = satlist[0]
						self.fillListWithAdvancedSatEntrys(self.nimConfig.advanced.sat[cur_orb_pos])
				self.have_advanced = True
			if self.nimConfig.configMode.value != "nothing" and config.usage.setup_level.index >= 2:
				if fileExists("/proc/stb/frontend/%d/tone_amplitude" % self.nim.slot):
					self.toneamplitude = getConfigListEntry(_("Tone amplitude"), self.nimConfig.toneAmplitude)
					self.list.append(self.toneamplitude)
				if fileExists("/proc/stb/frontend/%d/use_scpc_optimized_search_range" % self.nim.slot):
					self.scpc = getConfigListEntry(_("SCPC optimized search range"), self.nimConfig.scpcSearchRange)
					self.list.append(self.scpc)
				if SystemInfo["HasForceLNBOn"] and self.nim.isFBCRoot():
					self.forcelnbpower = getConfigListEntry(_("Force LNB Power"), config.misc.forceLnbPower)
					self.list.append(self.forcelnbpower)
				if SystemInfo["HasForceToneburst"] and self.nim.isFBCRoot():
					self.forcetoneburst = getConfigListEntry(_("Force ToneBurst"), config.misc.forceToneBurst)
					self.list.append(self.forcetoneburst)
		elif self.nim.isCompatible("DVB-C"):
			self.configMode = getConfigListEntry(_("Configuration mode"), self.nimConfig.configMode)
			self.list.append(self.configMode)
			if self.nimConfig.configMode.value == "enabled":
				self.list.append(getConfigListEntry(_("Network ID"), self.nimConfig.cable.scan_networkid))
				self.cableScanType=getConfigListEntry(_("Used service scan type"), self.nimConfig.cable.scan_type)
				self.list.append(self.cableScanType)
				if self.nimConfig.cable.scan_type.value == "provider":
					# country/region tier one
					if self.cableCountriesEntry is None:
						cablecountrycodelist = nimmanager.getCablesCountrycodeList()
						cablecountrycode = nimmanager.getCableCountrycode(self.slotid)
						default = cablecountrycode in cablecountrycodelist and cablecountrycode or None
						choices = [("all", _("All"))]+sorted([(x, self.countrycodeToCountry(x)) for x in cablecountrycodelist], key=lambda listItem: listItem[1])
						self.cableCountries = ConfigSelection(default = default, choices = choices)
						self.cableCountriesEntry = getConfigListEntry(_("Country"), self.cableCountries)
						self.originalCableRegion = self.nimConfig.cable.scan_provider.value
					# country/region tier two
					if self.cableCountries.value == "all":
						cableNames = [x[0] for x in sorted(sorted(nimmanager.getCablesList(), key=lambda listItem: listItem[0]), key=lambda listItem: self.countrycodeToCountry(listItem[2]))]
					else:
						cableNames = sorted([x[0] for x in nimmanager.getCablesByCountrycode(self.cableCountries.value)])
					default = self.nimConfig.cable.scan_provider.value in cableNames and self.nimConfig.cable.scan_provider.value or None
					self.cableRegions = ConfigSelection(default = default, choices = cableNames)
					def updateCableProvider(configEntry):
						self.nimConfig.cable.scan_provider.value = configEntry.value
						self.nimConfig.cable.scan_provider.save()
					self.cableRegions.addNotifier(updateCableProvider)
					self.cableRegionsEntry = getConfigListEntry(_("Region"), self.cableRegions)
					self.list.append(self.cableCountriesEntry)
					self.list.append(self.cableRegionsEntry)
					#self.list.append(getConfigListEntry(_("Provider to scan"), self.nimConfig.cable.scan_provider))
				else:
					self.cableConfigScanDetails = getConfigListEntry(_("Config Scan Details"), self.nimConfig.cable.config_scan_details)
					self.list.append(self.cableConfigScanDetails)
					if self.nimConfig.cable.config_scan_details.value:
						if self.nimConfig.cable.scan_type.value == "bands":
							# TRANSLATORS: option name, indicating which type of (DVB-C) band should be scanned. The name of the band is printed in '%s'. E.g.: 'Scan EU MID band'
							self.list.append(getConfigListEntry(_("Scan %s band") % ("EU VHF I"), self.nimConfig.cable.scan_band_EU_VHF_I))
							self.list.append(getConfigListEntry(_("Scan %s band") % ("EU MID"), self.nimConfig.cable.scan_band_EU_MID))
							self.list.append(getConfigListEntry(_("Scan %s band") % ("EU VHF III"), self.nimConfig.cable.scan_band_EU_VHF_III))
							self.list.append(getConfigListEntry(_("Scan %s band") % ("EU UHF IV"), self.nimConfig.cable.scan_band_EU_UHF_IV))
							self.list.append(getConfigListEntry(_("Scan %s band") % ("EU UHF V"), self.nimConfig.cable.scan_band_EU_UHF_V))
							self.list.append(getConfigListEntry(_("Scan %s band") % ("EU SUPER"), self.nimConfig.cable.scan_band_EU_SUPER))
							self.list.append(getConfigListEntry(_("Scan %s band") % ("EU HYPER"), self.nimConfig.cable.scan_band_EU_HYPER))
							self.list.append(getConfigListEntry(_("Scan %s band") % ("US LOW"), self.nimConfig.cable.scan_band_US_LOW))
							self.list.append(getConfigListEntry(_("Scan %s band") % ("US MID"), self.nimConfig.cable.scan_band_US_MID))
							self.list.append(getConfigListEntry(_("Scan %s band") % ("US HIGH"), self.nimConfig.cable.scan_band_US_HIGH))
							self.list.append(getConfigListEntry(_("Scan %s band") % ("US SUPER"), self.nimConfig.cable.scan_band_US_SUPER))
							self.list.append(getConfigListEntry(_("Scan %s band") % ("US HYPER"), self.nimConfig.cable.scan_band_US_HYPER))
						else:
							self.list.append(getConfigListEntry(_("Frequency scan step size(khz)"), self.nimConfig.cable.scan_frequency_steps))
						# TRANSLATORS: option name, indicating which type of (DVB-C) modulation should be scanned. The modulation type is printed in '%s'. E.g.: 'Scan QAM16'
						self.list.append(getConfigListEntry(_("Scan %s") % ("QAM16"), self.nimConfig.cable.scan_mod_qam16))
						self.list.append(getConfigListEntry(_("Scan %s") % ("QAM32"), self.nimConfig.cable.scan_mod_qam32))
						self.list.append(getConfigListEntry(_("Scan %s") % ("QAM64"), self.nimConfig.cable.scan_mod_qam64))
						self.list.append(getConfigListEntry(_("Scan %s") % ("QAM128"), self.nimConfig.cable.scan_mod_qam128))
						self.list.append(getConfigListEntry(_("Scan %s") % ("QAM256"), self.nimConfig.cable.scan_mod_qam256))
						self.list.append(getConfigListEntry(_("Scan %s") % ("SR6900"), self.nimConfig.cable.scan_sr_6900))
						self.list.append(getConfigListEntry(_("Scan %s") % ("SR6875"), self.nimConfig.cable.scan_sr_6875))
						self.list.append(getConfigListEntry(_("Scan additional SR"), self.nimConfig.cable.scan_sr_ext1))
						self.list.append(getConfigListEntry(_("Scan additional SR"), self.nimConfig.cable.scan_sr_ext2))
			self.have_advanced = False
		elif self.nim.isCompatible("DVB-T"):
			self.configMode = getConfigListEntry(_("Configuration mode"), self.nimConfig.configMode)
			self.list.append(self.configMode)
			self.have_advanced = False
			if self.nimConfig.configMode.value == "enabled":
				# country/region tier one
				if self.terrestrialCountriesEntry is None:
					terrestrialcountrycodelist = nimmanager.getTerrestrialsCountrycodeList()
					terrestrialcountrycode = nimmanager.getTerrestrialCountrycode(self.slotid)
					default = terrestrialcountrycode in terrestrialcountrycodelist and terrestrialcountrycode or None
					choices = [("all", _("All"))]+sorted([(x, self.countrycodeToCountry(x)) for x in terrestrialcountrycodelist], key=lambda listItem: listItem[1])
					self.terrestrialCountries = ConfigSelection(default = default, choices = choices)
					self.terrestrialCountriesEntry = getConfigListEntry(_("Country"), self.terrestrialCountries)
					self.originalTerrestrialRegion = self.nimConfig.terrestrial.value
				# country/region tier two
				if self.terrestrialCountries.value == "all":
					terrstrialNames = [x[0] for x in sorted(sorted(nimmanager.getTerrestrialsList(), key=lambda listItem: listItem[0]), key=lambda listItem: self.countrycodeToCountry(listItem[2]))]
				else:
					terrstrialNames = sorted([x[0] for x in nimmanager.getTerrestrialsByCountrycode(self.terrestrialCountries.value)])
				default = self.nimConfig.terrestrial.value in terrstrialNames and self.nimConfig.terrestrial.value or None
				self.terrestrialRegions = ConfigSelection(default = default, choices = terrstrialNames)
				def updateTerrestrialProvider(configEntry):
					self.nimConfig.terrestrial.value = configEntry.value
					self.nimConfig.terrestrial.save()
				self.terrestrialRegions.addNotifier(updateTerrestrialProvider)
				self.terrestrialRegionsEntry = getConfigListEntry(_("Region"), self.terrestrialRegions)
				self.list.append(self.terrestrialCountriesEntry)
				self.list.append(self.terrestrialRegionsEntry)
				#self.list.append(getConfigListEntry(_("Terrestrial provider"), self.nimConfig.terrestrial))
				self.list.append(getConfigListEntry(_("Enable 5V for active antenna"), self.nimConfig.terrestrial_5V))
		elif self.nim.isCompatible("ATSC"):
			self.configMode = getConfigListEntry(_("Configuration mode"), self.nimConfig.configMode)
			self.list.append(self.configMode)
			if self.nimConfig.configMode.value == "enabled":
				self.list.append(getConfigListEntry(_("ATSC provider"), self.nimConfig.atsc))
			self.have_advanced = False
		else:
			self.have_advanced = False
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	def newConfig(self):
		self.setTextKeyBlue()
		if self["config"].getCurrent() == self.multiType:
			update_slots = [self.slotid]
			from Components.NimManager import InitNimManager
			InitNimManager(nimmanager, update_slots)
			self.nim = nimmanager.nim_slots[self.slotid]
			self.nimConfig = self.nim.config
		if self["config"].getCurrent() in (self.configMode, self.diseqcModeEntry, self.advancedSatsEntry, self.advancedLnbsEntry, self.advancedDiseqcMode, self.advancedUsalsEntry,\
			self.advancedLof, self.advancedPowerMeasurement, self.turningSpeed, self.advancedType, self.advancedSCR, self.advancedPosition, self.advancedFormat, self.advancedManufacturer,\
			self.advancedUnicable, self.advancedConnected, self.toneburst, self.committedDiseqcCommand, self.uncommittedDiseqcCommand, self.singleSatEntry,	self.commandOrder,\
			self.showAdditionalMotorOptions, self.cableScanType, self.multiType, self.cableConfigScanDetails, self.terrestrialCountriesEntry, self.cableCountriesEntry, \
			self.toneamplitude, self.scpc, self.forcelnbpower, self.forcetoneburst):
			       self.createSetup()

	def run(self):
		if self.nimConfig.configMode.value == "simple":
			autodiseqc_ports = 0
			if self.nimConfig.diseqcMode.value == "single":
				if self.nimConfig.diseqcA.orbital_position == 3600:
					autodiseqc_ports = 1
			elif self.nimConfig.diseqcMode.value == "diseqc_a_b":
				if self.nimConfig.diseqcA.orbital_position == 3600 or self.nimConfig.diseqcB.orbital_position == 3600:
					autodiseqc_ports = 2
			elif self.nimConfig.diseqcMode.value == "diseqc_a_b_c_d":
				if self.nimConfig.diseqcA.orbital_position == 3600 or self.nimConfig.diseqcB.orbital_position == 3600 or self.nimConfig.diseqcC.orbital_position == 3600 or self.nimConfig.diseqcD.orbital_position == 3600:
					autodiseqc_ports = 4
			if autodiseqc_ports:
				self.autoDiseqcRun(autodiseqc_ports)
				return False
		if self.have_advanced and self.nim.config_mode == "advanced":
			self.fillAdvancedList()
		for x in self.list:
			if x in (self.turnFastEpochBegin, self.turnFastEpochEnd):
				# workaround for storing only hour*3600+min*60 value in configfile
				# not really needed.. just for cosmetics..
				tm = localtime(x[1].value)
				dt = datetime(1970, 1, 1, tm.tm_hour, tm.tm_min)
				x[1].value = int(mktime(dt.timetuple()))
			x[1].save()
		nimmanager.sec.update()
		self.saveAll()
		return True

	def autoDiseqcRun(self, ports):
		self.session.openWithCallback(self.autoDiseqcCallback, AutoDiseqc, self.slotid, ports, self.nimConfig.simpleDiSEqCSetVoltageTone, self.nimConfig.simpleDiSEqCOnlyOnSatChange)

	def autoDiseqcCallback(self, result):
		from Screens.Wizard import Wizard
		if Wizard.instance is not None:
			Wizard.instance.back()
		else:
			self.createSetup()

	def fillListWithAdvancedSatEntrys(self, Sat):
		lnbnum = int(Sat.lnb.value)
		currLnb = self.nimConfig.advanced.lnb[lnbnum]

		if isinstance(currLnb, ConfigNothing):
			currLnb = None

		# LNBs
		self.advancedLnbsEntry = getConfigListEntry(_("LNB"), Sat.lnb)
		self.list.append(self.advancedLnbsEntry)

		if currLnb:
			if self.nim.isFBCLink():
				currLnb.lof.value = "unicable"
			self.list.append(getConfigListEntry(_("Priority"), currLnb.prio))
			self.advancedLof = getConfigListEntry("LOF", currLnb.lof)
			self.list.append(self.advancedLof)
			if currLnb.lof.value == "user_defined":
				self.list.append(getConfigListEntry("LOF/L", currLnb.lofl))
				self.list.append(getConfigListEntry("LOF/H", currLnb.lofh))
				self.list.append(getConfigListEntry(_("Threshold"), currLnb.threshold))

			if currLnb.lof.value == "unicable":
				self.advancedUnicable = getConfigListEntry("SCR (Unicable/JESS) "+_("type"), currLnb.unicable)
				self.list.append(self.advancedUnicable)
				if currLnb.unicable.value == "unicable_user":
					self.advancedFormat = getConfigListEntry(_("Format"), currLnb.format)
					self.advancedPosition = getConfigListEntry(_("Position"), currLnb.positionNumber)
					self.advancedSCR = getConfigListEntry(_("Channel"), currLnb.scrList)
					self.list.append(self.advancedFormat)
					self.list.append(self.advancedPosition)
					self.list.append(self.advancedSCR)
					self.list.append(getConfigListEntry(_("Frequency"), currLnb.scrfrequency))
					self.list.append(getConfigListEntry("LOF/L", currLnb.lofl))
					self.list.append(getConfigListEntry("LOF/H", currLnb.lofh))
					self.list.append(getConfigListEntry(_("Threshold"), currLnb.threshold))
				else:
					self.advancedManufacturer = getConfigListEntry(_("Manufacturer"), currLnb.unicableManufacturer)
					self.advancedType = getConfigListEntry(_("Model"), currLnb.unicableProduct)
					self.advancedSCR = getConfigListEntry(_("Channel"), currLnb.scrList)
					self.advancedPosition = getConfigListEntry(_("Position"), currLnb.positionNumber)
					self.list.append(self.advancedManufacturer)
					self.list.append(self.advancedType)
					if currLnb.positions.value > 1:
						self.list.append(self.advancedPosition)
					self.list.append(self.advancedSCR)
				choices = []
				connectable = nimmanager.canConnectTo(self.slotid)
				for id in connectable:
					choices.append((str(id), nimmanager.getNimDescription(id)))
				if len(choices):
					if self.nim.isFBCLink():
						if self.nimConfig.advanced.unicableconnected.value != True:
							self.nimConfig.advanced.unicableconnected.value = True
					self.advancedConnected = getConfigListEntry(_("connected"), self.nimConfig.advanced.unicableconnected)
					self.list.append(self.advancedConnected)
					if self.nimConfig.advanced.unicableconnected.value:
						self.nimConfig.advanced.unicableconnectedTo.setChoices(choices)
						self.list.append(getConfigListEntry(_("Connected to"),self.nimConfig.advanced.unicableconnectedTo))

			else:	#kein Unicable
				self.list.append(getConfigListEntry(_("Voltage mode"), Sat.voltage))
				self.list.append(getConfigListEntry(_("Increased voltage"), currLnb.increased_voltage))
				self.list.append(getConfigListEntry(_("Tone mode"), Sat.tonemode))

			if lnbnum < 65:
				self.advancedDiseqcMode = getConfigListEntry(_("DiSEqC mode"), currLnb.diseqcMode)
				self.list.append(self.advancedDiseqcMode)
			if currLnb.diseqcMode.value != "none":
				self.list.append(getConfigListEntry(_("Fast DiSEqC"), currLnb.fastDiseqc))
				self.toneburst = getConfigListEntry(_("Toneburst"), currLnb.toneburst)
				self.list.append(self.toneburst)
				self.committedDiseqcCommand = getConfigListEntry(_("DiSEqC 1.0 command"), currLnb.commitedDiseqcCommand)
				self.list.append(self.committedDiseqcCommand)
				if currLnb.diseqcMode.value == "1_0":
					if currLnb.toneburst.index and currLnb.commitedDiseqcCommand.index:
						self.list.append(getConfigListEntry(_("Command order"), currLnb.commandOrder1_0))
				else:
					self.uncommittedDiseqcCommand = getConfigListEntry(_("DiSEqC 1.1 command"), currLnb.uncommittedDiseqcCommand)
					self.list.append(self.uncommittedDiseqcCommand)
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
					self.commandOrder = getConfigListEntry(_("Command order"), currLnb.commandOrder)
					if 1 < ((1 if currLnb.uncommittedDiseqcCommand.index else 0) + (1 if currLnb.commitedDiseqcCommand.index else 0) + (1 if currLnb.toneburst.index else 0)):
						self.list.append(self.commandOrder)
					if currLnb.uncommittedDiseqcCommand.index:
						self.list.append(getConfigListEntry(_("DiSEqC 1.1 repeats"), currLnb.diseqcRepeats))
				self.list.append(getConfigListEntry(_("Sequence repeat"), currLnb.sequenceRepeat))
				if currLnb.diseqcMode.value == "1_2":
					if SystemInfo["CanMeasureFrontendInputPower"]:
						self.advancedPowerMeasurement = getConfigListEntry(_("Use power measurement"), currLnb.powerMeasurement)
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
					self.advancedUsalsEntry = getConfigListEntry(_("Use USALS for this sat"), Sat.usals)
					if lnbnum < 65:
						self.list.append(self.advancedUsalsEntry)
					if Sat.usals.value:
						self.list.append(getConfigListEntry(_("Longitude"), currLnb.longitude))
						self.list.append(getConfigListEntry(" ", currLnb.longitudeOrientation))
						self.list.append(getConfigListEntry(_("Latitude"), currLnb.latitude))
						self.list.append(getConfigListEntry(" ", currLnb.latitudeOrientation))
					else:
						self.list.append(getConfigListEntry(_("Stored position"), Sat.rotorposition))
					if not hasattr(self, 'additionalMotorOptions'):
						self.additionalMotorOptions = NoSave(ConfigYesNo(False))
					self.showAdditionalMotorOptions = getConfigListEntry(_("Extra motor options"), self.additionalMotorOptions)
					self.list.append(self.showAdditionalMotorOptions)
					if self.additionalMotorOptions.value:
						self.list.append(getConfigListEntry("   " + _("Horizontal turning speed") + " [" + chr(176) + "/sec]", currLnb.turningspeedH))
						self.list.append(getConfigListEntry("   " + _("Vertical turning speed") + " [" + chr(176) + "/sec]", currLnb.turningspeedV))
						self.list.append(getConfigListEntry("   " + _("Turning step size") + " [" + chr(176) + "]", currLnb.tuningstepsize))
						self.list.append(getConfigListEntry("   " + _("Max memory positions"), currLnb.rotorPositions))

	def fillAdvancedList(self):
		self.list = [ ]
		self.configMode = getConfigListEntry(_("Configuration mode"), self.nimConfig.configMode)
		self.list.append(self.configMode)
		self.advancedSatsEntry = getConfigListEntry(_("Satellite"), self.nimConfig.advanced.sats)
		self.list.append(self.advancedSatsEntry)
		for x in self.nimConfig.advanced.sat.keys():
			Sat = self.nimConfig.advanced.sat[x]
			self.fillListWithAdvancedSatEntrys(Sat)
		self["config"].list = self.list

	def checkLoopthrough(self):
		if self.nimConfig.configMode.value == "loopthrough":
			loopthrough_count = 0
			dvbs_slots = nimmanager.getNimListOfType('DVB-S')
			dvbs_slots_len = len(dvbs_slots)

			for x in dvbs_slots:
				try:
					nim_slot = nimmanager.nim_slots[x]
					if nim_slot == self.nimConfig:
						self_idx = x
					if nim_slot.config.configMode.value == "loopthrough":
						loopthrough_count += 1
				except: pass
			if loopthrough_count >= dvbs_slots_len:
				return False

		self.slot_dest_list = []
		def checkRecursiveConnect(slot_id):
			if slot_id in self.slot_dest_list:
				return False
			self.slot_dest_list.append(slot_id)
			slot_config = nimmanager.nim_slots[slot_id].config
			if slot_config.configMode.value == "loopthrough":
				return checkRecursiveConnect(int(slot_config.connectedTo.value))
			return True

		return checkRecursiveConnect(self.slotid)

	def keyOk(self):
		self.stopService()
		if self["config"].getCurrent() == self.advancedSelectSatsEntry:
			conf = self.nimConfig.advanced.sat[int(self.nimConfig.advanced.sats.value)].userSatellitesList
			self.session.openWithCallback(boundFunction(self.updateConfUserSatellitesList, conf), SelectSatsEntryScreen, userSatlist=conf.value)
		elif self["config"].getCurrent() == self.selectSatsEntry:
			conf = self.nimConfig.userSatellitesList
			self.session.openWithCallback(boundFunction(self.updateConfUserSatellitesList, conf), SelectSatsEntryScreen, userSatlist=conf.value)
		else:
			self.keySave()

	def updateConfUserSatellitesList(self, conf, val=None):
		if val is not None:
			conf.value = val
			conf.save()

	def keySave(self):
		self.stopService()
		if not self.checkLoopthrough():
			self.session.open(MessageBox, _("The loopthrough setting is wrong."),MessageBox.TYPE_ERROR,timeout=10)
			return
		old_configured_sats = nimmanager.getConfiguredSats()
		if not self.run():
			return
		new_configured_sats = nimmanager.getConfiguredSats()
		self.unconfed_sats = old_configured_sats - new_configured_sats
		self.satpos_to_remove = None
		self.deleteConfirmed((None, "no"))

	def deleteConfirmed(self, confirmed):
		if confirmed is None:
			confirmed = (None, "no")

		if confirmed[1] == "yes" or confirmed[1] == "yestoall":
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

			if confirmed[1] == "yes" or confirmed[1] == "no":
				# TRANSLATORS: The satellite with name '%s' is no longer used after a configuration change. The user is asked whether or not the satellite should be deleted.
				self.session.openWithCallback(self.deleteConfirmed, ChoiceBox, _("%s is no longer used. Should it be deleted?") % sat_name, [(_("Yes"), "yes"), (_("No"), "no"), (_("Yes to all"), "yestoall"), (_("No to all"), "notoall")], None, 1)
			if confirmed[1] == "yestoall" or confirmed[1] == "notoall":
				self.deleteConfirmed(confirmed)
			break
		else:
			self.restartPrevService()

	def __init__(self, session, slotid, menu_path=""):
		Screen.__init__(self, session)
		screentitle = _("Tuner settings")
		if config.usage.show_menupath.value == 'large':
			menu_path += screentitle
			title = menu_path
			self["menu_path_compressed"] = StaticText("")
		elif config.usage.show_menupath.value == 'small':
			title = screentitle
			self["menu_path_compressed"] = StaticText(menu_path + " >" if not menu_path.endswith(' / ') else menu_path[:-3] + " >" or "")
		else:
			title = screentitle
			self["menu_path_compressed"] = StaticText("")
		Screen.setTitle(self, title)

		self.list = [ ]
		ServiceStopScreen.__init__(self)
		ConfigListScreen.__init__(self, self.list)

		self["key_red"] = Label(_("Close"))
		self["key_green"] = Label(_("Save"))
		self["key_yellow"] = Label(_("Configuration mode"))
		self["key_blue"] = Label()

		self["actions"] = ActionMap(["SetupActions", "SatlistShortcutAction", "ColorActions"],
		{
			"ok": self.keyOk,
			"save": self.keySave,
			"cancel": self.keyCancel,
			"changetype": self.changeConfigurationMode,
			"nothingconnected": self.nothingConnectedShortcut,
			"red": self.keyCancel,
			"green": self.keySave,
		}, -2)

		self.slotid = slotid
		self.nim = nimmanager.nim_slots[slotid]
		self.nimConfig = self.nim.config
		self.createConfigMode()
		self.createSetup()
		self.setTitle(_("Setup") + " " + self.nim.friendly_full_description)

	def keyLeft(self):
		if self.nim.isFBCLink() and self["config"].getCurrent() in (self.advancedLof, self.advancedConnected):
			return
		ConfigListScreen.keyLeft(self)
		if self["config"].getCurrent() in (self.advancedSelectSatsEntry, self.selectSatsEntry):
			self.keyOk()
		else:
			self.newConfig()

	def setTextKeyBlue(self):
		self["key_blue"].setText("")
		if self["config"].isChanged():
			self["key_blue"].setText(_("Set default"))

	def keyRight(self):
		if self.nim.isFBCLink() and self["config"].getCurrent() in (self.advancedLof, self.advancedConnected):
			return
		ConfigListScreen.keyRight(self)
		if self["config"].getCurrent() in (self.advancedSelectSatsEntry, self.selectSatsEntry):
			self.keyOk()
		else:
			self.newConfig()

	def handleKeyFileCallback(self, answer):
		ConfigListScreen.handleKeyFileCallback(self, answer)
		self.newConfig()

	def keyCancel(self):
		if self["config"].isChanged():
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"), default = False)
		else:
			self.restartPrevService()

	def isChanged(self):
		is_changed = False
		for x in self["config"].list:
			if x == self.showAdditionalMotorOptions:
				continue
			is_changed |= x[1].isChanged()
		return is_changed

	def saveAll(self):
		if self.nim.isCompatible("DVB-S"):
			# reset connectedTo to all choices to properly store the default value
			choices = []
			nimlist = nimmanager.getNimListOfType("DVB-S", self.slotid)
			for id in nimlist:
				choices.append((str(id), nimmanager.getNimDescription(id)))
			self.nimConfig.connectedTo.setChoices(choices)
			# sanity check for empty sat list
			if self.nimConfig.configMode.value != "satposdepends" and len(nimmanager.getSatListForNim(self.slotid)) < 1:
				self.nimConfig.configMode.value = "nothing"
			if self.nim.isFBCRoot():
				if SystemInfo["HasForceLNBOn"]:
					config.misc.forceLnbPower.save()
				if SystemInfo["HasForceToneburst"]:
					config.misc.forceToneBurst.save()
		for x in self["config"].list:
			x[1].save()
		configfile.save()

	def cancelConfirm(self, result):
		if not result:
			return
		for x in self["config"].list:
			x[1].cancel()
		if hasattr(self, "originalTerrestrialRegion"):
			self.nimConfig.terrestrial.value = self.originalTerrestrialRegion
			self.nimConfig.terrestrial.save()
		if hasattr(self, "originalCableRegion"):
			self.nimConfig.cable.scan_provider.value = self.originalCableRegion
			self.nimConfig.cable.scan_provider.save()
		# we need to call saveAll to reset the connectedTo choices
		self.saveAll()
		self.restartPrevService()

	def changeConfigurationMode(self):
		if self.configMode:
			self.nimConfig.configMode.selectNext()
			self["config"].invalidate(self.configMode)
			self.setTextKeyBlue()
			self.createSetup()

	def nothingConnectedShortcut(self):
		if self.isChanged():
			for x in self["config"].list:
				x[1].cancel()
			self.setTextKeyBlue()
			self.createSetup()

	def countrycodeToCountry(self, cc):
		if not hasattr(self, 'countrycodes'):
			self.countrycodes = {}
			from Tools.CountryCodes import ISO3166
			for country in ISO3166:
				self.countrycodes[country[2]] = country[0]
		if cc.upper() in self.countrycodes:
			return self.countrycodes[cc.upper()]
		return cc

class NimSelection(Screen):
	def __init__(self, session, menu_path=""):
		Screen.__init__(self, session)
		screentitle = _("Tuner setup")
		self.menu_path = menu_path
		if config.usage.show_menupath.value == 'large':
			self.menu_path += screentitle
			title = self.menu_path
			self["menu_path_compressed"] = StaticText("")
			self.menu_path += ' / '
		elif config.usage.show_menupath.value == 'small':
			title = screentitle
			condtext = ""
			if self.menu_path and not self.menu_path.endswith(' / '):
				condtext = self.menu_path + " >"
			elif self.menu_path:
				condtext = self.menu_path[:-3] + " >"
			self["menu_path_compressed"] = StaticText(condtext)
			self.menu_path += screentitle + ' / '
		else:
			title = screentitle
			self["menu_path_compressed"] = StaticText("")
		Screen.setTitle(self, title)

		self.list = [None] * nimmanager.getSlotCount()
		self["nimlist"] = List(self.list)
		self.updateList()

		self.setResultClass()

		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Select"))
		self["key_yellow"] = StaticText(_("Client mode"))

		self["actions"] = ActionMap(["SetupActions", "ColorActions", "MenuActions", "ChannelSelectEPGActions"],
		{
			"ok": self.okbuttonClick,
			"info": self.extraInfo,
			"epg": self.extraInfo,
			"cancel": self.close,
			"red": self.close,
			"green": self.okbuttonClick,
			"menu": self.exit,
			"yellow": self.clientmode,
		}, -2)

	def clientmode(self):
		from Screens.ClientMode import ClientModeScreen
		self.session.open(ClientModeScreen, self.menu_path)

	def exit(self):
		self.close(True)

	def setResultClass(self):
		self.resultclass = NimSetup

	def OrbToStr(self, orbpos=-1):
		if orbpos == -1 or orbpos > 3600: return "??"
		if orbpos > 1800:
			orbpos = 3600 - orbpos
			return "%d.%dW" % (orbpos/10, orbpos%10)
		return "%d.%dE" % (orbpos/10, orbpos%10)

	def extraInfo(self):
		nim = self["nimlist"].getCurrent()
		nim = nim and nim[3]
		if config.usage.setup_level.index >= 2 and nim is not None:
			text = _("Capabilities: ") + eDVBResourceManager.getInstance().getFrontendCapabilities(nim.slot)
			self.session.open(MessageBox, text, MessageBox.TYPE_INFO, simple=True)

	def okbuttonClick(self):
		recordings = self.session.nav.getRecordings()
		next_rec_time = self.session.nav.RecordTimer.getNextRecordingTime()
		if recordings or (next_rec_time and next_rec_time > 0 and (next_rec_time - time()) < 360):
			if getImageType() == 'release':
				self.session.open(MessageBox, _("Recording(s) are in progress or coming up in few seconds!"), MessageBox.TYPE_INFO, timeout=5, enable_input=False)
			else:
				message = _("Recording(s) are in progress or coming up in few seconds!")
				ybox = self.session.openWithCallback(self.processok, MessageBox, message, MessageBox.TYPE_YESNO)
				ybox.setTitle(_("Are You Sure ?"))
		else:
			self.processok(True)

	def processok(self, answer=False):
		if answer is True:
			nim = self["nimlist"].getCurrent()
			nim = nim and nim[3]

			nimConfig = nimmanager.getNimConfig(nim.slot)
			if nim.isFBCLink() and nimConfig.configMode.value == "nothing" and not getLinkedSlotID(nim.slot) == -1:
				return

			if nim is not None and not nim.empty and nim.isSupported():
				self.session.openWithCallback(boundFunction(self.NimSetupCB, self["nimlist"].getIndex()), self.resultclass, nim.slot)

	def NimSetupCB(self, index=None):
		self.updateList(index)

	def showNim(self, nim):
		return True

	def updateList(self, index=None):
		self.list = [ ]
		for x in nimmanager.nim_slots:
			slotid = x.slot
			nimConfig = nimmanager.getNimConfig(x.slot)
			text = nimConfig.configMode.value
			if self.showNim(x):
				if x.isCompatible("DVB-S"):
					if nimConfig.configMode.value in ("loopthrough", "equal", "satposdepends"):
						if x.isFBCLink():
							text = _("FBC automatic\nconnected to")
						else:
							text = { "loopthrough": _("Loop through from"),
									"equal": _("Equal to"),
									"satposdepends": _("Second cable of motorized LNB") } [nimConfig.configMode.value]
						text += " " + nimmanager.getNim(int(nimConfig.connectedTo.value)).slot_name
					elif nimConfig.configMode.value == "nothing":
						if x.isFBCLink():
							link = getLinkedSlotID(x.slot)
							if link == -1:
								text = _("FBC automatic\ninactive")
							else:
								link = nimmanager.getNim(link).slot_name
								text = _("FBC automatic\nconnected to %s") % link
						else:
							text = _("not configured")
					elif nimConfig.configMode.value == "simple":
						if nimConfig.diseqcMode.value in ("single", "toneburst_a_b", "diseqc_a_b", "diseqc_a_b_c_d"):
							text = {"single": _("Single"), "toneburst_a_b": _("Toneburst A/B"), "diseqc_a_b": _("DiSEqC A/B"), "diseqc_a_b_c_d": _("DiSEqC A/B/C/D")}[nimConfig.diseqcMode.value] + "\n"
							text += _("Sats") + ": "
							satnames = []
							if nimConfig.diseqcA.orbital_position < 3600:
								satnames.append(nimmanager.getSatName(int(nimConfig.diseqcA.value)))
							if nimConfig.diseqcMode.value in ("toneburst_a_b", "diseqc_a_b", "diseqc_a_b_c_d"):
								if nimConfig.diseqcB.orbital_position < 3600:
									satnames.append(nimmanager.getSatName(int(nimConfig.diseqcB.value)))
							if nimConfig.diseqcMode.value == "diseqc_a_b_c_d":
								if nimConfig.diseqcC.orbital_position < 3600:
									satnames.append(nimmanager.getSatName(int(nimConfig.diseqcC.value)))
								if nimConfig.diseqcD.orbital_position < 3600:
									satnames.append(nimmanager.getSatName(int(nimConfig.diseqcD.value)))
							if len(satnames) <= 2:
								text += ", ".join(satnames)
							elif len(satnames) > 2:
								# we need a newline here, since multi content lists don't support automtic line wrapping
								text += ", ".join(satnames[:2]) + ",\n"
								text += "         " + ", ".join(satnames[2:])
						elif nimConfig.diseqcMode.value in ("positioner", "positioner_select"):
							text = {"positioner": _("Positioner"), "positioner_select": _("Positioner (selecting satellites)")}[nimConfig.diseqcMode.value]
							text += ": "
							if nimConfig.positionerMode.value == "usals":
								text += "USALS"
							elif nimConfig.positionerMode.value == "manual":
								text += _("Manual")
						else:
							text = _("Simple")
					elif nimConfig.configMode.value == "advanced":
						text = _("Advanced") + "\n"
						text += _("Sats") + ": "
						satnames = []
						for sat in nimmanager.getSatListForNim(slotid):
							satnames.append(self.OrbToStr(int(sat[0])))
						text += ", ".join(satnames)
				elif x.isCompatible("DVB-T") or x.isCompatible("DVB-C") or x.isCompatible("ATSC"):
					if nimConfig.configMode.value == "nothing":
						text = _("Nothing connected")
					elif nimConfig.configMode.value == "enabled":
						text = _("Enabled")
				if x.isMultiType():
					text = _("Switchable tuner types:") + " (" + ','.join(x.getMultiTypeList().values()) + ")" + "\n" + text
				if not x.isSupported():
					text = _("Tuner is not supported")

				self.list.append((slotid, x.friendly_full_description, text, x))
		self["nimlist"].setList(self.list)
		self["nimlist"].updateList(self.list)
		if index is not None:
			self["nimlist"].setIndex(index)

class SelectSatsEntryScreen(Screen):
	skin = """
		<screen name="SelectSatsEntryScreen" position="center,center" size="560,410" title="Select Sats Entry" >
			<ePixmap name="red" position="0,0"   zPosition="2" size="140,40" pixmap="skin_default/buttons/red.png" transparent="1" alphatest="on" />
			<ePixmap name="green" position="140,0" zPosition="2" size="140,40" pixmap="skin_default/buttons/green.png" transparent="1" alphatest="on" />
			<ePixmap name="yellow" position="280,0" zPosition="2" size="140,40" pixmap="skin_default/buttons/yellow.png" transparent="1" alphatest="on" />
			<ePixmap name="blue" position="420,0" zPosition="2" size="140,40" pixmap="skin_default/buttons/blue.png" transparent="1" alphatest="on" />
			<widget name="key_red" position="0,0" size="140,40" valign="center" halign="center" zPosition="4"  foregroundColor="white" font="Regular;17" transparent="1" shadowColor="background" shadowOffset="-2,-2" />
			<widget name="key_green" position="140,0" size="140,40" valign="center" halign="center" zPosition="4" foregroundColor="white" font="Regular;17" transparent="1" shadowColor="background" shadowOffset="-2,-2" />
			<widget name="key_yellow" position="280,0" size="140,40" valign="center" halign="center" zPosition="4" foregroundColor="white" font="Regular;17" transparent="1" shadowColor="background" shadowOffset="-2,-2" />
			<widget name="key_blue" position="420,0" size="140,40" valign="center" halign="center" zPosition="4" foregroundColor="white" font="Regular;17" transparent="1" shadowColor="background" shadowOffset="-2,-2" />
			<widget name="list" position="10,40" size="540,330" scrollbarMode="showNever" />
			<ePixmap pixmap="skin_default/div-h.png" position="0,375" zPosition="1" size="540,2" transparent="1" alphatest="on" />
			<widget name="hint" position="10,380" size="540,25" font="Regular;19" halign="center" transparent="1" />
		</screen>"""
	def __init__(self, session, menu_path="", userSatlist=""):
		Screen.__init__(self, session)
		screentitle = _("Select satellites")
		if config.usage.show_menupath.value == 'large':
			menu_path += screentitle
			title = menu_path
			self["menu_path_compressed"] = StaticText("")
		elif config.usage.show_menupath.value == 'small':
			title = screentitle
			self["menu_path_compressed"] = StaticText(menu_path + " >" if not menu_path.endswith(' / ') else menu_path[:-3] + " >" or "")
		else:
			title = screentitle
			self["menu_path_compressed"] = StaticText("")
		Screen.setTitle(self, title)

		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("Save"))
		self["key_yellow"] = Button(_("Sort by"))
		self["key_blue"] = Button(_("Select all"))
		self["hint"] = Label(_("Press OK to toggle the selection"))
		SatList = []
		if not isinstance(userSatlist, str):
			userSatlist = ""
		else:
			userSatlist = userSatlist.replace("]", "").replace("[", "")
		for sat in nimmanager.getSatList():
			selected = False
			sat_str = str(sat[0])
			if userSatlist and ("," not in userSatlist and sat_str == userSatlist) or ((', ' + sat_str + ',' in userSatlist) or (userSatlist.startswith(sat_str + ',')) or (userSatlist.endswith(', ' + sat_str))):
				selected = True
			SatList.append((sat[0], sat[1], sat[2], selected))
		sat_list = [SelectionEntryComponent(x[1], x[0], x[2], x[3]) for x in SatList]
		self["list"] = SelectionList(sat_list, enableWrapAround=True)
		self["setupActions"] = ActionMap(["SetupActions", "ColorActions"],
		{
			"red": self.cancel,
			"green": self.save,
			"yellow": self.sortBy,
			"blue": self["list"].toggleAllSelection,
			"save": self.save,
			"cancel": self.cancel,
			"ok": self["list"].toggleSelection,
		}, -2)

	def save(self):
		val = [x[0][1] for x in self["list"].list if x[0][3]]
		self.close(str(val))

	def cancel(self):
		self.close(None)

	def sortBy(self):
		lst = self["list"].list
		if len(lst) > 1:
			menu = [(_("Reverse list"), "2"), (_("Standart list"), "1")]
			connected_sat = [x[0][1] for x in lst if x[0][3]]
			if len(connected_sat) > 0:
				menu.insert(0,(_("Connected satellites"), "3"))
			def sortAction(choice):
				if choice:
					reverse_flag = False
					sort_type = int(choice[1])
					if choice[1] == "2":
						sort_type = reverse_flag = 1
					elif choice[1] == "3":
						reverse_flag = not reverse_flag
					self["list"].sort(sortType=sort_type, flag=reverse_flag)
					self["list"].moveToIndex(0)
			self.session.openWithCallback(sortAction, ChoiceBox, title= _("Select sort method:"), list=menu)
