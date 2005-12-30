from config import *
import os
from enigma import *

def InitRecordingConfig():
	config.recording = ConfigSubsection();
	config.recording.asktozap = configElement("config.recording.asktozap", configSelection, 1, (("yes", _("yes")), ("no", _("no"))) );


