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
components["$002"] = screens["clockDisplay"](components["clock"])

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

def runScreenTest():
	desktop = getDesktop()

	wnd = eWindow(desktop)
	mainwnd = wnd
	wnd.setTitle("Screen from python!")
	wnd.move(ePoint(300, 100))
	wnd.resize(eSize(300, 300))

	gui = GUIOutputDevice()
	gui.parent = wnd
	gui.create(components["$002"])

	applyGUIskin(components["$002"], None, "clockDialog")

	wnd.show()
	
#	components["$002"].data["okbutton"]["instance"].push()
	runMainloop()
	
	return 0


# first, setup a screen
runScreenTest()

# now, run the mainloop
