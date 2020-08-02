from GlobalActions import globalActionMap
from Components.ActionMap import ActionMap, HelpableActionMap
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
from enigma import eServiceReference, eActionMap
from Components.Label import Label
from boxbranding import getHaveHDMIinHD, getHaveHDMIinFHD, getHaveCI
import os

def getButtonSetupKeys():
	buttonConfig = [
			("Red button", "red", ""),
			("Red button hold", "red_long", ""),
			("Green", "green", ""),
			("Green button hold", "green_long", ""),
			("Yellow button", "yellow", ""),
			("Yellow button hold", "yellow_long", ""),
			("Blue", "blue", ""),
			("Blue button hold", "blue_long", ""),
			("Info/EPG button", "info", "Infobar/InfoPressed/1"),
			("Info/EPG button hold", "info_long", "Infobar/showEventInfoPlugins/1"),
			("EPG/Guide button", "epg", "Infobar/EPGPressed/1"),
			("EPG/Guide button hold", "epg_long", "Infobar/showEventGuidePlugins/1"),
			("◀︎ Left button", "cross_left", ""),
			("Right", "cross_right", ""),
			("◀︎ Left button hold", "cross_left_long", ""),
			("Right ▶︎ button hold", "cross_right_long", "Infobar/seekFwdVod"),
			("▲ Up button", "cross_up", ""),
			("▼ Down button", "cross_down", ""),
			("Page Up button", "pageup", ""),
			("Page Up button hold", "pageup_long", ""),
			("Page Down button", "pagedown", ""),
			("Page Down button hold", "pagedown_long", ""),
			("Channel + button", "channelup", ""),
			("Channel - button", "channeldown", ""),
			("Eject button", "ejectcd", ""),
			("Eject button hold", "ejectcd_long", ""),
			("TV", "showTv", ""),
			("Radio button", "radio", ""),
			("Radio button hold", "radio_long", ""),
			("Rec", "rec", ""),
			("● REC button hold", "rec_long", ""),
			("Teletext", "text", ""),
			("Help", "displayHelp", ""),
			("Help button hold", "displayHelp_long", ""),
			("Subtitle", "subtitle", ""),
			("Subtitle button hold", "subtitle_long", ""),
			("Menu", "mainMenu", ""),
			("List/FAV button", "list", ""),
			("List/Fav button hold", "list_long", ""),
			("PVR button", "pvr", ""),
			("PVR button hold", "pvr_long", ""),
			("Favorites", "favorites", ""),
			("Favorites button hold", "favorites_long", ""),
			("File", "file", ""),
			("File button hold", "file_long", ""),
			("OK button hold", "ok_long", ""),
			("Media button", "media", ""),
			("Media button hold", "media_long", ""),
			("Open button", "open", ""),
			("Open button hold", "open_long", ""),
			("Option button", "option", ""),
			("Option button hold", "option_long", ""),
			("www button", "www", ""),
			("www button hold", "www_long", ""),
			("Directory", "directory", ""),
			("Directory button hold", "directory_long", ""),
			("Back/Recall button", "back", ""),
			("Back/Recall button hold", "back_long", ""),
			("History", "archive", ""),
			("History button hold", "archive_long", ""),
			("Aspect button", "mode", ""),
			("Aspect button hold", "mode_long", ""),
			("Home", "home", ""),
			("Home button hold", "home_long", ""),
			("End", "end", ""),
			("End button hold", "end_long", ""),
			("Next", "next", ""),
			("Previous", "previous", ""),
			("Audio", "audio", ""),
			("Audio button hold", "audio_long", ""),
			("Play", "play", ""),
			("▶︎|| Play/Pause button", "playpause", ""),
			("Stop", "stop", ""),
			("Pause", "pause", ""),
			("◀︎◀︎ Rewind", "rewind", ""),
			("▶︎▶︎ Fast Forward button", "fastforward", ""),
			("Skip back", "skip_back", ""),
			("Skip forward", "skip_forward", ""),
			("activatePiP", "activatePiP", ""),
			("Playlist button", "playlist", ""),
			("Playlist button hold", "playlist_long", ""),
			("Next Track ▶︎▶︎| button", "nextsong", ""),
			("Next Track ▶︎▶︎| button hold", "nextsong_long", ""),
			("|◀︎◀︎ Previous Track button", "prevsong", ""),
			("|◀︎◀︎ Previous Track button hold", "prevsong_long", ""),
			("Program button", "prog", ""),
			("Program button hold", "prog_long", ""),
			("Time", "time", ""),
			("Time button hold", "time_long", ""),
			("Homepage button", "homep", ""),
			("Homepage button hold", "homep_long", ""),
			("Search/WEB button", "search", ""),
			("Search/WEB button hold", "search_long", ""),
			("Slow", "slow", ""),
			("Mark/Portal/Playlist button", "mark", ""),
			("Mark/Portal/Playlist button hold", "mark_long", ""),
			("Sleep button", "sleep", ""),
			("Sleep button hold", "sleep_long", ""),
			("Power button", "power", ""),
			("Power button hold", "power_long", ""),
			("HDMIin", "HDMIin", "Infobar/HDMIIn"),
			("HDMIin button hold", "HDMIin_long", (SystemInfo["LcdLiveTV"] and "Infobar/ToggleLCDLiveTV") or ""),
			("Context button", "contextMenu", "Infobar/showExtensionSelection"),
			("Context button hold", "context_long", ""),
			("SAT", "sat", "Infobar/openSatellites"),
			("SAT button hold", "sat_long", ""),
			("Prov button", "prov", ""),
			("Prov button hold", "prov_long", ""),
			("LAN", "lan", ""),
			("LAN button hold", "lan_long", ""),
			("PC", "pc", ""),
			("PC button hold", "pc_long", ""),
			("F1 button", "f1", ""),
			("F1 button hold", "f1_long", ""),
			("F2 button", "f2", ""),
			("F2 button hold", "f2_long", ""),
			("F3 button", "f3", ""),
			("F3 button hold", "f3_long", ""),
			("F4 button", "f4", ""),
			("F4 button hold", "f4_long", ""),
			("PIP", "f6", ""),
			("PiP button hold", "f6_long", ""),
			("Mouse button", "mouse", ""),
			("Mouse button hold", "mouse_long", ""),
			("VoD button", "vod", ""),
			("VoD button hold", "vod_long", ""),
			("Keyboard", "keyboard", ""),
			("Keyboard button hold", "keyboard_long", ""),
			("Zoom button", "zoom", ""),
			("Zoom button hold", "zoom_long", ""),
	]
	return [(pgettext("button|label", button[0]), button[1], button[2]) for button in buttonConfig]

