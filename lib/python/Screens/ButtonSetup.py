from os import listdir
from os.path import isdir, isfile

from enigma import eActionMap, eServiceReference

from GlobalActions import globalActionMap
from ServiceReference import ServiceReference
from Components.ActionMap import ActionMap, HelpableActionMap
from Components.config import ConfigSubsection, ConfigText, ConfigYesNo, config
from Components.ChoiceList import ChoiceEntryComponent, ChoiceList
from Components.Label import Label
from Components.SystemInfo import BoxInfo
from Components.PluginComponent import plugins
from Components.Sources.StaticText import StaticText
from Screens.ChoiceBox import ChoiceBox
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Plugins.Plugin import PluginDescriptor
from Tools.BoundFunction import boundFunction
from Tools.Directories import isPluginInstalled


BUTTON_SETUP_KEYS = [
	(_("Red"), "red", ""),
	(_("Red"), "red_long", ""),
	(_("Green"), "green", ""),
	(_("Green"), "green_long", ""),
	(_("Yellow"), "yellow", ""),
	(_("Yellow"), "yellow_long", ""),
	(_("Blue"), "blue", ""),
	(_("Blue"), "blue_long", ""),
	(_("Info (EPG)"), "info", "Infobar/InfoPressed/1"),
	(_("Info (EPG)"), "info_long", "Infobar/showEventInfoPlugins/1"),
	(_("Epg/Guide"), "epg", "Infobar/EPGPressed/1"),
	(_("Epg/Guide"), "epg_long", "Infobar/showEventGuidePlugins/1"),
	(_("Left"), "cross_left", ""),
	(_("Left"), "cross_left_long", ""),
	(_("Right"), "cross_right", ""),
	(_("Right"), "cross_right_long", "Infobar/seekFwdVod"),
	(_("Up"), "cross_up", ""),
	(_("Down"), "cross_down", ""),
	(_("PageUp"), "pageup", ""),
	(_("PageUp"), "pageup_long", ""),
	(_("PageDown"), "pagedown", ""),
	(_("PageDown"), "pagedown_long", ""),
	(_("Channel up"), "channelup", ""),
	(_("Channel down"), "channeldown", ""),
	(_("EJECTCD"), "ejectcd", ""),
	(_("EJECTCD"), "ejectcd_long", ""),
	(_("TV"), "showTv", ""),
	(_("RADIO"), "radio", ""),
	(_("RADIO"), "radio_long", ""),
	(_("Rec"), "rec", ""),
	(_("Rec"), "rec_long", ""),
	(_("Teletext"), "text", ""),
	(_("Teletext"), "text_long", ""),
	(_("Help"), "displayHelp", ""),
	(_("Help"), "displayHelp_long", ""),
	(_("Subtitle"), "subtitle", ""),
	(_("Subtitle"), "subtitle_long", ""),
	(_("Menu"), "mainMenu", ""),
	(_("List/Fav"), "list", ""),
	(_("List/Fav"), "list_long", ""),
	(_("PVR"), "pvr", ""),
	(_("PVR"), "pvr_long", ""),
	(_("Favorites"), "favorites", ""),
	(_("Favorites"), "favorites_long", ""),
	(_("File"), "file", ""),
	(_("File"), "file_long", ""),
	(_("OK"), "ok_long", ""),
	(_("Media"), "media", ""),
	(_("Media"), "media_long", ""),
	(_("Open"), "open", ""),
	(_("Open"), "open_long", ""),
	(_("Option"), "option", ""),
	(_("Option"), "option_long", ""),
	(_("Www"), "www", ""),
	(_("Www"), "www_long", ""),
	(_("Directory"), "directory", ""),
	(_("Directory"), "directory_long", ""),
	(_("Back/Recall"), "back", ""),
	(_("Back/Recall"), "back_long", ""),
	(_("History"), "archive", ""),
	(_("History"), "archive_long", ""),
	(_("Aspect"), "mode", ""),
	(_("Aspect"), "mode_long", ""),
	(_("Home"), "home", ""),
	(_("Home"), "home_long", ""),
	(_("End"), "end", ""),
	(_("End"), "end_long", ""),
	(_("Next"), "next", ""),
	(_("Previous"), "previous", ""),
	(_("Audio"), "audio", ""),
	(_("Audio"), "audio_long", ""),
	(_("Play"), "play", ""),
	(_("Playpause"), "playpause", ""),
	(_("Stop"), "stop", ""),
	(_("Pause"), "pause", ""),
	(_("Rewind"), "rewind", ""),
	(_("Fast forward"), "fastforward", ""),
	(_("Skip back"), "skip_back", ""),
	(_("Skip forward"), "skip_forward", ""),
	(_("activatePiP"), "activatePiP", ""),
	(_("Playlist"), "playlist", ""),
	(_("Playlist"), "playlist_long", ""),
	(_("Nextsong"), "nextsong", ""),
	(_("Nextsong"), "nextsong_long", ""),
	(_("Prevsong"), "prevsong", ""),
	(_("Prevsong"), "prevsong_long", ""),
	(_("Program"), "prog", ""),
	(_("Program"), "prog_long", ""),
	(_("Time"), "time", ""),
	(_("Time"), "time_long", ""),
	(_("Homepage"), "homep", ""),
	(_("Homepage"), "homep_long", ""),
	(_("Search/WEB"), "search", ""),
	(_("Search/WEB"), "search_long", ""),
	(_("Slow"), "slow", ""),
	(_("Mark/Portal/Playlist"), "mark", ""),
	(_("Mark/Portal/Playlist"), "mark_long", ""),
	(_("Sleep"), "sleep", ""),
	(_("Sleep"), "sleep_long", ""),
	(_("Power"), "power", ""),
	(_("Power"), "power_long", ""),
	(_("HDMIin"), "HDMIin", "Infobar/HDMIIn"),
	(_("HDMIin"), "HDMIin_long", (BoxInfo.getItem("LcdLiveTV") and "Infobar/ToggleLCDLiveTV") or ""),
	(_("Context"), "contextMenu", "Infobar/showExtensionSelection"),
	(_("Context"), "context_long", ""),
	(_("SAT"), "sat", "Infobar/openSatellites"),
	(_("SAT"), "sat_long", ""),
	(_("Prov"), "prov", ""),
	(_("Prov"), "prov_long", ""),
	(_("LAN"), "lan", ""),
	(_("LAN"), "lan_long", ""),
	(_("PC"), "pc", ""),
	(_("PC"), "pc_long", ""),
	(_("F1"), "f1", ""),
	(_("F1"), "f1_long", ""),
	(_("F2"), "f2", ""),
	(_("F2"), "f2_long", ""),
	(_("F3"), "f3", ""),
	(_("F3"), "f3_long", ""),
	(_("F4"), "f4", ""),
	(_("F4"), "f4_long", ""),
	(_("Magic"), "f10", ""),
	(_("Magic"), "f10_long", ""),
	# TRANSLATORS: PIP with uppercase i is for the button key text
	(_("PIP"), "f6", ""),
	# TRANSLATORS: PIP with uppercase i is for the button key text
	(_("PIP"), "f6_long", ""),
	(_("MOUSE"), "mouse", ""),
	(_("MOUSE"), "mouse_long", ""),
	(_("VOD"), "vod", ""),
	(_("VOD"), "vod_long", ""),
	(_("Keyboard"), "keyboard", ""),
	(_("Keyboard"), "keyboard_long", ""),
	(_("Kodi"), "kodi", ""),
	(_("Kodi"), "kodi_long", ""),
	(_("YouTube"), "youtube", ""),
	(_("YouTube"), "youtube_long", ""),
	(_("ZOOM"), "zoom", ""),
	(_("ZOOM"), "zoom_long", "")
]


