from config import *
import os
from enigma import *

def InitUsageConfig():
	config.usage = ConfigSubsection();
	config.usage.showdish = configElement("config.usage.showdish", configSelection, 1, (("yes", _("yes")), ("no", _("no"))) )
	config.usage.multibouquet = configElement("config.usage.multibouquet", configSelection, 1, (("yes", _("yes")), ("no", _("no"))) )