config.misc.ButtonSetup = ConfigSubsection()
config.misc.ButtonSetup.additional_keys = ConfigYesNo(default=True)
for x in getButtonSetupKeys():
	exec "config.misc.ButtonSetup." + x[1] + " = ConfigText(default='" + x[2] + "')"

def getButtonSetupFunctions():
	ButtonSetupFunctions = []
	twinPlugins = []
	twinPaths = {}
	pluginlist = plugins.getPlugins(PluginDescriptor.WHERE_EVENTINFO)
	pluginlist.sort(key=lambda p: p.name)
	for plugin in pluginlist:
		if plugin.name not in twinPlugins and plugin.path and 'selectedevent' not in plugin.__call__.func_code.co_varnames:
			if twinPaths.has_key(plugin.path[plugin.path.rfind("Plugins"):]):
				twinPaths[plugin.path[plugin.path.rfind("Plugins"):]] += 1
			else:
				twinPaths[plugin.path[plugin.path.rfind("Plugins"):]] = 1
			ButtonSetupFunctions.append((plugin.name, plugin.path[plugin.path.rfind("Plugins"):] + "/" + str(twinPaths[plugin.path[plugin.path.rfind("Plugins"):]]) , "EPG"))
			twinPlugins.append(plugin.name)
	pluginlist = plugins.getPlugins([PluginDescriptor.WHERE_PLUGINMENU, PluginDescriptor.WHERE_EXTENSIONSMENU, PluginDescriptor.WHERE_EVENTINFO])
	pluginlist.sort(key=lambda p: p.name)
	for plugin in pluginlist:
		if plugin.name not in twinPlugins and plugin.path:
			if twinPaths.has_key(plugin.path[plugin.path.rfind("Plugins"):]):
				twinPaths[plugin.path[plugin.path.rfind("Plugins"):]] += 1
			else:
				twinPaths[plugin.path[plugin.path.rfind("Plugins"):]] = 1
			ButtonSetupFunctions.append((plugin.name, plugin.path[plugin.path.rfind("Plugins"):] + "/" + str(twinPaths[plugin.path[plugin.path.rfind("Plugins"):]]) , "Plugins"))
			twinPlugins.append(plugin.name)
	ButtonSetupFunctions.append((_("Show vertical Program Guide"), "Infobar/openVerticalEPG", "EPG"))
	ButtonSetupFunctions.append((_("Show graphical multi EPG"), "Infobar/openGraphEPG", "EPG"))
	ButtonSetupFunctions.append((_("Main menu"), "Infobar/mainMenu", "InfoBar"))
	ButtonSetupFunctions.append((_("Show help"), "Infobar/showHelp", "InfoBar"))
	ButtonSetupFunctions.append((_("Show extension selection"), "Infobar/showExtensionSelection", "InfoBar"))
	ButtonSetupFunctions.append((_("Zap down"), "Infobar/zapDown", "InfoBar"))
	ButtonSetupFunctions.append((_("Zap up"), "Infobar/zapUp", "InfoBar"))
	ButtonSetupFunctions.append((_("Volume down"), "Infobar/volumeDown", "InfoBar"))
	ButtonSetupFunctions.append((_("Volume up"), "Infobar/volumeUp", "InfoBar"))
	ButtonSetupFunctions.append((_("Show Infobar"), "Infobar/toggleShow", "InfoBar"))
	ButtonSetupFunctions.append((_("Show service list"), "Infobar/openServiceList", "InfoBar"))
	ButtonSetupFunctions.append((_("Show favourites list"), "Infobar/openBouquets", "InfoBar"))
	ButtonSetupFunctions.append((_("Show satellites list"), "Infobar/openSatellites", "InfoBar"))
	ButtonSetupFunctions.append((_("History back"), "Infobar/historyBack", "InfoBar"))
	ButtonSetupFunctions.append((_("History next"), "Infobar/historyNext", "InfoBar"))
	ButtonSetupFunctions.append((_("Show eventinfo plugins"), "Infobar/showEventInfoPlugins", "EPG"))
	ButtonSetupFunctions.append((_("Show event details"), "Infobar/openEventView", "EPG"))
	ButtonSetupFunctions.append((_("Show single service EPG"), "Infobar/openSingleServiceEPG", "EPG"))
	ButtonSetupFunctions.append((_("Show multi channel EPG"), "Infobar/openMultiServiceEPG", "EPG"))
	ButtonSetupFunctions.append((_("Show Audioselection"), "Infobar/audioSelection", "InfoBar"))
	ButtonSetupFunctions.append((_("Enable digital downmix"), "Infobar/audioDownmixOn", "InfoBar"))
	ButtonSetupFunctions.append((_("Disable digital downmix"), "Infobar/audioDownmixOff", "InfoBar"))
	ButtonSetupFunctions.append((_("Switch to radio mode"), "Infobar/showRadio", "InfoBar"))
	ButtonSetupFunctions.append((_("Switch to TV mode"), "Infobar/showTv", "InfoBar"))
	ButtonSetupFunctions.append((_("Show servicelist or movies"), "Infobar/showServiceListOrMovies", "InfoBar"))
	ButtonSetupFunctions.append((_("Show movies"), "Infobar/showMovies", "InfoBar"))
	ButtonSetupFunctions.append((_("Instant record"), "Infobar/instantRecord", "InfoBar"))
	ButtonSetupFunctions.append((_("Start instant recording"), "Infobar/startInstantRecording", "InfoBar"))
	ButtonSetupFunctions.append((_("Activate timeshift End"), "Infobar/activateTimeshiftEnd", "InfoBar"))
	ButtonSetupFunctions.append((_("Activate timeshift end and pause"), "Infobar/activateTimeshiftEndAndPause", "InfoBar"))
	ButtonSetupFunctions.append((_("Start timeshift"), "Infobar/startTimeshift", "InfoBar"))
	ButtonSetupFunctions.append((_("Stop timeshift"), "Infobar/stopTimeshift", "InfoBar"))
	ButtonSetupFunctions.append((_("Start teletext"), "Infobar/startTeletext", "InfoBar"))
	ButtonSetupFunctions.append((_("Show subservice selection"), "Infobar/subserviceSelection", "InfoBar"))
	ButtonSetupFunctions.append((_("Show subtitle selection"), "Infobar/subtitleSelection", "InfoBar"))
	ButtonSetupFunctions.append((_("Show subtitle quick menu"), "Infobar/subtitleQuickMenu", "InfoBar"))
	ButtonSetupFunctions.append((_("Letterbox zoom"), "Infobar/vmodeSelection", "InfoBar"))
	ButtonSetupFunctions.append((_("Seekbar"), "Infobar/seekFwdVod", "InfoBar"))
	if SystemInfo["PIPAvailable"]:
		ButtonSetupFunctions.append((_("Show PIP"), "Infobar/showPiP", "InfoBar"))
		ButtonSetupFunctions.append((_("Swap PIP"), "Infobar/swapPiP", "InfoBar"))
		ButtonSetupFunctions.append((_("Move PIP"), "Infobar/movePiP", "InfoBar"))
		ButtonSetupFunctions.append((_("Toggle PIPzap"), "Infobar/togglePipzap", "InfoBar"))
	ButtonSetupFunctions.append((_("Activate HbbTV (Redbutton)"), "Infobar/activateRedButton", "InfoBar"))
	if getHaveHDMIinHD() == 'True' or getHaveHDMIinFHD() == 'True':
		ButtonSetupFunctions.append((_("Toggle HDMI-In full screen"), "Infobar/HDMIInFull", "InfoBar"))
		ButtonSetupFunctions.append((_("Toggle HDMI-In PiP"), "Infobar/HDMIInPiP", "InfoBar"))
	if SystemInfo["LcdLiveTV"]:
		ButtonSetupFunctions.append((_("Toggle LCD LiveTV"), "Infobar/ToggleLCDLiveTV", "InfoBar"))
	if SystemInfo["canMultiBoot"]:
		ButtonSetupFunctions.append((_("Multiboot Image Selector"), "Module/Screens.MultiBootSelector/MultiBootSelector", "InfoBar"))
	ButtonSetupFunctions.append((_("Hotkey Setup"), "Module/Screens.ButtonSetup/ButtonSetup", "Setup"))
	ButtonSetupFunctions.append((_("Software update"), "Module/Screens.SoftwareUpdate/UpdatePlugin", "Setup"))
	if getHaveCI() == 'True':
		ButtonSetupFunctions.append((_("CI (Common Interface) Setup"), "Module/Screens.Ci/CiSelection", "Setup"))
	ButtonSetupFunctions.append((_("Videosetup"), "Module/Screens.VideoMode/VideoSetup", "Setup"))
	ButtonSetupFunctions.append((_("Tuner Configuration"), "Module/Screens.Satconfig/NimSelection", "Scanning"))
	ButtonSetupFunctions.append((_("Manual Scan"), "Module/Screens.ScanSetup/ScanSetup", "Scanning"))
	ButtonSetupFunctions.append((_("Automatic Scan"), "Module/Screens.ScanSetup/ScanSimple", "Scanning"))
	for plugin in plugins.getPluginsForMenu("scan"):
		ButtonSetupFunctions.append((plugin[0], "MenuPlugin/scan/" + plugin[2], "Scanning"))
	ButtonSetupFunctions.append((_("Network setup"), "Module/Screens.NetworkSetup/NetworkAdapterSelection", "Setup"))
	ButtonSetupFunctions.append((_("Network menu"), "Infobar/showNetworkMounts", "Setup"))
	ButtonSetupFunctions.append((_("VPN"), "Module/Screens.NetworkSetup/NetworkOpenvpn", "Setup"))
	ButtonSetupFunctions.append((_("Plugin Browser"), "Module/Screens.PluginBrowser/PluginBrowser", "Setup"))
	ButtonSetupFunctions.append((_("Channel Info"), "Module/Screens.ServiceInfo/ServiceInfo", "Setup"))
	ButtonSetupFunctions.append((_("SkinSelector"), "Module/Screens.SkinSelector/SkinSelector", "Setup"))
	if SystemInfo["LCDSKINSetup"]:
		ButtonSetupFunctions.append((_("LCD SkinSelector"), "Module/Screens.SkinSelector/LcdSkinSelector", "Setup"))
	ButtonSetupFunctions.append((_("Timer"), "Module/Screens.TimerEdit/TimerEditList", "Setup"))
	ButtonSetupFunctions.append((_("Open AutoTimer"), "Infobar/showAutoTimerList", "Setup"))
	for plugin in plugins.getPluginsForMenu("system"):
		if plugin[2]:
			ButtonSetupFunctions.append((plugin[0], "MenuPlugin/system/" + plugin[2], "Setup"))
	ButtonSetupFunctions.append((_("Standby"), "Module/Screens.Standby/Standby", "Power"))
	ButtonSetupFunctions.append((_("Restart"), "Module/Screens.Standby/TryQuitMainloop/2", "Power"))
	ButtonSetupFunctions.append((_("Restart enigma"), "Module/Screens.Standby/TryQuitMainloop/3", "Power"))
	ButtonSetupFunctions.append((_("Deep standby"), "Module/Screens.Standby/TryQuitMainloop/1", "Power"))
	ButtonSetupFunctions.append((_("SleepTimer"), "Module/Screens.SleepTimerEdit/SleepTimerEdit", "Power"))
	ButtonSetupFunctions.append((_("PowerTimer"), "Module/Screens.PowerTimerEdit/PowerTimerEditList", "Power"))
	ButtonSetupFunctions.append((_("Usage Setup"), "Setup/usage", "Setup"))
	ButtonSetupFunctions.append((_("User interface settings"), "Setup/userinterface", "Setup"))
	ButtonSetupFunctions.append((_("Recording Setup"), "Setup/recording", "Setup"))
	ButtonSetupFunctions.append((_("Harddisk Setup"), "Setup/harddisk", "Setup"))
	ButtonSetupFunctions.append((_("Subtitles Settings"), "Setup/subtitlesetup", "Setup"))
	ButtonSetupFunctions.append((_("Language"), "Module/Screens.LanguageSelection/LanguageSelection", "Setup"))
	ButtonSetupFunctions.append((_("OscamInfo Mainmenu"), "Module/Screens.OScamInfo/OscamInfoMenu", "Plugins"))
	ButtonSetupFunctions.append((_("CCcamInfo Mainmenu"), "Module/Screens.CCcamInfo/CCcamInfoMain", "Plugins"))
	ButtonSetupFunctions.append((_("Movieplayer"), "Infobar/showMoviePlayer", "Plugins"))
	if os.path.isdir("/etc/ppanels"):
		for x in [x for x in os.listdir("/etc/ppanels") if x.endswith(".xml")]:
			x = x[:-4]
			ButtonSetupFunctions.append((_("PPanel") + " " + x, "PPanel/" + x, "PPanels"))
	if os.path.isdir("/usr/script"):
		for x in [x for x in os.listdir("/usr/script") if x.endswith(".sh")]:
			x = x[:-3]
			ButtonSetupFunctions.append((_("Shellscript") + " " + x, "Shellscript/" + x, "Shellscripts"))
	if os.path.isfile("/usr/lib/enigma2/python/Plugins/Extensions/Infopanel/ScriptRunner.pyo"):
		ButtonSetupFunctions.append((_("ScriptRunner"), "ScriptRunner/", "Plugins"))
	if os.path.isfile("/usr/lib/enigma2/python/Plugins/Extensions/Infopanel/QuickMenu.pyo"):
		ButtonSetupFunctions.append((_("QuickMenu"), "QuickMenu/", "Plugins"))
	if os.path.isfile("/usr/lib/enigma2/python/Plugins/Extensions/Kodi/plugin.pyo"):
		ButtonSetupFunctions.append((_("Kodi MediaCenter"), "Kodi/", "Plugins"))
	if os.path.isfile("/usr/lib/enigma2/python/Plugins/SystemPlugins/BluetoothSetup/plugin.pyo"):
		ButtonSetupFunctions.append((_("Bluetooth Setup"), "Bluetooth/", "Plugins"))
	if os.path.isfile("/usr/lib/enigma2/python/Plugins/Extensions/Chromium/plugin.pyo"):
		ButtonSetupFunctions.append((_("Youtube TV"), "YoutubeTV/", "Plugins"))
	return ButtonSetupFunctions

