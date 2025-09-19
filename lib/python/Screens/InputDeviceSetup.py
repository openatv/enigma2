from Components.ActionMap import HelpableActionMap
from Components.config import ConfigSelection, ConfigYesNo, config, getConfigListEntry
from Components.InputDevice import inputDevices, keyboard, iRcTypeControl
from Components.SystemInfo import BoxInfo, getBoxDisplayName
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Setup import Setup
from Tools.Directories import resolveFilename, SCOPE_GUISKIN
from Tools.LoadPixmap import LoadPixmap


class InputDeviceSelection(Screen):
	def __init__(self, session):
		Screen.__init__(self, session, enableHelp=True)
		self.setTitle(_("Select input device"))
		self.edittext = _("Press OK to edit the settings.")
		self["key_red"] = StaticText(_("Close"))
		self["key_green"] = StaticText(_("Select"))
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText("")
		self["introduction"] = StaticText(self.edittext)
		self.devices = [(inputDevices.getDeviceName(x), x) for x in inputDevices.getDeviceList()]
		print(f"[InputDeviceSelection] found devices :-> {len(self.devices)} {str(self.devices)}")
		self["OkCancelActions"] = HelpableActionMap(self, "OkCancelActions", {
			"cancel": (self.close, _("Exit input device selection.")),
			"ok": (self.okbuttonClick, _("Select input device."))
		}, prio=-2)
		self["ColorActions"] = HelpableActionMap(self, "ColorActions", {
			"red": (self.close, _("Exit input device selection.")),
			"green": (self.okbuttonClick, _("Select input device."))
		}, prio=-2)
		self.currentIndex = 0
		self.list = []
		self["list"] = List(self.list)
		self.updateList()
		self.onClose.append(self.cleanup)

	def cleanup(self):
		self.currentIndex = 0

	def buildInterfaceList(self, device, description, type, isinputdevice=True):
		divpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "div-h.png"))
		activepng = None
		devicepng = None
		enabled = inputDevices.getDeviceAttribute(device, "enabled")
		if type == "remote":
			if config.misc.rcused.value == 0:
				if enabled:
					devicepng = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/input_rcnew-configured.png"))
				else:
					devicepng = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/input_rcnew.png"))
			else:
				if enabled:
					devicepng = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/input_rcold-configured.png"))
				else:
					devicepng = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/input_rcold.png"))
		elif type == "keyboard":
			if enabled:
				devicepng = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/input_keyboard-configured.png"))
			else:
				devicepng = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/input_keyboard.png"))
		elif type == "mouse":
			if enabled:
				devicepng = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/input_mouse-configured.png"))
			else:
				devicepng = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/input_mouse.png"))
		elif isinputdevice:
			devicepng = LoadPixmap(resolveFilename(SCOPE_GUISKIN, "icons/input_rcnew.png"))
		return device, description, devicepng, divpng

	def updateList(self):
		self.list = []
		if iRcTypeControl.multipleRcSupported():
			self.list.append(self.buildInterfaceList("rctype", _("Configure remote control type"), None, False))

		for x in self.devices:
			dev_type = inputDevices.getDeviceAttribute(x[1], "type")
			self.list.append(self.buildInterfaceList(x[1], _(x[0]), dev_type))
		self["list"].setList(self.list)
		self["list"].setIndex(self.currentIndex)

	def okbuttonClick(self):
		selection = self["list"].getCurrent()
		self.currentIndex = self["list"].getIndex()
		if selection is not None:
			if selection[0] == "rctype":
				self.session.open(RemoteControlType)
			else:
				self.session.openWithCallback(self.DeviceSetupClosed, InputDeviceSetup, selection[0])

	def DeviceSetupClosed(self, *ret):
		self.updateList()


class KeyboardSelection(Setup):
	def __init__(self, session):
		Setup.__init__(self, session, "Keyboard")
		self.initialKeyboardsIndex = config.inputDevices.keyboardsIndex.value

	def keySave(self):
		def keySaveCallback(answer):
			if answer:
				return Setup.keySave(self)
			config.inputDevices.keyboardsIndex.value = self.initialKeyboardsIndex
			print("[InputDeviceSetup] Keyboard selection rejected by user, returning to initial selection.")
			keyboard.loadKeyboard(self.initialKeyboardsIndex)
			for item in self["config"].getList():
				self["config"].invalidate(item)

		index = config.inputDevices.keyboardsIndex.value
		if index == self.initialKeyboardsIndex:
			self.close()  # Use 'Setup.keySave(self)' if there are other settings to be saved.
		else:
			keyboard.loadKeyboard(index)
			self.session.openWithCallback(keySaveCallback, MessageBox, _("Is the keyboard working?"), MessageBox.TYPE_YESNO, timeout=30, default=True, timeout_default=False, windowTitle=self.getTitle())


