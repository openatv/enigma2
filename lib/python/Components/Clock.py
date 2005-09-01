from HTMLComponent import *
from GUIComponent import *
from VariableText import *

#from enigma import eTimer
#from enigma import eLabel

from enigma import *

import time
# now some "real" components:

class Clock(HTMLComponent, GUIComponent, VariableText):
	def __init__(self):
		VariableText.__init__(self)
		GUIComponent.__init__(self)
		self.doClock()
		
		self.clockTimer = eTimer()
		self.clockTimer.timeout.get().append(self.doClock)
		self.clockTimer.start(1000)

# "funktionalitaet"	
	def doClock(self):
		t = time.localtime()
		#HACK use timezone settings
		timestr = "%2d:%02d:%02d" % (t[3] + 2, t[4], t[5])
		self.setText(timestr)
		setLCDClock(timestr)

# realisierung als GUI
	def createWidget(self, parent):
		return eLabel(parent)

	def removeWidget(self, w):
		del self.clockTimer

# ...und als HTML:
	def produceHTML(self):
		return self.getText()
		
