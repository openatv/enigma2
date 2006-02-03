from config import *
import os
from enigma import *

def InitRecordingConfig():
	config.recording = ConfigSubsection();
	config.recording.asktozap = configElement("config.recording.asktozap", configSelection, 1, (("yes", _("yes")), ("no", _("no"))) )
	config.recording.margin_before = configElement("config.recording.margin_before", configSequence, [0], configsequencearg.get("INTEGER", (0, 30)))
	config.recording.margin_after = configElement("config.recording.margin_after", configSequence, [0], configsequencearg.get("INTEGER", (0, 30)))
