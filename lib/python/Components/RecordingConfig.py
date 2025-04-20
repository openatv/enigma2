from time import localtime, mktime
from enigma import pNavigation

from Components.config import ConfigClock, ConfigInteger, ConfigSelection, ConfigSubsection, ConfigYesNo, config
from Components.SystemInfo import BoxInfo


def calculateTime(hours, minutes, day_offset=0):
    cur_time = localtime()
    unix_time = mktime((cur_time.tm_year, cur_time.tm_mon, cur_time.tm_mday, hours, minutes, 0, cur_time.tm_wday, cur_time.tm_yday, cur_time.tm_isdst)) + day_offset
    return unix_time


def InitRecordingConfig():
	if hasattr(config, "recording"):
		return
	config.recording = ConfigSubsection()
	config.recording.asktozap = ConfigYesNo(default=True)  # Actually this is "recordings always have priority" where 'Yes' does mean don't ask. The RecordTimer will ask when value is 0.
	choices = [(x, ngettext("%d Minute", "%d Minutes", x) % x) for x in range(121)]
	config.recording.margin_before = ConfigSelection(default=3, choices=choices)
	config.recording.margin_after = ConfigSelection(default=5, choices=choices)
	config.recording.zap_margin_before = ConfigSelection(default=0, choices=choices)
	config.recording.zap_margin_after = ConfigSelection(default=0, choices=choices)
	config.recording.zap_has_endtime = ConfigYesNo(default=False)
	config.recording.ascii_filenames = ConfigYesNo(default=False)
	config.recording.keep_timers = ConfigSelection(default=7, choices=[(x, ngettext("%d Day", "%d Days", x) % x) for x in range(1, 121)])
	config.recording.filename_composition = ConfigSelection(default="standard", choices=[
		("standard", _("Standard")),
		("veryveryshort", _("Very very short filenames - Warning")),
		("veryshort", _("Very short filenames")),
		("shortwithtime", _("Short filenames with time")),
		("short", _("Short filenames")),
		("long", _("Long filenames"))
	])
	config.recording.always_ecm = ConfigYesNo(default=False)
	config.recording.never_decrypt = ConfigYesNo(default=False)
	config.recording.offline_decode_delay = ConfigInteger(default=1000, limits=(1, 10000))
	config.recording.ecm_data = ConfigSelection(default="normal", choices=[
		("normal", _("Normal")),
		("descrambled+ecm", _("Unscramble and record ECM")),
		("scrambled+ecm", _("Don't unscramble, record ECM"))
	])
	config.recording.default_timertype = ConfigSelection(default="record", choices=[
		("zap", _("Zap")),
		("record", _("Record")),
		("zap+record", _("Zap and record"))
	])
	shutdownString = _("Go to deep standby") if BoxInfo.getItem("DeepstandbySupport") else _("Shut down")
	config.recording.default_afterevent = ConfigSelection(default="3", choices=[
		("0", _("Do nothing")),
		("1", _("Go to standby")),
		("2", shutdownString),
		("3", _("Auto"))
	])
	config.recording.include_ait = ConfigYesNo(default=False)
	choices = [
		("any", _("Any recordings")),
		("real", _("Real recordings")),
		("real_streaming", _("Real recordings or streaming")),
		("real_pseudo", _("Real or pseudo recordings"))
	]
	config.recording.show_rec_symbol_for_rec_types = ConfigSelection(default="real_streaming", choices=choices)
	config.recording.warn_box_restart_rec_types = ConfigSelection(default="real_streaming", choices=choices)
	choices = [
		("ask", _("Ask user")),
		("abort_no_msg", _("Just abort, no message")),
		("abort_msg", _("Just abort, show message")),
		("never_abort", _("Never abort"))
	]
	config.recording.ask_to_abort_pseudo_rec = ConfigSelection(default="abort_msg", choices=choices)
	config.recording.ask_to_abort_streaming = ConfigSelection(default="abort_msg", choices=choices)
	config.recording.ask_to_abort_pip = ConfigSelection(default="abort_msg", choices=choices)
	config.recording.prepare_time = ConfigSelection(default=20, choices=[(x, _("%d Seconds") % x) for x in range(20, 121, 10)])
	config.recording.timerviewshowfreespace = ConfigYesNo(default=True)

	if BoxInfo.getItem("CanDescrambleInStandby"):
		config.recording.standbyDescramble = ConfigYesNo(default=True)
		config.recording.standbyDescrambleShutdown = ConfigYesNo(default=True)
	else:
		config.recording.standbyDescramble = ConfigYesNo(default=False)
		config.recording.standbyDescrambleShutdown = ConfigYesNo(default=False)
	config.recording.standbyDescrambleStart = ConfigClock(default=calculateTime(0, 1))
	config.recording.standbyDescrambleEnd = ConfigClock(default=calculateTime(23, 59))


def recType(configString):
	return {
		"any": pNavigation.isAnyRecording,
		"real": pNavigation.isRealRecording,
		"real_streaming": pNavigation.isRealRecording | pNavigation.isStreaming,
		"real_pseudo": pNavigation.isRealRecording | pNavigation.isPseudoRecording
	}.get(configString)
