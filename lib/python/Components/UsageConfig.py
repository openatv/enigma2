from glob import glob
from locale import AM_STR, PM_STR, nl_langinfo
from os import makedirs, remove, system as ossystem, unlink
from os.path import exists, isfile, join as pathjoin, normpath, splitext
from sys import maxsize
from time import time

from enigma import Misc_Options, RT_HALIGN_CENTER, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_CENTER, RT_WRAP, eActionMap, eBackgroundFileEraser, eDVBDB, eDVBFrontend, eEnv, eEPGCache, eServiceEvent, eSubtitleSettings, eSettings, setEnableTtCachingOnOff, setPreferredTuner, setSpinnerOnOff, setTunerTypePriorityOrder

from keyids import KEYIDS
from skin import getcomponentTemplateNames, parameters, domScreens
from Components.config import ConfigBoolean, ConfigClock, ConfigDictionarySet, ConfigDirectory, ConfigFloat, ConfigInteger, ConfigIP, ConfigLocations, ConfigNumber, ConfigPassword, ConfigSelection, ConfigSelectionNumber, ConfigSequence, ConfigSet, ConfigSlider, ConfigSubDict, ConfigSubsection, ConfigText, ConfigYesNo, NoSave, config, configfile
from Components.Harddisk import harddiskmanager
from Components.International import international
from Components.NimManager import nimmanager
from Components.ServiceList import refreshServiceList
from Components.SystemInfo import BoxInfo
from Tools.Directories import SCOPE_HDD, SCOPE_SKINS, SCOPE_TIMESHIFT, defaultRecordingLocation, fileReadXML, fileWriteLine, resolveFilename

MODULE_NAME = __name__.split(".")[-1]
DEFAULTKEYMAP = eEnv.resolve("${datadir}/enigma2/keymap.xml")


originalAudioTracks = "orj dos ory org esl qaa qaf und mis mul ORY ORJ Audio_ORJ oth"
visuallyImpairedCommentary = "NAR qad"


