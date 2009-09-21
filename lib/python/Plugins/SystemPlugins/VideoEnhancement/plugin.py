from Plugins.Plugin import PluginDescriptor
from Components.ConfigList import ConfigListScreen
from Components.config import getConfigListEntry, config, ConfigBoolean
from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.Label import Label
from Screens.Screen import Screen
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from enigma import ePoint
from Tools import Notifications
from Tools.HardwareInfo import HardwareInfo
from VideoEnhancement import video_enhancement
import os

class VideoEnhancementSetup(Screen, ConfigListScreen):

	skin = """
		<screen name="VideoEnhancementSetup" position="center,center" size="560,430" title="VideoEnhancementSetup">
		<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" alphatest="on" />
		<widget name="key_red" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		<widget name="key_green" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		<widget name="key_yellow" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
		<widget name="key_blue" position="420,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" />
		<widget name="config" position="5,50" size="550,340" scrollbarMode="showOnDemand" />
		<ePixmap pixmap="skin_default/div-h.png" position="0,390" zPosition="1" size="560,2" />
		<widget name="introduction" position="5,400" size="550,25" zPosition="10" font="Regular;21" halign="center" valign="center" backgroundColor="#25062748" transparent="1" />

	</screen>"""

	def __init__(self, session, hw):
		Screen.__init__(self, session)

		self.session = session
		self.hw = hw
		self.onChangedEntry = [ ]
		self.setup_title = "Videoenhancement"

		self.contrastEntry = None
		self.saturationEntry = None
		self.hueEntry = None
		self.brightnessEntry = None
		self.splitEntry = None
		self.sharpnessEntry = None
		self.auto_fleshEntry = None
		self.green_boostEntry = None
		self.blue_boostEntry = None
		self.block_noise_reductionEntry = None
		self.mosquito_noise_reductionEntry = None
		self.digital_contour_removalEntry = None
		self.dynamic_contrastEntry = None

		# handle hotplug by re-creating setup
		self.onShow.append(self.startHotplug)
		self.onHide.append(self.stopHotplug)

		self.list = [ ]
		self.xtdlist = [ ]
		self.hw_type = HardwareInfo().get_device_name()
		ConfigListScreen.__init__(self, self.list, session = self.session, on_change = self.changedEntry)

		self["actions"] = ActionMap(["SetupActions", "ColorActions"],
			{
				"cancel": self.keyCancel,
				"save": self.apply,
				"yellow": self.keyYellow,
				"blue": self.keyBlue,
			}, -2)

		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("OK"))
		self["key_yellow"] = Button(_("Last config"))
		self["key_blue"] = Button(_("Default"))
		self["introduction"] = Label()

		self.createSetup()
		self.rememberOldSettings()
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(_("Video enhancement setup"))

	def startHotplug(self):
		self.hw.on_hotplug.append(self.createSetup)

	def stopHotplug(self):
		self.hw.on_hotplug.remove(self.createSetup)

	def rememberOldSettings(self):
		self.oldContrast = config.pep.contrast.value
		self.oldSaturation = config.pep.saturation.value
		self.oldHue = config.pep.hue.value
		self.oldBrightness = config.pep.brightness.value
		if self.hw_type == 'dm8000':
			self.oldSplit = config.pep.split.value
			self.oldSharpness = config.pep.sharpness.value
			self.oldAuto_flesh = config.pep.auto_flesh.value
			self.oldGreen_boost = config.pep.green_boost.value
			self.oldBlue_boost = config.pep.blue_boost.value
			self.oldBlock_noise = config.pep.block_noise_reduction.value
			self.oldMosquito_noise = config.pep.mosquito_noise_reduction.value
			self.oldDigital_contour = config.pep.digital_contour_removal.value
			self.oldDynamic_contrast = config.pep.dynamic_contrast.value

	def createSetup(self):
		self.contrastEntry = getConfigListEntry(_("Contrast"), config.pep.contrast)
		self.saturationEntry = getConfigListEntry(_("Saturation"), config.pep.saturation)
		self.hueEntry = getConfigListEntry(_("Hue"), config.pep.hue)
		self.brightnessEntry = getConfigListEntry(_("Brightness"), config.pep.brightness)

		self.list = [
			self.contrastEntry
		]

		self.list.extend((
			self.saturationEntry,
			self.hueEntry,
			self.brightnessEntry
		))
		if self.hw_type == 'dm8000':
			self.splitEntry = getConfigListEntry(_("Split preview mode"), config.pep.split)
			self.sharpnessEntry = getConfigListEntry(_("Sharpness"), config.pep.sharpness)
			self.auto_fleshEntry = getConfigListEntry(_("Auto flesh"), config.pep.auto_flesh)
			self.green_boostEntry = getConfigListEntry(_("Green boost"), config.pep.green_boost)
			self.blue_boostEntry = getConfigListEntry(_("Blue boost"), config.pep.blue_boost)
			self.block_noise_reductionEntry = getConfigListEntry(_("Block noise reduction"), config.pep.block_noise_reduction)
			self.mosquito_noise_reductionEntry = getConfigListEntry(_("Mosquito noise reduction"), config.pep.mosquito_noise_reduction)
			self.digital_contour_removalEntry = getConfigListEntry(_("Digital contour removal"), config.pep.digital_contour_removal)
			self.dynamic_contrastEntry = getConfigListEntry(_("Dynamic contrast"), config.pep.dynamic_contrast)

			self.xtdlist = [
				self.splitEntry
			]

			self.xtdlist.extend((
				self.sharpnessEntry,
				self.auto_fleshEntry,
				self.green_boostEntry,
				self.blue_boostEntry,
				self.block_noise_reductionEntry,
				self.mosquito_noise_reductionEntry,
				self.digital_contour_removalEntry,
				self.dynamic_contrastEntry
			))

			self.list.extend((
				self.splitEntry,
				self.sharpnessEntry,
				self.auto_fleshEntry,
				self.green_boostEntry,
				self.blue_boostEntry,
				self.block_noise_reductionEntry,
				self.mosquito_noise_reductionEntry,
				self.digital_contour_removalEntry,
				self.dynamic_contrastEntry
			))

		self["config"].list = self.list
		self["config"].l.setSeperation(300)
		self["config"].l.setList(self.list)
		if not self.selectionChanged in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def selectionChanged(self):
		self["introduction"].setText(_("Current value: ") + self.getCurrentValue())

	def PreviewClosed(self):
		self["config"].invalidate(self["config"].getCurrent())
		self.createSetup()

	def keyLeft(self):
		current = self["config"].getCurrent()
		if current == self.splitEntry:
			ConfigListScreen.keyLeft(self)
			self.createSetup()
		elif current != self.splitEntry and current in self.xtdlist:
			self.previewlist = [
				current,
				self.splitEntry
			]
			self.session.openWithCallback(self.PreviewClosed, VideoEnhancementPreview, configEntry = self.previewlist, oldSplitMode = config.pep.split.value)
		else:
			self.previewlist = [
				current
			]
			self.session.openWithCallback(self.PreviewClosed, VideoEnhancementPreview, configEntry = self.previewlist)

	def keyRight(self):
		current = self["config"].getCurrent()
		if current == self.splitEntry:
			ConfigListScreen.keyRight(self)
			self.createSetup()
		elif current != self.splitEntry and current in self.xtdlist:
			self.previewlist = [
				current,
				self.splitEntry
			]
			self.session.openWithCallback(self.PreviewClosed, VideoEnhancementPreview, configEntry = self.previewlist, oldSplitMode = config.pep.split.value )
		else:
			self.previewlist = [
				current
			]
			self.session.openWithCallback(self.PreviewClosed, VideoEnhancementPreview, configEntry = self.previewlist)

	def confirm(self, confirmed):
		if not confirmed:
			print "not confirmed"
		else:
			if self.splitEntry is not None:
				config.pep.split.setValue('off')
			self.keySave()

	def apply(self):
		self.session.openWithCallback(self.confirm, MessageBox, _("Use this video enhancement settings?"), MessageBox.TYPE_YESNO, timeout = 20, default = False)

	def cancelConfirm(self, result):
		if not result:
			return
		self.keyYellowConfirm(True)
		self.close()

	def keyCancel(self):
		if self["config"].isChanged():
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"))
		else:
			self.close()

	def keyYellowConfirm(self, confirmed):
		if not confirmed:
			print "not confirmed"
		else:
			if self.contrastEntry is not None:
				config.pep.contrast.setValue(self.oldContrast)
			if self.saturationEntry is not None:
				config.pep.saturation.setValue(self.oldSaturation)
			if self.hueEntry is not None:
				config.pep.hue.setValue(self.oldHue)
			if self.brightnessEntry is not None:
				config.pep.brightness.setValue(self.oldBrightness)

			if self.hw_type == 'dm8000':
				if self.splitEntry is not None:
					config.pep.split.setValue('off')
				if self.sharpnessEntry is not None:
					config.pep.sharpness.setValue(self.oldSharpness)
				if self.auto_fleshEntry is not None:
					config.pep.auto_flesh.setValue(self.oldAuto_flesh)
				if self.green_boostEntry is not None:
					config.pep.green_boost.setValue(self.oldGreen_boost)
				if self.blue_boostEntry is not None:
					config.pep.blue_boost.setValue(self.oldBlue_boost)
				if self.block_noise_reductionEntry is not None:
					config.pep.block_noise_reduction.setValue(self.oldBlock_noise)
				if self.mosquito_noise_reductionEntry is not None:
					config.pep.mosquito_noise_reduction.setValue(self.oldMosquito_noise)
				if self.digital_contour_removalEntry is not None:
					config.pep.digital_contour_removal.setValue(self.oldDigital_contour)
				if self.dynamic_contrastEntry is not None:
					config.pep.dynamic_contrast.setValue(self.oldDynamic_contrast)
			self.keySave()

	def keyYellow(self):
		self.session.openWithCallback(self.keyYellowConfirm, MessageBox, _("Reset video enhancement settings to your last configuration?"), MessageBox.TYPE_YESNO, timeout = 20, default = False)

	def keyBlueConfirm(self, confirmed):
		if not confirmed:
			print "not confirmed"
		else:
			if self.contrastEntry is not None:
				config.pep.contrast.setValue(128)
			if self.saturationEntry is not None:
				config.pep.saturation.setValue(128)
			if self.hueEntry is not None:
				config.pep.hue.setValue(128)
			if self.brightnessEntry is not None:
				config.pep.brightness.setValue(128)

			if self.hw_type == 'dm8000':
				if self.splitEntry is not None:
					config.pep.split.setValue('off')
				if self.sharpnessEntry is not None:
					config.pep.sharpness.setValue(0)
				if self.auto_fleshEntry is not None:
					config.pep.auto_flesh.setValue(0)
				if self.green_boostEntry is not None:
					config.pep.green_boost.setValue(0)
				if self.blue_boostEntry is not None:
					config.pep.blue_boost.setValue(0)
				if self.block_noise_reductionEntry is not None:
					config.pep.block_noise_reduction.setValue(0)
				if self.mosquito_noise_reductionEntry is not None:
					config.pep.mosquito_noise_reduction.setValue(0)
				if self.digital_contour_removalEntry is not None:
					config.pep.digital_contour_removal.setValue(0)
				if self.dynamic_contrastEntry is not None:
					config.pep.dynamic_contrast.setValue(0)
			self.keySave()

	def keyBlue(self):
		self.session.openWithCallback(self.keyBlueConfirm, MessageBox, _("Reset video enhancement settings to system defaults?"), MessageBox.TYPE_YESNO, timeout = 20, default = False)

	# for summary:
	def changedEntry(self):
		for x in self.onChangedEntry:
			x()

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())

	def createSummary(self):
		from Screens.Setup import SetupSummary
		return SetupSummary


