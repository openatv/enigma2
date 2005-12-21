from enigma import *
from Screens.Screen import Screen
from Components.ActionMap import ActionMap
from Components.Label import Label

class Example(Screen):
	skin = """
		<screen position="100,100" size="200,200" title="Example plugin..." >
			<widget name="text" position="0,0" size="100,50" font="Arial;23" />
		</screen>"""
		
	def __init__(self, session):
		self.skin = Example.skin
		Screen.__init__(self, session)

		self["text"] = Label("Small test")

		self["actions"] = ActionMap(["WizardActions"], 
		{
			"ok": self.ok
		}, -1)
		
	def ok(self):
		self.close()
		
def main(session):
	session.open(Example)
	

def getPicturePath():
		return "/usr/share/enigma2/record.png"

def getPluginName():
		return "Fancy example-plugin"