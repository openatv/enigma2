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
		
	def __init__(self, session, args = None):
		self.skin = Example.skin
		Screen.__init__(self, session)

		self["text"] = Label(_("Please press OK!"))
				
		self["actions"] = ActionMap(["WizardActions"], 
		{
			"ok": self.go,
			"back": self.close
		}, -1)
		
		self.update = True
		self.delayTimer = eTimer()
		self.delayTimer.timeout.get().append(self.doUpdateDelay)
		
	def go(self):
		if self.update:
			self.session.openWithCallback(self.doUpdate, MessageBox, _("Do you want to update your Dreambox?\nAfter pressing OK, please wait!"))		
		else:
			self.close()
	
	def doUpdateDelay(self):
		lines = os.popen("ipkg update && ipkg upgrade", "r").readlines()
		string = ""
		for x in lines:
			string += x
		self["text"].setText(_("Updating finished. Here is the result:") + "\n\n" + string)
		self.update = False
			
	
	def doUpdate(self, val = False):
		if val == True:
			self["text"].setText(_("Updating... Please wait... This can take some minutes..."))
			self.delayTimer.start(0, 1)
		else:
			self.close()		
		
#def autostart():
	#print "**************************** AUTOSTART"
#
#def autoend():
	#print "**************************** AUTOEND"

def getPicturePaths():
	return ["update.png"]

def getPlugins():
	return [("Softwareupdate", "screen", "Example")]
	
def getMenuRegistrationList():
	list = []
	list.append(("setup", 2, "Softwareupdate", "Example"))
	return list