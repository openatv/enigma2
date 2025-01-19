from copy import deepcopy
from os import unlink
from os.path import isfile, exists
from pickle import dump, load

from enigma import eDVBVolumecontrol, eEnv, eServiceReference, eServiceCenter, iPlayableService, iServiceInformation

from ServiceReference import ServiceReference
from Components.ActionMap import HelpableActionMap
from Components.config import ConfigSelection, ConfigSelectionNumber, ConfigSubsection, ConfigYesNo, NoSave, config, getConfigListEntry
from Components.ServiceEventTracker import ServiceEventTracker
from Components.Sources.StaticText import StaticText
from Screens.ChannelSelection import ChannelSelectionBase, OFF
from Screens.Setup import Setup
from Tools.Directories import SCOPE_CONFIG, fileReadXML, moveFiles, resolveFilename

MODULE_NAME = "VolumeAdjust"
VOLUME_FILE = resolveFilename(SCOPE_CONFIG, "volume.xml")
SERVICE_VOLUME_FILE = resolveFilename(SCOPE_CONFIG, "ava_volume.cfg")

OFFSET_MIN = -100
OFFSET_MAX = 100
NEW_VALUE = -1000  # NEW_VALUE must not be between OFFSET_MIN and OFFSET_MAX (inclusive).
DEFAULT_VOLUME = 50
DEFAULT_OFFSET = 10

config.volume = ConfigSubsection()
config.volume.defaultOffset = ConfigSelectionNumber(min=OFFSET_MIN, max=OFFSET_MAX, stepwidth=1, default=DEFAULT_OFFSET, wraparound=False)
config.volume.dolbyEnabled = ConfigYesNo(default=False)
config.volume.dolbyOffset = ConfigSelectionNumber(min=OFFSET_MIN, max=OFFSET_MAX, stepwidth=1, default=DEFAULT_OFFSET, wraparound=False)
config.volume.adjustMode = ConfigSelection(choices=[(0, _("Disabled")), (1, _("Defined")), (2, _("Remember"))], default=0)
config.volume.mpegMax = ConfigSelectionNumber(10, 100, 5, default=100)
config.volume.showVolumeBar = ConfigYesNo(default=False)


