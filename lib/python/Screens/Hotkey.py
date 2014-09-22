from Components.ActionMap import ActionMap
from Components.Button import Button
from Components.ChoiceList import ChoiceList, ChoiceEntryComponent
from Components.SystemInfo import SystemInfo
from Components.config import config, ConfigSubsection, ConfigText, ConfigYesNo
from Components.PluginComponent import plugins
from Screens.ChoiceBox import ChoiceBox
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Plugins.Plugin import PluginDescriptor

hotkeys = [(_("Red long"), "red_long", ""),
	(_("Green long"), "green_long", ""),
	(_("Yellow long"), "yellow_long", ""),
	(_("Blue long"), "blue_long", "Plugins/PLi/SoftcamSetup"),
	(_("F1"), "f1", ""),
	(_("F1 long"), "f1_long", ""),
	(_("F2"), "f2", ""),
	(_("F2 long"), "f2_long", ""),
	(_("F3"), "f3", ""),
	(_("F3 long"), "f3_long", ""),
	(_("Red"), "red", ""),
	(_("Green"), "green", ""),
	(_("Yellow"), "yellow", ""),
	(_("Blue"), "blue", ""),
	(_("PVR"), "pvr", ""),
	(_("Radio"), "radio", ""),
	(_("TV"), "showTv", ""),
	(_("Teletext"), "text", ""),
	(_("Help"), "displayHelp", ""),
	(_("Subtitle"), "subtitle", ""),
	(_("Menu"), "mainMenu", ""),
	(_("Info"), "info", ""),
	(_("Info Long"), "info_long", ""),
	(_("List"), "list", ""),
	(_("Back"), "back", ""),
	(_("End"), "end", ""),
	(_("Epg"), "epg", ""),
	(_("Epg long"), "epg_long", ""),
	(_("Left"), "cross_left", ""),
	(_("Right"), "cross_right", ""),
	(_("Up"), "cross_up", ""),
	(_("Down"), "cross_down", ""),
	(_("Channel up"), "channelup", ""),
	(_("Channel down"), "channeldown", ""),
	(_("Next"), "next", ""),
	(_("Previous"), "previous", ""),
	(_("Audio"), "audio", ""),
	(_("Play"), "play", ""),
	(_("Stop"), "stop", ""),
	(_("Pause"), "pause", ""),
	(_("Rewind"), "rewind", ""),
	(_("Fastforward"), "fastforward", ""),
	(_("Rewind"), "rewind", ""),
	(_("activatePiP"), "activatePiP", ""),
	(_("Timer"), "timer", ""),
	(_("Portal"), "portal", ""),
	(_("Playlist"), "playlist", ""),
	(_("Timeshift"), "timeshift", ""),
	(_("Search"), "search", ""),
	(_("Slow"), "slow", ""),
	(_("Mark"), "mark", "")]

config.misc.hotkey = ConfigSubsection()
config.misc.hotkey.additional_keys = ConfigYesNo(default=False)
for x in hotkeys:
	exec "config.misc.hotkey." + x[1] + " = ConfigText(default='" + x[2] + "')"

