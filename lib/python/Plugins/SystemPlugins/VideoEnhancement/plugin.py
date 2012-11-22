from Plugins.Plugin import PluginDescriptor
from Components.ConfigList import ConfigListScreen
from Components.config import getConfigListEntry, config, ConfigNothing, ConfigSelection
from Components.ActionMap import ActionMap
from Components.Sources.StaticText import StaticText
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
import VideoEnhancement
from os import path as os_path

class VideoEnhancementSetup(Screen, ConfigListScreen):

	skin = """
		<screen name="VideoEnhancementSetup" position="center,center" size="560,440" title="VideoEnhancementSetup">
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
			<widget source="key_blue" render="Label" position="420,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" />
			<widget name="config" position="5,50" size="550,350" scrollbarMode="showOnDemand" />
			<ePixmap pixmap="skin_default/div-h.png" position="0,400" zPosition="1" size="560,2" />
			<widget source="introduction" render="Label" position="5,410" size="550,30" zPosition="10" font="Regular;21" halign="center" valign="center" backgroundColor="#25062748" transparent="1" />
		</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)

		self.session = session
		self.onChangedEntry = [ ]
		self.setup_title = "Videoenhancement"

		self.list = [ ]
		self.xtdlist = [ ]
		ConfigListScreen.__init__(self, self.list, session = self.session, on_change = self.changedEntry)

		self["actions"] = ActionMap(["SetupActions", "ColorActions", "MenuActions"],
			{
				"cancel": self.keyCancel,
				"save": self.apply,
				"yellow": self.keyYellow,
				"blue": self.keyBlue,
				"menu": self.closeRecursive,
			}, -2)

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self["key_yellow"] = StaticText(_("Last config"))
		self["key_blue"] = StaticText(_("Default"))
		self["introduction"] = StaticText()

		self.createSetup()
		self.rememberOldSettings()
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(_("Video enhancement setup"))

	def rememberOldSettings(self):
		self.oldContrast = config.pep.contrast.value
		self.oldSaturation = config.pep.saturation.value
		self.oldHue = config.pep.hue.value
		self.oldBrightness = config.pep.brightness.value
		self.oldBlock_noise = config.pep.block_noise_reduction.value
		self.oldMosquito_noise = config.pep.mosquito_noise_reduction.value
		self.oldDigital_contour = config.pep.digital_contour_removal.value
		self.oldScaler_sharpness = config.av.scaler_sharpness.value
		self.oldSplit = config.pep.split.value
		self.oldSharpness = config.pep.sharpness.value
		self.oldAuto_flesh = config.pep.auto_flesh.value
		self.oldGreen_boost = config.pep.green_boost.value
		self.oldBlue_boost = config.pep.blue_boost.value
		self.oldDynamic_contrast = config.pep.dynamic_contrast.value

	def addToConfigList(self, description, configEntry, add_to_xtdlist=False):
		if isinstance(configEntry, ConfigNothing):
			return None
		entry = getConfigListEntry(description, configEntry)
		self.list.append(entry);
		if add_to_xtdlist:
			self.xtdlist.append(entry)
		return entry

	def createSetup(self):
		self.list = []
		self.xtdlist = []
		addToConfigList = self.addToConfigList
		self.contrastEntry = addToConfigList(_("Contrast"), config.pep.contrast)
		self.saturationEntry = addToConfigList(_("Saturation"), config.pep.saturation)
		self.hueEntry = addToConfigList(_("Hue"), config.pep.hue)
		self.brightnessEntry = addToConfigList(_("Brightness"), config.pep.brightness)
		self.scaler_sharpnessEntry = addToConfigList(_("Scaler sharpness"), config.av.scaler_sharpness)
		self.splitEntry = addToConfigList(_("Split preview mode"), config.pep.split, True)
		add_to_xtdlist = self.splitEntry is not None
		self.sharpnessEntry = addToConfigList(_("Sharpness"), config.pep.sharpness, add_to_xtdlist)
		self.auto_fleshEntry = addToConfigList(_("Auto flesh"), config.pep.auto_flesh, add_to_xtdlist)
		self.green_boostEntry = addToConfigList(_("Green boost"), config.pep.green_boost, add_to_xtdlist)
		self.blue_boostEntry = addToConfigList(_("Blue boost"), config.pep.blue_boost, add_to_xtdlist)
		self.dynamic_contrastEntry = addToConfigList(_("Dynamic contrast"), config.pep.dynamic_contrast, add_to_xtdlist)
		self.block_noise_reductionEntry = addToConfigList(_("Block noise reduction"), config.pep.block_noise_reduction, add_to_xtdlist)
		self.mosquito_noise_reductionEntry = addToConfigList(_("Mosquito noise reduction"), config.pep.mosquito_noise_reduction, add_to_xtdlist)
		self.digital_contour_removalEntry = addToConfigList(_("Digital contour removal"), config.pep.digital_contour_removal, add_to_xtdlist)

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
		elif current != self.splitEntry and current in self.xtdlist:
			self.previewlist = [
				current,
				self.splitEntry
			]
			maxvalue = current[1].max
			self.session.openWithCallback(self.PreviewClosed, VideoEnhancementPreview, configEntry = self.previewlist, oldSplitMode = config.pep.split.value, maxValue = maxvalue)
		else:
			self.previewlist = [
				current
			]
			maxvalue = current[1].max
			self.session.openWithCallback(self.PreviewClosed, VideoEnhancementPreview, configEntry = self.previewlist, oldSplitMode = None, maxValue = maxvalue)

	def keyRight(self):
		current = self["config"].getCurrent()
		if current == self.splitEntry:
			ConfigListScreen.keyRight(self)
		elif current != self.splitEntry and current in self.xtdlist:
			self.previewlist = [
				current,
				self.splitEntry
			]
			maxvalue = current[1].max
			self.session.openWithCallback(self.PreviewClosed, VideoEnhancementPreview, configEntry = self.previewlist, oldSplitMode = config.pep.split.value, maxValue = maxvalue )
		else:
			self.previewlist = [
				current
			]
			maxvalue = current[1].max
			self.session.openWithCallback(self.PreviewClosed, VideoEnhancementPreview, configEntry = self.previewlist, oldSplitMode = None, maxValue = maxvalue)

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
			if self.block_noise_reductionEntry is not None:
				config.pep.block_noise_reduction.setValue(self.oldBlock_noise)
			if self.mosquito_noise_reductionEntry is not None:
				config.pep.mosquito_noise_reduction.setValue(self.oldMosquito_noise)
			if self.digital_contour_removalEntry is not None:
				config.pep.digital_contour_removal.setValue(self.oldDigital_contour)
			if self.scaler_sharpnessEntry is not None:
				config.av.scaler_sharpness.setValue(self.oldScaler_sharpness)
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
			if self.block_noise_reductionEntry is not None:
				config.pep.block_noise_reduction.setValue(0)
			if self.mosquito_noise_reductionEntry is not None:
				config.pep.mosquito_noise_reduction.setValue(0)
			if self.digital_contour_removalEntry is not None:
				config.pep.digital_contour_removal.setValue(0)
			if self.scaler_sharpnessEntry is not None:
				config.av.scaler_sharpness.setValue(13)
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
			if self.dynamic_contrastEntry is not None:
				config.pep.dynamic_contrast.setValue(0)
			self.keySave()

	def keyBlue(self):
		self.session.openWithCallback(self.keyBlueConfirm, MessageBox, _("Reset video enhancement settings to system defaults?"), MessageBox.TYPE_YESNO, timeout = 20, default = False)

	# for summary:
	def changedEntry(self):
		for x in self.onChangedEntry:
			x()
		self.selectionChanged()

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())

	def createSummary(self):
		from Screens.Setup import SetupSummary
		return SetupSummary


class VideoEnhancementPreview(Screen, ConfigListScreen):

	skin = """
		<screen name="VideoEnhancementPreview" position="center,360" size="560,170" title="VideoEnhancementPreview">
			<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="config" position="5,50" size="550,80" scrollbarMode="showOnDemand" />
			<ePixmap pixmap="skin_default/div-h.png" position="0,130" zPosition="1" size="560,2" />
			<widget source="introduction" render="Label" position="0,140" size="550,25" zPosition="10" font="Regular;21" halign="center" valign="center" backgroundColor="#25062748" transparent="1" />
		</screen>"""

	def __init__(self, session, configEntry = None, oldSplitMode = None, maxValue = None):
		Screen.__init__(self, session)

		self.onChangedEntry = [ ]
		self.setup_title = "Videoenhancement"
		self.oldSplitMode = oldSplitMode
		self.maxValue = maxValue
		self.configStepsEntry = None
		self.isStepSlider = None

		self.list = [ ]
		self.configEntry = configEntry
		ConfigListScreen.__init__(self, self.list, session = session, on_change = self.changedEntry)

		self["actions"] = ActionMap(["SetupActions"],
			{
				"cancel": self.keyCancel,
				"save": self.keySave,
			}, -2)

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self["introduction"] = StaticText()

		self.createSetup()
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.setTitle(_("Video enhancement preview"))

	def createSetup(self):
		self.list = [ ]
		if self.maxValue == 256:
			self.configStepsEntry = getConfigListEntry(_("Change step size"), config.pep.configsteps)

		if self.configEntry is not None:
			self.list = self.configEntry
		if self.maxValue == 256:
			self.list.append(self.configStepsEntry)

		self["config"].list = self.list
		self["config"].l.setSeperation(300)
		self["config"].l.setList(self.list)
		if not self.selectionChanged in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def selectionChanged(self):
		self["introduction"].setText(_("Current value: ") + self.getCurrentValue())
		try:
			max_avail=self["config"].getCurrent()[1].max
			if max_avail == 256:
				self.isStepSlider = True
			else:
				self.isStepSlider = False
		except AttributeError:
			print "no max value"

	def keyLeft(self):
		if self.isStepSlider is True:
			self["config"].getCurrent()[1].increment = config.pep.configsteps.value
		ConfigListScreen.keyLeft(self)

	def keyRight(self):
		if self.isStepSlider is True:
			self["config"].getCurrent()[1].increment = config.pep.configsteps.value
		ConfigListScreen.keyRight(self)

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
		self.selectionChanged()

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())

	def createSummary(self):
		from Screens.Setup import SetupSummary
		return SetupSummary

def videoEnhancementSetupMain(session, **kwargs):
	session.open(VideoEnhancementSetup)

def startSetup(menuid):
	if menuid != "system":
		return [ ]
	return [(_("Video enhancement settings") , videoEnhancementSetupMain, "videoenhancement_setup", 41)]

def Plugins(**kwargs):
	list = []
	if config.usage.setup_level.index >= 2 and os_path.exists("/proc/stb/vmpeg/0/pep_apply"):
		list.append(PluginDescriptor(name=_("Video enhancement setup"), description=_("Advanced video enhancement setup"), where = PluginDescriptor.WHERE_MENU, needsRestart = False, fnc=startSetup))
	return list
