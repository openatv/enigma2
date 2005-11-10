from config import *
import os
from enigma import *

class AVSwitch:
	def __init__(self):
		pass

	def setColorFormat(self, value):
		#print "colorformat:" + str(value)
		eAVSwitch.getInstance().setColorFormat(value)
		
	def setAspectRatio(self, value):
		#print "aspectratio:" + str(value)
		eAVSwitch.getInstance().setAspectRatio(value)

	def setSystem(self, value):
		print "system:" + str(value)
		eAVSwitch.getInstance().setVideomode(value)

	def setWSS(self, value):
		#print "wss:" + str(value)
		pass

def InitAVSwitch():
	config.av = ConfigSubsection();
	config.av.colorformat = configElement("config.av.colorformat", configSelection, 1, ("CVBS", "RGB", "S-Video") );
	config.av.aspectratio = configElement("config.av.aspectratio", configSelection, 0, ("4:3 Letterbox", "4:3 PanScan", "16:9", "16:9 always") );
	config.av.tvsystem = configElement("config.av.tvsystem", configSelection, 0, ("PAL", "PAL + PAL60", "Multi", "NTSC") );
	config.av.wss = configElement("config.av.wss", configSelection, 0, ("Enable", "Disable") );
	config.av.defaultac3 = configElement("config.av.defaultac3", configSelection, 1, ("Enable", "Disable") );
	config.av.vcrswitch = configElement("config.av.vcrswitch", configSelection, 0, ("Enable", "Disable") );

	iAVSwitch = AVSwitch()

	def setColorFormat(configElement):
		iAVSwitch.setColorFormat(configElement.value);
	def setAspectRatio(configElement):
		iAVSwitch.setAspectRatio(configElement.value);
	def setSystem(configElement):
		iAVSwitch.setSystem(configElement.value);
	def setWSS(configElement):
		iAVSwitch.setWSS(configElement.value);

	# this will call the "setup-val" initial
	config.av.colorformat.addNotifier(setColorFormat);
	config.av.aspectratio.addNotifier(setAspectRatio);
	config.av.tvsystem.addNotifier(setSystem);
	config.av.wss.addNotifier(setWSS);