def getHotkeyFunctionsList():
	hotkeyFunctions = []
	twinPlugins = []
	pluginlist = plugins.getPlugins([PluginDescriptor.WHERE_PLUGINMENU ,PluginDescriptor.WHERE_EXTENSIONSMENU, PluginDescriptor.WHERE_EVENTINFO])
	pluginlist.sort(key=lambda p: p.name)
	for plugin in pluginlist:
		if plugin.name not in twinPlugins:
			hotkeyFunctions.append((plugin.name, plugin.path[24:]))
			twinPlugins.append(plugin.name)
	hotkeyFunctions.append(("--", "--"))
	hotkeyFunctions.append((_("mainMenu"), "Infobar/mainMenu"))
	hotkeyFunctions.append((_("showHelp"), "Infobar/showHelp"))
	hotkeyFunctions.append((_("showExtensionSelection"), "Infobar/showExtensionSelection"))
	hotkeyFunctions.append((_("zapDown"), "Infobar/zapDown"))
	hotkeyFunctions.append((_("zapUp"), "Infobar/zapUp"))
	hotkeyFunctions.append((_("switchChannelUp"), "Infobar/switchChannelUp"))
	hotkeyFunctions.append((_("switchChannelDown"), "Infobar/switchChannelDown"))
	hotkeyFunctions.append((_("openServiceList"), "Infobar/openServiceList"))
	hotkeyFunctions.append((_("historyBack"), "Infobar/historyBack"))
	hotkeyFunctions.append((_("historyNext"), "Infobar/historyNext"))
	hotkeyFunctions.append((_("showEventInfoPlugins"), "Infobar/showEventInfoPlugins"))
	hotkeyFunctions.append((_("openEventView"), "Infobar/openEventView"))
	hotkeyFunctions.append((_("openSingleServiceEPG"), "Infobar/openSingleServiceEPG"))
	hotkeyFunctions.append((_("openMultiServiceEPG"), "Infobar/openMultiServiceEPG"))
	hotkeyFunctions.append((_("audioSelection"), "Infobar/audioSelection"))
	hotkeyFunctions.append((_("showRadio"), "Infobar/showRadio"))
	hotkeyFunctions.append((_("showTv"), "Infobar/showTv"))
	hotkeyFunctions.append((_("showMovies"), "Infobar/showMovies"))
	hotkeyFunctions.append((_("instantRecord"), "Infobar/instantRecord"))
	hotkeyFunctions.append((_("startInstantRecording"), "Infobar/startInstantRecording"))
	hotkeyFunctions.append((_("activateTimeshiftEnd"), "Infobar/activateTimeshiftEnd"))
	hotkeyFunctions.append((_("activateTimeshiftEndAndPause"), "Infobar/activateTimeshiftEndAndPause"))
	hotkeyFunctions.append((_("startTimeshift"), "Infobar/startTimeshift"))
	hotkeyFunctions.append((_("stopTimeshift"), "Infobar/stopTimeshift"))
	hotkeyFunctions.append((_("startTeletext"), "Infobar/startTeletext"))
	hotkeyFunctions.append((_("subserviceSelection"), "Infobar/subserviceSelection"))
	hotkeyFunctions.append((_("subtitleSelection"), "Infobar/subtitleSelection"))
	hotkeyFunctions.append((_("show/hide infoBar"), "Infobar/toggleShow"))
	hotkeyFunctions.append((_("Letterbox zoom"), "Infobar/vmodeSelection"))
	if SystemInfo["PIPAvailable"]:
		hotkeyFunctions.append((_("showPiP"), "Infobar/showPiP"))
		hotkeyFunctions.append((_("swapPiP"), "Infobar/swapPiP"))
		hotkeyFunctions.append((_("movePiP"), "Infobar/movePiP"))
		hotkeyFunctions.append((_("togglePipzap"), "Infobar/togglePipzap"))
	hotkeyFunctions.append(("--", "--"))
	hotkeyFunctions.append((_("HotKey Setup"), "Module/Screens.Hotkey/HotkeySetup"))
	hotkeyFunctions.append((_("CI (Common Interface) Setup"), "Module/Screens.Ci/CiSelection"))
	hotkeyFunctions.append((_("Tuner Configuration"), "Module/Screens.Satconfig/NimSelection"))
	hotkeyFunctions.append((_("Manual Scan"), "Module/Screens.ScanSetup/ScanSetup"))
	hotkeyFunctions.append((_("Automatic Scan"), "Module/Screens.ScanSetup/ScanSimple"))
	hotkeyFunctions.append((_("Network"), "Module/Screens.NetworkSetup/NetworkAdapterSelection"))
	hotkeyFunctions.append((_("Plugin Browser"), "Module/Screens.PluginBrowser/PluginBrowser"))
	hotkeyFunctions.append((_("Sleeptimer"), "Module/Screens.SleepTimerEdit/SleepTimerEdit"))
	hotkeyFunctions.append((_("Channel Info"), "Module/Screens.ServiceInfo/ServiceInfo"))
	hotkeyFunctions.append((_("Timer"), "Module/Screens.TimerEdit/TimerEditList"))
	hotkeyFunctions.append((_("SkinSelector"), "Module/Plugins.SystemPlugins.SkinSelector.plugin/SkinSelector"))
	hotkeyFunctions.append((_("Sleeptimer edit"), "Module/Screens.SleepTimerEdit/SleepTimerEdit"))
	hotkeyFunctions.append((_("Standby"), "Module/Screens.Standby/Standby"))
	hotkeyFunctions.append((_("Restart"), "Module/Screens.Standby/TryQuitMainloop/2"))
	hotkeyFunctions.append((_("Restart enigma"), "Module/Screens.Standby/TryQuitMainloop/3"))
	hotkeyFunctions.append((_("Deep standby"), "Module/Screens.Standby/TryQuitMainloop/1"))
	hotkeyFunctions.append(("--", "--"))
	hotkeyFunctions.append((_("Usage Setup"), "Setup/usage"))
	hotkeyFunctions.append((_("Recording Setup"), "Setup/recording"))
	hotkeyFunctions.append((_("Harddisk Setup"), "Setup/harddisk"))
	hotkeyFunctions.append((_("Subtitles Settings"), "Setup/subtitlesetup"))
	return hotkeyFunctions

