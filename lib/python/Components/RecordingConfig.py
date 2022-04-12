from __future__ import absolute_import
from Components.config import ConfigInteger, ConfigSelectionNumber, ConfigYesNo, ConfigSubsection, ConfigSelection, config
from enigma import pNavigation
from Components.SystemInfo import BoxInfo


def InitRecordingConfig():
	config.recording = ConfigSubsection()
	# actually this is "recordings always have priority". "Yes" does mean: don't ask. The RecordTimer will ask when value is 0.
	config.recording.asktozap = ConfigYesNo(default=True)
	config.recording.margin_before = ConfigSelectionNumber(min=0, max=120, stepwidth=1, default=3, wraparound=True)
	config.recording.margin_after = ConfigSelectionNumber(min=0, max=120, stepwidth=1, default=5, wraparound=True)
	config.recording.ascii_filenames = ConfigYesNo(default=False)
	config.recording.keep_timers = ConfigSelectionNumber(min=1, max=120, stepwidth=1, default=7, wraparound=True)
	config.recording.filename_composition = ConfigSelection(default="standard", choices=[
		("standard", _("standard")),
		("veryveryshort", _("Very very short filenames - Warning")),
		("veryshort", _("Very short filenames")),
		("shortwithtime", _("Short filenames with time")),
		("short", _("Short filenames")),
		("long", _("Long filenames"))])
	config.recording.always_ecm = ConfigYesNo(default=False)
	config.recording.never_decrypt = ConfigYesNo(default=False)
	config.recording.offline_decode_delay = ConfigInteger(default=1000, limits=(1, 10000))
	config.recording.ecm_data = ConfigSelection(choices=[("normal", _("Normal")), ("descrambled+ecm", _("Descramble and record ecm")), ("scrambled+ecm", _("Don't descramble, record ecm"))], default="normal")
	config.recording.default_timertype = ConfigSelection(choices=[("zap", _("Zap")), ("record", _("Record")), ("zap+record", _("Zap and record"))], default="record")
	if BoxInfo.getItem("DeepstandbySupport"):
		shutdownString = _("Go to deep standby")
	else:
		shutdownString = _("Shut down")
	config.recording.default_afterevent = ConfigSelection(choices=[("0", _("Do nothing")), ("1", _("Go to standby")), ("2", shutdownString), ("3", _("auto"))], default="3")
	config.recording.include_ait = ConfigYesNo(default=False)
	config.recording.show_rec_symbol_for_rec_types = ConfigSelection(choices=[("any", _("any recordings")), ("real", _("real recordings")), ("real_streaming", _("real recordings or streaming")), ("real_pseudo", _("real or pseudo recordings"))], default="real_streaming")
	config.recording.warn_box_restart_rec_types = ConfigSelection(choices=[("any", _("any recordings")), ("real", _("real recordings")), ("real_streaming", _("real recordings or streaming")), ("real_pseudo", _("real or pseudo recordings"))], default="real_streaming")
	config.recording.ask_to_abort_pseudo_rec = ConfigSelection(choices=[("ask", _("ask user")), ("abort_no_msg", _("just abort, no message")), ("abort_msg", _("just abort, show message")), ("never_abort", _("never abort"))], default="abort_msg")
	config.recording.ask_to_abort_streaming = ConfigSelection(choices=[("ask", _("ask user")), ("abort_no_msg", _("just abort, no message")), ("abort_msg", _("just abort, show message")), ("never_abort", _("never abort"))], default="abort_msg")
	config.recording.ask_to_abort_pip = ConfigSelection(choices=[("ask", _("ask user")), ("abort_no_msg", _("just abort, no message")), ("abort_msg", _("just abort, show message")), ("never_abort", _("never abort"))], default="abort_msg")
	config.recording.prepare_time = ConfigSelectionNumber(min=20, max=120, stepwidth=10, default=20, wraparound=True)


def recType(configString):
	if (configString == "any"):
		return pNavigation.isAnyRecording
	elif (configString == "real"):
		return pNavigation.isRealRecording
	elif (configString == "real_streaming"):
		return pNavigation.isRealRecording | pNavigation.isStreaming
	elif (configString == "real_pseudo"):
		return pNavigation.isRealRecording | pNavigation.isPseudoRecording
