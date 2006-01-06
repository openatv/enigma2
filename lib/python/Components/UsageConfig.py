from config import *
import os
from enigma import *

def InitUsageConfig():
	config.usage = ConfigSubsection();
	config.usage.epgtoggle = configElement("config.usage.epgtoggle", configSelection, 1, (("yes", _("yes")), ("no", _("no"))) );