class InputDeviceSetup(Setup):
	def __init__(self, session, device):
		self.device = device
		inputDevices.currentDevice = self.device
		configItem = getattr(config.inputDevices, device)
		self.enableEntry = getConfigListEntry(self.formatItemText(_("Change repeat and delay settings?")), configItem.enabled, self.formatItemDescription(configItem.enabled, _("Select 'Yes' to enable editing of this device's settings. Selecting 'No' resets the devices settings to their default values.")))
		self.nameEntry = getConfigListEntry(self.formatItemText(_("Device name:")), configItem.name, self.formatItemDescription(configItem.name, _("Enter a new name for this device.")))
		self.delayEntry = getConfigListEntry(self.formatItemText(_("Delay before key repeat starts:")), configItem.delay, self.formatItemDescription(configItem.delay, _("Select the time delay before the button starts repeating.")))
		self.repeatEntry = getConfigListEntry(self.formatItemText(_("Interval between keys when repeating:")), configItem.repeat, self.formatItemDescription(configItem.repeat, _("Select the time delay between each repeat of the button.")))
		Setup.__init__(self, session, "InputDeviceSetup")
		self.setTitle(_("Setup InputDevice"))
		# self.skinName.insert(0, "InputDeviceDriverSetup")
		self.onClose.append(self.cleanup)
		# For generating strings into .po only.
		devicenames = [
			_("%s %s front panel") % getBoxDisplayName(),
			_("%s %s front panel") % getBoxDisplayName(),
			_("%s %s remote control (native)") % getBoxDisplayName(),
			_("%s %s advanced remote control (native)") % getBoxDisplayName(),
			_("%s %s ir keyboard") % getBoxDisplayName(),
			_("%s %s ir mouse") % getBoxDisplayName()
		]

	def cleanup(self):
		inputDevices.currentDevice = None

	def createSetup(self, appendItems=None, prependItems=None):
		settingsList = []
		if self.enableEntry and isinstance(self.enableEntry[1], ConfigYesNo):
			settingsList.append(self.enableEntry)
			if self.enableEntry[1].value is True:
				settingsList.append(self.nameEntry)
				settingsList.append(self.delayEntry)
				settingsList.append(self.repeatEntry)
			else:
				self.nameEntry[1].setValue(self.nameEntry[1].default)
				self.delayEntry[1].setValue(self.delayEntry[1].default)
				self.repeatEntry[1].setValue(self.repeatEntry[1].default)
		self["config"].list = settingsList

	def keySave(self):
		self.session.openWithCallback(self.keySaveConfirm, MessageBox, _("Use these input device settings?"), MessageBox.TYPE_YESNO, timeout=20, default=True)

	def keySaveConfirm(self, confirmed):
		if confirmed:
			configItem = getattr(config.inputDevices, self.device)
			configItem.save()
			print(f"[InputDeviceSetup] Changes made for '{self.device}' ({self.nameEntry[1].value}) saved.")
			return Setup.keySave(self)
		else:
			print(f"[InputDeviceSetup] Changes made for '{self.device}' ({self.nameEntry[1].value}) were not confirmed.")


