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
		print "test dialog clicked!"
		self["title"].setText("bla")

	def __init__(self):
		HTMLSkin.__init__(self, ("title", "okbutton"))
		b = Button("ok")
		b.onClick = [ self.testDialogClick ]
		self["okbutton"] = b
		self["title"] = Header("Test Dialog - press ok to leave!")

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

