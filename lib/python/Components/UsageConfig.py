from config import *
import os
from enigma import *

def InitUsageConfig():
	config.usage = ConfigSubsection();
	config.usage.showdish = configElement("config.usage.showdish", configSelection, 1, (("yes", _("yes")), ("no", _("no"))) )
	config.usage.multibouquet = configElement("config.usage.multibouquet", configSelection, 1, (("yes", _("yes")), ("no", _("no"))) )
	config.usage.quickzap_bouquet_change = configElement("config.usage.quickzap_bouquet_change", configSelection, 1, (("yes", _("yes")), ("no", _("no"))) )
	config.usage.e1like_radio_mode = configElement("config.usage.e1like_radio_mode", configSelection, 1, (("yes", _("yes")), ("no", _("no"))) )
