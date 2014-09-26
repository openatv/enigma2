from config import ConfigSelectionNumber, ConfigYesNo, ConfigSubsection, ConfigSelection, config

def InitRecordingConfig():
	config.recording = ConfigSubsection()
	# actually this is "recordings always have priority". "Yes" does mean: don't ask. The RecordTimer will ask when value is 0.
	config.recording.asktozap = ConfigYesNo(default=True)
	config.recording.margin_before = ConfigSelectionNumber(min = 0, max = 120, stepwidth = 1, default = 3, wraparound = True)
	config.recording.margin_after = ConfigSelectionNumber(min = 0, max = 120, stepwidth = 1, default = 5, wraparound = True)
	config.recording.ascii_filenames = ConfigYesNo(default = False)
	config.recording.keep_timers = ConfigSelectionNumber(min = 1, max = 120, stepwidth = 1, default = 7, wraparound = True)
	config.recording.filename_composition = ConfigSelection(default = "standard", choices = [
		("standard", _("standard")),
		("veryveryshort", _("Very very short filenames - Warning")),
		("veryshort", _("Very short filenames")),
		("short", _("Short filenames")),
		("long", _("Long filenames")) ] )
	config.recording.offline_decode_delay = ConfigSelectionNumber(min = 1, max = 10000, stepwidth = 10, default = 1000, wraparound = True)
	config.recording.ecm_data = ConfigSelection(choices = [("normal", _("normal")), ("descrambled+ecm", _("descramble and record ecm")), ("scrambled+ecm", _("don't descramble, record ecm"))], default = "normal")
