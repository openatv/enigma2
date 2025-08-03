from Plugins.Plugin import PluginDescriptor
from Components.ConfigList import ConfigListScreen
from Components.config import getConfigListEntry, config, ConfigNothing
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.Pixmap import Pixmap
from Components.Sources.Boolean import Boolean
from Components.Sources.StaticText import StaticText
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from . import VideoEnhancement


class VideoEnhancementSetup(ConfigListScreen, Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.onChangedEntry = []
		self.skinName = ["VideoEnhancementSetup"]
		self.setTitle(_("Video enhancement setup"))
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["VKeyIcon"] = Boolean(False)
		self['footnote'] = Label()
		self["description"] = Label("")
		self["introduction"] = StaticText()

		self.list = []
		ConfigListScreen.__init__(self, self.list, session=session, on_change=self.changedEntry)
		self.createSetup()

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

		if self.SelectionChanged not in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.SelectionChanged)
		self.rememberOldSettings()
		self.changedEntry()

	def rememberOldSettings(self):
		self.oldContrast1 = config.amvecm.contrast1.value
		self.oldContrast2 = config.amvecm.contrast2.value
		self.oldSaturation = config.amvecm.saturation.value
		self.oldHue = config.amvecm.hue.value
		self.oldBrightness1 = config.amvecm.brightness1.value
		self.oldBrightness2 = config.amvecm.brightness2.value
		self.oldColor_bottom = config.amvecm.color_bottom.value
		self.oldColor_top = config.amvecm.color_top.value

	def addToConfigList(self, description, configEntry, hinttext):
		if isinstance(configEntry, ConfigNothing):
			return None
		entry = getConfigListEntry(description, configEntry, hinttext)
		self.list.append(entry)
		return entry

	def createSetup(self):
		self.list = []
		addToConfigList = self.addToConfigList
		self.brightness1Entry = addToConfigList(_("Brightness Video"), config.amvecm.brightness1, _("This option sets the video picture brightness."))
		self.brightness2Entry = addToConfigList(_("Brightness Video & OSD"), config.amvecm.brightness2, _("This option sets the video & osd picture brightness."))
		self.color_bottomEntry = addToConfigList(_("Color Bottom"), config.amvecm.color_bottom, _("This option allows you to boost the blue tones in the picture."))
		self.color_topEntry = addToConfigList(_("Color Top"), config.amvecm.color_top, _("This option allows you to boost the green tones in the picture."))
		self.contrast1Entry = addToConfigList(_("Contrast Video"), config.amvecm.contrast1, _("This option sets the video picture contrast."))
		self.contrast2Entry = addToConfigList(_("Contrast Video & OSD"), config.amvecm.contrast2, _("This option sets the video & osd picture contrast."))
		self.hueEntry = addToConfigList(_("Hue"), config.amvecm.hue, _("This option sets the picture hue."))
		self.saturationEntry = addToConfigList(_("Saturation"), config.amvecm.saturation, _("This option sets the picture saturation."))
		self["config"].list = self.list
		self["config"].l.setList(self.list)
		#if config.usage.sort_settings.value:
		#	self["config"].list.sort()

	def SelectionChanged(self):
		self["description"].setText(self["config"].getCurrent()[2])

	def PreviewClosed(self):
		self["config"].invalidate(self["config"].getCurrent())
		self.createSetup()

	def keyLeft(self):
		current = self["config"].getCurrent()
		if current == self.color_bottomEntry or current == self.color_topEntry:
			ConfigListScreen.keyLeft(self)
		else:
			self.previewlist = [
				current
			]
			maxvalue = current[1].max
			self.session.openWithCallback(self.PreviewClosed, VideoEnhancementPreview, configEntry=self.previewlist, maxValue=maxvalue)

	def keyRight(self):
		current = self["config"].getCurrent()
		if current == self.color_bottomEntry or current == self.color_topEntry:
			ConfigListScreen.keyRight(self)
		else:
			self.previewlist = [
				current
			]
			maxvalue = current[1].max
			self.session.openWithCallback(self.PreviewClosed, VideoEnhancementPreview, configEntry=self.previewlist, maxValue=maxvalue)

	def confirm(self, confirmed):
		if not confirmed:
			print("not confirmed")
		else:
			self.keySave()

	def apply(self):
		self.session.openWithCallback(self.confirm, MessageBox, _("Use this video enhancement settings?"), MessageBox.TYPE_YESNO, timeout=20, default=True)

	def cancelConfirm(self, result):
		if not result:
			return
		self.keyYellowConfirm(True)
		self.close()

	def keyCancel(self):
		if self["config"].isChanged():
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"), default=False)
		else:
			self.close()

	def keyYellowConfirm(self, confirmed):
		if not confirmed:
			print("not confirmed")
		else:
			if self.contrast1Entry is not None:
				config.amvecm.contrast1.setValue(self.oldContrast1)
			if self.contrast2Entry is not None:
				config.amvecm.contrast2.setValue(self.oldContrast2)
			if self.saturationEntry is not None:
				config.amvecm.saturation.setValue(self.oldSaturation)
			if self.hueEntry is not None:
				config.amvecm.hue.setValue(self.oldHue)
			if self.brightness1Entry is not None:
				config.amvecm.brightness1.setValue(self.oldBrightness1)
			if self.brightness2Entry is not None:
				config.amvecm.brightness2.setValue(self.oldBrightness2)
			if self.color_bottomEntry is not None:
				config.amvecm.color_bottom.setValue(self.oldColor_bottom)
			if self.color_topEntry is not None:
				config.amvecm.color_top.setValue(self.oldColor_top)
			self.keySave()

	def keyYellow(self):
		self.session.openWithCallback(self.keyYellowConfirm, MessageBox, _("Reset video enhancement settings to your last configuration?"), MessageBox.TYPE_YESNO, timeout=20, default=False)

	def keyBlueConfirm(self, confirmed):
		if not confirmed:
			print("not confirmed")
		else:
			if self.contrast1Entry is not None:
				config.amvecm.contrast1.setValue(0)
			if self.contrast2Entry is not None:
				config.amvecm.contrast2.setValue(0)
			if self.saturationEntry is not None:
				config.amvecm.saturation.setValue(0)
			if self.hueEntry is not None:
				config.amvecm.hue.setValue(256)
			if self.brightness1Entry is not None:
				config.amvecm.brightness1.setValue(0)
			if self.brightness2Entry is not None:
				config.amvecm.brightness2.setValue(0)
			if self.color_bottomEntry is not None:
				config.amvecm.color_bottom.setValue(0)
			if self.color_topEntry is not None:
				config.amvecm.color_top.setValue(1073741823)
			self.keySave()

	def keyBlue(self):
		self.session.openWithCallback(self.keyBlueConfirm, MessageBox, _("Reset video enhancement settings to system defaults?"), MessageBox.TYPE_YESNO, timeout=20, default=False)

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


