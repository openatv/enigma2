from Components.ActionMap import ActionMap, HelpableActionMap, NumberActionMap
from Components.Button import Button
from Components.ChoiceList import ChoiceList, ChoiceEntryComponent
from Components.SystemInfo import SystemInfo
from Components.config import config, ConfigSubsection, ConfigText, ConfigYesNo
from Components.PluginComponent import plugins
from Screens.ChoiceBox import ChoiceBox
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Plugins.Plugin import PluginDescriptor
from Tools.BoundFunction import boundFunction
from ServiceReference import ServiceReference
from enigma import eServiceReference
import os

def getHotkeys():
	return [(_("Red") + " " + _("long"), "red_long", ""),
		(_("Green") + " " + _("long"), "green_long", ""),
		(_("Yellow") + " " + _("long"), "yellow_long", ""),
		(_("Blue") + " " + _("long"), "blue_long", "Plugins/PLi/SoftcamSetup/1"),
		("F1/LAN", "f1", ""),
		("F1" + " " + _("long"), "f1_long", ""),
		("F2", "f2", ""),
		("F2" + " " + _("long"), "f2_long", ""),
		("F3", "f3", ""),
		("F3" + " " + _("long"), "f3_long", ""),
		(_("Red"), "red", ""),
		(_("Green"), "green", ""),
		(_("Yellow"), "yellow", ""),
		(_("Blue"), "blue", ""),
		("Rec", "rec", ""),
		("Radio", "radio", ""),
		("TV", "showTv", ""),
		("Teletext", "text", ""),
		("Help", "displayHelp", ""),
		("Help" + " " + _("long"), "displayHelp_long", ""),
		("Subtitle", "subtitle", ""),
		("Menu", "mainMenu", ""),
		("Info (EPG)", "info", "Infobar/openEventView"),
		("Info (EPG)" + " " + _("long"), "info_long", "Infobar/showEventInfoPlugins"),
		("List/Fav/PVR", "list", ""),
		("Back/Recall", "back", ""),
		("Back/Recall" + " " + _("long"), "back_long", ""),
		("End", "end", ""),
		("Epg/Guide", "epg", "Plugins/Extensions/GraphMultiEPG/1"),
		("Epg/Guide" + " " + _("long"), "epg_long", "Infobar/showEventInfoPlugins"),
		("Left", "cross_left", ""),
		("Right", "cross_right", ""),
		("Up", "cross_up", ""),
		("Down", "cross_down", ""),
		("Ok", "ok", ""),
		("Channel up", "channelup", ""),
		("Channel down", "channeldown", ""),
		("Next", "next", ""),
		("Previous", "previous", ""),
		("Audio", "audio", ""),
		("Play", "play", ""),
		("Playpause", "playpause", ""),
		("Stop", "stop", ""),
		("Pause", "pause", ""),
		("Rewind", "rewind", ""),
		("Fastforward", "fastforward", ""),
		("Skip back", "skip_back", ""),
		("Skip forward", "skip_forward", ""),
		("activatePiP", "activatePiP", ""),
		("Timer", "timer", ""),
		("Timer" + " " + _("long"), "timer_long", ""),
		("Playlist", "playlist", ""),
		("Timeshift", "timeshift", ""),
		("Search", "search", ""),
		("Search" + " " + _("long"), "search_long", ""),
		("Slow", "slow", ""),
		("Mark/Portal/Playlist", "mark", ""),
		("Mark/Portal/Playlist" + " " + _("long"), "mark_long", ""),
		("Sleep", "sleep", ""),
		("Sleep" + " " + _("long"), "sleep_long", ""),
		("Context", "contextmenu", ""),
		("Context" + " " + _("long"), "contextmenu_long", ""),
		("Video Mode", "vmode", ""),
		("Video Mode" + " " + _("long"), "vmode_long", ""),
		("Home", "home", ""),
		("Power", "power", ""),
		("Power" + " " + _("long"), "power_long", ""),
		("HDMIin", "HDMIin", "Infobar/HDMIIn"),
		("HDMIin" + " " + _("long"), "HDMIin_long", SystemInfo["LcdLiveTV"] and "Infobar/ToggleLCDLiveTV" or "")]

