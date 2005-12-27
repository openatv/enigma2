from enigma import *
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.Label import Label

import os

class Example(Screen):
	skin = """
		<screen position="100,100" size="550,400" title="IPKG upgrade..." >
			<widget name="text" position="0,0" size="550,400" font="Regular;15" />
		</screen>"""
		
	def __init__(self, session):
		self.skin = Example.skin
		Screen.__init__(self, session)

		self["text"] = Label("Please press OK!")
				
		self["actions"] = ActionMap(["WizardActions"], 
		{
			"ok": self.ok,
			"back": self.close
		}, -1)
		
	def ok(self):
		self.session.openWithCallback(self.doUpdate, MessageBox, _("Do you want to update your Dreambox?\nAfter pressing OK, please wait!"))
		
	def doUpdate(self, val = False):
		
		if val:
			lines = os.popen("ipkg update && ipkg upgrade", "r").readlines()
			string = ""
			for x in lines:
				string += x
			self["text"].setText("Updating finished. Here is the result:\n\n" + string)
		else:
			self.close()		
		
		
def main(session):
	session.open(Example)
	

def getPicturePath():
		return ""

def getPluginName():
		return "Softwareupdate"