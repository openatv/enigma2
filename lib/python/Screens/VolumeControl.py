from copy import deepcopy

from enigma import eDVBVolumecontrol, eServiceCenter, eServiceReference, eTimer, iPlayableService, iServiceInformation

from GlobalActions import globalActionMap
from ServiceReference import ServiceReference
from Components.ActionMap import HelpableActionMap
from Components.config import ConfigBoolean, ConfigInteger, ConfigSelection, ConfigSelectionNumber, ConfigSubsection, ConfigYesNo, NoSave, config, getConfigListEntry
from Components.Label import Label
from Components.ServiceEventTracker import ServiceEventTracker
from Components.VolumeBar import VolumeBar
from Components.Sources.StaticText import StaticText
from Screens.ChannelSelection import ChannelSelectionBase
from Screens.Screen import Screen
from Screens.Setup import Setup
from Tools.Directories import SCOPE_CONFIG, fileReadXML, fileWriteLines, resolveFilename

MODULE_NAME = __name__.split(".")[-1]


class Mute(Screen):
	pass


class Volume(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self["VolumeText"] = Label()
		self["Volume"] = VolumeBar()

	def getVolume(self):
		return self["Volume"].getValue()

	def setValue(self, volume):
		print(f"[VolumeControl] Volume set to {volume}.")
		self["VolumeText"].setText(str(volume))
		self["Volume"].setValue(volume)


class VolumeAdjustSettings(Setup):
	def __init__(self, session):
		self.volumeControl = eDVBVolumecontrol.getInstance()
		self.initialVolume = self.volumeControl.getVolume()
		self.initialOffset = self.volumeControl.getVolumeOffset()
		self.volumeOffsets = VolumeAdjust.instance.getVolumeOffsets()
		self.volumeRemembered = VolumeAdjust.instance.getVolumeRemembered()
		self.activeServiceReference, serviceName = VolumeAdjust.instance.getPlayingServiceReference()
		self.activeServiceReference = self.activeServiceReference.toString() if self.activeServiceReference else None
		self.initialVolumeOffsets = deepcopy(self.volumeOffsets)
		self.initialVolumeRemembered = deepcopy(self.volumeRemembered)
		Setup.__init__(self, session, setup="VolumeAdjust")
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self["offsetActions"] = HelpableActionMap(self, ["ColorActions", "TVRadioActions"], {
			"yellow": (self.keyAddRemoveService, _("Add/Remove the current service to/from the Volume Offset list")),
			"keyTV": (self.keyAddTVService, _("Add a TV service to the Volume Offset list")),
			"keyRadio": (self.keyAddRadioService, _("Add a RADIO service to the Volume Offset list")),
			"keyTVRadio": (self.keyAddService, _("Add a service to the Volume Offset list"))
		}, prio=0, description=_("Volume Adjust Actions"))
		self["currentAction"] = HelpableActionMap(self, ["ColorActions"], {
			"blue": (self.keyAddServiceReference, _("Add the current/active service to the Volume Offset list"))
		}, prio=0, description=_("Volume Adjust Actions"))

	def layoutFinished(self):
		Setup.layoutFinished(self)
		self.selectionChanged()

	def createSetup(self, appendItems=None, prependItems=None):  # Redefine the method of the same in in the Setup class.
		self.list = []
		Setup.createSetup(self)
		volumeList = self["config"].getList()
		if config.volumeAdjust.adjustMode.value == VolumeAdjust.MODE_OFFSET and self.volumeOffsets:
			volumeList.append(getConfigListEntry(_("Currently Defined Volume Offsets:")))
			for serviceReference in self.volumeOffsets.keys():
				[serviceName, offset] = self.volumeOffsets[serviceReference]
				default = config.volumeAdjust.defaultOffset.value if offset == VolumeAdjust.NEW_VALUE else offset
				entry = NoSave(ConfigSelectionNumber(default=default, min=VolumeAdjust.OFFSET_MIN, max=VolumeAdjust.OFFSET_MAX, stepwidth=1, wraparound=False))
				if offset == VolumeAdjust.NEW_VALUE:
					entry.default = VolumeAdjust.NEW_VALUE  # This triggers a cancel confirmation for unedited new entries.
				volumeList.append(getConfigListEntry(f"-   {serviceName}", entry, _("Set the volume offset for the '%s' service.") % serviceName, serviceReference))
		elif config.volumeAdjust.adjustMode.value == VolumeAdjust.MODE_LAST and self.volumeRemembered:
			volumeList.append(getConfigListEntry(_("Currently Remembered Volume Levels:")))
			for serviceReference in self.volumeRemembered.keys():
				[serviceName, last] = self.volumeRemembered[serviceReference]
				if serviceReference == self.activeServiceReference:  # Update the current service volume to the current volume level.
					last = self.volumeControl.getVolume()
				entry = NoSave(ConfigSelectionNumber(default=last, min=VolumeAdjust.LAST_MIN, max=VolumeAdjust.LAST_MAX, stepwidth=1, wraparound=False))
				volumeList.append(getConfigListEntry(f"-   {serviceName}", entry, _("Set the volume level for the '%s' service.") % serviceName, serviceReference))
		self["config"].setList(volumeList)

	def selectionChanged(self):  # Redefine the method of the same in in the Setup class.
		# self.initialVolume = self.volumeControl.getVolume()
		if len(self["config"].getCurrent()) > 3:
			if (config.volumeAdjust.adjustMode.value == VolumeAdjust.MODE_OFFSET and self.volumeOffsets) or (config.volumeAdjust.adjustMode.value == VolumeAdjust.MODE_LAST and self.volumeRemembered):
				self["key_yellow"].setText(_("Remove Service"))
		elif config.volumeAdjust.adjustMode.value == VolumeAdjust.MODE_OFFSET:
			self["key_yellow"].setText(_("Add Service"))
		else:
			self["key_yellow"].setText("")
		if config.volumeAdjust.adjustMode.value == VolumeAdjust.MODE_OFFSET and self.activeServiceReference not in self.volumeOffsets.keys():
			self["key_blue"].setText(_("Add Current"))
			self["currentAction"].setEnabled(True)
		else:
			self["key_blue"].setText("")
			self["currentAction"].setEnabled(False)
		Setup.selectionChanged(self)

	def changedEntry(self):  # Redefine the method of the same in in the Setup class. Setup method calls createSetup() when a ConfigBoolean or ConfigSelection based class is changed!
		# self.initialVolume = self.volumeControl.getVolume()
		current = self["config"].getCurrent()
		if len(current) > 3:
			value = current[1].value
			serviceReference = current[3]
			match config.volumeAdjust.adjustMode.value:
				case VolumeAdjust.MODE_OFFSET:
					serviceName, offset = self.volumeOffsets[serviceReference]
					self.volumeOffsets[serviceReference] = [serviceName, value]
					if serviceReference == self.activeServiceReference:  # Apply the offset if we are setting an offset for the current service.
						self.volumeControl.setVolumeOffset(value)
				case VolumeAdjust.MODE_LAST:
					serviceName, last = self.volumeRemembered[serviceReference]
					self.volumeRemembered[serviceReference] = [serviceName, value]
					if serviceReference == self.activeServiceReference:  # Apply the offset if we are setting an offset for the current service.
						self.volumeControl.setVolume(value, value)  # Volume left, volume right.
		else:
			Setup.changedEntry(self)

	def keySave(self):  # Redefine the method of the same in in the Setup class.
		if self.volumeOffsets != self.initialVolumeOffsets or self.volumeRemembered != self.initialVolumeRemembered:  # Save the volume data if there are any changes.
			VolumeAdjust.instance.saveVolumeXML()
		VolumeAdjust.instance.refreshSettings()
		Setup.keySave(self)

	def cancelConfirm(self, result):  # Redefine the method of the same in in the Setup class.
		if not result:
			return
		if self.volumeOffsets != self.initialVolumeOffsets:
			VolumeAdjust.instance.setVolumeOffsets(self.initialVolumeOffsets)
		if self.volumeRemembered != self.initialVolumeRemembered:
			VolumeAdjust.instance.setVolumeRemembered(self.initialVolumeRemembered)
		if self.volumeControl.getVolume() != self.initialVolume:  # Reset the volume if we were setting a volume for the current service.
			self.volumeControl.setVolume(self.initialVolume, self.initialVolume)
		if self.volumeControl.getVolumeOffset() != self.initialOffset:  # Reset the offset if we were setting an offset for the current service.
			self.volumeControl.setVolumeOffset(self.initialOffset)
		Setup.cancelConfirm(self, result)

	def keyAddRemoveService(self):
		current = self["config"].getCurrent()
		if len(current) > 3:
			serviceReference = current[3]
			match config.volumeAdjust.adjustMode.value:
				case VolumeAdjust.MODE_OFFSET:
					serviceName = self.volumeOffsets[serviceReference][0]
					del self.volumeOffsets[serviceReference]
				case VolumeAdjust.MODE_LAST:
					serviceName = self.volumeRemembered[serviceReference][0]
					del self.volumeRemembered[serviceReference]
				case _:
					serviceName = "?"
			index = self["config"].getCurrentIndex()
			self.createSetup()
			configLength = len(self["config"].getList())
			self["config"].setCurrentIndex(index if index < configLength else configLength - 1)
			self.setFootnote(_("Service '%s' deleted.") % serviceName)
		elif config.volumeAdjust.adjustMode.value == VolumeAdjust.MODE_OFFSET:
			self.keyAddService()

	def keyAddTVService(self):
		self.session.openWithCallback(self.addServiceCallback, VolumeAdjustServiceSelection, "TV")

	def keyAddRadioService(self):
		self.session.openWithCallback(self.addServiceCallback, VolumeAdjustServiceSelection, "RADIO")

	def keyAddService(self):
		from Screens.InfoBar import InfoBar  # This must be here to avoid cyclic imports!
		mode = InfoBar.instance.servicelist.getCurrentMode() if InfoBar.instance and InfoBar.instance.servicelist else "TV"
		self.session.openWithCallback(self.addServiceCallback, VolumeAdjustServiceSelection, mode)

	def addServiceCallback(self, serviceReference):
		if serviceReference:
			serviceName = VolumeAdjust.instance.getServiceName(serviceReference)
			serviceReference = serviceReference.toString()
			if serviceReference in self.volumeOffsets.keys():
				self.setFootnote(_("Service '%s' is already defined.") % serviceName)
			else:
				self.keyAddServiceReference(serviceReference, serviceName)
		else:
			self.setFootnote(_("Service selection canceled."))

	def keyAddServiceReference(self, serviceReference=None, serviceName=None):
		if serviceReference is None:
			serviceReference = self.activeServiceReference
		if serviceName is None:
			serviceName = VolumeAdjust.instance.getServiceName(serviceReference)
		if serviceReference is not None and serviceName is not None:
			self.volumeOffsets[serviceReference] = [serviceName, VolumeAdjust.NEW_VALUE]
			self.createSetup()
			self["config"].goBottom()
			self.setFootnote(_("Service '%s' added.") % serviceName)


class VolumeAdjustServiceSelection(ChannelSelectionBase):
	skin = """
	<screen name="VolumeAdjustServiceSelection" title="Volume Adjust Service Selection" position="center,center" size="560,430" resolution="1280,720">
		<widget name="list" position="0,0" size="e,e-50" scrollbarMode="showOnDemand" />
		<widget source="key_red" render="Label" position="0,e-40" size="180,40" backgroundColor="key_red" conditional="key_red" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_green" render="Label" position="190,e-40" size="180,40" backgroundColor="key_green" conditional="key_green" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_yellow" render="Label" position="380,e-40" size="180,40" backgroundColor="key_yellow" conditional="key_yellow" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_blue" render="Label" position="570,e-40" size="180,40" backgroundColor="key_blue" conditional="key_blue" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-80,e-40" size="80,40" backgroundColor="key_back" conditional="key_help" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	def __init__(self, session, mode):
		ChannelSelectionBase.__init__(self, session)
		self.skinName = ["VolumeAdjustServiceSelection", "SmallChannelSelection", "mySmallChannelSelection"]  # The screen "mySmallChannelSelection" is for legacy support only.
		self.setTitle(_("Volume Adjust Service Selection"))
		service = self.session.nav.getCurrentService()
		if service:
			info = service.info()
			if info:
				self.servicelist.setPlayableIgnoreService(eServiceReference(info.getInfoString(iServiceInformation.sServiceref)))
		self["volumeServiceActions"] = HelpableActionMap(self, ["SelectCancelActions", "TVRadioActions"], {
			"select": (self.keySelect, _("Select the currently highlighted service")),
			"cancel": (self.keyCancel, _("Cancel the service selection")),
			"keyTVRadio": (self.keyModeToggle, _("Toggle between the available TV and RADIO services"))
		}, prio=0, description=_("Volume Adjust Service Selection Actions"))
		self["tvAction"] = HelpableActionMap(self, ["TVRadioActions"], {
			"keyTV": (self.keyModeTV, _("Switch to the available TV services"))
		}, prio=0, description=_("Volume Adjust Service Selection Actions"))
		self["radioAction"] = HelpableActionMap(self, ["TVRadioActions"], {
			"keyRadio": (self.keyModeRadio, _("Switch to the available RADIO services"))
		}, prio=0, description=_("Volume Adjust Service Selection Actions"))
		match mode:
			case "TV":
				mode = self.MODE_TV
			case "RADIO":
				mode = self.MODE_RADIO
		self.mode = mode
		self.onShown.append(self.setMode)

	def setMode(self, mode=None):
		if mode is None:
			mode = self.mode
		self["tvAction"].setEnabled(mode == self.MODE_RADIO)
		self["radioAction"].setEnabled(mode == self.MODE_TV)
		self.setCurrentMode(mode)
		self.showFavourites()

	def keySelect(self):
		serviceReference = self.getCurrentSelection()
		if (serviceReference.flags & 7) == 7:
			self.enterPath(serviceReference)
		elif not (serviceReference.flags & eServiceReference.isMarker):
			serviceReference = self.getCurrentSelection()
			self.close(serviceReference)

	def keyCancel(self):
		self.close(None)

	def keyModeToggle(self):
		self.mode = self.MODE_RADIO if self.mode == self.MODE_TV else self.MODE_TV
		self.setMode(self.mode)

	def keyModeTV(self):
		self.setMode(self.MODE_TV)

	def keyModeRadio(self):
		self.setMode(self.MODE_RADIO)


class VolumeAdjust:
	VOLUME_FILE = resolveFilename(SCOPE_CONFIG, "volume.xml")
	DEFAULT_VOLUME = 50
	DEFAULT_OFFSET = 10
	OFFSET_MIN = -100
	OFFSET_MAX = 100
	NEW_VALUE = -1000  # NEW_VALUE must not be between OFFSET_MIN and OFFSET_MAX (inclusive).
	LAST_MIN = 0
	LAST_MAX = 100

	MODE_DISABLED = 0
	MODE_OFFSET = 1
	MODE_LAST = 2

	instance = None

	def __init__(self, session):
		if VolumeAdjust.instance:
			print("[VolumeControl] Error: Only one VolumeAdjust instance is allowed!")
		else:
			VolumeAdjust.instance = self
			self.session = session
			self.serviceReference = None
			self.volumeControl = eDVBVolumecontrol.getInstance()
			config.volumeAdjust = ConfigSubsection()
			config.volumeAdjust.adjustMode = ConfigSelection(default=self.MODE_DISABLED, choices=[
				(self.MODE_DISABLED, _("Disabled")),
				(self.MODE_OFFSET, _("Defined volume offset")),
				(self.MODE_LAST, _("Last used/set volume"))
			])
			config.volumeAdjust.defaultOffset = ConfigSelectionNumber(default=self.DEFAULT_OFFSET, min=self.OFFSET_MIN, max=self.OFFSET_MAX, stepwidth=1, wraparound=False)
			config.volumeAdjust.dolbyEnabled = ConfigYesNo(default=False)
			config.volumeAdjust.dolbyOffset = ConfigSelectionNumber(default=self.DEFAULT_OFFSET, min=self.OFFSET_MIN, max=self.OFFSET_MAX, stepwidth=1, wraparound=False)
			config.volumeAdjust.mpegMax = ConfigSelectionNumber(default=100, min=10, max=100, stepwidth=5)
			config.volumeAdjust.showVolumeBar = ConfigYesNo(default=False)
			self.onClose = []  # This is used by ServiceEventTracker.
			self.eventTracker = ServiceEventTracker(screen=self, eventmap={
				iPlayableService.evStart: self.eventStart,
				iPlayableService.evEnd: self.eventEnd,
				iPlayableService.evUpdatedInfo: self.eventUpdatedInfo
			})
			self.refreshSettings()  # Pre-load some stable config data to save processing time.
			self.loadVolumeXML()
			self.session.onShutdown.append(self.saveVolumeXML)

	def loadVolumeXML(self):  # Load the volume adjustment configuration data.
		volumeOffsets = {}
		volumeRemembered = {}
		volumeDom = fileReadXML(self.VOLUME_FILE, source=MODULE_NAME)
		if volumeDom is None:
			print("[VolumeControl] Volume adjustment data initialized.")
		else:
			print(f"[VolumeControl] Volume adjustment data initialized from '{self.VOLUME_FILE}'.")
			for offsets in volumeDom.findall("offsets"):
				for entry in offsets.findall("offset"):
					serviceReference = entry.get("serviceReference")
					serviceName = entry.get("serviceName")
					offset = int(entry.get("value", 0))
					if serviceReference and serviceName:
						volumeOffsets[serviceReference] = [serviceName, offset]
			for remembered in volumeDom.findall("remembered"):
				for entry in remembered.findall("remember"):
					serviceReference = entry.get("serviceReference")
					serviceName = entry.get("serviceName")
					last = int(entry.get("value", self.DEFAULT_VOLUME))
					if serviceReference and serviceName:
						volumeRemembered[serviceReference] = [serviceName, last]
		self.volumeOffsets = volumeOffsets
		self.volumeRemembered = volumeRemembered

	def saveVolumeXML(self):  # Save the volume adjustment configuration data.
		xml = []
		xml.append("<?xml version=\"1.0\" encoding=\"utf-8\" ?>")
		xml.append("<volumexml>")
		if self.volumeOffsets:
			xml.append("\t<offsets>")
			for serviceReference in self.volumeOffsets.keys():
				[serviceName, offset] = self.volumeOffsets[serviceReference]
				xml.append(f"\t\t<offset serviceReference=\"{serviceReference}\" serviceName=\"{serviceName}\" value=\"{offset}\" />")
			xml.append("\t</offsets>")
		if self.volumeRemembered:
			xml.append("\t<remembered>")
			for serviceReference in self.volumeRemembered.keys():
				[serviceName, last] = self.volumeRemembered[serviceReference]
				xml.append(f"\t\t<remember serviceReference=\"{serviceReference}\" serviceName=\"{serviceName}\" value=\"{last}\" />")
			xml.append("\t</remembered>")
		xml.append("</volumexml>")
		if fileWriteLines(self.VOLUME_FILE, xml, source=MODULE_NAME):
			print(f"[VolumeControl] Volume adjustment data saved to '{self.VOLUME_FILE}'.")
		else:
			print(f"[VolumeControl] Error: Volume adjustment data could not be saved to '{self.VOLUME_FILE}'!")

	def eventStart(self):
		serviceReference, serviceName = self.getPlayingServiceReference()
		if serviceReference and serviceReference.valid():
			serviceReference = serviceReference.toString()
			self.volumeControl.setVolumeOffset(0)
			volume = self.volumeControl.getVolume()
			match self.adjustMode:
				case self.MODE_OFFSET:
					print(f"[VolumeControl] Volume for service '{serviceName}' reset to {volume} until audio data available.")
				case self.MODE_LAST:
					[serviceName, last] = self.volumeRemembered.get(serviceReference, [serviceName, volume])
					if last != volume:
						self.updateVolumeControlUI(last)
						print(f"[VolumeControl] Volume for service '{serviceName}' being restored to {last}.")
						self.volumeControl.setVolume(last, last)  # Set new volume.
					self.volumeRemembered[serviceReference] = [serviceName, last]
			self.serviceReference = serviceReference
			self.serviceName = serviceName
		else:
			self.serviceReference = None
			self.serviceName = ""
		self.serviceAudio = None

	def eventEnd(self):
		if self.serviceReference:
			match self.adjustMode:
				case self.MODE_OFFSET:
					offset = self.volumeControl.getVolumeOffset()
					if offset:
						self.volumeControl.setVolumeOffset(0)
						print(f"[VolumeControl] Volume offset of {offset} for service '{self.serviceName}' removed.")
				case self.MODE_LAST:
					volume = self.volumeControl.getVolume()
					self.volumeRemembered[self.serviceReference] = [self.serviceName, volume]
					print(f"[VolumeControl] Volume for service '{self.serviceName}' saved as {volume}.")
			self.serviceReference = None
			self.serviceName = ""
			self.serviceAudio = None

	def eventUpdatedInfo(self):
		def isCurrentAudioAC3DTS():
			audioTracks = self.session.nav.getCurrentService().audioTracks()
			result = False
			if audioTracks:
				try:  # Uhh, servicemp3 sometimes leads to OverflowError errors!
					description = audioTracks.getTrackInfo(audioTracks.getCurrentTrack()).getDescription()
					if "AC3" in description or "DTS" in description or description == "Dolby Digital" or (description and description.split()[0] in ("AC3", "AC-3", "A_AC3", "A_AC-3", "A-AC-3", "E-AC-3", "A_EAC3", "DTS", "DTS-HD", "AC4", "AAC-HE")):
						result = True
				except Exception:
					description = "Unknown"
			# print(f"[VolumeControl] isCurrentAudioAC3DTS DEBUG: Service '{self.serviceName}' audio description '{description}' means AudioAC3Dolby is {result}.")
			return result

		if self.serviceReference and self.adjustMode == self.MODE_OFFSET:
			if self.serviceReference in self.volumeOffsets.keys():
				isAC3 = isCurrentAudioAC3DTS()
				if isAC3 != self.serviceAudio:
					self.serviceAudio = isAC3
					[serviceName, offset] = self.volumeOffsets[self.serviceReference]  # The test above ensures that serviceReference is defined.
					if offset:  # For now it is assumed that serviceName is the same as self.serviceName so the offset is assumed to be appropriate!
						offset = self.volumeControl.setVolumeOffset(offset)
						volume = self.volumeControl.getVolume()
						print(f"[VolumeControl] Volume for service '{serviceName}' being adjusted by {offset} to {volume}.")
						self.updateVolumeControlUI(volume)
				# else:
				# 	print(f"[VolumeControl] eventUpdatedInfo DEBUG: Audio track unchanged from {isAC3}.")
			else:
				self.updateVolumeControlUI(self.volumeControl.getVolume())

	def getPlayingServiceReference(self):
		serviceReference = self.session.nav.getCurrentlyPlayingServiceReference()
		if serviceReference:
			serviceName = self.getServiceName(serviceReference)
			# print(f"[VolumeControl] getPlayingServiceReference DEBUG: serviceName='{serviceName}' serviceReference='{serviceReference.toString()}'.")
			if serviceReference.getPath().startswith("/"):  # Check if a movie is playing.
				info = eServiceCenter.getInstance().info(serviceReference)  # Get the eServicereference information if available.
				if info:
					serviceReference = eServiceReference(info.getInfoString(serviceReference, iServiceInformation.sServiceref))  # Get eServicereference from meta file. No need to know if eServiceReference is valid.
					serviceName = self.getServiceName(serviceReference)
					# print(f"[VolumeControl] getPlayingServiceReference DEBUG: resolved serviceName='{serviceName}' serviceReference='{serviceReference.toString()}'.")
		return serviceReference, serviceName

	def getServiceName(self, serviceReference):
		return ServiceReference(serviceReference).getServiceName().replace("\xc2\x86", "").replace("\xc2\x87", "") if serviceReference else ""

	def updateVolumeControlUI(self, volume):
		if VolumeControl.instance:
			if VolumeControl.instance.volumeDialog.getVolume() != volume:  # Update volume control progress bar value if the volume has changed.
				VolumeControl.instance.volumeDialog.setValue(volume)
			if self.showVolumeBar and not VolumeControl.instance.isMuted():  # Show volume control if not muted.
				VolumeControl.instance.volumeDialog.show()
				VolumeControl.instance.hideTimer.start(config.volumeControl.hideTimer.value * 1000, True)

	def getVolumeOffsets(self):
		return self.volumeOffsets

	def setVolumeOffsets(self, volumeOffsets):
		self.volumeOffsets = volumeOffsets

	def getVolumeRemembered(self):
		return self.volumeRemembered

	def setVolumeRemembered(self, volumeRemembered):
		self.volumeRemembered = volumeRemembered

	def refreshSettings(self):  # Refresh the cached data when the settings are changed.
		self.adjustMode = config.volumeAdjust.adjustMode.value
		self.defaultOffset = config.volumeAdjust.defaultOffset.value
		self.dolbyEnabled = config.volumeAdjust.dolbyEnabled.value
		self.dolbyOffset = config.volumeAdjust.dolbyOffset.value
		self.mpegMax = config.volumeAdjust.mpegMax.value
		self.showVolumeBar = config.volumeAdjust.showVolumeBar.value


# NOTE: This code does not remember the current volume as other code can change
# 	the volume directly. Always get the current volume from the driver.
#
class VolumeControl:
	"""Volume control, handles volumeUp, volumeDown, volumeMute, and other actions and display a corresponding dialog."""
	instance = None

	def __init__(self, session):
		def updateStep(configElement):
			self.volumeControl.setVolumeSteps(configElement.value)

		if VolumeControl.instance:
			print("[VolumeControl] Error: Only one VolumeControl instance is allowed!")
		else:
			VolumeControl.instance = self
			self.volumeControl = eDVBVolumecontrol.getInstance()
			config.volumeControl = ConfigSubsection()
			config.volumeControl.volume = ConfigInteger(default=20, limits=(0, 100))
			config.volumeControl.mute = ConfigBoolean(default=False)
			config.volumeControl.pressStep = ConfigSelectionNumber(1, 10, 1, default=1)
			config.volumeControl.pressStep.addNotifier(updateStep, initial_call=True, immediate_feedback=True)
			config.volumeControl.longStep = ConfigSelectionNumber(1, 10, 1, default=5)
			config.volumeControl.hideTimer = ConfigSelectionNumber(1, 10, 1, default=3)
			global globalActionMap
			globalActionMap.actions["volumeUp"] = self.keyVolumeUp
			globalActionMap.actions["volumeDown"] = self.keyVolumeDown
			globalActionMap.actions["volumeUpLong"] = self.keyVolumeLong
			globalActionMap.actions["volumeDownLong"] = self.keyVolumeLong
			globalActionMap.actions["volumeUpStop"] = self.keyVolumeStop
			globalActionMap.actions["volumeDownStop"] = self.keyVolumeStop
			globalActionMap.actions["volumeMute"] = self.keyVolumeMute
			globalActionMap.actions["volumeMuteLong"] = self.keyVolumeMuteLong
			print("[VolumeControl] Volume control settings initialized.")
			self.muteDialog = session.instantiateDialog(Mute)
			self.muteDialog.setAnimationMode(0)
			self.volumeDialog = session.instantiateDialog(Volume)
			self.volumeDialog.setAnimationMode(0)
			self.hideTimer = eTimer()
			self.hideTimer.callback.append(self.hideVolume)
			if config.volumeControl.mute.value:
				self.volumeControl.volumeMute()
				self.muteDialog.show()
			volume = config.volumeControl.volume.value
			self.volumeControl.setVolume(volume, volume)
			self.volumeDialog.setValue(volume)
			# Next 2 lines are a compatibility interface for shared plugins.
			self.volctrl = self.volumeControl
			self.hideVolTimer = self.hideTimer
			session.onShutdown.append(self.shutdown)

	def keyVolumeUp(self):
		self.updateVolume(self.volumeControl.volumeUp(0, 0))

	def keyVolumeDown(self):
		self.updateVolume(self.volumeControl.volumeDown(0, 0))

	def keyVolumeLong(self):
		self.volumeControl.setVolumeSteps(config.volumeControl.longStep.value)

	def keyVolumeStop(self):
		self.volumeControl.setVolumeSteps(config.volumeControl.pressStep.value)

	def keyVolumeMute(self):  # This will toggle the current mute status.
		mute = self.volumeControl.volumeToggleMute()
		if mute:
			self.muteDialog.show()
			self.volumeDialog.hide()
		else:
			self.muteDialog.hide()
			self.volumeDialog.setValue(self.volumeControl.getVolume())
			self.volumeDialog.show()
		config.volumeControl.mute.value = mute
		self.hideTimer.start(config.volumeControl.hideTimer.value * 1000, True)

	def keyVolumeMuteLong(self):  # Long press MUTE will keep the mute icon on-screen without a timeout.
		if self.volumeControl.isMuted():
			self.hideTimer.stop()

	def updateVolume(self, volume):
		if self.volumeControl.isMuted():
			self.keyVolumeMute()  # Unmute.
		else:
			self.volumeDialog.setValue(volume)
			self.volumeDialog.show()
			self.hideTimer.start(config.volumeControl.hideTimer.value * 1000, True)

	def hideVolume(self):
		self.muteDialog.hide()
		self.volumeDialog.hide()

	def isMuted(self):
		return self.volumeControl.isMuted()

	def shutdown(self):
		config.volumeControl.volume.setValue(self.volumeControl.getBaseVolume())
		config.volumeControl.save()
		print("[VolumeControl] Volume control settings saved.")

	# These methods are provided for compatibility with shared plugins.
	#
	def volUp(self):
		self.keyVolumeUp()

	def volDown(self):
		self.keyVolumeDown()

	def volMute(self):
		self.keyVolumeMute()

	def volSave(self):
		pass  # Volume (and mute) saving is now done when Enigma2 shuts down.