class VolumeAdjust(Setup):
	def __init__(self, session):
		self.serviceVolumeOffsets = VolumeInstance.getServiceVolumeOffsets()
		self.initialVolumeOffsets = deepcopy(self.serviceVolumeOffsets)
		Setup.__init__(self, session, setup="VolumeAdjust")
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText("")
		self["addServiceActions"] = HelpableActionMap(self, ["VolumeAdjustActions"], {
			"addService": (self.addService, _("Add a service to the Volume Offsets list"))
		}, prio=0, description=_("Volume Adjust Actions"))
		self["addCurrentActions"] = HelpableActionMap(self, ["VolumeAdjustActions"], {
			"addCurrentService": (self.addCurrentService, _("Add the current service to the Volume Offsets list"))
		}, prio=0, description=_("Volume Adjust Actions"))
		self["addCurrentActions"].setEnabled(False)
		self["deleteActions"] = HelpableActionMap(self, ["VolumeAdjustActions"], {
			"deleteService": (self.deleteService, _("Delete the currently highlighted service from the Volume Offsets list"))
		}, prio=0, description=_("Volume Adjust Actions"))
		self["deleteActions"].setEnabled(False)
		serviceRef = self.session.nav.getCurrentlyPlayingServiceReference()
		if serviceRef:
			self.serviceName = ServiceReference(serviceRef).getServiceName().replace("\xc2\x87", "").replace("\xc2\x86", "")
			self.serviceReference = serviceRef.toCompareString()
		else:
			self.serviceName = None
			self.serviceReference = None
		self.volumeControl = eDVBVolumecontrol.getInstance()
		self.serviceVolume = self.volumeControl.getVolume()
		self.normalVolume = VolumeInstance.getNormalVolume()

	def createSetup(self):  # NOSONAR silence S2638
		self.list = []
		Setup.createSetup(self)
		volumeList = self["config"].getList()
		self.volumeStart = len(volumeList)
		if self.serviceVolumeOffsets:
			volumeList.append(getConfigListEntry(_("Currently Defined Volume Offsets:")))
			for serviceVolumeOffset in self.serviceVolumeOffsets:
				default = config.volume.defaultOffset.value if serviceVolumeOffset[2] == NEW_VALUE else serviceVolumeOffset[2]
				entry = NoSave(ConfigSelectionNumber(min=OFFSET_MIN, max=OFFSET_MAX, stepwidth=1, default=default, wraparound=False))
				if serviceVolumeOffset[2] == NEW_VALUE:
					serviceVolumeOffset[2] = config.volume.defaultOffset.value
					entry.default = NEW_VALUE  # This triggers a cancel confirmation for unedited new entries.
				volumeList.append(getConfigListEntry(f"  -  {serviceVolumeOffset[0]}", entry, _("Set the volume offset for the '%s' service.") % serviceVolumeOffset[0]))
		self["config"].setList(volumeList)

	def selectionChanged(self):
		Setup.selectionChanged(self)
		if self.findCurrentService(self.serviceName, self.serviceReference) == -1:
			self["addCurrentActions"].setEnabled(True)
			self["key_yellow"].setText(_("Add Current"))
		else:
			self["addCurrentActions"].setEnabled(False)
			self["key_yellow"].setText("")
		if self["config"].getCurrentIndex() > self.volumeStart:
			self["deleteActions"].setEnabled(True)
			self["key_blue"].setText(_("Delete"))
		else:
			self["deleteActions"].setEnabled(False)
			self["key_blue"].setText("")

	def changedEntry(self):  # Override the Setup method that calls createSetup() when a ConfigBoolean or ConfigSelection based class is changed!
		index = self["config"].getCurrentIndex() - self.volumeStart - 1
		if index > -1:
			value = self["config"].getCurrent()[1].value
			self.serviceVolumeOffsets[index][2] = value
			if self.serviceVolumeOffsets[index][1] == self.serviceReference:  # Apply the offset if we are setting an offset for the current service.
				volume = self.normalVolume + value
				self.volumeControl.setVolume(volume, volume)  # Volume left, volume right.

	def keySave(self):
		if self.serviceVolumeOffsets != self.initialVolumeOffsets:  # Save the volume configuration data if there are any changes.
			VolumeInstance.setServiceVolumeOffsets(self.serviceVolumeOffsets)
		VolumeInstance.refreshSettings()
		Setup.keySave(self)

	def cancelConfirm(self, result):
		if not result:
			return
		VolumeInstance.setServiceVolumeOffsets(self.initialVolumeOffsets)
		if self.volumeControl.getVolume() != self.serviceVolume:  # Reset the offset if we were setting an offset for the current service.
			self.volumeControl.setVolume(self.serviceVolume, self.serviceVolume)  # Volume left, volume right.
		Setup.cancelConfirm(self, result)

	def addService(self):
		self.session.openWithCallback(self.addServiceCallback, SmallChannelSelection, None)

	def addServiceCallback(self, serviceReference):
		if serviceReference:
			serviceName = ServiceReference(serviceReference).getServiceName().replace("\xc2\x87", "").replace("\xc2\x86", "")
			serviceReference = serviceReference.toCompareString()
			if self.findCurrentService(serviceName, serviceReference) == -1:
				self.serviceVolumeOffsets.append([serviceName, serviceReference, NEW_VALUE])
				self.createSetup()
				self["config"].setCurrentIndex(self.volumeStart + len(self.serviceVolumeOffsets))
				self.setFootnote(_("Service '%s' added.") % serviceName)
			else:
				self.setFootnote(_("Service '%s' is already defined.") % serviceName)
		else:
			self.setFootnote(_("Service selection canceled."))

	def addCurrentService(self):
		self.serviceVolumeOffsets.append([self.serviceName, self.serviceReference, NEW_VALUE])
		self.createSetup()
		self["config"].setCurrentIndex(self.volumeStart + len(self.serviceVolumeOffsets))
		self.setFootnote(_("Service '%s' added.") % self.serviceName)

	def deleteService(self):
		index = self["config"].getCurrentIndex()
		name, ref, offset = self.serviceVolumeOffsets.pop(index - self.volumeStart - 1)
		self.createSetup()
		configLength = len(self["config"].getList())
		if index >= configLength:
			index = configLength - 1
		self["config"].setCurrentIndex(index)
		self.setFootnote(_("Service '%s' deleted.") % name)

	def findCurrentService(self, serviceName, serviceReference):
		for index, (name, ref, offset) in enumerate(self.serviceVolumeOffsets):
			if name == serviceName and ref == serviceReference:
				return index
		return -1


