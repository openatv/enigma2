from copy import deepcopy
from datetime import datetime
from os.path import exists
from time import localtime, mktime, time

from enigma import eDVBDB, eDVBResourceManager, eStreamServer, eTimer, getLinkedSlotID, isFBCLink

from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.config import ConfigBoolean, ConfigNothing, ConfigSelection, config, configfile, getConfigListEntry
from Components.ConfigList import ConfigListScreen
from Components.International import international
from Components.Label import Label
from Components.NimManager import InitNimManager, LNB_CHOICES, MAX_LNB_WILDCARDS, UNICABLE_CHOICES, inputPowerSlotForNim, maxFixedLnbPositions, nimmanager
from Components.SelectionList import SelectionEntryComponent, SelectionList
from Components.SystemInfo import BoxInfo
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Screens.AutoDiseqc import AutoDiseqc
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Setup import SetupSummary
from Tools.BoundFunction import boundFunction
from Tools.BugHunting import printCallSequence


class ConfigReadOnlyValue(ConfigSelection):
	def __init__(self):
		ConfigSelection.__init__(self, choices=[("", "")], default="")

	def isChanged(self):
		return False

	def save(self):  # Overwrite to force read only
		pass

	def cancel(self):  # Overwrite to force read only
		pass


class ServiceStopScreen:
	def __init__(self):
		try:
			self.session
		except Exception:
			print("[SatConfig] ServiceStopScreen ERROR: No self.session set!")
		self.oldref = None
		self.oldAlternativeRef = None
		self.serviceSlot = -1
		self.onClose.append(self.__onClose)

	def pipAvailable(self):  # PiP isn't available in every state of Enigma2.
		try:
			self.session.pipshown
			pipavailable = True
		except Exception:
			pipavailable = False
		return pipavailable

	def getServiceSlot(self):
		service = self.session.nav.getCurrentService()
		frontendInfo = service and service.frontendInfo()
		frontendData = frontendInfo and frontendInfo.getFrontendData()
		return frontendData.get("tuner_number", -1) if frontendData else -1

	def stopService(self):
		if self.oldref is None:
			serviceRef = self.session.nav.getCurrentlyPlayingServiceOrGroup()
			if serviceRef:
				serviceRefString = serviceRef.toString()
				servicePath = serviceRefString.rsplit(":", 1)[-1]
				if "%3a//" not in serviceRefString.lower() and not servicePath.startswith("/"):
					self.serviceSlot = self.getServiceSlot()
					self.oldref = serviceRef
					self.oldAlternativeRef = self.session.nav.getCurrentlyPlayingServiceReference()
					self.session.nav.stopService()
			if self.pipAvailable() and self.session.pipshown:  # Try to disable PiP.
				if hasattr(self.session, "infobar"):
					if self.session.infobar.servicelist and self.session.infobar.servicelist.dopipzap:
						self.session.infobar.servicelist.togglePipzap()
				if hasattr(self.session, "pip"):
					del self.session.pip
				self.session.pipshown = False
			streamServer = eStreamServer.getInstance()
			if streamServer and streamServer.getConnectedClients():
				streamServer.stopStream()

	def __onClose(self):
		if self.oldref:
			self.session.nav.playService(self.oldref)

	def restoreService(self, msg=_("Zap back to previously tuned service?")):
		if self.oldref:
			self.session.openWithCallback(self.restartPrevService, MessageBox, msg, MessageBox.TYPE_YESNO)
		else:
			self.restartPrevService(False)

	def restartPrevService(self, yesno=True, close=True):
		if not yesno:
			self.oldref = None
			self.oldAlternativeRef = None
			self.serviceSlot = -1
		if close:
			self.close()
		else:
			self.__onClose()
			self.oldref = None
			self.oldAlternativeRef = None
			self.serviceSlot = -1


