from config import ConfigInteger, ConfigYesNo, ConfigSubsection, config
import os

def InitRecordingConfig():
	config.recording = ConfigSubsection();
	# actually this is "recordings always have priority". "Yes" does mean: don't ask. The RecordTimer will ask when value is 0.
	config.recording.asktozap = ConfigYesNo(default=True)
	config.recording.margin_before = ConfigInteger(default=0, limits=(0,30))
	config.recording.margin_after = ConfigInteger(default=0, limits=(0,30))
