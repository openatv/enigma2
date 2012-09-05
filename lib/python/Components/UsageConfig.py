from Components.Harddisk import harddiskmanager
from config import config, ConfigSubsection, ConfigYesNo, ConfigSelection, ConfigText, ConfigNumber, ConfigSet, ConfigLocations, NoSave, ConfigClock, ConfigInteger, ConfigBoolean, ConfigPassword, ConfigIP, ConfigSlider, ConfigSelectionNumber
from Tools.Directories import resolveFilename, SCOPE_HDD, SCOPE_TIMESHIFT, SCOPE_SYSETC
from enigma import setTunerTypePriorityOrder, setPreferredTuner, setSpinnerOnOff, setEnableTtCachingOnOff, Misc_Options, eEnv
from Components.NimManager import nimmanager
from SystemInfo import SystemInfo
import os
import enigma
from time import time

def InitUsageConfig():
	try:
		file = open(resolveFilename(SCOPE_SYSETC, 'image-version'), 'r')
		lines = file.readlines()
		file.close()
		for x in lines:
			splitted = x.split('=')
			if splitted[0] == "box_type":
				folderprefix = splitted[1].replace('\n','') # 0 = release, 1 = experimental
				boxtype = splitted[1].replace('\n','') # 0 = release, 1 = experimental
	except:
		folderprefix=""
		boxtype="not detected"

	config.misc.boxtype = ConfigText(default = boxtype)
	config.misc.useNTPminutes = ConfigSelection(default = "30", choices = [("30", "30" + " " +_("minutes")), ("60", _("Hour")), ("1440", _("Once per day"))])
	config.misc.remotecontrol_text_support = ConfigYesNo(default = False)

	config.usage = ConfigSubsection();
	config.usage.showdish = ConfigSelection(default = "flashing", choices = [("flashing", _("Flashing")), ("normal", _("Not Flashing")), ("off", _("Off"))])
	config.usage.multibouquet = ConfigYesNo(default = True)
	config.usage.panicbutton = ConfigYesNo(default = True)
	config.usage.multiepg_ask_bouquet = ConfigYesNo(default = False)

	config.usage.quickzap_bouquet_change = ConfigYesNo(default = False)
	config.usage.e1like_radio_mode = ConfigYesNo(default = True)

	config.usage.infobar_onlinecheck = ConfigYesNo(default = True)
	config.usage.infobar_onlinechecktimer = ConfigInteger(default=6, limits=(1, 48))
	config.usage.infobar_onlineupdatelastcheck = ConfigInteger(default=0)
	config.usage.infobar_onlineupdatefound = NoSave(ConfigBoolean(default = False))
	config.usage.infobar_onlineupdatebeta = ConfigYesNo(default = False)
	config.usage.infobar_onlineupdateisunstable = ConfigInteger(default=0)

	choicelist = []
	for i in range(1, 12):
		choicelist.append(("%d" % i, ngettext("%d second", "%d seconds", i) % i))
	config.usage.infobar_timeout = ConfigSelection(default = "5", choices = [("0", _("no timeout"))] + choicelist)
	config.usage.show_infobar_on_zap = ConfigYesNo(default = True)
	config.usage.show_infobar_on_skip = ConfigYesNo(default = True)
	config.usage.show_infobar_on_event_change = ConfigYesNo(default = False)
	config.usage.show_second_infobar = ConfigYesNo(default = True)
	config.usage.second_infobar_timeout = ConfigSelection(default = "5", choices = [("0", _("no timeout"))] + choicelist)
	config.usage.show_picon_bkgrn = ConfigSelection(default = "transparent", choices = [("transparent", _("Transparent")), ("blue", _("Blue")), ("red", _("Red")), ("black", _("Black")), ("white", _("White")), ("lightgrey", _("Light Grey")), ("grey", _("Grey"))])

	config.usage.show_spinner = ConfigYesNo(default = True)
	config.usage.enable_tt_caching = ConfigYesNo(default = True)
	config.usage.sort_settings = ConfigYesNo(default = False)
	config.usage.sort_menus = ConfigYesNo(default = False)
	config.usage.sort_pluginlist = ConfigYesNo(default = True)
	config.usage.movieplayer_pvrstate = ConfigYesNo(default = True)

	choicelist = []
	for i in (10, 30):
		choicelist.append(("%d" % i, ngettext("%d second", "%d seconds", i) % i))
	for i in (60, 120, 300, 600, 1200, 1800):
		m = i / 60
		choicelist.append(("%d" % i, ngettext("%d minute", "%d minutes", m) % m))
	for i in (3600, 7200, 14400):
		h = i / 3600
		choicelist.append(("%d" % i, ngettext("%d hour", "%d hours", h) % h))
	config.usage.hdd_standby = ConfigSelection(default = "300", choices = [("0", _("no standby"))] + choicelist)
	config.usage.output_12V = ConfigSelection(default = "do not change", choices = [
		("do not change", _("do not change")), ("off", _("off")), ("on", _("on")) ])

	config.usage.pip_zero_button = ConfigSelection(default = "standard", choices = [
		("standard", _("standard")), ("swap", _("swap PiP and main picture")),
		("swapstop", _("move PiP to main picture")), ("stop", _("stop PiP")) ])

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
		if not config.usage.default_path.value.endswith('/'):
			tmpvalue = config.usage.default_path.value
			config.usage.default_path.setValue(tmpvalue + '/')
			config.usage.default_path.save()
	config.usage.default_path.addNotifier(defaultpathChanged, immediate_feedback = False)

	config.usage.timer_path = ConfigText(default = "<default>")
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

	config.usage.movielist_trashcan = ConfigYesNo(default=True)
	config.usage.movielist_trashcan_days = ConfigNumber(default=8)
	config.usage.movielist_trashcan_reserve = ConfigNumber(default=40)
	config.usage.on_movie_start = ConfigSelection(default = "ask", choices = [
		("ask", _("Ask user")), ("resume", _("Resume from last position")), ("beginning", _("Start from the beginning")) ])
	config.usage.on_movie_stop = ConfigSelection(default = "movielist", choices = [
		("ask", _("Ask user")), ("movielist", _("Return to movie list")), ("quit", _("Return to previous service")) ])
	config.usage.on_movie_eof = ConfigSelection(default = "movielist", choices = [
		("ask", _("Ask user")), ("movielist", _("Return to movie list")), ("quit", _("Return to previous service")), ("pause", _("Pause movie at end")), ("playlist", _("Play next (return to movie list)")),
		("playlistquit", _("Play next (return to previous service)")), ("loop", _("Continues play (loop)"))])
	config.usage.next_movie_msg = ConfigYesNo(default = True)

	config.usage.setup_level = ConfigSelection(default = "expert", choices = [
		("simple", _("Simple")),
		("intermediate", _("Intermediate")),
		("expert", _("Expert")) ])

	config.usage.on_long_powerpress = ConfigSelection(default = "show_menu", choices = [
		("show_menu", _("show shutdown menu")),
		("shutdown", _("immediate shutdown")),
		("standby", _("Standby")) ] )

	config.usage.on_short_powerpress = ConfigSelection(default = "standby", choices = [
		("show_menu", _("show shutdown menu")),
		("shutdown", _("immediate shutdown")),
		("standby", _("Standby")) ] )


	config.usage.alternatives_priority = ConfigSelection(default = "0", choices = [
		("0", "DVB-S/-C/-T"),
		("1", "DVB-S/-T/-C"),
		("2", "DVB-C/-S/-T"),
		("3", "DVB-C/-T/-S"),
		("4", "DVB-T/-C/-S"),
		("5", "DVB-T/-S/-C") ])

	nims = [("-1", _("auto"))]
	for x in nimmanager.nim_slots:
		nims.append((str(x.slot), x.getSlotName()))
	config.usage.frontend_priority = ConfigSelection(default = "-1", choices = nims)
	config.misc.disable_background_scan = ConfigYesNo(default = False)

	config.usage.jobtaksextensions = ConfigYesNo(default = True)

	config.usage.servicenum_fontsize = ConfigSelectionNumber(default = 0, stepwidth = 1, min = -8, max = 10, wraparound = True)
	config.usage.servicename_fontsize = ConfigSelectionNumber(default = 0, stepwidth = 1, min = -8, max = 10, wraparound = True)
	config.usage.serviceinfo_fontsize = ConfigSelectionNumber(default = 0, stepwidth = 1, min = -8, max = 10, wraparound = True)
	config.usage.serviceitems_per_page = ConfigSelectionNumber(default = 16, stepwidth = 1, min = 3, max = 40, wraparound = True)
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
					("2", _("Bouquet List"))])
	config.usage.show_bouquetalways = ConfigYesNo(default = False)
	config.usage.show_event_progress_in_servicelist = ConfigSelection(default = 'barright', choices = [
		('barleft', _("Progress Bar Left")),
		('barright', _("Progress Bar Right")),
		('percleft', _("Percentage Left")),
		('percright', _("Percentage Right")),
		('no', _("No")) ])
	config.usage.show_channel_numbers_in_servicelist = ConfigYesNo(default = True)
	config.usage.show_channel_jump_in_servicelist = ConfigSelection(default="alpha", choices = [
					("alpha", _("Alpha")),
					("number", _("Number"))])

	def refreshServiceList(configElement):
		from Screens.InfoBar import InfoBar
		InfoBarInstance = InfoBar.instance
		if InfoBarInstance is not None:
			servicelist = InfoBarInstance.servicelist
			if servicelist:
				servicelist.setMode()
	config.usage.show_event_progress_in_servicelist.addNotifier(refreshServiceList)
	config.usage.show_channel_numbers_in_servicelist.addNotifier(refreshServiceList)

	config.usage.blinking_display_clock_during_recording = ConfigYesNo(default = False)

	config.usage.show_message_when_recording_starts = ConfigYesNo(default = True)

	config.usage.load_length_of_movies_in_moviellist = ConfigYesNo(default = True)
	config.usage.show_icons_in_movielist = ConfigSelection(default = 'i', choices = [
		('o', _("Off")),
		('p', _("Progress")),
		('s', _("Progress Small")),
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
		setPreferredTuner(int(configElement.value))
	config.usage.frontend_priority.addNotifier(PreferredTunerChanged)

	config.usage.hide_zap_errors = ConfigYesNo(default = False)
	config.usage.hide_ci_messages = ConfigYesNo(default = False)
	config.usage.show_cryptoinfo = ConfigSelection([("0", _("Off")),("1", _("One line")),("2", _("Two lines"))], "2")
	config.usage.show_eit_nownext = ConfigYesNo(default = True)

	config.epg = ConfigSubsection()
	config.epg.eit = ConfigYesNo(default = True)
	config.epg.mhw = ConfigYesNo(default = False)
	config.epg.freesat = ConfigYesNo(default = True)
	config.epg.viasat = ConfigYesNo(default = True)
	config.epg.netmed = ConfigYesNo(default = True)

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
		eEPGCache.getInstance().setEpgSources(mask)
	config.epg.eit.addNotifier(EpgSettingsChanged)
	config.epg.mhw.addNotifier(EpgSettingsChanged)
	config.epg.freesat.addNotifier(EpgSettingsChanged)
	config.epg.viasat.addNotifier(EpgSettingsChanged)
	config.epg.netmed.addNotifier(EpgSettingsChanged)

	config.epg.histminutes = ConfigSelectionNumber(min = 0, max = 120, stepwidth = 15, default = 0, wraparound = True)
	def EpgHistorySecondsChanged(configElement):
		from enigma import eEPGCache
		eEPGCache.getInstance().setEpgHistorySeconds(config.epg.histminutes.getValue()*60)
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
	config.osd.threeDmode = ConfigSelection([("off", _("Off")), ("auto", _("Auto")), ("sidebyside", _("Side by Side")),("topandbottom", _("Top and Bottom"))], "auto")
	config.osd.threeDznorm = ConfigSlider(default = 50, increment = 1, limits = (0, 100))
	config.osd.show3dextensions = ConfigYesNo(default = False)

	hddchoises = [('/etc/enigma2/', 'Internal Flash')]
	for p in harddiskmanager.getMountedPartitions():
		d = os.path.normpath(p.mountpoint)
		if os.path.exists(p.mountpoint):
			if p.mountpoint != '/':
				hddchoises.append((d + '/', p.mountpoint))
	config.misc.epgcachepath = ConfigSelection(default = '/etc/enigma2/', choices = hddchoises)
	config.misc.epgcachefilename = ConfigText(default='epg', fixed_size=False)
	config.misc.epgcache_filename = ConfigText(default = (config.misc.epgcachepath.value + config.misc.epgcachefilename.value.replace('.dat','') + '.dat'))
	def EpgCacheChanged(configElement):
		config.misc.epgcache_filename.setValue(os.path.join(config.misc.epgcachepath.value, config.misc.epgcachefilename.value.replace('.dat','') + '.dat'))
		config.misc.epgcache_filename.save()
		enigma.eEPGCache.getInstance().setCacheFile(config.misc.epgcache_filename.value)
		from enigma import eEPGCache
		epgcache = eEPGCache.getInstance()
		epgcache.save()
 	config.misc.epgcachepath.addNotifier(EpgCacheChanged, immediate_feedback = False)
	config.misc.epgcachefilename.addNotifier(EpgCacheChanged, immediate_feedback = False)

	config.misc.showradiopic = ConfigYesNo(default = True)

	def setHDDStandby(configElement):
		for hdd in harddiskmanager.HDDList():
			hdd[1].setIdleTime(int(configElement.value))
	config.usage.hdd_standby.addNotifier(setHDDStandby, immediate_feedback=False)

	def set12VOutput(configElement):
		if configElement.value == "on":
			enigma.Misc_Options.getInstance().set_12V_output(1)
		elif configElement.value == "off":
			enigma.Misc_Options.getInstance().set_12V_output(0)
	config.usage.output_12V.addNotifier(set12VOutput, immediate_feedback=False)

	SystemInfo["12V_Output"] = enigma.Misc_Options.getInstance().detected_12V_output()

	config.usage.keymap = ConfigText(default = eEnv.resolve("${datadir}/enigma2/keymap.xml"))

	config.network = ConfigSubsection()
	config.network.AFP_autostart = ConfigYesNo(default = True)
	config.network.NFS_autostart = ConfigYesNo(default = True)
	config.network.OpenVPN_autostart = ConfigYesNo(default = True)
	config.network.Samba_autostart = ConfigYesNo(default = True)
	config.network.Inadyn_autostart = ConfigYesNo(default = True)
	config.network.uShare_autostart = ConfigYesNo(default = True)

	config.timeshift = ConfigSubsection()
	config.timeshift.enabled = ConfigYesNo(default = False)
	config.timeshift.maxevents = ConfigInteger(default=5, limits=(1, 99))
	config.timeshift.maxlength = ConfigInteger(default=180, limits=(5, 999))
	config.timeshift.startdelay = ConfigInteger(default=5, limits=(5, 999))
	config.timeshift.showinfobar = ConfigYesNo(default = True)
	config.timeshift.stopwhilerecording = ConfigYesNo(default = False)
	config.timeshift.favoriteSaveAction = ConfigSelection([("askuser", _("Ask user")),("savetimeshift", _("Save and stop")),("savetimeshiftandrecord", _("Save and record")),("noSave", _("Don't save"))], "askuser")
	config.timeshift.permanentrecording = ConfigYesNo(default = False)
	config.timeshift.isRecording = NoSave(ConfigYesNo(default = False))

	config.seek = ConfigSubsection()
	config.seek.baractivation = ConfigSelection([("leftright", _("Long Left/Right")),("ffrw", _("Long << / >>"))], "leftright")
	config.seek.sensibility = ConfigInteger(default=10, limits=(1, 10))
	config.seek.selfdefined_13 = ConfigNumber(default=15)
	config.seek.selfdefined_46 = ConfigNumber(default=60)
	config.seek.selfdefined_79 = ConfigNumber(default=300)

	config.seek.speeds_forward = ConfigSet(default=[2, 4, 8, 16, 32, 64, 128], choices=[2, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128])
	config.seek.speeds_backward = ConfigSet(default=[2, 4, 8, 16, 32, 64, 128], choices=[1, 2, 4, 6, 8, 12, 16, 24, 32, 48, 64, 96, 128])
	config.seek.speeds_slowmotion = ConfigSet(default=[2, 4, 8], choices=[2, 4, 6, 8, 12, 16, 25])

	config.seek.enter_forward = ConfigSelection(default = "2", choices = ["2", "4", "6", "8", "12", "16", "24", "32", "48", "64", "96", "128"])
	config.seek.enter_backward = ConfigSelection(default = "1", choices = ["1", "2", "4", "6", "8", "12", "16", "24", "32", "48", "64", "96", "128"])

	config.seek.on_pause = ConfigSelection(default = "play", choices = [
		("play", _("Play")),
		("step", _("Singlestep (GOP)")),
		("last", _("Last speed")) ])


	config.crash = ConfigSubsection()
	config.crash.details = ConfigYesNo(default = True)
	config.crash.enabledebug = ConfigYesNo(default = False)
	config.crash.debugloglimit = ConfigNumber(default=4)
	config.crash.daysloglimit = ConfigNumber(default=8)
	config.crash.sizeloglimit = ConfigNumber(default=10)

	debugpath = [('/home/root/logs/', '/home/root/')]
	for p in harddiskmanager.getMountedPartitions():
		d = os.path.normpath(p.mountpoint)
		if os.path.exists(p.mountpoint):
			if p.mountpoint != '/':
				debugpath.append((d + '/logs/', p.mountpoint))
	config.crash.debug_path = ConfigSelection(default = "/home/root/logs/", choices = debugpath)

	def updatedebug_path(configElement):
		if not os.path.exists(config.crash.debug_path.value):
			os.mkdir(config.crash.debug_path.value,0755)
	config.crash.debug_path.addNotifier(updatedebug_path, immediate_feedback = False)

	config.usage.timerlist_finished_timer_position = ConfigSelection(default = "end", choices = [("beginning", _("at beginning")), ("end", _("at end"))])

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
		enigma.eBackgroundFileEraser.getInstance().setEraseSpeed(int(el.value))
	def updateEraseFlags(el):
		enigma.eBackgroundFileEraser.getInstance().setEraseFlags(int(el.value))
	config.misc.erase_speed = ConfigSelection(default="20", choices = [
		("10", "10 MB/s"),
		("20", "20 MB/s"),
		("50", "50 MB/s"),
		("100", "100 MB/s")])
	config.misc.erase_speed.addNotifier(updateEraseSpeed, immediate_feedback = False)
	config.misc.erase_flags = ConfigSelection(default="1", choices = [
		("0", _("Disable")),
		("1", _("Internal hdd only")),
		("3", _("Everywhere"))])
	config.misc.erase_flags.addNotifier(updateEraseFlags, immediate_feedback = False)

	SystemInfo["ZapMode"] = os.path.exists("/proc/stb/video/zapmode") or os.path.exists("/proc/stb/video/zapping_mode")
	if os.path.exists("/proc/stb/video/zapping_mode"):
		zapoptions = [("mute", _("Black screen")), ("hold", _("Hold screen"))]
		zapfile = "/proc/stb/video/zapping_mode"
	else:
		zapoptions = [("mute", _("Black screen")), ("hold", _("Hold screen")), ("mutetilllock", _("Black screen till locked")), ("holdtilllock", _("Hold till locked"))]
		zapfile = "/proc/stb/video/zapmode"
	if SystemInfo["ZapMode"]:
		def setZapmode(el):
			try:
				file = open(zapfile, "w")
				file.write(el.value)
				file.close()
			except:
				pass
		config.misc.zapmode = ConfigSelection(default = "mute", choices = zapoptions )
		config.misc.zapmode.addNotifier(setZapmode, immediate_feedback = False)

	config.subtitles = ConfigSubsection()
	config.subtitles.ttx_subtitle_colors = ConfigSelection(default = "1", choices = [
		("0", _("original")),
		("1", _("white")),
		("2", _("yellow")) ])
	config.subtitles.ttx_subtitle_original_position = ConfigYesNo(default = False)
	config.subtitles.subtitle_position = ConfigSelection( choices = ["0", "10", "20", "30", "40", "50", "60", "70", "80", "90", "100", "150", "200", "250", "300", "350", "400", "450"], default = "50")
	config.subtitles.subtitle_alignment = ConfigSelection(choices = [("left", _("left")), ("center", _("center")), ("right", _("right"))], default = "center")
	config.subtitles.subtitle_rewrap = ConfigYesNo(default = False)
	config.subtitles.subtitle_borderwidth = ConfigSelection(choices = ["1", "2", "3", "4", "5"], default = "3")
	config.subtitles.subtitle_fontsize  = ConfigSelection(choices = ["16", "18", "20", "22", "24", "26", "28", "30", "32", "34", "36", "38", "40", "42", "44", "46", "48", "50", "52", "54"], default = "34")
	choicelist = []
	for i in range(45000, 945000, 45000):
		choicelist.append(("%d" % i, "%2.1f sec" % (i / 90000.)))
	config.subtitles.subtitle_noPTSrecordingdelay = ConfigSelection(default = "315000", choices = [("0", _("No Delay"))] + choicelist)

	config.subtitles.dvb_subtitles_yellow = ConfigYesNo(default = False)
	config.subtitles.dvb_subtitles_original_position = ConfigSelection(default = "0", choices = [("0", _("original")), ("1", _("fixed")), ("2", _("relative"))])
	config.subtitles.dvb_subtitles_centered = ConfigYesNo(default = False)
	config.subtitles.dvb_subtitles_backtrans = ConfigSelection(default = "0", choices = [
		("0", _("no transparency")),
		("25", "10%"),
		("50", "20%"),
		("75", "30%"),
		("100", "40%"),
		("125", "50%"),
		("150", "60%"),
		("175", "70%"),
		("200", "80%"),
		("225", "90%"),
		("255", _("full transparency"))])
	config.subtitles.pango_subtitles_yellow = ConfigYesNo(default = False)

	config.autolanguage = ConfigSubsection()
	audio_language_choices=[
		("---", _("None")),
		("und", _("Undetermined")),
		("orj dos ory org esl qaa und mis mul ORY ORJ Audio_ORJ", _("Original")),
		("ara", _("Arabic")),
		("eus baq", _("Basque")),
		("bul", _("Bulgarian")),
		("hrv", _("Croatian")),
		("ces cze", _("Czech")),
		("dan", _("Danish")),
		("dut ndl", _("Dutch")),
		("eng qaa", _("English")),
		("est", _("Estonian")),
		("fin", _("Finnish")),
		("fra fre", _("French")),
		("deu ger", _("German")),
		("ell gre", _("Greek")),
		("heb", _("Hebrew")),
		("hun", _("Hungarian")),
		("ita", _("Italian")),
		("lat", _("Latvian")),
		("lit", _("Lithuanian")),
		("ltz", _("Letzeburgesch")),
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
		("tur Audio_TUR", _("Turkish"))]

	def setEpgLanguage(configElement):
		enigma.eServiceEvent.setEPGLanguage(configElement.value)
	config.autolanguage.audio_epglanguage = ConfigSelection(audio_language_choices[:1] + audio_language_choices [2:], default="---")
	config.autolanguage.audio_epglanguage.addNotifier(setEpgLanguage)

	def setEpgLanguageAlternative(configElement):
		enigma.eServiceEvent.setEPGLanguageAlternative(configElement.value)
	config.autolanguage.audio_epglanguage_alternative = ConfigSelection(audio_language_choices[:1] + audio_language_choices [2:], default="---")
	config.autolanguage.audio_epglanguage_alternative.addNotifier(setEpgLanguageAlternative)

	config.autolanguage.audio_autoselect1 = ConfigSelection(choices=audio_language_choices, default="---")
	config.autolanguage.audio_autoselect2 = ConfigSelection(choices=audio_language_choices, default="---")
	config.autolanguage.audio_autoselect3 = ConfigSelection(choices=audio_language_choices, default="---")
	config.autolanguage.audio_autoselect4 = ConfigSelection(choices=audio_language_choices, default="---")
	config.autolanguage.audio_defaultac3 = ConfigYesNo(default = True)
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
		("0", "None"),("1", "1"),("2", "2"),("3", "1,2"),
		("4", "3"),("5", "1,3"),("6", "2,3"),("7", "1,2,3"),
		("8", "4"),("9", "1,4"),("10", "2,4"),("11", "1,2,4"),
		("12", "3,4"),("13", "1,3,4"),("14", "2,3,4"),("15", "All")])

	config.logmanager = ConfigSubsection()
	config.logmanager.showinextensions = ConfigYesNo(default = False)
	config.logmanager.user = ConfigText(default='', fixed_size=False)
	config.logmanager.useremail = ConfigText(default='', fixed_size=False)
	config.logmanager.usersendcopy = ConfigYesNo(default = True)
	config.logmanager.path = ConfigText(default = "/")
	config.logmanager.additionalinfo = NoSave(ConfigText(default = ""))
	config.logmanager.sentfiles = ConfigLocations(default='')

	config.softcammanager = ConfigSubsection()
	config.softcammanager.softcams_autostart = ConfigLocations(default='')
	config.softcammanager.softcamtimerenabled = ConfigYesNo(default = True)
	config.softcammanager.softcamtimer = ConfigNumber(default = 6)

	config.imagemanager = ConfigSubsection()
	config.imagemanager.folderprefix = ConfigText(default=folderprefix, fixed_size=False)
	config.imagemanager.backuplocation = ConfigSelection(choices = hddchoises)
	config.imagemanager.schedule = ConfigYesNo(default = False)
	config.imagemanager.scheduletime = ConfigClock(default = 0) # 1:00
	config.imagemanager.repeattype = ConfigSelection(default = "daily", choices = [("daily", _("Daily")), ("weekly", _("Weekly")), ("monthly", _("30 Days"))])
	config.imagemanager.backupretry = ConfigNumber(default = 30)
	config.imagemanager.backupretrycount = NoSave(ConfigNumber(default = 0))
	config.imagemanager.nextscheduletime = NoSave(ConfigNumber(default = 0))
	config.imagemanager.restoreimage = NoSave(ConfigText(default=folderprefix, fixed_size=False))

	config.backupmanager = ConfigSubsection()
	config.backupmanager.folderprefix = ConfigText(default=folderprefix, fixed_size=False)
	config.backupmanager.backuplocation = ConfigSelection(choices = hddchoises)
	config.backupmanager.schedule = ConfigYesNo(default = False)
	config.backupmanager.scheduletime = ConfigClock(default = 0) # 1:00
	config.backupmanager.repeattype = ConfigSelection(default = "daily", choices = [("daily", _("Daily")), ("weekly", _("Weekly")), ("monthly", _("30 Days"))])
	config.backupmanager.backupretry = ConfigNumber(default = 30)
	config.backupmanager.backupretrycount = NoSave(ConfigNumber(default = 0))
	config.backupmanager.nextscheduletime = NoSave(ConfigNumber(default = 0))
	config.backupmanager.backupdirs = ConfigLocations(default=[eEnv.resolve('${sysconfdir}/enigma2/'), eEnv.resolve('${sysconfdir}/fstab'), eEnv.resolve('${sysconfdir}/hostname'), eEnv.resolve('${sysconfdir}/network/interfaces'), eEnv.resolve('${sysconfdir}/passwd'), eEnv.resolve('${sysconfdir}/etc/shadow'), eEnv.resolve('${sysconfdir}/resolv.conf'), eEnv.resolve('${sysconfdir}/ushare.conf'), eEnv.resolve('${sysconfdir}/inadyn.conf'), eEnv.resolve('${sysconfdir}/tuxbox/config/'), eEnv.resolve('${sysconfdir}/wpa_supplicant.conf'), '/usr/softcams/'])
	config.backupmanager.lastlog = ConfigText(default=' ', fixed_size=False)

	config.vixsettings = ConfigSubsection()
	config.vixsettings.Subservice = ConfigYesNo(default = False)
	config.vixsettings.ColouredButtons = ConfigYesNo(default = True)
	config.vixsettings.QuickEPG_mode = ConfigSelection(default="3", choices = [
					("0", _("as plugin in extended bar")),
					("1", _("with long OK press")),
					("2", _("with exit button")),
					("3", _("with left/right buttons"))])

	config.epgselection = ConfigSubsection()
	config.epgselection.showbouquet_vixepg = ConfigYesNo(default = False)
	config.epgselection.showbouquet_multi = ConfigYesNo(default = False)
	config.epgselection.preview_mode_vixepg = ConfigYesNo(default = True)
	config.epgselection.preview_mode_enhanced = ConfigYesNo(default = True)
	config.epgselection.preview_mode_infobar = ConfigYesNo(default = True)
	config.epgselection.preview_mode = ConfigYesNo(default = True)
	config.epgselection.graphics_mode = ConfigSelection(choices = [("graphics",_("Graphics")), ("text", _("Text"))], default = "graphics")
	config.epgselection.OK = ConfigSelection(choices = [("Zap",_("Zap")), ("Zap + Exit", _("Zap + Exit"))], default = "Zap")
	config.epgselection.OKLong = ConfigSelection(choices = [("Zap",_("Zap")), ("Zap + Exit", _("Zap + Exit"))], default = "Zap + Exit")
	config.epgselection.OK_vixepg = ConfigSelection(choices = [("Zap",_("Zap")), ("Zap + Exit", _("Zap + Exit"))], default = "Zap")
	config.epgselection.OKLong_vixepg = ConfigSelection(choices = [("Zap",_("Zap")), ("Zap + Exit", _("Zap + Exit"))], default = "Zap + Exit")
	config.epgselection.OK_enhanced = ConfigSelection(choices = [("Zap",_("Zap")), ("Zap + Exit", _("Zap + Exit"))], default = "Zap")
	config.epgselection.OKLong_enhanced = ConfigSelection(choices = [("Zap",_("Zap")), ("Zap + Exit", _("Zap + Exit"))], default = "Zap + Exit")
	config.epgselection.OK_infobar = ConfigSelection(choices = [("Zap",_("Zap")), ("Zap + Exit", _("Zap + Exit"))], default = "Zap")
	config.epgselection.OKLong_infobar = ConfigSelection(choices = [("Zap",_("Zap")), ("Zap + Exit", _("Zap + Exit"))], default = "Zap + Exit")
	config.epgselection.Info = ConfigSelection(choices = [("Channel Info", _("Channel Info")), ("Single EPG", _("Single EPG"))], default = "Channel Info")
	config.epgselection.InfoLong = ConfigSelection(choices = [("Channel Info", _("Channel Info")), ("Single EPG", _("Single EPG"))], default = "Single EPG")
	config.epgselection.roundTo = ConfigSelection(default = "15", choices = [("15", _("%d minutes") % 15), ("30", _("%d minutes") % 30), ("60", _("%d minutes") % 60)])
	config.epgselection.sort = ConfigSelection(default="0", choices = [("0", _("Time")),("1", _("Alphanumeric"))])
	config.epgselection.prev_time = ConfigClock(default = time())
	config.epgselection.primetimehour = ConfigSelectionNumber(default = 20, stepwidth = 1, min = 00, max = 23, wraparound = True)
	config.epgselection.primetimemins = ConfigSelectionNumber(default = 00, stepwidth = 1, min = 00, max = 59, wraparound = True)
	config.epgselection.servicetitle_mode = ConfigSelection(default = "picon+servicename", choices = [
	("servicename", _("Service Name")),
	("picon", _("Picon")),
	("picon+servicename", _("Picon and Service Name")) ])
	config.epgselection.channel1 = ConfigYesNo(default = False)
	config.epgselection.prev_time_period = ConfigSelectionNumber(default = 180, stepwidth = 1, min = 60, max = 300, wraparound = True)
	config.epgselection.serv_fontsize_vixepg = ConfigSelectionNumber(default = 0, stepwidth = 1, min = -8, max = 10, wraparound = True)
	config.epgselection.ev_fontsize_vixepg = ConfigSelectionNumber(default = 0, stepwidth = 1, min = -8, max = 10, wraparound = True)
	config.epgselection.tl_fontsize_vixepg = ConfigSelectionNumber(default = 0, stepwidth = 1, min = -8, max = 10, wraparound = True)
	config.epgselection.ev_fontsize_enhanced = ConfigSelectionNumber(default = 0, stepwidth = 1, min = -8, max = 10, wraparound = True)
	config.epgselection.ev_fontsize_multi = ConfigSelectionNumber(default = 0, stepwidth = 1, min = -8, max = 10, wraparound = True)
	config.epgselection.ev_fontsize_infobar = ConfigSelectionNumber(default = 0, stepwidth = 1, min = -8, max = 10, wraparound = True)
	config.epgselection.itemsperpage_vixepg = ConfigSelectionNumber(default = 8, stepwidth = 1, min = 3, max = 16, wraparound = True)
	config.epgselection.itemsperpage_enhanced = ConfigSelectionNumber(default = 18, stepwidth = 1, min = 12, max = 40, wraparound = True)
	config.epgselection.itemsperpage_multi = ConfigSelectionNumber(default = 18, stepwidth = 1, min = 12, max = 40, wraparound = True)
	config.epgselection.itemsperpage_infobar = ConfigSelectionNumber(default = 2, stepwidth = 1, min = 2, max = 4, wraparound = True)
	config.epgselection.overjump = ConfigYesNo(default = False)
	config.epgselection.pictureingraphics = ConfigYesNo(default = True)
	config.epgselection.heightswitch = NoSave(ConfigYesNo(default = False))

	if not os.path.exists('/usr/softcams/'):
		os.mkdir('/usr/softcams/',0755)
	softcams = os.listdir('/usr/softcams/')
	config.oscaminfo = ConfigSubsection()
	config.oscaminfo.showInExtensions = ConfigYesNo(default=False)
	config.oscaminfo.userdatafromconf = ConfigYesNo(default = False)
	config.oscaminfo.autoupdate = ConfigYesNo(default = False)
	config.oscaminfo.username = ConfigText(default = "username", fixed_size = False, visible_width=12)
	config.oscaminfo.password = ConfigPassword(default = "password", fixed_size = False)
	config.oscaminfo.ip = ConfigIP( default = [ 127,0,0,1 ], auto_jump=True)
	config.oscaminfo.port = ConfigInteger(default = 16002, limits=(0,65536) )
	config.oscaminfo.intervall = ConfigInteger(default = 10, limits=(1,600) )
	SystemInfo["OScamInstalled"] = False

	config.cccaminfo = ConfigSubsection()
	config.cccaminfo.showInExtensions = ConfigYesNo(default=False)
	config.cccaminfo.serverNameLength = ConfigInteger(default=22, limits=(10, 100))
	config.cccaminfo.name = ConfigText(default="Profile", fixed_size=False)
	config.cccaminfo.ip = ConfigText(default="192.168.2.12", fixed_size=False)
	config.cccaminfo.username = ConfigText(default="", fixed_size=False)
	config.cccaminfo.password = ConfigText(default="", fixed_size=False)
	config.cccaminfo.port = ConfigInteger(default=16001, limits=(1, 65535))
	config.cccaminfo.profile = ConfigText(default="", fixed_size=False)
	config.cccaminfo.ecmInfoEnabled = ConfigYesNo(default=True)
	config.cccaminfo.ecmInfoTime = ConfigInteger(default=5, limits=(1, 10))
	config.cccaminfo.ecmInfoForceHide = ConfigYesNo(default=True)
	config.cccaminfo.ecmInfoPositionX = ConfigInteger(default=50)
	config.cccaminfo.ecmInfoPositionY = ConfigInteger(default=50)
	config.cccaminfo.blacklist = ConfigText(default="/media/cf/CCcamInfo.blacklisted", fixed_size=False)
	config.cccaminfo.profiles = ConfigText(default="/media/cf/CCcamInfo.profiles", fixed_size=False)
	SystemInfo["CCcamInstalled"] = False
	for softcam in softcams:
		if softcam.lower().startswith('cccam'):
			config.cccaminfo.showInExtensions = ConfigYesNo(default=True)
			SystemInfo["CCcamInstalled"] = True
		elif softcam.lower().startswith('oscam'):
			config.oscaminfo.showInExtensions = ConfigYesNo(default=True)
			SystemInfo["OScamInstalled"] = True

	config.streaming = ConfigSubsection()
	config.streaming.stream_ecm = ConfigYesNo(default = False)
	config.streaming.descramble = ConfigYesNo(default = True)
	config.streaming.stream_eit = ConfigYesNo(default = True)
	config.streaming.stream_ait = ConfigYesNo(default = True)

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
	return config.usage.default_path.value