class ButtonSetup(Screen):
	def __init__(self, session, args=None):
		Screen.__init__(self, session)
		self['description'] = Label(_('Click on your remote on the button you want to change'))
		self.session = session
		self.setTitle(_("Hotkey Setup"))
		self["key_red"] = Button(_("Exit"))
		self.list = []
		self.ButtonSetupKeys = getButtonSetupKeys()
		self.ButtonSetupFunctions = getButtonSetupFunctions()
		for x in self.ButtonSetupKeys:
			self.list.append(ChoiceEntryComponent('',(_(x[0]), x[1])))
		self["list"] = ChoiceList(list=self.list[:config.misc.ButtonSetup.additional_keys.value and len(self.ButtonSetupKeys) or 10], selection = 0)
		self["choosen"] = ChoiceList(list=[])
		self.getFunctions()
		self["actions"] = ActionMap(["OkCancelActions"],
		{
			"cancel": self.close,
		}, -1)
		self["ButtonSetupButtonActions"] = ButtonSetupActionMap(["ButtonSetupActions"], dict((x[1], self.ButtonSetupGlobal) for x in self.ButtonSetupKeys))
		self.longkeyPressed = False
		self.onLayoutFinish.append(self.__layoutFinished)
		self.onExecBegin.append(self.getFunctions)
		self.onShown.append(self.disableKeyMap)
		self.onClose.append(self.enableKeyMap)

	def __layoutFinished(self):
		self["choosen"].selectionEnabled(0)

	def disableKeyMap(self):
		globalActionMap.setEnabled(False)
		eActionMap.getInstance().unbindNativeKey("ListboxActions", 0)
		eActionMap.getInstance().unbindNativeKey("ListboxActions", 1)
		eActionMap.getInstance().unbindNativeKey("ListboxActions", 4)
		eActionMap.getInstance().unbindNativeKey("ListboxActions", 5)

	def enableKeyMap(self):
		globalActionMap.setEnabled(True)
		eActionMap.getInstance().bindKey("keymap.xml", "generic", 103, 5, "ListboxActions", "moveUp")
		eActionMap.getInstance().bindKey("keymap.xml", "generic", 108, 5, "ListboxActions", "moveDown")
		eActionMap.getInstance().bindKey("keymap.xml", "generic", 105, 5, "ListboxActions", "pageUp")
		eActionMap.getInstance().bindKey("keymap.xml", "generic", 106, 5, "ListboxActions", "pageDown")

	def ButtonSetupGlobal(self, key):
		if self.longkeyPressed:
			self.longkeyPressed = False
		index = 0
		for x in self.list[:config.misc.ButtonSetup.additional_keys.value and len(self.ButtonSetupKeys) or 10]:
			if key == x[0][1]:
				self["list"].moveToIndex(index)
				if key.endswith("_long"):
					self.longkeyPressed = True
				break
			index += 1
		self.getFunctions()
		self.session.open(ButtonSetupSelect, self["list"].l.getCurrentSelection())

	def getFunctions(self):
		key = self["list"].l.getCurrentSelection()[0][1]
		if key:
			selected = []
			for x in eval("config.misc.ButtonSetup." + key + ".value.split(',')"):
				function = list(function for function in self.ButtonSetupFunctions if function[1] == x )
				if function:
					selected.append(ChoiceEntryComponent('',((function[0][0]), function[0][1])))
			self["choosen"].setList(selected)