config.misc.hotkey = ConfigSubsection()
config.misc.hotkey.additional_keys = ConfigYesNo(default=False)
for x in getHotkeys():
	exec "config.misc.hotkey." + x[1] + " = ConfigText(default='" + x[2] + "')"

def getHotkeyFunctions():
	hotkeyFunctions = []
	twinPlugins = []
	twinPaths = {}
	pluginlist = plugins.getPlugins(PluginDescriptor.WHERE_EVENTINFO)
	pluginlist.sort(key=lambda p: p.name)
	for plugin in pluginlist:
		if plugin.name not in twinPlugins and plugin.path and 'selectedevent' not in plugin.__call__.func_code.co_varnames:
			if twinPaths.has_key(plugin.path[24:]):
				twinPaths[plugin.path[24:]] += 1
			else:
				twinPaths[plugin.path[24:]] = 1
			hotkeyFunctions.append((plugin.name, plugin.path[24:] + "/" + str(twinPaths[plugin.path[24:]]) , "EPG"))
			twinPlugins.append(plugin.name)
	pluginlist = plugins.getPlugins([PluginDescriptor.WHERE_PLUGINMENU, PluginDescriptor.WHERE_EXTENSIONSMENU])
	pluginlist.sort(key=lambda p: p.name)
	for plugin in pluginlist:
		if plugin.name not in twinPlugins and plugin.path:
			if twinPaths.has_key(plugin.path[24:]):
				twinPaths[plugin.path[24:]] += 1
			else:
				twinPaths[plugin.path[24:]] = 1
			hotkeyFunctions.append((plugin.name, plugin.path[24:] + "/" + str(twinPaths[plugin.path[24:]]) , "Plugins"))
			twinPlugins.append(plugin.name)
	hotkeyFunctions.append((_("Main menu"), "Infobar/mainMenu", "InfoBar"))
	hotkeyFunctions.append((_("Show help"), "Infobar/showHelp", "InfoBar"))
	hotkeyFunctions.append((_("Show extension selection"), "Infobar/showExtensionSelection", "InfoBar"))
	hotkeyFunctions.append((_("Zap down"), "Infobar/zapDown", "InfoBar"))
	hotkeyFunctions.append((_("Zap up"), "Infobar/zapUp", "InfoBar"))
	hotkeyFunctions.append((_("Switch channel up"), "Infobar/switchChannelUp", "InfoBar"))
	hotkeyFunctions.append((_("Switch channel down"), "Infobar/switchChannelDown", "InfoBar"))
	hotkeyFunctions.append((_("Show service list"), "Infobar/openServiceList", "InfoBar"))
	hotkeyFunctions.append((_("Show movies"), "Infobar/showMovies", "InfoBar"))
	hotkeyFunctions.append((_("Show servicelist or movies"), "Infobar/showServiceListOrMovies", "InfoBar"))
	hotkeyFunctions.append((_("Show favourites list"), "Infobar/openFavouritesList", "InfoBar"))
	hotkeyFunctions.append((_("History back"), "Infobar/historyBack", "InfoBar"))
	hotkeyFunctions.append((_("History next"), "Infobar/historyNext", "InfoBar"))
	hotkeyFunctions.append((_("Recall to previous service"), "Infobar/servicelist/recallPrevService", "InfoBar"))
	hotkeyFunctions.append((_("Show eventinfo plugins"), "Infobar/showEventInfoPlugins", "EPG"))
	hotkeyFunctions.append((_("Show event details"), "Infobar/openEventView", "EPG"))
	hotkeyFunctions.append((_("Show single service EPG"), "Infobar/openSingleServiceEPG", "EPG"))
	hotkeyFunctions.append((_("Show multi channel EPG"), "Infobar/openMultiServiceEPG", "EPG"))
	hotkeyFunctions.append((_("Show Audioselection"), "Infobar/audioSelection", "InfoBar"))
	hotkeyFunctions.append((_("Switch to radio mode"), "Infobar/showRadio", "InfoBar"))
	hotkeyFunctions.append((_("Switch to TV mode"), "Infobar/showTv", "InfoBar"))
	hotkeyFunctions.append((_("Instant record"), "Infobar/instantRecord", "InfoBar"))
	hotkeyFunctions.append((_("Start instant recording"), "Infobar/startInstantRecording", "InfoBar"))
	hotkeyFunctions.append((_("Activate timeshift End"), "Infobar/activateTimeshiftEnd", "InfoBar"))
	hotkeyFunctions.append((_("Activate timeshift end and pause"), "Infobar/activateTimeshiftEndAndPause", "InfoBar"))
	hotkeyFunctions.append((_("Start timeshift"), "Infobar/startTimeshift", "InfoBar"))
	hotkeyFunctions.append((_("Stop timeshift"), "Infobar/stopTimeshift", "InfoBar"))
	hotkeyFunctions.append((_("Start teletext"), "Infobar/startTeletext", "InfoBar"))
	hotkeyFunctions.append((_("Show subservice selection"), "Infobar/subserviceSelection", "InfoBar"))
	hotkeyFunctions.append((_("Show subtitle selection"), "Infobar/subtitleSelection", "InfoBar"))
	hotkeyFunctions.append((_("Show InfoBar"), "Infobar/showFirstInfoBar", "InfoBar"))
	hotkeyFunctions.append((_("Show second InfoBar"), "Infobar/showSecondInfoBar", "InfoBar"))
	hotkeyFunctions.append((_("Toggle infoBar"), "Infobar/toggleShow", "InfoBar"))
	hotkeyFunctions.append((_("Letterbox zoom"), "Infobar/vmodeSelection", "InfoBar"))
	if SystemInfo["PIPAvailable"]:
		hotkeyFunctions.append((_("Show PIP"), "Infobar/showPiP", "InfoBar"))
		hotkeyFunctions.append((_("Swap PIP"), "Infobar/swapPiP", "InfoBar"))
		hotkeyFunctions.append((_("Move PIP"), "Infobar/movePiP", "InfoBar"))
		hotkeyFunctions.append((_("Toggle PIPzap"), "Infobar/togglePipzap", "InfoBar"))
	hotkeyFunctions.append((_("Activate HbbTV (Redbutton)"), "Infobar/activateRedButton", "InfoBar"))		
	hotkeyFunctions.append((_("Toggle HDMI In"), "Infobar/HDMIIn", "InfoBar"))
	if SystemInfo["LcdLiveTV"]:
		hotkeyFunctions.append((_("Toggle LCD LiveTV"), "Infobar/ToggleLCDLiveTV", "InfoBar"))
	hotkeyFunctions.append((_("HotKey Setup"), "Module/Screens.Hotkey/HotkeySetup", "Setup"))
	hotkeyFunctions.append((_("Software update"), "Module/Screens.SoftwareUpdate/UpdatePlugin", "Setup"))
	hotkeyFunctions.append((_("Latest Commits"), "Module/Screens.About/CommitInfo", "Setup"))
	hotkeyFunctions.append((_("CI (Common Interface) Setup"), "Module/Screens.Ci/CiSelection", "Setup"))
	hotkeyFunctions.append((_("Tuner Configuration"), "Module/Screens.Satconfig/NimSelection", "Scanning"))
	hotkeyFunctions.append((_("Manual Scan"), "Module/Screens.ScanSetup/ScanSetup", "Scanning"))
	hotkeyFunctions.append((_("Automatic Scan"), "Module/Screens.ScanSetup/ScanSimple", "Scanning"))
	for plugin in plugins.getPluginsForMenu("scan"):
		hotkeyFunctions.append((plugin[0], "MenuPlugin/scan/" + plugin[2], "Scanning"))
	hotkeyFunctions.append((_("Network"), "Module/Screens.NetworkSetup/NetworkAdapterSelection", "Setup"))
	hotkeyFunctions.append((_("Plugin Browser"), "Module/Screens.PluginBrowser/PluginBrowser", "Setup"))
	hotkeyFunctions.append((_("Sleeptimer edit"), "Module/Screens.SleepTimerEdit/SleepTimerEdit", "Setup"))
	hotkeyFunctions.append((_("Channel Info"), "Module/Screens.ServiceInfo/ServiceInfo", "Setup"))
	hotkeyFunctions.append((_("Timer"), "Module/Screens.TimerEdit/TimerEditList", "Setup"))
	for plugin in plugins.getPluginsForMenu("system"):
		if plugin[2]:
			hotkeyFunctions.append((plugin[0], "MenuPlugin/system/" + plugin[2], "Setup"))
	hotkeyFunctions.append((_("Standby"), "Module/Screens.Standby/Standby", "Power"))
	hotkeyFunctions.append((_("Restart"), "Module/Screens.Standby/TryQuitMainloop/2", "Power"))
	hotkeyFunctions.append((_("Restart enigma"), "Module/Screens.Standby/TryQuitMainloop/3", "Power"))
	hotkeyFunctions.append((_("Deep standby"), "Module/Screens.Standby/TryQuitMainloop/1", "Power"))
	hotkeyFunctions.append((_("Usage Setup"), "Setup/usage", "Setup"))
	hotkeyFunctions.append((_("User interface"), "Setup/userinterface", "Setup"))
	hotkeyFunctions.append((_("Recording Setup"), "Setup/recording", "Setup"))
	hotkeyFunctions.append((_("Harddisk Setup"), "Setup/harddisk", "Setup"))
	hotkeyFunctions.append((_("Subtitles Settings"), "Setup/subtitlesetup", "Setup"))
	hotkeyFunctions.append((_("Language"), "Module/Screens.LanguageSelection/LanguageSelection", "Setup"))
	hotkeyFunctions.append((_("Skin setup"), "Module/Screens.SkinSelector/SkinSelector", "Setup"))
	hotkeyFunctions.append((_("Memory Info"), "Module/Screens.About/MemoryInfo", "Setup"))
	if os.path.isdir("/etc/ppanels"):
		for x in [x for x in os.listdir("/etc/ppanels") if x.endswith(".xml")]:
			x = x[:-4]
			hotkeyFunctions.append((_("PPanel") + " " + x, "PPanel/" + x, "PPanels"))
	if os.path.isdir("/usr/script"):
		for x in [x for x in os.listdir("/usr/script") if x.endswith(".sh")]:
			x = x[:-3]
			hotkeyFunctions.append((_("Shellscript") + " " + x, "Shellscript/" + x, "Shellscripts"))
	return hotkeyFunctions

