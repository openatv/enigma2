from enigma import *

import sys
import time

from screens import *
from skin import applyGUIskin


def CONNECT(slot, fnc):
	slot.get().append(fnc)

def DISCONNECT(slot, fnc):
	slot.get().remove(fnc)

# A screen is a function which instanciates all components of a screen into a temporary component.
# Thus, the global stuff is a screen, too.
# In a screen, components can either be instanciated from the class-tree, cloned (copied) or
# "linked" from the instance tree.
# A screen itself lives as the container of the components, so a screen is a component, too.

# we thus have one (static) hierarchy of screens (classes, not instances)
# and one with the instanciated components itself (both global and dynamic)

def dump(dir, p = ""):
	if isinstance(dir, dict):
		for (entry, val) in dir.items():
			dump(val, p + "/" + entry)
	print p + ":" + str(dir.__class__)

# defined components
components = {}

# do global
screens["global"](components)

# test our screens
components["$001"] = screens["testDialog"]()

#print "*** classes:"
#dump(screens)
#
#print "*** instances:"
#dump(components)

# display

class OutputDevice:
	def create(self, screen): pass

# display: HTML

class HTMLOutputDevice(OutputDevice):
	def create(self, comp):
		print comp.produceHTML()

html = HTMLOutputDevice()

class GUIOutputDevice(OutputDevice):
	parent = None
	def create(self, comp):
		comp.createGUIScreen(self.parent)

class Session:
	def __init__(self):
		self.desktop = None
		self.delayTimer = eTimer()
		self.delayTimer.timeout.get().append(self.processDelay)
		
		self.currentDialog = None
	
	def processDelay(self):
		self.currentDialog.close()
		if self.currentWindow != None:
			self.currentWindow.hide()
		
		del self.currentDialog
		del self.currentWindow
		
		self.open(screens["testDialog"]())

	def open(self, screen):
		self.currentDialog = screen
		screen.session = self
		
		if self.desktop != None:
			self.currentWindow = wnd = eWindow(self.desktop)
			wnd.setTitle("Screen from python!")
			wnd.move(ePoint(300, 100))
			wnd.resize(eSize(300, 300))

			gui = GUIOutputDevice()
			gui.parent = wnd
			gui.create(self.currentDialog)

		 	applyGUIskin(self.currentDialog, None, screen.__class__.__name__)

			wnd.show()
		else:
			self.currentWindow = None

	def keyEvent(self, code):
#		print "code " + str(code)
		if code == 32:
			self.currentDialog.data["okbutton"]["instance"].push()
		
		if code >= 0x30 and code <= 0x39:
			self.currentDialog.data["menu"]["instance"].moveSelection(code - 0x31)

	def close(self):
		self.delayTimer.start(0, 1)

def runScreenTest():
	session = Session()
	session.desktop = getDesktop()
	
	session.open(screens["clockDisplay"](components["clock"]))
#	session.open(screens["testDialog"]())

	# simple reason for this helper function: we want to call the currently
	# active "okbutton", even when we changed the dialog
	#
	# more complicated reason: we don't want to hold a reference.
#	def blub():
#		session.currentDialog.data["okbutton"]["instance"].push()	
#		session.currentDialog["okbutton"].setText("hello!")
#	
#	tmr = eTimer()
#	CONNECT(tmr.timeout, blub)
#	tmr.start(4000, 0)
#	
	CONNECT(keyPressedSignal(), session.keyEvent)
	
	runMainloop()
	
	return 0


# first, setup a screen
runScreenTest()

# now, run the mainloop