class VideoEnhancementPreview(ConfigListScreen, Screen):
	skin = """
		<screen name="VideoEnhancementPreview" position="center,e-170" size="560,170" title="VideoEnhancementPreview" resolution="1280,720">
			<ePixmap pixmap="buttons/red.png" position="0,0" size="140,40" alphatest="on" />
			<ePixmap pixmap="buttons/green.png" position="140,0" size="140,40" alphatest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
			<widget name="config" position="5,50" size="550,80" scrollbarMode="showOnDemand" />
			<ePixmap pixmap="div-h.png" position="0,130" zPosition="1" size="560,2" />
			<widget source="introduction" render="Label" position="0,140" size="550,25" zPosition="10" font="Regular;21" halign="center" valign="center" backgroundColor="#25062748" transparent="1" />
		</screen>"""

	def __init__(self, session, configEntry=None, maxValue=None):
		Screen.__init__(self, session)

		self.onChangedEntry = []
		self.setup_title = "Videoenhancement"
		self.maxValue = maxValue
		self.configStepsEntry = None
		self.isStepSlider = None

		self.list = []
		self.configEntry = configEntry
		ConfigListScreen.__init__(self, self.list, session=session, on_change=self.changedEntry)

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
		self.list = []
		if self.maxValue == 255:
			self.configStepsEntry = getConfigListEntry(_("Change step size"), config.amvecm.configsteps)

		if self.configEntry is not None:
			self.list = self.configEntry
		if self.maxValue == 255:
			self.list.append(self.configStepsEntry)

		self["config"].list = self.list
		self["config"].l.setSeperation(300)
		self["config"].l.setList(self.list)
		if self.selectionChanged not in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def selectionChanged(self):
		self["introduction"].setText(_("Current value: ") + self.getCurrentValue())
		try:
			max_avail = self["config"].getCurrent()[1].max
			if max_avail == 255:
				self.isStepSlider = True
			else:
				self.isStepSlider = False
		except AttributeError:
			print("no max value")

	def keyLeft(self):
		if self.isStepSlider is True:
			self["config"].getCurrent()[1].increment = config.amvecm.configsteps.value
		ConfigListScreen.keyLeft(self)

	def keyRight(self):
		if self.isStepSlider is True:
			self["config"].getCurrent()[1].increment = config.amvecm.configsteps.value
		ConfigListScreen.keyRight(self)

	def keySave(self):
		self.close()

	def keyCancel(self):
		for x in self["config"].list:
			x[1].cancel()
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
	if menuid != "video_menu":
		return []
	return [(_("Video enhancement setup"), videoEnhancementSetupMain, "videoenhancement_setup", 5)]


def Plugins(**kwargs):
	return PluginDescriptor(name=_("Video enhancement setup"), description=_("Advanced video enhancement setup"), where=PluginDescriptor.WHERE_MENU, needsRestart=False, fnc=startSetup)