class HotkeySetup(Screen):
	def __init__(self, session, args=None):
		Screen.__init__(self, session)
		self.session = session
		self.setTitle(_("Hotkey Setup"))
		self["key_red"] = Button(_("Exit"))
		self["key_green"] = Button(_("Toggle Extra Keys"))
		self.list = []
		self.hotkeys = getHotkeys()
		self.hotkeyFunctions = getHotkeyFunctions()
		for x in self.hotkeys:
			self.list.append(ChoiceEntryComponent('',(x[0], x[1])))
		self["list"] = ChoiceList(list=self.list[:config.misc.hotkey.additional_keys.value and len(self.hotkeys) or 10], selection = 0)
		self["choosen"] = ChoiceList(list=[])
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "MenuActions"],
		{
			"ok": self.keyOk,
			"cancel": self.close,
			"red": self.close,
			"green": self.toggleAdditionalKeys,
			"up": self.keyUp,
			"down": self.keyDown,
			"left": self.keyLeft,
			"right": self.keyRight,
			"menu": boundFunction(self.close, True),
		}, -1)
		self["NumberActions"] = NumberActionMap(["NumberActions"],
		{
			"0": self.keyNumberGlobal
		})
		self["HotkeyButtonActions"] = hotkeyActionMap(["HotkeyActions"], dict((x[1], self.hotkeyGlobal) for x in self.hotkeys))
		self.longkeyPressed = False
		self.onLayoutFinish.append(self.__layoutFinished)
		self.onExecBegin.append(self.getFunctions)

	def __layoutFinished(self):
		self["choosen"].selectionEnabled(0)

	def hotkeyGlobal(self, key):
		if self.longkeyPressed:
			self.longkeyPressed = False
		else:
			index = 0
			for x in self.list[:config.misc.hotkey.additional_keys.value and len(self.hotkeys) or 10]:
				if key == x[0][1]:
					self["list"].moveToIndex(index)
					if key.endswith("_long"):
						self.longkeyPressed = True
					break
				index += 1
			self.getFunctions()

	def keyOk(self):
		self.session.openWithCallback(self.HotkeySetupSelectCallback, HotkeySetupSelect, self["list"].l.getCurrentSelection())

	def HotkeySetupSelectCallback(self, answer):
		if answer:
			self.close(True)

	def keyLeft(self):
		self["list"].instance.moveSelection(self["list"].instance.pageUp)
		self.getFunctions()

	def keyRight(self):
		self["list"].instance.moveSelection(self["list"].instance.pageDown)
		self.getFunctions()

	def keyUp(self):
		self["list"].instance.moveSelection(self["list"].instance.moveUp)
		self.getFunctions()

	def keyDown(self):
		self["list"].instance.moveSelection(self["list"].instance.moveDown)
		self.getFunctions()

	def setDefaultHotkey(self, answer):
		if answer:
			for x in getHotkeys():
				current_config = eval("config.misc.hotkey." + x[1])
				current_config.value = str(x[2])
				current_config.save()
			self.getFunctions()

	def keyNumberGlobal(self, number):
		self.session.openWithCallback(self.setDefaultHotkey, MessageBox, _("Set all hotkey to default?"), MessageBox.TYPE_YESNO)

	def toggleAdditionalKeys(self):
		config.misc.hotkey.additional_keys.value = not config.misc.hotkey.additional_keys.value
		config.misc.hotkey.additional_keys.save()
		self["list"].setList(self.list[:config.misc.hotkey.additional_keys.value and len(self.hotkeys) or 10])

	def getFunctions(self):
		key = self["list"].l.getCurrentSelection()[0][1]
		if key:
			selected = []
			for x in eval("config.misc.hotkey." + key + ".value.split(',')"):
				if x.startswith("ZapPanic"):
					selected.append(ChoiceEntryComponent('',((_("Panic to") + " " + ServiceReference(eServiceReference(x.split("/", 1)[1]).toString()).getServiceName()), x)))
				elif x.startswith("Zap"):
					selected.append(ChoiceEntryComponent('',((_("Zap to") + " " + ServiceReference(eServiceReference(x.split("/", 1)[1]).toString()).getServiceName()), x)))
				else:
					function = list(function for function in self.hotkeyFunctions if function[1] == x )
					if function:
						selected.append(ChoiceEntryComponent('',((function[0][0]), function[0][1])))
			self["choosen"].setList(selected)