class NimSetup(Screen, ConfigListScreen, ServiceStopScreen):
	def __init__(self, session, slotid):
		printCallSequence(10)
		Screen.__init__(self, session)
		self.setup_title = _("Tuner Settings")
		self.slotid = slotid
		self.list = []
		ServiceStopScreen.__init__(self)
		ConfigListScreen.__init__(self, self.list, on_change=self.changedEntry)
		self["key_red"] = Label(_("Close"))
		self["key_green"] = Label(_("Save"))
		self["key_yellow"] = Label(_("Configuration mode"))
		self["key_blue"] = Label()
		self["description"] = Label(" ")
		self["actions"] = ActionMap(["SetupActions", "SatlistShortcutAction", "ColorActions"], {
			"ok": self.keyOk,
			"save": self.keySave,
			"cancel": self.keyCancel,
			"changetype": self.changeConfigurationMode,
			"nothingconnected": self.nothingConnectedShortcut,
			"red": self.keyCancel,
			"green": self.keySave,
		}, prio=-2)
		self.configMode = None
		self.nimCountries = international.getNIMCountries()
		self.nim = nimmanager.nim_slots[slotid]
		self.nimConfig = self.nim.config
		self.tunerTemplateSource = None
		self.tunerTemplateSnapshot = []
		self.applyCableTerrestrialTemplate()
		self.inputPowerSlot = inputPowerSlotForNim(slotid)
		self.resourceManager = eDVBResourceManager.getInstance()
		self.canMeasureInputPower = self.resourceManager and self.resourceManager.canMeasureFrontendInputPower(self.inputPowerSlot)
		self.inputPowerValue = ConfigReadOnlyValue()
		self.inputPowerEntry = None
		self.inputPowerTimer = eTimer()
		self.inputPowerTimer.callback.append(self.updateInputPowerStatus)
		self.onClose.append(self.stopInputPowerTimer)
		self.createSetup()
		if self.canMeasureInputPower:
			self.updateInputPowerStatus()
			self.inputPowerTimer.start(500, False)
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.newConfig()
		self.setTitle(f"{_('Reception Settings')} {_('Tuner')} {self.nim.slot_input_name}")
		if self.selectionChanged not in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def selectionChanged(self):
		self["description"].setText(self["config"].getCurrent() and len(self["config"].getCurrent()) > 2 and self["config"].getCurrent()[2] or "")

	@staticmethod
	def cableTerrestrialTypes(nim):
		return tuple(receptionType for receptionType in ("DVB-C", "DVB-T") if nim.canBeCompatible(receptionType))

	@staticmethod
	def configWasSaved(configElement):
		return getattr(configElement, "saved_value", None) is not None

	def sectionWasConfigured(self, section):
		return section.settingsConfigured.value or any(self.configWasSaved(configElement) for configElement in section.content.items.values() if configElement is not section.settingsConfigured)

	def copyTemplateElement(self, sourceElement, targetElement):
		if not hasattr(sourceElement, "value") or not hasattr(targetElement, "value"):
			return
		if not any(snapshot[0] is targetElement for snapshot in self.tunerTemplateSnapshot):
			self.tunerTemplateSnapshot.append((targetElement, deepcopy(targetElement.value), deepcopy(targetElement.saved_value), deepcopy(targetElement.loadValue)))
		targetElement.setValue(deepcopy(sourceElement.value))

	def copyTemplateSection(self, sourceSection, targetSection):
		for name, sourceElement in sourceSection.content.items.items():
			targetElement = targetSection.content.items.get(name)
			if targetElement is not None:
				self.copyTemplateElement(sourceElement, targetElement)

	def applyCableTerrestrialTemplate(self):
		templateTypes = self.cableTerrestrialTypes(self.nim)
		if not templateTypes or self.nim.isFBCLink():
			return
		if any(self.sectionWasConfigured(getattr(self.nimConfig, receptionType.lower().replace("-", ""))) for receptionType in templateTypes):
			return
		for sourceNim in nimmanager.nim_slots[:self.slotid]:
			if sourceNim.isFBCLink() or sourceNim.description != self.nim.description or self.cableTerrestrialTypes(sourceNim) != templateTypes:
				continue
			sourceConfig = sourceNim.config
			if not any(self.sectionWasConfigured(getattr(sourceConfig, receptionType.lower().replace("-", ""))) for receptionType in templateTypes):
				continue
			for name in ("force_legacy_signal_stats",):
				sourceElement = sourceConfig.content.items.get(name)
				targetElement = self.nimConfig.content.items.get(name)
				if sourceElement is not None and targetElement is not None and self.configWasSaved(sourceElement) and not self.configWasSaved(targetElement):
					self.copyTemplateElement(sourceElement, targetElement)
			for receptionType in templateTypes:
				sectionName = receptionType.lower().replace("-", "")
				self.copyTemplateSection(getattr(sourceConfig, sectionName), getattr(self.nimConfig, sectionName))
			self.tunerTemplateSource = sourceNim.slot
			sourceName = sourceNim.slot_name
			print(f"[SatConfig] Using {sourceName} as DVB-C/T settings template for {self.nim.slot_name}.")
			break

	def restoreCableTerrestrialTemplate(self):
		for configElement, value, savedValue, loadValue in reversed(self.tunerTemplateSnapshot):
			configElement.saved_value = savedValue
			configElement.loadValue = loadValue
			configElement.setValue(deepcopy(value))
		self.tunerTemplateSnapshot = []

	def saveCableTerrestrialTemplate(self):
		if self.tunerTemplateSource is None:
			return
		for snapshot in self.tunerTemplateSnapshot:
			snapshot[0].save()
		self.tunerTemplateSnapshot = []
		self.tunerTemplateSource = None

	def markCableTerrestrialConfigured(self):
		templateTypes = self.cableTerrestrialTypes(self.nim)
		activeTypes = [receptionType for receptionType in templateTypes if self.nim.isCompatible(receptionType)]
		if self.isCableTerrestrialHybrid() and self.nimConfig.hybridTunerMode.value == "switch":
			activeTypes = templateTypes
		for receptionType in activeTypes:
			section = getattr(self.nimConfig, receptionType.lower().replace("-", ""))
			section.settingsConfigured.value = True
			section.settingsConfigured.save()
		configfile.save()

	def stopInputPowerTimer(self):
		self.inputPowerTimer.stop()

	def updateInputPowerStatus(self):
		if not self.canMeasureInputPower or not self.inputPowerEntry:
			return
		power = self.resourceManager.readFrontendInputPower(self.inputPowerSlot)
		value = _("Not available") if power < 0 else f"{power} mA"
		if self.inputPowerValue.value != value:
			self.inputPowerValue.setChoices([(value, value)], default=value)
			self["config"].invalidate(self.inputPowerEntry)

	def addInputPowerEntry(self):
		self.inputPowerEntry = getConfigListEntry(_("Measured current"), self.inputPowerValue, _("Current supplied to the LNB and positioner."))
		self.list.append(self.inputPowerEntry)

	def getUnicableUserBand(self, lnb, requireFrequency=True):
		if isinstance(lnb, ConfigNothing) or lnb.lof.value != "unicable" or isinstance(lnb.unicable, ConfigNothing):
			return None, _("is not configured for Unicable")
		deviceType = lnb.unicable.value
		try:
			if deviceType == "unicable_user":
				diction = lnb.dictionuser.value
				if diction == "EN50607":
					scr = lnb.satcruserEN50607
					vco = lnb.satcrvcouserEN50607
				else:
					scr = lnb.satcruserEN50494
					vco = lnb.satcrvcouserEN50494
				userDefined = True
				positions = 64 if diction == "EN50607" else 2
				positionsOffset = 0
			elif deviceType in ("unicable_matrix", "unicable_lnb"):
				if deviceType == "unicable_matrix":
					configManufacturer = lnb.unicableMatrixManufacturer
					productDict = lnb.unicableMatrix
				else:
					configManufacturer = lnb.unicableLnbManufacturer
					productDict = lnb.unicableLnb
				nimmanager.sec.reconstructUnicableData(configManufacturer, productDict, lnb)
				manufacturerName = configManufacturer.value.decode(encoding="UTF-8", errors="strict") if isinstance(configManufacturer.value, bytes) else configManufacturer.value
				manufacturer = productDict[manufacturerName]
				productName = manufacturer.product.value.decode(encoding="UTF-8", errors="strict") if isinstance(manufacturer.product.value, bytes) else manufacturer.product.value
				if productName not in manufacturer.scr:
					return None, _("has no valid Unicable product")
				scr = manufacturer.scr[productName]
				vco = manufacturer.vco[productName]
				diction = manufacturer.diction[productName].value
				userDefined = False
				positions = int(manufacturer.positions[productName][0].value)
				positionsOffset = int(manufacturer.positionsoffset[productName][0].value)
			else:
				return None, _("has no supported Unicable device type")
			index = scr.index
			if index < 0 or index >= len(vco):
				return None, _("has no valid User Band channel")
			frequency = int(vco[index].value)
			if requireFrequency and frequency <= 0:
				return None, _("uses an unavailable User Band frequency")
		except (AttributeError, IndexError, KeyError, TypeError, ValueError):
			return None, _("has incomplete Unicable settings")
		return {
			"diction": diction,
			"frequency": frequency,
			"index": index,
			"pin": int(lnb.unicable_pin.value) if lnb.unicable_use_pin.value else -1,
			"positions": positions,
			"positionsOffset": positionsOffset,
			"scr": scr,
			"userDefined": userDefined,
			"vco": vco,
		}, None

	def validateUnicablePositions(self):
		for lnbnum, lnb in self.nimConfig.dvbs.advanced.lnb.items():
			if not isinstance(lnbnum, int) or not 0 < lnbnum <= maxFixedLnbPositions or isinstance(lnb, ConfigNothing) or lnb.lof.value != "unicable" or not lnb.unicablePosition.value:
				continue
			device, error = self.getUnicableUserBand(lnb, requireFrequency=False)
			if error:
				return _("Unable to validate the Unicable position for LNB %d: %s.") % (lnbnum, error)
			firstPosition = device["positionsOffset"] + 1
			lastPosition = device["positionsOffset"] + device["positions"]
			if not firstPosition <= lnb.unicablePosition.value <= lastPosition:
				return _("Unicable position %d is not supported by the selected device for LNB %d. Valid positions are %d to %d; use 'User defined' for a reprogrammed device.") % (lnb.unicablePosition.value, lnbnum, firstPosition, lastPosition)
		return None

	def getInheritedUnicableUserBand(self, lnbnum, source=None):
		lnbs = self.nimConfig.dvbs.advanced.lnb
		if source is None:
			try:
				source, error = self.getUnicableUserBand(lnbs[1])
			except KeyError:
				source, error = None, _("is not configured")
			if error:
				return None, "%s %s" % (_("LNB 1"), error)
		try:
			targetLnb = lnbs[lnbnum]
		except KeyError:
			return None, _("the target LNB is not configured")
		target, error = self.getUnicableUserBand(targetLnb, requireFrequency=False)
		if error:
			return None, "%s %s" % (_("the target LNB"), error)
		if source["diction"] != target["diction"]:
			return None, _("LNB 1 and the target LNB use different Unicable protocols")
		index = source["index"]
		if index >= len(target["vco"]) or index >= len(target["scr"].choices.choices):
			return None, _("the User Band channel from LNB 1 is not available")
		targetFrequency = int(target["vco"][index].value)
		if not target["userDefined"] and targetFrequency != source["frequency"]:
			return None, _("the selected device does not use the LNB 1 frequency on this User Band channel")
		return {
			"frequency": source["frequency"],
			"index": index,
			"link": targetLnb.unicableUseLnb1UserBand,
			"pin": source["pin"],
			"pinConfig": targetLnb.unicable_pin,
			"scr": target["scr"],
			"scrValue": target["scr"].choices.choices[index][0],
			"usePin": targetLnb.unicable_use_pin,
			"vco": target["vco"][index] if target["userDefined"] else None,
		}, None

	def appendInheritedUnicableUserBand(self, lnbnum):
		inherited, error = self.getInheritedUnicableUserBand(lnbnum)
		value = _("Unavailable") if error else "SCR %d / %d MHz" % (inherited["index"] + 1, inherited["frequency"])
		if not error and inherited["pin"] >= 0:
			value += " / PIN %d" % inherited["pin"]
		description = error if error else _("The User Band channel, frequency and optional PIN are inherited from LNB 1 and cannot be changed here.")
		self.advancedInheritedSCR = getConfigListEntry(_("Inherited channel / frequency"), ConfigSelection(choices=[("inherited", value)], default="inherited"), description)
		self.list.append(self.advancedInheritedSCR)

	def synchronizeInheritedUnicableUserBands(self):
		lnbs = self.nimConfig.dvbs.advanced.lnb
		try:
			source, error = self.getUnicableUserBand(lnbs[1])
		except KeyError:
			source, error = None, _("is not configured")
		plans = []
		for lnbnum in sorted(key for key in lnbs.keys() if isinstance(key, int) and 1 < key < 65):
			lnb = lnbs[lnbnum]
			if isinstance(lnb, ConfigNothing) or lnb.lof.value != "unicable" or not lnb.unicableUseLnb1UserBand.value:
				continue
			if error:
				return _("Unable to inherit the User Band for LNB %d: LNB 1 %s.") % (lnbnum, error)
			plan, planError = self.getInheritedUnicableUserBand(lnbnum, source)
			if planError:
				return _("Unable to inherit the User Band for LNB %d: %s.") % (lnbnum, planError)
			plans.append(plan)
		for plan in plans:
			plan["scr"].setValue(plan["scrValue"])
			plan["scr"].save()
			if plan["vco"] is not None:
				plan["vco"].setValue(plan["frequency"])
				plan["vco"].save()
			plan["usePin"].setValue(plan["pin"] >= 0)
			plan["usePin"].save()
			if plan["pin"] >= 0:
				plan["pinConfig"].setValue(plan["pin"])
				plan["pinConfig"].save()
			plan["link"].save()
		return None

	def keyMenuCallback(self, answer):
		if answer:
			cur = self["config"].getCurrent()
			prev = str(self.getCurrentValue())
			self["config"].getCurrent()[1].setValue(answer[1])
			self["config"].invalidateCurrent()
			if answer[1] != prev:
				self.entryChanged()
				if cur in (self.advancedSelectSatsEntry, self.selectSatsEntry) and cur:
					self.keyOk()
				else:
					if cur == self.hybridTunerMode and cur:
						self.applyHybridTunerMode()
						self.saveAll(validateSat=False)
					self.newConfig()

	def keyLeft(self):
		cur = self["config"].getCurrent()
		if cur and isFBCLink(self.nim.slot):
			checkList = (self.advancedLof, self.advancedConnected)
			if cur in checkList:
				return
		ConfigListScreen.keyLeft(self)
		if cur in (self.advancedSelectSatsEntry, self.selectSatsEntry) and cur:
			self.keyOk()
		else:
			if cur == self.hybridTunerMode and cur:
				self.applyHybridTunerMode()
				self.saveAll(validateSat=False)
			self.newConfig()

	def setTextKeyBlue(self):
		self["key_blue"].setText("")
		if self["config"].isChanged():
			self["key_blue"].setText(_("Set Default"))

	def keyRight(self):
		cur = self["config"].getCurrent()
		if cur and isFBCLink(self.nim.slot):
			checkList = (self.advancedLof, self.advancedConnected)
			if cur in checkList:
				return
		ConfigListScreen.keyRight(self)
		if cur in (self.advancedSelectSatsEntry, self.selectSatsEntry) and cur:
			self.keyOk()
		else:
			if cur == self.hybridTunerMode and cur:
				self.applyHybridTunerMode()
				self.saveAll(validateSat=False)
			self.newConfig()

	def handleKeyFileCallback(self, answer):
		ConfigListScreen.handleKeyFileCallback(self, answer)
		self.newConfig()

	def keyCancel(self):
		if self["config"].isChanged() or self.tunerTemplateSource is not None:
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"), default=False)
		else:
			self.restoreService(_("Zap back to service before tuner setup?"))

	def saveAll(self, validateSat=True, reopen=False):
		if self.isCableTerrestrialHybrid():
			self.nimConfig.hybridTunerMode.save()
			self.nimConfig.dvbc.configMode.save()
			self.nimConfig.dvbt.configMode.save()
			try:
				self.nimConfig.multiType.save()
			except Exception:
				pass
		if self.nim.isCompatible("DVB-S"):
			# Reset connectedTo to all choices to properly store the default value.
			choices = []
			nimlist = nimmanager.getNimListOfType("DVB-S", self.slotid)
			for id in nimlist:
				choices.append((str(id), nimmanager.getNimDescription(id)))
			self.nimConfig.dvbs.connectedTo.setChoices(choices)
			# Sanity check for empty sat list.
			if validateSat and self.nimConfig.dvbs.configMode.value != "satposdepends" and len(nimmanager.getSatListForNim(self.slotid)) < 1:
				self.nimConfig.dvbs.configMode.value = "nothing"
		if self.nim.isCompatible("DVB-C") and self.nim.isFBCRoot():
			rootMode = self.nimConfig.dvbc.configMode.value
			for slot in nimmanager.nim_slots:
				if slot.isFBCLink() and slot.is_fbc[2] == self.nim.is_fbc[2]:
					slot.config.dvbc.configMode.value = rootMode
					slot.config.dvbc.configMode.save()
		if reopen and self.oldref and self.serviceSlot == self.slotid and self.oldAlternativeRef:
			serviceType = self.oldAlternativeRef.getUnsignedData(4) >> 16
			forceReopen = serviceType == 0xEEEE and self.nim.canBeCompatible("DVB-T") and self.nimConfig.dvbt.configMode.value == "nothing"
			forceReopen |= serviceType == 0xFFFF and (
				self.nim.canBeCompatible("DVB-C") and self.nimConfig.dvbc.configMode.value == "nothing"
				or self.nim.canBeCompatible("ATSC") and self.nimConfig.atsc.configMode.value == "nothing"
			)
			if forceReopen:
				rawChannel = eDVBResourceManager.getInstance().allocateRawChannel(self.slotid)
				if rawChannel:
					frontend = rawChannel.getFrontend()
					if frontend:
						frontend.closeFrontend()
						frontend.reopenFrontend()
				del rawChannel
		for x in self["config"].list:
			x[1].save()
		if self.isSatelliteCableTerrestrialHybrid():
			self.nimConfig.dvbs.configMode.save()
		configfile.save()

	def cancelConfirm(self, result):
		if not result:
			return
		for x in self["config"].list:
			x[1].cancel()
		if self.tunerTemplateSource is not None:
			self.restoreCableTerrestrialTemplate()
			self.restoreService(_("Zap back to service before tuner setup?"))
			return
		if hasattr(self, "originalTerrestrialRegion"):
			self.nimConfig.dvbt.terrestrial.value = self.originalTerrestrialRegion
			self.nimConfig.dvbt.terrestrial.save()
		if hasattr(self, "originalCableRegion"):
			self.nimConfig.dvbc.scan_provider.value = self.originalCableRegion
			self.nimConfig.dvbc.scan_provider.save()
		# We need to call saveAll to reset the connectedTo choices.
		self.saveAll()
		self.restoreService(_("Zap back to service before tuner setup?"))

	def changeConfigurationMode(self):
		if self.configMode:
			if self.nim.isCompatible("DVB-S"):
				self.nimConfig.dvbs.configMode.selectNext()
			elif self.nim.isCompatible("DVB-C"):
				self.nimConfig.dvbc.configMode.selectNext()
			elif self.nim.isCompatible("DVB-T"):
				self.nimConfig.dvbt.configMode.selectNext()
			else:
				pass
			self["config"].invalidate(self.configMode)
			self.setTextKeyBlue()
			self.createSetup()

	def nothingConnectedShortcut(self):
		if self["config"].isChanged():
			for x in self["config"].list:
				x[1].cancel()
			self.setTextKeyBlue()
			self.createSetup()

	def countrycodeToCountry(self, cc):
		return self.nimCountries.get(cc.upper(), cc).upper()

	def createSimpleSetup(self, mode):
		nim = self.nimConfig.dvbs
		if mode == "single":
			self.singleSatEntry = getConfigListEntry(_("Satellite"), nim.diseqcA, _("Select the satellite from which your dish is receiving its signal. If you are unsure select 'Automatic' and the receiver will attempt to determine this for you."))
			self.list.append(self.singleSatEntry)
			if nim.diseqcA.value in ("360", "560"):
				self.list.append(getConfigListEntry(_("Use circular LNB"), nim.simpleDiSEqCSetCircularLNB, _("If you are using a circular polarized LNB select 'Yes', otherwise select 'No'.")))
			self.list.append(getConfigListEntry(_("Send DiSEqC"), nim.simpleSingleSendDiSEqC, _("Select 'Yes' if you are using a multi-switch which requires a DiSEqC Port-A command signal. Select 'No' for all other setups.")))
		else:
			self.list.append(getConfigListEntry(_("Port A"), nim.diseqcA, _("Select the satellite which is connected to Port-A of your switch. If you are unsure select 'Automatic' and the receiver will attempt to determine this for you. If nothing is connected to this port, select 'Nothing connected'.")))
		if mode in ("toneburst_a_b", "diseqc_a_b", "diseqc_a_b_c_d"):
			self.list.append(getConfigListEntry(_("Port B"), nim.diseqcB, _("Select the satellite which is connected to Port-B of your switch. If you are unsure select 'Automatic' and the receiver will attempt to determine this for you. If nothing is connected to this port, select 'Nothing connected'.")))
			if mode == "diseqc_a_b_c_d":
				self.list.append(getConfigListEntry(_("Port C"), nim.diseqcC, _("Select the satellite which is connected to Port-C of your switch. If you are unsure select 'Automatic' and the receiver will attempt to determine this for you. If nothing is connected to this port, select 'Nothing connected'.")))
				self.list.append(getConfigListEntry(_("Port D"), nim.diseqcD, _("Select the satellite which is connected to Port-D of your switch. If you are unsure select 'Automatic' and the receiver will attempt to determine this for you. If nothing is connected to this port, select 'Nothing connected'.")))
			if mode != "toneburst_a_b":
				self.list.append(getConfigListEntry(_("Set voltage and 22KHz"), nim.simpleDiSEqCSetVoltageTone, _("Leave this set to 'Yes' unless you fully understand why you are adjusting it.")))
				self.list.append(getConfigListEntry(_("Send DiSEqC only on satellite change"), nim.simpleDiSEqCOnlyOnSatChange, _("Select 'Yes' to only send the DiSEqC command when changing from one satellite to another, or select 'No' for the DiSEqC command to be resent on every zap.")))
		if mode in ("single", "diseqc_a_b", "diseqc_a_b_c_d"):
			automaticSelected = nim.diseqcA.orbital_position == 3600
			if mode in ("diseqc_a_b", "diseqc_a_b_c_d"):
				automaticSelected |= nim.diseqcB.orbital_position == 3600
			if mode == "diseqc_a_b_c_d":
				automaticSelected |= nim.diseqcC.orbital_position == 3600 or nim.diseqcD.orbital_position == 3600
			if automaticSelected:
				autoOrder = nim.autoDiSEqCOrderSingle if mode == "single" else nim.autoDiSEqCOrder
				self.autoDiseqcOrderEntry = getConfigListEntry(_("Auto DiSEqC search order"), autoOrder, _("Limit the search to the satellite group normally used by this installation."))
				self.list.append(self.autoDiseqcOrderEntry)

	def createPositionerSetup(self):
		nim = self.nimConfig.dvbs
		if nim.diseqcMode.value == "positioner_select":
			self.selectSatsEntry = getConfigListEntry(_("Press OK to select satellites"), nim.pressOKtoList, _("Press OK to select a group of satellites to configure in one block."))
			self.list.append(self.selectSatsEntry)
		self.list.append(getConfigListEntry(_("Longitude"), nim.longitude, _("Enter your current longitude. This is the number of degrees you are from zero meridian as a decimal.")))
		self.list.append(getConfigListEntry(" ", nim.longitudeOrientation, _("Enter if you are in the East or West hemisphere.")))
		self.list.append(getConfigListEntry(_("Latitude"), nim.latitude, _("Enter your current latitude. This is the number of degrees you are from the equator as a decimal.")))
		self.list.append(getConfigListEntry(" ", nim.latitudeOrientation, _("Enter if you are North or South of the equator.")))
		if self.canMeasureInputPower:
			self.addInputPowerEntry()
			self.advancedPowerMeasurement = getConfigListEntry(_("Use power measurement"), nim.powerMeasurement, _("Detect positioner movement by its current consumption."))
			self.list.append(self.advancedPowerMeasurement)
			if nim.powerMeasurement.value:
				self.list.append(getConfigListEntry(_("Power threshold in mA"), nim.powerThreshold, _("Minimum difference between idle and moving current.")))
				self.turningSpeed = getConfigListEntry(_("Rotor turning speed"), nim.turningSpeed, _("Select how quickly the dish should move between satellites."))
				self.list.append(self.turningSpeed)
				if nim.turningSpeed.value == "fast epoch":
					self.turnFastEpochBegin = getConfigListEntry(_("Begin time"), nim.fastTurningBegin, _("Only move the dish quickly after this hour."))
					self.turnFastEpochEnd = getConfigListEntry(_("End time"), nim.fastTurningEnd, _("Only move the dish quickly before this hour."))
					self.list.append(self.turnFastEpochBegin)
					self.list.append(self.turnFastEpochEnd)
		else:
			if nim.powerMeasurement.value:
				nim.powerMeasurement.value = False
				nim.powerMeasurement.save()
		if not hasattr(self, "additionalMotorOptions"):
			customMotorValues = any(x.value != x.default for x in (nim.turningspeedH, nim.turningspeedV, nim.tuningstepsize, nim.rotorPositions))
			self.additionalMotorOptions = ConfigBoolean(default=customMotorValues, descriptions={False: _("Show sub-menu"), True: _("Hide sub-menu")})
		self.showAdditionalMotorOptions = getConfigListEntry(_("Extra motor options"), self.additionalMotorOptions, _("Additional motor options allow you to enter details from your motor's specifications so Enigma can work out how long it will take to move the dish from one satellite to another."))
		self.list.append(self.showAdditionalMotorOptions)
		if self.additionalMotorOptions.value:
			self.list.append(getConfigListEntry("   %s [\u00B0%s" % (_("Horizontal turning speed"), _("/sec]")), nim.turningspeedH, _("Consult your motor's specifications for this information, or leave the default setting.")))
			self.list.append(getConfigListEntry("   %s [\u00B0%s" % (_("Vertical turning speed"), _("/sec]")), nim.turningspeedV, _("Consult your motor's specifications for this information, or leave the default setting.")))
			self.list.append(getConfigListEntry("   %s [\u00B0]" % _("Turning step size"), nim.tuningstepsize, _("Consult your motor's specifications for this information, or leave the default setting.")))
			self.list.append(getConfigListEntry("   %s" % _("Max memory positions"), nim.rotorPositions, _("Consult your motor's specifications for this information, or leave the default setting.")))

	def adaptConfigModeChoices(self):
		if self.nim.canBeCompatible("DVB-S") and not self.nim.isFBCLink():
			choices = {
				"nothing": _("Not configured"),
				"simple": _("Simple"),
				"advanced": _("Advanced")
			}
			if len(nimmanager.canEqualTo(self.slotid)) > 0:
				choices["equal"] = _("Equal to")
			if len(nimmanager.canDependOn(self.slotid)) > 0:
				choices["satposdepends"] = _("Second cable of motorized LNB")
			if len(nimmanager.canConnectTo(self.slotid)) > 0:
				choices["loopthrough"] = _("Loop through to")
			if isFBCLink(self.nim.slot):
				choices = {
					"nothing": _("Not configured"),
					"advanced": _("Advanced")
				}
			if self.nim.isMultiType():
				self.nimConfig.dvbs.configMode.setChoices(choices, default="nothing")
			else:
				self.nimConfig.dvbs.configMode.setChoices(choices, default="simple")

	def isCableTerrestrialHybrid(self):
		return self.nim.isMultiType() and self.nim.canBeCompatible("DVB-C") and self.nim.canBeCompatible("DVB-T") and hasattr(self.nimConfig, "hybridTunerMode")

	def isSatelliteCableTerrestrialHybrid(self):
		return self.isCableTerrestrialHybrid() and self.nim.canBeCompatible("DVB-S")

	def ensureSatelliteEnabled(self):
		if self.nimConfig.dvbs.configMode.value == "nothing":
			self.nimConfig.dvbs.configMode.value = "simple"

	def setHybridMultiType(self, deliverySystem):
		try:
			multiType = self.nimConfig.multiType
		except Exception:
			return
		for value, description in multiType.choices.choices:
			if description.startswith(deliverySystem):
				multiType.setValue(value)
				return

	def applyHybridTunerMode(self):
		if not self.isCableTerrestrialHybrid():
			return
		mode = self.nimConfig.hybridTunerMode.value
		if mode == "cable":
			self.nimConfig.dvbc.configMode.value = "enabled"
			self.nimConfig.dvbt.configMode.value = "nothing"
			if self.isSatelliteCableTerrestrialHybrid():
				self.nimConfig.dvbs.configMode.value = "nothing"
			self.setHybridMultiType("DVB-C")
		elif mode == "terrestrial":
			self.nimConfig.dvbc.configMode.value = "nothing"
			self.nimConfig.dvbt.configMode.value = "enabled"
			if self.isSatelliteCableTerrestrialHybrid():
				self.nimConfig.dvbs.configMode.value = "nothing"
			self.setHybridMultiType("DVB-T")
		elif mode == "satellite" and self.isSatelliteCableTerrestrialHybrid():
			self.nimConfig.dvbc.configMode.value = "nothing"
			self.nimConfig.dvbt.configMode.value = "nothing"
			self.ensureSatelliteEnabled()
			self.setHybridMultiType("DVB-S")
		elif mode == "switch" and not self.isSatelliteCableTerrestrialHybrid():
			self.nimConfig.dvbc.configMode.value = "enabled"
			self.nimConfig.dvbt.configMode.value = "enabled"
			self.nimConfig.dvbt.terrestrial_5V.value = True

	def createSetup(self):
		self.adaptConfigModeChoices()
		print("[SatConfig] Creating setup.")
		self.list = []
		self.multiType = None
		self.hybridTunerMode = None
		self.diseqcModeEntry = None
		self.advancedSatsEntry = None
		self.advancedLnbsEntry = None
		self.advancedDiseqcMode = None
		self.advancedUsalsEntry = None
		self.advancedLof = None
		self.advancedPowerMeasurement = None
		self.inputPowerEntry = None
		self.autoDiseqcOrderEntry = None
		self.turningSpeed = None
		self.turnFastEpochBegin = None
		self.turnFastEpochEnd = None
		self.toneburst = None
		self.committedDiseqcCommand = None
		self.uncommittedDiseqcCommand = None
		self.commandOrder = None
		self.cableScanType = None
		self.have_advanced = False
		self.advancedUnicable = None
		self.advancedUnicableUseLnb1 = None
		self.advancedUnicableUsePin = None
		self.advancedType = None
		self.advancedManufacturer = None
		self.advancedSCR = None
		self.advancedInheritedSCR = None
		self.advancedDiction = None
		self.advancedConnected = None
		self.advancedUnicableTuningAlgo = None
		self.advancedPowerInserter = None
		self.showAdditionalMotorOptions = None
		self.selectSatsEntry = None
		self.advancedSelectSatsEntry = None
		self.singleSatEntry = None
		self.terrestrialRegionsEntry = None
		self.cableRegionsEntry = None
		if not hasattr(self, "terrestrialCountriesEntry"):
			self.terrestrialCountriesEntry = None
		if not hasattr(self, "cableCountriesEntry"):
			self.cableCountriesEntry = None
		if self.isCableTerrestrialHybrid():
			description = _("Configure the tuner mode.") if self.isSatelliteCableTerrestrialHybrid() else _("Select how this DVB-C/T tuner is connected. Use the external coax switch option only with a 5V controlled coax switch.")
			self.hybridTunerMode = getConfigListEntry(_("Hybrid tuner mode"), self.nimConfig.hybridTunerMode, description)
			self.list.append(self.hybridTunerMode)
		if self.nim.isMultiType():
			try:
				multiType = self.nimConfig.multiType
				choices = []
				for x in multiType.choices.choices:  # Set list entry corresponding to the current tuner type.
					if self.nim.isCompatible(x[1]):
						multiType.setValue(x[0])
					choices.append(x[1])
				choices = f"({', '.join(choices)})"
				if not self.isCableTerrestrialHybrid() or (not self.isSatelliteCableTerrestrialHybrid() and self.nimConfig.hybridTunerMode.value == "switch"):
					self.multiType = getConfigListEntry(_("Tuner type %s") % choices, multiType, _("You can switch with left and right this tuner types %s") % choices)
					self.list.append(self.multiType)
			except Exception:
				self.multiType = None
		if self.nim.isCompatible("DVB-S"):
			nimConfig = self.nimConfig.dvbs
			self.configMode = getConfigListEntry(_("Configuration mode"), nimConfig.configMode, _("Configure this tuner using Simple or Advanced options, loop it through to another tuner, copy a configuration from another tuner or disable it."))
			self.list.append(self.configMode)
			if nimConfig.configMode.value == "simple":  # Simple setup.
				self.diseqcModeEntry = getConfigListEntry(pgettext(_("Satellite configuration mode"), _("Mode")), nimConfig.diseqcMode, _("Select how the satellite dish is set up. i.e. fixed dish, single LNB, DiSEqC switch, positioner, etc."))
				self.list.append(self.diseqcModeEntry)
				if nimConfig.diseqcMode.value in ("single", "toneburst_a_b", "diseqc_a_b", "diseqc_a_b_c_d"):
					self.createSimpleSetup(nimConfig.diseqcMode.value)
				if nimConfig.diseqcMode.value in ("positioner", "positioner_select"):
					self.createPositionerSetup()
			elif nimConfig.configMode.value == "equal":
				choices = []
				nimlist = nimmanager.canEqualTo(self.nim.slot)
				for id in nimlist:
					choices.append((str(id), nimmanager.getNimDescription(id)))
				nimConfig.connectedTo.setChoices(choices)
				self.list.append(getConfigListEntry(_("Tuner"), nimConfig.connectedTo, _("This setting allows the tuner configuration to be a duplication of another configured tuner.")))
			elif nimConfig.configMode.value == "satposdepends":
				choices = []
				nimlist = nimmanager.canDependOn(self.nim.slot)
				for id in nimlist:
					choices.append((str(id), nimmanager.getNimDescription(id)))
				nimConfig.connectedTo.setChoices(choices)
				self.list.append(getConfigListEntry(_("Tuner"), nimConfig.connectedTo, _("Select the tuner that controls the motorized dish.")))
			elif nimConfig.configMode.value == "loopthrough":
				choices = []
				print(f"[SatConfig] Connectable to {nimmanager.canConnectTo(self.slotid)}.")
				connectable = nimmanager.canConnectTo(self.slotid)
				for id in connectable:
					choices.append((str(id), nimmanager.getNimDescription(id)))
				nimConfig.connectedTo.setChoices(choices)
				self.list.append(getConfigListEntry(_("Connected to"), nimConfig.connectedTo, _("Select the tuner upon which this loop through depends.")))
			elif nimConfig.configMode.value == "nothing":
				pass
			elif nimConfig.configMode.value == "advanced":  # Advanced SATs.
				additionalRotorCable = (3607, _("Additional cable of motorized LNB"))
				advancedSatChoices = [choice for choice in nimConfig.advanced.sats.choices.choices if int(choice[0]) != 3607]
				if isFBCLink(self.nim.slot):
					advancedSatChoices = [choice for choice in advancedSatChoices if int(choice[0]) < 3600]
				rotorSources = nimmanager.canDependOn(self.slotid, advancedSatposdepends="fbc" if isFBCLink(self.nim.slot) else "all")
				if rotorSources:
					advancedSatChoices.append(additionalRotorCable)
				currentAdvancedSat = int(nimConfig.advanced.sats.value)
				if currentAdvancedSat not in {int(choice[0]) for choice in advancedSatChoices}:
					currentAdvancedSat = 192 if any(int(choice[0]) == 192 for choice in advancedSatChoices) else int(advancedSatChoices[0][0])
				nimConfig.advanced.sats.setChoices(advancedSatChoices, default=currentAdvancedSat)
				self.advancedSatsEntry = getConfigListEntry(_("Satellite"), nimConfig.advanced.sats, _("Select the satellite you want to configure. Once configured you can select and configure other satellites that will be accessed using this same tuner."))
				self.list.append(self.advancedSatsEntry)
				current_config_sats = int(nimConfig.advanced.sats.value)
				if current_config_sats == 3607:
					nimConfig.connectedTo.setChoices([(str(slot), nimmanager.getNimDescription(slot)) for slot in rotorSources])
					self.list.append(getConfigListEntry(_("Tuner"), nimConfig.connectedTo, _("Select the tuner that controls the motorized dish.")))
				if current_config_sats in (3605, 3606):
					self.advancedSelectSatsEntry = getConfigListEntry(_("Press OK to select satellites"), nimConfig.pressOKtoList, _("Selecting this option allows you to configure a group of satellites in one block."))
					self.list.append(self.advancedSelectSatsEntry)
					self.fillListWithAdvancedSatEntrys(nimConfig.advanced.sat[int(current_config_sats)])
				elif current_config_sats == 3607:
					self.fillListWithAdvancedSatEntrys(nimConfig.advanced.sat[3607])
				else:
					cur_orb_pos = nimConfig.advanced.sats.orbital_position
					satlist = nimConfig.advanced.sat.keys()
					if cur_orb_pos is not None:
						if cur_orb_pos not in satlist:
							cur_orb_pos = satlist[0]
						self.fillListWithAdvancedSatEntrys(nimConfig.advanced.sat[cur_orb_pos])
				self.have_advanced = True
			if exists("/proc/stb/frontend/%d/tone_amplitude" % self.nim.slot) and config.usage.setup_level.index >= 2:  # Expert mode.
				self.list.append(getConfigListEntry(_("Tone amplitude"), nimConfig.toneAmplitude, _("Your receiver can use tone amplitude. Consult your receiver's manual for more information.")))
			if exists("/proc/stb/frontend/%d/use_scpc_optimized_search_range" % self.nim.slot) and config.usage.setup_level.index >= 2:  # Expert mode.
				self.list.append(getConfigListEntry(_("SCPC optimized search range"), nimConfig.scpcSearchRange, _("Your receiver can use SCPC optimized search range. Consult your receiver's manual for more information.")))
			if exists("/proc/stb/frontend/%d/t2mirawmode" % self.nim.slot) and config.usage.setup_level.index >= 2:  # Expert mode.
				self.list.append(getConfigListEntry(_("T2MI RAW Mode"), nimConfig.t2miRawMode, _("With T2MI RAW mode disabled (default) we can use single T2MI PLP de-encapsulation. With T2MI RAW mode enabled we can use astra-sm to analyze T2MI")))
			if len(nimConfig.input.choices) > 1:
				self.list.append(getConfigListEntry(_("Connector"), nimConfig.input, _("Select the input connector you want to use.")))

		elif self.nim.isCompatible("DVB-C"):
			warningText = ""
			if "Vuplus DVB-C NIM(BCM3148)" in (self.nim.description or "") and self.nim.isFBCRoot() and self.nim.is_fbc[2] != 1:
				warningText = _("Warning: This FBC-C V1 tuner should be installed in the first slot. In the second slot only 2 of 8 demodulators may be available. ")
			self.configMode = getConfigListEntry(_("Configuration mode"), self.nimConfig.dvbc.configMode, warningText + _("Select 'Enabled' if this tuner has a signal cable connected, otherwise select 'Nothing connected'."))
			self.list.append(self.configMode)
			if self.nimConfig.dvbc.configMode.value == "enabled":
				self.list.append(getConfigListEntry(_("Network ID"), self.nimConfig.dvbc.scan_networkid, _("This setting depends on your cable provider and location. If you don't know the correct setting refer to the menu in the official cable receiver, or get it from your cable provider, or seek help via Internet forum.")))
				self.cableScanType = getConfigListEntry(_("Used service scan type"), self.nimConfig.dvbc.scan_type, _("Select 'Provider' to scan from the predefined list of cable multiplexes. Select 'Bands' to only scan certain parts of the spectrum. Select 'Steps' to scan in steps of a particular frequency bandwidth."))
				self.list.append(self.cableScanType)
				if self.nimConfig.dvbc.scan_type.value == "provider":
					# Country/Region tier one.
					if self.cableCountriesEntry is None:
						cablecountrycodelist = nimmanager.getCablesCountrycodeList()
						cablecountrycode = nimmanager.getCableCountrycode(self.slotid)
						default = cablecountrycode in cablecountrycodelist and cablecountrycode or None
						choices = [("all", _("All"))] + sorted([(x, self.countrycodeToCountry(x)) for x in cablecountrycodelist], key=lambda listItem: listItem[1])
						self.cableCountries = ConfigSelection(default=default, choices=choices)
						self.cableCountriesEntry = getConfigListEntry(_("Country"), self.cableCountries, _("Select your country. If not available select 'All'."))
						self.originalCableRegion = self.nimConfig.dvbc.scan_provider.value
					# Country/Region tier two.
					if self.cableCountries.value == "all":
						cableNames = [x[0] for x in sorted(sorted(nimmanager.getCablesList(), key=lambda listItem: listItem[0]), key=lambda listItem: self.countrycodeToCountry(listItem[2]))]
					else:
						cableNames = sorted([x[0] for x in nimmanager.getCablesByCountrycode(self.cableCountries.value)])
					default = self.nimConfig.dvbc.scan_provider.value in cableNames and self.nimConfig.dvbc.scan_provider.value or None
					self.cableRegions = ConfigSelection(default=default, choices=cableNames)

					def updateCableProvider(configEntry):
						self.nimConfig.dvbc.scan_provider.value = configEntry.value
						self.nimConfig.dvbc.scan_provider.save()

					self.cableRegions.addNotifier(updateCableProvider)
					self.cableRegionsEntry = getConfigListEntry(_("Region"), self.cableRegions, _("Select your provider and region. If not present in this list you will need to select one of the other 'Service scan types'."))
					self.list.append(self.cableCountriesEntry)
					self.list.append(self.cableRegionsEntry)
				else:
					if self.nimConfig.dvbc.scan_type.value == "bands":
						# TRANSLATORS: Option name, indicating which type of (DVB-C) band should be scanned. The name of the band is printed in '%s'. E.g.: 'Scan EU MID band'.
						self.list.append(getConfigListEntry(_("Scan %s band") % "EU VHF I", self.nimConfig.dvbc.scan_band_EU_VHF_I, _("Select 'Yes' to include the %s band in your search.") % ("EU VHF I")))
						self.list.append(getConfigListEntry(_("Scan %s band") % "EU MID", self.nimConfig.dvbc.scan_band_EU_MID, _("Select 'Yes' to include the %s band in your search.") % ("EU MID")))
						self.list.append(getConfigListEntry(_("Scan %s band") % "EU VHF III", self.nimConfig.dvbc.scan_band_EU_VHF_III, _("Select 'Yes' to include the %s band in your search.") % ("EU VHF III")))
						self.list.append(getConfigListEntry(_("Scan %s band") % "EU UHF IV", self.nimConfig.dvbc.scan_band_EU_UHF_IV, _("Select 'Yes' to include the %s band in your search.") % ("EU VHF IV")))
						self.list.append(getConfigListEntry(_("Scan %s band") % "EU UHF V", self.nimConfig.dvbc.scan_band_EU_UHF_V, _("Select 'Yes' to include the %s band in your search.") % ("EU VHF V")))
						self.list.append(getConfigListEntry(_("Scan %s band") % "EU SUPER", self.nimConfig.dvbc.scan_band_EU_SUPER, _("Select 'Yes' to include the %s band in your search.") % ("EU SUPER")))
						self.list.append(getConfigListEntry(_("Scan %s band") % "EU HYPER", self.nimConfig.dvbc.scan_band_EU_HYPER, _("Select 'Yes' to include the %s band in your search.") % ("EU HYPER")))
						self.list.append(getConfigListEntry(_("Scan %s band") % "US LOW", self.nimConfig.dvbc.scan_band_US_LOW, _("Select 'Yes' to include the %s band in your search.") % ("US LOW")))
						self.list.append(getConfigListEntry(_("Scan %s band") % "US MID", self.nimConfig.dvbc.scan_band_US_MID, _("Select 'Yes' to include the %s band in your search.") % ("US MID")))
						self.list.append(getConfigListEntry(_("Scan %s band") % "US HIGH", self.nimConfig.dvbc.scan_band_US_HIGH, _("Select 'Yes' to include the %s band in your search.") % ("US HIGH")))
						self.list.append(getConfigListEntry(_("Scan %s band") % "US SUPER", self.nimConfig.dvbc.scan_band_US_SUPER, _("Select 'Yes' to include the %s band in your search.") % ("US SUPER")))
						self.list.append(getConfigListEntry(_("Scan %s band") % "US HYPER", self.nimConfig.dvbc.scan_band_US_HYPER, _("Select 'Yes' to include the %s band in your search.") % ("US HYPER")))
					elif self.nimConfig.dvbc.scan_type.value == "steps":
						self.list.append(getConfigListEntry(_("Frequency scan step size(khz)"), self.nimConfig.dvbc.scan_frequency_steps, _("Enter the frequency step size for the tuner to use when searching for cable multiplexes. For more information consult your cable provider's documentation.")))
					# TRANSLATORS: Option name, indicating which type of (DVB-C) modulation should be scanned. The modulation type is printed in '%s'. E.g.: 'Scan QAM16'.
					if self.nim.description != "ATBM781x":
						self.list.append(getConfigListEntry(_("Scan %s") % "QAM16", self.nimConfig.dvbc.scan_mod_qam16, _("Select 'Yes' to include %s multiplexes in your search.") % ("QAM16")))
						self.list.append(getConfigListEntry(_("Scan %s") % "QAM32", self.nimConfig.dvbc.scan_mod_qam32, _("Select 'Yes' to include %s multiplexes in your search.") % ("QAM32")))
						self.list.append(getConfigListEntry(_("Scan %s") % "QAM64", self.nimConfig.dvbc.scan_mod_qam64, _("Select 'Yes' to include %s multiplexes in your search.") % ("QAM64")))
						self.list.append(getConfigListEntry(_("Scan %s") % "QAM128", self.nimConfig.dvbc.scan_mod_qam128, _("Select 'Yes' to include %s multiplexes in your search.") % ("QAM128")))
						self.list.append(getConfigListEntry(_("Scan %s") % "QAM256", self.nimConfig.dvbc.scan_mod_qam256, _("Select 'Yes' to include %s multiplexes in your search.") % ("QAM256")))
						self.list.append(getConfigListEntry(_("Scan %s") % "SR6900", self.nimConfig.dvbc.scan_sr_6900, _("Select 'Yes' to include symbol rate %s in your search.") % ("6900")))
						self.list.append(getConfigListEntry(_("Scan %s") % "SR6875", self.nimConfig.dvbc.scan_sr_6875, _("Select 'Yes' to include symbol rate %s in your search.") % ("6875")))
						self.list.append(getConfigListEntry(_("Scan additional SR"), self.nimConfig.dvbc.scan_sr_ext1, _("This field allows you to search an additional symbol rate up to %s.") % ("7320")))
						self.list.append(getConfigListEntry(_("Scan additional SR"), self.nimConfig.dvbc.scan_sr_ext2, _("This field allows you to search an additional symbol rate up to %s.") % ("7320")))
			self.have_advanced = False
		elif self.nim.isCompatible("DVB-T"):
			self.configMode = getConfigListEntry(_("Configuration mode"), self.nimConfig.dvbt.configMode, _("Select 'Enabled' if this tuner has a signal cable connected, otherwise select 'Nothing connected'."))
			self.list.append(self.configMode)
			self.have_advanced = False
			if self.nimConfig.dvbt.configMode.value == "enabled":
				# Country/Region tier one.
				if self.terrestrialCountriesEntry is None:
					terrestrialcountrycodelist = nimmanager.getTerrestrialsCountrycodeList()
					terrestrialcountrycode = nimmanager.getTerrestrialCountrycode(self.slotid)
					default = terrestrialcountrycode in terrestrialcountrycodelist and terrestrialcountrycode or None
					if terrestrialcountrycode is None and BoxInfo.getItem("displaybrand") == "Beyonwiz" and "AUS" in terrestrialcountrycodelist:
						default = "AUS"
					choices = [("all", _("All"))] + sorted([(x, self.countrycodeToCountry(x)) for x in terrestrialcountrycodelist], key=lambda listItem: listItem[1])
					self.terrestrialCountries = ConfigSelection(default=default, choices=choices)
					self.terrestrialCountriesEntry = getConfigListEntry(_("Country"), self.terrestrialCountries, _("Select your country. If not available select 'All'."))
					self.originalTerrestrialRegion = self.nimConfig.dvbt.terrestrial.value
				# Country/Region tier two.
				if self.terrestrialCountries.value == "all":
					terrstrialNames = [x[0] for x in sorted(sorted(nimmanager.getTerrestrialsList(), key=lambda listItem: listItem[0]), key=lambda listItem: self.countrycodeToCountry(listItem[2]))]
				else:
					terrstrialNames = sorted([x[0] for x in nimmanager.getTerrestrialsByCountrycode(self.terrestrialCountries.value)])
				default = self.nimConfig.dvbt.terrestrial.value in terrstrialNames and self.nimConfig.dvbt.terrestrial.value or None
				if default is None and BoxInfo.getItem("displaybrand") == "Beyonwiz" and "All regions, Australia, (DVB-T)" in terrstrialNames:
					default = "All regions, Australia, (DVB-T)"
				self.terrestrialRegions = ConfigSelection(default=default, choices=terrstrialNames)

				def updateTerrestrialProvider(configEntry):
					self.nimConfig.dvbt.terrestrial.value = configEntry.value
					self.nimConfig.dvbt.terrestrial.save()

				self.terrestrialRegions.addNotifier(updateTerrestrialProvider)
				self.terrestrialRegionsEntry = getConfigListEntry(_("Region"), self.terrestrialRegions, _("Select your region. If it is not available change 'Country' to 'All' and select one of the default alternatives."))
				self.list.append(self.terrestrialCountriesEntry)
				self.list.append(self.terrestrialRegionsEntry)
				if BoxInfo.getItem("machinebuild") not in ('spycat',):
					self.list.append(getConfigListEntry(_("Enable 5V for active antenna"), self.nimConfig.dvbt.terrestrial_5V, _("Enable this setting if your aerial system needs power.")))
		elif self.nim.isCompatible("ATSC"):
			self.configMode = getConfigListEntry(_("Configuration mode"), self.nimConfig.atsc.configMode, _("Select 'Enabled' if this tuner has a signal cable connected, otherwise select 'Nothing connected'."))
			self.list.append(self.configMode)
			if self.nimConfig.atsc.configMode.value == "enabled":
				self.list.append(getConfigListEntry(_("ATSC provider"), self.nimConfig.atsc.atsc, _("Select your ATSC provider.")))
			self.have_advanced = False
		else:
			self.have_advanced = False
		if config.usage.setup_level.index > 1:
			self.list.append(getConfigListEntry(_("Force Legacy Signal stats"), self.nimConfig.force_legacy_signal_stats, _("Select 'Yes' to use signal values (SNR, etc) calculated from the older API V3. This API version has now been superseded.")))
		self["config"].list = self.list

	def newConfig(self):
		self.setTextKeyBlue()
		checkList = (
			self.configMode, self.diseqcModeEntry, self.advancedSatsEntry,
			self.advancedLnbsEntry, self.advancedDiseqcMode, self.advancedUsalsEntry,
			self.advancedLof, self.advancedPowerMeasurement, self.turningSpeed,
			self.advancedType, self.advancedSCR, self.advancedDiction, self.advancedManufacturer, self.advancedUnicable, self.advancedUnicableUseLnb1, self.advancedUnicableUsePin, self.advancedConnected, self.advancedUnicableTuningAlgo, self.advancedPowerInserter,
			self.toneburst, self.committedDiseqcCommand, self.uncommittedDiseqcCommand, self.singleSatEntry,
			self.commandOrder, self.showAdditionalMotorOptions, self.autoDiseqcOrderEntry, self.cableScanType, self.terrestrialCountriesEntry, self.cableCountriesEntry, self.hybridTunerMode, self.multiType
		)
		if self["config"].getCurrent() in (self.hybridTunerMode, self.multiType) and (self.hybridTunerMode or self.multiType):
			update_slots = [self.slotid]
			InitNimManager(nimmanager, update_slots)
			self.nim = nimmanager.nim_slots[self.slotid]
			self.nimConfig = self.nim.config
		for x in checkList:
			if self["config"].getCurrent() == x and x:
				self.createSetup()
				break

	def run(self):
		if self.nim.canBeCompatible("DVB-S"):
			if self.nimConfig.dvbs.configMode.value == "simple":
				autodiseqc_ports = 0
				if self.nimConfig.dvbs.diseqcMode.value == "single":
					if self.nimConfig.dvbs.diseqcA.orbital_position == 3600:
						autodiseqc_ports = 1
				elif self.nimConfig.dvbs.diseqcMode.value == "diseqc_a_b":
					if self.nimConfig.dvbs.diseqcA.orbital_position == 3600 or self.nimConfig.dvbs.diseqcB.orbital_position == 3600:
						autodiseqc_ports = 2
				elif self.nimConfig.dvbs.diseqcMode.value == "diseqc_a_b_c_d":
					if self.nimConfig.dvbs.diseqcA.orbital_position == 3600 or self.nimConfig.dvbs.diseqcB.orbital_position == 3600 or self.nimConfig.dvbs.diseqcC.orbital_position == 3600 or self.nimConfig.dvbs.diseqcD.orbital_position == 3600:
						autodiseqc_ports = 4
				if autodiseqc_ports:
					autoOrder = self.nimConfig.dvbs.autoDiSEqCOrderSingle.value if self.nimConfig.dvbs.diseqcMode.value == "single" else self.nimConfig.dvbs.autoDiSEqCOrder.value
					self.autoDiseqcRun(autodiseqc_ports, autoOrder)
					return False
			if self.have_advanced and self.nimConfig.dvbs.configMode.value == "advanced":
				self.saveAll()  # Save any unsaved data before self.list entries are gone.
				self.fillAdvancedList()  # Resets self.list so some entries like t2mirawmode removed.
		for x in self.list:
			if x in (self.turnFastEpochBegin, self.turnFastEpochEnd):
				# Workaround for storing only hour * 3600 + min * 60 value in config file not really needed, just for cosmetics.
				tm = localtime(x[1].value)
				dt = datetime(1970, 1, 1, tm.tm_hour, tm.tm_min)
				x[1].value = int(mktime(dt.timetuple()))
			x[1].save()
		nimmanager.sec.update()
		self.saveAll(reopen=True)
		return True

	def autoDiseqcRun(self, ports, order="all"):
		self.stopService()
		self.session.openWithCallback(self.autoDiseqcCallback, AutoDiseqc, self.slotid, ports, self.nimConfig.dvbs.simpleDiSEqCSetVoltageTone, self.nimConfig.dvbs.simpleDiSEqCOnlyOnSatChange, order)

	def autoDiseqcCallback(self, result):
		from Screens.Wizard import Wizard
		if Wizard.instance is not None:
			Wizard.instance.back()
		else:
			self.restartPrevService(close=False)
			self.createSetup()

	def fillListWithAdvancedSatEntrys(self, Sat):
		def ensure_text(text):
			return text.decode(encoding="UTF-8", errors="strict") if isinstance(text, bytes) else text

		lnbnum = int(Sat.lnb.value)
		nimConfig_advanced = self.nimConfig.dvbs.advanced
		currLnb = nimConfig_advanced.lnb[lnbnum]
		diction = None
		if isinstance(currLnb, ConfigNothing):
			currLnb = None
		# LNBs.
		self.advancedLnbsEntry = getConfigListEntry(_("LNB"), Sat.lnb, _("Allocate a number to the physical LNB you are configuring. You will be able to select this LNB again for other satellites (e.g. motorized dishes) to save setting up the same LNB multiple times."))
		self.list.append(self.advancedLnbsEntry)
		if currLnb:
			if isFBCLink(self.nim.slot):
				if currLnb.lof.value != "unicable":
					currLnb.lof.value = "unicable"
			self.list.append(getConfigListEntry(_("Priority"), currLnb.prio, _("This setting is for special setups only. It gives this LNB higher priority over other LNBs with lower values. The free LNB with the highest priority will be the first LNB selected for tuning services.")))
			self.advancedLof = getConfigListEntry(_("Type of LNB/Device"), currLnb.lof, _("Select the type of LNB/device being used (normally 'Universal'). If your LNB type is not available select 'User defined'."))
			self.list.append(self.advancedLof)
			if currLnb.lof.value == "user_defined":
				self.list.append(getConfigListEntry(_("LOF/L"), currLnb.lofl, _("Enter your low band local oscillator frequency. For more information consult the specifications of your LNB.")))
				self.list.append(getConfigListEntry(_("LOF/H"), currLnb.lofh, _("Enter your high band local oscillator frequency. For more information consult the specifications of your LNB.")))
				self.list.append(getConfigListEntry(_("Threshold"), currLnb.threshold, _("Enter the frequency at which you LNB switches between low band and high band. For more information consult the specifications of your LNB.")))
			if currLnb.lof.value == "unicable":
				warningText = ""
				if "Vuplus DVB-S NIM(AVL6222)" in (self.nim.description or "") and self.nim.internallyConnectableTo() is not None:
					warningText = _("Warning: The second input of this dual tuner may not support Unicable devices. ")
				self.advancedUnicable = getConfigListEntry("%s%s" % (_("Unicable "), _("Type of device")), currLnb.unicable, warningText + _("Select the type of Single Cable Reception device you are using."))
				self.list.append(self.advancedUnicable)
				self.advancedPowerInserter = getConfigListEntry(_("Externally powered"), currLnb.powerInserter, _("Enable this when a power inserter or external supply powers the Unicable device."))
				self.list.append(self.advancedPowerInserter)
				if lnbnum <= maxFixedLnbPositions:
					self.list.append(getConfigListEntry(_("Unicable position"), currLnb.unicablePosition, _("Leave this at 0 to derive the position from the LNB number and device profile. Enter 1 to 64 only for a reprogrammed Unicable device.")))
				inheritUserBand = 1 < lnbnum < 65 and currLnb.unicableUseLnb1UserBand.value
				if 1 < lnbnum < 65:
					self.advancedUnicableUseLnb1 = getConfigListEntry(_("Use LNB 1 User Band"), currLnb.unicableUseLnb1UserBand, _("Select 'Yes' to use the same User Band channel and frequency as LNB 1. This is intended for multiple satellite positions delivered by the same Unicable system."))
					self.list.append(self.advancedUnicableUseLnb1)
				if currLnb.unicable.value == "unicable_user":
					self.advancedDiction = getConfigListEntry(_("Diction"), currLnb.dictionuser, _("Select the protocol used by your SCR device. Choices are 'SCR Unicable' (Unicable), or 'SCR JESS' (JESS, also known as Unicable II)."))
					self.list.append(self.advancedDiction)
					if currLnb.dictionuser.value == "EN50494":
						satcr = currLnb.satcruserEN50494
						stcrvco = currLnb.satcrvcouserEN50494[currLnb.satcruserEN50494.index]
					elif currLnb.dictionuser.value == "EN50607":
						satcr = currLnb.satcruserEN50607
						stcrvco = currLnb.satcrvcouserEN50607[currLnb.satcruserEN50607.index]
					if inheritUserBand:
						self.appendInheritedUnicableUserBand(lnbnum)
					else:
						self.advancedSCR = getConfigListEntry(_("Channel"), satcr, _("Select the Unicable channel to be assigned to this tuner. This is a unique value. Be certain that no other device connected to this same Unicable system is allocated to the same Unicable channel."))
						self.list.append(self.advancedSCR)
						self.list.append(getConfigListEntry(_("Frequency"), stcrvco, _("Select the User Band frequency to be assigned to this tuner. This is the frequency the SCR switch or SCR LNB uses to pass the requested transponder to the tuner.")))
					self.list.append(getConfigListEntry(_("LOF/L"), currLnb.lofl, _("Consult your SCR device specifications for this information.")))
					self.list.append(getConfigListEntry(_("LOF/H"), currLnb.lofh, _("Consult your SCR device specifications for this information.")))
					self.list.append(getConfigListEntry(_("Threshold"), currLnb.threshold, _("Consult your SCR device specifications for this information.")))
					if not currLnb.powerInserter.value:
						self.list.append(getConfigListEntry(_("LNB/Switch Bootup time [ms]"), currLnb.bootuptimeuser))
				elif currLnb.unicable.value == "unicable_matrix":
					nimmanager.sec.reconstructUnicableData(currLnb.unicableMatrixManufacturer, currLnb.unicableMatrix, currLnb)
					manufacturer_name = ensure_text(currLnb.unicableMatrixManufacturer.value)
					manufacturer = currLnb.unicableMatrix[manufacturer_name]
					product_name = ensure_text(manufacturer.product.value)
					self.advancedManufacturer = getConfigListEntry(_("Manufacturer"), currLnb.unicableMatrixManufacturer, _("Select the manufacturer of your SCR device. If the manufacturer is not listed, set 'SCR' to 'User defined' and enter the device parameters manually according to its specifications."))
					self.list.append(self.advancedManufacturer)
					if product_name in manufacturer.scr:
						diction = manufacturer.diction[product_name].value
						self.advancedType = getConfigListEntry(_("Model"), manufacturer.product, _("Select the model number of your Unicable device. If the model number is not listed, set 'SCR' to 'User defined' and enter the device parameters manually according to its specifications."))
						self.list.append(self.advancedType)
						if inheritUserBand:
							self.appendInheritedUnicableUserBand(lnbnum)
						else:
							self.advancedSCR = getConfigListEntry(_("Channel"), manufacturer.scr[product_name], _("Select the User Band channel to be assigned to this tuner. This is an index into the table of frequencies the SCR switch uses to pass the requested transponder to the tuner."))
							self.list.append(self.advancedSCR)
							self.list.append(getConfigListEntry(_("Frequency"), manufacturer.vco[product_name][manufacturer.scr[product_name].index], _("Select the User Band frequency to be assigned to this tuner. This is the frequency the SCR switch uses to pass the requested transponder to the tuner.")))
				elif currLnb.unicable.value == "unicable_lnb":
					nimmanager.sec.reconstructUnicableData(currLnb.unicableLnbManufacturer, currLnb.unicableLnb, currLnb)
					manufacturer_name = ensure_text(currLnb.unicableLnbManufacturer.value)
					manufacturer = currLnb.unicableLnb[manufacturer_name]
					product_name = ensure_text(manufacturer.product.value)
					self.advancedManufacturer = getConfigListEntry(_("Manufacturer"), currLnb.unicableLnbManufacturer, _("Select the manufacturer of your SCR device. If the manufacturer is not listed, set 'SCR' to 'User defined' and enter the device parameters manually according to its specifications."))
					self.list.append(self.advancedManufacturer)
					if product_name in manufacturer.scr:
						diction = manufacturer.diction[product_name].value
						self.advancedType = getConfigListEntry(_("Model"), manufacturer.product, _("Select the model number of your Unicable device. If the model number is not listed, set 'SCR' to 'User defined' and enter the device parameters manually according to its specifications."))
						self.list.append(self.advancedType)
						if inheritUserBand:
							self.appendInheritedUnicableUserBand(lnbnum)
						else:
							self.advancedSCR = getConfigListEntry(_("Channel"), manufacturer.scr[product_name], _("Select the User Band channel to be assigned to this tuner. This is an index into the table of frequencies the SCR LNB uses to pass the requested transponder to the tuner."))
							self.list.append(self.advancedSCR)
							self.list.append(getConfigListEntry(_("Frequency"), manufacturer.vco[product_name][manufacturer.scr[product_name].index], _("Select the User Band frequency to be assigned to this tuner. This is the frequency the SCR LNB uses to pass the requested transponder to the tuner.")))
				if not inheritUserBand:
					self.advancedUnicableUsePin = getConfigListEntry(_("Use PIN"), currLnb.unicable_use_pin, _("Enable this when the User Band is protected by a PIN in a multi-dwelling Unicable installation."))
					self.list.append(self.advancedUnicableUsePin)
					if currLnb.unicable_use_pin.value:
						self.list.append(getConfigListEntry(_("PIN"), currLnb.unicable_pin, _("Enter the PIN from 0 to 255 assigned to this User Band by the installer or building operator.")))
				self.advancedUnicableTuningAlgo = getConfigListEntry(_("Tuning algorithm"), currLnb.unicableTuningAlgo, _("SCR timing adjustment, in conjunction with SCR socket and operation of several SCR devices with one cable."))
				self.list.append(self.advancedUnicableTuningAlgo)
				choices = []
				connectable = nimmanager.canConnectTo(self.slotid)
				for id in connectable:
					choices.append((str(id), nimmanager.getNimDescription(id)))
				if len(choices):
					if isFBCLink(self.nim.slot):
						if nimConfig_advanced.unicableconnected.value is not True:
							nimConfig_advanced.unicableconnected.value = True
					self.advancedConnected = getConfigListEntry(_("Connected through another tuner"), nimConfig_advanced.unicableconnected, _("Select 'Yes' if this tuner is connected to the SCR device through another tuner, otherwise select 'No'."))
					self.list.append(self.advancedConnected)
					if nimConfig_advanced.unicableconnected.value:
						nimConfig_advanced.unicableconnectedTo.setChoices(choices)
						self.list.append(getConfigListEntry(_("Connected to"), nimConfig_advanced.unicableconnectedTo, _("Select the tuner to which the signal cable of the SCR device is connected.")))
			else:  # No Unicable.
				self.list.append(getConfigListEntry(_("Voltage mode"), Sat.voltage, _("Select 'Polarization' if using a 'Universal' LNB, otherwise consult your LNB specifications.")))
				self.list.append(getConfigListEntry(_("Tone mode"), Sat.tonemode, _("Select 'Band' if using a 'Universal' LNB, otherwise consult your LNB specifications.")))
			self.list.append(getConfigListEntry(_("Increased voltage"), currLnb.increased_voltage, _("Use increased voltage '14/18V' if there are problems when switching the LNB.")))
			additionalRotorLnb = maxFixedLnbPositions + MAX_LNB_WILDCARDS
			if (lnbnum < 65 and diction != "EN50607") or lnbnum == additionalRotorLnb:
				if isFBCLink(self.nim.slot):
					diseqcChoices = [choice for choice in currLnb.diseqcMode.choices.choices if choice[0] != "1_2"]
					if currLnb.diseqcMode.value == "1_2":
						currLnb.diseqcMode.value = "none"
					currLnb.diseqcMode.setChoices(diseqcChoices, default="none")
				self.advancedDiseqcMode = getConfigListEntry(_("DiSEqC mode"), currLnb.diseqcMode, _("Select '1.0' for standard committed switches, '1.1' for uncommitted switches, and '1.2' for systems using a positioner."))
				self.list.append(self.advancedDiseqcMode)
			if currLnb.diseqcMode.value != "none":
				self.list.append(getConfigListEntry(_("Fast DiSEqC"), currLnb.fastDiseqc, _("Select Fast DiSEqC if your aerial system supports it. If you are unsure select 'No'.")))
				self.toneburst = getConfigListEntry(_("Tone burst"), currLnb.toneburst, _("Select 'A' or 'B' if your aerial system requires this, otherwise select 'None'. If you are unsure select 'None'."))
				self.list.append(self.toneburst)
				self.committedDiseqcCommand = getConfigListEntry(_("DiSEqC 1.0 command"), currLnb.commitedDiseqcCommand, _("If you are using a DiSEqC committed switch enter the port letter required to access the LNB used for this satellite."))
				self.list.append(self.committedDiseqcCommand)
				if currLnb.diseqcMode.value == "1_0":
					if currLnb.toneburst.index and currLnb.commitedDiseqcCommand.index:
						self.list.append(getConfigListEntry(_("Command order"), currLnb.commandOrder1_0, _("This is the order in which DiSEqC commands are sent to the aerial system. The order must correspond exactly with the order the physical devices are arranged along the signal cable (starting from the receiver end).")))
				else:
					self.uncommittedDiseqcCommand = getConfigListEntry(_("DiSEqC 1.1 command"), currLnb.uncommittedDiseqcCommand, _("If you are using a DiSEqC uncommitted switch enter the port number required to access the LNB used for this satellite."))
					self.list.append(self.uncommittedDiseqcCommand)
					if currLnb.uncommittedDiseqcCommand.index:
						if currLnb.commandOrder.value == "ct":
							currLnb.commandOrder.value = "cut"
						elif currLnb.commandOrder.value == "tc":
							currLnb.commandOrder.value = "tcu"
					else:
						currLnb.commandOrder.value = "tc" if currLnb.commandOrder.index & 1 else "ct"
					self.commandOrder = getConfigListEntry(_("Command order"), currLnb.commandOrder, _("This is the order in which DiSEqC commands are sent to the aerial system. The order must correspond exactly with the order the physical devices are arranged along the signal cable (starting from the receiver end)."))
					if 1 < ((1 if currLnb.uncommittedDiseqcCommand.index else 0) + (1 if currLnb.commitedDiseqcCommand.index else 0) + (1 if currLnb.toneburst.index else 0)):
						self.list.append(self.commandOrder)
					if currLnb.uncommittedDiseqcCommand.index:
						self.list.append(getConfigListEntry(_("DiSEqC 1.1 repeats"), currLnb.diseqcRepeats, _("If using multiple uncommitted switches the DiSEqC commands must be sent multiple times. Set to the number of uncommitted switches in the chain minus one.")))
				self.list.append(getConfigListEntry(_("Sequence repeat"), currLnb.sequenceRepeat, _("Set sequence repeats if your aerial system requires this. Normally if the aerial system has been configured correctly sequence repeats will not be necessary. If yours does, recheck you have command order set correctly.")))
				if currLnb.diseqcMode.value == "1_2":
					if self.canMeasureInputPower:
						self.addInputPowerEntry()
						self.advancedPowerMeasurement = getConfigListEntry(_("Use power measurement"), currLnb.powerMeasurement, _("Detect positioner movement by its current consumption."))
						self.list.append(self.advancedPowerMeasurement)
						if currLnb.powerMeasurement.value:
							self.list.append(getConfigListEntry(_("Power threshold in mA"), currLnb.powerThreshold, _("Minimum difference between idle and moving current.")))
							self.turningSpeed = getConfigListEntry(_("Rotor turning speed"), currLnb.turningSpeed, _("Select how quickly the dish should move between satellites."))
							self.list.append(self.turningSpeed)
							if currLnb.turningSpeed.value == "fast epoch":
								self.turnFastEpochBegin = getConfigListEntry(_("Begin time"), currLnb.fastTurningBegin, _("Only move the dish quickly after this hour."))
								self.turnFastEpochEnd = getConfigListEntry(_("End time"), currLnb.fastTurningEnd, _("Only move the dish quickly before this hour."))
								self.list.append(self.turnFastEpochBegin)
								self.list.append(self.turnFastEpochEnd)
					else:
						if currLnb.powerMeasurement.value:
							currLnb.powerMeasurement.value = False
							currLnb.powerMeasurement.save()
					self.advancedUsalsEntry = getConfigListEntry(_("Use USALS for this sat"), Sat.usals, _("USALS automatically moves a motorized dish to the correct satellite based on the coordinates entered by the user. Without USALS each satellite will need to be setup and saved individually."))
					if lnbnum < 65:
						self.list.append(self.advancedUsalsEntry)
					if Sat.usals.value:
						self.list.append(getConfigListEntry(_("Longitude"), currLnb.longitude, _("Enter your current longitude. This is the number of degrees you are from zero meridian as a decimal.")))
						self.list.append(getConfigListEntry(" ", currLnb.longitudeOrientation, _("Enter if you are in the East or West hemisphere.")))
						self.list.append(getConfigListEntry(_("Latitude"), currLnb.latitude, _("Enter your current latitude. This is the number of degrees you are from the equator as a decimal.")))
						self.list.append(getConfigListEntry(" ", currLnb.latitudeOrientation, _("Enter if you are North or South of the equator.")))
					else:
						self.list.append(getConfigListEntry(_("Stored position"), Sat.rotorposition, _("Enter the number stored in the positioner that corresponds to this satellite.")))
					if not hasattr(self, 'additionalMotorOptions'):
						customMotorValues = any(x.value != x.default for x in (currLnb.turningspeedH, currLnb.turningspeedV, currLnb.tuningstepsize, currLnb.rotorPositions))
						self.additionalMotorOptions = ConfigBoolean(default=customMotorValues, descriptions={False: _("Show sub-menu"), True: _("Hide sub-menu")})
					self.showAdditionalMotorOptions = getConfigListEntry(_("Extra motor options"), self.additionalMotorOptions, _("Additional motor options allow you to enter details from your motor's specifications so Enigma can work out how long it will take to move to another satellite."))
					self.list.append(self.showAdditionalMotorOptions)
					if self.additionalMotorOptions.value:
						self.list.append(getConfigListEntry("   %s [\u00B0%s" % (_("Horizontal turning speed"), "/sec]"), currLnb.turningspeedH, _("Consult your motor's specifications for this information, or leave the default setting.")))
						self.list.append(getConfigListEntry("   %s [\u00B0%s" % (_("Vertical turning speed"), "/sec]"), currLnb.turningspeedV, _("Consult your motor's specifications for this information, or leave the default setting.")))
						self.list.append(getConfigListEntry("   %s [\u00B0]" % _("Turning step size"), currLnb.tuningstepsize, _("Consult your motor's specifications for this information, or leave the default setting.")))
						self.list.append(getConfigListEntry("   %s" % _("Max memory positions"), currLnb.rotorPositions, _("Consult your motor's specifications for this information, or leave the default setting.")))

	def fillAdvancedList(self):
		self.list = []
		self.configMode = getConfigListEntry(_("Configuration mode"), self.nimConfig.dvbs.configMode)
		self.list.append(self.configMode)
		self.advancedSatsEntry = getConfigListEntry(_("Satellite"), self.nimConfig.dvbs.advanced.sats)
		self.list.append(self.advancedSatsEntry)
		for x in self.nimConfig.dvbs.advanced.sat.keys():
			Sat = self.nimConfig.dvbs.advanced.sat[x]
			self.fillListWithAdvancedSatEntrys(Sat)
		self["config"].list = self.list

	def unicableconnection(self):
		def checkRecursiveConnect(slot_id):
			if slot_id in self.slot_dest_list:
				print(f"[SatConfig] Slot ID {slot_id}.")
				return False
			self.slot_dest_list.append(slot_id)
			slot_config = nimmanager.nim_slots[slot_id].config.dvbs
			if slot_config.configMode.value == "advanced":
				try:
					connected = slot_config.advanced.unicableconnected.value
				except Exception:
					connected = False
				if connected is True:
					return checkRecursiveConnect(int(slot_config.advanced.unicableconnectedTo.value))
			return True

		if self.nimConfig.dvbs.configMode.value == "advanced":
			connect_count = 0
			dvbs_slots = nimmanager.getNimListOfType("DVB-S")
			dvbs_slots_len = len(dvbs_slots)
			for slot in dvbs_slots:
				try:
					nim_slot = nimmanager.nim_slots[slot]
					if nim_slot == self.nimConfig:
						self_idx = slot   # noqa F841
					if nim_slot.config.dvbs.configMode.value == "advanced":
						if nim_slot.config.dvbs.advanced.unicableconnected.value is True:
							connect_count += 1
				except Exception:
					pass
			if connect_count >= dvbs_slots_len:
				return False
		self.slot_dest_list = []
		return checkRecursiveConnect(self.slotid)

	def checkLoopthrough(self):
		def checkRecursiveConnect(slot_id):
			if slot_id in self.slot_dest_list:
				return False
			self.slot_dest_list.append(slot_id)
			slot_config = nimmanager.nim_slots[slot_id].config.dvbs
			if slot_config.configMode.value == "loopthrough":
				return checkRecursiveConnect(int(slot_config.connectedTo.value))
			return True

		if self.nimConfig.dvbs.configMode.value == "loopthrough":
			loopthrough_count = 0
			dvbs_slots = nimmanager.getNimListOfType("DVB-S")
			dvbs_slots_len = len(dvbs_slots)
			for slot in dvbs_slots:
				try:
					nim_slot = nimmanager.nim_slots[slot]
					if nim_slot == self.nimConfig:
						self_idx = slot  # noqa F841
					if nim_slot.config.dvbs.configMode.value == "loopthrough":
						loopthrough_count += 1
				except Exception:
					pass
			if loopthrough_count >= dvbs_slots_len:
				return False
		self.slot_dest_list = []
		return checkRecursiveConnect(self.slotid)

	def keyOk(self):
		if self["config"].getCurrent() == self.advancedSelectSatsEntry and self.advancedSelectSatsEntry:
			conf = self.nimConfig.dvbs.advanced.sat[self.nimConfig.dvbs.advanced.sats.value].userSatellitesList
			self.session.openWithCallback(boundFunction(self.updateConfUserSatellitesList, conf), SelectSatsEntryScreen, userSatlist=conf.value)
		elif self["config"].getCurrent() == self.selectSatsEntry and self.selectSatsEntry:
			conf = self.nimConfig.dvbs.userSatellitesList
			self.session.openWithCallback(boundFunction(self.updateConfUserSatellitesList, conf), SelectSatsEntryScreen, userSatlist=conf.value)
		else:
			self.keySave()

	def updateConfUserSatellitesList(self, conf, val=None):
		if val is not None:
			conf.value = val
			conf.save()

	def keySave(self, recordingConfirmed=False):
		if not recordingConfirmed:
			nextRecording = self.session.nav.RecordTimer.getNextRecordingTime()
			secondsUntilRecording = nextRecording - time() if nextRecording and nextRecording > 0 else -1
			recordingSoon = 0 <= secondsUntilRecording < 360
			if self.session.nav.getAnyRecordingsCount() or recordingSoon:
				self.session.openWithCallback(
					self.keySaveRecordingConfirmed,
					MessageBox,
					_("A recording is running or will start within six minutes. Changing the tuner configuration can interrupt it. Save anyway?"),
					MessageBox.TYPE_YESNO,
					default=False
				)
				return
		if self.nim.canBeCompatible("DVB-S"):
			if not self.unicableconnection():
				self.session.open(MessageBox, _("The unicable connection setting is wrong.\nMaybe recursive connection of tuners."), MessageBox.TYPE_ERROR, timeout=10)
				return
			if not self.checkLoopthrough():
				self.session.open(MessageBox, _("The loopthrough setting is wrong."), MessageBox.TYPE_ERROR, timeout=10)
				return
			if self.nimConfig.dvbs.configMode.value == "advanced":
				error = self.validateUnicablePositions() or self.synchronizeInheritedUnicableUserBands()
				if error:
					self.session.open(MessageBox, error, MessageBox.TYPE_ERROR, timeout=15)
					return
		self.stopService()
		old_configured_sats = nimmanager.getConfiguredSats()
		if not self.run():
			return
		self.saveCableTerrestrialTemplate()
		self.markCableTerrestrialConfigured()
		new_configured_sats = nimmanager.getConfiguredSats()
		self.unconfed_sats = old_configured_sats - new_configured_sats
		self.satpos_to_remove = None
		self.deleteConfirmed((None, "no"))

	def keySaveRecordingConfirmed(self, answer):
		if answer:
			self.keySave(recordingConfirmed=True)

	def deleteConfirmed(self, confirmed):
		if confirmed is None:
			confirmed = (None, "no")
		if confirmed[1] == "yes" or confirmed[1] == "yestoall":
			eDVBDB.getInstance().removeServices(-1, -1, -1, self.satpos_to_remove)
		try:
			if self.satpos_to_remove is not None:
				self.unconfed_sats.remove(self.satpos_to_remove)
		except Exception:
			self.unconfed_sats = None
		self.satpos_to_remove = None
		for orbpos in self.unconfed_sats:
			self.satpos_to_remove = orbpos
			orbpos = self.satpos_to_remove
			try:
				sat_name = str(nimmanager.getSatDescription(orbpos))  # Why we need this cast?
			except Exception:
				if orbpos > 1800:  # West.
					orbpos = 3600 - orbpos
					h = _("W")
				else:
					h = _("E")
				sat_name = ("%d.%d" + h) % (orbpos // 10, orbpos % 10)
			if confirmed[1] == "yes" or confirmed[1] == "no":
				# TRANSLATORS: The satellite with name '%s' is no longer used after a configuration change. The user is asked whether or not the satellite should be deleted.
				self.session.openWithCallback(self.deleteConfirmed, ChoiceBox, _("%s is no longer used. Should it be deleted?") % sat_name, [(_("Yes"), "yes"), (_("No"), "no"), (_("Yes to all"), "yestoall"), (_("No to all"), "notoall")], None, 1)
			if confirmed[1] == "yestoall" or confirmed[1] == "notoall":
				self.deleteConfirmed(confirmed)
			break
		else:
			self.restoreService(_("Zap back to service before tuner setup?"))

	def createSummary(self):
		return SetupSummary


class NimSelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("Choose Tuner"))
		self.list = [None] * nimmanager.getSlotCount()
		self["nimlist"] = List(self.list)
		self.loadFBCLinks()
		self.updateList()
		self.setResultClass()
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Select"))
		self["actions"] = ActionMap(["SetupActions", "ColorActions", "MenuActions", "ChannelSelectEPGActions"], {
			"ok": self.okbuttonClick,
			"info": self.extraInfo,
			"epg": self.extraInfo,
			"cancel": self.close,
			"red": self.close,
			"green": self.okbuttonClick,
			"menu": self.exit,
		}, prio=-2)

	def loadFBCLinks(self):
		for x in nimmanager.nim_slots:
			slotid = x.slot   # noqa F841
			if self.showNim(x):
				if x.isCompatible("DVB-S"):
					nimConfig = nimmanager.getNimConfig(x.slot).dvbs
					configMode = nimConfig.configMode.value
					if isFBCLink(x.slot) and configMode != "advanced":
						link = getLinkedSlotID(x.slot)
						if link == -1:
							nimConfig.configMode.value = "nothing"
						else:
							nimConfig.configMode.value = "loopthrough"
							nimConfig.connectedTo.value = str(link)

	def checkFBCLinks(self):
		for x in nimmanager.nim_slots:
			if self.showNim(x):
				if x.isCompatible("DVB-S"):
					slotid = x.slot
					if isFBCLink(slotid):
						link = getLinkedSlotID(slotid)
						if link != -1:
							linkNimConfig = nimmanager.getNimConfig(link).dvbs
							if linkNimConfig.configMode.value == "nothing":
								nimConfig = nimmanager.getNimConfig(slotid).dvbs
								nimConfig.configMode.value = "nothing"  # Reset child if parent is "nothing"
								nimConfig.configMode.save()

	def exit(self):
		self.close(True)

	def setResultClass(self):
		self.resultclass = NimSetup

	def extraInfo(self):
		nim = self["nimlist"].getCurrent()
		nim = nim and nim[3]
		if config.usage.setup_level.index >= 2 and nim is not None:
			output = []
			for value in eDVBResourceManager.getInstance().getFrontendCapabilities(nim.slot).splitlines():
				kv = value.split(":")
				if len(kv) == 2:
					val = kv[1]
					val = val[:-1] if val[-1] == "," else val
					output.append("%s: %s" % (_(kv[0]), val))
			text = "\n\n".join(output)
			self.session.open(MessageBox, text, MessageBox.TYPE_INFO, simple=True)

	def okbuttonClick(self):
		nim = self["nimlist"].getCurrent()
		nim = nim and nim[3]
		if nim is None:
			return
		if isFBCLink(nim.slot):
			if nim.isCompatible("DVB-S"):
				nimConfig = nimmanager.getNimConfig(nim.slot).dvbs
			elif nim.isCompatible("DVB-C"):
				nimConfig = nimmanager.getNimConfig(nim.slot).dvbc
			elif nim.isCompatible("DVB-T"):
				nimConfig = nimmanager.getNimConfig(nim.slot).dvbt
			if nimConfig.configMode.value == "loopthrough":
				return
		if not nim.empty and nim.isSupported():
			self.session.openWithCallback(boundFunction(self.NimSetupCB, self["nimlist"].getIndex()), self.resultclass, nim.slot)

	def NimSetupCB(self, index=None):
		self.checkFBCLinks()
		self.loadFBCLinks()
		self.updateList(index)

	def showNim(self, nim):
		return not (nim.isEmpty() or (nim.isCompatible("DVB-C") and nim.isFBCTuner() and not nim.isFBCRoot()))

	@staticmethod
	def orbitalPositionToString(position):
		if position > 1800:
			position = 3600 - position
			return f"{position // 10}.{position % 10}W"
		return f"{position // 10}.{position % 10}E"

	def updateList(self, index=None):
		self.list = []
		for x in nimmanager.nim_slots:
			if x.isFBCLink() and not x.isFBCLinkEnabled():
				continue
			slotid = x.slot
			text = ""
			if self.showNim(x):
				fbc_text = ""
				if x.isFBCTuner():
					fbc_text = (x.isFBCRoot() and _("Slot %s / FBC in %s") % (x.is_fbc[2], x.is_fbc[1])) or _("Slot %s / FBC virtual %s") % (x.is_fbc[2], x.is_fbc[1] - (x.isCompatible("DVB-S") and 2 or 1))
				if x.isMultiType():
					if x.canBeCompatible("DVB-S") and nimmanager.getNimConfig(x.slot).dvbs.configMode.value != "nothing":
						text = " DVB-S,"
					if x.canBeCompatible("DVB-C") and nimmanager.getNimConfig(x.slot).dvbc.configMode.value != "nothing":
						text = " DVB-C," + text
					if x.canBeCompatible("DVB-T") and nimmanager.getNimConfig(x.slot).dvbt.configMode.value != "nothing":
						text = " DVB-T," + text
					if text:
						text = _("Enabled") + ":" + text[:-1]
					else:
						text = _("nothing connected")
					text = _("Switchable tuner types:") + "(" + ",".join(list(x.getMultiTypeList().values())) + ")" + "\n" + text
				elif x.isCompatible("DVB-S"):
					nimConfig = nimmanager.getNimConfig(x.slot).dvbs
					text = nimConfig.configMode.value
					if nimConfig.configMode.value in ("loopthrough", "equal", "satposdepends"):
						text = {
								"loopthrough": _("Loop through to"),
								"equal": _("Equal to"),
								"satposdepends": _("Second cable of motorized LNB")
							}[nimConfig.configMode.value]
						if len(x.input_name) > 1:
							text += " " + _("Tuner") + " " + ["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B", "C"][int(nimConfig.connectedTo.value)]
						else:
							text += " " + _("Tuner") + " " + chr(ord("A") + int(nimConfig.connectedTo.value))
						if fbc_text:
							text += "\n" + fbc_text
					elif nimConfig.configMode.value == "nothing":
						if isFBCLink(x.slot):
							linkedSlot = getLinkedSlotID(x.slot)
							text = _("FBC automatic: inactive") if linkedSlot < 0 else _("FBC automatic: connected to %s") % nimmanager.getNimDescription(linkedSlot)
						else:
							text = _("Not configured")
						if fbc_text:
							text += "\n" + fbc_text
					elif nimConfig.configMode.value == "simple":
						if nimConfig.diseqcMode.value in ("single", "toneburst_a_b", "diseqc_a_b", "diseqc_a_b_c_d"):
							text = "%s\n%s:" % ({"single": _("Single"), "toneburst_a_b": _("Tone burst A/B"), "diseqc_a_b": _("DiSEqC A/B"), "diseqc_a_b_c_d": _("DiSEqC A/B/C/D")}[nimConfig.diseqcMode.value], _("Sats"))
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
								# We need a newline here, since multi content lists don't support automatic line wrapping.
								text += ", ".join(satnames[:2]) + ",\n"
								text += "         " + ", ".join(satnames[2:])
						elif nimConfig.diseqcMode.value in ("positioner", "positioner_select"):
							text = "%s: " % {"positioner": _("Positioner"), "positioner_select": _("Positioner (selecting satellites)")}[nimConfig.diseqcMode.value]
							if nimConfig.positionerMode.value == "usals":
								text += "USALS"
							elif nimConfig.positionerMode.value == "manual":
								text += _("Manual")
						else:
							text = _("Simple")
						if fbc_text:
							text = fbc_text + " / " + text
					elif nimConfig.configMode.value == "advanced":
						text = _("Advanced")
						sat = nimConfig.advanced.sats.value
						lnb = nimConfig.advanced.sat.get(sat)
						if lnb:
							lnb = nimConfig.advanced.sat.get(sat).content.items.get("lnb")
							if lnb:
								lnb = int(lnb.value)
								try:
									lof = nimConfig.advanced.lnb[lnb].lof.value
									text += " / " + LNB_CHOICES().get(lof, lof)
									if lof == "unicable":
										uni = nimConfig.advanced.lnb[lnb].unicable.value
										text += " / " + UNICABLE_CHOICES().get(uni, uni)
								except AttributeError:
									pass
						unicableConnected = nimConfig.advanced.content.items.get("unicableconnected")
						unicableConnectedTo = nimConfig.advanced.content.items.get("unicableconnectedTo")
						if unicableConnected is not None and unicableConnectedTo is not None and unicableConnected.value and unicableConnectedTo.value.isdigit():
							text += " / " + _("Connected to") + " " + nimmanager.getNimDescription(int(unicableConnectedTo.value))
						configuredSatellites = nimmanager.getSatListForNim(slotid)
						rotorSatellites = nimmanager.getRotorSatListForNim(slotid)
						if int(nimConfig.advanced.sat[3607].lnb.value) != 0 and nimConfig.connectedTo.value.isdigit():
							text += "\n" + _("Additional rotor cable from %s") % nimmanager.getNimDescription(int(nimConfig.connectedTo.value))
						elif rotorSatellites:
							text += "\n" + _("Rotor: %d satellites") % len(rotorSatellites)
						elif configuredSatellites:
							positions = [self.orbitalPositionToString(satellite[0]) for satellite in configuredSatellites]
							text += "\n" + _("Sats") + ": " + ", ".join(positions[:8]) + (", …" if len(positions) > 8 else "")
						if fbc_text:
							text += "\n" + fbc_text
					if isFBCLink(x.slot) and nimConfig.configMode.value not in ("advanced", "loopthrough", "nothing"):
						text += _("\n<This tuner is configured automatically>")
				elif x.isCompatible("DVB-T"):
					nimConfig = nimmanager.getNimConfig(x.slot).dvbt
					if nimConfig.configMode.value == "nothing":
						text = _("nothing connected")
					elif nimConfig.configMode.value == "enabled":
						text = _("Enabled")
						if hasattr(nimConfig, "terrestrial_5V") and nimConfig.terrestrial_5V.value:
							text += _(" (+5 volt terrestrial)")
				elif x.isCompatible("DVB-C"):
					nimConfig = nimmanager.getNimConfig(x.slot).dvbc
					if nimConfig.configMode.value == "nothing":
						text = _("nothing connected")
					elif nimConfig.configMode.value == "enabled":
						text = _("Enabled")
				elif x.isCompatible("ATSC"):
					nimConfig = nimmanager.getNimConfig(x.slot).atsc
					if nimConfig.configMode.value == "nothing":
						text = _("nothing connected")
					elif nimConfig.configMode.value == "enabled":
						text = _("Enabled")
				if not x.isSupported():
					text = _("Tuner is not supported")
				self.list.append((slotid, x.friendly_full_description_compressed if x.isCompatible("DVB-C") and x.isFBCTuner() else x.friendly_full_description, text, x))
		self["nimlist"].setList(self.list)
		self["nimlist"].updateList(self.list)
		if index is not None:
			self["nimlist"].setIndex(index)


