from enigma import *

import sys
import time

from screens import *
from skin import applyGUIskin

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

print "*** classes:"
dump(screens)

print "*** instances:"
dump(components)

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
	
	def processDelay(self):
		components[self.screenname].close()
		if self.currentWindow != None:
			self.currentWindow.hide()
		
		del components[self.screenname]
		del self.currentWindow
		

	def open(self, screenname, screen):
		components[screenname] = screen
		self.screenname = screenname
		screen.session = self
		
		if self.desktop != None:
			self.currentWindow = wnd = eWindow(self.desktop)
			wnd.setTitle("Screen from python!")
			wnd.move(ePoint(300, 100))
			wnd.resize(eSize(300, 300))

			gui = GUIOutputDevice()
			gui.parent = wnd
			gui.create(components["$002"])

		 	applyGUIskin(components["$002"], None, "clockDialog")

			wnd.show()
		else:
			self.currentWindow = None

	def close(self):
		self.delayTimer.start(0, 1)

def runScreenTest():
	session = Session()
	session.desktop = getDesktop()
	
#	components["$002"] = screens["clockDisplay"](components["clock"])

	session.open("$002", screens["clockDisplay"](components["clock"]))

	
	def blub():
#		x = components["$002"]
		components["$002"].data["okbutton"]["instance"].push()
#		dump(components)
#		print "session, close screen " + str(sys.getrefcount(x))
#		session.close()
		
	tmr = eTimer()
	tmr.timeout.get().append(blub)
	tmr.start(4000, 1)
	
	runMainloop()
	
	return 0


# first, setup a screen
runScreenTest()

# now, run the mainloop