class SmallChannelSelection(ChannelSelectionBase):
	skin = """
	<screen name="SmallChannelSelection" title="Volume Adjust Service Selection" position="center,center" size="560,430" resolution="1280,720">
		<widget name="list" position="0,0" size="e,e-50" scrollbarMode="showOnDemand" />
		<widget name="key_red" position="0,e-40" size="140,40" backgroundColor="key_red" font="Regular;20" foregroundColor="key_text" halign="center" valign="center" />
		<widget name="key_green" position="140,e-40" size="140,40" backgroundColor="key_green" font="Regular;20" foregroundColor="key_text" halign="center" valign="center" />
		<widget name="key_yellow" position="280,e-40" size="140,40" backgroundColor="key_yellow" font="Regular;20" foregroundColor="key_text" halign="center" valign="center" />
		<widget name="key_blue" position="420,e-40" size="140,40" backgroundColor="key_blue" font="Regular;20" foregroundColor="key_text" halign="center" valign="center" />
	</screen>"""

	def __init__(self, session, title):
		ChannelSelectionBase.__init__(self, session)
		self.skinName = ["SmallChannelSelection", "mySmallChannelSelection"]  # The screen "mySmallChannelSelection" is for legacy support only.
		self.setTitle(_("Volume Adjust Service Selection"))
		self.onShown.append(self.__onExecCallback)
		self.bouquet_mark_edit = OFF
		service = self.session.nav.getCurrentService()
		if service:
			info = service.info()
			if info:
				refstr = info.getInfoString(iServiceInformation.sServiceref)
				self.servicelist.setPlayableIgnoreService(eServiceReference(refstr))
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "TvRadioActions"], {
			"cancel": (self.cancel, _("Cancel the service selection")),
			"ok": (self.channelSelected, _("Select the currently highlighted service")),
			"keyTV": (self.setModeTv, _("Switch to the available TV services")),
			"keyRadio": (self.setModeRadio, _("Switch to the available RADIO services"))
		}, prio=0, description=_("Service Selection Actions"))

	def __onExecCallback(self):
		self.setModeTv()

	def channelSelected(self):
		ref = self.getCurrentSelection()
		if (ref.flags & 7) == 7:
			self.enterPath(ref)
		elif not (ref.flags & eServiceReference.isMarker):
			ref = self.getCurrentSelection()
			self.close(ref)

	def setModeTv(self):
		self.setTvMode()
		self.showFavourites()

	def setModeRadio(self):
		self.setRadioMode()
		self.showFavourites()

	def cancel(self):
		self.close(None)


