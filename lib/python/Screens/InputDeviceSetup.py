from Screen import Screen
from Screens.HelpMenu import HelpableScreen
from Screens.MessageBox import MessageBox
from Components.InputDevice import iInputDevices, iRcTypeControl
from Components.Sources.StaticText import StaticText
from Components.Sources.List import List
from Components.config import config, ConfigYesNo, getConfigListEntry, ConfigSelection
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import ActionMap, HelpableActionMap
from Tools.Directories import resolveFilename, SCOPE_ACTIVE_SKIN
from Tools.LoadPixmap import LoadPixmap
from boxbranding import getBoxType, getMachineBrand, getMachineName

boxtype = getBoxType()

class InputDeviceSelection(Screen, HelpableScreen):
	def __init__(self, session):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)

		self.setTitle(_("Select input device"))
		self.edittext = _("Press OK to edit the settings.")

		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Select"))
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText("")
		self["introduction"] = StaticText(self.edittext)

		self.devices = [(iInputDevices.getDeviceName(x),x) for x in iInputDevices.getDeviceList()]
		print "[InputDeviceSelection] found devices :->", len(self.devices),self.devices

		self["OkCancelActions"] = HelpableActionMap(self, "OkCancelActions",
			{
			"cancel": (self.close, _("Exit input device selection.")),
			"ok": (self.okbuttonClick, _("Select input device.")),
			}, -2)

		self["ColorActions"] = HelpableActionMap(self, "ColorActions",
			{
			"red": (self.close, _("Exit input device selection.")),
			"green": (self.okbuttonClick, _("Select input device.")),
			}, -2)

		self.currentIndex = 0
		self.list = []
		self["list"] = List(self.list)
		self.updateList()
		self.onLayoutFinish.append(self.layoutFinished)
		self.onClose.append(self.cleanup)

	def layoutFinished(self):
		self.setTitle(_("Select input device"))

	def cleanup(self):
		self.currentIndex = 0

	def buildInterfaceList(self, device, description, type, isinputdevice = True):
		divpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_ACTIVE_SKIN, "div-h.png"))
		activepng = None
		devicepng = None
		enabled = iInputDevices.getDeviceAttribute(device, 'enabled')

		if type == 'remote':
			if config.misc.rcused.value == 0:
				if enabled:
					devicepng = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/input_rcnew-configured.png"))
				else:
					devicepng = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/input_rcnew.png"))
			else:
				if enabled:
					devicepng = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/input_rcold-configured.png"))
				else:
					devicepng = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/input_rcold.png"))
		elif type == 'keyboard':
			if enabled:
				devicepng = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/input_keyboard-configured.png"))
			else:
				devicepng = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/input_keyboard.png"))
		elif type == 'mouse':
			if enabled:
				devicepng = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/input_mouse-configured.png"))
			else:
				devicepng = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/input_mouse.png"))
		elif isinputdevice:
			devicepng = LoadPixmap(resolveFilename(SCOPE_ACTIVE_SKIN, "icons/input_rcnew.png"))
		return device, description, devicepng, divpng

	def updateList(self):
		self.list = []

		if iRcTypeControl.multipleRcSupported():
			self.list.append(self.buildInterfaceList('rctype', _('Configure remote control type'), None, False))

		for x in self.devices:
			dev_type = iInputDevices.getDeviceAttribute(x[1], 'type')
			self.list.append(self.buildInterfaceList(x[1],_(x[0]), dev_type))

		self["list"].setList(self.list)
		self["list"].setIndex(self.currentIndex)

	def okbuttonClick(self):
		selection = self["list"].getCurrent()
		self.currentIndex = self["list"].getIndex()
		if selection is not None:
			if selection[0] == 'rctype':
				self.session.open(RemoteControlType)
			else:
				self.session.openWithCallback(self.DeviceSetupClosed, InputDeviceSetup, selection[0])

	def DeviceSetupClosed(self, *ret):
		self.updateList()


