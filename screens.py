from components import *
import sys

# some screens
def doGlobal(screen):
	screen["clock"] = Clock()

class Screen(dict, HTMLSkin, GUISkin):
	""" bla """
	
	def close(self):
		GUISkin.close(self)
	
# a test dialog
class testDialog(Screen):
	def testDialogClick(self):
		self["title"].setText(self["menu"].getCurrent())

		self.tries += 1

	def __init__(self):
		GUISkin.__init__(self)
		b = Button("ok")
		b.onClick = [ self.testDialogClick ]
		self["okbutton"] = b
		self["title"] = Header("Test Dialog - press ok to leave!")
		self["menu"] = MenuList()
		
		self.tries = 0

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

