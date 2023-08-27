from copy import deepcopy
from os import unlink
from os.path import isfile

from enigma import eDVBVolumecontrol, eServiceReference, iPlayableService, iServiceInformation

from ServiceReference import ServiceReference
from Components.ActionMap import HelpableActionMap
from Components.config import ConfigSelectionNumber, ConfigSubsection, ConfigYesNo, NoSave, config, getConfigListEntry
from Components.ServiceEventTracker import ServiceEventTracker
from Components.Sources.StaticText import StaticText
from Screens.ChannelSelection import ChannelSelectionBase, OFF
from Screens.HelpMenu import HelpableScreen
from Screens.Setup import Setup
from Tools.Directories import SCOPE_CONFIG, fileReadXML, moveFiles, resolveFilename

MODULE_NAME = "VolumeAdjust"
VOLUME_FILE = resolveFilename(SCOPE_CONFIG, "volume.xml")

OFFSET_MIN = -100
OFFSET_MAX = 100
NEW_VALUE = -1000  # NEW_VALUE must not be between OFFSET_MIN and OFFSET_MAX (inclusive).
DEFAULT_VOLUME = 50
DEFAULT_OFFSET = 10

config.volume = ConfigSubsection()
config.volume.defaultOffset = ConfigSelectionNumber(min=OFFSET_MIN, max=OFFSET_MAX, stepwidth=1, default=DEFAULT_OFFSET, wraparound=False)
config.volume.dolbyEnabled = ConfigYesNo(default=False)
config.volume.dolbyOffset = ConfigSelectionNumber(min=OFFSET_MIN, max=OFFSET_MAX, stepwidth=1, default=DEFAULT_OFFSET, wraparound=False)


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
				volumeList.append(getConfigListEntry("  -  %s" % serviceVolumeOffset[0], entry, _("Set the volume offset for the '%s' service.") % serviceVolumeOffset[0]))
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