class ButtonSetupSelect(Screen):
	def __init__(self, session, key, args=None):
		Screen.__init__(self, session)
		self.skinName="ButtonSetupSelect"
		self['description'] = Label(_('Select the desired function and click on "OK" to assign it. Use "CH+/-" to toggle between the lists. Select an assigned function and click on "OK" to de-assign it. Use "Next/Previous" to change the order of the assigned functions.'))
		self.session = session
		self.key = key
		self.setTitle(_("Hotkey Setup for") + ": " + key[0][0])
		self["key_red"] = Button(_("Cancel"))
		self["key_green"] = Button(_("Save"))
		self.mode = "list"
		self.ButtonSetupFunctions = getButtonSetupFunctions()
		self.config = eval("config.misc.ButtonSetup." + key[0][1])
		self.expanded = []
		self.selected = []
		for x in self.config.value.split(','):
			function = list(function for function in self.ButtonSetupFunctions if function[1] == x )
			if function:
				self.selected.append(ChoiceEntryComponent('',((function[0][0]), function[0][1])))
		self.prevselected = self.selected[:]
		self["choosen"] = ChoiceList(list=self.selected, selection=0)
		self["list"] = ChoiceList(list=self.getFunctionList(), selection=0)
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
			"pageDown": self.toggleMode,
			"moveUp": self.moveUp,
			"moveDown": self.moveDown,
		}, -1)
		self.onShown.append(self.enableKeyMap)
		self.onClose.append(self.disableKeyMap)
		self.onLayoutFinish.append(self.__layoutFinished)

	def __layoutFinished(self):
		self["choosen"].selectionEnabled(0)

	def disableKeyMap(self):
		globalActionMap.setEnabled(False)
		eActionMap.getInstance().unbindNativeKey("ListboxActions", 0)
		eActionMap.getInstance().unbindNativeKey("ListboxActions", 1)
		eActionMap.getInstance().unbindNativeKey("ListboxActions", 4)
		eActionMap.getInstance().unbindNativeKey("ListboxActions", 5)

	def enableKeyMap(self):
		globalActionMap.setEnabled(True)
		eActionMap.getInstance().bindKey("keymap.xml", "generic", 103, 5, "ListboxActions", "moveUp")
		eActionMap.getInstance().bindKey("keymap.xml", "generic", 108, 5, "ListboxActions", "moveDown")
		eActionMap.getInstance().bindKey("keymap.xml", "generic", 105, 5, "ListboxActions", "pageUp")
		eActionMap.getInstance().bindKey("keymap.xml", "generic", 106, 5, "ListboxActions", "pageDown")

	def getFunctionList(self):
		functionslist = []
		catagories = {}
		for function in self.ButtonSetupFunctions:
			if not catagories.has_key(function[2]):
				catagories[function[2]] = []
			catagories[function[2]].append(function)
		for catagorie in sorted(list(catagories)):
			if catagorie in self.expanded:
				functionslist.append(ChoiceEntryComponent('expanded',((catagorie), "Expander")))
				for function in catagories[catagorie]:
					functionslist.append(ChoiceEntryComponent('verticalline',((function[0]), function[1])))
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
					self.selected.append(currentSelected[:2])
		elif self.selected:
			self.selected.remove(self["choosen"].l.getCurrentSelection())
			if not self.selected:
				self.toggleMode()
		self["choosen"].setList(self.selected)

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
		self.close()

	def cancel(self):
		if self.selected != self.prevselected:
			self.session.openWithCallback(self.cancelCallback, MessageBox, _("Are you sure to cancel all changes?"), default=False)
		else:
			self.close()

	def cancelCallback(self, answer):
		answer and self.close()