class Volume:
	def __init__(self, session):  # Autostart instance, comes active when info is updated (zap).
		self.session = session
		self.onClose = []
		self.serviceVolumeOffsets = self.loadXML()  # Load the volume configuration data.
		self.volumeControl = eDVBVolumecontrol.getInstance()
		self.normalVolume = None
		self.lastAdjustedValue = 0  # Remember delta from last automatic volume up/down
		self.currentVolume = 0  # Only set when AC3 or DTS is available
		self.newService = [False, None]
		self.pluginStarted = False
		self.eventTracker = ServiceEventTracker(screen=self, eventmap={
				iPlayableService.evUpdatedInfo: self.processVolumeOffset,
				iPlayableService.evStart: self.eventStart,
				iPlayableService.evEnd: self.eventEnd
			})

		self.serviceList = {}
		self.adjustMode = config.volume.adjustMode.value
		self.mpegMax = config.volume.mpegMax.value
		self.dolbyEnabled = config.volume.dolbyEnabled.value
		self.defaultOffset = config.volume.defaultOffset.value
		if self.adjustMode == 1:  # Automatic volume adjust mode
			for name, ref, offset in self.serviceVolumeOffsets:
				self.serviceList[ref] = offset
		else:  # Remember channel volume mode
			if exists(SERVICE_VOLUME_FILE):
				with open(SERVICE_VOLUME_FILE, "rb") as fd:
					self.serviceList = load(fd)

	def refreshSettings(self):
		self.defaultOffset = config.volume.defaultOffset.value
		self.adjustMode = config.volume.adjustMode.value
		self.mpegMax = config.volume.mpegMax.value
		self.dolbyEnabled = config.volume.dolbyEnabled.value

	def eventStart(self):
		self.newService = [True, None]

	def eventEnd(self):
		if self.adjustMode == 1:  # Automatic volume adjust mode
			# if played service had AC3||DTS audio and volume value was changed with RC, take new delta value from the config
			if self.currentVolume and self.volumeControl.getVolume() != self.currentVolume:
				self.lastAdjustedValue = self.newService[1] and self.serviceList.get(self.newService[1].toString(), self.defaultOffset) or self.defaultOffset
		elif self.adjustMode == 2:  # Remember channel volume mode
			ref = self.newService[1]
			if ref and ref.valid():
				self.serviceList[ref.toString()] = self.volumeControl.getVolume()
		self.newService = [False, None]

	def loadXML(self):  # Load the volume configuration data.
		serviceVolumeOffsets = []
		volumeDom = fileReadXML(VOLUME_FILE, source=MODULE_NAME)
		if volumeDom is not None:
			print(f"[VolumeAdjust] Loading volume offset data from '{VOLUME_FILE}'.")
			for services in volumeDom.findall("services"):
				for service in services.findall("service"):
					serviceName = service.get("name")
					serviceReference = service.get("ref")
					serviceVolumeOffset = int(service.get("volume", "0"))
					if serviceName and serviceReference:
						serviceVolumeOffsets.append([serviceName, serviceReference, serviceVolumeOffset])
			for channels in volumeDom.findall("channels"):  # This code is for old versions of "volume.xml".  This can be removed after a reasonable period for users to update.
				for service in channels.findall("service"):
					serviceName = service.get("name")
					serviceReference = service.get("ref")
					serviceVolumeOffset = int(service.get("volume", "0"))
					if serviceName and serviceReference:
						serviceVolumeOffsets.append([serviceName, serviceReference, serviceVolumeOffset])
		return serviceVolumeOffsets

	def getServiceVolumeOffsets(self):
		return self.serviceVolumeOffsets

	def setServiceVolumeOffsets(self, serviceVolumeOffsets):
		self.serviceVolumeOffsets = serviceVolumeOffsets
		xml = []
		xml.append("<?xml version=\"1.0\" encoding=\"utf-8\" ?>")
		xml.append("<adjustlist>")
		xml.append("\t<services>")
		for serviceVolumeOffset in self.serviceVolumeOffsets:
			xml.append(f"\t\t<service name=\"{serviceVolumeOffset[0]}\" ref=\"{serviceVolumeOffset[1]}\" volume=\"{serviceVolumeOffset[2]}\" />")
		xml.append("\t</services>")
		xml.append("</adjustlist>")
		xml.append("")
		try:
			with open(VOLUME_FILE, "w") as fd:
				fd.write("\n".join(xml))
			print(f"[VolumeAdjust] Saving new volume offset data to '{VOLUME_FILE}'.")
		except OSError as err:
			print(f"[VolumeAdjust] Error {err.errno}: Unable to save the new volume offset data to '{VOLUME_FILE}'!  ({err.strerror})")
			if isfile(VOLUME_FILE):
				unlink(VOLUME_FILE)  # Remove the file as it is probably invalid or incomplete.

	def getNormalVolume(self):
		return self.normalVolume or DEFAULT_VOLUME

	def processVolumeOffset(self):  # This is the routine to change the volume offset.
		# taken from the plugin !!!!
		if self.adjustMode and self.newService[0]:
			serviceRef = self.session.nav.getCurrentlyPlayingServiceReference()
			if serviceRef:
				print("[VolumeAdjustment] service changed")
				self.newService = [False, serviceRef]
				self.currentVolume = 0  # init
				if self.adjustMode == 1:  # Automatic volume adjust mode
					self.currentAC3DTS = self.isCurrentAudioAC3DTS()
					if self.pluginStarted:
						if self.currentAC3DTS:  # ac3 dts?
							ref = self.getPlayingServiceReference()
							vol = self.volumeControl.getVolume()
							currentvol = vol  # remember current vol
							vol -= self.lastAdjustedValue  # go back to origin value first
							ajvol = self.serviceList.get(ref.toString(), self.defaultOffset)  # get delta from config
							if ajvol < 0:  # adjust vol down
								if vol + ajvol < 0:
									ajvol = (-1) * vol
							else:  # adjust vol up
								if vol >= 100 - ajvol:  # check if delta + vol < 100
									ajvol = 100 - vol  # correct delta value
							self.lastAdjustedValue = ajvol  # save delta value
							if (vol + ajvol != currentvol):
								if ajvol == 0:
									ajvol = vol - currentvol  # correction for debug -print(only)
								self.setVolume(vol + self.lastAdjustedValue)
								print(f"[VolumeAdjustment] Change volume for service: '{self.getServiceName(ref)}' (+{ajvol}) to {self.volumeControl.getVolume()}")
							self.currentVolume = self.volumeControl.getVolume()  # ac3||dts service , save current volume
						else:
							# mpeg or whatever audio
							if self.lastAdjustedValue != 0:
								# go back to origin value
								vol = self.volumeControl.getVolume()
								ajvol = vol - self.lastAdjustedValue
								if ajvol > self.mpegMax:
									ajvol = self.mpegMax
								self.setVolume(ajvol)
								print(f"[VolumeAdjustment] Change volume for service: '{self.getServiceName(self.session.nav.getCurrentlyPlayingServiceReference())}' (-{vol - ajvol}) to {self.volumeControl.getVolume()}")
								self.lastAdjustedValue = 0  # mpeg audio, no delta here
						return  # get out of here, nothing to do anymore
				elif self.adjustMode == 2:  # modus = Remember channel volume
					if self.pluginStarted:
						ref = self.getPlayingServiceReference()
						if ref.valid():
							# get value from dict
							lastvol = self.serviceList.get(ref.toString(), -1)
							if lastvol != -1 and lastvol != self.volumeControl.getVolume():
								# set volume value
								self.setVolume(lastvol)
								print(f"[VolumeAdjustment] Set last used volume value for service '{self.getServiceName(ref)}' to {self.volumeControl.getVolume()}")
						return  # get out of here, nothing to do anymore

			if not self.pluginStarted:
				if self.adjustMode == 1:  # Automatic volume adjust mode
					# starting plugin, if service audio is ac3 or dts --> get delta from config...volume value is set by enigma2-system at start
					if self.currentAC3DTS:
						self.lastAdjustedValue = self.serviceList.get(self.session.nav.getCurrentlyPlayingServiceReference().toString(), self.defaultOffset)
						self.currentVolume = self.volumeControl.getVolume()  # ac3||dts service , save current volume
				self.pluginStarted = True  # plugin started...

	def getServiceName(self, ref):
		return ServiceReference(ref).getServiceName().replace("\xc2\x86", "").replace("\xc2\x87", "") if ref else ""

	def findCurrentService(self, serviceReference):
		for index, (name, ref, offset) in enumerate(self.serviceVolumeOffsets):
			if ref == serviceReference:
				return index
		return -1

	def isCurrentAudioAC3DTS(self):
		service = self.session.nav.getCurrentService()
		audio = service.audioTracks()
		if audio:
			try:  # Uhh, servicemp3 leads sometimes to OverflowError Error.
				description = audio.getTrackInfo(audio.getCurrentTrack()).getDescription()
				print(f"[VolumeAdjust] Description: '{description}'.")
				if self.dolbyEnabled:
					if "AC3" in description or "DTS" in description or "Dolby Digital" == description:
						print("[VolumeAdjust] AudioAC3Dolby = YES")
						return True
					else:
						if description and description.split()[0] in ("AC3", "AC-3", "A_AC3", "A_AC-3", "A-AC-3", "E-AC-3", "A_EAC3", "DTS", "DTS-HD", "AC4", "AAC-HE"):
							print("[VolumeAdjust] AudioAC3Dolby = YES")
							return True
			except Exception:
				print("[VolumeAdjust] Exception: AudioAC3Dolby = NO")
				return False
		print("[VolumeAdjust] AudioAC3Dolby = NO")
		return False

	def getPlayingServiceReference(self):
		ref = self.session.nav.getCurrentlyPlayingServiceReference()
		if ref:
			refstr = ref.toString()
			if "%3a//" not in refstr and refstr.rsplit(":", 1)[1].startswith("/"):  # check if a movie is playing
				# it is , get the eServicereference if available
				self.serviceHandler = eServiceCenter.getInstance()
				info = self.serviceHandler.info(ref)
				if info:
					# no need here to know if eServiceReference is valid...
					ref = eServiceReference(info.getInfoString(ref, iServiceInformation.sServiceref))  # get new eServicereference from meta file
		return ref

	def setVolume(self, value):
		self.volumeControl.setVolume(value, value)  # Set new volume
		if self.volumeControlInstance is not None:
			self.volumeControlInstance.volumeDialog.setValue(value)  # Update progressbar value
			if config.volume.showVolumeBar.value:
				self.volumeControlInstance.volumeDialog.show()
				self.volumeControlInstance.hideVolTimer.start(3000, True)
		config.volumeControl.volume.value = self.volumeControl.getVolume()
		config.volumeControl.volume.save()


VolumeInstance = None


def shutdown():
	if VolumeInstance:
		with open(SERVICE_VOLUME_FILE, "wb") as fd:
			dump(VolumeInstance.serviceList, fd)


def autostart(session):
	oldFile = "/etc/volume.xml"  # This code is for old versions of "volume.xml".  This can be removed after a reasonable period for users to update.
	if isfile(oldFile):
		if isfile(VOLUME_FILE):
			unlink(oldFile)
			print(f"[VolumeAdjust] Update Note: Both '{oldFile}' and '{VOLUME_FILE}' exist.  Old version '{oldFile}' deleted!")
		else:
			moveFiles(((oldFile, VOLUME_FILE),))
			print(f"[VolumeAdjust] Update Note: Moving '{oldFile}' to '{VOLUME_FILE}'!")
	global VolumeInstance
	if VolumeInstance is None:
		VolumeInstance = Volume(session)