def InitUsageConfig():
	AvailRemotes = [splitext(x)[0] for x in glob("/usr/share/enigma2/hardware/*.xml")]
	RemoteChoices = []
	DefaultRemote = BoxInfo.getItem("rcname")

	remoteSelectable = False
	if AvailRemotes is not None:
		for remote in AvailRemotes:
			pngfile = "%s.png" % remote
			if isfile(pngfile):
				RemoteChoices.append(remote.split("/")[-1])

	config.misc.SettingsVersion = ConfigFloat(default=[1, 1], limits=[(1, 10), (0, 99)])
	config.misc.SettingsVersion.value = [1, 1]
	config.misc.SettingsVersion.save_forced = True
	config.misc.SettingsVersion.save()
	config.misc.useNTPminutes = ConfigSelection(default=30, choices=[(30, _("%d Minutes") % 30), (60, _("%d Hour") % 1), (1440, _("%d Hours") % 24)])
	config.misc.remotecontrol_text_support = ConfigYesNo(default=True)

	config.misc.extraopkgpackages = ConfigYesNo(default=False)
	config.misc.actionLeftRightToPageUpPageDown = ConfigYesNo(default=True)

	config.misc.usegstplaybin3 = ConfigYesNo(default=False)

	config.misc.spinnerPosition = ConfigSequence(default=[50, 50], limits=[(0, 1260), (0, 700)], seperator=",")

	config.workaround = ConfigSubsection()
	config.workaround.blueswitch = ConfigSelection(default=0, choices=[
		(0, _("QuickMenu/Extensions")),
		(1, _("Extensions/QuickMenu"))
	])
	config.workaround.deeprecord = ConfigYesNo(default=False)
	config.workaround.wakeuptime = ConfigSelectionNumber(default=5, stepwidth=1, min=0, max=30, wraparound=True)
	config.workaround.wakeupwindow = ConfigSelectionNumber(default=5, stepwidth=5, min=5, max=60, wraparound=True)

	config.usage = ConfigSubsection()

	# "UserInterface" settings.
	#
	config.usage.menuType = ConfigSelection(default="standard", choices=[
		("horzanim", _("Horizontal menu")),
		("horzicon", _("Horizontal icons")),
		("standard", _("Vertical menu"))
	])
	config.usage.menuEntryStyle = ConfigSelection(default="text", choices=[
		("text", _("Entry text only")),
		("number", _("Entry number and text")),
		("image", _("Entry image and text")),
		("both", _("Entry image, number and text")),
	])
	config.usage.menuSortOrder = ConfigSelection(default="user", choices=[
		("alpha", _("Alphabetical")),
		("default", _("Default")),
		("user", _("User defined"))
	])
	config.usage.showScreenPath = ConfigSelection(default="off", choices=[
		("off", _("None")),
		("small", _("Small")),
		("large", _("Large"))
	])
	config.usage.sortExtensionslist = ConfigSelection(default="", choices=[
		("alpha", _("Alphabetical")),
		("", _("Default")),
		("user", _("User defined"))
	])
	config.usage.show_restart_network_extensionslist = ConfigYesNo(default=True)
	config.usage.sort_pluginlist = ConfigYesNo(default=True)
	config.usage.helpSortOrder = ConfigSelection(default="headings+alphabetic", choices=[
		("headings+alphabetic", _("Alphabetical under headings")),
		("flat+alphabetic", _("Flat alphabetical")),
		("flat+remotepos", _("Flat by position on remote")),
		("flat+remotegroups", _("Flat by key group on remote"))
	])
	config.usage.setupShowDefault = ConfigSelection(default="newline", choices=[
		("", _("Don't show default")),
		("spaces", _("Show default after description")),
		("newline", _("Show default on new line"))
	])
	config.usage.helpAnimationSpeed = ConfigSelection(default=10, choices=[
		(1, _("Very fast")),
		(5, _("Fast")),
		(10, _("Default")),
		(20, _("Slow")),
		(50, _("Very slow"))
	])
	config.usage.unhandledKeyTimeout = ConfigSelection(default=2, choices=[(x, ngettext("%d Second", "%d Seconds", x) % x) for x in range(1, 6)])
	config.usage.show_spinner = ConfigYesNo(default=True)
	config.usage.screenSaverStartTimer = ConfigSelection(default=0, choices=[(0, _("Disabled"))] + [(x, _("%d Seconds") % x) for x in (5, 10, 20, 30, 40, 50)] + [(x * 60, ngettext("%d Minute", "%d Minutes", x) % x) for x in (1, 5, 10, 15, 20, 30, 45, 60)])
	config.usage.screenSaverMoveTimer = ConfigSelection(default=10, choices=[(x, ngettext("%d Second", "%d Seconds", x) % x) for x in range(1, 61)])
	config.usage.informationShowAllMenuScreens = ConfigYesNo(default=False)
	config.usage.informationExtraSpacing = ConfigYesNo(False)
	config.usage.movieSelectionInMenu = ConfigYesNo(False)

	# Settings for servicemp3 and handling from cue sheet file.
	config.usage.useVideoCuesheet = ConfigYesNo(default=True)  # Use marker for video media file.
	config.usage.useAudioCuesheet = ConfigYesNo(default=True)  # Use marker for audio media file.
	config.usage.useChapterInfo = ConfigYesNo(default=True)  # Show chapter positions (gst >= 1 and supported media files).

	config.usage.shutdownOK = ConfigBoolean(default=True)
	config.usage.shutdownNOK_action = ConfigSelection(default="normal", choices=[
		("normal", _("Just boot")),
		("standby", _("Goto standby")),
		("deepstandby", _("Goto deep standby"))
	])
	config.usage.boot_action = ConfigSelection(default="normal", choices=[
		("normal", _("Just boot")),
		("standby", _("Goto standby"))
	])
	config.usage.showdish = ConfigSelection(default="flashing", choices=[
		("flashing", _("Flashing")),
		("normal", _("Not Flashing")),
		("off", _("Off"))
	])
	config.usage.multibouquet = ConfigYesNo(default=True)
	config.usage.numberZapDigits = ConfigSelection(default=4, choices=[(x, ngettext("%d Digit", "%d Digits", x) % x) for x in range(1, 6)])
	config.usage.numberZapDisplay = ConfigSelection(default="number", choices=[
		("number", _("Number only")),
		("name", _("Number and name")),
		("picon", _("Number and picon")),
		("both", _("Number, name and picon"))
	])
	config.usage.numberZapTimeoutFirst = ConfigSelection(default=3000, choices=[(x, ngettext("%.2f Second", "%.2f Seconds", x / 1000.0) % (x / 1000.0)) for x in range(500, 5001, 250)])
	config.usage.numberZapTimeoutOther = ConfigSelection(default=1000, choices=[(x, ngettext("%.2f Second", "%.2f Seconds", x / 1000.0) % (x / 1000.0)) for x in range(0, 5001, 250)])
	config.usage.numberZapTimeouts = ConfigSelection(default="default", choices=[
		("off", _("Off")),
		("default", _("Default")),
		("user", _("User defined"))
	])
	config.usage.numzappicon = ConfigYesNo(default=False)
	config.usage.use_pig = ConfigYesNo(default=False)
	config.usage.update_available = NoSave(ConfigYesNo(default=False))
	config.misc.ecm_info = ConfigYesNo(default=False)
	choices = [
		("dhcp-router", _("Router / Gateway")),
		("custom", _("Static IP / Custom"))
	]
	fileDom = fileReadXML(resolveFilename(SCOPE_SKINS, "dnsservers.xml"), source=MODULE_NAME)
	for dns in fileDom.findall("dnsserver"):
		if dns.get("key", ""):
			choices.append((dns.get("key"), _(dns.get("title"))))

	config.usage.dns = ConfigSelection(default="dhcp-router", choices=choices)
	config.usage.dnsMode = ConfigSelection(default=0, choices=[
		(0, _("Prefer IPv4")),
		(1, _("Prefer IPv6")),
		(2, _("IPv4 only")),
		(3, _("IPv6 only"))
	])
	config.usage.dnsSuffix = ConfigText(default="", fixed_size=False)
	config.usage.dnsRotate = ConfigYesNo(default=False)
	config.usage.subnetwork = ConfigYesNo(default=True)
	config.usage.subnetwork_cable = ConfigYesNo(default=True)
	config.usage.subnetwork_terrestrial = ConfigYesNo(default=True)

	def correctInvalidEPGDataChange(configElement):
		eServiceEvent.setUTF8CorrectMode(configElement.value)

	config.usage.correct_invalid_epgdata = ConfigSelection(default=1, choices=[
		(0, _("Disabled")),
		(1, _("Enabled")),
		(2, _("Debug"))
	])
	config.usage.correct_invalid_epgdata.addNotifier(correctInvalidEPGDataChange)

	def setNumberModeChange(configElement):
		eDVBDB.getInstance().setNumberingMode(configElement.value)
		config.usage.alternative_number_mode.value = config.usage.numberMode.value != 0
		refreshServiceList()

	config.usage.numberMode = ConfigSelection(default=0, choices=[
		(0, _("Unique numbering")),
		(1, _("Bouquets start at 1")),
		(2, _("LCN numbering"))
	])
	config.usage.numberMode.addNotifier(setNumberModeChange, initial_call=False)

	# Fallback old settigs will be removed later because this setting is probably used in plugins
	config.usage.alternative_number_mode = ConfigYesNo(default=config.usage.numberMode.value != 0)

	config.usage.hide_number_markers = ConfigYesNo(default=True)
	config.usage.hide_number_markers.addNotifier(refreshServiceList)

	config.usage.servicetype_icon_mode = ConfigSelection(default="0", choices=[
		("0", _("None")),
		("1", _("Left from service name")),
		("2", _("Right from service name"))
	])
	config.usage.servicetype_icon_mode.addNotifier(refreshServiceList)
	config.usage.crypto_icon_mode = ConfigSelection(default="0", choices=[
		("0", _("None")),
		("1", _("Left from service name")),
		("2", _("Right from service name"))
	])
	config.usage.crypto_icon_mode.addNotifier(refreshServiceList)
	config.usage.record_indicator_mode = ConfigSelection(default="3", choices=[
		("0", _("None")),
		("1", _("Left from service name")),
		("2", _("Right from service name")),
		("3", _("Red colored"))
	])
	config.usage.record_indicator_mode.addNotifier(refreshServiceList)

	# Just merge note, config.usage.servicelist_column was already there.
	config.usage.servicelist_column = ConfigSelection(default="-1", choices=[
		("-1", _("Disable")),
		("0", _("Event name only"))
	] + [(str(x), ngettext("%d Pixel wide", "%d Pixels wide", x) % x) for x in range(100, 1325, 25)])
	config.usage.servicelist_column.addNotifier(refreshServiceList)
	# Two lines options.
	config.usage.servicelist_twolines = ConfigYesNo(default=False)
	config.usage.servicelist_twolines.addNotifier(refreshServiceList)
	config.usage.serviceitems_per_page_twolines = ConfigSelectionNumber(default=12, stepwidth=1, min=4, max=20, wraparound=True)
	config.usage.servicelist_servicenumber_valign = ConfigSelection(default="0", choices=[
		("0", _("Centered")),
		("1", _("Upper line"))
	])
	config.usage.servicelist_servicenumber_valign.addNotifier(refreshServiceList)
	config.usage.servicelist_eventprogress_valign = ConfigSelection(default="0", choices=[
		("0", _("Centered")),
		("1", _("Upper line"))
	])
	config.usage.servicelist_eventprogress_valign.addNotifier(refreshServiceList)
	config.usage.servicelist_eventprogress_view_mode = ConfigSelection(default="0_barright", choices=[
		# Single.
		("0_no", _("No")),
		("0_barleft", _("Progress bar left")),
		("0_barright", _("Progress bar right")),
		("0_percleft", _("Percentage left")),
		("0_percright", _("Percentage right")),
		("0_minsleft", _("Remaining minutes left")),
		("0_minsright", _("Remaining minutes right")),
		# Bar value.
		("1_barpercleft", _("Progress bar/Percentage left")),
		("1_barpercright", _("Progress bar/Percentage right")),
		("1_barminsleft", _("Progress bar/Remaining minutes left")),
		("1_barminsright", _("Progress bar/Remaining minutes right")),
		# Value bar.
		("2_percbarleft", _("Percentage/Progress bar left")),
		("2_percbarright", _("Percentage/Progress bar right")),
		("2_minsbarleft", _("Remaining minutes/Progress bar left")),
		("2_minsbarright", _("Remaining minutes/Progress bar right"))
	])
	config.usage.servicelist_eventprogress_view_mode.addNotifier(refreshServiceList)
	#
	config.usage.servicelist_infokey = ConfigSelection(default="event", choices=[
		("epg", _("Single EPG")),
		("event", _("Event View"))
	])

	config.usage.service_icon_enable = ConfigYesNo(default=False)
	config.usage.service_icon_enable.addNotifier(refreshServiceList)
	config.usage.servicelist_picon_downsize = ConfigSelectionNumber(default=-2, stepwidth=1, min=-10, max=0, wraparound=True)
	config.usage.servicelist_picon_ratio = ConfigSelection(default="167", choices=[
		("167", _("XPicon, ZZZPicon")),
		("235", _("ZZPicon")),
		("250", _("ZPicon"))
	])
	config.usage.servicelist_cursor_behavior = ConfigSelection(default="keep", choices=[
		("standard", _("Standard")),
		("keep", _("Keep service")),
		("reverseB", _("Reverse bouquet buttons")),
		("keep reverseB", "%s + %s" % (_("Keep service"), _("Reverse bouquet buttons")))
	])
	config.usage.multiepg_ask_bouquet = ConfigYesNo(default=False)
	config.usage.showpicon = ConfigYesNo(default=True)

	# New ServiceList
	config.channelSelection = ConfigSubsection()
	config.channelSelection.showNumber = ConfigYesNo(default=True)
	config.channelSelection.showPicon = ConfigYesNo(default=False)
	config.channelSelection.showServiceTypeIcon = ConfigYesNo(default=False)
	config.channelSelection.showCryptoIcon = ConfigYesNo(default=False)
	config.channelSelection.recordIndicatorMode = ConfigSelection(default=2, choices=[
		(0, _("None")),
		(1, _("Record Icon")),
		(2, _("Colored Text"))
	])
	config.channelSelection.piconRatio = ConfigSelection(default=167, choices=[
		(167, _("XPicon, ZZZPicon")),
		(235, _("ZZPicon")),
		(250, _("ZPicon"))
	])

	config.channelSelection.showTimers = ConfigYesNo(default=False)

	screenChoiceList = [("", _("Legacy mode"))]
	widgetChoiceList = []
	styles = getcomponentTemplateNames("serviceList")
	default = ""
	if styles:
		for screen in domScreens:
			element, path = domScreens.get(screen, (None, None))
			if element.get("base") == "ChannelSelection":
				label = element.get("label", screen)
				screenChoiceList.append((screen, label))

		default = styles[0]
		for style in styles:
			widgetChoiceList.append((style, style))

	config.channelSelection.screenStyle = ConfigSelection(default="", choices=screenChoiceList)
	config.channelSelection.widgetStyle = ConfigSelection(default=default, choices=widgetChoiceList)

	# ########  Workaround for VTI Skins   ##############
	config.usage.picon_dir = ConfigDirectory(default="/usr/share/enigma2/picon")
	config.usage.movielist_show_picon = ConfigYesNo(default=False)
	config.usage.use_extended_pig = ConfigYesNo(default=False)
	config.usage.use_extended_pig_channelselection = ConfigYesNo(default=False)
	config.usage.servicelist_preview_mode = ConfigYesNo(default=False)
	config.usage.numberzap_show_picon = ConfigYesNo(default=False)
	config.usage.numberzap_show_servicename = ConfigYesNo(default=False)
	# ####################################################

	config.usage.panicbutton = ConfigYesNo(default=False)
	config.usage.panicchannel = ConfigInteger(default=1, limits=(1, 5000))
	config.usage.quickzap_bouquet_change = ConfigYesNo(default=False)
	config.usage.e1like_radio_mode = ConfigYesNo(default=True)

	config.usage.shutdown_msgbox_timeout = ConfigSelection(default="120", choices=[(str(x), _("%d Seconds") % x) for x in range(10, 301, 10)])
	choiceList = [
		("0", _("No timeout"))
	] + [(str(x), ngettext("%d Second", "%d Seconds", x) % x) for x in range(1, 21)]
	config.usage.infobar_timeout = ConfigSelection(default="5", choices=choiceList)
	config.usage.show_infobar_on_zap = ConfigYesNo(default=True)
	config.usage.show_infobar_on_skip = ConfigYesNo(default=True)
	config.usage.show_infobar_locked_on_pause = ConfigYesNo(default=True)
	config.usage.show_infobar_on_event_change = ConfigYesNo(default=False)
	config.usage.show_infobar_channel_number = ConfigYesNo(default=False)
	config.usage.show_infobar_lite = ConfigYesNo(default=False)
	config.usage.show_infobar_do_dimming = ConfigYesNo(default=False)
	config.usage.show_infobar_dimming_speed = ConfigSelectionNumber(min=1, max=40, stepwidth=1, default=10, wraparound=True)
	config.usage.show_second_infobar = ConfigSelection(default="1", choices=[
		("0", _("Off")),
		("1", _("Event Info")),
		("2", _("2nd InfoBar INFO")),
		("3", _("2nd InfoBar ECM"))
	])
	config.usage.second_infobar_timeout = ConfigSelection(default="5", choices=choiceList)
	config.usage.showInfoBarSubservices = ConfigSelection(default=1, choices=[
		(0, _("Off")),
		(1, _("If EPG available")),
		(2, _("Always"))
	])
	config.usage.subservice = ConfigSelection(default=3, choices=[
		(0, _("No, show the RecordTimer Overview")),
		(1, _("No, show the Plugin Browser")),
		(2, _("Yes, show RecordTimer if unavailable")),
		(3, _("Yes, show Plugin Browser if unavailable"))
	])

	def showsecondinfobarChanged(configElement):
		if config.usage.show_second_infobar.value != "INFOBAREPG":
			BoxInfo.setMutableItem("InfoBarEpg", True)
		else:
			BoxInfo.setMutableItem("InfoBarEpg", False)
	config.usage.show_second_infobar.addNotifier(showsecondinfobarChanged, immediate_feedback=True)
	config.usage.infobar_frontend_source = ConfigSelection(default="tuner", choices=[
		("settings", _("Settings")),
		("tuner", _("Tuner"))
	])

	config.usage.show_picon_bkgrn = ConfigSelection(default="transparent", choices=[
		("none", _("Disabled")),
		("transparent", _("Transparent")),
		("blue", _("Blue")),
		("red", _("Red")),
		("black", _("Black")),
		("white", _("White")),
		("lightgrey", _("Light Grey")),
		("grey", _("Grey"))
	])
	config.usage.show_genre_info = ConfigYesNo(default=True)
	config.usage.enable_tt_caching = ConfigYesNo(default=True)

	config.usage.tuxtxt_font_and_res = ConfigSelection(default="TTF_SD", choices=[
		("X11_SD", _("Fixed X11 font (SD)")),
		("TTF_SD", _("TrueType font (SD)")),
		("TTF_HD", _("TrueType font (HD)")),
		("TTF_FHD", _("TrueType font (full-HD)")),
		("expert_mode", _("Expert mode"))
	])
	config.usage.tuxtxt_UseTTF = ConfigSelection(default="1", choices=[("0", "0"), ("1", "1")])
	config.usage.tuxtxt_TTFBold = ConfigSelection(default="1", choices=[("0", "0"), ("1", "1")])
	config.usage.tuxtxt_TTFScreenResX = ConfigSelection(default="720", choices=[
		("720", "720"),
		("1280", "1280"),
		("1920", "1920")
	])
	config.usage.tuxtxt_StartX = ConfigInteger(default=50, limits=(0, 200))
	config.usage.tuxtxt_EndX = ConfigInteger(default=670, limits=(500, 1920))
	config.usage.tuxtxt_StartY = ConfigInteger(default=30, limits=(0, 200))
	config.usage.tuxtxt_EndY = ConfigInteger(default=555, limits=(400, 1080))
	choiceList = [(str(x), str(x)) for x in range(-9, 10)]
	config.usage.tuxtxt_TTFShiftY = ConfigSelection(default="2", choices=choiceList)
	config.usage.tuxtxt_TTFShiftX = ConfigSelection(default="0", choices=choiceList)
	config.usage.tuxtxt_TTFWidthFactor16 = ConfigInteger(default=29, limits=(8, 31))
	config.usage.tuxtxt_TTFHeightFactor16 = ConfigInteger(default=14, limits=(8, 31))
	config.usage.tuxtxt_CleanAlgo = ConfigInteger(default=0, limits=(0, 9))
	config.usage.tuxtxt_ConfFileHasBeenPatched = NoSave(ConfigYesNo(default=False))

	config.usage.tuxtxt_font_and_res.addNotifier(patchTuxtxtConfFile, initial_call=False, immediate_feedback=False, call_on_save_or_cancel=True)
	config.usage.tuxtxt_UseTTF.addNotifier(patchTuxtxtConfFile, initial_call=False, immediate_feedback=False, call_on_save_or_cancel=True)
	config.usage.tuxtxt_TTFBold.addNotifier(patchTuxtxtConfFile, initial_call=False, immediate_feedback=False, call_on_save_or_cancel=True)
	config.usage.tuxtxt_TTFScreenResX.addNotifier(patchTuxtxtConfFile, initial_call=False, immediate_feedback=False, call_on_save_or_cancel=True)
	config.usage.tuxtxt_StartX.addNotifier(patchTuxtxtConfFile, initial_call=False, immediate_feedback=False, call_on_save_or_cancel=True)
	config.usage.tuxtxt_EndX.addNotifier(patchTuxtxtConfFile, initial_call=False, immediate_feedback=False, call_on_save_or_cancel=True)
	config.usage.tuxtxt_StartY.addNotifier(patchTuxtxtConfFile, initial_call=False, immediate_feedback=False, call_on_save_or_cancel=True)
	config.usage.tuxtxt_EndY.addNotifier(patchTuxtxtConfFile, initial_call=False, immediate_feedback=False, call_on_save_or_cancel=True)
	config.usage.tuxtxt_TTFShiftY.addNotifier(patchTuxtxtConfFile, initial_call=False, immediate_feedback=False, call_on_save_or_cancel=True)
	config.usage.tuxtxt_TTFShiftX.addNotifier(patchTuxtxtConfFile, initial_call=False, immediate_feedback=False, call_on_save_or_cancel=True)
	config.usage.tuxtxt_TTFWidthFactor16.addNotifier(patchTuxtxtConfFile, initial_call=False, immediate_feedback=False, call_on_save_or_cancel=True)
	config.usage.tuxtxt_TTFHeightFactor16.addNotifier(patchTuxtxtConfFile, initial_call=False, immediate_feedback=False, call_on_save_or_cancel=True)
	config.usage.tuxtxt_CleanAlgo.addNotifier(patchTuxtxtConfFile, initial_call=False, immediate_feedback=False, call_on_save_or_cancel=True)

	config.usage.sort_settings = ConfigYesNo(default=False)
	config.usage.sort_menu_byname = ConfigYesNo(default=False)
	config.usage.sort_plugins_byname = ConfigYesNo(default=True)
	config.usage.plugins_sort_mode = ConfigSelection(default="user", choices=[
		("a_z", _("Alphabetical")),
		("default", _("Default")),
		("user", _("User defined"))
	])
	config.usage.plugin_sort_weight = ConfigDictionarySet()
	config.usage.menu_sort_weight = ConfigDictionarySet(default={"mainmenu": {"submenu": {}}})
	config.usage.movieplayer_pvrstate = ConfigYesNo(default=False)
	# config.usage.rc_model = ConfigSelection(default=DefaultRemote, choices=RemoteChoices)

	choiceList = [
		("0", _("No standby"))
	] + [(str(x), _("%d Seconds") % x) for x in (10, 30)] + [(str(x * 60), ngettext("%d Minute", "%d Minutes", x) % x) for x in (1, 2, 5, 10, 20, 30)] + [(str(x * 3600), ngettext("%d Hour", "%d Hours", x) % x) for x in (1, 2, 4)]
	config.usage.hdd_standby = ConfigSelection(default="300", choices=choiceList)
	config.usage.hdd_standby_in_standby = ConfigSelection(default="-1", choices=[("-1", _("Same as in active"))] + choiceList)
	config.usage.hdd_timer = ConfigYesNo(default=False)
	config.usage.showUnknownDevices = ConfigYesNo(default=False)
	config.usage.output_12V = ConfigSelection(default="do not change", choices=[
		("do not change", _("Do not change")),
		("off", _("Off")),
		("on", _("On"))
	])

	config.usage.pip_zero_button = ConfigSelection(default="standard", choices=[
		("standard", _("Standard")),
		("swap", _("Swap PiP and main picture")),
		("swapstop", _("Move PiP to main picture")),
		("stop", _("Stop PiP"))
	])
	config.usage.pip_hideOnExit = ConfigSelection(default="no", choices=[
		("no", _("No")),
		("popup", _("With pop up")),
		("without popup", _("Without pop up"))
	])
	choiceList = [
		("-1", _("Disabled")),
		("0", _("No timeout"))
	] + [(str(x * 60), ngettext("%d Minute", "%d Minutes", x) % x) for x in (1, 5, 10, 15, 30, 45, 60)]
	config.usage.pip_last_service_timeout = ConfigSelection(default="-1", choices=choiceList)

	defaultPath = resolveFilename(SCOPE_HDD)
	config.usage.default_path = ConfigSelection(default=defaultPath, choices=[(defaultPath, defaultPath)])
	config.usage.default_path.load()
	savedPath = config.usage.default_path.saved_value
	if savedPath:
		savedPath = pathjoin(savedPath, "")
		if savedPath and savedPath != defaultPath:
			config.usage.default_path.setChoices(default=defaultPath, choices=[(defaultPath, defaultPath), (savedPath, savedPath)])
			config.usage.default_path.value = savedPath
	config.usage.default_path.save()
	currentPath = config.usage.default_path.value
	print("[UsageConfig] Checking/Creating current movie directory '%s'." % currentPath)
	try:
		makedirs(currentPath, 0o755, exist_ok=True)
	except OSError as err:
		print("[UsageConfig] Error %d: Unable to create current movie directory '%s'!  (%s)" % (err.errno, currentPath, err.strerror))
		if defaultPath != currentPath:
			print("[UsageConfig] Checking/Creating default movie directory '%s'." % defaultPath)
			try:
				makedirs(defaultPath, 0o755, exist_ok=True)
			except OSError as err:
				print("[UsageConfig] Error %d: Unable to create default movie directory '%s'!  (%s)" % (err.errno, defaultPath, err.strerror))

	choiceList = [
		("<default>", "<Default>"),
		("<current>", "<Current>"),
		("<timer>", "<Timer>")
	]
	config.usage.timer_path = ConfigSelection(default="<default>", choices=choiceList)
	config.usage.timer_path.load()
	if config.usage.timer_path.saved_value:
		savedValue = config.usage.timer_path.saved_value if config.usage.timer_path.saved_value.startswith("<") else pathjoin(config.usage.timer_path.saved_value, "")
		if savedValue and savedValue not in choiceList:
			config.usage.timer_path.setChoices(choiceList + [(savedValue, savedValue)], default="<default>")
			config.usage.timer_path.value = savedValue
	config.usage.timer_path.save()

	config.usage.instantrec_path = ConfigSelection(default="<default>", choices=choiceList)
	config.usage.instantrec_path.load()
	if config.usage.instantrec_path.saved_value:
		savedValue = config.usage.instantrec_path.saved_value if config.usage.instantrec_path.saved_value.startswith("<") else pathjoin(config.usage.instantrec_path.saved_value, "")
		if savedValue and savedValue not in choiceList:
			config.usage.instantrec_path.setChoices(choiceList + [(savedValue, savedValue)], default="<default>")
			config.usage.instantrec_path.value = savedValue
	config.usage.instantrec_path.save()

	config.usage.movielist_trashcan = ConfigYesNo(default=True)
	config.usage.movielist_trashcan_network_clean = ConfigYesNo(default=False)
	config.usage.movielist_trashcan_days = ConfigSelection(default=8, choices=[(x, ngettext("%d Day", "%d Days", x) % x) for x in range(1, 32)])
	config.usage.movielist_trashcan_reserve = ConfigNumber(default=40)
	config.usage.on_movie_start = ConfigSelection(default="ask yes", choices=[
		("ask yes", _("Ask user (with default as 'Yes')")),
		("ask no", _("Ask user (with default as 'No')")),
		("resume", _("Resume from last position")),
		("beginning", _("Start from the beginning"))])
	config.usage.on_movie_stop = ConfigSelection(default="movielist", choices=[
		("ask", _("Ask user")),
		("movielist", _("Return to movie list")),
		("quit", _("Return to previous service"))
	])
	config.usage.on_movie_eof = ConfigSelection(default="movielist", choices=[
		("ask", _("Ask user")),
		("movielist", _("Return to movie list")),
		("quit", _("Return to previous service")),
		("pause", _("Pause movie at end")),
		("playlist", _("Play next (return to movie list)")),
		("playlistquit", _("Play next (return to previous service)")),
		("loop", _("Continues play (loop)")),
		("repeatcurrent", _("Repeat"))
	])
	config.usage.next_movie_msg = ConfigYesNo(default=True)
	config.usage.last_movie_played = ConfigText()
	config.usage.leave_movieplayer_onExit = ConfigSelection(default="no", choices=[
		("no", _("No")),
		("popup", _("With pop up")),
		("without popup", _("Without pop up")),
		("stop", _("Behave like STOP button"))
	])

	config.usage.setup_level = ConfigSelection(default="expert", choices=[
		("simple", _("Simple")),
		("intermediate", _("Intermediate")),
		("expert", _("Expert"))
	])

	choiceList = [
		(0, _("Disabled")),
		(-1, _("At end of current program"))
	] + [(x * 60, _("%d Minutes") % x) for x in range(15, 241, 15)]
	config.usage.sleepTimer = ConfigSelection(default=0, choices=choiceList)
	choiceList = [
		(0, _("Disabled"))
	] + [(x * 3600, ngettext("%d Hour", "%d Hours", x) % x) for x in range(1, 4)]
	config.usage.energyTimer = ConfigSelection(default=0, choices=choiceList)
	choiceList = [
		("standby", _("Standby")),
		("deepstandby", _("Deep Standby"))
	]
	config.usage.sleepTimerAction = ConfigSelection(default="deepstandby", choices=choiceList)
	config.usage.energyTimerAction = ConfigSelection(default="deepstandby", choices=choiceList)

	choiceList = [
		("show_menu", _("Show shut down menu")),
		("shutdown", _("Immediate shut down")),
		("standby", _("Standby")),
		("standby_noTVshutdown", _("Standby without TV shut down")),
		("sleeptimer", _("SleepTimer")),
		("schedulerStandby", _("Scheduler Standby")),
		("schedulerDeepStandby", _("Scheduler deep standby"))
	]
	config.usage.on_long_powerpress = ConfigSelection(default="show_menu", choices=choiceList)
	config.usage.on_short_powerpress = ConfigSelection(default="standby", choices=choiceList)

	def setLongPressedEmulationKey(configElement):
		eActionMap.getInstance().setLongPressedEmulationKey(configElement.value)

	config.usage.long_press_emulation_key = ConfigSelection(default=0, choices=[
		(0, _("None")),
		(KEYIDS["KEY_AUDIO"], "AUDIO"),
		(KEYIDS["KEY_END"], "END"),
		(KEYIDS["KEY_EPG"], "EPG"),
		(KEYIDS["KEY_FAVORITES"], "FAV"),
		(KEYIDS["KEY_HELP"], "HELP"),
		(KEYIDS["KEY_HOME"], "HOME"),
		(KEYIDS["KEY_INFO"], "INFO"),
		(KEYIDS["KEY_LIST"], "LIST"),
		(KEYIDS["KEY_RADIO"], "RADIO"),
		(KEYIDS["KEY_SUBTITLE"], "SUBTITLE"),
		(KEYIDS["KEY_TEXT"], "TEXT"),
		(KEYIDS["KEY_TV"], "TV"),
		(KEYIDS["KEY_VIDEO"], "MEDIA")
	])
	config.usage.long_press_emulation_key.addNotifier(setLongPressedEmulationKey)

	config.usage.alternatives_priority = ConfigSelection(default="0", choices=[
		("0", "DVB-S/-C/-T"),
		("1", "DVB-S/-T/-C"),
		("2", "DVB-C/-S/-T"),
		("3", "DVB-C/-T/-S"),
		("4", "DVB-T/-C/-S"),
		("5", "DVB-T/-S/-C"),
		("127", _("No priority"))
	])

	def setRemoteFallbackEnabled(configElement):
		eSettings.setRemoteFallbackEnabled(configElement.value)

	config.usage.remote_fallback_enabled = ConfigYesNo(default=False)
	config.usage.remote_fallback_enabled.addNotifier(setRemoteFallbackEnabled)

	def remote_fallback_changed(configElement):
		if configElement.value:
			configElement.value = "%s%s" % (not configElement.value.startswith("http://") and "http://" or "", configElement.value)
			configElement.value = "%s%s" % (configElement.value, configElement.value.count(":") == 1 and ":8001" or "")
	config.usage.remote_fallback = ConfigText(default="", fixed_size=False)
	config.usage.remote_fallback.addNotifier(remote_fallback_changed, immediate_feedback=False)
	config.usage.remote_fallback_import_url = ConfigText(default="", fixed_size=False)
	config.usage.remote_fallback_import_url.addNotifier(remote_fallback_changed, immediate_feedback=False)
	config.usage.remote_fallback_alternative = ConfigYesNo(default=False)
	config.usage.remote_fallback_dvb_t = ConfigText(default="", fixed_size=False)
	config.usage.remote_fallback_dvb_t.addNotifier(remote_fallback_changed, immediate_feedback=False)
	config.usage.remote_fallback_dvb_c = ConfigText(default="", fixed_size=False)
	config.usage.remote_fallback_dvb_c.addNotifier(remote_fallback_changed, immediate_feedback=False)
	config.usage.remote_fallback_atsc = ConfigText(default="", fixed_size=False)
	config.usage.remote_fallback_atsc.addNotifier(remote_fallback_changed, immediate_feedback=False)
	config.usage.remote_fallback_import = ConfigSelection(default="", choices=[("", _("No")), ("channels", _("Channels only")), ("channels_epg", _("Channels and EPG")), ("epg", _("EPG only"))])
	config.usage.remote_fallback_import_restart = ConfigYesNo(default=False)
	config.usage.remote_fallback_import_standby = ConfigYesNo(default=False)
	config.usage.remote_fallback_ok = ConfigYesNo(default=False)
	config.usage.remote_fallback_nok = ConfigYesNo(default=False)
	config.usage.remote_fallback_extension_menu = ConfigYesNo(default=False)
	config.usage.remote_fallback_external_timer = ConfigYesNo(default=False)
	config.usage.remote_fallback_external_timer_default = ConfigYesNo(default=True)
	config.usage.remote_fallback_openwebif_customize = ConfigYesNo(default=False)
	config.usage.remote_fallback_openwebif_userid = ConfigText(default="root")
	config.usage.remote_fallback_openwebif_password = ConfigPassword(default="default")
	config.usage.remote_fallback_openwebif_port = ConfigInteger(default=80, limits=(0, 65535))
	config.usage.remote_fallback_dvbt_region = ConfigText(default="Fallback DVB-T/T2 Europe")

	def setHttpStartDelay(configElement):
		eSettings.setHttpStartDelay(configElement.value)

	config.usage.http_startdelay = ConfigSelection(default=0, choices=[(0, _("Disabled"))] + [(x, _("%d ms") % x) for x in (10, 50, 100, 500, 1000, 2000)])
	config.usage.http_startdelay.addNotifier(setHttpStartDelay)

	config.usage.alternateGitHubDNS = ConfigYesNo(default=False)

	nims = [
		("-1", _("Auto")),
		("expert_mode", _("Expert mode")),
		("experimental_mode", _("Experimental mode"))
	]
	recNims = [
		("-2", _("Disabled")),
		("-1", _("Auto")),
		("expert_mode", _("Expert mode")),
		("experimental_mode", _("Experimental mode"))
	]
	nimsMulti = [
		("-1", _("Auto"))
	]
	recNimsMulti = [
		("-2", _("Disabled")),
		("-1", _("Auto"))
	]

	slots = len(nimmanager.nim_slots)
	multi = []
	slotsX = []
	for index in range(0, slots):
		slotName = nimmanager.nim_slots[index].getSlotName()
		nims.append((str(index), slotName))
		recNims.append((str(index), slotName))
		slotX = 2 ** index
		slotsX.append(slotX)
		multi.append((str(slotX), slotName))
		for x in range(index + 1, slots):
			slotX += 2 ** x
			name = nimmanager.nim_slots[x].getSlotName()
			if len(name.split()) == 2:
				name = name.split()[1]
			slotName += "+%s" % name
			slotsX.append(slotX)
			multi.append((str(slotX), slotName))

	# Advanced tuner combination up to 10 tuners.
	for slotX in range(1, 2 ** min(10, slots)):
		if slotX in slotsX:
			continue
		slotName = ""
		for x in range(0, min(10, slots)):
			if (slotX & 2 ** x):
				name = nimmanager.nim_slots[x].getSlotName()
				if not slotName:
					slotName = name
				else:
					if len(name.split()) == 2:
						name = name.split()[1]
					slotName += "+%s" % name
		if slotName:
			multi.append((str(slotX), slotName))
	#

	multi = sorted(multi, key=lambda x: x[1])
	nimsMulti.extend(multi)
	recNimsMulti.extend(multi)

	priorityStrictlyChoices = [
		("no", _("No")),
		("yes", _("Yes")),
		("while_available", _("While available"))
	]
	config.usage.frontend_priority = ConfigSelection(default="-1", choices=nims)
	config.usage.frontend_priority_multiselect = ConfigSelection(default="-1", choices=nimsMulti)
	config.usage.frontend_priority_strictly = ConfigSelection(default="no", choices=priorityStrictlyChoices)
	config.usage.frontend_priority_intval = NoSave(ConfigInteger(default=0, limits=(-99, maxsize)))
	config.usage.recording_frontend_priority = ConfigSelection(default="-2", choices=recNims)
	config.usage.recording_frontend_priority_multiselect = ConfigSelection(default="-2", choices=recNimsMulti)
	config.usage.recording_frontend_priority_strictly = ConfigSelection(default="no", choices=priorityStrictlyChoices)
	config.usage.recording_frontend_priority_intval = NoSave(ConfigInteger(default=0, limits=(-99, maxsize)))
	config.misc.disable_background_scan = ConfigYesNo(default=False)

	config.usage.jobtaksextensions = ConfigYesNo(default=True)

	config.usage.servicenum_fontsize = ConfigSelectionNumber(default=0, stepwidth=1, min=-10, max=10, wraparound=True)
	config.usage.servicename_fontsize = ConfigSelectionNumber(default=0, stepwidth=1, min=-10, max=10, wraparound=True)
	config.usage.serviceinfo_fontsize = ConfigSelectionNumber(default=0, stepwidth=1, min=-10, max=10, wraparound=True)
	config.usage.progressinfo_fontsize = ConfigSelectionNumber(default=0, stepwidth=1, min=-10, max=10, wraparound=True)
	config.usage.serviceitems_per_page = ConfigSelectionNumber(default=18, stepwidth=1, min=8, max=40, wraparound=True)
	config.usage.show_servicelist = ConfigYesNo(default=True)
	config.usage.servicelist_mode = ConfigSelection(default="standard", choices=[
		("standard", _("Standard")),
		("simple", _("Simple"))
	])
	config.usage.servicelistpreview_mode = ConfigYesNo(default=False)
	config.usage.tvradiobutton_mode = ConfigSelection(default="BouquetList", choices=[
		("ChannelList", _("Channel List")),
		("BouquetList", _("Bouquet List")),
		("MovieList", _("Movie List"))
	])
	config.usage.channelbutton_mode = ConfigSelection(default="0", choices=[
		("0", _("Just change channels")),
		("1", _("Channel List")),
		("2", _("Bouquet List")),
		("3", _("Just change Bouquet"))
	])
	config.usage.updownbutton_mode = ConfigSelection(default="1", choices=[
		("0", _("Just change channels")),
		("1", _("Channel List"))
	])
	config.usage.okbutton_mode = ConfigSelection(default="0", choices=[
		("0", _("InfoBar")),
		("1", _("Channel List"))
	])
	config.usage.show_bouquetalways = ConfigYesNo(default=False)
	config.usage.show_event_progress_in_servicelist = ConfigSelection(default="barright", choices=[
		("barleft", _("Progress bar left")),
		("barright", _("Progress bar right")),
		("percleft", _("Percentage left")),
		("percright", _("Percentage right")),
		("minsleft", _("Remaining minutes left")),
		("minsright", _("Remaining minutes right")),
		("no", _("No"))
	])
	config.usage.show_channel_numbers_in_servicelist = ConfigYesNo(default=True)
	config.usage.show_channel_jump_in_servicelist = ConfigSelection(default="quick", choices=[
		("quick", _("Quick Actions")),
		("alpha", _("Alpha")),
		("number", _("Number"))
	])

	config.usage.show_event_progress_in_servicelist.addNotifier(refreshServiceList)
	config.usage.show_channel_numbers_in_servicelist.addNotifier(refreshServiceList)

	# Standby.
	if BoxInfo.getItem("displaytype") in ("7segment",):
		config.usage.blinking_display_clock_during_recording = ConfigSelection(default="Rec", choices=[
			("Rec", _("REC")),
			("RecBlink", _("Blinking REC")),
			("Time", _("Time")),
			("Nothing", _("Nothing"))
		])
	else:
		config.usage.blinking_display_clock_during_recording = ConfigYesNo(default=False)

	# In use.
	if BoxInfo.getItem("displaytype") in ("textlcd",):
		config.usage.blinking_rec_symbol_during_recording = ConfigSelection(default="Channel", choices=[
			("Rec", _("REC Symbol")),
			("RecBlink", _("Blinking REC Symbol")),
			("Channel", _("Channel name"))
		])
	if BoxInfo.getItem("displaytype") in ("7segment",):
		config.usage.blinking_rec_symbol_during_recording = ConfigSelection(default="Rec", choices=[
			("Rec", _("REC")),
			("RecBlink", _("Blinking REC")),
			("Time", _("Time"))
		])
	else:
		config.usage.blinking_rec_symbol_during_recording = ConfigYesNo(default=True)

	config.usage.show_in_standby = ConfigSelection(default="time", choices=[
		("time", _("Time")),
		("nothing", _("Nothing"))
	])

	config.usage.show_in_operation = ConfigSelection(default="time", choices=[
		("time", _("Time")),
		("number", _("Channel Number")),
		("nothing", _("Nothing"))
	])

	config.usage.show_message_when_recording_starts = ConfigYesNo(default=True)

	config.usage.load_length_of_movies_in_moviellist = ConfigYesNo(default=True)
	config.usage.show_icons_in_movielist = ConfigSelection(default="i", choices=[
		("o", _("Off")),
		("p", _("Progress")),
		("s", _("Small progress")),
		("i", _("Icons"))
	])
	config.usage.movielist_unseen = ConfigYesNo(default=True)

	config.usage.swap_snr_on_osd = ConfigYesNo(default=False)
	choiceList = [
		("0", _("Skin Setting")),
		("1", _("Minutes")),
		("2", _("Minutes Seconds")),
		("3", _("Hours Minutes")),
		("4", _("Hours Minutes Seconds")),
		("5", _("Percentage"))
	]
	config.usage.swap_time_display_on_osd = ConfigSelection(default="0", choices=choiceList)
	config.usage.swap_media_time_display_on_osd = ConfigSelection(default="0", choices=choiceList)
	config.usage.swap_time_display_on_vfd = ConfigSelection(default="0", choices=choiceList)
	config.usage.swap_media_time_display_on_vfd = ConfigSelection(default="0", choices=choiceList)
	choiceList = [
		("0", _("Remaining")),
		("1", _("Elapsed")),
		("2", _("Elapsed & Remaining")),
		("3", _("Remaining & Elapsed"))
	]
	config.usage.swap_time_remaining_on_osd = ConfigSelection(default="0", choices=choiceList)
	config.usage.swap_time_remaining_on_vfd = ConfigSelection(default="0", choices=choiceList)
	config.usage.elapsed_time_positive_osd = ConfigYesNo(default=False)
	config.usage.elapsed_time_positive_vfd = ConfigYesNo(default=False)
	config.usage.lcd_scroll_delay = ConfigSelection(default="10000", choices=[
		("10000", _("%d Seconds") % 10),
		("20000", _("%d Seconds") % 20),
		("30000", _("%d Seconds") % 30),
		("60000", _("%d Minute") % 1),
		("300000", _("%d Minutes") % 5),
		("noscrolling", _("Off"))
	])
	config.usage.lcd_scroll_speed = ConfigSelection(default="300", choices=[
		("500", _("Slow")),
		("300", _("Normal")),
		("100", _("Fast"))
	])

	def SpinnerOnOffChanged(configElement):
		setSpinnerOnOff(int(configElement.value))
	config.usage.show_spinner.addNotifier(SpinnerOnOffChanged)

	def EnableTtCachingChanged(configElement):
		setEnableTtCachingOnOff(int(configElement.value))
	config.usage.enable_tt_caching.addNotifier(EnableTtCachingChanged)

	def TunerTypePriorityOrderChanged(configElement):
		setTunerTypePriorityOrder(int(configElement.value))
	config.usage.alternatives_priority.addNotifier(TunerTypePriorityOrderChanged, immediate_feedback=False)

	def PreferredTunerChanged(configElement):
		config.usage.frontend_priority_intval.setValue(calcFrontendPriorityIntval(config.usage.frontend_priority, config.usage.frontend_priority_multiselect, config.usage.frontend_priority_strictly))
		debugstring = ""
		elem2 = config.usage.frontend_priority_intval.value
		if (int(elem2) > 0) and (int(elem2) & eDVBFrontend.preferredFrontendBinaryMode):
			elem2 = int(elem2) - eDVBFrontend.preferredFrontendBinaryMode
			debugstring = debugstring + "Binary +"
		if (int(elem2) > 0) and (int(elem2) & eDVBFrontend.preferredFrontendPrioForced):
			elem2 = int(elem2) - eDVBFrontend.preferredFrontendPrioForced
			debugstring = debugstring + "Forced +"
		if (int(elem2) > 0) and (int(elem2) & eDVBFrontend.preferredFrontendPrioHigh):
			elem2 = int(elem2) - eDVBFrontend.preferredFrontendPrioHigh
			debugstring = debugstring + "High +"
		setPreferredTuner(int(config.usage.frontend_priority_intval.value))
	config.usage.frontend_priority.addNotifier(PreferredTunerChanged)
	config.usage.frontend_priority_multiselect.addNotifier(PreferredTunerChanged)
	config.usage.frontend_priority_strictly.addNotifier(PreferredTunerChanged)

	config.usage.hide_zap_errors = ConfigYesNo(default=True)

	def setUseCIAssignment(configElement):
		eSettings.setUseCIAssignment(configElement.value)

	config.misc.use_ci_assignment = ConfigYesNo(default=True)
	config.misc.use_ci_assignment.addNotifier(setUseCIAssignment)

	config.usage.hide_ci_messages = ConfigYesNo(default=False)
	config.usage.show_cryptoinfo = ConfigSelection(default=2, choices=[
		(0, _("Off")),
		(1, _("One line")),
		(2, _("Two lines"))
	])
	config.usage.show_eit_nownext = ConfigYesNo(default=True)
	config.usage.show_vcr_scart = ConfigYesNo(default=False)
	config.usage.pic_resolution = ConfigSelection(default=None, choices=[
		(None, _("Same resolution as skin")),
		("(720, 576)", "720x576"),
		("(1280, 720)", "1280x720"),
		("(1920, 1080)", "1920x1080")
	])
	config.usage.enable_delivery_system_workaround = ConfigYesNo(default=False)

	config.usage.date = ConfigSubsection()
	config.usage.date.enabled = NoSave(ConfigBoolean(default=False))
	config.usage.date.enabled_display = NoSave(ConfigBoolean(default=False))
	config.usage.time = ConfigSubsection()
	config.usage.time.enabled = NoSave(ConfigBoolean(default=False))
	config.usage.time.disabled = NoSave(ConfigBoolean(default=True))
	config.usage.time.enabled_display = NoSave(ConfigBoolean(default=False))
	config.usage.time.wide = NoSave(ConfigBoolean(default=False))
	config.usage.time.wide_display = NoSave(ConfigBoolean(default=False))

	# TRANSLATORS: Full date representation dayname daynum monthname year in strftime() format! See 'man strftime'.
	choicelist = [
		(_("%A %d %B %Y"), _("Dayname DD Month Year")),
		(_("%A %d. %B %Y"), _("Dayname DD. Month Year")),
		(_("%A %-d %B %Y"), _("Dayname D Month Year")),
		(_("%A %-d. %B %Y"), _("Dayname D. Month Year")),
		(_("%A %d-%B-%Y"), _("Dayname DD-Month-Year")),
		(_("%A %-d-%B-%Y"), _("Dayname D-Month-Year")),
		(_("%A %d/%m/%Y"), _("Dayname DD/MM/Year")),
		(_("%A %d.%m.%Y"), _("Dayname DD.MM.Year")),
		(_("%A %-d/%m/%Y"), _("Dayname D/MM/Year")),
		(_("%A %-d.%m.%Y"), _("Dayname D.MM.Year")),
		(_("%A %d/%-m/%Y"), _("Dayname DD/M/Year")),
		(_("%A %d.%-m.%Y"), _("Dayname DD.M.Year")),
		(_("%A %-d/%-m/%Y"), _("Dayname D/M/Year")),
		(_("%A %-d.%-m.%Y"), _("Dayname D.M.Year")),
		(_("%A %B %d %Y"), _("Dayname Month DD Year")),
		(_("%A %B %-d %Y"), _("Dayname Month D Year")),
		(_("%A %B-%d-%Y"), _("Dayname Month-DD-Year")),
		(_("%A %B-%-d-%Y"), _("Dayname Month-D-Year")),
		(_("%A %m/%d/%Y"), _("Dayname MM/DD/Year")),
		(_("%A %-m/%d/%Y"), _("Dayname M/DD/Year")),
		(_("%A %m/%-d/%Y"), _("Dayname MM/D/Year")),
		(_("%A %-m/%-d/%Y"), _("Dayname M/D/Year")),
		(_("%A %Y %B %d"), _("Dayname Year Month DD")),
		(_("%A %Y %B %-d"), _("Dayname Year Month D")),
		(_("%A %Y-%B-%d"), _("Dayname Year-Month-DD")),
		(_("%A %Y-%B-%-d"), _("Dayname Year-Month-D")),
		(_("%A %Y/%m/%d"), _("Dayname Year/MM/DD")),
		(_("%A %Y/%m/%-d"), _("Dayname Year/MM/D")),
		(_("%A %Y/%-m/%d"), _("Dayname Year/M/DD")),
		(_("%A %Y/%-m/%-d"), _("Dayname Year/M/D"))]

	config.usage.date.dayfull = ConfigSelection(default=_("%A %d.%m.%Y") if config.misc.locale.value == "de_DE" else _("%A %-d %B %Y"), choices=choicelist)

	# TRANSLATORS: Long date representation short dayname daynum monthname year in strftime() format! See 'man strftime'.
	config.usage.date.shortdayfull = ConfigText(default=_("%a %-d %B %Y"))

	# TRANSLATORS: Long date representation short dayname daynum short monthname year in strftime() format! See 'man strftime'.
	config.usage.date.daylong = ConfigText(default=_("%a %-d %b %Y"))

	# TRANSLATORS: Short date representation dayname daynum short monthname in strftime() format! See 'man strftime'.
	config.usage.date.dayshortfull = ConfigText(default=_("%A %-d %B"))

	# TRANSLATORS: Short date representation short dayname daynum short monthname in strftime() format! See 'man strftime'.
	config.usage.date.dayshort = ConfigText(default=_("%a %-d %b"))

	# TRANSLATORS: Small date representation short dayname daynum in strftime() format! See 'man strftime'.
	config.usage.date.daysmall = ConfigText(default=_("%a %-d"))

	# TRANSLATORS: Full date representation daynum monthname year in strftime() format! See 'man strftime'.
	config.usage.date.full = ConfigText(default=_("%-d %B %Y"))

	# TRANSLATORS: Long date representation daynum short monthname year in strftime() format! See 'man strftime'.
	config.usage.date.long = ConfigText(default=_("%-d %b %Y"))

	# TRANSLATORS: Small date representation daynum short monthname in strftime() format! See 'man strftime'.
	config.usage.date.short = ConfigText(default=_("%-d %b"))

	def setDateStyles(configElement):
		dateStyles = {
			# dayfull            shortdayfull      daylong           dayshortfull   dayshort       daysmall    full           long           short
			_("%A %d %B %Y"): (_("%a %d %B %Y"), _("%a %d %b %Y"), _("%A %d %B"), _("%a %d %b"), _("%a %d"), _("%d %B %Y"), _("%d %b %Y"), _("%d %b")),
			_("%A %d. %B %Y"): (_("%a %d. %B %Y"), _("%a %d. %b %Y"), _("%A %d. %B"), _("%a %d. %b"), _("%a %d"), _("%d. %B %Y"), _("%d. %b %Y"), _("%d. %b")),
			_("%A %-d %B %Y"): (_("%a %-d %B %Y"), _("%a %-d %b %Y"), _("%A %-d %B"), _("%a %-d %b"), _("%a %-d"), _("%-d %B %Y"), _("%-d %b %Y"), _("%-d %b")),
			_("%A %-d. %B %Y"): (_("%a %-d. %B %Y"), _("%a %-d. %b %Y"), _("%A %-d. %B"), _("%a %-d. %b"), _("%a %-d"), _("%-d. %B %Y"), _("%-d. %b %Y"), _("%-d. %b")),
			_("%A %d-%B-%Y"): (_("%a %d-%B-%Y"), _("%a %d-%b-%Y"), _("%A %d-%B"), _("%a %d-%b"), _("%a %d"), _("%d-%B-%Y"), _("%d-%b-%Y"), _("%d-%b")),
			_("%A %-d-%B-%Y"): (_("%a %-d-%B-%Y"), _("%a %-d-%b-%Y"), _("%A %-d-%B"), _("%a %-d-%b"), _("%a %-d"), _("%-d-%B-%Y"), _("%-d-%b-%Y"), _("%-d-%b")),
			_("%A %d/%m/%Y"): (_("%a %d/%m/%Y"), _("%a %d/%m/%Y"), _("%A %d/%m"), _("%a %d/%m"), _("%a %d"), _("%d/%m/%Y"), _("%d/%m/%Y"), _("%d/%m")),
			_("%A %d.%m.%Y"): (_("%a %d.%m.%Y"), _("%a %d.%m.%Y"), _("%A %d.%m"), _("%a %d.%m"), _("%a %d"), _("%d.%m.%Y"), _("%d.%m.%Y"), _("%d.%m")),
			_("%A %-d/%m/%Y"): (_("%a %-d/%m/%Y"), _("%a %-d/%m/%Y"), _("%A %-d/%m"), _("%a %-d/%m"), _("%a %-d"), _("%-d/%m/%Y"), _("%-d/%m/%Y"), _("%-d/%m")),
			_("%A %-d.%m.%Y"): (_("%a %-d.%m.%Y"), _("%a %-d.%m.%Y"), _("%A %-d.%m"), _("%a %-d.%m"), _("%a %-d"), _("%-d.%m.%Y"), _("%-d.%m.%Y"), _("%-d.%m")),
			_("%A %d/%-m/%Y"): (_("%a %d/%-m/%Y"), _("%a %d/%-m/%Y"), _("%A %d/%-m"), _("%a %d/%-m"), _("%a %d"), _("%d/%-m/%Y"), _("%d/%-m/%Y"), _("%d/%-m")),
			_("%A %d.%-m.%Y"): (_("%a %d.%-m.%Y"), _("%a %d.%-m.%Y"), _("%A %d.%-m"), _("%a %d.%-m"), _("%a %d"), _("%d.%-m.%Y"), _("%d.%-m.%Y"), _("%d.%-m")),
			_("%A %-d/%-m/%Y"): (_("%a %-d/%-m/%Y"), _("%a %-d/%-m/%Y"), _("%A %-d/%-m"), _("%a %-d/%-m"), _("%a %-d"), _("%-d/%-m/%Y"), _("%-d/%-m/%Y"), _("%-d/%-m")),
			_("%A %-d.%-m.%Y"): (_("%a %-d.%-m.%Y"), _("%a %-d.%-m.%Y"), _("%A %-d.%-m"), _("%a %-d.%-m"), _("%a %-d"), _("%-d.%-m.%Y"), _("%-d.%-m.%Y"), _("%-d.%-m")),
			_("%A %B %d %Y"): (_("%a %B %d %Y"), _("%a %b %d %Y"), _("%A %B %d"), _("%a %b %d"), _("%a %d"), _("%B %d %Y"), _("%b %d %Y"), _("%b %d")),
			_("%A %B %-d %Y"): (_("%a %B %-d %Y"), _("%a %b %-d %Y"), _("%A %B %-d"), _("%a %b %-d"), _("%a %-d"), _("%B %-d %Y"), _("%b %-d %Y"), _("%b %-d")),
			_("%A %B-%d-%Y"): (_("%a %B-%d-%Y"), _("%a %b-%d-%Y"), _("%A %B-%d"), _("%a %b-%d"), _("%a %d"), _("%B-%d-%Y"), _("%b-%d-%Y"), _("%b-%d")),
			_("%A %B-%-d-%Y"): (_("%a %B-%-d-%Y"), _("%a %b-%-d-%Y"), _("%A %B-%-d"), _("%a %b-%-d"), _("%a %-d"), _("%B-%-d-%Y"), _("%b-%-d-%Y"), _("%b-%-d")),
			_("%A %m/%d/%Y"): (_("%a %m/%d/%Y"), _("%a %m/%d/%Y"), _("%A %m/%d"), _("%a %m/%d"), _("%a %d"), _("%m/%d/%Y"), _("%m/%d/%Y"), _("%m/%d")),
			_("%A %-m/%d/%Y"): (_("%a %-m/%d/%Y"), _("%a %-m/%d/%Y"), _("%A %-m/%d"), _("%a %-m/%d"), _("%a %d"), _("%-m/%d/%Y"), _("%-m/%d/%Y"), _("%-m/%d")),
			_("%A %m/%-d/%Y"): (_("%a %m/%-d/%Y"), _("%a %m/%-d/%Y"), _("%A %m/%-d"), _("%a %m/%-d"), _("%a %-d"), _("%m/%-d/%Y"), _("%m/%-d/%Y"), _("%m/%-d")),
			_("%A %-m/%-d/%Y"): (_("%a %-m/%-d/%Y"), _("%a %-m/%-d/%Y"), _("%A %-m/%-d"), _("%a %-m/%-d"), _("%a %-d"), _("%-m/%-d/%Y"), _("%-m/%-d/%Y"), _("%-m/%-d")),
			_("%A %Y %B %d"): (_("%a %Y %B %d"), _("%a %Y %b %d"), _("%A %B %d"), _("%a %b %d"), _("%a %d"), _("%Y %B %d"), _("%Y %b %d"), _("%b %d")),
			_("%A %Y %B %-d"): (_("%a %Y %B %-d"), _("%a %Y %b %-d"), _("%A %B %-d"), _("%a %b %-d"), _("%a %-d"), _("%Y %B %-d"), _("%Y %b %-d"), _("%b %-d")),
			_("%A %Y-%B-%d"): (_("%a %Y-%B-%d"), _("%a %Y-%b-%d"), _("%A %B-%d"), _("%a %b-%d"), _("%a %d"), _("%Y-%B-%d"), _("%Y-%b-%d"), _("%b-%d")),
			_("%A %Y-%B-%-d"): (_("%a %Y-%B-%-d"), _("%a %Y-%b-%-d"), _("%A %B-%-d"), _("%a %b-%-d"), _("%a %-d"), _("%Y-%B-%-d"), _("%Y-%b-%-d"), _("%b-%-d")),
			_("%A %Y/%m/%d"): (_("%a %Y/%m/%d"), _("%a %Y/%m/%d"), _("%A %m/%d"), _("%a %m/%d"), _("%a %d"), _("%Y/%m/%d"), _("%Y/%m/%d"), _("%m/%d")),
			_("%A %Y/%m/%-d"): (_("%a %Y/%m/%-d"), _("%a %Y/%m/%-d"), _("%A %m/%-d"), _("%a %m/%-d"), _("%a %-d"), _("%Y/%m/%-d"), _("%Y/%m/%-d"), _("%m/%-d")),
			_("%A %Y/%-m/%d"): (_("%a %Y/%-m/%d"), _("%a %Y/%-m/%d"), _("%A %-m/%d"), _("%a %-m/%d"), _("%a %d"), _("%Y/%-m/%d"), _("%Y/%-m/%d"), _("%-m/%d")),
			_("%A %Y/%-m/%-d"): (_("%a %Y/%-m/%-d"), _("%a %Y/%-m/%-d"), _("%A %-m/%-d"), _("%a %-m/%-d"), _("%a %-d"), _("%Y/%-m/%-d"), _("%Y/%-m/%-d"), _("%-m/%-d"))
		}
		style = dateStyles.get(configElement.value, ((_("Invalid")) * 8))
		config.usage.date.shortdayfull.value = style[0]
		config.usage.date.shortdayfull.save()
		config.usage.date.daylong.value = style[1]
		config.usage.date.daylong.save()
		config.usage.date.dayshortfull.value = style[2]
		config.usage.date.dayshortfull.save()
		config.usage.date.dayshort.value = style[3]
		config.usage.date.dayshort.save()
		config.usage.date.daysmall.value = style[4]
		config.usage.date.daysmall.save()
		config.usage.date.full.value = style[5]
		config.usage.date.full.save()
		config.usage.date.long.value = style[6]
		config.usage.date.long.save()
		config.usage.date.short.value = style[7]
		config.usage.date.short.save()

	config.usage.date.dayfull.addNotifier(setDateStyles)

	# TRANSLATORS: Full time representation hour:minute:seconds.
	if nl_langinfo(AM_STR) and nl_langinfo(PM_STR):
		config.usage.time.long = ConfigSelection(default=_("%T"), choices=[
			(_("%T"), _("HH:mm:ss")),
			(_("%-H:%M:%S"), _("H:mm:ss")),
			(_("%I:%M:%S%^p"), _("hh:mm:ssAM/PM")),
			(_("%-I:%M:%S%^p"), _("h:mm:ssAM/PM")),
			(_("%I:%M:%S%P"), _("hh:mm:ssam/pm")),
			(_("%-I:%M:%S%P"), _("h:mm:ssam/pm")),
			(_("%I:%M:%S"), _("hh:mm:ss")),
			(_("%-I:%M:%S"), _("h:mm:ss"))
		])
	else:
		config.usage.time.long = ConfigSelection(default=_("%T"), choices=[
			(_("%T"), _("HH:mm:ss")),
			(_("%-H:%M:%S"), _("H:mm:ss")),
			(_("%I:%M:%S"), _("hh:mm:ss")),
			(_("%-I:%M:%S"), _("h:mm:ss"))
		])

	# TRANSLATORS: Time representation hour:minute:seconds for 24 hour clock or 12 hour clock without AM/PM and hour:minute for 12 hour clocks with AM/PM.
	config.usage.time.mixed = ConfigText(default=_("%T"))

	# TRANSLATORS: Short time representation hour:minute (Same as "Default").
	config.usage.time.short = ConfigText(default=_("%R"))

	def setTimeStyles(configElement):
		timeStyles = {
			# long      mixed    short
			_("%T"): (_("%T"), _("%R")),
			_("%-H:%M:%S"): (_("%-H:%M:%S"), _("%-H:%M")),
			_("%I:%M:%S%^p"): (_("%I:%M%^p"), _("%I:%M%^p")),
			_("%-I:%M:%S%^p"): (_("%-I:%M%^p"), _("%-I:%M%^p")),
			_("%I:%M:%S%P"): (_("%I:%M%P"), _("%I:%M%P")),
			_("%-I:%M:%S%P"): (_("%-I:%M%P"), _("%-I:%M%P")),
			_("%I:%M:%S"): (_("%I:%M:%S"), _("%I:%M")),
			_("%-I:%M:%S"): (_("%-I:%M:%S"), _("%-I:%M"))
		}
		style = timeStyles.get(configElement.value, ((_("Invalid")) * 2))
		config.usage.time.mixed.value = style[0]
		config.usage.time.mixed.save()
		config.usage.time.short.value = style[1]
		config.usage.time.short.save()
		config.usage.time.wide.value = style[1].endswith(("P", "p"))

	config.usage.time.long.addNotifier(setTimeStyles)

	try:
		dateEnabled, timeEnabled = parameters.get("AllowUserDatesAndTimes", (0, 0))
	except Exception as error:
		print("[UsageConfig] Error loading 'AllowUserDatesAndTimes' skin parameter! (%s)" % error)
		dateEnabled, timeEnabled = (0, 0)
	if dateEnabled:
		config.usage.date.enabled.value = True
	else:
		config.usage.date.enabled.value = False
		config.usage.date.dayfull.value = config.usage.date.dayfull.default
	if timeEnabled:
		config.usage.time.enabled.value = True
		config.usage.time.disabled.value = not config.usage.time.enabled.value
	else:
		config.usage.time.enabled.value = False
		config.usage.time.disabled.value = not config.usage.time.enabled.value
		config.usage.time.long.value = config.usage.time.long.default

	# TRANSLATORS: Compact date representation (for VFD) daynum short monthname in strftime() format! See 'man strftime'.
	config.usage.date.display = ConfigSelection(default=_("%-d %b"), choices=[
		("", _("Hidden / Blank")),
		(_("%d %b"), _("Day DD Mon")),
		(_("%-d %b"), _("Day D Mon")),
		(_("%d-%b"), _("Day DD-Mon")),
		(_("%-d-%b"), _("Day D-Mon")),
		(_("%d/%m"), _("Day DD/MM")),
		(_("%-d/%m"), _("Day D/MM")),
		(_("%d/%-m"), _("Day DD/M")),
		(_("%-d/%-m"), _("Day D/M")),
		(_("%b %d"), _("Day Mon DD")),
		(_("%b %-d"), _("Day Mon D")),
		(_("%b-%d"), _("Day Mon-DD")),
		(_("%b-%-d"), _("Day Mon-D")),
		(_("%m/%d"), _("Day MM/DD")),
		(_("%m/%-d"), _("Day MM/D")),
		(_("%-m/%d"), _("Day M/DD")),
		(_("%-m/%-d"), _("Day M/D"))
	])

	config.usage.date.displayday = ConfigText(default=_("%a %-d+%b_"))
	config.usage.date.display_template = ConfigText(default=_("%-d+%b_"))
	config.usage.date.compact = ConfigText(default=_("%-d+%b_"))
	config.usage.date.compressed = ConfigText(default=_("%-d+%b_"))

	timeDisplayValue = [_("%R")]

	def adjustDisplayDates():
		if timeDisplayValue[0] == "":
			if config.usage.date.display.value == "":  # If the date and time are both hidden output a space to blank the VFD display.
				config.usage.date.compact.value = " "
				config.usage.date.compressed.value = " "
			else:
				config.usage.date.compact.value = config.usage.date.displayday.value
				config.usage.date.compressed.value = config.usage.date.displayday.value
		else:
			if config.usage.time.wide_display.value:
				config.usage.date.compact.value = config.usage.date.display_template.value.replace("_", "").replace("=", "").replace("+", "")
				config.usage.date.compressed.value = config.usage.date.display_template.value.replace("_", "").replace("=", "").replace("+", "")
			else:
				config.usage.date.compact.value = config.usage.date.display_template.value.replace("_", " ").replace("=", "-").replace("+", " ")
				config.usage.date.compressed.value = config.usage.date.display_template.value.replace("_", " ").replace("=", "").replace("+", "")
		config.usage.date.compact.save()
		config.usage.date.compressed.save()

	def setDateDisplayStyles(configElement):
		dateDisplayStyles = {
			# display      displayday     template
			"": ("", ""),
			_("%d %b"): (_("%a %d %b"), _("%d+%b_")),
			_("%-d %b"): (_("%a %-d %b"), _("%-d+%b_")),
			_("%d-%b"): (_("%a %d-%b"), _("%d=%b_")),
			_("%-d-%b"): (_("%a %-d-%b"), _("%-d=%b_")),
			_("%d/%m"): (_("%a %d/%m"), _("%d/%m ")),
			_("%-d/%m"): (_("%a %-d/%m"), _("%-d/%m ")),
			_("%d/%-m"): (_("%a %d/%-m"), _("%d/%-m ")),
			_("%-d/%-m"): (_("%a %-d/%-m"), _("%-d/%-m ")),
			_("%b %d"): (_("%a %b %d"), _("%b+%d ")),
			_("%b %-d"): (_("%a %b %-d"), _("%b+%-d ")),
			_("%b-%d"): (_("%a %b-%d"), _("%b=%d ")),
			_("%b-%-d"): (_("%a %b-%-d"), _("%b=%-d ")),
			_("%m/%d"): (_("%a %m/%d"), _("%m/%d ")),
			_("%m/%-d"): (_("%a %m/%-d"), _("%m/%-d ")),
			_("%-m/%d"): (_("%a %-m/%d"), _("%-m/%d ")),
			_("%-m/%-d"): (_("%a %-m/%-d"), _("%-m/%-d "))
		}
		style = dateDisplayStyles.get(configElement.value, ((_("Invalid")) * 2))
		config.usage.date.displayday.value = style[0]
		config.usage.date.displayday.save()
		config.usage.date.display_template.value = style[1]
		config.usage.date.display_template.save()
		adjustDisplayDates()

	config.usage.date.display.addNotifier(setDateDisplayStyles)

	# TRANSLATORS: Short time representation hour:minute (Same as "Default").
	if nl_langinfo(AM_STR) and nl_langinfo(PM_STR):
		config.usage.time.display = ConfigSelection(default=_("%R"), choices=[
			("", _("Hidden / Blank")),
			(_("%R"), _("HH:mm")),
			(_("%-H:%M"), _("H:mm")),
			(_("%I:%M%^p"), _("hh:mmAM/PM")),
			(_("%-I:%M%^p"), _("h:mmAM/PM")),
			(_("%I:%M%P"), _("hh:mmam/pm")),
			(_("%-I:%M%P"), _("h:mmam/pm")),
			(_("%I:%M"), _("hh:mm")),
			(_("%-I:%M"), _("h:mm"))
		])
	else:
		config.usage.time.display = ConfigSelection(default=_("%R"), choices=[
			("", _("Hidden / Blank")),
			(_("%R"), _("HH:mm")),
			(_("%-H:%M"), _("H:mm")),
			(_("%I:%M"), _("hh:mm")),
			(_("%-I:%M"), _("h:mm"))
		])

	def setTimeDisplayStyles(configElement):
		timeDisplayValue[0] = config.usage.time.display.value
		config.usage.time.wide_display.value = configElement.value.endswith(("P", "p"))
		adjustDisplayDates()

	config.usage.time.display.addNotifier(setTimeDisplayStyles)

	try:
		dateDisplayEnabled, timeDisplayEnabled = parameters.get("AllowUserDatesAndTimesDisplay", (0, 0))
	except Exception as error:
		print("[UsageConfig] Error loading 'AllowUserDatesAndTimesDisplay' display skin parameter! (%s)" % error)
		dateDisplayEnabled, timeDisplayEnabled = (0, 0)
	if dateDisplayEnabled:
		config.usage.date.enabled_display.value = True
	else:
		config.usage.date.enabled_display.value = False
		config.usage.date.display.value = config.usage.date.display.default
	if timeDisplayEnabled:
		config.usage.time.enabled_display.value = True
	else:
		config.usage.time.enabled_display.value = False
		config.usage.time.display.value = config.usage.time.display.default

	config.usage.boolean_graphic = ConfigYesNo(default=False)
	config.usage.show_slider_value = ConfigYesNo(default=True)
	config.usage.cursorscroll = ConfigSelectionNumber(min=0, max=50, stepwidth=5, default=0, wraparound=True)

	config.epg = ConfigSubsection()
	config.epg.eit = ConfigYesNo(default=True)
	config.epg.mhw = ConfigYesNo(default=False)
	config.epg.freesat = ConfigYesNo(default=True)
	config.epg.viasat = ConfigYesNo(default=True)
	config.epg.netmed = ConfigYesNo(default=True)
	config.epg.virgin = ConfigYesNo(default=False)
	config.epg.opentv = ConfigYesNo(default=True)
	config.epg.saveepg = ConfigYesNo(default=True)

	def showEPGChanged(configElement):
		from enigma import eEPGCache
		eEPGCache.getInstance().setSave(configElement.value)

	config.epg.saveepg.addNotifier(showEPGChanged, immediate_feedback=False, initial_call=False)

	config.misc.showradiopic = ConfigYesNo(default=True)
	config.misc.bootvideo = ConfigYesNo(default=True)

	def EpgSettingsChanged(configElement):
		from enigma import eEPGCache
		mask = 0xffffffff
		if not config.epg.eit.value:
			mask &= ~(eEPGCache.NOWNEXT | eEPGCache.SCHEDULE | eEPGCache.SCHEDULE_OTHER)
		if not config.epg.mhw.value:
			mask &= ~eEPGCache.MHW
		if not config.epg.freesat.value:
			mask &= ~(eEPGCache.FREESAT_NOWNEXT | eEPGCache.FREESAT_SCHEDULE | eEPGCache.FREESAT_SCHEDULE_OTHER)
		if not config.epg.viasat.value:
			mask &= ~eEPGCache.VIASAT
		if not config.epg.netmed.value:
			mask &= ~(eEPGCache.NETMED_SCHEDULE | eEPGCache.NETMED_SCHEDULE_OTHER)
		if not config.epg.virgin.value:
			mask &= ~(eEPGCache.VIRGIN_NOWNEXT | eEPGCache.VIRGIN_SCHEDULE)
		if not config.epg.opentv.value:
			mask &= ~eEPGCache.OPENTV
		eEPGCache.getInstance().setEpgSources(mask)
	config.epg.eit.addNotifier(EpgSettingsChanged, initial_call=False)
	config.epg.mhw.addNotifier(EpgSettingsChanged, initial_call=False)
	config.epg.freesat.addNotifier(EpgSettingsChanged, initial_call=False)
	config.epg.viasat.addNotifier(EpgSettingsChanged, initial_call=False)
	config.epg.netmed.addNotifier(EpgSettingsChanged, initial_call=False)
	config.epg.virgin.addNotifier(EpgSettingsChanged, initial_call=False)
	config.epg.opentv.addNotifier(EpgSettingsChanged)

	config.epg.maxdays = ConfigSelectionNumber(min=1, max=365, stepwidth=1, default=7, wraparound=True)

	def EpgmaxdaysChanged(configElement):
		from enigma import eEPGCache
		eEPGCache.getInstance().setEpgmaxdays(config.epg.maxdays.getValue())
	config.epg.maxdays.addNotifier(EpgmaxdaysChanged)

	config.epg.histminutes = ConfigSelectionNumber(min=0, max=1440, stepwidth=30, default=0, wraparound=True)

	def EpgHistorySecondsChanged(configElement):
		eEPGCache.getInstance().setEpgHistorySeconds(config.epg.histminutes.value * 60)
	config.epg.histminutes.addNotifier(EpgHistorySecondsChanged)

	config.epg.cacheloadsched = ConfigYesNo(default=False)
	config.epg.cachesavesched = ConfigYesNo(default=False)

	def EpgCacheLoadSchedChanged(configElement):
		import Components.EpgLoadSave
		Components.EpgLoadSave.EpgCacheLoadCheck()

	def EpgCacheSaveSchedChanged(configElement):
		import Components.EpgLoadSave
		Components.EpgLoadSave.EpgCacheSaveCheck()
	config.epg.cacheloadsched.addNotifier(EpgCacheLoadSchedChanged, immediate_feedback=False)
	config.epg.cachesavesched.addNotifier(EpgCacheSaveSchedChanged, immediate_feedback=False)
	config.epg.cacheloadtimer = ConfigSelectionNumber(default=24, stepwidth=1, min=1, max=24, wraparound=True)
	config.epg.cachesavetimer = ConfigSelectionNumber(default=24, stepwidth=1, min=1, max=24, wraparound=True)

	def debugEPGhanged(configElement):
		from enigma import eEPGCache
		eEPGCache.getInstance().setDebug(configElement.value)

	config.crash.debugEPG.addNotifier(debugEPGhanged, immediate_feedback=False, initial_call=False)

	def debugStorageChanged(configElement):
		udevDebugFile = "/etc/udev/udev.debug"
		if configElement.value:
			fileWriteLine(udevDebugFile, "", source=MODULE_NAME)
		elif exists(udevDebugFile):
			unlink(udevDebugFile)
		harddiskmanager.debug = configElement.value

	config.crash.debugStorage.addNotifier(debugStorageChanged)

	hddChoices = [("/etc/enigma2/", _("Internal Flash"))]
	for partition in harddiskmanager.getMountedPartitions():
		if exists(partition.mountpoint):
			path = normpath(partition.mountpoint)
			if partition.mountpoint != "/":
				hddChoices.append((partition.mountpoint, path))
	config.misc.epgcachepath = ConfigSelection(default="/etc/enigma2/", choices=hddChoices)
	config.misc.epgcachefilename = ConfigText(default="epg", fixed_size=False)
	epgCacheFilename = "%s.dat" % config.misc.epgcachefilename.value.replace(".dat", "")
	config.misc.epgcache_filename = ConfigText(default=pathjoin(config.misc.epgcachepath.value, epgCacheFilename))

	def EpgCacheChanged(configElement):
		config.misc.epgcache_filename.setValue(pathjoin(config.misc.epgcachepath.value, epgCacheFilename))
		config.misc.epgcache_filename.save()
		eEPGCache.getInstance().setCacheFile(config.misc.epgcache_filename.value)
		epgcache = eEPGCache.getInstance()
		epgcache.save()
		if not config.misc.epgcache_filename.value.startswith("/etc/enigma2/"):
			epgCachePath = pathjoin("/etc/enigma2/", epgCacheFilename)
			if exists(epgCachePath):
				remove(epgCachePath)
	config.misc.epgcachepath.addNotifier(EpgCacheChanged, immediate_feedback=False)
	config.misc.epgcachefilename.addNotifier(EpgCacheChanged, immediate_feedback=False)

	choiceList = [
		("", _("Auto Detect")),
		("ETSI", _("Generic")),
		("AUS", _("Australia"))
	]
	config.misc.epgratingcountry = ConfigSelection(default="", choices=choiceList)
	config.misc.epggenrecountry = ConfigSelection(default="", choices=choiceList)

	def setHDDStandby(configElement):
		for hdd in harddiskmanager.HDDList():
			hdd[1].setIdleTime(int(configElement.value))
	config.usage.hdd_standby.addNotifier(setHDDStandby, immediate_feedback=False)

	if BoxInfo.getItem("12V_Output"):
		def set12VOutput(configElement):
			Misc_Options.getInstance().set_12V_output(configElement.value == "on" and 1 or 0)
		config.usage.output_12V.addNotifier(set12VOutput, immediate_feedback=False)

	KM = {
		"xml": _("Default  (keymap.xml)"),
		"usr": _("User  (keymap.usr)"),
		"ntr": _("Neutrino  (keymap.ntr)"),
		"u80": _("UP80  (keymap.u80)")
	}

	keymapchoices = []
	for kmap in KM.keys():
		kmfile = eEnv.resolve("${datadir}/enigma2/keymap.%s" % kmap)
		if isfile(kmfile):
			keymapchoices.append((kmfile, KM.get(kmap)))

	if not isfile(DEFAULTKEYMAP):  # BIG PROBLEM
		keymapchoices.append((DEFAULTKEYMAP, KM.get("xml")))

	config.usage.keymap = ConfigSelection(default=DEFAULTKEYMAP, choices=keymapchoices)
	config.usage.keymap_usermod = ConfigText(default=eEnv.resolve("${datadir}/enigma2/keymap_usermod.xml"))

	config.network = ConfigSubsection()
	if BoxInfo.getItem("WakeOnLAN"):
		def wakeOnLANChanged(configElement):
			fileWriteLine(BoxInfo.getItem("WakeOnLAN"), BoxInfo.getItem("WakeOnLANType")[configElement.value], source=MODULE_NAME)

		config.network.wol = ConfigYesNo(default=False)
		config.network.wol.addNotifier(wakeOnLANChanged)
	config.network.NFS_autostart = ConfigYesNo(default=True)
	config.network.OpenVPN_autostart = ConfigYesNo(default=False)
	config.network.Samba_autostart = ConfigYesNo(default=True)
	config.network.Inadyn_autostart = ConfigYesNo(default=False)
	config.network.uShare_autostart = ConfigYesNo(default=False)

	config.samba = ConfigSubsection()
	config.samba.enableAutoShare = ConfigYesNo(default=True)
	config.samba.autoShareAccess = ConfigSelection(default=1, choices=[
		(0, _("Read Only")),
		(1, _("Read/Write"))
	])

	config.seek = ConfigSubsection()
	config.seek.baractivation = ConfigSelection(default="leftright", choices=[
		("leftright", _("Long Left/Right")),
		("ffrw", _("Long << / >>"))
	])
	config.seek.sensibilityHorizontal = ConfigSelection(default=1.0, choices=[(x, f"{x:.1f}%") for x in [0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0]])
	config.seek.sensibilityVertical = ConfigSelection(default=2.0, choices=[(x, f"{x:.1f}%") for x in [0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0]])
	config.seek.arrowSkipMode = ConfigSelection(default="t", choices=[
		("t", _("Traditional")),
		("s", _("Symmetrical skips")),
		("d", _("Defined skips"))
	])
	config.seek.numberSkipMode = ConfigSelection(default="s", choices=[
		("s", _("Symmetrical skips")),
		("d", _("Defined skips")),
		("p", _("Percentage skips"))
	])
	config.seek.defined = ConfigSubDict()
	config.seek.defined[13] = ConfigSelectionNumber(default=15, min=1, max=300, stepwidth=1, wraparound=True)
	config.seek.defined[46] = ConfigSelectionNumber(default=60, min=1, max=600, stepwidth=1, wraparound=True)
	config.seek.defined[79] = ConfigSelectionNumber(default=300, min=1, max=1200, stepwidth=1, wraparound=True)
	config.seek.defined[1] = ConfigSelectionNumber(default=-15, min=-1800, max=1800, stepwidth=1, wraparound=True)
	config.seek.defined[2] = ConfigSelectionNumber(default=10, min=-1800, max=1800, stepwidth=1, wraparound=True)
	config.seek.defined[3] = ConfigSelectionNumber(default=15, min=-1800, max=1800, stepwidth=1, wraparound=True)
	config.seek.defined[4] = ConfigSelectionNumber(default=-60, min=-1800, max=1800, stepwidth=1, wraparound=True)
	config.seek.defined[5] = ConfigSelectionNumber(default=30, min=-1800, max=1800, stepwidth=1, wraparound=True)
	config.seek.defined[6] = ConfigSelectionNumber(default=60, min=-1800, max=1800, stepwidth=1, wraparound=True)
	config.seek.defined[7] = ConfigSelectionNumber(default=-300, min=-1800, max=1800, stepwidth=1, wraparound=True)
	config.seek.defined[8] = ConfigSelectionNumber(default=180, min=-1800, max=1800, stepwidth=1, wraparound=True)
	config.seek.defined[9] = ConfigSelectionNumber(default=300, min=-1800, max=1800, stepwidth=1, wraparound=True)
	config.seek.defined[0] = ConfigSelectionNumber(default=300, min=-1800, max=1800, stepwidth=1, wraparound=True)
	config.seek.defined["UP"] = ConfigSelectionNumber(default=180, min=-1800, max=1800, stepwidth=1, wraparound=True)
	config.seek.defined["LEFT"] = ConfigSelectionNumber(default=-10, min=-1800, max=1800, stepwidth=1, wraparound=True)
	config.seek.defined["RIGHT"] = ConfigSelectionNumber(default=15, min=-1800, max=1800, stepwidth=1, wraparound=True)
	config.seek.defined["DOWN"] = ConfigSelectionNumber(default=-120, min=-1800, max=1800, stepwidth=1, wraparound=True)
	config.seek.defined["CUT_13"] = ConfigSelectionNumber(default=10, min=-1800, max=1800, stepwidth=1, wraparound=True)
	config.seek.defined["CUT_46"] = ConfigSelectionNumber(default=30, min=-1800, max=1800, stepwidth=1, wraparound=True)
	config.seek.defined["CUT_79"] = ConfigSelectionNumber(default=90, min=-1800, max=1800, stepwidth=1, wraparound=True)
	config.seek.defined["CUT_UP"] = ConfigSelectionNumber(default=300, min=-600, max=600, stepwidth=1, wraparound=True)
	config.seek.defined["CUT_LEFT"] = ConfigSelectionNumber(default=-1, min=-600, max=600, stepwidth=1, wraparound=True)
	config.seek.defined["CUT_RIGHT"] = ConfigSelectionNumber(default=1, min=-600, max=600, stepwidth=1, wraparound=True)
	config.seek.defined["CUT_DOWN"] = ConfigSelectionNumber(default=-300, min=-600, max=600, stepwidth=1, wraparound=True)
	# The following 4 items are legacy and kept for plugin compatibility.
	config.seek.sensibility = ConfigSelectionNumber(default=10, min=1, max=10, stepwidth=1, wraparound=True)
	config.seek.selfdefined_13 = ConfigSelectionNumber(default=15, min=1, max=300, stepwidth=1, wraparound=True)
	config.seek.selfdefined_46 = ConfigSelectionNumber(default=60, min=1, max=600, stepwidth=1, wraparound=True)
	config.seek.selfdefined_79 = ConfigSelectionNumber(default=300, min=1, max=1200, stepwidth=1, wraparound=True)
	config.seek.speeds_forward = ConfigSet(default=[2, 4, 8, 16, 32, 64, 128], choices=[2, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128])
	config.seek.speeds_backward = ConfigSet(default=[2, 4, 8, 16, 32, 64, 128], choices=[1, 2, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128])
	config.seek.speeds_slowmotion = ConfigSet(default=[2, 4, 8], choices=[2, 4, 6, 8, 12, 16, 25])
	config.seek.enter_forward = ConfigSelection(default="2", choices=["2", "4", "6", "8", "12", "16", "24", "32", "48", "64", "96", "128"])
	config.seek.enter_backward = ConfigSelection(default="1", choices=["1", "2", "4", "6", "8", "12", "16", "24", "32", "48", "64", "96", "128"])
	config.seek.on_pause = ConfigSelection(default="play", choices=[
		("play", _("Play")),
		("step", _("Single step (GOP)")),
		("last", _("Last speed"))
	])
	config.seek.withjumps = ConfigYesNo(default=True)
	config.seek.withjumps_after_ff_speed = ConfigSelection(default="4", choices=[
		("1", _("Never")),
		("2", _("2x")),
		("4", _("2x, 4x")),
		("6", _("2x, 4x, 6x")),
		("8", _("2x, 4x, 6x, 8x"))
	])
	choiceList = [(str(x), _("%2.1f Seconds") % (x / 1000.0)) for x in range(200, 1100, 100)] + [(str(int(x * 1000)), _("%2.1f Seconds") % x) for x in (1.2, 1.5, 1.7, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0)]
	config.seek.withjumps_forwards_ms = ConfigSelection(default="700", choices=choiceList)
	config.seek.withjumps_backwards_ms = ConfigSelection(default="700", choices=choiceList)
	config.seek.withjumps_repeat_ms = ConfigSelection(default="200", choices=choiceList[:9])
	config.seek.withjumps_avoid_zero = ConfigYesNo(default=True)

	# This is already in StartEniga.py.
	# config.crash = ConfigSubsection()

	# Handle python crashes.
	config.crash.bsodpython = ConfigYesNo(default=True)
	config.crash.bsodpython_ready = NoSave(ConfigYesNo(default=False))
	choiceList = [("0", _("Never"))] + [(str(x), str(x)) for x in range(1, 11)]
	config.crash.bsodhide = ConfigSelection(default="1", choices=choiceList)
	config.crash.bsodmax = ConfigSelection(default="3", choices=choiceList)

	config.crash.enabledebug = ConfigYesNo(default=False)
	config.crash.debugLevel = ConfigSelection(default=0, choices=[
		(0, _("Disabled")),
		(4, _("Enabled")),
		(5, _("Verbose"))
	])

	# Migrate old debug
	if config.crash.enabledebug.value:
		config.crash.debugLevel.value = 4
		config.crash.enabledebug.value = False
		config.crash.enabledebug.save()

	config.crash.debugloglimit = ConfigSelectionNumber(min=1, max=10, stepwidth=1, default=4, wraparound=True)
	config.crash.daysloglimit = ConfigSelectionNumber(min=1, max=30, stepwidth=1, default=8, wraparound=True)
	config.crash.sizeloglimit = ConfigSelectionNumber(min=1, max=250, stepwidth=1, default=10, wraparound=True)
	config.crash.lastfulljobtrashtime = ConfigInteger(default=-1)

	# The config.crash.debugTimeFormat item is used to set ENIGMA_DEBUG_TIME environmental variable on enigma2 start from enigma2.sh.
	config.crash.debugTimeFormat = ConfigSelection(default="2", choices=[
		("0", _("None")),
		("1", _("Boot time")),
		("2", _("Local time")),
		("3", _("Boot time and local time")),
		("6", _("Local date/time")),
		("7", _("Boot time and local date/time"))
	])
	config.crash.debugTimeFormat.save_forced = True

	config.crash.gstdebug = ConfigYesNo(default=False)
	config.crash.gstdebugcategory = ConfigSelection(default="*", choices=[
		("*", _("All")),
		("*audio*", _("Audio")),
		("*video*", _("Video"))
	])
	config.crash.gstdebuglevel = ConfigSelection(default="INFO", choices=[
		"none",
		"ERROR",
		"WARNING",
		"FIXME",
		"INFO",
		"DEBUG",
		"LOG",
		"TRACE",
		"MEMDUMP"
	])
	config.crash.gstdot = ConfigYesNo(default=False)

	config.crash.coredump = ConfigYesNo(default=False)

	def updateDebugPath(configElement):
		debugPath = config.crash.debug_path.value
		try:
			makedirs(debugPath, 0o755, exist_ok=True)
		except OSError as err:
			print("[UsageConfig] Error %d: Unable to create log directory '%s'!  (%s)" % (err.errno, debugPath, err.strerror))

	choiceList = [("/home/root/logs/", "/home/root/")]
	for partition in harddiskmanager.getMountedPartitions():
		if exists(partition.mountpoint) and partition.mountpoint != "/":
			choiceList.append((pathjoin(partition.mountpoint, "logs", ""), normpath(partition.mountpoint)))
	config.crash.debug_path = ConfigSelection(default="/home/root/logs/", choices=choiceList)
	config.crash.debug_path.addNotifier(updateDebugPath, immediate_feedback=False)
	config.crash.skin_error_crash = ConfigYesNo(default=True)

	def updateStackTracePrinter(configElement):
		from Components.StackTrace import StackTracePrinter
		if configElement.value:
			if (isfile("/tmp/doPythonStackTrace")):
				remove("/tmp/doPythonStackTrace")
			from threading import current_thread
			StackTracePrinter.getInstance().activate(current_thread().ident)
		else:
			StackTracePrinter.getInstance().deactivate()

	config.crash.pystackonspinner = ConfigYesNo(default=True)
	config.crash.pystackonspinner.addNotifier(updateStackTracePrinter, immediate_feedback=False, call_on_save_or_cancel=True, initial_call=True)

	config.usage.timerlist_finished_timer_position = ConfigSelection(default="end", choices=[
		("beginning", _("At beginning")),
		("end", _("At end"))
	])
	config.usage.timerlist_show_epg = ConfigYesNo(default=True)

	def updateEnterForward(configElement):
		if not configElement.value:
			configElement.value = [2]
		updateChoices(config.seek.enter_forward, configElement.value)

	config.seek.speeds_forward.addNotifier(updateEnterForward, immediate_feedback=False)

	def updateEnterBackward(configElement):
		if not configElement.value:
			configElement.value = [2]
		updateChoices(config.seek.enter_backward, configElement.value)

	config.seek.speeds_backward.addNotifier(updateEnterBackward, immediate_feedback=False)

	def updateEraseSpeed(el):
		eBackgroundFileEraser.getInstance().setEraseSpeed(int(el.value))

	def updateEraseFlags(el):
		eBackgroundFileEraser.getInstance().setEraseFlags(int(el.value))
	config.misc.erase_speed = ConfigSelection(default="20", choices=[
		("10", _("%d MB/s") % 10),
		("20", _("%d MB/s") % 20),
		("50", _("%d MB/s") % 50),
		("100", _("%d MB/s") % 100)
	])
	config.misc.erase_speed.addNotifier(updateEraseSpeed, immediate_feedback=False)
	config.misc.erase_flags = ConfigSelection(default="1", choices=[
		("0", _("Disable")),
		("1", _("Internal hdd only")),
		("3", _("Everywhere"))
	])
	config.misc.erase_flags.addNotifier(updateEraseFlags, immediate_feedback=False)

	if BoxInfo.getItem("ZapMode"):
		def setZapmode(el):
			fileWriteLine(BoxInfo.getItem("ZapMode"), el.value, source=MODULE_NAME)

		config.misc.zapmode = ConfigSelection(default="mute", choices=[
			("mute", _("Black Screen")),
			("hold", _("Hold screen")),
			("mutetilllock", _("Black screen till locked")),
			("holdtilllock", _("Hold till locked"))
		])
		config.misc.zapmode.addNotifier(setZapmode, immediate_feedback=False)

	config.usage.historymode = ConfigSelection(default="1", choices=[
		("0", _("Just zap")),
		("1", _("Show menu"))
	])

	config.usage.zapHistorySort = ConfigSelection(default=0, choices=[
		(0, _("Most recent first")),
		(1, _("Most recent last"))
	])

	config.subtitles = ConfigSubsection()

	def setTTXSubtitleColors(configElement):
		eSubtitleSettings.setTTXSubtitleColors(configElement.value)

	config.subtitles.ttx_subtitle_colors = ConfigSelection(default=1, choices=[
		(0, _("Original")),
		(1, _("White")),
		(2, _("Yellow"))
	])
	config.subtitles.ttx_subtitle_colors.addNotifier(setTTXSubtitleColors)

	def setTTXSubtitleOriginalPosition(configElement):
		eSubtitleSettings.setTTXSubtitleOriginalPosition(configElement.value)

	config.subtitles.ttx_subtitle_original_position = ConfigYesNo(default=False)
	config.subtitles.ttx_subtitle_original_position.addNotifier(setTTXSubtitleOriginalPosition)

	def setSubtitlePosition(configElement):
		eSubtitleSettings.setSubtitlePosition(configElement.value)

	config.subtitles.subtitle_position = ConfigSelection(default=50, choices=[(x, _("%d Pixels") % x) for x in list(range(0, 91, 10)) + list(range(100, 451, 50))])
	config.subtitles.subtitle_position.addNotifier(setSubtitlePosition)

	def setSubtitleAligment(configElement):
		aligments = {
			"left": 1,
			"center": 4,
			"right": 2
		}
		eSubtitleSettings.setSubtitleAligment(aligments.get(configElement.value, 4))

	config.subtitles.subtitle_alignment = ConfigSelection(default="center", choices=[
		("left", _("Left")),
		("center", _("Center")),
		("right", _("Right"))
	])
	config.subtitles.subtitle_alignment.addNotifier(setSubtitleAligment)

	def setSubtitleReWrap(configElement):
		eSubtitleSettings.setSubtitleReWrap(configElement.value)

	config.subtitles.subtitle_rewrap = ConfigYesNo(default=False)
	config.subtitles.subtitle_rewrap.addNotifier(setSubtitleReWrap)

	def setSubtitleColoriseDialogs(configElement):
		eSubtitleSettings.setSubtitleColoriseDialogs(configElement.value)

	config.subtitles.colourise_dialogs = ConfigYesNo(default=False)
	config.subtitles.colourise_dialogs.addNotifier(setSubtitleColoriseDialogs)

	def setSubtitleBorderWith(configElement):
		eSubtitleSettings.setSubtitleBorderWith(configElement.value)

	config.subtitles.subtitle_borderwidth = ConfigSelection(default=3, choices=[(x, str(x)) for x in range(1, 6)])
	config.subtitles.subtitle_borderwidth.addNotifier(setSubtitleBorderWith)

	def setSubtitleFontSize(configElement):
		eSubtitleSettings.setSubtitleFontSize(configElement.value)

	config.subtitles.subtitle_fontsize = ConfigSelection(default=40, choices=[(x, str(x)) for x in range(16, 101) if not x % 2])
	config.subtitles.subtitle_fontsize.addNotifier(setSubtitleFontSize)

	def setSubtitleBacktrans(configElement):
		eSubtitleSettings.setSubtitleBacktrans(configElement.value)

	choiceList = [
        (-1, _("Original")),
		(0, _("No transparency")),
		(12, "5%"),
		(25, "10%"),
		(38, "15%"),
		(50, "20%"),
		(75, "30%"),
		(100, "40%"),
		(125, "50%"),
		(150, "60%"),
		(175, "70%"),
		(200, "80%"),
		(225, "90%"),
		(255, _("Full transparency"))]
	config.subtitles.subtitles_backtrans = ConfigSelection(default=255, choices=choiceList)
	config.subtitles.subtitles_backtrans.addNotifier(setSubtitleBacktrans)

	def setDVBSubtitleBacktrans(configElement):
		eSubtitleSettings.setDVBSubtitleBacktrans(configElement.value)

	config.subtitles.dvb_subtitles_backtrans = ConfigSelection(default=-1, choices=choiceList)
	config.subtitles.dvb_subtitles_backtrans.addNotifier(setDVBSubtitleBacktrans)

	choiceList = []
	for x in range(-54000000, 54045000, 45000):
		if x == 0:
			choiceList.append((0, _("No delay")))
		else:
			choiceList.append((x, _("%2.1f Seconds") % (x / 90000.0)))

	def setSubtitleNoPTSDelay(configElement):
		eSubtitleSettings.setSubtitleNoPTSDelay(configElement.value)

	config.subtitles.subtitle_noPTSrecordingdelay = ConfigSelection(default=315000, choices=choiceList)
	config.subtitles.subtitle_noPTSrecordingdelay.addNotifier(setSubtitleNoPTSDelay)

	def setSubtitleBadTimingDelay(configElement):
		eSubtitleSettings.setSubtitleBadTimingDelay(configElement.value)

	config.subtitles.subtitle_bad_timing_delay = ConfigSelection(default=0, choices=choiceList)
	config.subtitles.subtitle_bad_timing_delay.addNotifier(setSubtitleBadTimingDelay)

	def setPangoSubtitleDelay(configElement):
		eSubtitleSettings.setPangoSubtitleDelay(configElement.value)

	config.subtitles.pango_subtitles_delay = ConfigSelection(default=0, choices=choiceList)
	config.subtitles.pango_subtitles_delay.addNotifier(setPangoSubtitleDelay)

	def setDVBSubtitleColor(configElement):
		eSubtitleSettings.setDVBSubtitleColor(configElement.value)

	config.subtitles.dvb_subtitles_color = ConfigSelection(default=0, choices=[(0, _("Original")), (1, _("Yellow")), (2, _("Green")), (3, _("Magenta")), (4, _("Cyan"))])
	config.subtitles.dvb_subtitles_color.addNotifier(setDVBSubtitleColor)

	def setDVBSubtitleOriginalPosition(configElement):
		eSubtitleSettings.setDVBSubtitleOriginalPosition(configElement.value)

	config.subtitles.dvb_subtitles_original_position = ConfigSelection(default=0, choices=[
		(0, _("Original")),
		(1, _("Fixed")),
		(2, _("Relative"))
	])
	config.subtitles.dvb_subtitles_original_position.addNotifier(setDVBSubtitleOriginalPosition)

	def setDVBSubtitleCentered(configElement):
		eSubtitleSettings.setDVBSubtitleCentered(configElement.value)

	config.subtitles.dvb_subtitles_centered = ConfigYesNo(default=False)
	config.subtitles.dvb_subtitles_centered.addNotifier(setDVBSubtitleCentered)

	def setPangoSubtitleColors(configElement):
		eSubtitleSettings.setPangoSubtitleColors(configElement.value)

	config.subtitles.pango_subtitle_colors = ConfigSelection(default=1, choices=[
		(0, _("Alternative")),
		(1, _("White")),
		(2, _("Yellow"))
	])
	config.subtitles.pango_subtitle_colors.addNotifier(setPangoSubtitleColors)

	def setPangoSubtitleFontWitch(configElement):
		eSubtitleSettings.setPangoSubtitleFontWitch(configElement.value)

	config.subtitles.pango_subtitle_fontswitch = ConfigYesNo(default=True)
	config.subtitles.pango_subtitle_fontswitch.addNotifier(setPangoSubtitleFontWitch)

	def setPangoSubtitleFPS(configElement):
		eSubtitleSettings.setPangoSubtitleFPS(configElement.value)

	config.subtitles.pango_subtitles_fps = ConfigSelection(default=1, choices=[
		(1, _("Original")),
		(23976, "23.976"),
		(24000, "24"),
		(25000, "25"),
		(29970, "29.97"),
		(30000, "30")
	])
	config.subtitles.pango_subtitles_fps.addNotifier(setPangoSubtitleFPS)

	def setPangoSubtitleRemovehi(configElement):
		eSubtitleSettings.setPangoSubtitleRemovehi(configElement.value)

	config.subtitles.pango_subtitle_removehi = ConfigYesNo(default=False)
	config.subtitles.pango_subtitle_removehi.addNotifier(setPangoSubtitleRemovehi)

	def setPangoSubtitleAutoRun(configElement):
		eSubtitleSettings.setPangoSubtitleAutoRun(configElement.value)

	config.subtitles.pango_autoturnon = ConfigYesNo(default=True)
	config.subtitles.pango_autoturnon.addNotifier(setPangoSubtitleAutoRun)

	# AI start
	def setAiEnabled(configElement):
		eSubtitleSettings.setAiEnabled(configElement.value)

	config.subtitles.ai_enabled = ConfigYesNo(default=False)
	config.subtitles.ai_enabled.addNotifier(setAiEnabled)

	def setAiSubscriptionCode(configElement):
		eSubtitleSettings.setAiSubscriptionCode(str(configElement.value))

	config.subtitles.ai_subscription_code = ConfigNumber(default=15)
	config.subtitles.ai_subscription_code.addNotifier(setAiSubscriptionCode)

	def setAiSubtitleColors(configElement):
		eSubtitleSettings.setAiSubtitleColors(configElement.value)

	config.subtitles.ai_subtitle_colors = ConfigSelection(default=1, choices=[
		(1, _("White")),
		(2, _("Yellow")),
		(3, _("Red")),
		(4, _("Green")),
		(5, _("Blue"))
	])
	config.subtitles.ai_subtitle_colors.addNotifier(setAiSubtitleColors)

	def setAiConnectionSpeed(configElement):
		eSubtitleSettings.setAiConnectionSpeed(configElement.value)

	config.subtitles.ai_connection_speed = ConfigSelection(default=1, choices=[
		(1, _("Up to 50 Mbps")),
		(2, _("50-200 Mbps")),
		(3, _("Above 200 Mbps"))
	])
	config.subtitles.ai_connection_speed.addNotifier(setAiConnectionSpeed)

	langsAI = ['af', 'sq', 'am', 'ar', 'hy', 'az', 'eu', 'be', 'bn', 'bs', 'bg', 'ca', 'zh', 'co', 'hr', 'cs', 'da', 'nl', 'en', 'eo', 'fr', 'fi', 'fy', 'gl', 'ka', 'de', 'el', 'ht', 'ha', 'hu', 'is', 'ig', 'ga', 'it', 'ja', 'jv', 'kn', 'kk', 'km', 'rw', 'ko', 'ku', 'ky', 'lo', 'la', 'lv', 'lt', 'lb', 'mk', 'mg', 'ms', 'mt', 'mi', 'mr', 'mn', 'no', 'ny', 'or', 'ps', 'fa', 'pl', 'pt', 'ro', 'ru', 'sm', 'gd', 'sr', 'st', 'sn', 'sk', 'sl', 'so', 'es', 'su', 'sw', 'sv', 'tl', 'tg', 'te', 'th', 'tr', 'tk', 'uk', 'ur', 'ug', 'uz', 'cy', 'xh', 'yi', 'yo', 'zu']
	langsAI = [(x, international.LANGUAGE_DATA[x][1]) for x in langsAI]
	langsAI.append(("zh-CN", _("Chinese (Simplified)")))
	langsAI.append(("ceb", _("Cebuano")))
	langsAI.append(("haw", _("Hawaiian")))
	langsAI.append(("iw", _("Hebrew")))
	langsAI.append(("hmn", _("Hmong")))
	langsAI.append(("ar_eg", _("Arabic (Egyptian)")))
	langsAI.append(("ar_ma", _("Arabic (Moroccan)")))
	langsAI.append(("ar_sy", _("Arabic (Syro-Lebanese)")))
	langsAI.append(("ar_iq", _("Arabic (Iraq)")))
	langsAI.append(("ar_tn", _("Arabic (Tunisian)")))
	langsAI.sort(key=lambda x: x[1])

	default = config.misc.locale.value
	default = default.split("_")[0] if "_" in default else default
	if default == "zh":
		default = "zh-CN"
	if default not in [x[0] for x in langsAI]:
		default = "en"

	def setAiTranslateTo(configElement):
		eSubtitleSettings.setAiTranslateTo(configElement.value)

	config.subtitles.ai_translate_to = ConfigSelection(default=default, choices=langsAI)
	config.subtitles.ai_translate_to.addNotifier(setAiTranslateTo)

	def setAiMode(configElement):
		eSubtitleSettings.setAiMode(configElement.value)

	config.subtitles.ai_mode = ConfigSelection(default=1, choices=[(x, f"{_("Mode")} {x}") for x in range(1, 4)])
	config.subtitles.ai_mode.addNotifier(setAiMode)

	# AI end

	config.autolanguage = ConfigSubsection()
	languageChoiceList = [
		("", _("None")),
		("und", _("Undetermined")),
		(originalAudioTracks, _("Original")),
		("ara", _("Arabic")),
		("eus baq", _("Basque")),
		("bul", _("Bulgarian")),
		("hrv", _("Croatian")),
		("chn sgp", _("Simplified Chinese")),
		("twn hkn", _("Traditional Chinese")),
		("ces cze", _("Czech")),
		("dan", _("Danish")),
		("dut ndl nld Dutch", _("Dutch")),
		("eng Englisch", _("English")),
		("est", _("Estonian")),
		("fin", _("Finnish")),
		("fra fre", _("French")),
		("deu ger", _("German")),
		("ell gre grc", _("Greek")),
		("heb", _("Hebrew")),
		("hun", _("Hungarian")),
		("ind", _("Indonesian")),
		("ita", _("Italian")),
		("lav", _("Latvian")),
		("lit", _("Lithuanian")),
		("ltz", _("Luxembourgish")),
		("nor", _("Norwegian")),
		("pol", _("Polish")),
		("por dub Dub DUB ud1 LEG", _("Portuguese")),
		("fas per fa pes", _("Persian")),
		("ron rum", _("Romanian")),
		("rus", _("Russian")),
		("srp scc", _("Serbian")),
		("slk slo", _("Slovak")),
		("slv", _("Slovenian")),
		("spa", _("Spanish")),
		("swe", _("Swedish")),
		("tha", _("Thai")),
		("tur Audio_TUR", _("Turkish")),
		("ukr Ukr", _("Ukrainian")),
		(visuallyImpairedCommentary, _("Visual impaired commentary"))
	]
	epgChoiceList = languageChoiceList[:1] + languageChoiceList[2:]
	subtitleChoiceList = languageChoiceList[:1] + languageChoiceList[2:]

	def setEpgLanguage(configElement):
		eServiceEvent.setEPGLanguage(configElement.value)

	def setEpgLanguageAlternative(configElement):
		eServiceEvent.setEPGLanguageAlternative(configElement.value)

	def epglanguage(configElement):
		config.autolanguage.audio_epglanguage.setChoices([x for x in epgChoiceList if x[0] and x[0] != config.autolanguage.audio_epglanguage_alternative.value or not x[0] and not config.autolanguage.audio_epglanguage_alternative.value])
		config.autolanguage.audio_epglanguage_alternative.setChoices([x for x in epgChoiceList if x[0] and x[0] != config.autolanguage.audio_epglanguage.value or not x[0]])
	config.autolanguage.audio_epglanguage = ConfigSelection(default="", choices=epgChoiceList)
	config.autolanguage.audio_epglanguage_alternative = ConfigSelection(default="", choices=epgChoiceList)
	config.autolanguage.audio_epglanguage.addNotifier(setEpgLanguage)
	config.autolanguage.audio_epglanguage.addNotifier(epglanguage, initial_call=False)
	config.autolanguage.audio_epglanguage_alternative.addNotifier(setEpgLanguageAlternative)
	config.autolanguage.audio_epglanguage_alternative.addNotifier(epglanguage)

	def getselectedlanguages(range):
		return [eval("config.autolanguage.audio_autoselect%x.value" % x) for x in range]

	def autolanguage(configElement):
		config.autolanguage.audio_autoselect1.setChoices([x for x in languageChoiceList if x[0] and x[0] not in getselectedlanguages((2, 3, 4)) or not x[0] and not config.autolanguage.audio_autoselect2.value])
		config.autolanguage.audio_autoselect2.setChoices([x for x in languageChoiceList if x[0] and x[0] not in getselectedlanguages((1, 3, 4)) or not x[0] and not config.autolanguage.audio_autoselect3.value])
		config.autolanguage.audio_autoselect3.setChoices([x for x in languageChoiceList if x[0] and x[0] not in getselectedlanguages((1, 2, 4)) or not x[0] and not config.autolanguage.audio_autoselect4.value])
		config.autolanguage.audio_autoselect4.setChoices([x for x in languageChoiceList if x[0] and x[0] not in getselectedlanguages((1, 2, 3)) or not x[0]])
		eSettings.setAudioLanguages(config.autolanguage.audio_autoselect1.value, config.autolanguage.audio_autoselect2.value, config.autolanguage.audio_autoselect3.value, config.autolanguage.audio_autoselect4.value)

	config.autolanguage.audio_autoselect1 = ConfigSelection(default="", choices=languageChoiceList)
	config.autolanguage.audio_autoselect2 = ConfigSelection(default="", choices=languageChoiceList)
	config.autolanguage.audio_autoselect3 = ConfigSelection(default="", choices=languageChoiceList)
	config.autolanguage.audio_autoselect4 = ConfigSelection(default="", choices=languageChoiceList)
	config.autolanguage.audio_autoselect1.addNotifier(autolanguage, initial_call=False)
	config.autolanguage.audio_autoselect2.addNotifier(autolanguage, initial_call=False)
	config.autolanguage.audio_autoselect3.addNotifier(autolanguage, initial_call=False)
	config.autolanguage.audio_autoselect4.addNotifier(autolanguage)

	def setAudioDefaultAC3(configElement):
		eSettings.setAudioDefaultAC3(configElement.value)

	config.autolanguage.audio_defaultac3 = ConfigYesNo(default=False)
	config.autolanguage.audio_defaultac3.addNotifier(setAudioDefaultAC3)

	def setAudioDefaultDDP(configElement):
		eSettings.setAudioDefaultDDP(configElement.value)

	config.autolanguage.audio_defaultddp = ConfigYesNo(default=False)
	config.autolanguage.audio_defaultddp.addNotifier(setAudioDefaultDDP)

	def setAudioUseCache(configElement):
		eSettings.setAudioUseCache(configElement.value)

	config.autolanguage.audio_usecache = ConfigYesNo(default=True)
	config.autolanguage.audio_usecache.addNotifier(setAudioUseCache)

	def getselectedsublanguages(range):
		return [eval("config.autolanguage.subtitle_autoselect%x.value" % x) for x in range]

	def autolanguagesub(configElement):
		config.autolanguage.subtitle_autoselect1.setChoices([x for x in subtitleChoiceList if x[0] and x[0] not in getselectedsublanguages((2, 3, 4)) or not x[0] and not config.autolanguage.subtitle_autoselect2.value])
		config.autolanguage.subtitle_autoselect2.setChoices([x for x in subtitleChoiceList if x[0] and x[0] not in getselectedsublanguages((1, 3, 4)) or not x[0] and not config.autolanguage.subtitle_autoselect3.value])
		config.autolanguage.subtitle_autoselect3.setChoices([x for x in subtitleChoiceList if x[0] and x[0] not in getselectedsublanguages((1, 2, 4)) or not x[0] and not config.autolanguage.subtitle_autoselect4.value])
		config.autolanguage.subtitle_autoselect4.setChoices([x for x in subtitleChoiceList if x[0] and x[0] not in getselectedsublanguages((1, 2, 3)) or not x[0]])
		choiceList = [(0, _("None"))]
		for y in list(range(1, 15 if config.autolanguage.subtitle_autoselect4.value else (7 if config.autolanguage.subtitle_autoselect3.value else (4 if config.autolanguage.subtitle_autoselect2.value else (2 if config.autolanguage.subtitle_autoselect1.value else 0))))):
			choiceList.append((y, ", ".join([eval("config.autolanguage.subtitle_autoselect%x.getText()" % x) for x in (y & 1, y & 2, y & 4 and 3, y & 8 and 4) if x])))
		if config.autolanguage.subtitle_autoselect3.value:
			choiceList.append((y + 1, _("All")))
		config.autolanguage.equal_languages.setChoices(default=0, choices=choiceList)
		eSubtitleSettings.setSubtitleLanguages(config.autolanguage.subtitle_autoselect1.value, config.autolanguage.subtitle_autoselect2.value, config.autolanguage.subtitle_autoselect3.value, config.autolanguage.subtitle_autoselect4.value)

	def setSubtitleEqualLanguages(configElement):
		eSubtitleSettings.setSubtitleEqualLanguages(configElement.value)

	config.autolanguage.equal_languages = ConfigSelection(default=0, choices=[x for x in range(0, 16)])
	config.autolanguage.equal_languages.addNotifier(setSubtitleEqualLanguages)
	config.autolanguage.subtitle_autoselect1 = ConfigSelection(default="", choices=subtitleChoiceList)
	config.autolanguage.subtitle_autoselect2 = ConfigSelection(default="", choices=subtitleChoiceList)
	config.autolanguage.subtitle_autoselect3 = ConfigSelection(default="", choices=subtitleChoiceList)
	config.autolanguage.subtitle_autoselect4 = ConfigSelection(default="", choices=subtitleChoiceList)
	config.autolanguage.subtitle_autoselect1.addNotifier(autolanguagesub, initial_call=False)
	config.autolanguage.subtitle_autoselect2.addNotifier(autolanguagesub, initial_call=False)
	config.autolanguage.subtitle_autoselect3.addNotifier(autolanguagesub, initial_call=False)
	config.autolanguage.subtitle_autoselect4.addNotifier(autolanguagesub)

	def setSubtitleHearingImpaired(configElement):
		eSubtitleSettings.setSubtitleHearingImpaired(configElement.value)
	config.autolanguage.subtitle_hearingimpaired = ConfigYesNo(default=False)
	config.autolanguage.subtitle_hearingimpaired.addNotifier(setSubtitleHearingImpaired)

	def setSubtitleDefaultImpaired(configElement):
		eSubtitleSettings.setSubtitleDefaultImpaired(configElement.value)
	config.autolanguage.subtitle_defaultimpaired = ConfigYesNo(default=False)
	config.autolanguage.subtitle_defaultimpaired.addNotifier(setSubtitleDefaultImpaired)

	def setSubtitleDefaultDVB(configElement):
		eSubtitleSettings.setSubtitleDefaultDVB(configElement.value)
	config.autolanguage.subtitle_defaultdvb = ConfigYesNo(default=False)
	config.autolanguage.subtitle_defaultdvb.addNotifier(setSubtitleDefaultDVB)

	def setSubtitleUseCache(configElement):
		eSubtitleSettings.setSubtitleUseCache(configElement.value)
	config.autolanguage.subtitle_usecache = ConfigYesNo(default=True)
	config.autolanguage.subtitle_usecache.addNotifier(setSubtitleUseCache)

	config.logmanager = ConfigSubsection()
	config.logmanager.showinextensions = ConfigYesNo(default=False)
	config.logmanager.path = ConfigText(default="/")
	config.logmanager.sentfiles = ConfigLocations(default=[])

	config.plisettings = ConfigSubsection()
	config.plisettings.InfoBarEpg_mode = ConfigSelection(default="0", choices=[
		("0", _("As plugin in extended bar")),
		("1", _("With long OK press")),
		("2", _("With EXIT button")),
		("3", _("With LEFT/RIGHT buttons"))
	])
	config.plisettings.PLIEPG_mode = ConfigSelection(default="pliepg", choices=[
		("pliepg", _("Show Graphical EPG")),
		("single", _("Show Single EPG")),
		("multi", _("Show Multi EPG")),
		("vertical", _("Show Vertical EPG")),
		("eventview", _("Show EventView")),
		("merlinepgcenter", _("Show Merlin EPG Center"))
	])
	config.plisettings.PLIINFO_mode = ConfigSelection(default="eventview", choices=[
		("eventview", _("Show EventView")),
		("epgpress", _("Show EPG")),
		("single", _("Show Single EPG"))
	])

	config.epgselection = ConfigSubsection()
	config.epgselection.sort = ConfigSelection(default="0", choices=[
		("0", _("Time")),
		("1", _("Alphanumeric"))
	])
	config.epgselection.overjump = ConfigYesNo(default=False)
	config.epgselection.infobar_type_mode = ConfigSelection(default="text", choices=[
		("text", _("Text")),
		("graphics", _("Multi EPG")),
		("single", _("Single EPG"))
	])
	if BoxInfo.getItem("NumVideoDecoders", 1) > 1:
		config.epgselection.infobar_preview_mode = ConfigSelection(default="1", choices=[
			("0", _("Disabled")),
			("1", _("Full screen")),
			("2", _("PiP"))
		])
	else:
		config.epgselection.infobar_preview_mode = ConfigSelection(default="1", choices=[
			("0", _("Disabled")),
			("1", _("Full screen"))
		])

	choiceList = [
		("Zap", _("Zap")),
		("Zap + Exit", _("Zap + Exit"))
	]

	config.epgselection.infobar_ok = ConfigSelection(default="Zap", choices=choiceList)
	config.epgselection.infobar_oklong = ConfigSelection(default="Zap + Exit", choices=choiceList)
	config.epgselection.infobar_itemsperpage = ConfigSelectionNumber(default=2, stepwidth=1, min=1, max=4, wraparound=True)
	config.epgselection.infobar_roundto = ConfigSelection(default="15", choices=[(str(x), _("%d Minutes") % x) for x in (15, 30, 60)])
	config.epgselection.infobar_histminutes = ConfigSelection(default="0", choices=[(str(x), _("%d Minutes") % x) for x in range(0, 121, 15)])
	config.epgselection.infobar_prevtime = ConfigClock(default=time())
	config.epgselection.infobar_prevtimeperiod = ConfigSelection(default="180", choices=[(str(x), _("%d Minutes") % x) for x in (60, 90, 120, 150, 180, 210, 240, 270, 300)])
	config.epgselection.infobar_primetimehour = ConfigSelectionNumber(default=20, stepwidth=1, min=00, max=23, wraparound=True)
	config.epgselection.infobar_primetimemins = ConfigSelectionNumber(default=15, stepwidth=1, min=00, max=59, wraparound=True)
	# config.epgselection.infobar_servicetitle_mode = ConfigSelection(default="servicename", choices=[
	# 	("servicename", _("Service Name")),
	# 	("picon", _("Picon")),
	# 	("picon+servicename", _("Picon and Service Name"))
	# ])
	titleChoiceList = [
		("servicename", _("Service Name")),
		("picon", _("Picon")),
		("servicenumber+picon+servicename", _("Service Number, Picon and Service Name")),
		("servicenumber+servicename", _("Service Number and Service Name")),
		("picon+servicename", _("Picon and Service Name"))
	]
	config.epgselection.infobar_servicetitle_mode = ConfigSelection(default="picon+servicename", choices=titleChoiceList)
	config.epgselection.infobar_servfs = ConfigSelectionNumber(default=0, stepwidth=1, min=-8, max=10, wraparound=True)
	config.epgselection.infobar_eventfs = ConfigSelectionNumber(default=0, stepwidth=1, min=-8, max=10, wraparound=True)
	config.epgselection.infobar_timelinefs = ConfigSelectionNumber(default=0, stepwidth=1, min=-8, max=10, wraparound=True)
	config.epgselection.infobar_timeline24h = ConfigYesNo(default=True)
	config.epgselection.infobar_servicewidth = ConfigSelectionNumber(default=250, stepwidth=1, min=70, max=500, wraparound=True)
	config.epgselection.infobar_piconwidth = ConfigSelectionNumber(default=100, stepwidth=1, min=50, max=500, wraparound=True)
	config.epgselection.infobar_infowidth = ConfigSelectionNumber(default=25, stepwidth=25, min=0, max=150, wraparound=True)
	config.epgselection.enhanced_preview_mode = ConfigYesNo(default=True)
	config.epgselection.enhanced_ok = ConfigSelection(default="Zap", choices=choiceList)
	config.epgselection.enhanced_oklong = ConfigSelection(default="Zap + Exit", choices=choiceList)
	config.epgselection.enhanced_eventfs = ConfigSelectionNumber(default=0, stepwidth=1, min=-8, max=10, wraparound=True)
	config.epgselection.enhanced_itemsperpage = ConfigSelectionNumber(default=16, stepwidth=1, min=8, max=40, wraparound=True)
	config.epgselection.multi_showbouquet = ConfigYesNo(default=False)
	config.epgselection.multi_preview_mode = ConfigYesNo(default=True)
	config.epgselection.multi_ok = ConfigSelection(default="Zap", choices=choiceList)
	config.epgselection.multi_oklong = ConfigSelection(default="Zap + Exit", choices=choiceList)
	config.epgselection.multi_eventfs = ConfigSelectionNumber(default=0, stepwidth=1, min=-8, max=10, wraparound=True)
	config.epgselection.multi_itemsperpage = ConfigSelectionNumber(default=16, stepwidth=1, min=8, max=40, wraparound=True)
	config.epgselection.graph_showbouquet = ConfigYesNo(default=False)
	config.epgselection.graph_preview_mode = ConfigYesNo(default=True)
	config.epgselection.graph_type_mode = ConfigSelection(default="text", choices=[
		("graphics", _("Graphics")),
		("text", _("Text"))
	])
	config.epgselection.graph_ok = ConfigSelection(default="Zap", choices=choiceList)
	config.epgselection.graph_oklong = ConfigSelection(default="Zap + Exit", choices=choiceList)
	config.epgselection.graph_info = ConfigSelection(default="Channel Info", choices=[
		("Channel Info", _("Channel Info")),
		("Single EPG", _("Single EPG"))
	])
	config.epgselection.graph_infolong = ConfigSelection(default="Single EPG", choices=[
		("Channel Info", _("Channel Info")),
		("Single EPG", _("Single EPG"))
	])
	config.epgselection.graph_roundto = ConfigSelection(default="15", choices=[(str(x), _("%d Minutes") % x) for x in (15, 30, 60)])
	config.epgselection.graph_histminutes = ConfigSelection(default="0", choices=[(str(x), _("%d Minutes") % x) for x in range(0, 121, 15)])
	config.epgselection.graph_prevtime = ConfigClock(default=time())
	config.epgselection.graph_prevtimeperiod = ConfigSelection(default="180", choices=[(str(x), _("%d Minutes") % x) for x in (60, 90, 120, 150, 180, 210, 240, 270, 300)])
	config.epgselection.graph_primetimehour = ConfigSelectionNumber(default=20, stepwidth=1, min=00, max=23, wraparound=True)
	config.epgselection.graph_primetimemins = ConfigSelectionNumber(default=15, stepwidth=1, min=00, max=59, wraparound=True)
	config.epgselection.graph_servicetitle_mode = ConfigSelection(default="picon+servicename", choices=titleChoiceList)
	config.epgselection.graph_startmode = ConfigSelection(default="standard", choices=[
		("standard", _("Standard")),
		("primetime", _("Prime time")),
		("channel1", _("Channel 1")),
		("channel1+primetime", _("Channel 1 with Prime time"))
	])
	config.epgselection.graph_servfs = ConfigSelectionNumber(default=0, stepwidth=1, min=-8, max=10, wraparound=True)
	config.epgselection.graph_eventfs = ConfigSelectionNumber(default=0, stepwidth=1, min=-8, max=10, wraparound=True)
	alignmentChoiceList = [
		(str(RT_HALIGN_LEFT | RT_VALIGN_CENTER), _("Left")),
		(str(RT_HALIGN_CENTER | RT_VALIGN_CENTER), _("Centered")),
		(str(RT_HALIGN_RIGHT | RT_VALIGN_CENTER), _("Right")),
		(str(RT_HALIGN_LEFT | RT_VALIGN_CENTER | RT_WRAP), _("Left, wrapped")),
		(str(RT_HALIGN_CENTER | RT_VALIGN_CENTER | RT_WRAP), _("Centered, wrapped")),
		(str(RT_HALIGN_RIGHT | RT_VALIGN_CENTER | RT_WRAP), _("Right, wrapped"))
	]
	config.epgselection.graph_event_alignment = ConfigSelection(default=alignmentChoiceList[0][0], choices=alignmentChoiceList)
	config.epgselection.graph_servicename_alignment = ConfigSelection(default=alignmentChoiceList[0][0], choices=alignmentChoiceList)
	config.epgselection.graph_timelinefs = ConfigSelectionNumber(default=0, stepwidth=1, min=-8, max=10, wraparound=True)
	config.epgselection.graph_timeline24h = ConfigYesNo(default=True)
	config.epgselection.graph_itemsperpage = ConfigSelectionNumber(default=8, stepwidth=1, min=3, max=20, wraparound=True)
	config.epgselection.graph_pig = ConfigYesNo(default=False)
	config.epgselection.graph_heightswitch = NoSave(ConfigYesNo(default=False))
	config.epgselection.graph_servicewidth = ConfigSelectionNumber(default=250, stepwidth=1, min=70, max=500, wraparound=True)
	config.epgselection.graph_piconwidth = ConfigSelectionNumber(default=100, stepwidth=1, min=50, max=500, wraparound=True)
	config.epgselection.graph_infowidth = ConfigSelectionNumber(default=25, stepwidth=25, min=0, max=150, wraparound=True)
	config.epgselection.graph_rec_icon_height = ConfigSelection(default="bottom", choices=[
		("bottom", _("Bottom")),
		("top", _("Top")),
		("middle", _("Middle")),
		("hide", _("Hide"))
	])

	choiceList = [
		("24minus", _("-24 Hours")),
		("prevpage", _("Previous Page")),
		("prevbouquet", _("Previous Bouquet")),
		("24plus", _("+24 Hours")),
		("nextpage", _("Next Page")),
		("nextbouquet", _("Next Bouquet")),
		("autotimer", _("AutoTimer")),
		("timer", _("Add/Remove Timer")),
		("imdb", _("IMDb Search")),
		("tmdb", _("TMDB Search")),
		("bouquetlist", _("Bouquet List")),
		("showmovies", _("Show Movies List")),
		("record", _("Record - same as record button")),
		("gotodatetime", _("Goto Date/Time")),
		("epgsearch", _("EPG Search"))
	]
	config.epgselection.graph_red = ConfigSelection(default="imdb", choices=choiceList)
	config.epgselection.graph_green = ConfigSelection(default="timer", choices=choiceList)
	config.epgselection.graph_yellow = ConfigSelection(default="epgsearch", choices=choiceList)
	config.epgselection.graph_blue = ConfigSelection(default="autotimer", choices=choiceList)

	config.epgselection.graph_channelbtn = ConfigSelection(default="24", choices=[
		("24", _("-24h/+24 Hours")),
		("page", _("Previous/Next page")),
		("bouquet", _("Previous/Next bouquet"))
	])

	config.epgselection.vertical_itemsperpage = ConfigSelectionNumber(default=6, stepwidth=1, min=3, max=12, wraparound=True)
	config.epgselection.vertical_eventfs = ConfigSelectionNumber(default=0, stepwidth=1, min=-10, max=10, wraparound=True)
	config.epgselection.vertical_ok = ConfigSelection(choices=[("Channel Info", _("Channel Info")), ("Zap", _("Zap")), ("Zap + Exit", _("Zap + Exit"))], default="Channel Info")
	config.epgselection.vertical_oklong = ConfigSelection(choices=[("Channel Info", _("Channel Info")), ("Zap", _("Zap")), ("Zap + Exit", _("Zap + Exit"))], default="Zap + Exit")
	config.epgselection.vertical_info = ConfigSelection(choices=[("Channel Info", _("Channel Info")), ("Single EPG", _("Single EPG"))], default="Channel Info")
	config.epgselection.vertical_infolong = ConfigSelection(choices=[("Channel Info", _("Channel Info")), ("Single EPG", _("Single EPG"))], default="Single EPG")
	config.epgselection.vertical_channelbtn = ConfigSelection(choices=[("page", _("Previous/Next page")), ("scroll", _("all up/down")), ("24", _("-24h/+24 Hours"))], default="page")
	config.epgselection.vertical_channelbtn_invert = ConfigYesNo(default=False)
	config.epgselection.vertical_updownbtn = ConfigYesNo(default=True)
	config.epgselection.vertical_primetimehour = ConfigSelectionNumber(default=20, stepwidth=1, min=00, max=23, wraparound=True)
	config.epgselection.vertical_primetimemins = ConfigSelectionNumber(default=15, stepwidth=1, min=00, max=59, wraparound=True)
	config.epgselection.vertical_preview_mode = ConfigYesNo(default=True)
	config.epgselection.vertical_pig = ConfigYesNo(default=False)
	config.epgselection.vertical_eventmarker = ConfigYesNo(default=False)
	config.epgselection.vertical_showlines = ConfigYesNo(default=True)
	config.epgselection.vertical_startmode = ConfigSelection(default="standard", choices=[("standard", _("Standard")), ("primetime", _("Prime time")), ("channel1", _("Channel 1")), ("channel1+primetime", _("Channel 1 with Prime time"))])
	config.epgselection.vertical_prevtime = ConfigClock(default=time())
	choiceList = [
		("autotimer", _("AutoTimer")),
		("timer", _("Add/Remove Timer")),
		("24plus", _("+24 Hours")),
		("24minus", _("-24 Hours")),
		("imdb", _("IMDb Search")),
		("tmdb", _("TMDB Search")),
		("bouquetlist", _("Bouquet List")),
		("showmovies", _("Show Movies List")),
		("record", _("Record - same as record button")),
		("gotodatetime", _("Goto Date/Time")),
		("gotoprimetime", _("Goto Prime Time")),
		("setbasetime", _("Set Base Time")),
		("epgsearch", _("EPG Search"))
	]
	config.epgselection.vertical_red = ConfigSelection(default="imdb", choices=choiceList)
	config.epgselection.vertical_green = ConfigSelection(default="timer", choices=choiceList)
	config.epgselection.vertical_yellow = ConfigSelection(default="epgsearch", choices=choiceList)
	config.epgselection.vertical_blue = ConfigSelection(default="autotimer", choices=choiceList)

	config.softcam = ConfigSubsection()
	config.softcam.showInExtensions = ConfigYesNo(default=False)
	config.softcam.hideServerName = ConfigYesNo(default=False)

	config.oscaminfo = ConfigSubsection()
	config.oscaminfo.userDataFromConf = ConfigYesNo(default=True)
	config.oscaminfo.username = ConfigText(default="username", fixed_size=False, visible_width=12)
	config.oscaminfo.password = ConfigPassword(default="password", fixed_size=False)
	config.oscaminfo.ip = ConfigText(default="127.0.0.1", fixed_size=False)
	config.oscaminfo.port = ConfigInteger(default=83, limits=(0, 65536))
	config.oscaminfo.usessl = ConfigYesNo(default=False)
	config.oscaminfo.verifycert = ConfigYesNo(default=False)
	choiceList = [
		(0, _("Disabled"))
	] + [(x, ngettext("%d Second", "%d Seconds", x) % x) for x in (2, 5, 10, 20, 30)] + [(x * 60, ngettext("%d Minute", "%d Minutes", x) % x) for x in (1, 2, 3)]
	config.oscaminfo.autoUpdate = ConfigSelection(default=10, choices=choiceList)
	choiceList = [
		(0, _("Disabled"))
	] + [(x, ngettext("%d Second", "%d Seconds", x) % x) for x in (2, 5, 10, 20, 30)] + [(x * 60, ngettext("%d Minute", "%d Minutes", x) % x) for x in (1, 2, 3)]
	config.oscaminfo.autoUpdateLog = ConfigSelection(default=0, choices=choiceList)
	BoxInfo.setItem("OScamInstalled", False)

	config.misc.softcam_streamrelay_url = ConfigIP(default=[127, 0, 0, 1], auto_jump=True)
	config.misc.softcam_streamrelay_port = ConfigInteger(default=17999, limits=(0, 65535))
	config.misc.softcam_streamrelay_delay = ConfigSelectionNumber(min=0, max=2000, stepwidth=50, default=0, wraparound=True)

	config.cccaminfo = ConfigSubsection()
	config.cccaminfo.serverNameLength = ConfigSelectionNumber(min=10, max=100, stepwidth=1, default=22, wraparound=True)
	config.cccaminfo.name = ConfigText(default="Profile", fixed_size=False)
	config.cccaminfo.ip = ConfigText(default="192.168.2.12", fixed_size=False)
	config.cccaminfo.username = ConfigText(default="", fixed_size=False)
	config.cccaminfo.password = ConfigText(default="", fixed_size=False)
	config.cccaminfo.port = ConfigInteger(default=16001, limits=(1, 65535))
	config.cccaminfo.profile = ConfigText(default="", fixed_size=False)
	config.cccaminfo.ecmInfoEnabled = ConfigYesNo(default=True)
	config.cccaminfo.ecmInfoTime = ConfigSelectionNumber(min=1, max=10, stepwidth=1, default=5, wraparound=True)
	config.cccaminfo.ecmInfoForceHide = ConfigYesNo(default=True)
	config.cccaminfo.ecmInfoPositionX = ConfigInteger(default=50)
	config.cccaminfo.ecmInfoPositionY = ConfigInteger(default=50)
	config.cccaminfo.blacklist = ConfigText(default="/media/cf/CCcamInfo.blacklisted", fixed_size=False)
	config.cccaminfo.profiles = ConfigText(default="/media/cf/CCcamInfo.profiles", fixed_size=False)

	config.streaming = ConfigSubsection()
	config.streaming.stream_ecm = ConfigYesNo(default=False)
	config.streaming.descramble = ConfigYesNo(default=True)
	config.streaming.descramble_client = ConfigYesNo(default=False)
	config.streaming.stream_eit = ConfigYesNo(default=True)
	config.streaming.stream_ait = ConfigYesNo(default=True)
	config.streaming.stream_sdtbat = ConfigYesNo(default=False)
	config.streaming.authentication = ConfigYesNo(default=False)

	config.pluginbrowser = ConfigSubsection()
	config.pluginbrowser.po = ConfigYesNo(default=False)
	config.pluginbrowser.src = ConfigYesNo(default=False)

	def setForceLNBPowerChanged(configElement):
		fileWriteLine("/proc/stb/frontend/fbc/force_lnbon", "on" if configElement.value else "off", source=MODULE_NAME)

	def setForceToneBurstChanged(configElement):
		fileWriteLine("/proc/stb/frontend/fbc/force_toneburst", "enable" if configElement.value else "disable", source=MODULE_NAME)

	config.tunermisc = ConfigSubsection()
	if BoxInfo.getItem("ForceLNBPowerChanged"):
		config.tunermisc.forceLnbPower = ConfigYesNo(default=False)
		config.tunermisc.forceLnbPower.addNotifier(setForceLNBPowerChanged)

	if BoxInfo.getItem("ForceToneBurstChanged"):
		config.tunermisc.forceToneBurst = ConfigYesNo(default=False)
		config.tunermisc.forceToneBurst.addNotifier(setForceToneBurstChanged)

	# Software Manager.
	config.plugins.softwaremanager = ConfigSubsection()
	config.plugins.softwaremanager.overwriteSettingsFiles = ConfigYesNo(default=False)
	config.plugins.softwaremanager.overwriteDriversFiles = ConfigYesNo(default=True)
	config.plugins.softwaremanager.overwriteEmusFiles = ConfigYesNo(default=True)
	config.plugins.softwaremanager.overwritePiconsFiles = ConfigYesNo(default=True)
	config.plugins.softwaremanager.overwriteBootlogoFiles = ConfigYesNo(default=True)
	config.plugins.softwaremanager.overwriteSpinnerFiles = ConfigYesNo(default=True)

	config.plugins.softwaremanager.overwriteConfigFiles = ConfigSelection(default="Y", choices=[
		("Y", _("Yes, always")),
		("N", _("No, never")),
		("ask", _("Always ask"))
	])

	config.plugins.softwaremanager.updatetype = ConfigSelection(default="hot", choices=[
		("hot", _("Upgrade with GUI")),
		("cold", _("Unattended upgrade without GUI"))
	])
	config.plugins.softwaremanager.restoremode = ConfigSelection(default="turbo", choices=[
		("turbo", _("turbo")),
		("fast", _("fast")),
		("slow", _("slow"))
	])
	config.plugins.softwaremanager.epgcache = ConfigYesNo(default=False)

	hddChoices = [("", _("Ask user"))]
	for partition in harddiskmanager.getMountedPartitions():
		if exists(partition.mountpoint):
			path = normpath(partition.mountpoint)
			if partition.mountpoint != "/":
				hddChoices.append((partition.mountpoint, path))

	config.plugins.softwaremanager.backuptarget = ConfigSelection(default="", choices=hddChoices)

	def partitionListChanged(action, device):
		hddchoises = []
		for partition in harddiskmanager.getMountedPartitions():
			if exists(partition.mountpoint):
				path = normpath(partition.mountpoint)
				if partition.mountpoint != "/":
					hddchoises.append((partition.mountpoint, path))
		config.misc.epgcachepath.setChoices([("/etc/enigma2/", _("Internal Flash"))] + hddchoises)
		if config.misc.epgcachepath.saved_value and config.misc.epgcachepath.saved_value != config.misc.epgcachepath.value and config.misc.epgcachepath.saved_value in [x[0] for x in hddchoises]:
			print(f"[UsageConfig] epgcachepath changed from '{config.misc.epgcachepath.value}' to '{config.misc.epgcachepath.saved_value}'")
			eEPGCache.getInstance().setCacheFile("")
			config.misc.epgcachepath.value = config.misc.epgcachepath.saved_value

		config.plugins.softwaremanager.backuptarget.setChoices([("", _("Ask user"))] + hddchoises)

	harddiskmanager.on_partition_list_change.append(partitionListChanged)

	#
	# Time shift settings.
	#
	config.timeshift = ConfigSubsection()
	config.timeshift.autorecord = ConfigYesNo(default=False)
	config.timeshift.check = ConfigYesNo(default=True)
	config.timeshift.checkEvents = ConfigSelection(default=0, choices=[(0, _("Disabled"))] + [(x, ngettext("%d Minute", "%d Minutes", x) % x) for x in (15, 30, 60, 120, 240, 480)])
	config.timeshift.checkFreeSpace = ConfigSelection(default=0, choices=[(0, _("No"))] + [(x * 1024, _("%d GB") % x) for x in (1, 2, 4, 8)])
	config.timeshift.deleteAfterZap = ConfigYesNo(default=True)
	config.timeshift.favoriteSaveAction = ConfigSelection(default="askuser", choices=[
		("askuser", _("Ask user")),
		("savetimeshift", _("Save and stop")),
		("savetimeshiftandrecord", _("Save and record")),
		("noSave", _("Don't save"))
	])
	config.timeshift.fileSplitting = ConfigYesNo(default=True)
	config.timeshift.isRecording = NoSave(ConfigYesNo(default=False))
	config.timeshift.maxEvents = ConfigSelection(default=12, choices=[(x, ngettext("%d Event", "%d Events", x) % x) for x in range(1, 999)])
	config.timeshift.maxHours = ConfigSelection(default=12, choices=[(x, ngettext("%d Hour", "%d Hours", x) % x) for x in range(1, 999)])
	config.timeshift.skipReturnToLive = ConfigYesNo(default=False)
	config.timeshift.showInfoBar = ConfigYesNo(default=True)
	config.timeshift.showLiveTVMsg = ConfigYesNo(default=True)
	choiceList = [
		(0, _("Disabled"))
	] + [(x, ngettext("%d Second", "%d Seconds", x) % x) for x in (2, 3, 4, 5, 10, 20, 30)] + [(x * 60, ngettext("%d Minute", "%d Minutes", x) % x) for x in (1, 2, 5)]
	config.timeshift.startDelay = ConfigSelection(default=0, choices=choiceList)
	config.timeshift.stopWhileRecording = ConfigYesNo(default=False)

	defaultPath = resolveFilename(SCOPE_TIMESHIFT)
	config.timeshift.allowedPaths = ConfigLocations(default=[defaultPath])
	config.usage.timeshift_path = ConfigText(default="")
	if config.usage.timeshift_path.value:
		defaultPath = config.usage.timeshift_path.value
		config.usage.timeshift_path.value = config.usage.timeshift_path.default
		config.usage.timeshift_path.save()
		configfile.save()  # This needs to be done once here to reset the legacy value.
	config.timeshift.path = ConfigSelection(default=defaultPath, choices=[(defaultPath, defaultPath)])
	config.timeshift.path.load()
	savedPath = config.timeshift.path.saved_value
	if savedPath:
		savedPath = pathjoin(savedPath, "")
		if savedPath and savedPath != defaultPath:
			config.timeshift.path.setChoices(default=defaultPath, choices=[(defaultPath, defaultPath), (savedPath, savedPath)])
			config.timeshift.path.value = savedPath
	config.timeshift.path.save()
	currentPath = config.timeshift.path.value
	print("[UsageConfig] Checking/Creating current time shift directory '%s'." % currentPath)
	try:
		makedirs(currentPath, 0o755, exist_ok=True)
	except OSError as err:
		print("[UsageConfig] Error %d: Unable to create current time shift directory '%s'!  (%s)" % (err.errno, currentPath, err.strerror))
		if defaultPath != currentPath:
			print("[UsageConfig] Checking/Creating default time shift directory '%s'." % defaultPath)
			try:
				makedirs(defaultPath, 0o755, exist_ok=True)
			except OSError as err:
				print("[UsageConfig] Error %d: Unable to create default time shift directory '%s'!  (%s)" % (err.errno, defaultPath, err.strerror))

	# The following code temporarily maintains the deprecated timeshift_path so it is available for external plug ins.
	config.usage.timeshift_path = NoSave(ConfigText(default=config.timeshift.path.value))

	def setTimeshiftPath(configElement):
		config.usage.timeshift_path.value = configElement.value
		eSettings.setTimeshiftPath(configElement.value)

	config.timeshift.path.addNotifier(setTimeshiftPath)

	config.timeshift.recordingPath = ConfigSelection(default="<default>", choices=choiceList)
	config.timeshift.recordingPath.load()
	if config.timeshift.recordingPath.saved_value:
		savedValue = config.timeshift.recordingPath.saved_value if config.timeshift.recordingPath.saved_value.startswith("<") else pathjoin(config.timeshift.recordingPath.saved_value, "")
		if savedValue and savedValue not in choiceList:
			config.timeshift.recordingPath.setChoices(choiceList + [(savedValue, savedValue)], default="<default>")
			config.timeshift.recordingPath.value = savedValue
	config.timeshift.recordingPath.save()


