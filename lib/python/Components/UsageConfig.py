from Components.Harddisk import harddiskmanager
from config import config, ConfigSubsection, ConfigYesNo, ConfigSelection, ConfigText, ConfigNumber, ConfigSet, ConfigLocations, NoSave, ConfigClock, ConfigInteger, ConfigBoolean, ConfigPassword, ConfigIP, ConfigSlider
from Tools.Directories import resolveFilename, SCOPE_HDD, SCOPE_TIMESHIFT
from enigma import setTunerTypePriorityOrder, setPreferredTuner, setSpinnerOnOff, setEnableTtCachingOnOff;
from enigma import Misc_Options, eEnv;
from Components.NimManager import nimmanager
from SystemInfo import SystemInfo
import os
import enigma
from time import time

def InitUsageConfig():
	try:
		file = open('/etc/image-version', 'r')
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
	config.misc.useNTPminutes = ConfigSelection(default = "30", choices = [("30", "30 Minutes"), ("60", _("Hour")), ("1440", _("Once per day"))])
	config.misc.remotecontrol_text_support = ConfigYesNo(default = False)

	config.usage = ConfigSubsection();
	config.usage.showdish = ConfigYesNo(default = True)
	config.usage.multibouquet = ConfigYesNo(default = True)
	config.usage.panicbutton = ConfigYesNo(default = False)
	config.usage.multiepg_ask_bouquet = ConfigYesNo(default = False)
	config.usage.showpicon = ConfigYesNo(default = True)
	config.usage.show_dvdplayer = ConfigYesNo(default = False)
	
	config.usage.quickzap_bouquet_change = ConfigYesNo(default = False)
	config.usage.e1like_radio_mode = ConfigYesNo(default = True)
	config.usage.infobar_onlinechecktimer = ConfigInteger(default=0, limits=(0, 48))
	config.usage.infobar_onlineupdatelastcheck = ConfigInteger(default=0)
	config.usage.infobar_onlineupdatefound = NoSave(ConfigBoolean(default = False))
	config.usage.infobar_timeout = ConfigSelection(default = "5", choices = [
		("0", _("no timeout")), ("1", "1 " + _("second")), ("2", "2 " + _("seconds")), ("3", "3 " + _("seconds")),
		("4", "4 " + _("seconds")), ("5", "5 " + _("seconds")), ("6", "6 " + _("seconds")), ("7", "7 " + _("seconds")),
		("8", "8 " + _("seconds")), ("9", "9 " + _("seconds")), ("10", "10 " + _("seconds"))])
	config.usage.show_infobar_on_zap = ConfigYesNo(default = True)
	config.usage.show_infobar_on_skip = ConfigYesNo(default = True)
	config.usage.show_infobar_on_event_change = ConfigYesNo(default = False)
	config.usage.show_infobar_lite = ConfigYesNo(default = False)
	config.usage.show_second_infobar = ConfigSelection(default = "1", choices = [("0", _("Off")), ("1", _("Event Info")), ("2", _("2nd Infobar INFO")), ("3", _("2nd Infobar ECM"))])
	config.usage.second_infobar_timeout = ConfigSelection(default = "5", choices = [
		("0", _("no timeout")), ("1", "1 " + _("second")), ("2", "2 " + _("seconds")),
		("3", "3 " + _("seconds")), ("4", "4 " + _("seconds")), ("5", "5 " + _("seconds")), ("6", "6 " + _("seconds")),
		("7", "7 " + _("seconds")), ("8", "8 " + _("seconds")), ("9", "9 " + _("seconds")), ("10", "10 " + _("seconds"))])
	config.usage.show_spinner = ConfigYesNo(default = True)
	config.usage.enable_tt_caching = ConfigYesNo(default = True)
	config.usage.hdd_standby = ConfigSelection(default = "300", choices = [
		("0", _("no standby")), ("10", "10 " + _("seconds")), ("30", "30 " + _("seconds")),
		("60", "1 " + _("minute")), ("120", "2 " + _("minutes")),
		("300", "5 " + _("minutes")), ("600", "10 " + _("minutes")), ("1200", "20 " + _("minutes")),
		("1800", "30 " + _("minutes")), ("3600", "1 " + _("hour")), ("7200", "2 " + _("hours")),
		("14400", "4 " + _("hours")) ])
	config.usage.hdd_timer = ConfigYesNo(default = False)	
	config.usage.output_12V = ConfigSelection(default = "do not change", choices = [
		("do not change", _("do not change")), ("off", _("off")), ("on", _("on")) ])

	config.usage.pip_zero_button = ConfigSelection(default = "standard", choices = [
		("standard", _("standard")), ("swap", _("swap PiP and main picture")),
		("swapstop", _("move PiP to main picture")), ("stop", _("stop PiP")) ])

	if not os.path.exists(resolveFilename(SCOPE_HDD)):
		try:
			os.mkdir(resolveFilename(SCOPE_HDD),0755)
		except OSError:
			return -1
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
		except OSError:
			return -1
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
		("ask", _("Ask user")), ("movielist", _("Return to movie list")), ("quit", _("Return to previous service")), ("pause", _("Pause movie at end")) ])

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
	config.usage.show_event_progress_in_servicelist = ConfigYesNo(default = True)
	config.usage.show_channel_numbers_in_servicelist = ConfigYesNo(default = True)
	config.usage.show_channel_jump_in_servicelist = ConfigSelection(default="alpha", choices = [
					("alpha", _("Alpha")),
					("number", _("Number"))])

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
	config.usage.swap_time_display_on_osd = ConfigSelection(default = "0", choices = [("0", _("Skin Setting")), ("1", _("Mins")), ("2", _("Hours Mins")), ("3", _("Percentage"))])
	config.usage.swap_media_time_display_on_osd = ConfigSelection(default = "0", choices = [("0", _("Skin Setting")), ("1", _("Mins")), ("2", _("Mins Secs")), ("3", _("Hours Mins")), ("4", _("Hours Mins Secs")), ("5", _("Percentage"))])
	config.usage.swap_time_remaining_on_osd = ConfigSelection(default = "0", choices = [("0", _("Remaining")), ("1", _("Elapsed")), ("2", _("Elapsed & Remaining")), ("3", _("Remaining & Elapsed"))])

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

	config.usage.hide_zap_errors = ConfigYesNo(default = True)
	config.usage.hide_ci_messages = ConfigYesNo(default = True)
	config.usage.show_cryptoinfo = ConfigYesNo(default = True)
	config.usage.show_eit_nownext = ConfigYesNo(default = True)

	config.osd = ConfigSubsection()
	config.osd.dst_left = ConfigSlider(default = 0, increment = 1, limits = (0, 720))
	config.osd.dst_width = ConfigSlider(default = 720, increment = 1, limits = (0, 720))
	config.osd.dst_top = ConfigSlider(default = 0, increment = 1, limits = (0, 576))
	config.osd.dst_height = ConfigSlider(default = 576, increment = 1, limits = (0, 576))
	config.osd.alpha = ConfigSlider(default=255, limits=(0,255))
	if config.misc.boxtype.value.startswith('vu'):
		choiceoptions = [("0", _("Off")), ("1", _("Side by Side")),("2", _("Top and Bottom")), ("3", _("Auto"))]
		config.osd.threeDmode = ConfigSelection(default = 'auto', choices = choiceoptions )
	elif config.misc.boxtype.value.startswith('et'):
		choiceoptions = [("off", _("Off")), ("auto", _("Auto")), ("sidebyside", _("Side by Side")),("topandbottom", _("Top and Bottom"))]
		config.osd.threeDmode = ConfigSelection(default = 'auto', choices = choiceoptions )
	elif config.misc.boxtype.value.startswith('gb'):
		choiceoptions = [("off", _("Off")), ("auto", _("Auto")), ("sidebyside", _("Side by Side")),("topandbottom", _("Top and Bottom"))]
		config.osd.threeDmode = ConfigSelection(default = 'auto', choices = choiceoptions )
	else:
		choiceoptions = [("off", _("Off"))]
		config.osd.threeDmode = ConfigSelection(default = 'off', choices = choiceoptions )
	config.osd.threeDznorm = ConfigSlider(default = 50, increment = 1, limits = (0, 100))
	config.osd.show3dextensions = ConfigYesNo(default = False)
	
	config.epg = ConfigSubsection()
	config.epg.eit = ConfigYesNo(default = True)
	config.epg.mhw = ConfigYesNo(default = False)
	config.epg.freesat = ConfigYesNo(default = True)
	config.epg.viasat = ConfigYesNo(default = True)
	config.epg.netmed = ConfigYesNo(default = True)
	config.misc.showradiopic = ConfigYesNo(default = True)
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
	config.epg.cacheloadsched = ConfigYesNo(default = False)
	config.epg.cachesavesched = ConfigYesNo(default = False)
	def EpgCacheLoadSchedChanged(configElement):
		import Screens.EpgLoadSave
		Screens.EpgLoadSave.EpgCacheLoadCheck()
	def EpgCacheSaveSchedChanged(configElement):
		import Screens.EpgLoadSave
		Screens.EpgLoadSave.EpgCacheSaveCheck()
	config.epg.cacheloadsched.addNotifier(EpgCacheLoadSchedChanged, immediate_feedback = False)
	config.epg.cachesavesched.addNotifier(EpgCacheSaveSchedChanged, immediate_feedback = False)
	config.epg.cacheloadtimer = ConfigSelection(default = 24, choices = [
		("1", "1"),("2", "2"),("3", "3"),("4", "4"),("5", "5"),("6", "6"),("7", "7"),("8", "8"),("9", "9"),("10", "10"),
		("11", "11"),("12", "12"),("13", "13"),("14", "14"),("15", "15"),("16", "16"),("17", "17"),("18", "18"),("19", "19"),("20", "20"),
		("21", "21"),("22", "22"),("23", "23"),("24", "24")])
	config.epg.cachesavetimer = ConfigSelection(default = 24, choices = [
		("1", "1"),("2", "2"),("3", "3"),("4", "4"),("5", "5"),("6", "6"),("7", "7"),("8", "8"),("9", "9"),("10", "10"),
		("11", "11"),("12", "12"),("13", "13"),("14", "14"),("15", "15"),("16", "16"),("17", "17"),("18", "18"),("19", "19"),("20", "20"),
		("21", "21"),("22", "22"),("23", "23"),("24", "24")])

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

	def setHDDStandby(configElement):
		for hdd in harddiskmanager.HDDList():
			hdd[1].setIdleTime(int(configElement.value),config.usage.hdd_timer.value)
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
	config.network.AFP_autostart = ConfigYesNo(default = False)
	config.network.NFS_autostart = ConfigYesNo(default = False)
	config.network.OpenVPN_autostart = ConfigYesNo(default = False)
	config.network.Samba_autostart = ConfigYesNo(default = False)
	config.network.Inadyn_autostart = ConfigYesNo(default = False)
	config.network.uShare_autostart = ConfigYesNo(default = False)

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
	config.crash.details = ConfigYesNo(default = False)
	config.crash.enabledebug = ConfigYesNo(default = False)
	config.crash.debugloglimit = ConfigNumber(default=4)

	debugpath = [('/home/root/', '/home/root/')]
	for p in harddiskmanager.getMountedPartitions():
		d = os.path.normpath(p.mountpoint)
		if os.path.exists(p.mountpoint):
			if p.mountpoint != '/':
				debugpath.append((d + '/', p.mountpoint))
	config.crash.debug_path = ConfigSelection(default = "/home/root/", choices = debugpath)

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

	def updateFlushSize(el):
		enigma.setFlushSize(int(el.value))
		print "[SETTING] getFlushSize=", enigma.getFlushSize()
	def updateDemuxSize(el):
		enigma.setDemuxSize(int(el.value))
		print "[SETTING] getDemuxSize=", enigma.getDemuxSize()
	config.misc.flush_size = ConfigSelection(default = "0", choices = [
		("0", "Off"),
		("524288", "512kB"),
		("1048576", "1 MB"),
		("2097152", "2 MB"),
		("4194304", "4 MB")])
	config.misc.flush_size.addNotifier(updateFlushSize, immediate_feedback = False)
	config.misc.demux_size = ConfigSelection(default = "1540096", choices = [
		("770048", "Small 0.7 MB"),
		("962560", "Normal 1 MB"),
		("1540096", "Large 1.5MB"),
		("1925120", "Huge 2 MB")])
	config.misc.demux_size.addNotifier(updateDemuxSize, immediate_feedback = False)
	
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

	SystemInfo["ZapMode"] = os.path.exists("/proc/stb/video/zapmode")
	def setZapmode(el):
		try:
			file = open("/proc/stb/video/zapmode", "w")
			file.write(el.value)
			file.close()
		except:
			pass
	config.misc.zapmode = ConfigSelection(default = "mute", choices = [
		("mute", _("Black screen")), ("hold", _("Hold screen")), ("mutetilllock", _("Black screen till locked")), ("holdtilllock", _("Hold till locked"))])
	config.misc.zapmode.addNotifier(setZapmode, immediate_feedback = False)

	config.subtitles = ConfigSubsection()
	config.subtitles.ttx_subtitle_colors = ConfigSelection(default = "1", choices = [
		("0", _("original")),
		("1", _("white")),
		("2", _("yellow")) ])
	config.subtitles.ttx_subtitle_original_position = ConfigYesNo(default = False)
	config.subtitles.subtitle_position = ConfigSelection( choices = ["0", "10", "20", "30", "40", "50", "60", "70", "80", "90", "100", "150", "200", "250", "300", "350", "400", "450"], default = "50")
	config.subtitles.subtitle_alignment = ConfigSelection(choices = ["left", "center", "right"], default = "center")
	config.subtitles.subtitle_rewrap = ConfigYesNo(default = False)
	config.subtitles.subtitle_borderwidth = ConfigSelection(choices = ["1", "2", "3", "4", "5"], default = "3")
	config.subtitles.subtitle_fontsize  = ConfigSelection(choices = ["16", "18", "20", "22", "24", "26", "28", "30", "32", "34", "36", "38", "40", "42", "44", "46", "48", "50", "52", "54"], default = "34")
	config.subtitles.subtitle_noPTSrecordingdelay  = ConfigSelection(default = "315000", choices = [
		("0", "No Delay"),
		("45000", "0.5 sec"),
		("90000", "1.0 sec"),
		("135000", "1.5 sec"),
		("180000", "2.0 sec"),
		("225000", "2.5 sec"),
		("270000", "3.0 sec"),
		("315000", "3.5 sec"),
		("360000", "4.0 sec"),
		("405000", "4.5 sec"),
		("450000", "5.0 sec"),
		("495000", "5.5 sec"),
		("540000", "6.0 sec"),
		("585000", "6.5 sec"),
		("630000", "7.0 sec"),
		("475000", "7.5 sec"),
		("720000", "8.0 sec"),
		("765000", "8.5 sec"),
		("810000", "9.0 sec"),
		("855000", "9.5 sec"),
		("900000", "10.0 sec")])

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
		("---", "None"),
		("und", "Undetermined"),
		("orj dos ory org esl qaa und mis mul ORY Audio_ORJ", "Original"),
		("ara", "Arabic"),
		("eus baq", "Basque"),
		("bul", "Bulgarian"), 
		("hrv", "Croatian"),
		("ces cze", "Czech"),
		("dan", "Danish"),
		("dut ndl", "Dutch"),
		("eng qaa", "English"),
		("est", "Estonian"),
		("fin", "Finnish"),
		("fra fre", "French"),
		("deu ger", "German"),
		("ell gre", "Greek"),
		("heb", "Hebrew"),
		("hun", "Hungarian"),
		("ita", "Italian"),
		("lat", "Latvian"),
		("lit", "Lithuanian"),
		("ltz", "Letzeburgesch"),
		("nor", "Norwegian"),
		("pol", "Polish"),
		("por", "Portuguese"),
		("fas per", "Persian"),
		("ron rum", "Romanian"),
		("rus", "Russian"),
		("srp", "Serbian"),
		("slk slo", "Slovak"),
		("slv", "Slovenian"),
		("spa", "Spanish"),
		("swe", "Swedish"),
		("tur Audio_TUR", "Turkish")]

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
	config.autolanguage.audio_defaultac3 = ConfigYesNo(default = False)
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
	config.backupmanager.backupdirs = ConfigLocations(default=[eEnv.resolve('${sysconfdir}/enigma2/'), eEnv.resolve('${sysconfdir}/fstab'), eEnv.resolve('${sysconfdir}/hostname'), eEnv.resolve('${sysconfdir}/network/interfaces'), eEnv.resolve('${sysconfdir}/passwd'), eEnv.resolve('${sysconfdir}/resolv.conf'), eEnv.resolve('${sysconfdir}/ushare.conf'), eEnv.resolve('${sysconfdir}/inadyn.conf'), eEnv.resolve('${sysconfdir}/tuxbox/config/'), eEnv.resolve('${sysconfdir}/wpa_supplicant.conf'), '/usr/softcams/'])
	config.backupmanager.lastlog = ConfigText(default=' ', fixed_size=False)

	config.plisettings = ConfigSubsection()
	config.plisettings.Subservice = ConfigYesNo(default = True)
	config.plisettings.ColouredButtons = ConfigYesNo(default = False)
	config.plisettings.PLIEPG_mode = ConfigSelection(default="cooltvguide", choices = [
					("pliepg", _("Show Graphical EPG")),
					("single", _("Show Single EPG")),
					("multi", _("Show Multi EPG")),
					("eventview", _("Show Eventview")),
					("merlinepgcenter", _("Show Merlin EPG Center")),
					("cooltvguide", _("Show CoolTVGuide"))])
	config.plisettings.PLIINFO_mode = ConfigSelection(default="coolinfoguide", choices = [
					("eventview", _("Show Eventview")),
					("epgpress", _("Show EPG")),
					("coolsingleguide", _("Show CoolSingleGuide")),
					("coolinfoguide", _("Show CoolInfoGuide"))])				
	config.plisettings.QuickEPG_mode = ConfigSelection(default="3", choices = [
					("0", _("as plugin in extended bar")),
					("1", _("with long OK press")),
					("2", _("with exit button")),
					("3", _("with left/right buttons"))])

	config.GraphEPG = ConfigSubsection()
	config.GraphEPG.ShowBouquet = ConfigYesNo(default = False)
	config.GraphEPG.preview_mode_pliepg = ConfigYesNo(default = True)
	config.GraphEPG.preview_mode_enhanced = ConfigYesNo(default = True)
	config.GraphEPG.preview_mode_infobar = ConfigYesNo(default = True)
	config.GraphEPG.preview_mode = ConfigYesNo(default = True)
	config.GraphEPG.OK = ConfigSelection(choices = [("Zap",_("Zap")), ("Zap + Exit", _("Zap + Exit"))], default = "Zap")
	config.GraphEPG.OKLong = ConfigSelection(choices = [("Zap",_("Zap")), ("Zap + Exit", _("Zap + Exit"))], default = "Zap + Exit")
	config.GraphEPG.OK_pliepg = ConfigSelection(choices = [("EventView",_("EventView")), ("Zap",_("Zap")), ("Zap + Exit", _("Zap + Exit"))], default = "Zap")
	config.GraphEPG.OKLong_pliepg = ConfigSelection(choices = [("Zap",_("Zap")), ("Zap + Exit", _("Zap + Exit"))], default = "Zap + Exit")
	config.GraphEPG.OK_enhanced = ConfigSelection(choices = [("EventView",_("EventView")), ("Zap",_("Zap")), ("Zap + Exit", _("Zap + Exit"))], default = "Zap")
	config.GraphEPG.OKLong_enhanced = ConfigSelection(choices = [("Zap",_("Zap")), ("Zap + Exit", _("Zap + Exit"))], default = "Zap + Exit")
	config.GraphEPG.OK_infobar = ConfigSelection(choices = [("EventView",_("EventView")), ("Zap",_("Zap")), ("Zap + Exit", _("Zap + Exit"))], default = "Zap")
	config.GraphEPG.OKLong_infobar = ConfigSelection(choices = [("Zap",_("Zap")), ("Zap + Exit", _("Zap + Exit"))], default = "Zap + Exit")
	config.GraphEPG.Info = ConfigSelection(choices = [("Channel Info", _("Channel Info")), ("Single EPG", _("Single EPG"))], default = "Channel Info")
	config.GraphEPG.InfoLong = ConfigSelection(choices = [("Channel Info", _("Channel Info")), ("Single EPG", _("Single EPG"))], default = "Single EPG")
	config.GraphEPG.prev_time=ConfigClock(default = time())
	config.GraphEPG.Primetime1 = ConfigSlider(default = 20, increment = 1, limits=(0, 23))
	config.GraphEPG.Primetime2 = ConfigSlider(default = 0, increment = 1, limits=(0, 59))
	config.GraphEPG.UsePicon = ConfigYesNo(default = True)
	config.GraphEPG.channel1 = ConfigYesNo(default = False)
	config.GraphEPG.prev_time_period = ConfigSlider(default = 180, increment = 1, limits=(60,300))
	config.GraphEPG.Fontsize = ConfigSlider(default = 18, increment = 1, limits=(10, 30))
	config.GraphEPG.Left_Fontsize = ConfigSlider(default = 22, increment = 1, limits=(10, 30))
	config.GraphEPG.Timeline = ConfigSlider(default = 20, increment = 1, limits=(10, 30))
	config.GraphEPG.items_per_page = ConfigSlider(default = 11, increment = 1, limits=(3, 16))
	config.GraphEPG.left8 = ConfigSlider(default = 110, increment = 1, limits=(70, 250))
	config.GraphEPG.left16 = ConfigSlider(default = 190, increment = 1, limits=(70, 250))
	config.GraphEPG.overjump = ConfigYesNo(default = False)
	config.GraphEPG.PIG = ConfigYesNo(default = False)
	config.GraphEPG.item_hight = NoSave(ConfigInteger(default=0))
	config.GraphEPG.item_width = NoSave(ConfigInteger(default=0))
	config.GraphEPG.item_rowhight = NoSave(ConfigInteger(default=0))
	config.GraphEPG.heightswitch = NoSave(ConfigYesNo(default = False))

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

