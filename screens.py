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
	
# a test dialog
class testDialog(Screen):
	def testDialogClick(self):
		selection = self["menu"].getCurrent()
		selection[1]()
	
	def goMain(self):
#		self.close(0)
		self["title"].setText("you selected the main menu!");
		
	def goEmu(self):
#		self.close(1)
		self["title"].setText("EMUs ARE ILLEGAL AND NOT SUPPORTED!");
	
	def goTimeshift(self):
#		self.close(2)
		self["title"].setText("JUST PRESS THE YELLOW BUTTON!");
	
	def goHDTV(self):
#		self.close(3)
		self["title"].setText("HDTV GREEN FLASHES: ENABLED");

	def __init__(self):
		GUISkin.__init__(self)
		b = Button("ok")
		b.onClick = [ self.testDialogClick ]
		self["okbutton"] = b
		self["title"] = Header("Test Dialog - press ok to leave!")
		self["menu"] = MenuList(
			[
				("MAIN MENU", self.goMain), 
				("EMU SETUP", self.goEmu),
				("TIMESHIFT SETUP", self.goTimeshift),
				("HDTV PIP CONFIG", self.goHDTV)
			])


class MainMenu(Screen):
	def __init__(self):
		GUISkin.__init__(self)
		
		self["ok"] = Button("ok")
		self["ok"].onClick = [ self.close ]

	
# a clock display dialog
class clockDisplay(Screen):
	def okbutton(self):
		print "clockDisplay close"
		
		self.session.close()
	
	def __init__(self, clock):
		GUISkin.__init__(self)
		self["theClock"] = clock
		b = Button("bye")
		b.onClick = [ self.okbutton ]
		self["okbutton"] = b
		self["title"] = Header("clock dialog: here you see the current uhrzeit!")

# defined screens
screens = {
	"global": doGlobal,
	"testDialog": testDialog,
	"clockDisplay": clockDisplay }

