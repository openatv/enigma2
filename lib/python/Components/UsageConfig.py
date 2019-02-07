import os
from time import time
from enigma import eDVBDB, eEPGCache, setTunerTypePriorityOrder, setPreferredTuner, setSpinnerOnOff, setEnableTtCachingOnOff, eEnv, Misc_Options, eBackgroundFileEraser, eServiceEvent, eDVBFrontend, RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_HALIGN_CENTER, RT_VALIGN_CENTER, RT_WRAP

from Components.About import about
from Components.Harddisk import harddiskmanager
from config import ConfigSubsection, ConfigYesNo, config, ConfigSelection, ConfigText, ConfigNumber, ConfigSet, ConfigLocations, NoSave, ConfigClock, ConfigInteger, ConfigBoolean, ConfigPassword, ConfigIP, ConfigSlider, ConfigSelectionNumber, ConfigFloat, ConfigDictionarySet, ConfigDirectory
from Tools.Directories import resolveFilename, SCOPE_HDD, SCOPE_TIMESHIFT, SCOPE_AUTORECORD, SCOPE_SYSETC, defaultRecordingLocation, fileExists
from Components.NimManager import nimmanager
from Components.ServiceList import refreshServiceList
from SystemInfo import SystemInfo
from Tools.HardwareInfo import HardwareInfo
from boxbranding import getBoxType, getDisplayType
from keyids import KEYIDS
from sys import maxint
import glob
import os
from Components.RcModel import rc_model

def InitUsageConfig():
	AvailRemotes=glob.glob('/usr/share/enigma2/rc_models/*')
	RemoteChoices=[]
	DefaultRemote=rc_model.getRcFolder(GetDefault=True)
	
	remoteSelectable=False
	if AvailRemotes is not None:
		for remote in AvailRemotes:
			if os.path.isfile(remote+'/rc.png') and os.path.isfile(remote+'/rcpositions.xml') and os.path.isfile(remote+'/remote.html'):
				pass
			else:
				AvailRemotes.remove(remote)
		if len(AvailRemotes)>1:
			remoteSelectable=True
			for remote in AvailRemotes:
				toadd = (remote.split('/')[-1], remote.split('/')[-1])
				RemoteChoices.append(toadd)
	config.misc.SettingsVersion = ConfigFloat(default = [1,1], limits = [(1,10),(0,99)])
	config.misc.SettingsVersion.value = [1,1]
	config.misc.SettingsVersion.save_forced = True
	config.misc.SettingsVersion.save()
	config.misc.useNTPminutes = ConfigSelection(default = "30", choices = [("30", "30" + " " +_("minutes")), ("60", _("Hour")), ("1440", _("Once per day"))])
	config.misc.remotecontrol_text_support = ConfigYesNo(default = True)

	config.workaround = ConfigSubsection()
	config.workaround.blueswitch = ConfigSelection(default = "0", choices = [("0", _("QuickMenu/Extensions")), ("1", _("Extensions/QuickMenu"))])
	config.workaround.deeprecord = ConfigYesNo(default = False)
	config.workaround.wakeuptime = ConfigSelectionNumber(default = 5, stepwidth = 1, min = 0, max = 30, wraparound = True)
	config.workaround.wakeupwindow = ConfigSelectionNumber(default = 5, stepwidth = 5, min = 5, max = 60, wraparound = True)

	config.usage = ConfigSubsection()

	#settings for servicemp3 and handling from cuesheet file
	config.usage.useVideoCuesheet = ConfigYesNo(default = True)		#use marker for video media file
	config.usage.useAudioCuesheet = ConfigYesNo(default = True)		#use marker for audio media file
	config.usage.useChapterInfo = ConfigYesNo(default = True) 		#show chapter positions (gst >= 1 and supported media files)
	###

	config.usage.shutdownOK = ConfigBoolean(default = True)
	config.usage.shutdownNOK_action = ConfigSelection(default = "normal", choices = [("normal", _("just boot")), ("standby", _("goto standby")), ("deepstandby", _("goto deep-standby"))])
	config.usage.boot_action = ConfigSelection(default = "normal", choices = [("normal", _("just boot")), ("standby", _("goto standby"))])
	config.usage.showdish = ConfigSelection(default = "flashing", choices = [("flashing", _("Flashing")), ("normal", _("Not Flashing")), ("off", _("Off"))])
	config.usage.multibouquet = ConfigYesNo(default = True)
	config.usage.maxchannelnumlen = ConfigSelection(default = "4", choices = [("1", _("1")), ("2", _("2")),("3", _("3")), ("4", _("4")), ("5", _("5"))])
	config.usage.numzaptimeoutmode = ConfigSelection(default = "standard", choices = [("standard", _("Standard")), ("userdefined", _("User defined")), ("off", _("off"))])
	config.usage.numzaptimeout1 = ConfigSlider(default = 3000, increment = 250, limits = (500, 5000))
	config.usage.numzaptimeout2 = ConfigSlider(default = 1000, increment = 250, limits = (0, 5000))
	config.usage.numzappicon = ConfigYesNo(default = False)
	config.usage.use_pig = ConfigYesNo(default = False)
	config.usage.update_available = NoSave(ConfigYesNo(default = False))
	config.misc.ecm_info = ConfigYesNo(default = False)
	config.usage.menu_show_numbers = ConfigYesNo(default = False)
	config.usage.subnetwork = ConfigYesNo(default = True)
	config.usage.subnetwork_cable = ConfigYesNo(default = True)
	config.usage.subnetwork_terrestrial = ConfigYesNo(default = True)

	config.usage.alternative_number_mode = ConfigYesNo(default = False)
	def alternativeNumberModeChange(configElement):
		eDVBDB.getInstance().setNumberingMode(configElement.value)
		refreshServiceList()
	config.usage.alternative_number_mode.addNotifier(alternativeNumberModeChange)

	config.usage.servicetype_icon_mode = ConfigSelection(default = "0", choices = [("0", _("None")), ("1", _("Left from servicename")), ("2", _("Right from servicename"))])
	config.usage.servicetype_icon_mode.addNotifier(refreshServiceList)
	config.usage.crypto_icon_mode = ConfigSelection(default = "0", choices = [("0", _("None")), ("1", _("Left from servicename")), ("2", _("Right from servicename"))])
	config.usage.crypto_icon_mode.addNotifier(refreshServiceList)
	config.usage.record_indicator_mode = ConfigSelection(default = "3", choices = [("0", _("None")), ("1", _("Left from servicename")), ("2", _("Right from servicename")), ("3", _("Red colored"))])
	config.usage.record_indicator_mode.addNotifier(refreshServiceList)

	# just merge note, config.usage.servicelist_column was allready there
	choicelist = [("-1", _("Disable")), ("0", _("Eventname only"))]
	for i in range(100,1325,25):
		choicelist.append(("%d" % i, ngettext("%d pixel wide", "%d pixels wide", i) % i))
	config.usage.servicelist_column = ConfigSelection(default="-1", choices=choicelist)
	config.usage.servicelist_column.addNotifier(refreshServiceList)
	config.usage.servicelist_infokey = ConfigSelection(default = "event", choices = [("epg", _("Single EPG")), ("event", _("Eventview"))])

	config.usage.service_icon_enable = ConfigYesNo(default = False)
	config.usage.service_icon_enable.addNotifier(refreshServiceList)
	config.usage.servicelist_picon_downsize = ConfigSelectionNumber(default = -2, stepwidth = 1, min = -8, max = 0, wraparound = True)
	config.usage.servicelist_picon_ratio = ConfigSelection(default = "167", choices = [("100", _("1:1")), ("150", _("3:2")), ("133", _("4:3")), ("250", _("5:2")), ("167", _("5:3")), ("233", _("7:3"))])
	config.usage.servicelist_cursor_behavior = ConfigSelection(default = "keep", choices = [
		("standard", _("Standard")),
		("keep", _("Keep service")),
		("reverseB", _("Reverse bouquet buttons")),
		("keep reverseB", _("Keep service") + " + " + _("Reverse bouquet buttons"))])
	config.usage.multiepg_ask_bouquet = ConfigYesNo(default = False)
	config.usage.showpicon = ConfigYesNo(default = True)
	
#########  Workaround for VTI Skins   ##############
	config.usage.picon_dir = ConfigDirectory(default = "/usr/share/enigma2/picon")
	config.usage.movielist_show_picon = ConfigYesNo(default = False)
	config.usage.use_extended_pig = ConfigYesNo(default = False)
	config.usage.use_extended_pig_channelselection = ConfigYesNo(default = False)
	config.usage.servicelist_preview_mode = ConfigYesNo(default = False)
	config.usage.numberzap_show_picon = ConfigYesNo(default = False)
	config.usage.numberzap_show_servicename = ConfigYesNo(default = False)