class InputDeviceSetup(Screen, ConfigListScreen):
	def __init__(self, session, device):
		Screen.__init__(self, session)
		self.inputDevice = device
		iInputDevices.currentDevice = self.inputDevice
		self.onChangedEntry = [ ]
		self.setup_title = _("Input device setup")
		self.isStepSlider = None
		self.enableEntry = None
		self.repeatEntry = None
		self.delayEntry = None
		self.nameEntry = None
		self.enableConfigEntry = None

		self.list = [ ]
		ConfigListScreen.__init__(self, self.list, session = session, on_change = self.changedEntry)

		self["actions"] = ActionMap(["SetupActions", "MenuActions"],
			{
				"cancel": self.keyCancel,
				"save": self.apply,
				"menu": self.closeRecursive,
			}, -2)

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self["key_yellow"] = StaticText()
		self["key_blue"] = StaticText()
		self["introduction"] = StaticText()

		# for generating strings into .po only
		devicenames = [_("%s %s front panel") % (getMachineBrand(), getMachineName()),_("%s %s front panel") % (getMachineBrand(), getMachineName()),_("%s %s remote control (native)") % (getMachineBrand(), getMachineName()),_("%s %s advanced remote control (native)") % (getMachineBrand(), getMachineName()),_("%s %s ir keyboard") % (getMachineBrand(), getMachineName()),_("%s %s ir mouse") % (getMachineBrand(), getMachineName())]

		self.createSetup()
		self.onLayoutFinish.append(self.layoutFinished)
		self.onClose.append(self.cleanup)

	def layoutFinished(self):
		self.setTitle(self.setup_title)
		listWidth = self["config"].l.getItemSize().width()
		# use 20% of list width for sliders
		self["config"].l.setSeperation(int(listWidth*.8))

	def cleanup(self):
		iInputDevices.currentDevice = ""

	def createSetup(self):
		self.list = [ ]
		label = _("Change repeat and delay settings?")
		cmd = "self.enableEntry = getConfigListEntry(label, config.inputDevices." + self.inputDevice + ".enabled)"
		exec cmd
		label = _("Interval between keys when repeating:")
		cmd = "self.repeatEntry = getConfigListEntry(label, config.inputDevices." + self.inputDevice + ".repeat)"
		exec cmd
		label = _("Delay before key repeat starts:")
		cmd = "self.delayEntry = getConfigListEntry(label, config.inputDevices." + self.inputDevice + ".delay)"
		exec cmd
		label = _("Devicename:")
		cmd = "self.nameEntry = getConfigListEntry(label, config.inputDevices." + self.inputDevice + ".name)"
		exec cmd
		if self.enableEntry:
			if isinstance(self.enableEntry[1], ConfigYesNo):
				self.enableConfigEntry = self.enableEntry[1]

		self.list.append(self.enableEntry)
		if self.enableConfigEntry:
			if self.enableConfigEntry.value is True:
				self.list.append(self.repeatEntry)
				self.list.append(self.delayEntry)
			else:
				self.repeatEntry[1].setValue(self.repeatEntry[1].default)
				self["config"].invalidate(self.repeatEntry)
				self.delayEntry[1].setValue(self.delayEntry[1].default)
				self["config"].invalidate(self.delayEntry)
				self.nameEntry[1].setValue(self.nameEntry[1].default)
				self["config"].invalidate(self.nameEntry)

		self["config"].list = self.list
		self["config"].l.setList(self.list)
		if not self.selectionChanged in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def selectionChanged(self):
		if self["config"].getCurrent() == self.enableEntry:
			self["introduction"].setText(_("Current device: ") + str(iInputDevices.getDeviceAttribute(self.inputDevice, 'name')) )
		else:
			self["introduction"].setText(_("Current value: ") + self.getCurrentValue() + ' ' + _("ms"))

	def newConfig(self):
		current = self["config"].getCurrent()
		if current:
			if current == self.enableEntry:
				self.createSetup()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.newConfig()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.newConfig()

	def confirm(self, confirmed):
		if not confirmed:
			print "not confirmed"
			return
		else:
			self.nameEntry[1].setValue(iInputDevices.getDeviceAttribute(self.inputDevice, 'name'))
			cmd = "config.inputDevices." + self.inputDevice + ".name.save()"
			exec cmd
			self.keySave()

	def apply(self):
		self.session.openWithCallback(self.confirm, MessageBox, _("Use these input device settings?"), MessageBox.TYPE_YESNO, timeout=20, default=True)

	def cancelConfirm(self, result):
		if not result:
			return
		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def keyCancel(self):
		if self["config"].isChanged():
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"), MessageBox.TYPE_YESNO, timeout=20, default=True)
		else:
			self.close()
	# for summary:
	def changedEntry(self):
		for x in self.onChangedEntry:
			x()
		self.selectionChanged()

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].value)

	def createSummary(self):
		from Screens.Setup import SetupSummary
		return SetupSummary


