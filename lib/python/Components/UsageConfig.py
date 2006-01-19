from config import *
import os
from enigma import *

from Screens.ChannelSelection import USE_MULTIBOUQUETS
global USE_MULTIBOUQUETS

def InitUsageConfig():
	config.usage = ConfigSubsection();
	config.usage.epgtoggle = configElement("config.usage.epgtoggle", configSelection, 1, (("yes", _("yes")), ("no", _("no"))) )
	config.usage.showdish = configElement("config.usage.showdish", configSelection, 1, (("yes", _("yes")), ("no", _("no"))) )
	config.usage.multibouquet = configElement("config.usage.multibouquet", configSelection, 1, (("yes", _("yes")), ("no", _("no"))) )
	
	def setMultiBouquet(configElement):
		if currentConfigSelectionElement(configElement) == "no":
			USE_MULTIBOUQUETS = False
		else:
			USE_MULTIBOUQUETS = True
		
	config.usage.multibouquet.addNotifier(setMultiBouquet);