def calcFrontendPriorityIntval(config_priority, config_priority_multiselect, config_priority_strictly):
	elem = config_priority.value
	if elem in ("expert_mode", "experimental_mode"):
		elem = int(config_priority_multiselect.value)
		if elem > 0:
			elem = int(elem) + int(eDVBFrontend.preferredFrontendBinaryMode)
			if config_priority.value == "experimental_mode":
				if config_priority_strictly.value == "yes":
					elem += eDVBFrontend.preferredFrontendPrioForced
				elif config_priority_strictly.value == "while_available":
					elem += eDVBFrontend.preferredFrontendPrioHigh
	return elem


def updateChoices(sel, choices):
	if choices:
		defval = None
		val = int(sel.value)
		if val not in choices:
			tmp = choices[:]
			tmp.reverse()
			for x in tmp:
				if x < val:
					defval = str(x)
					break
		sel.setChoices(list(map(str, choices)), defval)


def preferredPath(path):
	if config.usage.setup_level.index < 2 or path == "<default>":
		return None  # config.usage.default_path.value, but delay lookup until usage.
	elif path == "<current>":
		return config.movielist.last_videodir.value
	elif path == "<timer>":
		return config.movielist.last_timer_videodir.value
	else:
		return path


def preferredTimerPath():
	return preferredPath(config.usage.timer_path.value)