#####################################################

	config.usage.panicbutton = ConfigYesNo(default = False)
	config.usage.panicchannel = ConfigInteger(default = 1, limits=(1,5000) )
	config.usage.quickzap_bouquet_change = ConfigYesNo(default = False)
	config.usage.e1like_radio_mode = ConfigYesNo(default = True)

	choicelist = []
	for i in range(1, 21):
		choicelist.append(("%d" % i, ngettext("%d second", "%d seconds", i) % i))
	config.usage.infobar_timeout = ConfigSelection(default = "5", choices = [("0", _("No timeout"))] + choicelist)
	config.usage.show_infobar_on_zap = ConfigYesNo(default = True)
	config.usage.show_infobar_on_skip = ConfigYesNo(default = True)
	config.usage.show_infobar_locked_on_pause = ConfigYesNo(default = True)
	config.usage.show_infobar_on_event_change = ConfigYesNo(default = False)
	config.usage.show_infobar_channel_number = ConfigYesNo(default = False)	
	config.usage.show_infobar_lite = ConfigYesNo(default = False)
	config.usage.show_infobar_do_dimming = ConfigYesNo(default = False)
	config.usage.show_infobar_dimming_speed = ConfigSelectionNumber(min = 1, max = 40, stepwidth = 1, default = 10, wraparound = True)
	config.usage.show_infobar_channel_number = ConfigYesNo(default = False)
	config.usage.show_second_infobar = ConfigSelection(default = "1", choices = [("0", _("Off")), ("1", _("Event Info")), ("2", _("2nd Infobar INFO")), ("3", _("2nd Infobar ECM"))])
	config.usage.second_infobar_timeout = ConfigSelection(default = "5", choices = [("0", _("No timeout"))] + choicelist)
	def showsecondinfobarChanged(configElement):
		if config.usage.show_second_infobar.value != "INFOBAREPG":
			SystemInfo["InfoBarEpg"] = True
		else:
			SystemInfo["InfoBarEpg"] = False
	config.usage.show_second_infobar.addNotifier(showsecondinfobarChanged, immediate_feedback = True)
	config.usage.infobar_frontend_source = ConfigSelection(default = "tuner", choices = [("settings", _("Settings")), ("tuner", _("Tuner"))])
	
	config.usage.show_picon_bkgrn = ConfigSelection(default = "transparent", choices = [("none", _("Disabled")), ("transparent", _("Transparent")), ("blue", _("Blue")), ("red", _("Red")), ("black", _("Black")), ("white", _("White")), ("lightgrey", _("Light Grey")), ("grey", _("Grey"))])

	config.usage.show_spinner = ConfigYesNo(default = True)
	config.usage.enable_tt_caching = ConfigYesNo(default = True)

	config.usage.tuxtxt_font_and_res = ConfigSelection(default = "TTF_SD", choices = [("X11_SD", _("Fixed X11 font (SD)")), ("TTF_SD", _("TrueType font (SD)")), ("TTF_HD", _("TrueType font (HD)")), ("TTF_FHD", _("TrueType font (full-HD)")), ("expert_mode", _("Expert mode"))])
	config.usage.tuxtxt_UseTTF = ConfigSelection(default = "1", choices = [("0", "0"), ("1", "1")])
	config.usage.tuxtxt_TTFBold = ConfigSelection(default = "1", choices = [("0", "0"), ("1", "1")])
	config.usage.tuxtxt_TTFScreenResX = ConfigSelection(default = "720", choices = [("720", "720"), ("1280", "1280"), ("1920", "1920")])
	config.usage.tuxtxt_StartX = ConfigInteger(default=50, limits = (0, 200))
	config.usage.tuxtxt_EndX = ConfigInteger(default=670, limits = (500, 1920))
	config.usage.tuxtxt_StartY = ConfigInteger(default=30, limits = (0, 200))
	config.usage.tuxtxt_EndY = ConfigInteger(default=555, limits = (400, 1080))
	config.usage.tuxtxt_TTFShiftY = ConfigSelection(default = "2", choices = [("-9", "-9"), ("-8", "-8"), ("-7", "-7"), ("-6", "-6"), ("-5", "-5"), ("-4", "-4"), ("-3", "-3"), ("-2", "-2"), ("-1", "-1"), ("0", "0"), ("1", "1"), ("2", "2"), ("3", "3"), ("4", "4"), ("5", "5"), ("6", "6"), ("7", "7"), ("8", "8"), ("9", "9")])
	config.usage.tuxtxt_TTFShiftX = ConfigSelection(default = "0", choices = [("-9", "-9"), ("-8", "-8"), ("-7", "-7"), ("-6", "-6"), ("-5", "-5"), ("-4", "-4"), ("-3", "-3"), ("-2", "-2"), ("-1", "-1"), ("0", "0"), ("1", "1"), ("2", "2"), ("3", "3"), ("4", "4"), ("5", "5"), ("6", "6"), ("7", "7"), ("8", "8"), ("9", "9")])
	config.usage.tuxtxt_TTFWidthFactor16 = ConfigInteger(default=29, limits = (8, 31))
	config.usage.tuxtxt_TTFHeightFactor16 = ConfigInteger(default=14, limits = (8, 31))
	config.usage.tuxtxt_CleanAlgo = ConfigInteger(default=0, limits = (0, 9))
	config.usage.tuxtxt_ConfFileHasBeenPatched = NoSave(ConfigYesNo(default=False))

	config.usage.tuxtxt_font_and_res.addNotifier(patchTuxtxtConfFile, initial_call = False, immediate_feedback = False, call_on_save_or_cancel = True)
	config.usage.tuxtxt_UseTTF.addNotifier(patchTuxtxtConfFile, initial_call = False, immediate_feedback = False, call_on_save_or_cancel = True)
	config.usage.tuxtxt_TTFBold.addNotifier(patchTuxtxtConfFile, initial_call = False, immediate_feedback = False, call_on_save_or_cancel = True)
	config.usage.tuxtxt_TTFScreenResX.addNotifier(patchTuxtxtConfFile, initial_call = False, immediate_feedback = False, call_on_save_or_cancel = True)
	config.usage.tuxtxt_StartX.addNotifier(patchTuxtxtConfFile, initial_call = False, immediate_feedback = False, call_on_save_or_cancel = True)
	config.usage.tuxtxt_EndX.addNotifier(patchTuxtxtConfFile, initial_call = False, immediate_feedback = False, call_on_save_or_cancel = True)
	config.usage.tuxtxt_StartY.addNotifier(patchTuxtxtConfFile, initial_call = False, immediate_feedback = False, call_on_save_or_cancel = True)
	config.usage.tuxtxt_EndY.addNotifier(patchTuxtxtConfFile, initial_call = False, immediate_feedback = False, call_on_save_or_cancel = True)
	config.usage.tuxtxt_TTFShiftY.addNotifier(patchTuxtxtConfFile, initial_call = False, immediate_feedback = False, call_on_save_or_cancel = True)
	config.usage.tuxtxt_TTFShiftX.addNotifier(patchTuxtxtConfFile, initial_call = False, immediate_feedback = False, call_on_save_or_cancel = True)
	config.usage.tuxtxt_TTFWidthFactor16.addNotifier(patchTuxtxtConfFile, initial_call = False, immediate_feedback = False, call_on_save_or_cancel = True)
	config.usage.tuxtxt_TTFHeightFactor16.addNotifier(patchTuxtxtConfFile, initial_call = False, immediate_feedback = False, call_on_save_or_cancel = True)
	config.usage.tuxtxt_CleanAlgo.addNotifier(patchTuxtxtConfFile, initial_call = False, immediate_feedback = False, call_on_save_or_cancel = True)
	
	config.usage.sort_settings = ConfigYesNo(default = False)
	config.usage.sort_menu_byname = ConfigYesNo(default = False)
	config.usage.sort_plugins_byname = ConfigYesNo(default = True)
	config.usage.plugins_sort_mode = ConfigSelection(default = "user", choices = [
		("a_z", _("alphabetical")),
		("default", _("Default")),
		("user", _("user defined")),])
	config.usage.plugin_sort_weight = ConfigDictionarySet()
	config.usage.menu_sort_weight = ConfigDictionarySet(default = { "mainmenu" : {"submenu" : {} }})
	config.usage.menu_sort_mode = ConfigSelection(default = "user", choices = [
		("a_z", _("alphabetical")),
		("default", _("Default")),
		("user", _("user defined")),])
	config.usage.sort_pluginlist = ConfigYesNo(default = True)
	config.usage.sort_extensionslist = ConfigYesNo(default = False)
	config.usage.show_restart_network_extensionslist = ConfigYesNo(default = True)
	config.usage.movieplayer_pvrstate = ConfigYesNo(default = False)
	config.usage.rc_model = ConfigSelection(default = DefaultRemote, choices = RemoteChoices)

	choicelist = []
	for i in (10, 30):
		choicelist.append(("%d" % i, ngettext("%d second", "%d seconds", i) % i))
	for i in (60, 120, 300, 600, 1200, 1800):
		m = i / 60
		choicelist.append(("%d" % i, ngettext("%d minute", "%d minutes", m) % m))
	for i in (3600, 7200, 14400):
		h = i / 3600
		choicelist.append(("%d" % i, ngettext("%d hour", "%d hours", h) % h))
	config.usage.hdd_standby = ConfigSelection(default = "300", choices = [("0", _("No standby"))] + choicelist)
	config.usage.hdd_standby_in_standby = ConfigSelection(default = "-1", choices = [("-1", _("Same as in active")), ("0", _("No standby"))] + choicelist)
	config.usage.hdd_timer = ConfigYesNo(default = False)	
	config.usage.output_12V = ConfigSelection(default = "do not change", choices = [
		("do not change", _("Do not change")), ("off", _("Off")), ("on", _("On")) ])

	config.usage.pip_zero_button = ConfigSelection(default = "standard", choices = [
		("standard", _("Standard")), ("swap", _("Swap PiP and main picture")),
		("swapstop", _("Move PiP to main picture")), ("stop", _("Stop PiP")) ])
	config.usage.pip_hideOnExit = ConfigSelection(default = "no", choices = [
		("no", _("No")), ("popup", _("With popup")), ("without popup", _("Without popup")) ])
	choicelist = [("-1", _("Disabled")), ("0", _("No timeout"))]
	for i in [60, 300, 600, 900, 1800, 2700, 3600]:
		m = i/60
		choicelist.append(("%d" % i, ngettext("%d minute", "%d minutes", m) % m))
	config.usage.pip_last_service_timeout = ConfigSelection(default = "-1", choices = choicelist)
	if not os.path.exists(resolveFilename(SCOPE_HDD)):
		try:
			os.mkdir(resolveFilename(SCOPE_HDD),0755)
		except:
			pass
	config.usage.default_path = ConfigText(default = resolveFilename(SCOPE_HDD))
	if not config.usage.default_path.value.endswith('/'):
		tmpvalue = config.usage.default_path.value
		config.usage.default_path.setValue(tmpvalue + '/')
		config.usage.default_path.save()
	def defaultpathChanged(configElement):
		tmpvalue = config.usage.default_path.value
		try:
			if not os.path.exists(tmpvalue):
				os.system("mkdir -p %s" %tmpvalue)
		except:
			print "Failed to create recording path: %s" %tmpvalue
		if not config.usage.default_path.value.endswith('/'):
			config.usage.default_path.setValue(tmpvalue + '/')
			config.usage.default_path.save()
	config.usage.default_path.addNotifier(defaultpathChanged, immediate_feedback = False)

	config.usage.timer_path = ConfigText(default = "<default>")
	config.usage.autorecord_path = ConfigText(default = "<default>")
	config.usage.instantrec_path = ConfigText(default = "<default>")

	if not os.path.exists(resolveFilename(SCOPE_TIMESHIFT)):
		try:
			os.mkdir(resolveFilename(SCOPE_TIMESHIFT),0755)
		except:
			pass
	config.usage.timeshift_path = ConfigText(default = resolveFilename(SCOPE_TIMESHIFT))
	if not config.usage.default_path.value.endswith('/'):
		tmpvalue = config.usage.timeshift_path.value
		config.usage.timeshift_path.setValue(tmpvalue + '/')
		config.usage.timeshift_path.save()
	def timeshiftpathChanged(configElement):
		if not config.usage.timeshift_path.value.endswith('/'):
			tmpvalue = config.usage.timeshift_path.value
			config.usage.timeshift_path.setValue(tmpvalue + '/')
			config.usage.timeshift_path.save()
	config.usage.timeshift_path.addNotifier(timeshiftpathChanged, immediate_feedback = False)
	config.usage.allowed_timeshift_paths = ConfigLocations(default = [resolveFilename(SCOPE_TIMESHIFT)])


	if not os.path.exists(resolveFilename(SCOPE_AUTORECORD)):
		try:
			os.mkdir(resolveFilename(SCOPE_AUTORECORD),0755)
		except:
			pass
	config.usage.autorecord_path = ConfigText(default = resolveFilename(SCOPE_AUTORECORD))
	if not config.usage.default_path.value.endswith('/'):
		tmpvalue = config.usage.autorecord_path.value
		config.usage.autorecord_path.setValue(tmpvalue + '/')
		config.usage.autorecord_path.save()
	def autorecordpathChanged(configElement):
		if not config.usage.autorecord_path.value.endswith('/'):
			tmpvalue = config.usage.autorecord_path.value
			config.usage.autorecord_path.setValue(tmpvalue + '/')
			config.usage.autorecord_path.save()
	config.usage.autorecord_path.addNotifier(autorecordpathChanged, immediate_feedback = False)
	config.usage.allowed_autorecord_paths = ConfigLocations(default = [resolveFilename(SCOPE_AUTORECORD)])


	config.usage.movielist_trashcan = ConfigYesNo(default=True)
	config.usage.movielist_trashcan_network_clean = ConfigYesNo(default=False)
	config.usage.movielist_trashcan_days = ConfigSelectionNumber(min = 1, max = 31, stepwidth = 1, default = 8, wraparound = True)
	config.usage.movielist_trashcan_reserve = ConfigNumber(default = 40)
	config.usage.on_movie_start = ConfigSelection(default = "ask yes", choices = [
		("ask yes", _("Ask user (with default as 'yes')")),
		("ask no", _("Ask user (with default as 'no')")),
		("resume", _("Resume from last position")),
		("beginning", _("Start from the beginning"))])
	config.usage.on_movie_stop = ConfigSelection(default = "movielist", choices = [
		("ask", _("Ask user")), ("movielist", _("Return to movie list")), ("quit", _("Return to previous service")) ])
	config.usage.on_movie_eof = ConfigSelection(default = "movielist", choices = [
		("ask", _("Ask user")), ("movielist", _("Return to movie list")), ("quit", _("Return to previous service")), ("pause", _("Pause movie at end")), ("playlist", _("Play next (return to movie list)")),
		("playlistquit", _("Play next (return to previous service)")), ("loop", _("Continues play (loop)")), ("repeatcurrent", _("Repeat"))])
	config.usage.next_movie_msg = ConfigYesNo(default = True)
	config.usage.last_movie_played = ConfigText()
	config.usage.leave_movieplayer_onExit = ConfigSelection(default = "no", choices = [
		("no", _("No")), ("popup", _("With popup")), ("without popup", _("Without popup")), ("stop", _("Behave like stop-button")) ])

	config.usage.setup_level = ConfigSelection(default = "expert", choices = [
		("simple", _("Simple")),
		("intermediate", _("Intermediate")),
		("expert", _("Expert")) ])

	choicelist = [("standby", _("Standby")),("deepstandby", _("Deep Standby"))]
	config.usage.sleep_timer_action = ConfigSelection(default = "deepstandby", choices = choicelist)
	choicelist = [("0", _("Disabled")),("event_standby", _("Execute after current event"))]
	for i in range(900, 14401, 900):
		m = abs(i / 60)
		m = ngettext("%d minute", "%d minutes", m) % m
		choicelist.append((str(i), _("Execute in ") + m))
	config.usage.sleep_timer = ConfigSelection(default = "0", choices = choicelist)

	choicelist = [("show_menu", _("Show shutdown menu")), ("shutdown", _("Immediate shutdown")), ("standby", _("Standby")), ("standby_noTVshutdown", _("Standby without TV shutdown")), ("sleeptimer", _("SleepTimer")), ("powertimerStandby", _("PowerTimer Standby")), ("powertimerDeepStandby", _("PowerTimer DeepStandby"))]
	config.usage.on_long_powerpress = ConfigSelection(default = "show_menu", choices = choicelist)
	config.usage.on_short_powerpress = ConfigSelection(default = "standby", choices = choicelist)

	config.usage.long_press_emulation_key = ConfigSelection(default = "0", choices = [
		("0", _("None")),
		(str(KEYIDS["KEY_TV"]), _("TV")),
		(str(KEYIDS["KEY_RADIO"]), _("Radio")),
		(str(KEYIDS["KEY_AUDIO"]), _("Audio")),
		(str(KEYIDS["KEY_VIDEO"]), _("List/Fav")),
		(str(KEYIDS["KEY_HOME"]), _("Home")),
		(str(KEYIDS["KEY_END"]), _("End")),
		(str(KEYIDS["KEY_HELP"]), _("Help")),
		(str(KEYIDS["KEY_INFO"]), _("Info (EPG)")),
		(str(KEYIDS["KEY_TEXT"]), _("Teletext")),
		(str(KEYIDS["KEY_SUBTITLE"]), _("Subtitle")),
		(str(KEYIDS["KEY_FAVORITES"]), _("Favorites")) ])

	choicelist = [("0", _("Disabled"))]
	for i in (5, 30, 60, 300, 600, 900, 1200, 1800, 2700, 3600):
		if i < 60:
			m = ngettext("%d second", "%d seconds", i) % i
		else:
			m = abs(i / 60)
			m = ngettext("%d minute", "%d minutes", m) % m
		choicelist.append(("%d" % i, m))
	config.usage.screen_saver = ConfigSelection(default = "0", choices = choicelist)

	config.usage.check_timeshift = ConfigYesNo(default = True)

	config.usage.alternatives_priority = ConfigSelection(default = "0", choices = [
		("0", "DVB-S/-C/-T"),
		("1", "DVB-S/-T/-C"),
		("2", "DVB-C/-S/-T"),
		("3", "DVB-C/-T/-S"),
		("4", "DVB-T/-C/-S"),
		("5", "DVB-T/-S/-C"),
		("127", _("No priority")) ])

	config.usage.remote_fallback_enabled = ConfigYesNo(default = False)
	config.usage.remote_fallback = ConfigText(default = "http://IP-ADRESS:8001", visible_width = 50, fixed_size = False)

	nims = [("-1", _("auto")), ("expert_mode", _("Expert mode")), ("experimental_mode", _("Experimental mode"))]
	rec_nims = [("-2", _("Disabled")), ("-1", _("auto")), ("expert_mode", _("Expert mode")), ("experimental_mode", _("Experimental mode"))]
	nims_multi = [("-1", _("auto"))]
	rec_nims_multi = [("-2", _("Disabled")), ("-1", _("auto"))]

	slots = len(nimmanager.nim_slots)
	for i in range(0,slots):
		slotname = nimmanager.nim_slots[i].getSlotName()
		nims.append((str(i), slotname))
		rec_nims.append((str(i), slotname))
		slotx = 2**i
		nims_multi.append((str(slotx), slotname))
		rec_nims_multi.append((str(slotx), slotname))
		for x in range(i+1,slots):
			slotx += 2**x
			name = nimmanager.nim_slots[x].getSlotName()
			if len(name.split()) == 2: name = name.split()[1]
			slotname += '+' + name
			nims_multi.append((str(slotx), slotname))
			rec_nims_multi.append((str(slotx), slotname))

	priority_strictly_choices = [("no", _("No")), ("yes", _("Yes")), ("while_available", _("While available"))]
	config.usage.frontend_priority                       = ConfigSelection(default = "-1", choices = nims)
	config.usage.frontend_priority_multiselect           = ConfigSelection(default = "-1", choices = nims_multi)
	config.usage.frontend_priority_strictly              = ConfigSelection(default = "no", choices = priority_strictly_choices)
	config.usage.frontend_priority_intval                = NoSave(ConfigInteger(default = 0, limits = (-99, maxint)))
	config.usage.recording_frontend_priority             = ConfigSelection(default = "-2", choices = rec_nims)
	config.usage.recording_frontend_priority_multiselect = ConfigSelection(default = "-2", choices = rec_nims_multi)
	config.usage.recording_frontend_priority_strictly    = ConfigSelection(default = "no", choices = priority_strictly_choices)
	config.usage.recording_frontend_priority_intval      = NoSave(ConfigInteger(default = 0, limits = (-99, maxint)))
	config.misc.disable_background_scan = ConfigYesNo(default = False)

	config.usage.jobtaksextensions = ConfigYesNo(default = True)

	config.usage.servicenum_fontsize = ConfigSelectionNumber(default = 0, stepwidth = 1, min = -8, max = 10, wraparound = True)
	config.usage.servicename_fontsize = ConfigSelectionNumber(default = 0, stepwidth = 1, min = -8, max = 10, wraparound = True)
	config.usage.serviceinfo_fontsize = ConfigSelectionNumber(default = 0, stepwidth = 1, min = -8, max = 10, wraparound = True)
	config.usage.serviceitems_per_page = ConfigSelectionNumber(default = 18, stepwidth = 1, min = 8, max = 40, wraparound = True)
	config.usage.show_servicelist = ConfigYesNo(default = True)
	config.usage.servicelist_mode = ConfigSelection(default = "standard", choices = [
		("standard", _("Standard")),
		("simple", _("Simple")) ] )
	config.usage.servicelistpreview_mode = ConfigYesNo(default = False)
	config.usage.tvradiobutton_mode = ConfigSelection(default="BouquetList", choices = [
					("ChannelList", _("Channel List")),
					("BouquetList", _("Bouquet List")),
					("MovieList", _("Movie List"))])
	config.usage.channelbutton_mode = ConfigSelection(default="0", choices = [
					("0", _("Just change channels")),
					("1", _("Channel List")),
					("2", _("Bouquet List")),
					("3", _("Just change Bouquet"))])
	config.usage.updownbutton_mode = ConfigSelection(default="1", choices = [
					("0", _("Just change channels")),
					("1", _("Channel List"))])
	if fileExists("/usr/lib/enigma2/python/Plugins/Extensions/CoolTVGuide/plugin.pyo"):
		config.usage.okbutton_mode = ConfigSelection(default="0", choices = [
						("0", _("InfoBar")),
						("1", _("Channel List")),
						("2", _("Show CoolInfoGuide")),
						("3", _("Show CoolSingleGuide")),
						("4", _("Show CoolTVGuide")),
						("5", _("Show CoolEasyGuide")),
						("6", _("Show CoolChannelGuide"))])
	else:
		config.usage.okbutton_mode = ConfigSelection(default="0", choices = [
						("0", _("InfoBar")),
						("1", _("Channel List"))])
	config.usage.show_bouquetalways = ConfigYesNo(default = False)
	config.usage.show_event_progress_in_servicelist = ConfigSelection(default = 'barright', choices = [
		('barleft', _("Progress bar left")),
		('barright', _("Progress bar right")),
		('percleft', _("Percentage left")),
		('percright', _("Percentage right")),
		('no', _("No")) ])
	config.usage.show_channel_numbers_in_servicelist = ConfigYesNo(default = True)
	config.usage.show_channel_jump_in_servicelist = ConfigSelection(default="quick", choices = [
					("quick", _("Quick Actions")),
					("alpha", _("Alpha")),
					("number", _("Number"))])

	config.usage.show_event_progress_in_servicelist.addNotifier(refreshServiceList)
	config.usage.show_channel_numbers_in_servicelist.addNotifier(refreshServiceList)

	#standby
	if getDisplayType() in ('textlcd7segment'):
		config.usage.blinking_display_clock_during_recording = ConfigSelection(default = "Rec", choices = [
						("Rec", _("REC")), 
						("RecBlink", _("Blinking REC")), 
						("Nothing", _("Nothing"))])
	else:
		config.usage.blinking_display_clock_during_recording = ConfigYesNo(default = False)
		
	#in use
	if getDisplayType() in ('textlcd'):
		config.usage.blinking_rec_symbol_during_recording = ConfigSelection(default = "Channel", choices = [
						("Rec", _("REC Symbol")), 
						("RecBlink", _("Blinking REC Symbol")), 
						("Channel", _("Channelname"))])
	if getDisplayType() in ('textlcd7segment'):
		config.usage.blinking_rec_symbol_during_recording = ConfigSelection(default = "Rec", choices = [
						("Rec", _("REC")), 
						("RecBlink", _("Blinking REC")), 
						("Time", _("Time"))])
	else:
		config.usage.blinking_rec_symbol_during_recording = ConfigYesNo(default = True)
		
	if getDisplayType() in ('textlcd7segment'):
		config.usage.show_in_standby = ConfigSelection(default = "time", choices = [
						("time", _("Time")), 
						("nothing", _("Nothing"))])

	config.usage.show_message_when_recording_starts = ConfigYesNo(default = True)

	config.usage.load_length_of_movies_in_moviellist = ConfigYesNo(default = True)
	config.usage.show_icons_in_movielist = ConfigSelection(default = 'i', choices = [
		('o', _("Off")),
		('p', _("Progress")),
		('s', _("Small progress")),
		('i', _("Icons")),
	])
	config.usage.movielist_unseen = ConfigYesNo(default = True)

	config.usage.swap_snr_on_osd = ConfigYesNo(default = False)
	config.usage.swap_time_display_on_osd = ConfigSelection(default = "0", choices = [("0", _("Skin Setting")), ("1", _("Mins")), ("2", _("Mins Secs")), ("3", _("Hours Mins")), ("4", _("Hours Mins Secs")), ("5", _("Percentage"))])
	config.usage.swap_media_time_display_on_osd = ConfigSelection(default = "0", choices = [("0", _("Skin Setting")), ("1", _("Mins")), ("2", _("Mins Secs")), ("3", _("Hours Mins")), ("4", _("Hours Mins Secs")), ("5", _("Percentage"))])
	config.usage.swap_time_remaining_on_osd = ConfigSelection(default = "0", choices = [("0", _("Remaining")), ("1", _("Elapsed")), ("2", _("Elapsed & Remaining")), ("3", _("Remaining & Elapsed"))])
	config.usage.elapsed_time_positive_osd = ConfigYesNo(default = False)
	config.usage.swap_time_display_on_vfd = ConfigSelection(default = "0", choices = [("0", _("Skin Setting")), ("1", _("Mins")), ("2", _("Mins Secs")), ("3", _("Hours Mins")), ("4", _("Hours Mins Secs")), ("5", _("Percentage"))])
	config.usage.swap_media_time_display_on_vfd = ConfigSelection(default = "0", choices = [("0", _("Skin Setting")), ("1", _("Mins")), ("2", _("Mins Secs")), ("3", _("Hours Mins")), ("4", _("Hours Mins Secs")), ("5", _("Percentage"))])
	config.usage.swap_time_remaining_on_vfd = ConfigSelection(default = "0", choices = [("0", _("Remaining")), ("1", _("Elapsed")), ("2", _("Elapsed & Remaining")), ("3", _("Remaining & Elapsed"))])
	config.usage.elapsed_time_positive_vfd = ConfigYesNo(default = False)
	config.usage.lcd_scroll_delay = ConfigSelection(default = "10000", choices = [
		("10000", "10 " + _("seconds")),
		("20000", "20 " + _("seconds")),
		("30000", "30 " + _("seconds")),
		("60000", "1 " + _("minute")),
		("300000", "5 " + _("minutes")),
		("noscrolling", _("off"))])
	config.usage.lcd_scroll_speed = ConfigSelection(default = "300", choices = [
		("500", _("slow")),
		("300", _("normal")),
		("100", _("fast"))])
	

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

	config.usage.hide_zap_errors = ConfigYesNo(default = True)
	config.misc.use_ci_assignment = ConfigYesNo(default = True)
	config.usage.hide_ci_messages = ConfigYesNo(default = False)
	config.usage.show_cryptoinfo = ConfigSelection([("0", _("Off")),("1", _("One line")),("2", _("Two lines"))], "2")
	config.usage.show_eit_nownext = ConfigYesNo(default = True)
	config.usage.show_vcr_scart = ConfigYesNo(default = False)
	config.usage.pic_resolution = ConfigSelection(default = None, choices = [(None, _("Same resolution as skin")), ("(720, 576)","720x576"), ("(1280, 720)", "1280x720"), ("(1920, 1080)", "1920x1080")])
	config.usage.enable_delivery_system_workaround = ConfigYesNo(default = False)

	config.usage.boolean_graphic = ConfigYesNo(default=False)
	config.usage.show_slider_value = ConfigYesNo(default=True)

	config.epg = ConfigSubsection()
	config.epg.eit = ConfigYesNo(default = True)
	config.epg.mhw = ConfigYesNo(default = False)
	config.epg.freesat = ConfigYesNo(default = True)
	config.epg.viasat = ConfigYesNo(default = True)
	config.epg.netmed = ConfigYesNo(default = True)
	config.epg.virgin = ConfigYesNo(default = False)
	config.epg.saveepg = ConfigYesNo(default = True)
	
	config.misc.showradiopic = ConfigYesNo(default = True)
	config.misc.bootvideo = ConfigYesNo(default = True)
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
		eEPGCache.getInstance().setEpgSources(mask)
	config.epg.eit.addNotifier(EpgSettingsChanged)
	config.epg.mhw.addNotifier(EpgSettingsChanged)
	config.epg.freesat.addNotifier(EpgSettingsChanged)
	config.epg.viasat.addNotifier(EpgSettingsChanged)
	config.epg.netmed.addNotifier(EpgSettingsChanged)
	config.epg.virgin.addNotifier(EpgSettingsChanged)
	
	config.epg.maxdays = ConfigSelectionNumber(min = 1, max = 365, stepwidth = 1, default = 7, wraparound = True)
	def EpgmaxdaysChanged(configElement):
		from enigma import eEPGCache
		eEPGCache.getInstance().setEpgmaxdays(config.epg.maxdays.getValue())
	config.epg.maxdays.addNotifier(EpgmaxdaysChanged)

	config.epg.histminutes = ConfigSelectionNumber(min = 0, max = 120, stepwidth = 15, default = 0, wraparound = True)
	def EpgHistorySecondsChanged(configElement):
		eEPGCache.getInstance().setEpgHistorySeconds(config.epg.histminutes.value*60)
	config.epg.histminutes.addNotifier(EpgHistorySecondsChanged)

	config.epg.cacheloadsched = ConfigYesNo(default = False)
	config.epg.cachesavesched = ConfigYesNo(default = False)
	def EpgCacheLoadSchedChanged(configElement):
		import EpgLoadSave
		EpgLoadSave.EpgCacheLoadCheck()
	def EpgCacheSaveSchedChanged(configElement):
		import EpgLoadSave
		EpgLoadSave.EpgCacheSaveCheck()
	config.epg.cacheloadsched.addNotifier(EpgCacheLoadSchedChanged, immediate_feedback = False)
	config.epg.cachesavesched.addNotifier(EpgCacheSaveSchedChanged, immediate_feedback = False)
	config.epg.cacheloadtimer = ConfigSelectionNumber(default = 24, stepwidth = 1, min = 1, max = 24, wraparound = True)
	config.epg.cachesavetimer = ConfigSelectionNumber(default = 24, stepwidth = 1, min = 1, max = 24, wraparound = True)

	config.osd.dst_left = ConfigSelectionNumber(default = 0, stepwidth = 1, min = 0, max = 720, wraparound = False)
	config.osd.dst_width = ConfigSelectionNumber(default = 720, stepwidth = 1, min = 0, max = 720, wraparound = False)
	config.osd.dst_top = ConfigSelectionNumber(default = 0, stepwidth = 1, min = 0, max = 576, wraparound = False)
	config.osd.dst_height = ConfigSelectionNumber(default = 576, stepwidth = 1, min = 0, max = 576, wraparound = False)
	config.osd.alpha = ConfigSelectionNumber(default = 255, stepwidth = 1, min = 0, max = 255, wraparound = False)
	config.osd.alpha_teletext = ConfigSelectionNumber(default = 255, stepwidth = 1, min = 0, max = 255, wraparound = False)
	config.osd.alpha_webbrowser = ConfigSelectionNumber(default = 255, stepwidth = 1, min = 0, max = 255, wraparound = False)
	config.av.osd_alpha = NoSave(ConfigNumber(default = 255))
	config.osd.threeDmode = ConfigSelection([("off", _("Off")), ("auto", _("Auto")), ("sidebyside", _("Side by Side")),("topandbottom", _("Top and Bottom"))], "auto")
	config.osd.threeDznorm = ConfigSlider(default = 50, increment = 1, limits = (0, 100))
	config.osd.show3dextensions = ConfigYesNo(default = False)
	choiceoptions = [("mode1", _("Mode 1")), ("mode2", _("Mode 2"))]
	config.osd.threeDsetmode = ConfigSelection(default = 'mode1' , choices = choiceoptions )

	hddchoises = [('/etc/enigma2/', 'Internal Flash')]
	for p in harddiskmanager.getMountedPartitions():
		if os.path.exists(p.mountpoint):
			d = os.path.normpath(p.mountpoint)
			if p.mountpoint != '/':
				hddchoises.append((p.mountpoint, d))
	config.misc.epgcachepath = ConfigSelection(default = '/etc/enigma2/', choices = hddchoises)
	config.misc.epgcachefilename = ConfigText(default='epg', fixed_size=False)
	config.misc.epgcache_filename = ConfigText(default = (config.misc.epgcachepath.value + config.misc.epgcachefilename.value.replace('.dat','') + '.dat'))
	def EpgCacheChanged(configElement):
		config.misc.epgcache_filename.setValue(os.path.join(config.misc.epgcachepath.value, config.misc.epgcachefilename.value.replace('.dat','') + '.dat'))
		config.misc.epgcache_filename.save()
		eEPGCache.getInstance().setCacheFile(config.misc.epgcache_filename.value)
		epgcache = eEPGCache.getInstance()
		epgcache.save()
		if not config.misc.epgcache_filename.value.startswith("/etc/enigma2/"):
			if os.path.exists('/etc/enigma2/' + config.misc.epgcachefilename.value.replace('.dat','') + '.dat'):
				os.remove('/etc/enigma2/' + config.misc.epgcachefilename.value.replace('.dat','') + '.dat')
	config.misc.epgcachepath.addNotifier(EpgCacheChanged, immediate_feedback = False)
	config.misc.epgcachefilename.addNotifier(EpgCacheChanged, immediate_feedback = False)

	config.misc.showradiopic = ConfigYesNo(default = True)

	def setHDDStandby(configElement):
		for hdd in harddiskmanager.HDDList():
			hdd[1].setIdleTime(int(configElement.value))
	config.usage.hdd_standby.addNotifier(setHDDStandby, immediate_feedback=False)

	if SystemInfo["12V_Output"]:
		def set12VOutput(configElement):
			Misc_Options.getInstance().set_12V_output(configElement.value == "on" and 1 or 0)
		config.usage.output_12V.addNotifier(set12VOutput, immediate_feedback=False)

	config.usage.keymap = ConfigText(default = eEnv.resolve("${datadir}/enigma2/keymap.xml"))
	config.usage.keytrans = ConfigText(default = eEnv.resolve("${datadir}/enigma2/keytranslation.xml"))
	config.usage.keymap_usermod = ConfigText(default = eEnv.resolve("${datadir}/enigma2/keymap_usermod.xml"))

	config.network = ConfigSubsection()
	if SystemInfo["WakeOnLAN"]:
		def wakeOnLANChanged(configElement):
			if getBoxType() in ('et7000', 'et7100', 'et7500', 'gbx1', 'gbx2', 'gbx3', 'gbx3h', 'et10000', 'gbquadplus', 'gbquad', 'gb800ueplus', 'gb800seplus', 'gbultraue', 'gbultraueh', 'gbultrase', 'gbipbox', 'quadbox2400', 'mutant2400', 'et7x00', 'et8500', 'et8500s'):
				open(SystemInfo["WakeOnLAN"], "w").write(configElement.value and "on" or "off")
			else:
				open(SystemInfo["WakeOnLAN"], "w").write(configElement.value and "enable" or "disable")
		config.network.wol = ConfigYesNo(default = False)
		config.network.wol.addNotifier(wakeOnLANChanged)
	config.network.AFP_autostart = ConfigYesNo(default = False)
	config.network.NFS_autostart = ConfigYesNo(default = True)
	config.network.OpenVPN_autostart = ConfigYesNo(default = False)
	config.network.Samba_autostart = ConfigYesNo(default = True)
	config.network.Inadyn_autostart = ConfigYesNo(default = False)
	config.network.uShare_autostart = ConfigYesNo(default = False)

	config.softwareupdate = ConfigSubsection()
	config.softwareupdate.autosettingsbackup = ConfigYesNo(default = False)
	config.softwareupdate.autoimagebackup = ConfigYesNo(default = False)
	config.softwareupdate.check = ConfigYesNo(default = False)
	config.softwareupdate.checktimer = ConfigSelectionNumber(min = 1, max = 48, stepwidth = 1, default = 6, wraparound = True)
	config.softwareupdate.updatelastcheck = ConfigInteger(default=0)
	config.softwareupdate.updatefound = NoSave(ConfigBoolean(default = False))
	config.softwareupdate.updatebeta = ConfigYesNo(default = False)
	config.softwareupdate.updateisunstable = ConfigInteger(default=0)

	config.timeshift = ConfigSubsection()
	choicelist = [("0", _("Disabled"))]
	for i in (2, 3, 4, 5, 10, 20, 30):
		choicelist.append(("%d" % i, ngettext("%d second", "%d seconds", i) % i))
	for i in (60, 120, 300):
		m = i / 60
		choicelist.append(("%d" % i, ngettext("%d minute", "%d minutes", m) % m))
	config.timeshift.startdelay = ConfigSelection(default = "0", choices = choicelist)
	config.timeshift.showinfobar = ConfigYesNo(default = True)
	config.timeshift.stopwhilerecording = ConfigYesNo(default = False)
	config.timeshift.favoriteSaveAction = ConfigSelection([("askuser", _("Ask user")),("savetimeshift", _("Save and stop")),("savetimeshiftandrecord", _("Save and record")),("noSave", _("Don't save"))], "askuser")
	config.timeshift.autorecord = ConfigYesNo(default = False)
	config.timeshift.isRecording = NoSave(ConfigYesNo(default = False))
	config.timeshift.timeshiftMaxHours = ConfigSelectionNumber(min = 1, max = 999, stepwidth = 1, default = 12, wraparound = True)
	config.timeshift.timeshiftMaxEvents = ConfigSelectionNumber(min = 1, max = 999, stepwidth = 1, default = 12, wraparound = True)
	config.timeshift.timeshiftCheckEvents = ConfigSelection(default = "0", choices = [("0", _("Disabled")), "15", "30", "60", "120", "240", "480"])
	config.timeshift.timeshiftCheckFreeSpace = ConfigSelection(default = "0", choices = [("0", _("No")), ("1024", _("1 GB")),("2048", _("2 GB")),("4096", _("4 GB")),("8192", _("8 GB")),])
	config.timeshift.deleteAfterZap = ConfigYesNo(default = True)
	config.timeshift.filesplitting = ConfigYesNo(default = True)
	config.timeshift.showlivetvmsg = ConfigYesNo(default = True)

	config.seek = ConfigSubsection()
	config.seek.baractivation = ConfigSelection([("leftright", _("Long Left/Right")),("ffrw", _("Long << / >>"))], "leftright")
	config.seek.sensibility = ConfigSelectionNumber(min = 1, max = 10, stepwidth = 1, default = 10, wraparound = True)
	config.seek.selfdefined_13 = ConfigSelectionNumber(min = 1, max = 300, stepwidth = 1, default = 15, wraparound = True)
	config.seek.selfdefined_46 = ConfigSelectionNumber(min = 1, max = 600, stepwidth = 1, default = 60, wraparound = True)
	config.seek.selfdefined_79 = ConfigSelectionNumber(min = 1, max = 1200, stepwidth = 1, default = 300, wraparound = True)

	config.seek.speeds_forward = ConfigSet(default=[2, 4, 8, 16, 32, 64, 128], choices=[2, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128])
	config.seek.speeds_backward = ConfigSet(default=[2, 4, 8, 16, 32, 64, 128], choices=[1, 2, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128])
	config.seek.speeds_slowmotion = ConfigSet(default=[2, 4, 8], choices=[2, 4, 6, 8, 12, 16, 25])

	config.seek.enter_forward = ConfigSelection(default = "2", choices = ["2", "4", "6", "8", "12", "16", "24", "32", "48", "64", "96", "128"])
	config.seek.enter_backward = ConfigSelection(default = "1", choices = ["1", "2", "4", "6", "8", "12", "16", "24", "32", "48", "64", "96", "128"])

	config.seek.on_pause = ConfigSelection(default = "play", choices = [
		("play", _("Play")),
		("step", _("Single step (GOP)")),
		("last", _("Last speed")) ])

	config.seek.withjumps = ConfigYesNo(default = True)
	config.seek.withjumps_after_ff_speed = ConfigSelection([("1", _("never")), ("2", _("2x")), ("4", _("2x, 4x")), ("6", _("2x, 4x, 6x")), ("8", _("2x, 4x, 6x, 8x"))], default="4")
	config.seek.withjumps_forwards_ms  = ConfigSelection([("200", _("0.2s")), ("300", _("0.3s")), ("400", _("0.4s")), ("500", _("0.5s")), ("600", _("0.6s")), ("700", _("0.7s")), ("800", _("0.8s")), ("900", _("0.9s")), ("1000", _("1s")), ("1200", _("1.2s")), ("1500", _("1.5s")), ("1700", _("1.7s")), ("2000", _("2s")), ("2500", _("2.5s")), ("3000", _("3s")), ("3500", _("3.5s")), ("4000", _("4s")), ("5000", _("5s"))], default="700")
	config.seek.withjumps_backwards_ms = ConfigSelection([("200", _("0.2s")), ("300", _("0.3s")), ("400", _("0.4s")), ("500", _("0.5s")), ("600", _("0.6s")), ("700", _("0.7s")), ("800", _("0.8s")), ("900", _("0.9s")), ("1000", _("1s")), ("1200", _("1.2s")), ("1500", _("1.5s")), ("1700", _("1.7s")), ("2000", _("2s")), ("2500", _("2.5s")), ("3000", _("3s")), ("3500", _("3.5s")), ("4000", _("4s")), ("5000", _("5s"))], default="700")
	config.seek.withjumps_repeat_ms    = ConfigSelection([("200", _("0.2s")), ("300", _("0.3s")), ("400", _("0.4s")), ("500", _("0.5s")), ("600", _("0.6s")), ("700", _("0.7s")), ("800", _("0.8s")), ("900", _("0.9s")), ("1000", _("1s"))], default="200")
	config.seek.withjumps_avoid_zero   = ConfigYesNo(default = True)

	config.crash = ConfigSubsection()
	#// handle python crashes
	config.crash.bsodpython = ConfigYesNo(default = True)
	config.crash.bsodpython_ready = NoSave(ConfigYesNo(default = False))
	choicelist = [("0", _("never")), ("1", "1") , ("2", "2"), ("3", "3"), ("4", "4"), ("5", "5"), ("6", "6"), ("7", "7"), ("8", "8"), ("9", "9"), ("10", "10")]
	config.crash.bsodhide = ConfigSelection(default = "1", choices = choicelist)
	config.crash.bsodmax = ConfigSelection(default = "3", choices = choicelist)
	#//
	
	config.crash.enabledebug = ConfigYesNo(default = False)
	config.crash.debugloglimit = ConfigSelectionNumber(min = 1, max = 10, stepwidth = 1, default = 4, wraparound = True)
	config.crash.daysloglimit = ConfigSelectionNumber(min = 1, max = 30, stepwidth = 1, default = 8, wraparound = True)
	config.crash.sizeloglimit = ConfigSelectionNumber(min = 1, max = 20, stepwidth = 1, default = 10, wraparound = True)
	config.crash.lastfulljobtrashtime = ConfigInteger(default=-1)

	debugpath = [('/home/root/logs/', '/home/root/')]
	for p in harddiskmanager.getMountedPartitions():
		if os.path.exists(p.mountpoint):
			d = os.path.normpath(p.mountpoint)
			if p.mountpoint != '/':
				debugpath.append((p.mountpoint + 'logs/', d))
	config.crash.debug_path = ConfigSelection(default = "/home/root/logs/", choices = debugpath)
	if not os.path.exists("/home"):
		os.mkdir("/home",0755)
	if not os.path.exists("/home/root"):
		os.mkdir("/home/root",0755)

	def updatedebug_path(configElement):
		if not os.path.exists(config.crash.debug_path.value):
			try:
				os.mkdir(config.crash.debug_path.value,0755)
			except:
				print "Failed to create log path: %s" %config.crash.debug_path.value
	config.crash.debug_path.addNotifier(updatedebug_path, immediate_feedback = False)

	crashlogheader = _("We are really sorry. Your receiver encountered " \
					 "a software problem, and needs to be restarted.\n" \
					 "Please send the logfile %senigma2_crash_xxxxxx.log to www.opena.tv.\n" \
					 "Your receiver restarts in 10 seconds!\n" \
					 "Component: enigma2") % config.crash.debug_path.value
	config.crash.debug_text = ConfigText(default=crashlogheader, fixed_size=False)
	config.crash.skin_error_crash = ConfigYesNo(default = True)

	def updateStackTracePrinter(configElement):
		from Components.StackTrace import StackTracePrinter
		if configElement.value:
			if (os.path.isfile("/tmp/doPythonStackTrace")):
				os.remove("/tmp/doPythonStackTrace")
			from threading import current_thread
			StackTracePrinter.getInstance().activate(current_thread().ident)
		else:
			StackTracePrinter.getInstance().deactivate()

	config.crash.pystackonspinner = ConfigYesNo(default = True)
	config.crash.pystackonspinner.addNotifier(updateStackTracePrinter, immediate_feedback = False, call_on_save_or_cancel = True, initial_call = True)

	config.usage.timerlist_finished_timer_position = ConfigSelection(default = "end", choices = [("beginning", _("at beginning")), ("end", _("at end"))])
	config.usage.timerlist_show_epg = ConfigYesNo(default = True)

	def updateEnterForward(configElement):
		if not configElement.value:
			configElement.value = [2]
		updateChoices(config.seek.enter_forward, configElement.value)

	config.seek.speeds_forward.addNotifier(updateEnterForward, immediate_feedback = False)

	def updateEnterBackward(configElement):
		if not configElement.value:
			configElement.value = [2]
		updateChoices(config.seek.enter_backward, configElement.value)

	config.seek.speeds_backward.addNotifier(updateEnterBackward, immediate_feedback = False)

	def updateEraseSpeed(el):
		eBackgroundFileEraser.getInstance().setEraseSpeed(int(el.value))
	def updateEraseFlags(el):
		eBackgroundFileEraser.getInstance().setEraseFlags(int(el.value))
	config.misc.erase_speed = ConfigSelection(default="20", choices = [
		("10", _("10 MB/s")),
		("20", _("20 MB/s")),
		("50", _("50 MB/s")),
		("100", _("100 MB/s"))])
	config.misc.erase_speed.addNotifier(updateEraseSpeed, immediate_feedback = False)
	config.misc.erase_flags = ConfigSelection(default="1", choices = [
		("0", _("Disable")),
		("1", _("Internal hdd only")),
		("3", _("Everywhere"))])
	config.misc.erase_flags.addNotifier(updateEraseFlags, immediate_feedback = False)
	
	if SystemInfo["ZapMode"]:
		def setZapmode(el):
			open(SystemInfo["ZapMode"], "w").write(el.value)
		config.misc.zapmode = ConfigSelection(default = "mute", choices = [
			("mute", _("Black screen")), ("hold", _("Hold screen")), ("mutetilllock", _("Black screen till locked")), ("holdtilllock", _("Hold till locked"))])
		config.misc.zapmode.addNotifier(setZapmode, immediate_feedback = False)

	config.usage.historymode = ConfigSelection(default = "1", choices = [("0", _("Just zap")), ("1", _("Show menu"))])

	config.subtitles = ConfigSubsection()
	config.subtitles.ttx_subtitle_colors = ConfigSelection(default = "1", choices = [
		("0", _("original")),
		("1", _("white")),
		("2", _("yellow")) ])
	config.subtitles.ttx_subtitle_original_position = ConfigYesNo(default = False)
	config.subtitles.subtitle_position = ConfigSelection( choices = ["0", "10", "20", "30", "40", "50", "60", "70", "80", "90", "100", "150", "200", "250", "300", "350", "400", "450"], default = "50")
	config.subtitles.subtitle_alignment = ConfigSelection(choices = [("left", _("left")), ("center", _("center")), ("right", _("right"))], default = "center")
	config.subtitles.subtitle_rewrap = ConfigYesNo(default = False)
	config.subtitles.colourise_dialogs = ConfigYesNo(default = False)
	config.subtitles.subtitle_borderwidth = ConfigSelection(choices = ["1", "2", "3", "4", "5"], default = "3")
	config.subtitles.subtitle_fontsize  = ConfigSelection(choices = ["%d" % x for x in range(16,101) if not x % 2], default = "40")
	backtrans = [
		("0", _("No transparency")),
		("12", "5%"),
		("25", "10%"),
		("38", "15%"),
		("50", "20%"),
		("75", "30%"),
		("100", "40%"),
		("125", "50%"),
		("150", "60%"),
		("175", "70%"),
		("200", "80%"),
		("225", "90%"),
		("255", _("Full transparency"))]
	config.subtitles.subtitles_backtrans = ConfigSelection(default = "255", choices = backtrans)
	config.subtitles.dvb_subtitles_backtrans = ConfigSelection(default = "0", choices = backtrans)

	subtitle_delay_choicelist = []
	for i in range(-54000000, 54045000, 45000):
		if i == 0:
			subtitle_delay_choicelist.append(("0", _("No delay")))
		else:
			subtitle_delay_choicelist.append(("%d" % i, _("%2.1f sec") % (i / 90000.)))
	config.subtitles.subtitle_noPTSrecordingdelay = ConfigSelection(default = "315000", choices = subtitle_delay_choicelist)

	config.subtitles.dvb_subtitles_yellow = ConfigYesNo(default = False)
	config.subtitles.dvb_subtitles_original_position = ConfigSelection(default = "0", choices = [("0", _("Original")), ("1", _("Fixed")), ("2", _("Relative"))])
	config.subtitles.dvb_subtitles_centered = ConfigYesNo(default = False)
	config.subtitles.subtitle_bad_timing_delay = ConfigSelection(default = "0", choices = subtitle_delay_choicelist)
	config.subtitles.pango_subtitle_colors = ConfigSelection(default = "1", choices = [
		("0", _("alternative")),
		("1", _("white")),
		("2", _("yellow")) ])
	config.subtitles.pango_subtitle_fontswitch = ConfigYesNo(default = True)
	config.subtitles.pango_subtitles_delay = ConfigSelection(default = "0", choices = subtitle_delay_choicelist)
	config.subtitles.pango_subtitles_fps = ConfigSelection(default = "1", choices = [
		("1", _("Original")),
		("23976", _("23.976")),
		("24000", _("24")),
		("25000", _("25")),
		("29970", _("29.97")),
		("30000", _("30"))])
	config.subtitles.pango_subtitle_removehi = ConfigYesNo(default = False)
	config.subtitles.pango_autoturnon = ConfigYesNo(default = True)

	config.autolanguage = ConfigSubsection()
	audio_language_choices=[
		("---", _("None")),
		("und", _("Undetermined")),
		("orj dos ory org esl qaa und mis mul ORY ORJ Audio_ORJ", _("Original")),
		("ara", _("Arabic")),
		("eus baq", _("Basque")),
		("bul", _("Bulgarian")),
		("hrv", _("Croatian")),
		("chn sgp", _("Simplified Chinese")),
		("twn hkn",_("Traditional Chinese")),
		("ces cze", _("Czech")),
		("dan", _("Danish")),
		("dut ndl nld Dutch", _("Dutch")),
		("eng qaa Englisch", _("English")),
		("est", _("Estonian")),
		("fin", _("Finnish")),
		("fra fre", _("French")),
		("deu ger", _("German")),
		("ell gre", _("Greek")),
		("heb", _("Hebrew")),
		("hun", _("Hungarian")),
		("ind", _("Indonesian")),
		("ita", _("Italian")),
		("lav", _("Latvian")),
		("lit", _("Lithuanian")),
		("ltz", _("Luxembourgish")),
		("nor", _("Norwegian")),
		("pol", _("Polish")),
		("por", _("Portuguese")),
		("fas per", _("Persian")),
		("ron rum", _("Romanian")),
		("rus", _("Russian")),
		("srp", _("Serbian")),
		("slk slo", _("Slovak")),
		("slv", _("Slovenian")),
		("spa", _("Spanish")),
		("swe", _("Swedish")),
		("tha", _("Thai")),
		("tur Audio_TUR", _("Turkish")),
		("ukr Ukr", _("Ukrainian"))]

	def setEpgLanguage(configElement):
		eServiceEvent.setEPGLanguage(configElement.value)
	config.autolanguage.audio_epglanguage = ConfigSelection(audio_language_choices[:1] + audio_language_choices [2:], default="---")
	config.autolanguage.audio_epglanguage.addNotifier(setEpgLanguage)

	def setEpgLanguageAlternative(configElement):
		eServiceEvent.setEPGLanguageAlternative(configElement.value)
	config.autolanguage.audio_epglanguage_alternative = ConfigSelection(audio_language_choices[:1] + audio_language_choices [2:], default="---")
	config.autolanguage.audio_epglanguage_alternative.addNotifier(setEpgLanguageAlternative)

	config.autolanguage.audio_autoselect1 = ConfigSelection(choices=audio_language_choices, default="---")
	config.autolanguage.audio_autoselect2 = ConfigSelection(choices=audio_language_choices, default="---")
	config.autolanguage.audio_autoselect3 = ConfigSelection(choices=audio_language_choices, default="---")
	config.autolanguage.audio_autoselect4 = ConfigSelection(choices=audio_language_choices, default="---")
	config.autolanguage.audio_defaultac3 = ConfigYesNo(default = False)
	config.autolanguage.audio_defaultddp = ConfigYesNo(default = False)
	config.autolanguage.audio_usecache = ConfigYesNo(default = True)

	subtitle_language_choices = audio_language_choices[:1] + audio_language_choices [2:]
	config.autolanguage.subtitle_autoselect1 = ConfigSelection(choices=subtitle_language_choices, default="---")
	config.autolanguage.subtitle_autoselect2 = ConfigSelection(choices=subtitle_language_choices, default="---")
	config.autolanguage.subtitle_autoselect3 = ConfigSelection(choices=subtitle_language_choices, default="---")
	config.autolanguage.subtitle_autoselect4 = ConfigSelection(choices=subtitle_language_choices, default="---")
	config.autolanguage.subtitle_hearingimpaired = ConfigYesNo(default = False)
	config.autolanguage.subtitle_defaultimpaired = ConfigYesNo(default = False)
	config.autolanguage.subtitle_defaultdvb = ConfigYesNo(default = False)
	config.autolanguage.subtitle_usecache = ConfigYesNo(default = True)
	config.autolanguage.equal_languages = ConfigSelection(default = "15", choices = [
		("0", _("None")),("1", "1"),("2", "2"),("3", "1,2"),
		("4", "3"),("5", "1,3"),("6", "2,3"),("7", "1,2,3"),
		("8", "4"),("9", "1,4"),("10", "2,4"),("11", "1,2,4"),
		("12", "3,4"),("13", "1,3,4"),("14", "2,3,4"),("15", _("All"))])

	config.logmanager = ConfigSubsection()
	config.logmanager.showinextensions = ConfigYesNo(default = False)
	config.logmanager.user = ConfigText(default='', fixed_size=False)
	config.logmanager.useremail = ConfigText(default='', fixed_size=False)
	config.logmanager.usersendcopy = ConfigYesNo(default = True)
	config.logmanager.path = ConfigText(default = "/")
	config.logmanager.additionalinfo = NoSave(ConfigText(default = ""))
	config.logmanager.sentfiles = ConfigLocations(default='')

	config.plisettings = ConfigSubsection()
	#config.plisettings.Subservice = ConfigYesNo(default = True)
	config.plisettings.Subservice = ConfigSelection(default="3", choices = [
					("0", _("No, show always the timer list")),
					("1", _("No, show always the plugin browser")),
					("2", _("Yes, but if not available show the timer list")),
					("3", _("Yes, but if not available show the plugin browser"))])
	config.plisettings.ColouredButtons = ConfigYesNo(default = False)
	config.plisettings.InfoBarEpg_mode = ConfigSelection(default="3", choices = [
					("0", _("as plugin in extended bar")),
					("1", _("with long OK press")),
					("2", _("with exit button")),
					("3", _("with left/right buttons"))])
	if fileExists("/usr/lib/enigma2/python/Plugins/Extensions/CoolTVGuide/plugin.pyo"):
		config.plisettings.PLIEPG_mode = ConfigSelection(default="cooltvguide", choices = [
					("pliepg", _("Show Graphical EPG")),
					("single", _("Show Single EPG")),
					("multi", _("Show Multi EPG")),
					("vertical", _("Show Vertical EPG")),
					("eventview", _("Show Eventview")),
#					("merlinepgcenter", _("Show Merlin EPG Center")),
					("cooltvguide", _("Show CoolTVGuide"))])
		config.plisettings.PLIINFO_mode = ConfigSelection(default="coolinfoguide", choices = [
					("eventview", _("Show Eventview")),
					("epgpress", _("Show EPG")),
					("single", _("Show Single EPG")),
					("coolsingleguide", _("Show CoolSingleGuide")),
					("coolinfoguide", _("Show CoolInfoGuide")),
					("cooltvguide", _("Show CoolTVGuide"))])
	else:
		config.plisettings.PLIEPG_mode = ConfigSelection(default="pliepg", choices = [
					("pliepg", _("Show Graphical EPG")),
					("single", _("Show Single EPG")),
					("multi", _("Show Multi EPG")),
					("vertical", _("Show Vertical EPG")),
					("eventview", _("Show Eventview")),
					("merlinepgcenter", _("Show Merlin EPG Center"))])
		config.plisettings.PLIINFO_mode = ConfigSelection(default="eventview", choices = [
					("eventview", _("Show Eventview")),
					("epgpress", _("Show EPG")),
					("single", _("Show Single EPG"))])

	config.epgselection = ConfigSubsection()
	config.epgselection.sort = ConfigSelection(default="0", choices = [("0", _("Time")),("1", _("Alphanumeric"))])
	config.epgselection.overjump = ConfigYesNo(default = False)
	config.epgselection.infobar_type_mode = ConfigSelection(choices = [("text", _("Text")), ("graphics",_("Multi EPG")), ("single", _("Single EPG"))], default = "text")
	if SystemInfo.get("NumVideoDecoders", 1) > 1:
		config.epgselection.infobar_preview_mode = ConfigSelection(choices = [("0",_("Disabled")), ("1", _("Fullscreen")), ("2", _("PiP"))], default = "1")
	else:
		config.epgselection.infobar_preview_mode = ConfigSelection(choices = [("0",_("Disabled")), ("1", _("Fullscreen"))], default = "1")
	config.epgselection.infobar_ok = ConfigSelection(choices = [("Zap",_("Zap")), ("Zap + Exit", _("Zap + Exit"))], default = "Zap")
	config.epgselection.infobar_oklong = ConfigSelection(choices = [("Zap",_("Zap")), ("Zap + Exit", _("Zap + Exit"))], default = "Zap + Exit")
	config.epgselection.infobar_itemsperpage = ConfigSelectionNumber(default = 2, stepwidth = 1, min = 1, max = 4, wraparound = True)
	config.epgselection.infobar_roundto = ConfigSelection(default = "15", choices = [("15", _("%d minutes") % 15), ("30", _("%d minutes") % 30), ("60", _("%d minutes") % 60)])
	config.epgselection.infobar_prevtime = ConfigClock(default = time())
	config.epgselection.infobar_prevtimeperiod = ConfigSelection(default = "180", choices = [("60", _("%d minutes") % 60), ("90", _("%d minutes") % 90), ("120", _("%d minutes") % 120), ("150", _("%d minutes") % 150), ("180", _("%d minutes") % 180), ("210", _("%d minutes") % 210), ("240", _("%d minutes") % 240), ("270", _("%d minutes") % 270), ("300", _("%d minutes") % 300)])
	config.epgselection.infobar_primetimehour = ConfigSelectionNumber(default = 20, stepwidth = 1, min = 00, max = 23, wraparound = True)
	config.epgselection.infobar_primetimemins = ConfigSelectionNumber(default = 00, stepwidth = 1, min = 00, max = 59, wraparound = True)
	#config.epgselection.infobar_servicetitle_mode = ConfigSelection(default = "servicename", choices = [("servicename", _("Service Name")),("picon", _("Picon")),("picon+servicename", _("Picon and Service Name")) ])
	config.epgselection.infobar_servicetitle_mode = ConfigSelection(default = "picon+servicename", choices = [("servicename", _("Service Name")),("picon", _("Picon")),("servicenumber+picon+servicename", _("Service Number, Picon and Service Name")),("servicenumber+servicename", _("Service Number and Service Name")),("picon+servicename", _("Picon and Service Name")) ])
	config.epgselection.infobar_servfs = ConfigSelectionNumber(default = 0, stepwidth = 1, min = -8, max = 10, wraparound = True)
	config.epgselection.infobar_eventfs = ConfigSelectionNumber(default = 0, stepwidth = 1, min = -8, max = 10, wraparound = True)
	config.epgselection.infobar_timelinefs = ConfigSelectionNumber(default = 0, stepwidth = 1, min = -8, max = 10, wraparound = True)
	config.epgselection.infobar_timeline24h = ConfigYesNo(default = True)
	config.epgselection.infobar_servicewidth = ConfigSelectionNumber(default = 250, stepwidth = 1, min = 70, max = 500, wraparound = True)
	config.epgselection.infobar_piconwidth = ConfigSelectionNumber(default = 100, stepwidth = 1, min = 50, max = 500, wraparound = True)
	config.epgselection.infobar_infowidth = ConfigSelectionNumber(default = 25, stepwidth = 25, min = 0, max = 150, wraparound = True)
	config.epgselection.enhanced_preview_mode = ConfigYesNo(default = True)
	config.epgselection.enhanced_ok = ConfigSelection(choices = [("Zap",_("Zap")), ("Zap + Exit", _("Zap + Exit"))], default = "Zap")
	config.epgselection.enhanced_oklong = ConfigSelection(choices = [("Zap",_("Zap")), ("Zap + Exit", _("Zap + Exit"))], default = "Zap + Exit")
	config.epgselection.enhanced_eventfs = ConfigSelectionNumber(default = 0, stepwidth = 1, min = -8, max = 10, wraparound = True)
	config.epgselection.enhanced_itemsperpage = ConfigSelectionNumber(default = 16, stepwidth = 1, min = 8, max = 40, wraparound = True)
	config.epgselection.multi_showbouquet = ConfigYesNo(default = False)
	config.epgselection.multi_preview_mode = ConfigYesNo(default = True)
	config.epgselection.multi_ok = ConfigSelection(choices = [("Zap",_("Zap")), ("Zap + Exit", _("Zap + Exit"))], default = "Zap")
	config.epgselection.multi_oklong = ConfigSelection(choices = [("Zap",_("Zap")), ("Zap + Exit", _("Zap + Exit"))], default = "Zap + Exit")
	config.epgselection.multi_eventfs = ConfigSelectionNumber(default = 0, stepwidth = 1, min = -8, max = 10, wraparound = True)
	config.epgselection.multi_itemsperpage = ConfigSelectionNumber(default = 16, stepwidth = 1, min = 8, max = 40, wraparound = True)
	config.epgselection.graph_showbouquet = ConfigYesNo(default = False)
	config.epgselection.graph_preview_mode = ConfigYesNo(default = True)
	config.epgselection.graph_type_mode = ConfigSelection(choices = [("graphics",_("Graphics")), ("text", _("Text"))], default = "text")
	config.epgselection.graph_ok = ConfigSelection(choices = [("Zap",_("Zap")), ("Zap + Exit", _("Zap + Exit"))], default = "Zap")
	config.epgselection.graph_oklong = ConfigSelection(choices = [("Zap",_("Zap")), ("Zap + Exit", _("Zap + Exit"))], default = "Zap + Exit")
	config.epgselection.graph_info = ConfigSelection(choices = [("Channel Info", _("Channel Info")), ("Single EPG", _("Single EPG"))], default = "Channel Info")
	config.epgselection.graph_infolong = ConfigSelection(choices = [("Channel Info", _("Channel Info")), ("Single EPG", _("Single EPG"))], default = "Single EPG")
	config.epgselection.graph_roundto = ConfigSelection(default = "15", choices = [("15", _("%d minutes") % 15), ("30", _("%d minutes") % 30), ("60", _("%d minutes") % 60)])
	config.epgselection.graph_prevtime = ConfigClock(default = time())
	config.epgselection.graph_prevtimeperiod = ConfigSelection(default = "180", choices = [("60", _("%d minutes") % 60), ("90", _("%d minutes") % 90), ("120", _("%d minutes") % 120), ("150", _("%d minutes") % 150), ("180", _("%d minutes") % 180), ("210", _("%d minutes") % 210), ("240", _("%d minutes") % 240), ("270", _("%d minutes") % 270), ("300", _("%d minutes") % 300)])
	config.epgselection.graph_primetimehour = ConfigSelectionNumber(default = 20, stepwidth = 1, min = 00, max = 23, wraparound = True)
	config.epgselection.graph_primetimemins = ConfigSelectionNumber(default = 00, stepwidth = 1, min = 00, max = 59, wraparound = True)
	config.epgselection.graph_servicetitle_mode = ConfigSelection(default = "picon+servicename", choices = [("servicename", _("Service Name")),("picon", _("Picon")),("servicenumber+picon+servicename", _("Service Number, Picon and Service Name")),("servicenumber+servicename", _("Service Number and Service Name")),("picon+servicename", _("Picon and Service Name")) ])
	config.epgselection.graph_startmode = ConfigSelection(default = "standard", choices = [("standard", _("Standard")), ("primetime", _("Primetime")),("channel1", _("Channel 1")), ("channel1+primetime", _("Channel 1 with Primetime")) ])
	config.epgselection.graph_servfs = ConfigSelectionNumber(default = 0, stepwidth = 1, min = -8, max = 10, wraparound = True)
	config.epgselection.graph_eventfs = ConfigSelectionNumber(default = 0, stepwidth = 1, min = -8, max = 10, wraparound = True)
	possibleAlignmentChoices = [
		( str(RT_HALIGN_LEFT   | RT_VALIGN_CENTER          ) , _("left")),
		( str(RT_HALIGN_CENTER | RT_VALIGN_CENTER          ) , _("centered")),
		( str(RT_HALIGN_RIGHT  | RT_VALIGN_CENTER          ) , _("right")),
		( str(RT_HALIGN_LEFT   | RT_VALIGN_CENTER | RT_WRAP) , _("left, wrapped")),
		( str(RT_HALIGN_CENTER | RT_VALIGN_CENTER | RT_WRAP) , _("centered, wrapped")),
		( str(RT_HALIGN_RIGHT | RT_VALIGN_CENTER | RT_WRAP) , _("right, wrapped"))]
	config.epgselection.graph_event_alignment = ConfigSelection(default = possibleAlignmentChoices[0][0], choices = possibleAlignmentChoices)
	config.epgselection.graph_servicename_alignment = ConfigSelection(default = possibleAlignmentChoices[0][0], choices = possibleAlignmentChoices)
	config.epgselection.graph_timelinefs = ConfigSelectionNumber(default = 0, stepwidth = 1, min = -8, max = 10, wraparound = True)
	config.epgselection.graph_timeline24h = ConfigYesNo(default = True)
	config.epgselection.graph_itemsperpage = ConfigSelectionNumber(default = 8, stepwidth = 1, min = 3, max = 20, wraparound = True)
	config.epgselection.graph_pig = ConfigYesNo(default = False)
	config.epgselection.graph_heightswitch = NoSave(ConfigYesNo(default = False))
	config.epgselection.graph_servicewidth = ConfigSelectionNumber(default = 250, stepwidth = 1, min = 70, max = 500, wraparound = True)
	config.epgselection.graph_piconwidth = ConfigSelectionNumber(default = 100, stepwidth = 1, min = 50, max = 500, wraparound = True)
	config.epgselection.graph_infowidth = ConfigSelectionNumber(default = 25, stepwidth = 25, min = 0, max = 150, wraparound = True)
	config.epgselection.graph_rec_icon_height = ConfigSelection(choices = [("bottom",_("bottom")),("top", _("top")), ("middle", _("middle")),  ("hide", _("hide"))], default = "bottom")

	epg_colorkeys = [('autotimer', _('Auto Timer')),
					('timer', _('Add/Remove Timer')),
					('24plus', _('24+ Hours')),
					('24minus', _('24- Hours')),
					('imdb', _('IMDB search')),
					('bouquetlist', _('Bouquet List')),
					('showmovies', _('Show Movies List')),
					('record', _('Record - same as record button')),
					('gotodatetime', _('Goto Date/Timer')),
					('epgsearch', _('EPG search'))]
	config.epgselection.graph_red = ConfigSelection(default='imdb', choices=epg_colorkeys)
	config.epgselection.graph_green = ConfigSelection(default='timer', choices=epg_colorkeys)
	config.epgselection.graph_yellow = ConfigSelection(default='epgsearch',choices=epg_colorkeys)
	config.epgselection.graph_blue = ConfigSelection(default='autotimer', choices=epg_colorkeys)

	config.epgselection.vertical_itemsperpage = ConfigSelectionNumber(default = 6, stepwidth = 1, min = 3, max = 12, wraparound = True)
	config.epgselection.vertical_eventfs = ConfigSelectionNumber(default = 0, stepwidth = 1, min = -10, max = 10, wraparound = True)
	config.epgselection.vertical_ok = ConfigSelection(choices = [("Channel Info", _("Channel Info")),("Zap",_("Zap")), ("Zap + Exit", _("Zap + Exit"))], default = "Channel Info")
	config.epgselection.vertical_oklong = ConfigSelection(choices = [("Channel Info", _("Channel Info")),("Zap",_("Zap")), ("Zap + Exit", _("Zap + Exit"))], default = "Zap + Exit")
	config.epgselection.vertical_info = ConfigSelection(choices = [("Channel Info", _("Channel Info")), ("Single EPG", _("Single EPG"))], default = "Channel Info")
	config.epgselection.vertical_infolong = ConfigSelection(choices = [("Channel Info", _("Channel Info")), ("Single EPG", _("Single EPG"))], default = "Single EPG")
	config.epgselection.vertical_channelbtn = ConfigSelection(choices = [("page", _("previous/next Page")), ("scroll", _("all up/down")), ("24", _("-24h/+24 Hours"))], default = "page")
	config.epgselection.vertical_channelbtn_invert = ConfigYesNo(default = False)
	config.epgselection.vertical_updownbtn = ConfigYesNo(default = True)
	config.epgselection.vertical_primetimehour = ConfigSelectionNumber(default = 20, stepwidth = 1, min = 00, max = 23, wraparound = True)
	config.epgselection.vertical_primetimemins = ConfigSelectionNumber(default = 15, stepwidth = 1, min = 00, max = 59, wraparound = True)
	config.epgselection.vertical_preview_mode = ConfigYesNo(default = True)
	config.epgselection.vertical_pig = ConfigYesNo(default = False)
	config.epgselection.vertical_eventmarker = ConfigYesNo(default = False)
	config.epgselection.vertical_showlines = ConfigYesNo(default = True)
	config.epgselection.vertical_startmode = ConfigSelection(default = "standard", choices = [("standard", _("Standard")), ("primetime", _("Primetime")),("channel1", _("Channel 1")), ("channel1+primetime", _("Channel 1 with Primetime")) ])
	config.epgselection.vertical_prevtime = ConfigClock(default = time())
	vertical_colorkeys = [('autotimer', _('Auto Timer')),
					('timer', _('Add/Remove Timer')),
					('24plus', _('24+ Hours')),
					('24minus', _('24- Hours')),
					('imdb', _('IMDB search')),
					('bouquetlist', _('Bouquet List')),
					('showmovies', _('Show Movies List')),
					('record', _('Record - same as record button')),
					('gotodatetime', _('Goto Date/Timer')),
					('gotoprimetime', _('Goto Primetime')),
					('setbasetime', _('Set Basetime')),
					('epgsearch', _('EPG search'))]
	config.epgselection.vertical_red = ConfigSelection(default='imdb', choices=vertical_colorkeys)
	config.epgselection.vertical_green = ConfigSelection(default='timer', choices=vertical_colorkeys)
	config.epgselection.vertical_yellow = ConfigSelection(default='epgsearch',choices=vertical_colorkeys)
	config.epgselection.vertical_blue = ConfigSelection(default='autotimer', choices=vertical_colorkeys)

	config.oscaminfo = ConfigSubsection()
	config.oscaminfo.showInExtensions = ConfigYesNo(default=False)
	config.oscaminfo.userdatafromconf = ConfigYesNo(default = True)
	config.oscaminfo.autoupdate = ConfigYesNo(default = False)
	config.oscaminfo.username = ConfigText(default = "username", fixed_size = False, visible_width=12)
	config.oscaminfo.password = ConfigPassword(default = "password", fixed_size = False)
	config.oscaminfo.ip = ConfigIP( default = [ 127,0,0,1 ], auto_jump=True)
	config.oscaminfo.port = ConfigInteger(default = 16002, limits=(0,65536) )
	config.oscaminfo.intervall = ConfigSelectionNumber(min = 1, max = 600, stepwidth = 1, default = 10, wraparound = True)
	SystemInfo["OScamInstalled"] = False

	config.cccaminfo = ConfigSubsection()
	config.cccaminfo.showInExtensions = ConfigYesNo(default=False)
	config.cccaminfo.serverNameLength = ConfigSelectionNumber(min = 10, max = 100, stepwidth = 1, default = 22, wraparound = True)
	config.cccaminfo.name = ConfigText(default="Profile", fixed_size=False)
	config.cccaminfo.ip = ConfigText(default="192.168.2.12", fixed_size=False)
	config.cccaminfo.username = ConfigText(default="", fixed_size=False)
	config.cccaminfo.password = ConfigText(default="", fixed_size=False)
	config.cccaminfo.port = ConfigInteger(default=16001, limits=(1, 65535))
	config.cccaminfo.profile = ConfigText(default="", fixed_size=False)
	config.cccaminfo.ecmInfoEnabled = ConfigYesNo(default=True)
	config.cccaminfo.ecmInfoTime = ConfigSelectionNumber(min = 1, max = 10, stepwidth = 1, default = 5, wraparound = True)
	config.cccaminfo.ecmInfoForceHide = ConfigYesNo(default=True)
	config.cccaminfo.ecmInfoPositionX = ConfigInteger(default=50)
	config.cccaminfo.ecmInfoPositionY = ConfigInteger(default=50)
	config.cccaminfo.blacklist = ConfigText(default="/media/cf/CCcamInfo.blacklisted", fixed_size=False)
	config.cccaminfo.profiles = ConfigText(default="/media/cf/CCcamInfo.profiles", fixed_size=False)

	config.streaming = ConfigSubsection()
	config.streaming.stream_ecm = ConfigYesNo(default = False)
	config.streaming.descramble = ConfigYesNo(default = True)
	config.streaming.descramble_client = ConfigYesNo(default = False)
	config.streaming.stream_eit = ConfigYesNo(default = True)
	config.streaming.stream_ait = ConfigYesNo(default = True)
	config.streaming.authentication = ConfigYesNo(default = False)

	config.pluginbrowser = ConfigSubsection()
	config.pluginbrowser.po = ConfigYesNo(default = False)
	config.pluginbrowser.src = ConfigYesNo(default = False)

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
		if not val in choices:
			tmp = choices[:]
			tmp.reverse()
			for x in tmp:
				if x < val:
					defval = str(x)
					break
		sel.setChoices(map(str, choices), defval)