config.misc.ButtonSetup = ConfigSubsection()
config.misc.ButtonSetup.additional_keys = ConfigYesNo(default=True)
for button in BUTTON_SETUP_KEYS:
	# exec("config.misc.ButtonSetup." + button[1] + " = ConfigText(default='" + button[2] + "')")
	setattr(config.misc.ButtonSetup, button[1], ConfigText(default=button[2]))


def getButtonSetupFunctions():
	ButtonSetupFunctions = []
	twinPlugins = []
	twinPaths = {}
	pluginlist = plugins.getPlugins(PluginDescriptor.WHERE_EVENTINFO)
	pluginlist.sort(key=lambda p: p.name)
	for plugin in pluginlist:
		if plugin.name not in twinPlugins and plugin.path and "selectedevent" not in plugin.__call__.__code__.co_varnames:
			if plugin.path[plugin.path.rfind("Plugins"):] in twinPaths:
				twinPaths[plugin.path[plugin.path.rfind("Plugins"):]] += 1
			else:
				twinPaths[plugin.path[plugin.path.rfind("Plugins"):]] = 1
			ButtonSetupFunctions.append((plugin.name, "%s/%s" % (plugin.path[plugin.path.rfind("Plugins"):], str(twinPaths[plugin.path[plugin.path.rfind("Plugins"):]])), "EPG"))
			twinPlugins.append(plugin.name)
	pluginlist = plugins.getPlugins([PluginDescriptor.WHERE_PLUGINMENU, PluginDescriptor.WHERE_EXTENSIONSMENU, PluginDescriptor.WHERE_EVENTINFO, PluginDescriptor.WHERE_BUTTONSETUP])
	pluginlist.sort(key=lambda p: p.name)
	for plugin in pluginlist:
		if plugin.name not in twinPlugins and plugin.path:
			if plugin.path[plugin.path.rfind("Plugins"):] in twinPaths:
				twinPaths[plugin.path[plugin.path.rfind("Plugins"):]] += 1
			else:
				twinPaths[plugin.path[plugin.path.rfind("Plugins"):]] = 1
			ButtonSetupFunctions.append((plugin.name, "%s/%s" % (plugin.path[plugin.path.rfind("Plugins"):], str(twinPaths[plugin.path[plugin.path.rfind("Plugins"):]])), "Plugins"))
			twinPlugins.append(plugin.name)
	ButtonSetupFunctions.append((_("Show vertical Program Guide"), "Infobar/openVerticalEPG", "EPG"))
	ButtonSetupFunctions.append((_("Show graphical multi EPG"), "Infobar/openGraphEPG", "EPG"))
	ButtonSetupFunctions.append((_("Main Menu"), "Infobar/showMainMenu", "InfoBar"))
	ButtonSetupFunctions.append((_("Show help"), "Infobar/showHelp", "InfoBar"))
	ButtonSetupFunctions.append((_("Show extension selection"), "Infobar/showExtensionSelection", "InfoBar"))
	ButtonSetupFunctions.append((_("Zap down"), "Infobar/zapDown", "InfoBar"))
	ButtonSetupFunctions.append((_("Zap up"), "Infobar/zapUp", "InfoBar"))
	ButtonSetupFunctions.append((_("Volume down"), "Infobar/volumeDown", "InfoBar"))
	ButtonSetupFunctions.append((_("Volume up"), "Infobar/volumeUp", "InfoBar"))
	ButtonSetupFunctions.append((_("Show InfoBar"), "Infobar/toggleShow", "InfoBar"))
	ButtonSetupFunctions.append((_("Show service list"), "Infobar/openServiceList", "InfoBar"))
	ButtonSetupFunctions.append((_("Show favorites list"), "Infobar/openBouquets", "InfoBar"))
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
	ButtonSetupFunctions.append((_("Start recording current event"), "Infobar/startRecordingCurrentEvent", "InfoBar"))
	ButtonSetupFunctions.append((_("Activate time shift End"), "Infobar/activateTimeshiftEnd", "InfoBar"))
	ButtonSetupFunctions.append((_("Activate time shift end and pause"), "Infobar/activateTimeshiftEndAndPause", "InfoBar"))
	ButtonSetupFunctions.append((_("Start time shift"), "Infobar/startTimeshift", "InfoBar"))
	ButtonSetupFunctions.append((_("Stop time shift"), "Infobar/stopTimeshift", "InfoBar"))
	ButtonSetupFunctions.append((_("Start teletext"), "Infobar/startTeletext", "InfoBar"))
	ButtonSetupFunctions.append((_("Show subservice selection"), "Infobar/subserviceSelection", "InfoBar"))
	ButtonSetupFunctions.append((_("Show subtitle selection"), "Infobar/subtitleSelection", "InfoBar"))
	ButtonSetupFunctions.append((_("Show subtitle quick menu"), "Infobar/subtitleQuickMenu", "InfoBar"))
	ButtonSetupFunctions.append((_("Letterbox zoom"), "Infobar/vmodeSelection", "InfoBar"))
	ButtonSetupFunctions.append((_("Seekbar"), "Infobar/seekFwdVod", "InfoBar"))
	if BoxInfo.getItem("PIPAvailable"):
		ButtonSetupFunctions.append((_("Show PiP"), "Infobar/showPiP", "InfoBar"))
		ButtonSetupFunctions.append((_("Swap PiP"), "Infobar/swapPiP", "InfoBar"))
		ButtonSetupFunctions.append((_("Move PiP"), "Infobar/movePiP", "InfoBar"))
		ButtonSetupFunctions.append((_("Toggle PiPzap"), "Infobar/togglePipzap", "InfoBar"))
		ButtonSetupFunctions.append((_("Cycle PiP(zap)"), "Infobar/activePiP", "InfoBar"))
	ButtonSetupFunctions.append((_("Activate HbbTV (RED button)"), "Infobar/activateRedButton", "InfoBar"))
	if BoxInfo.getItem("hdmihdin") or BoxInfo.getItem("hdmifhdin"):
		ButtonSetupFunctions.append((_("Toggle HDMI-In full screen"), "Infobar/HDMIInFull", "InfoBar"))
		ButtonSetupFunctions.append((_("Toggle HDMI-In PiP"), "Infobar/HDMIInPiP", "InfoBar"))
	if BoxInfo.getItem("LcdLiveTV"):
		ButtonSetupFunctions.append((_("Toggle LCD LiveTV"), "Infobar/ToggleLCDLiveTV", "InfoBar"))
	if BoxInfo.getItem("canMultiBoot"):
		ButtonSetupFunctions.append((_("MultiBoot Manager"), "Module/Screens.MultiBootManager/MultiBootManager", "InfoBar"))
	ButtonSetupFunctions.append((_("Hotkey Settings"), "Module/Screens.ButtonSetup/ButtonSetup", "Setup"))
	ButtonSetupFunctions.append((_("Software Update"), "Module/Screens.SoftwareUpdate/SoftwareUpdate", "Setup"))
	if BoxInfo.getItem("ci"):
		ButtonSetupFunctions.append((_("CI (Common Interface) Setup"), "Module/Screens.Ci/CiSelection", "Setup"))
	if BoxInfo.getItem("SoftCam"):
		ButtonSetupFunctions.append((_("Softcam Setup"), "Module/Screens.SoftcamSetup/SoftcamSetup", "Setup"))
	ButtonSetupFunctions.append((_("Videosetup"), "Module/Screens.VideoMode/VideoSetup", "Setup"))
	ButtonSetupFunctions.append((_("Tuner Configuration"), "Module/Screens.Satconfig/NimSelection", "Scanning"))
	ButtonSetupFunctions.append((_("Manual Scan"), "Module/Screens.ScanSetup/ScanSetup", "Scanning"))
	ButtonSetupFunctions.append((_("Automatic Scan"), "Module/Screens.ScanSetup/ScanSimple", "Scanning"))
	for plugin in plugins.getPluginsForMenu("scan"):
		ButtonSetupFunctions.append((plugin[0], "MenuPlugin/scan/" + plugin[2], "Scanning"))
	ButtonSetupFunctions.append((_("Network Settings"), "Module/Screens.NetworkSetup/NetworkAdapterSelection", "Setup"))
	ButtonSetupFunctions.append((_("Network menu"), "Infobar/showNetworkMenu", "Setup"))
	ButtonSetupFunctions.append((_("VPN"), "Module/Screens.NetworkSetup/NetworkOpenvpn", "Setup"))
	ButtonSetupFunctions.append((_("Plugin Browser"), "Module/Screens.PluginBrowser/PluginBrowser", "Setup"))
	ButtonSetupFunctions.append((_("Channel Info"), "Module/Screens.ServiceInfo/ServiceInfo", "Setup"))
	ButtonSetupFunctions.append((_("SkinSelector"), "Module/Screens.SkinSelector/SkinSelector", "Setup"))
	if BoxInfo.getItem("LCDSKINSetup"):
		ButtonSetupFunctions.append((_("LCD SkinSelector"), "Module/Screens.SkinSelector/LcdSkinSelector", "Setup"))
	ButtonSetupFunctions.append((_("RecordTimer"), "Module/Screens.Timers/RecordTimerOverview", "Setup"))
	ButtonSetupFunctions.append((_("Open AutoTimer"), "Infobar/showAutoTimerList", "Setup"))
	for plugin in plugins.getPluginsForMenu("system"):
		if plugin[2]:
			ButtonSetupFunctions.append((plugin[0], "MenuPlugin/system/" + plugin[2], "Setup"))
	ButtonSetupFunctions.append((_("Standby"), "Module/Screens.Standby/Standby", "Power"))
	ButtonSetupFunctions.append((_("Restart"), "Module/Screens.Standby/TryQuitMainloop/2", "Power"))
	ButtonSetupFunctions.append((_("Restart enigma"), "Module/Screens.Standby/TryQuitMainloop/3", "Power"))
	ButtonSetupFunctions.append((_("Deep Standby"), "Module/Screens.Standby/TryQuitMainloop/1", "Power"))
	ButtonSetupFunctions.append((_("SleepTimer"), "Module/Screens.SleepTimer/SleepTimer", "Power"))
	ButtonSetupFunctions.append((_("PowerTimer"), "Module/Screens.Timers/PowerTimerOverview", "Power"))
	ButtonSetupFunctions.append((_("Usage Setup"), "Setup/Usage", "Setup"))
	ButtonSetupFunctions.append((_("User interface settings"), "Setup/UserInterface", "Setup"))
	ButtonSetupFunctions.append((_("Recording Setup"), "Setup/Recording", "Setup"))
	ButtonSetupFunctions.append((_("Harddisk Setup"), "Setup/HardDisk", "Setup"))
	ButtonSetupFunctions.append((_("Subtitles Settings"), "Setup/Subtitle", "Setup"))
	ButtonSetupFunctions.append((_("Language"), "Module/Screens.LocaleSelection/LocaleSelection", "Setup"))
	if BoxInfo.getItem("SoftCam"):
		ButtonSetupFunctions.append((_("OscamInfo Mainmenu"), "Module/Screens.OScamInfo/OscamInfoMenu", "Plugins"))
		ButtonSetupFunctions.append((_("CCcamInfo Mainmenu"), "Module/Screens.CCcamInfo/CCcamInfoMain", "Plugins"))
	ButtonSetupFunctions.append((_("Movieplayer"), "Infobar/showMoviePlayer", "Plugins"))
	if isdir("/etc/ppanels"):
		for file in [x for x in listdir("/etc/ppanels") if x.endswith(".xml")]:
			file = file[:-4]
			ButtonSetupFunctions.append(("%s %s" % (_("PPanel"), file), "PPanel/%s" % file, "PPanels"))
	if isdir("/usr/script"):
		for file in [x for x in listdir("/usr/script") if x.endswith(".sh")]:
			file = file[:-3]
			ButtonSetupFunctions.append(("%s %s" % (_("Shellscript"), file), "Shellscript/%s" % file, "Shellscripts"))
	ButtonSetupFunctions.append((_("ScriptRunner"), "Module/Screens.ScriptRunner/ScriptRunner", "Plugins"))
	ButtonSetupFunctions.append((_("QuickMenu"), "Module/Screens.QuickMenu/QuickMenu", "Plugins"))
	if isPluginInstalled("Kodi"):
		ButtonSetupFunctions.append((_("Kodi MediaCenter"), "Kodi/", "Plugins"))
	if isPluginInstalled("BluetoothSetup"):
		ButtonSetupFunctions.append((_("Bluetooth Setup"), "Bluetooth/", "Plugins"))
	if isPluginInstalled("Chromium"):
		ButtonSetupFunctions.append((_("Youtube TV"), "YoutubeTV/", "Plugins"))
	return ButtonSetupFunctions


