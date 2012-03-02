from Screen import Screen
from Screens.HelpMenu import HelpableScreen
from Screens.MessageBox import MessageBox
from Components.InputDevice import iInputDevices
from Components.Sources.StaticText import StaticText
from Components.Sources.Boolean import Boolean
from Components.Sources.List import List
from Components.config import config, ConfigSlider, ConfigSubsection, ConfigYesNo, ConfigText, getConfigListEntry, ConfigNothing
from Components.ConfigList import ConfigListScreen
from Components.ActionMap import ActionMap, NumberActionMap, HelpableActionMap
from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN
from Tools.LoadPixmap import LoadPixmap

class InputDeviceSelection(Screen,HelpableScreen):
	skin = """
	<screen name="InputDeviceSelection" position="center,center" size="560,400" title="Select input device">
		<ePixmap pixmap="skin_default/buttons/red.png" position="0,0" size="140,40" alphatest="on"/>
		<ePixmap pixmap="skin_default/buttons/green.png" position="140,0" size="140,40" alphatest="on"/>
		<ePixmap pixmap="skin_default/buttons/yellow.png" position="280,0" size="140,40" alphatest="on"/>
		<ePixmap pixmap="skin_default/buttons/blue.png" position="420,0" size="140,40" alphatest="on"/>
		<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1"/>
		<widget source="key_green" render="Label" position="140,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1"/>
		<widget source="key_yellow" render="Label" position="280,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1"/>
		<widget source="key_blue" render="Label" position="420,0" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1"/>
		<widget source="list" render="Listbox" position="5,50" size="550,280" zPosition="10" scrollbarMode="showOnDemand">
			<convert type="TemplatedMultiContent">
			<!--  device, description, devicepng, divpng  -->
							{"template": [
									MultiContentEntryPixmapAlphaTest(pos = (2, 8), size = (54, 54), png = 2), # index 3 is the interface pixmap
									MultiContentEntryText(pos = (65, 6), size = (450, 54), font=0, flags = RT_HALIGN_LEFT|RT_VALIGN_CENTER|RT_WRAP, text = 1), # index 1 is the interfacename
								],
							"fonts": [gFont("Regular", 28),gFont("Regular", 20)],
							"itemHeight": 70
							}
						
			</convert>
		</widget>
		<ePixmap pixmap="skin_default/div-h.png" position="0,340" zPosition="1" size="560,2"/>
		<widget source="introduction" render="Label" position="0,350" size="560,50" zPosition="10" font="Regular;21" halign="center" valign="center" backgroundColor="#25062748" transparent="1"/>
	</screen>"""


	def __init__(self, session):
		Screen.__init__(self, session)
		HelpableScreen.__init__(self)
		
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

	def buildInterfaceList(self,device,description,type ):
		divpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/div-h.png"))
		activepng = None
		devicepng = None
		enabled = iInputDevices.getDeviceAttribute(device, 'enabled')

		if type == 'remote':
			if config.misc.rcused.value == 0:
				if enabled:
					devicepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/input_rcnew-configured.png"))
				else:
					devicepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/input_rcnew.png"))
			else:
				if enabled:
					devicepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/input_rcold-configured.png"))
				else:
					devicepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/input_rcold.png"))
		elif type == 'keyboard':
			if enabled:
				devicepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/input_keyboard-configured.png"))
			else:
				devicepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/input_keyboard.png"))
		elif type == 'mouse':
			if enabled:
				devicepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/input_mouse-configured.png"))
			else:
				devicepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/input_mouse.png"))
		else:
			devicepng = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/input_rcnew.png"))
		return((device, description, devicepng, divpng))	

	def updateList(self):
		self.list = []
		for x in self.devices:
			dev_type = iInputDevices.getDeviceAttribute(x[1], 'type')
			self.list.append(self.buildInterfaceList(x[1],_(x[0]), dev_type ))
		self["list"].setList(self.list)
		self["list"].setIndex(self.currentIndex)

	def okbuttonClick(self):
		selection = self["list"].getCurrent()
		self.currentIndex = self["list"].getIndex()
		if selection is not None:
			self.session.openWithCallback(self.DeviceSetupClosed, InputDeviceSetup, selection[0])

	def DeviceSetupClosed(self, *ret):
		self.updateList()


class InputDeviceSetup(Screen, ConfigListScreen):

	skin = """
		<screen name="InputDeviceSetup" position="center,center" size="560,440" title="Input device setup">
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
		devicenames = [_("dreambox front panel"),_("dreambox front panel"),_("dreambox remote control (native)"),_("dreambox advanced remote control (native)"),_("dreambox ir keyboard"),_("dreambox ir mouse")]

		self.createSetup()
		self.onLayoutFinish.append(self.layoutFinished)
		self.onClose.append(self.cleanup)

	def layoutFinished(self):
		self.setTitle(self.setup_title)

	def cleanup(self):
		iInputDevices.currentDevice = ""

	def createSetup(self):
		self.list = [ ]
		string = _("Change repeat and delay settings?")
		cmd = "self.enableEntry = getConfigListEntry(string, config.inputDevices." + self.inputDevice + ".enabled)"
		exec (cmd)
		string = _("Interval between keys when repeating:")
		cmd = "self.repeatEntry = getConfigListEntry(string, config.inputDevices." + self.inputDevice + ".repeat)"
		exec (cmd)
		string = _("Delay before key repeat starts:")
		cmd = "self.delayEntry = getConfigListEntry(string, config.inputDevices." + self.inputDevice + ".delay)"
		exec (cmd)
		string = _("Devicename:")
		cmd = "self.nameEntry = getConfigListEntry(string, config.inputDevices." + self.inputDevice + ".name)"
		exec (cmd)
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
		self["config"].l.setSeperation(400)
		self["config"].l.setList(self.list)
		if not self.selectionChanged in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def selectionChanged(self):
		if self["config"].getCurrent() == self.enableEntry:
			self["introduction"].setText(_("Current device: ") + _(str(iInputDevices.getDeviceAttribute(self.inputDevice, 'name'))))
		else:
			self["introduction"].setText(_("Current value: ") + self.getCurrentValue() + _(" ms"))

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
			exec (cmd)
			self.keySave()

	def apply(self):
		self.session.openWithCallback(self.confirm, MessageBox, _("Use this input device settings?"), MessageBox.TYPE_YESNO, timeout = 20, default = True)

	def cancelConfirm(self, result):
		if not result:
			return
		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def keyCancel(self):
		if self["config"].isChanged():
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"), MessageBox.TYPE_YESNO, timeout = 20, default = True)
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
