from enigma import *
from Screens.Screen import Screen
from Components.Button import Button
from Components.Label import Label
from Components.ActionMap import ActionMap

class AboutTeam(Screen):
	skin = """
        <screen name="AboutTeam" position="center,center" size="660,460" title="About">
                <widget name="about" font="Regular;21" position="40,5" size="660,440"/>
        </screen>"""
		
	def __init__(self, session, args = 0):
		Screen.__init__(self, session)
		
		abouttxt = """
special thanks to
babsy98
black 64
andy-1
obi
AAF BETA Team
openembedded team
openVIX team
openPLI team
opendreambox team
opensif team
coolman
kerni

and all plugin Developers 
for the great job"""
		
		self["about"] = Label(abouttxt)
		self["key_green"] = Button("")
		self["key_red"] = Button("")
		self["key_blue"] = Button(_("Exit"))
		self["key_yellow"] = Button("")
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"],
		{
			"blue": self.quit,
			"cancel": self.quit,
		}, -2)
		
	def quit(self):
		self.close()
