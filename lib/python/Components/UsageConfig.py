from Components.Harddisk import harddiskmanager
from config import ConfigSubsection, ConfigYesNo, config, ConfigSelection, ConfigText, ConfigNumber, ConfigSet, ConfigLocations
from Tools.Directories import resolveFilename, SCOPE_HDD
from enigma import setTunerTypePriorityOrder, setPreferredTuner, setSpinnerOnOff, setEnableTtCachingOnOff;
from Components.NimManager import nimmanager
from Components.Harddisk import harddiskmanager
from SystemInfo import SystemInfo
import os
import enigma

def InitUsageConfig():
	config.usage = ConfigSubsection();
	config.usage.showdish = ConfigYesNo(default = True)
	config.usage.multibouquet = ConfigYesNo(default = True)
	config.usage.quickzap_bouquet_change = ConfigYesNo(default = False)
	config.usage.e1like_radio_mode = ConfigYesNo(default = True)
	config.usage.infobar_timeout = ConfigSelection(default = "5", choices = [
		("0", _("no timeout")), ("1", "1 " + _("second")), ("2", "2 " + _("seconds")), ("3", "3 " + _("seconds")),
		("4", "4 " + _("seconds")), ("5", "5 " + _("seconds")), ("6", "6 " + _("seconds")), ("7", "7 " + _("seconds")),
		("8", "8 " + _("seconds")), ("9", "9 " + _("seconds")), ("10", "10 " + _("seconds"))])
	config.usage.show_infobar_on_zap = ConfigYesNo(default = True)
	config.usage.show_infobar_on_skip = ConfigYesNo(default = True)
	config.usage.show_infobar_on_event_change = ConfigYesNo(default = False)
	config.usage.show_spinner = ConfigYesNo(default = True)
	config.usage.enable_tt_caching = ConfigYesNo(default = True)
	config.usage.hdd_standby = ConfigSelection(default = "300", choices = [
		("0", _("no standby")), ("10", "10 " + _("seconds")), ("30", "30 " + _("seconds")),
		("60", "1 " + _("minute")), ("120", "2 " + _("minutes")),
		("300", "5 " + _("minutes")), ("600", "10 " + _("minutes")), ("1200", "20 " + _("minutes")),
		("1800", "30 " + _("minutes")), ("3600", "1 " + _("hour")), ("7200", "2 " + _("hours")),
		("14400", "4 " + _("hours")) ])
	config.usage.output_12V = ConfigSelection(default = "do not change", choices = [
		("do not change", _("do not change")), ("off", _("off")), ("on", _("on")) ])

	config.usage.pip_zero_button = ConfigSelection(default = "standard", choices = [
		("standard", _("standard")), ("swap", _("swap PiP and main picture")),
		("swapstop", _("move PiP to main picture")), ("stop", _("stop PiP")) ])

	config.usage.default_path = ConfigText(default = resolveFilename(SCOPE_HDD))
	config.usage.timer_path = ConfigText(default = "<default>")
	config.usage.instantrec_path = ConfigText(default = "<default>")
	config.usage.timeshift_path = ConfigText(default = "/media/hdd/")
	config.usage.allowed_timeshift_paths = ConfigLocations(default = ["/media/hdd/"])

	config.usage.movielist_trashcan = ConfigYesNo(default=True)
	config.usage.movielist_trashcan_days = ConfigNumber(default=8)
	config.usage.movielist_trashcan_reserve = ConfigNumber(default=40)
	config.usage.on_movie_start = ConfigSelection(default = "resume", choices = [
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
		("shutdown", _("immediate shutdown")) ] )

	config.usage.alternatives_priority = ConfigSelection(default = "0", choices = [
		("0", "DVB-S/-C/-T"),
		("1", "DVB-S/-T/-C"),
		("2", "DVB-C/-S/-T"),
		("3", "DVB-C/-T/-S"),
		("4", "DVB-T/-C/-S"),
		("5", "DVB-T/-S/-C") ])

	nims = []
	nims.append(("-1", _("auto")))
	for x in nimmanager.nim_slots:
		nims.append((str(x.slot), x.getSlotName()))
	config.usage.frontend_priority = ConfigSelection(default = "-1", choices = nims)
	config.misc.disable_background_scan = ConfigYesNo(default = False)

	config.usage.blinking_display_clock_during_recording = ConfigYesNo(default = False)

	config.usage.show_message_when_recording_starts = ConfigYesNo(default = True)

	config.usage.load_length_of_movies_in_moviellist = ConfigYesNo(default = True)
	config.usage.show_icons_in_movielist = ConfigYesNo(default = True)

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
	config.usage.show_cryptoinfo = ConfigYesNo(default = True)
	config.usage.show_eit_nownext = ConfigYesNo(default = True)

	config.epg = ConfigSubsection()
	config.epg.eit = ConfigYesNo(default = True)
	config.epg.mhw = ConfigYesNo(default = False)
	config.epg.freesat = ConfigYesNo(default = True)
	config.epg.viasat = ConfigYesNo(default = True)
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
		eEPGCache.getInstance().setEpgSources(mask)
	config.epg.eit.addNotifier(EpgSettingsChanged)
	config.epg.mhw.addNotifier(EpgSettingsChanged)
	config.epg.freesat.addNotifier(EpgSettingsChanged)
	config.epg.viasat.addNotifier(EpgSettingsChanged)

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

	config.usage.keymap = ConfigText(default = "/usr/share/enigma2/keymap.xml")

	config.seek = ConfigSubsection()
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
	config.subtitles = ConfigSubsection()
	config.subtitles.ttx_subtitle_colors = ConfigYesNo(default = False)
	config.subtitles.ttx_subtitle_original_position = ConfigYesNo(default = False)
	config.subtitles.subtitle_position = ConfigSelection(
		choices =
			[("0", "0"),
			("10", "10"),
			("20", "20"),
			("30", "30"),
			("40", "40"),
			("50", "50"),
			("60", "60"),
			("70", "70"),
			("80", "80"),
			("90", "90"),
			("100", "100"),
			("150", "150"),
			("200", "200"),
			("250", "250"),
			("300", "300"),
			("350", "350"),
			("400", "400"),
			("450", "450")],
		default = "50")
	config.subtitles.subtitle_alignment = ConfigSelection(
		choices =
			[("left", "left"),
			("center", "center"),
			("right", "right")],
		default = "center")
	config.subtitles.subtitle_rewrap = ConfigYesNo(default = False)
	config.subtitles.subtitle_borderwidth = ConfigSelection(
		choices =
			[("1", "1"),
			("2", "2"),
			("3", "3")],
		default = "2")
	
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