class HotkeySetupSelect(Screen):
	def __init__(self, session, key, args=None):
		Screen.__init__(self, session)
		self.skinName="HotkeySetup"
		self.session = session
		self.key = key
		self.setTitle(_("Hotkey Setup") + " " + key[0][0])
		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("Save"))
		self.mode = "list"
		self.hotkeyFunctions = getHotkeyFunctions()
		self.config = eval("config.misc.hotkey." + key[0][1])
		self.expanded = []
		self.selected = []
		for x in self.config.value.split(','):
			if x.startswith("ZapPanic"):
				self.selected.append(ChoiceEntryComponent('',((_("Panic to") + " " + ServiceReference(eServiceReference(x.split("/", 1)[1]).toString()).getServiceName()), x)))
			elif x.startswith("Zap"):
				self.selected.append(ChoiceEntryComponent('',((_("Zap to") + " " + ServiceReference(eServiceReference(x.split("/", 1)[1]).toString()).getServiceName()), x)))
			else:
				function = list(function for function in self.hotkeyFunctions if function[1] == x )
				if function:
					self.selected.append(ChoiceEntryComponent('',((function[0][0]), function[0][1])))
		self.prevselected = self.selected[:]
		self["choosen"] = ChoiceList(list=self.selected, selection=0)
		self["list"] = ChoiceList(list=self.getFunctionList(), selection=0)
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "KeyboardInputActions", "MenuActions"], 
		{
			"ok": self.keyOk,
			"cancel": self.cancel,
			"red": self.cancel,
			"green": self.save,
			"up": self.keyUp,
			"down": self.keyDown,
			"left": self.keyLeft,
			"right": self.keyRight,
			"upRepeated": self.keyUp,
			"downRepeated": self.keyDown,
			"leftRepeated": self.keyLeft,
			"rightRepeated": self.keyRight,
			"pageUp": self.toggleMode,
			"pageDown": self.toggleMode,
			"moveUp": self.moveUp,
			"moveDown": self.moveDown,
			"menu": boundFunction(self.close, True),
		}, -1)
		self.onLayoutFinish.append(self.__layoutFinished)

	def __layoutFinished(self):
		self["choosen"].selectionEnabled(0)

	def getFunctionList(self):
		functionslist = []
		catagories = {}
		for function in self.hotkeyFunctions:
			if not catagories.has_key(function[2]):
				catagories[function[2]] = []
			catagories[function[2]].append(function)
		for catagorie in sorted(list(catagories)):
			if catagorie in self.expanded:
				functionslist.append(ChoiceEntryComponent('expanded',((catagorie), "Expander")))
				for function in catagories[catagorie]:
					functionslist.append(ChoiceEntryComponent('verticalline',((function[0]), function[1])))
				if catagorie == "InfoBar":
					functionslist.append(ChoiceEntryComponent('verticalline',((_("Zap to")), "Zap")))
					functionslist.append(ChoiceEntryComponent('verticalline',((_("Panic to")), "ZapPanic")))
			else:
				functionslist.append(ChoiceEntryComponent('expandable',((catagorie), "Expander")))
		return functionslist

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
			if currentSelected[0][1] == "Expander":
				if currentSelected[0][0] in self.expanded:
					self.expanded.remove(currentSelected[0][0])
				else:
					self.expanded.append(currentSelected[0][0])
				self["list"].setList(self.getFunctionList())
			else:
				if currentSelected[:2] in self.selected:
					self.selected.remove(currentSelected[:2])
				else:
					if currentSelected[0][1].startswith("ZapPanic"):
						from Screens.ChannelSelection import SimpleChannelSelection
						self.session.openWithCallback(self.zaptoCallback, SimpleChannelSelection, _("Hotkey Panic") + " " + self.key[0][0], currentBouquet=True)
					elif currentSelected[0][1].startswith("Zap"):
						from Screens.ChannelSelection import SimpleChannelSelection
						self.session.openWithCallback(self.zaptoCallback, SimpleChannelSelection, _("Hotkey zap") + " " + self.key[0][0], currentBouquet=True)
					else:
						self.selected.append(currentSelected[:2])
		elif self.selected:
			self.selected.remove(self["choosen"].l.getCurrentSelection())
			if not self.selected:
				self.toggleMode()
		self["choosen"].setList(self.selected)

	def zaptoCallback(self, *args):
		if args:
			currentSelected = self["list"].l.getCurrentSelection()[:]
			currentSelected[1]=currentSelected[1][:-1] + (currentSelected[0][0] + " " + ServiceReference(args[0]).getServiceName(),)
			self.selected.append([(currentSelected[0][0], currentSelected[0][1] + "/" + args[0].toString()), currentSelected[1]])

	def keyLeft(self):
		self[self.mode].instance.moveSelection(self[self.mode].instance.pageUp)

	def keyRight(self):
		self[self.mode].instance.moveSelection(self[self.mode].instance.pageDown)

	def keyUp(self):
		self[self.mode].instance.moveSelection(self[self.mode].instance.moveUp)

	def keyDown(self):
		self[self.mode].instance.moveSelection(self[self.mode].instance.moveDown)

	def moveUp(self):
		self.moveChoosen(self.keyUp)

	def moveDown(self):
		self.moveChoosen(self.keyDown)

	def moveChoosen(self, direction):
		if self.mode == "choosen":
			currentIndex = self["choosen"].getSelectionIndex()
			swapIndex = (currentIndex + (direction == self.keyDown and 1 or -1)) % len(self["choosen"].list)
			self["choosen"].list[currentIndex], self["choosen"].list[swapIndex] = self["choosen"].list[swapIndex], self["choosen"].list[currentIndex]
			self["choosen"].setList(self["choosen"].list)
			direction()
		else:
			return 0

	def save(self):
		configValue = []
		for x in self.selected:
			configValue.append(x[0][1])
		self.config.value = ",".join(configValue)
		self.config.save()
		self.close(False)

	def cancel(self):
		if self.selected != self.prevselected:
			self.session.openWithCallback(self.cancelCallback, MessageBox, _("are you sure to cancel all changes"), default=False)
		else:
			self.close(None)

	def cancelCallback(self, answer):
		answer and self.close(None)

