from HTMLComponent import *
from GUIComponent import *

from tools import CONNECT, DISCONNECT

from enigma import eInput, eInputContentString

class TextInput(HTMLComponent, GUIComponent):
	def __init__(self):
		GUIComponent.__init__(self)
		self.content = eInputContentString()

	def contentChanged(self):
		print "content changed to %s!" % (self.getText())
	
	def getText(self):
		return self.content.getText()
	
	def setText(self, text):
		# TODO :  support unicode!
		self.content.setText(str(text))
	
	def GUIcreate(self, parent, skindata):
		self.instance = eInput(parent)
		CONNECT(self.instance.changed, self.contentChanged)
		self.instance.setContent(self.content)
	
	def GUIdelete(self):
		DISCONNECT(self.instance.changed, self.contentChanged)
		self.instance.setContent(None)
		self.instance = None
