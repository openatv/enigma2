from Components.ActionMap import ActionMap
from Components.config import config, configfile, getConfigListEntry, ConfigSubList, ConfigSubsection
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.Sources.StaticText import StaticText
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Screens.Standby import TryQuitMainloop

class ClientModeScreen(ConfigListScreen, Screen):
	def __init__(self, session, menu_path=""):
		Screen.__init__(self, session)
		self.setup_title = screentitle = _("Client mode")
		try:
			if config.usage.show_menupath.value == 'large':
				menu_path += screentitle
				title = menu_path
				self["menu_path_compressed"] = StaticText("")
			elif config.usage.show_menupath.value == 'small':
				title = screentitle
				self["menu_path_compressed"] = StaticText(menu_path + " >" if not menu_path.endswith(' / ') else menu_path[:-3] + " >" or "")
			else:
				title = screentitle
				self["menu_path_compressed"] = StaticText("")
		except: # for start wizard
			title = screentitle
			self["menu_path_compressed"] = StaticText("")
		Screen.setTitle(self, title)
		self.skinName = ["ClientModeScreen", "Setup"]
		self.initial_state = config.clientmode.enabled.value
		self.onChangedEntry = []
		self.session = session
		ConfigListScreen.__init__(self, [], session = session, on_change = self.changedEntry)

		self["actions"] = ActionMap(["SetupActions", "MenuActions", "ColorActions"],
		{
			"ok": self.keyGo,
			"menu": self.keyCancel,
			"cancel": self.keyCancel,
			"save": self.keyGo,
		}, -2)

		self["key_red"] = StaticText(_("Exit"))
		self["key_green"] = StaticText(_("Save"))

		self["description"] = Label("")

		self.createSetup()

		if not self.selectionChanged in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def createSetup(self):
		setup_list = []
		setup_list.append(getConfigListEntry(_("Enable client mode"), config.clientmode.enabled,_('Client mode sets up this receiver to stream from another receiver. In this mode no local tuners will be available and channel lists, EPG, etc, will come from the remote receiver. All tuner settings will be cleared.')))
		if config.clientmode.enabled.value:
			setup_list.append(getConfigListEntry(_("Host receiver address type"), config.clientmode.serverAddressType,_('Select between entering an IP address or a domain.')))
			if config.clientmode.serverAddressType.value == "ip":
				setup_list.append(getConfigListEntry(_("Host receiver IP address"), config.clientmode.serverIP,_('Enter the IP address of the host receiver.')))
			else:
				setup_list.append(getConfigListEntry(_("Host domain"), config.clientmode.serverDomain,_("Enter the domain of the host receiver. Do not include 'http://' or port number.")))
			setup_list.append(getConfigListEntry(_("Host receiver streaming port"), config.clientmode.serverStreamingPort,_("Enter the streaming port of the host receiver (normally '8001').")))
			setup_list.append(getConfigListEntry(_("Host receiver FTP username"), config.clientmode.serverFTPusername,_("Enter the FTP username of the host receiver (normally 'root').")))
			setup_list.append(getConfigListEntry(_("Host receiver FTP password"), config.clientmode.serverFTPpassword,_("Enter the FTP password of the host receiver (normally just leave empty).")))
			setup_list.append(getConfigListEntry(_("Host receiver FTP port"), config.clientmode.serverFTPPort,_("Enter the FTP port of the host receiver (normally '21').")))
			setup_list.append(getConfigListEntry(_("FTP passive mode"), config.clientmode.passive,_("Should the FTP connection to the remote receiver be established in passive mode (normally 'no')?")))
			setup_list.append(getConfigListEntry(_("Schedule EPG and channel list import"), config.clientmode.enableSchedule,_("Allows you to set a schedule to import the EPG and channels list. The EPG and channels list will always be imported on reboot or GUI restart.")))
			if config.clientmode.enableSchedule.value:
				setup_list.append(getConfigListEntry(_("Repeat how often"), config.clientmode.scheduleRepeatInterval,_("Set the repeat interval of the schedule.")))
				if config.clientmode.scheduleRepeatInterval.value in ("daily",):
					setup_list.append(getConfigListEntry(_("Time import should start"), config.clientmode.scheduletime,_("Set the time of day to perform the import.")))

		self["config"].list = setup_list
		self["config"].l.setList(setup_list)

	def selectionChanged(self):
		self["description"].setText(self["config"].getCurrent()[2])

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

	def run(self): # for start wizard
		self.saveconfig()

	def keyGo(self):
		if config.clientmode.enabled.value and not self.checkFTPconnection():
			mbox = self.session.open(MessageBox, _("Connection using the supplied FTP parameters failed. Please recheck the details and try again."), MessageBox.TYPE_ERROR)
			mbox.setTitle(_("FTP connection failure"))
			return
		if self.initial_state != config.clientmode.enabled.value:
			restartbox = self.session.openWithCallback(self.restartGUI, MessageBox,_("GUI needs a restart to switch modes\nDo you want to restart the GUI now?"), MessageBox.TYPE_YESNO)
			restartbox.setTitle(_("Restart GUI now?"))
		else:
			self.saveconfig()
			self.close()

	def keyCancel(self):
		if self["config"].isChanged():
			self.session.openWithCallback(self.cancelCallback, MessageBox, _("Really close without saving settings?"))
		else:
			self.cancelCallback(True)

	def cancelCallback(self, answer):
		if answer:
			for x in self["config"].list:
				x[1].cancel()
			self.close(False)

	def saveconfig(self):
		nim_config_list = []
		if self.initial_state != config.clientmode.enabled.value and self.initial_state == False:  # switching to client mode
			# save normal mode config so it can be reinsated when returning to normal mode
			nim_config_list = []
			for x in config.Nims:
				nim_config_list.append(x.getSavedValue())
			import json
			config.clientmode.nim_cache.value = json.dumps(nim_config_list)
			config.clientmode.remote_fallback_enabled_cache.value = config.usage.remote_fallback_enabled.value
			config.clientmode.remote_fallback_cache.value = config.usage.remote_fallback.value
			config.clientmode.timer_sanity_check_enabled_cache.value = config.usage.timer_sanity_check_enabled.value
			# normal mode config values saved
		if config.clientmode.enabled.value:
			config.usage.remote_fallback_enabled.value = True
			config.usage.remote_fallback.value = "http://%s:%d" % (self.getRemoteAddress(), config.clientmode.serverStreamingPort.value)
			config.usage.timer_sanity_check_enabled.value = False
		elif self.initial_state != config.clientmode.enabled.value: # switching back to normal mode
			# load nim config from config.clientmode.nimcache
			import json
			nim_config_list = json.loads(config.clientmode.nim_cache.value)
			config.clientmode.nim_cache.value = ""
			config.Nims = ConfigSubList()
			for x in nim_config_list:
				tuner = ConfigSubsection()
				tuner.setSavedValue(x)
				config.Nims.append(tuner)
			config.Nims.save()
			# nim config loaded... but needs restart
			# reinstate normal mode values
			config.usage.remote_fallback_enabled.value = config.clientmode.remote_fallback_enabled_cache.value
			config.usage.remote_fallback.value = config.clientmode.remote_fallback_cache.value
			config.usage.timer_sanity_check_enabled.value = config.clientmode.timer_sanity_check_enabled_cache.value
			# reset some client mode settings
			config.clientmode.remote_fallback_enabled_cache.value = False
			config.clientmode.remote_fallback_cache.value = ""
			config.clientmode.timer_sanity_check_enabled_cache.value = True
		config.usage.save()
		config.clientmode.save()
		configfile.save()

	def getRemoteAddress(self):
		if config.clientmode.serverAddressType.value == "ip":
			return '%d.%d.%d.%d' % (config.clientmode.serverIP.value[0], config.clientmode.serverIP.value[1], config.clientmode.serverIP.value[2], config.clientmode.serverIP.value[3])
		else:
			return config.clientmode.serverDomain.value

	def checkFTPconnection(self):
		print "[ClientMode][checkFTPconnection] Testing FTP connection..."
		try:
			from ftplib import FTP
			ftp = FTP()
			ftp.set_pasv(config.clientmode.passive.value)
			ftp.connect(host=self.getRemoteAddress(), port=config.clientmode.serverFTPPort.value, timeout=5)
			result = ftp.login(user=config.clientmode.serverFTPusername.value, passwd=config.clientmode.serverFTPpassword.value)
			ftp.quit()
			if result.startswith("230"):
				print "[ClientMode][checkFTPconnection] FTP connection success:", result
				return True
			print "[ClientMode][checkFTPconnection] FTP connection failure:", result
			return False
		except Exception, err:
			print "[ChannelsImporter][checkFTPconnection] Error:", err
			return False

	def restartGUI(self, answer):
		if answer is True:
			self.saveconfig()
			self.session.open(TryQuitMainloop, 3)

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.createSetup()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.createSetup()