def preferredPath(path):
	if config.usage.setup_level.index < 2 or path == "<default>":
		return None  # config.usage.default_path.value, but delay lookup until usage
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

def defaultMoviePath():
	return defaultRecordingLocation(config.usage.default_path.value)

def refreshServiceList(configElement = None):
	from Screens.InfoBar import InfoBar
	InfoBarInstance = InfoBar.instance
	if InfoBarInstance is not None:
		servicelist = InfoBarInstance.servicelist
		if servicelist:
			servicelist.setMode()

def patchTuxtxtConfFile(dummyConfigElement):
	print "[tuxtxt] patching tuxtxt2.conf"
	if config.usage.tuxtxt_font_and_res.value == "X11_SD":
		tuxtxt2 = [["UseTTF",0],
		           ["TTFBold",1],
		           ["TTFScreenResX",720],
		           ["StartX",50],
		           ["EndX",670],
		           ["StartY",30],
		           ["EndY",555],
		           ["TTFShiftY",0],
		           ["TTFShiftX",0],
		           ["TTFWidthFactor16",26],
		           ["TTFHeightFactor16",14]]
	elif config.usage.tuxtxt_font_and_res.value == "TTF_SD":
		tuxtxt2 = [["UseTTF",1],
		           ["TTFBold",1],
		           ["TTFScreenResX",720],
		           ["StartX",50],
		           ["EndX",670],
		           ["StartY",30],
		           ["EndY",555],
		           ["TTFShiftY",2],
		           ["TTFShiftX",0],
		           ["TTFWidthFactor16",29],
		           ["TTFHeightFactor16",14]]
	elif config.usage.tuxtxt_font_and_res.value == "TTF_HD":
		tuxtxt2 = [["UseTTF",1],
		           ["TTFBold",0],
		           ["TTFScreenResX",1280],
		           ["StartX",80],
		           ["EndX",1200],
		           ["StartY",35],
		           ["EndY",685],
		           ["TTFShiftY",-3],
		           ["TTFShiftX",0],
		           ["TTFWidthFactor16",26],
		           ["TTFHeightFactor16",14]]
	elif config.usage.tuxtxt_font_and_res.value == "TTF_FHD":
		tuxtxt2 = [["UseTTF",1],
		           ["TTFBold",0],
		           ["TTFScreenResX",1920],
		           ["StartX",140],
		           ["EndX",1780],
		           ["StartY",52],
		           ["EndY",1027],
		           ["TTFShiftY",-6],
		           ["TTFShiftX",0],
		           ["TTFWidthFactor16",26],
		           ["TTFHeightFactor16",14]]
	elif config.usage.tuxtxt_font_and_res.value == "expert_mode":
		tuxtxt2 = [["UseTTF",            int(config.usage.tuxtxt_UseTTF.value)],
		           ["TTFBold",           int(config.usage.tuxtxt_TTFBold.value)],
		           ["TTFScreenResX",     int(config.usage.tuxtxt_TTFScreenResX.value)],
		           ["StartX",            config.usage.tuxtxt_StartX.value],
		           ["EndX",              config.usage.tuxtxt_EndX.value],
		           ["StartY",            config.usage.tuxtxt_StartY.value],
		           ["EndY",              config.usage.tuxtxt_EndY.value],
		           ["TTFShiftY",         int(config.usage.tuxtxt_TTFShiftY.value)],
		           ["TTFShiftX",         int(config.usage.tuxtxt_TTFShiftX.value)],
		           ["TTFWidthFactor16",  config.usage.tuxtxt_TTFWidthFactor16.value],
		           ["TTFHeightFactor16", config.usage.tuxtxt_TTFHeightFactor16.value]]
	tuxtxt2.append(    ["CleanAlgo",         config.usage.tuxtxt_CleanAlgo.value] )

	TUXTXT_CFG_FILE = "/etc/tuxtxt/tuxtxt2.conf"
	command = "sed -i -r '"
	for f in tuxtxt2:
		#replace keyword (%s) followed by any value ([-0-9]+) by that keyword \1 and the new value %d
		command += "s|(%s)\s+([-0-9]+)|\\1 %d|;" % (f[0],f[1])
	command += "' %s" % TUXTXT_CFG_FILE
	for f in tuxtxt2:
		#if keyword is not found in file, append keyword and value
		command += " ; if ! grep -q '%s' %s ; then echo '%s %d' >> %s ; fi"  % (f[0],TUXTXT_CFG_FILE,f[0],f[1],TUXTXT_CFG_FILE)
	try:
		os.system(command)
	except:
		print "Error: failed to patch %s!" % TUXTXT_CFG_FILE
	print "[tuxtxt] patched tuxtxt2.conf"

	config.usage.tuxtxt_ConfFileHasBeenPatched.setValue(True)