class hotkeyActionMap(ActionMap):
	def action(self, contexts, action):
		if (action in tuple(x[1] for x in getHotkeys()) and self.actions.has_key(action)):
			res = self.actions[action](action)
			if res is not None:
				return res
			return 1
		else:
			return ActionMap.action(self, contexts, action)

class helpableHotkeyActionMap(HelpableActionMap):
	def action(self, contexts, action):
		if (action in tuple(x[1] for x in getHotkeys()) and self.actions.has_key(action)):
			res = self.actions[action](action)
			if res is not None:
				return res
			return 1
		else:
			return ActionMap.action(self, contexts, action)

class InfoBarHotkey():
	def __init__(self):
		self.hotkeys = getHotkeys()
		self["HotkeyButtonActions"] = helpableHotkeyActionMap(self, "HotkeyActions",
			dict((x[1],(self.hotkeyGlobal, boundFunction(self.getHelpText, x[1]))) for x in self.hotkeys), -10)
		self.onExecBegin.append(self.clearLongkeyPressed)

	def clearLongkeyPressed(self):
		self.longkeyPressed = False

	def getKeyFunctions(self, key):
		if key in ("play", "playpause", "Stop", "stop", "pause", "rewind", "next", "previous", "fastforward", "skip_back", "skip_forward") and (self.__class__.__name__ == "MoviePlayer" or hasattr(self, "timeshiftActivated") and self.timeshiftActivated()):
			return False
		selection = eval("config.misc.hotkey." + key + ".value.split(',')")
		selected = []
		for x in selection:
			if x.startswith("ZapPanic"):
				selected.append(((_("Panic to") + " " + ServiceReference(eServiceReference(x.split("/", 1)[1]).toString()).getServiceName()), x))
			elif x.startswith("Zap"):
				selected.append(((_("Zap to") + " " + ServiceReference(eServiceReference(x.split("/", 1)[1]).toString()).getServiceName()), x))
			else:
				function = list(function for function in getHotkeyFunctions() if function[1] == x )
				if function:
					selected.append(function[0])
		return selected

	def getHelpText(self, key):
		selected = self.getKeyFunctions(key)
		if not selected:
			return
		if len(selected) == 1:
			return selected[0][0]
		else:
			return _("Hotkey") + " " + tuple(x[0] for x in self.hotkeys if x[1] == key)[0]

	def hotkeyGlobal(self, key):
		if self.longkeyPressed:
			self.longkeyPressed = False
		else:
			selected = self.getKeyFunctions(key)
			if not selected:
				return 0
			elif len(selected) == 1:
				self.longkeyPressed = key.endswith("_long")
				return self.execHotkey(selected[0])
			else:
				key = tuple(x[0] for x in self.hotkeys if x[1] == key)[0]
				self.session.openWithCallback(self.execHotkey, ChoiceBox, _("Hotkey") + " " + key, selected)

	def execHotkey(self, selected):
		if selected:
			selected = selected[1].split("/")
			if selected[0] == "Plugins":
				twinPlugins = []
				twinPaths = {}
				pluginlist = plugins.getPlugins(PluginDescriptor.WHERE_EVENTINFO)
				pluginlist.sort(key=lambda p: p.name)
				for plugin in pluginlist:
					if plugin.name not in twinPlugins and plugin.path and 'selectedevent' not in plugin.__call__.func_code.co_varnames:	
						if twinPaths.has_key(plugin.path[24:]):
							twinPaths[plugin.path[24:]] += 1
						else:
							twinPaths[plugin.path[24:]] = 1
						if plugin.path[24:] + "/" + str(twinPaths[plugin.path[24:]]) == "/".join(selected):
							self.runPlugin(plugin)
							return
						twinPlugins.append(plugin.name)
				pluginlist = plugins.getPlugins([PluginDescriptor.WHERE_PLUGINMENU, PluginDescriptor.WHERE_EXTENSIONSMENU])
				pluginlist.sort(key=lambda p: p.name)
				for plugin in pluginlist:
					if plugin.name not in twinPlugins and plugin.path:
						if twinPaths.has_key(plugin.path[24:]):
							twinPaths[plugin.path[24:]] += 1
						else:
							twinPaths[plugin.path[24:]] = 1
						if plugin.path[24:] + "/" + str(twinPaths[plugin.path[24:]]) == "/".join(selected):
							self.runPlugin(plugin)
							return
						twinPlugins.append(plugin.name)
			elif selected[0] == "MenuPlugin":
				for plugin in plugins.getPluginsForMenu(selected[1]):
					if plugin[2] == selected[2]:
						self.runPlugin(plugin[1])
						return
			elif selected[0] == "Infobar":
				if hasattr(self, selected[1]):
					exec "self." + ".".join(selected[1:]) + "()"
				else:
					return 0
			elif selected[0] == "Module":
				try:
					exec "from " + selected[1] + " import *"
					exec "self.session.open(" + ",".join(selected[2:]) + ")"
				except:
					print "[Hotkey] error during executing module %s, screen %s" % (selected[1], selected[2])
			elif selected[0] == "Setup":
				exec "from Screens.Setup import *"
				exec "self.session.open(Setup, \"" + selected[1] + "\")"
			elif selected[0].startswith("Zap"):
				if selected[0] == "ZapPanic":
					self.servicelist.history = []
					self.pipShown() and self.showPiP()
				self.servicelist.servicelist.setCurrent(eServiceReference("/".join(selected[1:])))
				self.servicelist.zap(enable_pipzap = True)
				if hasattr(self, "lastservice"):
					self.lastservice = eServiceReference("/".join(selected[1:]))
					self.close()
				else:
					self.show()
				from Screens.MovieSelection import defaultMoviePath
				moviepath = defaultMoviePath()
				if moviepath:
					config.movielist.last_videodir.value = moviepath
			elif selected[0] == "PPanel":
				ppanelFileName = '/etc/ppanels/' + selected[1] + ".xml"
				if os.path.isfile(ppanelFileName) and os.path.isdir('/usr/lib/enigma2/python/Plugins/Extensions/PPanel'):
					from Plugins.Extensions.PPanel.ppanel import PPanel
					self.session.open(PPanel, name=selected[1] + ' PPanel', node=None, filename=ppanelFileName, deletenode=None)
			elif selected[0] == "Shellscript":
				command = '/usr/script/' + selected[1] + ".sh"
				if os.path.isfile(command) and os.path.isdir('/usr/lib/enigma2/python/Plugins/Extensions/PPanel'):
					from Plugins.Extensions.PPanel.ppanel import Execute
					self.session.open(Execute, selected[1] + " shellscript", None, command)

	def showServiceListOrMovies(self):
		if hasattr(self, "openServiceList"):
			self.openServiceList()
		elif hasattr(self, "showMovies"):
			self.showMovies()

	def ToggleLCDLiveTV(self):
		config.lcd.showTv.value = not config.lcd.showTv.value
