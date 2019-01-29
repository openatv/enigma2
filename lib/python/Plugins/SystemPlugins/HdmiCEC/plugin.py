from boxbranding import getMachineBrand, getMachineName
from os import path

from Screens.Screen import Screen
from Components.ConfigList import ConfigListScreen
from Components.config import config, configfile, getConfigListEntry
from Components.Sources.StaticText import StaticText
from Components.Label import Label

from Tools.Directories import fileExists

if path.exists("/dev/hdmi_cec") or path.exists("/dev/misc/hdmi_cec0"):
	import Components.HdmiCec

class HdmiCECSetupScreen(Screen, ConfigListScreen):
	skin = """
	<screen position="c-300,c-250" size="600,500" title="HDMI CEC setup">
		<widget name="config" position="15,15" size="720,350" scrollbarMode="showOnDemand"/>
		<widget name="description" position="15,375" size="720,90" font="Regular;19" halign="center" valign="center" />
		<widget source="current_address" render="Label" position="15,475" size="550,30" zPosition="10" font="Regular;21" halign="left" valign="center" />
		<widget source="fixed_address" render="Label" position="15,505" size="550,30" zPosition="10" font="Regular;21" halign="left" valign="center" />
		<ePixmap pixmap="buttons/red.png" position="20,e-45" size="140,40" alphatest="on" />
		<ePixmap pixmap="buttons/green.png" position="160,e-45" size="140,40" alphatest="on" />
		<ePixmap pixmap="buttons/yellow.png" position="300,e-45" size="140,40" alphatest="on" />
		<ePixmap pixmap="buttons/blue.png" position="440,e-45" size="140,40" alphatest="on" />
		<widget source="key_red" render="Label" position="20,e-45" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" />
		<widget source="key_green" render="Label" position="160,e-45" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" />
		<widget source="key_yellow" render="Label" position="300,e-45" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" />
		<widget source="key_blue" render="Label" position="440,e-45" zPosition="1" size="140,40" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" />
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		Screen.setTitle(self, _("HDMI CEC Setup"))

		from Components.ActionMap import ActionMap

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("OK"))
		self["key_yellow"] = StaticText(_("Set fixed"))
		self["key_blue"] = StaticText(_("Clear fixed"))
		self["current_address"] = StaticText()
		self["fixed_address"] = StaticText()
		self["description"] = Label()

		self["actions"] = ActionMap(["SetupActions", "ColorActions", "MenuActions"],
		{
			"ok": self.keyGo,
			"save": self.keyGo,
			#"cancel": self.keyCancel,
			"cancel": self.closeRecursive,
			"green": self.keyGo,
			#"red": self.keyCancel,
			"red": self.closeRecursive,
			"yellow": self.setFixedAddress,
			"blue": self.clearFixedAddress,
			"menu": self.closeRecursive,
			"up": self.keyUp,
			"down": self.keyDown,
		}, -2)

		self.onChangedEntry = [ ]
		self.list = []
		ConfigListScreen.__init__(self, self.list, session = self.session, on_change = self.changedEntry)
		self.createSetup()

	def createSetup(self):
		self.list = []
		self.list.append(getConfigListEntry(_("Enabled"), config.hdmicec.enabled, _('helptext'), 'refreshlist'))
		if config.hdmicec.enabled.value:
			tab = ' ' * 10
			self.list.append(getConfigListEntry(_("Advanced Settings"), config.hdmicec.advanced_settings, _('helptext'), 'refreshlist'))
			if config.hdmicec.advanced_settings.value:
				self.list.append(getConfigListEntry(_("Load Default Settings"), config.hdmicec.default_settings, _('helptext'), 'refreshlist'))
			self.list.append(getConfigListEntry(_("Regard deep standby as standby"), config.hdmicec.handle_deepstandby_events, _('helptext'),'refreshlist'))
			if config.hdmicec.advanced_settings.value and config.hdmicec.handle_deepstandby_events.value and config.workaround.deeprecord.value:
				self.list.append(getConfigListEntry(tab + _("Wait for timesync at startup"), config.hdmicec.deepstandby_waitfortimesync, _("If the 'deep standby workaround' is enabled, it waits until the system time is syncronised. Depending on the requirement, the devices wake up will continuing after a maximum of 2 minutes."), ))
			self.list.append(getConfigListEntry(_("Put TV in standby"), config.hdmicec.control_tv_standby, _('helptext'),'refreshlist'))
			if config.hdmicec.advanced_settings.value and config.hdmicec.control_tv_standby.value:
				self.list.append(getConfigListEntry(tab + _("Even if TV has another input active?"), config.hdmicec.tv_standby_notinputactive, _('You can skip this function and turn off the TV when you wake the receiver from standby and immediately switch back to standby.'), ))
			self.list.append(getConfigListEntry(_("Wakeup TV from standby"), config.hdmicec.control_tv_wakeup, _('helptext') ,'refreshlist'))
			if config.hdmicec.advanced_settings.value and config.hdmicec.control_tv_wakeup.value:
				self.list.append(getConfigListEntry(tab + _("Even if a 'zap' recording timer starting?"), config.hdmicec.tv_wakeup_zaptimer, _('helptext'), ))
				self.list.append(getConfigListEntry(tab + _("Even if a 'zap and record' recording timer starting?"), config.hdmicec.tv_wakeup_zapandrecordtimer, _('helptext'), ))
				self.list.append(getConfigListEntry(tab + _("Even if a 'wakeup' power timer starting?"), config.hdmicec.tv_wakeup_wakeuppowertimer, _('helptext'), ))
			self.list.append(getConfigListEntry(_("Switch TV to correct input"), config.hdmicec.report_active_source, _('helptext'),'refreshlist'))
			if config.hdmicec.advanced_settings.value and config.hdmicec.report_active_source.value:
				self.list.append(getConfigListEntry(tab + _("Switch off the TV to correct input"), config.hdmicec.workaround_activesource, _("Some TV devices can't swich to correct input if a another hdmi port active. This setting set the TV to standby before.\n(If the TV does not turn back on, may require a slower transmission interval or the repetition of wake-up commands.)"),))
			self.list.append(getConfigListEntry(_("Handle wakeup from TV"), config.hdmicec.handle_tv_wakeup, _('Choose a setting where your receiver wakes up from standby.'),))
			self.list.append(getConfigListEntry(_("Handle standby from TV"), config.hdmicec.handle_tv_standby, _('helptext'),'refreshlist'))
			if config.hdmicec.advanced_settings.value: 
				self.list.append(getConfigListEntry(_("Handle input from TV"), config.hdmicec.handle_tv_input, _('helptext'),'refreshlist'))
				if config.hdmicec.handle_tv_standby.value != 'disabled' or config.hdmicec.handle_tv_input.value != 'disabled':
					self.list.append(getConfigListEntry(_("Time delay until standby or deep standby"), config.hdmicec.handle_tv_delaytime, _("'Handle standby from TV' has a higher priority as 'Handle input from TV'"),))
			self.list.append(getConfigListEntry(_("Forward volume keys"), config.hdmicec.volume_forwarding, _('Activation takes place immediately. If this feature is not supported, the volume keys has no function!'),))
			self.list.append(getConfigListEntry(_("Put your AV Receiver in standby"), config.hdmicec.control_receiver_standby, _('helptext'),))
			self.list.append(getConfigListEntry(_("Wakeup your AV Receiver from standby"), config.hdmicec.control_receiver_wakeup, _('helptext'),))
			self.list.append(getConfigListEntry(_("Use TV remote control"), config.hdmicec.report_active_menu, _('Activation takes place immediately. If it does feature not work, then try again with a slower send interval.'),))
			self.list.append(getConfigListEntry(_("Minimum send interval"), config.hdmicec.minimum_send_interval, _('Try to slow down the send interval if not all commands are executed.'), ))
			if config.hdmicec.advanced_settings.value: 
				self.list.append(getConfigListEntry(_("Repeat the sent standby and wakeup commands"), config.hdmicec.messages_repeat, _('Try to send repeated commands if not all commands are executed.\n') + _('(e.g. TV wakeup, but not switched to correct input)'),'refreshlist'))
				if int(config.hdmicec.messages_repeat.value):
					self.list.append(getConfigListEntry(tab + _("Time delay for the repeated transmission"), config.hdmicec.messages_repeat_slowdown, _('The time is multiplied by the current repeat counter.'), ))
					self.list.append(getConfigListEntry(tab + _("Repeat the standby commands?"), config.hdmicec.messages_repeat_standby, _('Is not necessary in most cases.'),'refreshlist'))
				self.list.append(getConfigListEntry(_("Check power and input state from TV"), config.hdmicec.check_tv_state, _('An attempt is made to capture the current TV status. If this is not possible due to incorrect or missing status messages, it may cause the receiver to respond unexpectedly.\nOn the other hand, tries to respond better to different operating conditions.'), ))
				self.list.append(getConfigListEntry(_("Ignore unexpectedly wakeup and stay in standby"), config.hdmicec.workaround_turnbackon, _("This is a workaround for some devices there wakeup again after switching in standby. The wak up command's from other devices will ignored for few seconds."),))
				if fileExists("/proc/stb/hdmi/preemphasis"):
					self.list.append(getConfigListEntry(_("Use HDMI-preemphasis"), config.hdmicec.preemphasis, _('With this setting, you can probably improve the signal quality or eliminate problems that can occur with longer HDMI cables.'),))

		self["config"].list = self.list
		self["config"].l.setList(self.list)

		self.updateAddress()
		self.showHelpText()

	# for summary:
	def changedEntry(self):
		cur = self["config"].getCurrent()
		if cur and (len(cur) > 2 and cur[2] == 'refreshlist' or len(cur) > 3 and cur[3] == 'refreshlist'):
			if config.hdmicec.default_settings.value:
				for x in self["config"].list:
					if x[0] == _("Enabled"):
						continue
					x[1].setValue(x[1].default)
					x[1].save()
				self.keyUp()
			self.createSetup()
		for x in self.onChangedEntry:
			x()

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)

	def keyRight(self):
		ConfigListScreen.keyRight(self)

	def keyDown(self):
		self["config"].moveDown()
		self.showHelpText()

	def keyUp(self):
		self["config"].moveUp()
		self.showHelpText()

	def keyGo(self):
		for x in self["config"].list:
			x[1].save()
		configfile.save()
		self.close()

	def keyCancel(self):
		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def setFixedAddress(self):
		Components.HdmiCec.hdmi_cec.setFixedPhysicalAddress(Components.HdmiCec.hdmi_cec.getPhysicalAddress())
		self.updateAddress()

	def clearFixedAddress(self):
		Components.HdmiCec.hdmi_cec.setFixedPhysicalAddress("0.0.0.0")
		self.updateAddress()

	def updateAddress(self):
		self["current_address"].setText(_("Current CEC address") + ": " + Components.HdmiCec.hdmi_cec.getPhysicalAddress())
		if config.hdmicec.fixed_physical_address.value == "0.0.0.0":
			fixedaddresslabel = ""
		else:
			fixedaddresslabel = _("Using fixed address") + ": " + config.hdmicec.fixed_physical_address.value
		self["fixed_address"].setText(fixedaddresslabel)

	def showHelpText(self):
		cur = self["config"].getCurrent()
		if cur and len(cur) > 2 and not cur[2] in ('refreshlist', _('helptext')):
			self["description"].setText(cur[2])
		elif cur and len(cur) > 3 and not cur[3] in ('refreshlist', _('helptext')):
			self["description"].setText(cur[3])
		else:
			self["description"].setText(" ")

def Plugins(**kwargs):
	return []
