from config import ConfigNumber, ConfigYesNo, ConfigSubsection, ConfigSelection, config

def InitRecordingConfig():
	config.recording = ConfigSubsection();
	# actually this is "recordings always have priority". "Yes" does mean: don't ask. The RecordTimer will ask when value is 0.
	config.recording.asktozap = ConfigYesNo(default=True)
	config.recording.margin_before = ConfigNumber(default=3)
	config.recording.margin_after = ConfigNumber(default=5)
	config.recording.debug = ConfigYesNo(default = False)
	config.recording.ascii_filenames = ConfigYesNo(default = False)
	config.recording.keep_timers = ConfigNumber(default=7)
	config.recording.filename_composition = ConfigSelection(default = "standard", choices = [
		("standard", _("standard")),
		("veryshort", _("Very short filenames")),
		("short", _("Short filenames")),
		("long", _("Long filenames")) ] )
	config.recording.always_ecm = ConfigYesNo(default = False)
	config.recording.never_decrypt = ConfigYesNo(default = False)
	config.recording.offline_decode_delay = ConfigNumber(default = 1000)
	config.recording.ecm_data = ConfigSelection(choices = [("normal", _("normal")), ("descrambled+ecm", _("descramble and record ecm")), ("scrambled+ecm", _("don't descramble, record ecm"))], default = "normal")
	config.recording.include_ait = ConfigYesNo(default = False)