class HotkeySetup(Screen):
	def __init__(self, session, args=None):
		Screen.__init__(self, session)
		self.session = session
		self.setTitle(_("Hotkey Setup"))
		self["key_red"] = Button(_("Exit"))
		self["key_green"] = Button(_("Toggle Extra Keys"))
		self.list = []
		for x in hotkeys:
			self.list.append(ChoiceEntryComponent('',((x[0]), x[1])))
		self["list"] = ChoiceList(list=self.list[:config.misc.hotkey.additional_keys.value and len(hotkeys) - 1 or 10], selection = 0)
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
		{
			"ok": self.ok,
			"cancel": self.close,
			"red": self.close,
			"green": self.toggleAdditionalKeys
		}, -1)

	def ok(self):
		self.session.open(HotkeySetupSelect, self["list"].l.getCurrentSelection())

	def toggleAdditionalKeys(self):
		config.misc.hotkey.additional_keys.value = not config.misc.hotkey.additional_keys.value
		config.misc.hotkey.additional_keys.save()
		self["list"].setList(self.list[:config.misc.hotkey.additional_keys.value and len(hotkeys) - 1 or 10])

class HotkeySetupSelect(Screen):
	def __init__(self, session, key, args=None):
		Screen.__init__(self, session)
		self.session = session
		self.setTitle(_("Hotkey Setup") + " " + key[0][0])
		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("Save"))
		self.mode = "list"
		self.selected = []
		self.list = []
		self.config = eval("config.misc.hotkey." + key[0][1])
		selected = self.config.value.split(',')
		for plugin in getHotkeyFunctionsList():
			self.list.append(ChoiceEntryComponent('',((plugin[0]), plugin[1])))
			if plugin[1] in selected:
				self.selected.append(ChoiceEntryComponent('',((plugin[0]), plugin[1])))
		self.prevselected = self.selected[:]
		self["choosen"] = ChoiceList(list=self.selected, selection=0)
		self["list"] = ChoiceList(list=self.list, selection=0)
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "KeyboardInputActions"], 
		{
			"ok": self.keyOk,
			"cancel": self.cancel,
			"red": self.cancel,
			"green": self.save,
			"up": self.keyUp,
			"down": self.keyDown,
			"left": self.keyLeft,
			"right": self.keyRight,
			"pageUp": self.toggleMode,
			"pageDown": self.toggleMode
		}, -1)
		self.onLayoutFinish.append(self.__layoutFinished)

	def __layoutFinished(self):
		self["choosen"].selectionEnabled(0)

	def toggleMode(self):
		if self.mode == "list" and self.selected:
			self.mode = "choosen"
			self["choosen"].selectionEnabled(1)
			self["list"].selectionEnabled(0)
		elif self.mode == "choosen":
			self.mode = "list"
			self["choosen"].selectionEnabled(0)
			self["list"].selectionEnabled(1)

	def keyOk(self):
		if self.mode == "list":
			currentSelected = self["list"].l.getCurrentSelection()
			if currentSelected in self.selected:
				self.selected.remove(currentSelected)
			else:
				self.selected.append(currentSelected)
		elif self.selected:
			self.selected.remove(self["choosen"].l.getCurrentSelection())
			if not self.selected:
				self.toggleMode()
		self["choosen"].setList(self.selected)

	def keyLeft(self):
		if self.mode == "list":
			self["list"].instance.moveSelection(self["list"].instance.pageUp)
			if self["list"].l.getCurrentSelection()[0][0] == "--":
				self.keyUp()
		else:
			self["choosen"].instance.moveSelection(self["list"].instance.pageUp)

	def keyRight(self):
		if self.mode == "list":
			self["list"].instance.moveSelection(self["list"].instance.pageDown)
			if self["list"].l.getCurrentSelection()[0][0] == "--":
				self.keyDown()
		else:
			self["choosen"].instance.moveSelection(self["list"].instance.pageDown)

	def keyUp(self):
		if self.mode == "list":
			self["list"].instance.moveSelection(self["list"].instance.moveUp)
			if self["list"].l.getCurrentSelection()[0][0] == "--":
				self.keyUp()
		else:
			self["choosen"].instance.moveSelection(self["list"].instance.moveUp)

	def keyDown(self):
		if self.mode == "list":
			self["list"].instance.moveSelection(self["list"].instance.moveDown)
			if self["list"].l.getCurrentSelection()[0][0] == "--":
				self.keyDown()
		else:
			self["choosen"].instance.moveSelection(self["list"].instance.moveDown)

	def save(self):
		configValue = []
		for x in self.selected:
			configValue.append(x[0][1])
		self.config.value = ",".join(configValue)
		self.config.save()
		self.close()

	def cancel(self):
		if self.selected != self.prevselected:
			self.session.openWithCallback(self.cancelCallback, MessageBox, "are you sure to cancel all changes", default=False)
		else:
			self.close()

	def cancelCallback(self, answer):
		answer and self.close()

