from config import ConfigNumber, ConfigYesNo, ConfigSubsection, ConfigSelection, config

def InitRecordingConfig():
	config.recording = ConfigSubsection();
	# actually this is "recordings always have priority". "Yes" does mean: don't ask. The RecordTimer will ask when value is 0.
	config.recording.asktozap = ConfigYesNo(default=True)
	config.recording.margin_before = ConfigNumber(default=0)
	config.recording.margin_after = ConfigNumber(default=0)
	config.recording.debug = ConfigYesNo(default = False)
	config.recording.ascii_filenames = ConfigYesNo(default = False)
	config.recording.filename_composition = ConfigSelection(default = "standard", choices = [
		("standard", _("standard")),
		("short", _("Short filenames")),
		("long", _("Long filenames")) ] )