class VideoEnhancementPreview(Screen, ConfigListScreen):

	skin = """
		<screen name="VideoEnhancementPreview" position="90,430" size="560,110" title="VideoEnhancementPreview">
		<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
		<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
		<widget name="key_red" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		<widget name="key_green" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		<widget name="config" position="5,50" size="550,60" scrollbarMode="showOnDemand" />
	</screen>"""

	def __init__(self, session, configEntry = None, oldSplitMode = None):
		Screen.__init__(self, session)

		self.onChangedEntry = [ ]
		self.setup_title = "Videoenhancement"
		self.oldSplitMode = oldSplitMode

		self.list = [ ]
		self.configEntry = configEntry
		ConfigListScreen.__init__(self, self.list, session = session, on_change = self.changedEntry)

		self["actions"] = ActionMap(["SetupActions"],
			{
				"cancel": self.keyCancel,
				"save": self.keySave,
			}, -2)

		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("OK"))

		self.createSetup()
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(_("Video enhancement preview"))

	def createSetup(self):
		self.list = [ ]
		if self.configEntry is not None:
			self.list = self.configEntry
		self["config"].list = self.list
		self["config"].l.setSeperation(300)
		self["config"].l.setList(self.list)

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.createSetup()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.createSetup()

	def keySave(self):
		if self.oldSplitMode is not None:
			currentSplitMode = config.pep.split.value
			if self.oldSplitMode == 'off' and currentSplitMode != 'off':
				config.pep.split.setValue('off')
			else:
				pass
		self.close()

	def keyCancel(self):
		for x in self["config"].list:
			x[1].cancel()
		if self.oldSplitMode is not None:
			currentSplitMode = config.pep.split.value
			if self.oldSplitMode == 'off' and currentSplitMode != 'off':
				config.pep.split.setValue('off')
			else:
				pass
		self.close()

	# for summary:
	def changedEntry(self):
		for x in self.onChangedEntry:
			x()

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())

	def createSummary(self):
		from Screens.Setup import SetupSummary
		return SetupSummary


def videoEnhancementSetupMain(session, **kwargs):
	session.open(VideoEnhancementSetup, video_enhancement)


def startSetup(menuid):
	if menuid != "system":
		return [ ]

	return [(_("Video enhancement settings") , videoEnhancementSetupMain, "videoenhancement_setup", 41)]


def Plugins(**kwargs):
	list = []
	if config.usage.setup_level.index >= 2: # expert+
		hw_type = HardwareInfo().get_device_name()
		if hw_type == 'dm8000' or hw_type == 'dm800':
			if (os.path.exists("/proc/stb/vmpeg/0/pep_apply") == True):
				list.append(PluginDescriptor(name=_("Videoenhancement Setup"), description=_("Advanced Video Enhancement Setup"), where = PluginDescriptor.WHERE_MENU, fnc=startSetup))
	return list