class SmallChannelSelection(ChannelSelectionBase, HelpableScreen):
	skin = """
	<screen name="SmallChannelSelection" title="Volume Adjust Service Selection" position="center,center" size="560,430">
		<widget name="list" position="0,0" size="e,e-50" scrollbarMode="showOnDemand" />
		<widget name="key_red" position="0,e-40" size="140,40" backgroundColor="key_red" font="Regular;20" foregroundColor="key_text" halign="center" valign="center" />
		<widget name="key_green" position="140,e-40" size="140,40" backgroundColor="key_green" font="Regular;20" foregroundColor="key_text" halign="center" valign="center" />
		<widget name="key_yellow" position="280,e-40" size="140,40" backgroundColor="key_yellow" font="Regular;20" foregroundColor="key_text" halign="center" valign="center" />
		<widget name="key_blue" position="420,e-40" size="140,40" backgroundColor="key_blue" font="Regular;20" foregroundColor="key_text" halign="center" valign="center" />
	</screen>"""

	def __init__(self, session, title):
		ChannelSelectionBase.__init__(self, session)
		HelpableScreen.__init__(self)
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
		self.previousServiceReference = None
		self.previousOffset = 0
		self.eventTracker = ServiceEventTracker(screen=self, eventmap={
			iPlayableService.evUpdatedInfo: self.processVolumeOffset,
		})

	def loadXML(self):  # Load the volume configuration data.
		serviceVolumeOffsets = []
		volumeDom = fileReadXML(VOLUME_FILE, source=MODULE_NAME)
		if volumeDom:
			print("[VolumeAdjust] Loading volume offset data from '%s'." % VOLUME_FILE)
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
			xml.append("\t\t<service name=\"%s\" ref=\"%s\" volume=\"%s\" />" % (serviceVolumeOffset[0], serviceVolumeOffset[1], serviceVolumeOffset[2]))
		xml.append("\t</services>")
		xml.append("</adjustlist>")
		xml.append("")
		try:
			with open(VOLUME_FILE, "w") as fd:
				fd.write("\n".join(xml))
			print("[VolumeAdjust] Saving new volume offset data to '%s'." % VOLUME_FILE)
		except OSError as err:
			print("[VolumeAdjust] Error %d: Unable to save the new volume offset data to '%s'! (%s)" % (err.errno, VOLUME_FILE, err.strerror))
			if isfile(VOLUME_FILE):
				unlink(VOLUME_FILE)  # Remove the file as it is probably invalid or incomplete.

	def getNormalVolume(self):
		return self.normalVolume or DEFAULT_VOLUME

	def processVolumeOffset(self):  # This is the routine to change the volume offset.
		serviceRef = self.session.nav.getCurrentlyPlayingServiceReference()
		if serviceRef:
			serviceReference = serviceRef.toCompareString()
			if serviceReference != self.previousServiceReference:  # Check if the service has changed.
				self.previousServiceReference = serviceReference
				index = self.findCurrentService(serviceReference)
				name, ref, offset = [ServiceReference(serviceRef).getServiceName().replace("\xc2\x87", "").replace("\xc2\x86", ""), serviceReference, 0] if index == -1 else self.serviceVolumeOffsets[index]
				serviceVolume = self.volumeControl.getVolume()
				if self.previousOffset:
					self.normalVolume = serviceVolume - self.previousOffset
					print("[VolumeAdjust] Volume offset of %d is currently in effect.  Normal volume is %d." % (self.previousOffset, self.normalVolume))
				else:
					self.normalVolume = serviceVolume
					print("[VolumeAdjust] Normal volume is %d." % self.normalVolume)
				if index == -1:  # Service not found, check if Dolby Digital volume needs to be offset.
					if config.volume.dolbyEnabled.value and self.isCurrentAudioAC3DTS():
						offset = config.volume.dolbyOffset.value
						newVolume = self.normalVolume + offset
						if serviceVolume != newVolume:
							self.volumeControl.setVolume(newVolume, newVolume)
							print("[VolumeAdjust] New volume of %d, including an offset of %d, set for Dolby Digital / Dolby AC-3 service '%s'." % (newVolume, offset, name))
					elif serviceVolume != self.normalVolume:
						self.volumeControl.setVolume(self.normalVolume, self.normalVolume)
						print("[VolumeAdjust] Normal volume of %d restored for service '%s'." % (self.normalVolume, name))
				else:  # Service found in serviceVolumeOffsets list, use volume offset to change the volume.
					newVolume = self.normalVolume + offset
					if serviceVolume != newVolume:
						self.volumeControl.setVolume(newVolume, newVolume)
						print("[VolumeAdjust] New volume of %d, including an offset of %d, set for service '%s'." % (newVolume, offset, name))
				self.previousOffset = offset

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
				print("[VolumeAdjust] Description: '%s'." % description)
				if "AC3" in description or "DTS" in description or "Dolby Digital" == description:
					print("[VolumeAdjust] AudioAC3Dolby = YES")
					return True
			except Exception:
				print("[VolumeAdjust] Exception: AudioAC3Dolby = NO")
				return False
		print("[VolumeAdjust] AudioAC3Dolby = NO")
		return False


VolumeInstance = None


def autostart(session):
	oldFile = "/etc/volume.xml"  # This code is for old versions of "volume.xml".  This can be removed after a reasonable period for users to update.
	if isfile(oldFile):
		if isfile(VOLUME_FILE):
			unlink(oldFile)
			print("[VolumeAdjust] Update Note: Both '%s' and '%s' exist.  Old version '%s' deleted!" % (oldFile, VOLUME_FILE, oldFile))
		else:
			moveFiles(((oldFile, VOLUME_FILE),))
			print("[VolumeAdjust] Update Note: Moving '%s' to '%s'!" % (oldFile, VOLUME_FILE))
	global VolumeInstance
	if VolumeInstance is None:
		VolumeInstance = Volume(session)