class ButtonSetup(Screen):
	def __init__(self, session, args=None):
		Screen.__init__(self, session)
		self.setTitle(_("Hotkey Settings"))
		self["description"] = Label(_("Click the button on your remote you want to change."))
		self["key_red"] = StaticText(_("Exit"))
		self.ButtonSetupFunctions = getButtonSetupFunctions()
		count = len(BUTTON_SETUP_KEYS) or 10
		self.buttonList = []
		for button in BUTTON_SETUP_KEYS:
			self.buttonList.append(ChoiceEntryComponent("dummy", (_("%s long" % button[0]) if "_long" in button[1] else button[0], button[1])))
		self["list"] = ChoiceList(list=self.buttonList[:config.misc.ButtonSetup.additional_keys.value and count], selection=0)
		self["choosen"] = ChoiceList(list=[])
		self.getFunctions()
		self["actions"] = ActionMap(["OkCancelActions"], {  # No help available, HELP is a changeable button!
			"cancel": self.close,
		}, prio=-1)
		self["ButtonSetupButtonActions"] = ButtonSetupActionMap(["ButtonSetupActions"], dict((x[1], self.ButtonSetupGlobal) for x in BUTTON_SETUP_KEYS))
		self.longKeyPressed = False
		self.onLayoutFinish.append(self.layoutFinished)
		self.onExecBegin.append(self.getFunctions)
		self.onShown.append(self.disableKeyMap)
		self.onClose.append(self.enableKeyMap)

	def layoutFinished(self):
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
		if self.longKeyPressed:
			self.longKeyPressed = False
		count = len(BUTTON_SETUP_KEYS) or 10
		for index, button in enumerate(self.buttonList[:config.misc.ButtonSetup.additional_keys.value and count]):
			if key == button[0][1]:
				self["list"].moveToIndex(index)
				if key.endswith("_long"):
					self.longKeyPressed = True
				break
		self.getFunctions()
		self.session.open(ButtonSetupSelect, self["list"].getCurrent())

	def getFunctions(self):
		key = self["list"].getCurrent()[0][1]
		if key:
			selected = []
			# for button in eval("config.misc.ButtonSetup." + key + ".value.split(',')"):
			for button in [x.strip() for x in getattr(config.misc.ButtonSetup, key).value.split(",")]:
				function = list(function for function in self.ButtonSetupFunctions if function[1] == button)
				if function:
					selected.append(ChoiceEntryComponent("dummy", ((function[0][0]), function[0][1])))
			self["choosen"].setList(selected)


