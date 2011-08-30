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
		
		abouttxt = """andy-1 (manager)
Babsy98 (developer & coder)
Black64 (developer & coder)		
obiwatn76 (developer & coder)
neipe (quality)
janojano (translator)
rangerm (Plugins)
matze70(Settings Chief)
XuP (designer)
husky (betaster)
Kleanthis (betatester)"""
		
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
