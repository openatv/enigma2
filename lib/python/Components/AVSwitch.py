from config import *
import os
from enigma import *

class AVSwitch:
	INPUT = { "ENCODER": 0, "SCART": 1, "AUX": 2 }
	def __init__(self):
		pass

	def setColorFormat(self, value):
		eAVSwitch.getInstance().setColorFormat(value)
		
	def setAspectRatio(self, value):
		eAVSwitch.getInstance().setAspectRatio(value)
		self.checkWSS()

	def setSystem(self, value):
		eAVSwitch.getInstance().setVideomode(value)
		
	def checkWSS(self):
		if currentConfigSelectionElement(config.av.aspectratio) == "4_3_letterbox" or currentConfigSelectionElement(config.av.aspectratio) == "4_3_panscan":
			writevalue = "4:3_full_format"
		elif currentConfigSelectionElement(config.av.aspectratio) == "16_9":
			if currentConfigSelectionElement(config.av.wss) == "off":
				writevalue = "auto(4:3_off)"
			else:
				writevalue = "auto"
		elif currentConfigSelectionElement(config.av.aspectratio) == "16_9_always":
			writevalue = "16:9_full_format"
		try:
			file = open("/proc/stb/denc/0/wss", "w")
			file.write(writevalue)
			file.close()
		except:
			print "[AVSwitch.py] Error writing to /proc/stb/denc/0/wss"

	def setWSS(self, value = None):
		self.checkWSS()
	
	def setInput(self, input):
		eAVSwitch.getInstance().setInput(self.INPUT[input])
		# FIXME why do we have to reset the colorformat? bug in avs-driver?
		eAVSwitch.getInstance().setColorFormat(config.av.colorformat.value)

def InitAVSwitch():
	config.av = ConfigSubsection();
	config.av.colorformat = configElement("config.av.colorformat", configSelection, 1, (("cvbs", _("CVBS")), ("rgb", _("RGB")), ("svideo", _("S-Video")) ))
	config.av.aspectratio = configElement("config.av.aspectratio", configSelection, 0, (("4_3_letterbox", _("4:3 Letterbox")), ("4_3_panscan", _("4:3 PanScan")), ("16_9", _("16:9")), ("16_9_always", _("16:9 always"))) )
	#config.av.tvsystem = configElement("config.av.tvsystem", configSelection, 0, ("PAL", "PAL + PAL60", "Multi", "NTSC") )
	config.av.tvsystem = configElement("config.av.tvsystem", configSelection, 0, (("pal", _("PAL")), ("ntsc", _("NTSC"))) )
	config.av.wss = configElement("config.av.wss", configSelection, 0, (("off", _("Off")), ("on", _("On"))) )
	config.av.defaultac3 = configElement("config.av.defaultac3", configSelection, 1, (("enable", _("Enable")), ("disable", _("Disable"))))
	config.av.vcrswitch = configElement("config.av.vcrswitch", configSelection, 1, (("enable", _("Enable")), ("disable", _("Disable"))))

	iAVSwitch = AVSwitch()

	def setColorFormat(configElement):
		iAVSwitch.setColorFormat(configElement.value)
	def setAspectRatio(configElement):
		iAVSwitch.setAspectRatio(configElement.value)
	def setSystem(configElement):
		iAVSwitch.setSystem(configElement.value)
	def setWSS(configElement):
		iAVSwitch.setWSS(configElement.value)

	# this will call the "setup-val" initial
	config.av.colorformat.addNotifier(setColorFormat)
	config.av.aspectratio.addNotifier(setAspectRatio)
	config.av.tvsystem.addNotifier(setSystem)
	config.av.wss.addNotifier(setWSS)
	
	iAVSwitch.setInput("ENCODER") # init on startup