class ButtonSetupSelect(Screen):
	def __init__(self, session, key, args=None):
		Screen.__init__(self, session)
		self.key = key
		# self.skinName = "ButtonSetupSelect"
		self.setTitle("%s: %s" % (_("Hotkey Settings"), key[0][0]))
		self["description"] = Label(_("Select the desired function and click on 'OK' to assign it. Use 'CH+/-' to toggle between the lists. Select an assigned function and click on 'OK' to deassign it. Use 'NEXT/PREVIOUS' to change the order of the assigned functions."))
		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))
		self.mode = "list"
		self.ButtonSetupFunctions = getButtonSetupFunctions()
		# self.config = eval("config.misc.ButtonSetup." + key[0][1])
		self.config = getattr(config.misc.ButtonSetup, key[0][1])
		self.expanded = []
		self.selected = []
		for button in self.config.value.split(","):
			function = list(function for function in self.ButtonSetupFunctions if function[1] == button)
			if function:
				self.selected.append(ChoiceEntryComponent("dummy", ((function[0][0]), function[0][1])))
		self.prevSelected = self.selected[:]
		self["choosen"] = ChoiceList(list=self.selected, selection=0)
		self["list"] = ChoiceList(list=self.getFunctionList(), selection=0)
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "KeyboardInputActions"], {  # No help available, HELP is a changeable button!
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
		}, prio=-1)
		self.onShown.append(self.enableKeyMap)
		self.onClose.append(self.disableKeyMap)
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
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
		functionsList = []
		catagories = {}
		for function in self.ButtonSetupFunctions:
			if function[2] not in catagories:
				catagories[function[2]] = []
			catagories[function[2]].append(function)
		# for catagory in sorted(list(catagories)):
		for catagory in sorted(catagories.keys()):
			if catagory in self.expanded:
				functionsList.append(ChoiceEntryComponent("expanded", ((catagory), "Expander")))
				for function in catagories[catagory]:
					functionsList.append(ChoiceEntryComponent("verticalline", ((function[0]), function[1])))
			else:
				functionsList.append(ChoiceEntryComponent("expandable", ((catagory), "Expander")))
		return functionsList

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
			currentSelected = self["list"].getCurrent()
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
			self.selected.remove(self["choosen"].getCurrent())
			if not self.selected:
				self.toggleMode()
		self["choosen"].setList(self.selected)

	def keyLeft(self):
		self[self.mode].instance.moveSelection(self[self.mode].instance.pageUp)

	def keyUp(self):
		self[self.mode].instance.moveSelection(self[self.mode].instance.moveUp)

	def keyDown(self):
		self[self.mode].instance.moveSelection(self[self.mode].instance.moveDown)

	def keyRight(self):
		self[self.mode].instance.moveSelection(self[self.mode].instance.pageDown)

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
		for button in self.selected:
			configValue.append(button[0][1])
		self.config.value = ",".join(configValue)
		self.config.save()
		self.close()

	def cancel(self):
		if self.selected != self.prevSelected:
			self.session.openWithCallback(self.cancelCallback, MessageBox, _("Are you sure to cancel all changes?"), default=False)
		else:
			self.close()

	def cancelCallback(self, answer):
		answer and self.close()


