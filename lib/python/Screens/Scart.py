from Screen import Screen
from MessageBox import MessageBox

from Components.AVSwitch import AVSwitch

from enigma import *

class Scart(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		
		self.avswitch = AVSwitch()
		
		self.avswitch.setInput("SCART")
		
		self.onShown.append(self.showMessageBox)
				
	def showMessageBox(self):
		self.session.openWithCallback(self.switchToTV, MessageBox, _("If you see this, something is wrong with\nyour scart connection. Press OK to return."), MessageBox.TYPE_ERROR)
		
	def switchToTV(self, val):
		self.avswitch.setInput("ENCODER")
		self.close()
