from HTMLComponent import HTMLComponent
from GUIComponent import GUIComponent
from VariableText import VariableText

from enigma import eTimer, eLabel

from time import localtime, strftime

# now some "real" components:

class Clock(VariableText, HTMLComponent, GUIComponent):
	def __init__(self):
		VariableText.__init__(self)
		GUIComponent.__init__(self)
		self.doClock()

		self.clockTimer = eTimer()
		self.clockTimer.callback.append(self.doClock)

	def onShow(self):
		self.doClock()
		self.clockTimer.start(1000)

	def onHide(self):
		self.clockTimer.stop()

	def doClock(self):
		self.setText(strftime("%T", localtime()))

	def createWidget(self, parent):
		return eLabel(parent)

	def removeWidget(self, w):
		del self.clockTimer

	def produceHTML(self):
		return self.getText()