class ButtonSetupActionMap(ActionMap):
	def action(self, contexts, action):
		if (action in tuple(button[1] for button in BUTTON_SETUP_KEYS) and action in self.actions):
			res = self.actions[action](action)
			if res is not None:
				return res
			return 1
		else:
			return ActionMap.action(self, contexts, action)


class HelpableButtonSetupActionMap(HelpableActionMap):
	def action(self, contexts, action):
		if (action in tuple(button[1] for button in BUTTON_SETUP_KEYS) and action in self.actions):
			res = self.actions[action](action)
			if res is not None:
				return res
			return 1
		else:
			return ActionMap.action(self, contexts, action)


class InfoBarButtonSetup():
	def __init__(self):
		self["ButtonSetupButtonActions"] = HelpableButtonSetupActionMap(self, "ButtonSetupActions",
			dict((button[1], (self.ButtonSetupGlobal, boundFunction(self.getHelpText, button[1]))) for button in BUTTON_SETUP_KEYS), -10)
		self.longKeyPressed = False
		self.onExecEnd.append(self.clearLongKeyPressed)

	def clearLongKeyPressed(self):
		self.longKeyPressed = False

	def getKeyFunctions(self, key):
		if key.lower() in ("play", "playpause", "stop", "pause", "rewind", "next", "previous", "fastforward", "skip_back", "skip_forward") and (self.__class__.__name__ == "MoviePlayer" or hasattr(self, "timeshiftActivated") and self.timeshiftActivated()):
			return False
		# selection = eval("config.misc.ButtonSetup." + key + ".value.split(',')")
		selection = [x.strip() for x in getattr(config.misc.ButtonSetup, key).value.split(",")]
		selected = []
		for button in selection:
			if button.startswith("ZapPanic"):
				selected.append(("%s %s" % (_("Panic to"), ServiceReference(eServiceReference(button.split("/", 1)[1]).toString()).getServiceName()), button))
			elif button.startswith("Zap"):
				selected.append(("%s %s" % (_("Zap to"), ServiceReference(eServiceReference(button.split("/", 1)[1]).toString()).getServiceName()), button))
			else:
				function = list(x for x in getButtonSetupFunctions() if x[1] == button)
				if function:
					selected.append(function[0])
		return selected

	def getName(self, key):
		return tuple([_("%s long" % x[0]) if "_long" in x[1] else x[0] for x in BUTTON_SETUP_KEYS if x[1] == key])[0]

	def getHelpText(self, key):
		selected = self.getKeyFunctions(key)
		if not selected:
			return
		if len(selected) == 1:
			button = selected[0]
			return _("%s long" % button[0]) if "_long" in button[1] else button[0]
		else:
			return "%s %s" % (_("ButtonSetup"), self.getName(key))

	def ButtonSetupGlobal(self, key):
		if self.longKeyPressed:
			self.longKeyPressed = False
		else:
			selected = self.getKeyFunctions(key)
			if not selected:
				return 0
			elif len(selected) == 1:
				if key.endswith("_long"):
					self.longKeyPressed = True
				return self.execButtonSetup(selected[0])
			else:
				key = self.getName(key)
				self.session.openWithCallback(self.execButtonSetup, ChoiceBox, "%s: %s" % (_("Hotkey"), key), selected)

	def execButtonSetup(self, selected):
		if selected:
			selected = selected[1].split("/")
			if selected[0] == "Plugins":
				twinPlugins = []
				twinPaths = {}
				pluginList = plugins.getPlugins(PluginDescriptor.WHERE_EVENTINFO)
				pluginList.sort(key=lambda x: x.name)
				for plugin in pluginList:
					if plugin.name not in twinPlugins and plugin.path and "selectedevent" not in plugin.__call__.__code__.co_varnames:
						if plugin.path[plugin.path.rfind("Plugins"):] in twinPaths:
							twinPaths[plugin.path[plugin.path.rfind("Plugins"):]] += 1
						else:
							twinPaths[plugin.path[plugin.path.rfind("Plugins"):]] = 1
						if "%s/%s" % (plugin.path[plugin.path.rfind("Plugins"):], str(twinPaths[plugin.path[plugin.path.rfind("Plugins"):]])) == "/".join(selected):
							self.runPlugin(plugin)
							return
						twinPlugins.append(plugin.name)
				pluginList = plugins.getPlugins([PluginDescriptor.WHERE_PLUGINMENU, PluginDescriptor.WHERE_EXTENSIONSMENU, PluginDescriptor.WHERE_BUTTONSETUP])
				pluginList.sort(key=lambda p: p.name)
				for plugin in pluginList:
					if plugin.name not in twinPlugins and plugin.path:
						if plugin.path[plugin.path.rfind("Plugins"):] in twinPaths:
							twinPaths[plugin.path[plugin.path.rfind("Plugins"):]] += 1
						else:
							twinPaths[plugin.path[plugin.path.rfind("Plugins"):]] = 1
						if "%s/%s" % (plugin.path[plugin.path.rfind("Plugins"):], str(twinPaths[plugin.path[plugin.path.rfind("Plugins"):]])) == "/".join(selected):
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
					exec("self.%s()" % ".".join(selected[1:]))
				else:
					return 0
			elif selected[0] == "Module":
				try:
					exec("from %s import %s\nself.session.open(%s)" % (selected[1], selected[2], ",".join(selected[2:])))
				except Exception as err:
					print("[ButtonSetup] Error: Exception raised executing module '%s', screen '%s'!  (%s)" % (selected[1], selected[2], str(err)))
					import traceback
					traceback.print_exc()
			elif selected[0] == "Setup":
				from Screens.Setup import Setup
				# exec("self.session.open(Setup, \"%s\")" % selected[1])  # DEBUG: What is this trying to do?
				self.session.open(Setup, selected[1])
			elif selected[0].startswith("Zap"):
				if selected[0] == "ZapPanic":
					self.servicelist.history = []
					self.pipShown() and self.showPiP()
				self.servicelist.servicelist.setCurrent(eServiceReference("/".join(selected[1:])))
				self.servicelist.zap(enable_pipzap=True)
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
				ppanelFileName = "/etc/ppanels/%s.xml" % selected[1]
				if isfile(ppanelFileName) and isdir("/usr/lib/enigma2/python/Plugins/Extensions/PPanel"):
					from Plugins.Extensions.PPanel.ppanel import PPanel
					self.session.open(PPanel, name="%s PPanel" % selected[1], node=None, filename=ppanelFileName, deletenode=None)
			elif selected[0] == "Shellscript":
				command = "/usr/script/%s.sh" % selected[1]
				if isfile(command) and isdir("/usr/lib/enigma2/python/Plugins/Extensions/PPanel"):
					from Plugins.Extensions.PPanel.ppanel import Execute
					self.session.open(Execute, "%s shellscript" % selected[1], None, command)
				else:
					from Screens.Console import Console
					# exec("self.session.open(Console, title=_(selected[1]), cmdlist=[command])")  # DEBUG: What is this trying to do?
					self.session.open(Console, selected[1], [command])
			elif selected[0] == "EMC":
				try:
					from Plugins.Extensions.EnhancedMovieCenter.plugin import showMoviesNew
					from Screens.InfoBar import InfoBar
					open(showMoviesNew(InfoBar.instance))  # DEBUG: Should this be self.session.open?
				except Exception as err:
					print("[ButtonSetup] EMCPlayer: showMovies exception: %s!" % str(err))
			elif selected[0] == "ScriptRunner":
				from Screens.ScriptRunner import ScriptRunner
				self.session.open(ScriptRunner)
			elif selected[0] == "QuickMenu":
				from Screens.QuickMenu import QuickMenu
				self.session.open(QuickMenu)
			elif selected[0] == "Kodi":
				if isPluginInstalled("Kodi"):
					from Plugins.Extensions.Kodi.plugin import KodiMainScreen
					self.session.open(KodiMainScreen)
			elif selected[0] == "Bluetooth":
				if isPluginInstalled("BluetoothSetup"):
					from Plugins.SystemPlugins.BluetoothSetup.plugin import BluetoothSetup
					self.session.open(BluetoothSetup)
			elif selected[0] == "YoutubeTV":
				if isPluginInstalled("Chromium"):
					from Plugins.Extensions.Chromium.youtube import YoutubeTVWindow
					self.session.open(YoutubeTVWindow)

	def showServiceListOrMovies(self):
		if hasattr(self, "openServiceList"):
			self.openServiceList()
		elif hasattr(self, "showMovies"):
			self.showMovies()

	def ToggleLCDLiveTV(self):
		config.lcd.showTv.value = not config.lcd.showTv.value