class ButtonSetupActionMap(ActionMap):
	def action(self, contexts, action):
		if (action in tuple(x[1] for x in getButtonSetupKeys()) and self.actions.has_key(action)):
			res = self.actions[action](action)
			if res is not None:
				return res
			return 1
		else:
			return ActionMap.action(self, contexts, action)

class helpableButtonSetupActionMap(HelpableActionMap):
	def action(self, contexts, action):
		if (action in tuple(x[1] for x in getButtonSetupKeys()) and self.actions.has_key(action)):
			res = self.actions[action](action)
			if res is not None:
				return res
			return 1
		else:
			return ActionMap.action(self, contexts, action)

class InfoBarButtonSetup():
	def __init__(self):
		self.ButtonSetupKeys = getButtonSetupKeys()
		self["ButtonSetupButtonActions"] = helpableButtonSetupActionMap(self, "ButtonSetupActions",
			dict((x[1],(self.ButtonSetupGlobal, boundFunction(self.getHelpText, x[1]))) for x in self.ButtonSetupKeys), -10)
		self.longkeyPressed = False
		self.onExecEnd.append(self.clearLongkeyPressed)

	def clearLongkeyPressed(self):
		self.longkeyPressed = False

	def getKeyFunctions(self, key):
		if key in ("play", "playpause", "Stop", "stop", "pause", "rewind", "next", "previous", "fastforward", "skip_back", "skip_forward") and (self.__class__.__name__ == "MoviePlayer" or hasattr(self, "timeshiftActivated") and self.timeshiftActivated()):
			return False
		selection = eval("config.misc.ButtonSetup." + key + ".value.split(',')")
		selected = []
		for x in selection:
			if x.startswith("ZapPanic"):
				selected.append(((_("Panic to") + " " + ServiceReference(eServiceReference(x.split("/", 1)[1]).toString()).getServiceName()), x))
			elif x.startswith("Zap"):
				selected.append(((_("Zap to") + " " + ServiceReference(eServiceReference(x.split("/", 1)[1]).toString()).getServiceName()), x))
			else:
				function = list(function for function in getButtonSetupFunctions() if function[1] == x )
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
			return _("ButtonSetup") + " " + tuple(x[0] for x in self.ButtonSetupKeys if x[1] == key)[0]

	def ButtonSetupGlobal(self, key):
		if self.longkeyPressed:
			self.longkeyPressed = False
		else:
			selected = self.getKeyFunctions(key)
			if not selected:
				return 0
			elif len(selected) == 1:
				if key.endswith("_long"):
					self.longkeyPressed = True
				return self.execButtonSetup(selected[0])
			else:
				key = tuple(x[0] for x in self.ButtonSetupKeys if x[1] == key)[0]
				self.session.openWithCallback(self.execButtonSetup, ChoiceBox, (_("Hotkey")) + ": " + key, selected)

	def execButtonSetup(self, selected):
		if selected:
			selected = selected[1].split("/")
			if selected[0] == "Plugins":
				twinPlugins = []
				twinPaths = {}
				pluginlist = plugins.getPlugins(PluginDescriptor.WHERE_EVENTINFO)
				pluginlist.sort(key=lambda p: p.name)
				for plugin in pluginlist:
					if plugin.name not in twinPlugins and plugin.path and 'selectedevent' not in plugin.__call__.func_code.co_varnames:	
						if twinPaths.has_key(plugin.path[plugin.path.rfind("Plugins"):]):
							twinPaths[plugin.path[plugin.path.rfind("Plugins"):]] += 1
						else:
							twinPaths[plugin.path[plugin.path.rfind("Plugins"):]] = 1
						if plugin.path[plugin.path.rfind("Plugins"):] + "/" + str(twinPaths[plugin.path[plugin.path.rfind("Plugins"):]]) == "/".join(selected):
							self.runPlugin(plugin)
							return
						twinPlugins.append(plugin.name)
				pluginlist = plugins.getPlugins([PluginDescriptor.WHERE_PLUGINMENU, PluginDescriptor.WHERE_EXTENSIONSMENU])
				pluginlist.sort(key=lambda p: p.name)
				for plugin in pluginlist:
					if plugin.name not in twinPlugins and plugin.path:
						if twinPaths.has_key(plugin.path[plugin.path.rfind("Plugins"):]):
							twinPaths[plugin.path[plugin.path.rfind("Plugins"):]] += 1
						else:
							twinPaths[plugin.path[plugin.path.rfind("Plugins"):]] = 1
						if plugin.path[plugin.path.rfind("Plugins"):] + "/" + str(twinPaths[plugin.path[plugin.path.rfind("Plugins"):]]) == "/".join(selected):
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
					exec "from %s import %s" % (selected[1], selected[2])
					exec "self.session.open(%s)" %  ",".join(selected[2:])
				except:
					print "[ButtonSetup] error during executing module %s, screen %s" % (selected[1], selected[2])
			elif selected[0] == "Setup":
				from Screens.Setup import Setup
				exec "self.session.open(Setup, \"%s\")" % selected[1]
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
				else:
					from Screens.Console import Console
					exec "self.session.open(Console,_(selected[1]),[command])"
			elif selected[0] == "EMC":
				try:
					from Plugins.Extensions.EnhancedMovieCenter.plugin import showMoviesNew
					from Screens.InfoBar import InfoBar
					open(showMoviesNew(InfoBar.instance))
				except Exception as e:
					print('[EMCPlayer] showMovies exception:\n' + str(e))
			elif selected[0] == "ScriptRunner":
				if os.path.isfile("/usr/lib/enigma2/python/Plugins/Extensions/Infopanel/ScriptRunner.pyo"):
					from Plugins.Extensions.Infopanel.ScriptRunner import ScriptRunner
					self.session.open (ScriptRunner)
			elif selected[0] == "QuickMenu":
				if os.path.isfile("/usr/lib/enigma2/python/Plugins/Extensions/Infopanel/QuickMenu.pyo"):
					from Plugins.Extensions.Infopanel.QuickMenu import QuickMenu
					self.session.open (QuickMenu)
			elif selected[0] == "Kodi":
				if os.path.isfile("/usr/lib/enigma2/python/Plugins/Extensions/Kodi/plugin.pyo"):
					from Plugins.Extensions.Kodi.plugin import KodiMainScreen
					self.session.open(KodiMainScreen)
			elif selected[0] == "Bluetooth":
				if os.path.isfile("/usr/lib/enigma2/python/Plugins/SystemPlugins/BluetoothSetup/plugin.pyo"):
					from Plugins.SystemPlugins.BluetoothSetup.plugin import BluetoothSetup
					self.session.open(BluetoothSetup)
			elif selected[0] == "YoutubeTV":
				if os.path.isfile("/usr/lib/enigma2/python/Plugins/Extensions/Chromium/plugin.pyo"):
					from Plugins.Extensions.Chromium.youtube import YoutubeTVWindow
					self.session.open(YoutubeTVWindow)

	def showServiceListOrMovies(self):
		if hasattr(self, "openServiceList"):
			self.openServiceList()
		elif hasattr(self, "showMovies"):
			self.showMovies()

	def ToggleLCDLiveTV(self):
		config.lcd.showTv.value = not config.lcd.showTv.value