def preferredInstantRecordPath():
	return preferredPath(config.usage.instantrec_path.value)


def preferredTimeShiftRecordingPath():
	return preferredPath(config.timeshift.recordingPath.value) or defaultMoviePath()


def defaultMoviePath():
	return defaultRecordingLocation(config.usage.default_path.value)


def patchTuxtxtConfFile(dummyConfigElement):
	print("[UsageConfig] TuxTxt: Patching tuxtxt2.conf.")
	if config.usage.tuxtxt_font_and_res.value == "X11_SD":
		tuxtxt2 = [
			["UseTTF", 0],
			["TTFBold", 1],
			["TTFScreenResX", 720],
			["StartX", 50],
			["EndX", 670],
			["StartY", 30],
			["EndY", 555],
			["TTFShiftY", 0],
			["TTFShiftX", 0],
			["TTFWidthFactor16", 26],
			["TTFHeightFactor16", 14]
		]
	elif config.usage.tuxtxt_font_and_res.value == "TTF_SD":
		tuxtxt2 = [
			["UseTTF", 1],
			["TTFBold", 1],
			["TTFScreenResX", 720],
			["StartX", 50],
			["EndX", 670],
			["StartY", 30],
			["EndY", 555],
			["TTFShiftY", 2],
			["TTFShiftX", 0],
			["TTFWidthFactor16", 29],
			["TTFHeightFactor16", 14]
		]
	elif config.usage.tuxtxt_font_and_res.value == "TTF_HD":
		tuxtxt2 = [
			["UseTTF", 1],
			["TTFBold", 0],
			["TTFScreenResX", 1280],
			["StartX", 80],
			["EndX", 1200],
			["StartY", 35],
			["EndY", 685],
			["TTFShiftY", -3],
			["TTFShiftX", 0],
			["TTFWidthFactor16", 26],
			["TTFHeightFactor16", 14]
		]
	elif config.usage.tuxtxt_font_and_res.value == "TTF_FHD":
		tuxtxt2 = [
			["UseTTF", 1],
			["TTFBold", 0],
			["TTFScreenResX", 1920],
			["StartX", 140],
			["EndX", 1780],
			["StartY", 52],
			["EndY", 1027],
			["TTFShiftY", -6],
			["TTFShiftX", 0],
			["TTFWidthFactor16", 26],
			["TTFHeightFactor16", 14]
		]
	elif config.usage.tuxtxt_font_and_res.value == "expert_mode":
		tuxtxt2 = [
			["UseTTF", int(config.usage.tuxtxt_UseTTF.value)],
			["TTFBold", int(config.usage.tuxtxt_TTFBold.value)],
			["TTFScreenResX", int(config.usage.tuxtxt_TTFScreenResX.value)],
			["StartX", config.usage.tuxtxt_StartX.value],
			["EndX", config.usage.tuxtxt_EndX.value],
			["StartY", config.usage.tuxtxt_StartY.value],
			["EndY", config.usage.tuxtxt_EndY.value],
			["TTFShiftY", int(config.usage.tuxtxt_TTFShiftY.value)],
			["TTFShiftX", int(config.usage.tuxtxt_TTFShiftX.value)],
			["TTFWidthFactor16", config.usage.tuxtxt_TTFWidthFactor16.value],
			["TTFHeightFactor16", config.usage.tuxtxt_TTFHeightFactor16.value]
		]
	tuxtxt2.append(["CleanAlgo", config.usage.tuxtxt_CleanAlgo.value])

	TUXTXT_CFG_FILE = "/etc/tuxtxt/tuxtxt2.conf"
	command = "sed -i -r '"
	for f in tuxtxt2:
		# Replace keyword (%s) followed by any value ([-0-9]+) by that keyword \1 and the new value %d.
		command += r"s|(%s)\s+([-0-9]+)|\\1 %d|;" % (f[0], f[1])
	command += "' %s" % TUXTXT_CFG_FILE
	for f in tuxtxt2:
		# If keyword is not found in file, append keyword and value.
		command += " ; if ! grep -q '%s' %s ; then echo '%s %d' >> %s ; fi" % (f[0], TUXTXT_CFG_FILE, f[0], f[1], TUXTXT_CFG_FILE)
	try:
		ossystem(command)
	except:
		print("[UsageConfig] TuxTxt Error: Failed to patch %s!" % TUXTXT_CFG_FILE)
	print("[UsageConfig] TuxTxt: Patched tuxtxt2.conf.")

	config.usage.tuxtxt_ConfFileHasBeenPatched.setValue(True)