class SelectSatsEntryScreen(Screen):
	skin = """
		<screen name="SelectSatsEntryScreen" position="center,center" size="560,410" title="Select Sats Entry" resolution="1280,720">
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

	def __init__(self, session, userSatlist=[]):
		Screen.__init__(self, session)
		self.setTitle(_("Select Satellites"))
		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("Save"))
		self["key_yellow"] = Button(_("Sort by"))
		self["key_blue"] = Button(_("Invert"))
		self["hint"] = Label(_("Press OK to toggle the selection"))
		SatList = []
		for sat in nimmanager.getSatList():
			selected = False
			if isinstance(userSatlist, str) and str(sat[0]) in userSatlist:
				selected = True
			SatList.append((sat[0], sat[1], sat[2], selected))
		self["list"] = SelectionList(enableWrapAround=True)
		sat_list = [SelectionEntryComponent(x[1], x[0], x[2], x[3]) for x in SatList]
		self["list"].setList(sat_list)
		self["setupActions"] = ActionMap(["SetupActions", "ColorActions"], {
			"red": self.cancel,
			"green": self.save,
			"yellow": self.sortBy,
			"blue": self["list"].toggleAllSelection,
			"save": self.save,
			"cancel": self.cancel,
			"ok": self["list"].toggleSelection,
		}, prio=-2)

	def save(self):
		val = [x[0][1] for x in self["list"].list if x[0][3]]
		self.close(str(val))

	def cancel(self):
		self.close(None)

	def sortBy(self):
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

		lst = self["list"].list
		if len(lst) > 1:
			menu = [(_("Reverse list"), "2"), (_("Standard list"), "1")]
			connected_sat = [x[0][1] for x in lst if x[0][3]]
			if len(connected_sat) > 0:
				menu.insert(0, (_("Connected satellites"), "3"))
			self.session.openWithCallback(sortAction, ChoiceBox, title=_("Select sort method:"), list=menu)
