from config import *
import os
from enigma import *

def InitRecordingConfig():
	config.recording = ConfigSubsection();
	# actually this is "recordings always have priority". "Yes" does mean: don't ask. The RecordTimer will ask when value is 0.
	config.recording.asktozap = configElement("config.recording.asktozap", configSelection, 1, (("no", _("no")), ("yes", _("yes"))) )
	config.recording.margin_before = configElement("config.recording.margin_before", configSequence, [0], configsequencearg.get("INTEGER", (0, 30)))
	config.recording.margin_after = configElement("config.recording.margin_after", configSequence, [0], configsequencearg.get("INTEGER", (0, 30)))