class RemoteControlType(Screen, ConfigListScreen):
	
	rcList = [
			("0", _("Default")),
			("3", _("MaraM9")),
			("4", _("DMM normal")),
			("5", _("et9000/et9100")),
			("6", _("DMM advanced")),
			("7", _("et5000/6000")),
			("8", _("VU+")),
			("9", _("et8000/et10000")),
			("11", _("et9200/9500/6500")),
			("13", _("et4000")),
			("14", _("XP1000")),
			("16", _("HD1100/HD1200/HD1265/HD500C/et7x00/et8500")),
			("17", _("XP3000")),
			("18", _("F1/F3/TRIPLEX")),
			("19", _("HD2400"))
			]

	defaultRcList = [
			("et4000", 13),
			("et5000", 7),
			("et6000", 7),
			("et6500", 11),
			("et7x00",16),
			("et8000", 9),
			("et8500",16),
			("et9000", 5),
			("et9100", 5),
			("et9200", 11),
			("et9500", 11),
			("et10000", 9),
			("hd1100",16),
			("hd1200",16),
			("hd1265",16),
			("hd500c",16),
			("hd2400",19),
			("formuler1",18),
			("formuler3",18),
			("triplex",18),
			("xp1000", 14),
			("xp3000", 17)
			]

	def __init__(self, session):
		Screen.__init__(self, session)
		self.skinName = ["RemoteControlType", "Setup" ]

		self["actions"] = ActionMap(["SetupActions"],
		{
			"cancel": self.keyCancel,
			"save": self.keySave,
		}, -1)

		self["key_green"] = StaticText(_("Save"))
		self["key_red"] = StaticText(_("Cancel"))

		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session)

		rctype = config.plugins.remotecontroltype.rctype.value
		self.rctype = ConfigSelection(choices = self.rcList, default = str(rctype))
		self.list.append(getConfigListEntry(_("Remote control type"), self.rctype))
		self["config"].list = self.list

		self.defaultRcType = None
		self.getDefaultRcType()

	def getDefaultRcType(self):
		data = iRcTypeControl.getBoxType()
		for x in self.defaultRcList:
			if x[0] in data:
				self.defaultRcType = x[1]
				break

	def setDefaultRcType(self):
		iRcTypeControl.writeRcType(self.defaultRcType)

	def keySave(self):
		if config.plugins.remotecontroltype.rctype.value == int(self.rctype.value):
			self.close()
		else:
			self.setNewSetting()
			self.session.openWithCallback(self.keySaveCallback, MessageBox, _("Is this setting ok?"), MessageBox.TYPE_YESNO, timeout=20, default=True, timeout_default=False)

	def keySaveCallback(self, answer):
		if answer is False:
			self.restoreOldSetting()
		else:
			config.plugins.remotecontroltype.rctype.value = int(self.rctype.value)
			config.plugins.remotecontroltype.save()
			self.close()

	def restoreOldSetting(self):
		if config.plugins.remotecontroltype.rctype.value == 0:
			self.setDefaultRcType()
		else:
			iRcTypeControl.writeRcType(config.plugins.remotecontroltype.rctype.value)

	def setNewSetting(self):
		if int(self.rctype.value) == 0:
			self.setDefaultRcType()
		else:
			iRcTypeControl.writeRcType(int(self.rctype.value))

	def keyCancel(self):
		self.restoreOldSetting()
		self.close()