class hotkeyActionMap(ActionMap):
	def action(self, contexts, action):
		if (action in tuple(x[1] for x in hotkeys) and self.actions.has_key(action)):
			res = self.actions[action](action)
			if res is not None:
				return res
			return 1
		else:
			return ActionMap.action(self, contexts, action)

class InfoBarHotkey():
	def __init__(self):
		self["HotkeyButtonActions"] = hotkeyActionMap(["HotkeyActions"], dict((x[1], self.hotkeyGlobal) for x in hotkeys), -10)

	def hotkeyGlobal(self, key):
		selection = eval("config.misc.hotkey." + key + ".value.split(',')")
		if selection:
			selected = []
			for x in selection:
				plugin = list(plugin for plugin in getHotkeyFunctionsList() if plugin[1] == x )
				if plugin:
					selected.append(plugin[0])
			if not selected:
				return 0
			if len(selected) == 1:
				self.execHotkey(selected[0])
			else:
				key = tuple(x[0] for x in hotkeys if x[1] == key)[0]
				self.session.openWithCallback(self.execHotkey, ChoiceBox, _("Hotkey") + " " + key, selected)

	def execHotkey(self, selected):
		if selected:
			selected = selected[1].split("/")
			if selected[0] == "Plugins":
				for plugin in plugins.getPlugins([PluginDescriptor.WHERE_PLUGINMENU ,PluginDescriptor.WHERE_EXTENSIONSMENU, PluginDescriptor.WHERE_EVENTINFO]):
					if plugin.path[24:] == "/".join(selected):
						self.runPlugin(plugin)
			elif selected[0] == "Infobar" or selected[0] == "Code":
				if hasattr(self, selected[1]):
					exec "self." + selected[1] + "()"
			elif selected[0] == "Module":
				try:
					exec "from " + selected[1] + " import *"
					exec "self.session.open(" + ",".join(selected[2:]) + ")"
				except:
					print "[Hotkey] error during executing module %s, screen %s" % (selected[1], selected[2])
			elif selected[0] == "Setup":
				from Screens.Setup import *
				exec "self.session.open(Setup, \"" + selected[1] + "\")"
