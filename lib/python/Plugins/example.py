from enigma import *
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox

from Components.ActionMap import ActionMap
from Components.Label import Label

class Example(Screen):
	skin = """
		<screen position="100,100" size="200,200" title="Example plugin..." >
			<widget name="text" position="0,0" size="100,50" font="Regular;23" />
		</screen>"""
		
	def __init__(self, session):
		self.skin = Example.skin
		Screen.__init__(self, session)

		self["text"] = Label("Big test")

		self["actions"] = ActionMap(["WizardActions"], 
		{
			"ok": self.ok,
			"back": self.close
		}, -1)
		
	def ok(self):
		self.session.open(MessageBox, "Bla bla bla bla bla bla bla bla\n bla bla bla bla bla bla\n bla bla bla bla bla bla\n bla bla bla bla bla", MessageBox.TYPE_YESNO)
				
def main(session):
	session.open(Example)
	

def getPicturePath():
		return "/usr/share/enigma2/record.png"

def getPluginName():
		return "Fancy example-plugin"