class RemoteControlType(Setup):
	if BoxInfo.getItem("brand") in ("broadmedia", "octagon", "odin", "protek", "ultramini") or BoxInfo.getItem("machinebuild") in ("et7000", "et7100", "et7200", "et7500", "et7x00", "et8500", "et1x000", "et13000"):
		rcList = [
			("0", _("Default")),
			("3", "MaraM9"),
			("4", _("DMM normal")),
			("5", "et9000/et9100"),
			("6", _("DMM advanced")),
			("7", "et5000/6000"),
			("8", "VU+"),
			("9", "et8000/et10000/et13000/SF5008"),
			("11", "et9200/9500/6500"),
			("13", "et4000"),
			("14", "XP1000"),
			("16", "HD11/HD51/HD1100/HD1200/HD1265/HD1500/HD500C/HD530C/et7x00/et8500/VS1000/VS1500"),
			("17", "XP3000"),
			("18", "F1/F3/F4/F4-TURBO/TRIPLEX"),
			("19", "HD2400"),
			("20", "Zgemma Star S/2S/H1/H2"),
			("21", "Zgemma H.S/H.2S/H.2H/H5/H7/H17"),
			("500", "WWIO_BRE2ZE_TC"),
			("501", "OCTAGON_SF4008"),
			("502", "GIGABLUE Black"),
			("503", "MIRACLEBOX_TWINPLUS"),
			("504", "E3HD/XPEEDLX/GI"),
			("505", "ODIN_M7"),
			("507", "Beyonwiz U4"),
			("511", "OCTAGON SF5008")
		]
		defaultRcList = [
			("default", 0),
			("et4000", 13),
			("et5000", 7),
			("et6000", 7),
			("et6500", 11),
			("et7x00", 16),
			("et7100", 16),
			("et7000", 16),
			("et7500", 16),
			("et7000mini", 16),
			("et8000", 9),
			("et13000", 9),
			("et8500", 16),
			("et9000", 5),
			("et9100", 5),
			("et9200", 11),
			("et9500", 11),
			("et10000", 9),
			("formuler1", 18),
			("formuler3", 18),
			("formuler4", 18),
			("formuler4turbo", 18),
			("hd11", 16),
			("hd51", 16),
			("hd1100", 16),
			("hd1200", 16),
			("hd1265", 16),
			("hd500c", 16),
			("hd530c", 16),
			("vs1000", 16),
			("vs1500", 16),
			("hd2400", 19),
			("triplex", 18),
			("xp1000", 14),
			("xp3000", 17),
			("sh1", 20),
			("h3", 21),
			("h5", 21),
			("h7", 21),
			("h17", 21),
			("bre2ze_tc", 500),
			("sf4008", 501),
			("g100", 501),
			("sf4018", 501),
			("gbquadplus", 502),
			("g300", 503),
			("e3hd", 504),
			("et7000mini", 504),
			("et1x000", 504),
			("xpeedc.", 504),
			("odinm7", 505),
			("beyonwizu4", 507),
			("sf5008", 511)
		]
	else:
		rcList = [
			("0", _("Default")),
			("3", "MaraM9"),
			("4", _("DMM normal")),
			("5", "et9000/et9100"),
			("6", _("DMM advanced")),
			("7", "et5000/6000"),
			("8", "VU+"),
			("9", "et8000/et10000/et13000"),
			("11", "et9200/9500/6500"),
			("13", "et4000"),
			("14", "XP1000"),
			("16", "HD11/HD51/HD1100/HD1200/HD1265/HD1500/HD500C/HD530C/VS1000/VS1500"),
			("17", "XP3000"),
			("18", "F1/F3/F4/F4-TURBO/TRIPLEX"),
			("19", "HD2400"),
			("20", "Zgemma Star S/2S/H1/H2"),
			("21", _("Zgemma H.S/H.2S/H.2H/H5/H7 old Model")),
			("22", "Zgemma i55"),
			("23", "WWIO 4K"),
			("24", "Axas E4HD Ultra"),
			("25", "Zgemma H8/H0/H9/I55Plus old Model"),
			("26", "Protek 4K UHD/HD61"),
			("27", "HD60/HD66SE/Multibox/Multiboxse/Multiboxpro"),
			("28", _("I55SE/H7/H17/H9/H9SE/H9COMBO/H9COMBOSE/H10/H11 new Model"))
		]
		defaultRcList = [
			("default", 0),
			("et4000", 13),
			("et5000", 7),
			("et6000", 7),
			("et6500", 11),
			("et8000", 9),
			("et13000", 9),
			("et9000", 5),
			("et9100", 5),
			("et9200", 11),
			("et9500", 11),
			("et10000", 9),
			("formuler1", 18),
			("formuler3", 18),
			("formuler4", 18),
			("formuler4turbo", 18),
			("hd11", 16),
			("hd51", 16),
			("hd1100", 16),
			("hd1200", 16),
			("hd1265", 16),
			("hd500c", 16),
			("hd530c", 16),
			("vs1000", 16),
			("vs1500", 16),
			("hd2400", 19),
			("triplex", 18),
			("xp1000", 14),
			("xp3000", 17),
			("sh1", 20),
			("h3", 21),
			("h5", 21),
			# ("h7", 21),  # Old model.
			("i55", 22),
			("bre2ze4k", 23),
			("e4hd", 24),
			# ("h9", 25),  # Old model.
			("i55plus", 25),
			("hzero", 25),
			("h8", 25),
			("protek4k", 26),
			("hd61", 26),
			("hd60", 27),
			("hd66se", 27),
			("multibox", 27),
			("multiboxse", 27),
			("multiboxpro", 27),
			("h7", 21),  # New model.
			("h17", 28),
			("h9", 28),  # New model.
			("h9se", 28),  # New model.
			("h9combo", 28),
			("h9combose", 28),
			("i55se", 28),
			("h10", 28),
			("h11", 28)
		]

	def __init__(self, session):
		self.rctype = None
		self.defaultRcType = 0
		self.getDefaultRcType()
		Setup.__init__(self, session, None)
		self.setTitle(_("Setup InputDevice"))

	def createSetup(self, appendItems=None, prependItems=None):
		settingsList = []
		if self.rctype is None:
			rctype = config.plugins.remotecontroltype.rctype.value
			self.rctype = ConfigSelection(choices=self.rcList, default=str(rctype))
		settingsList.append(getConfigListEntry(_("Remote control type"), self.rctype))
		self["config"].list = settingsList

	def getBoxTypeCompatible(self):
		try:
			with open("/proc/stb/info/boxtype") as fd:
				boxType = fd.read()
				return boxType
		except OSError:
			pass
		return "Default"

	def getDefaultRcType(self):
		boxtype = BoxInfo.getItem("machinebuild")
		boxtypecompat = self.getBoxTypeCompatible()
		self.defaultRcType = 0
		# print("[InputDeviceSetup] Boxtype is {boxtype}.")
		for x in self.defaultRcList:
			if x[0] in boxtype:
				self.defaultRcType = x[1]
				# print(f"[InputDeviceSetup] Selecting {self.defaultRcType} as defaultRcType")
				break

		# boxtypecompat should be removed in the future.
		if (self.defaultRcType == 0):
			for x in self.defaultRcList:
				if x[0] in boxtypecompat:
					self.defaultRcType = x[1]
					# print("[InputDeviceSetup] Selecting {self.defaultRcType} as defaultRcType")
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
