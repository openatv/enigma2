from components import *
import sys

# some screens
def doGlobal(screen):
	screen["clock"] = Clock()

class Screen(dict, HTMLSkin, GUISkin):
	""" bla """
	
	# never call this directly - it will be called from the session!
	def doClose(self):
		GUISkin.close(self)
	
	def close(self, retval=None):
		self.session.close()
	
class mainMenu(Screen):
	
	def goEmu(self):
		self["title"].setText("EMUs ARE ILLEGAL AND NOT SUPPORTED!")
	
	def goTimeshift(self):
		self["title"].setText("JUST PRESS THE YELLOW BUTTON!")
	
	def goHDTV(self):
		self["title"].setText("HDTV GREEN FLASHES: ENABLED")
	
	def goClock(self):
		self.session.open(clockDisplay(Clock()))

	def okbuttonClick(self):
		selection = self["menu"].getCurrent()
		selection[1]()

	def __init__(self):
		GUISkin.__init__(self)
		b = Button("ok")

		b.onClick = [ self.okbuttonClick ]
		self["okbutton"] = b
		self["title"] = Header("Main Menu! - press ok to leave!")
		self["menu"] = MenuList(
			[
				("EMU SETUP", self.goEmu),
				("TIMESHIFT SETUP", self.goTimeshift),
				("HDTV PIP CONFIG", self.goHDTV),
				("wie spaet ists?!", self.goClock)
			])

#class mainMenu(Screen):
#	def __init__(self):
#		GUISkin.__init__(self)
#		
#		self["title"] = Header("this is the\nMAIN MENU !!!");
#		self["okbutton"] = Button("ok")
#		self["okbutton"].onClick = [ self.close ]

class channelSelection(Screen):
	def __init__(self):
		GUISkin.__init__(self)
		
		self["list"] = ServiceList()
		self["list"].setRoot(eServiceReference("1:0:1:0:0:0:0:0:0:0:PREMIERE"))
		
		self["okbutton"] = Button("ok", [self.channelSelected, self.close])

	def channelSelected(self):
#		print "channel selected!"
		pass

class infoBar(Screen):
	def __init__(self):
		GUISkin.__init__(self)
		
		self["channelSwitcher"] = Button("switch Channel", [self.switchChannel])
		self["okbutton"] = Button("mainMenu", [self.mainMenu])
	
	def mainMenu(self):
		self.session.open(mainMenu())
		
	def switchChannel(self):
		self.session.open(channelSelection())

# a clock display dialog
class clockDisplay(Screen):
	def okbutton(self):
		self.session.close()
	
	def __init__(self, clock):
		GUISkin.__init__(self)
		self["theClock"] = clock
		b = Button("bye")
		b.onClick = [ self.okbutton ]
		self["okbutton"] = b
		self["title"] = Header("clock dialog: here you see the current uhrzeit!")

