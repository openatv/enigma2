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



def test():
	desktop = getDesktop()
	print "desktop: " + str(desktop)

	wnd = eWindow(desktop)
	print "window " + str(wnd)
	wnd.setTitle("python")
	wnd.move(ePoint(300, 100))
	wnd.resize(eSize(300, 300))

	gui = GUIOutputDevice()
	gui.parent = wnd
	gui.create(components["$002"])
#	for (x,y) in components["$001"].data.items():
#		print str(x) + " -> " + str(y) + " (" + y["instance"].getText() + ")"

#	print components["$001"].data["okbutton"]["instance"].doClick()

# diese sachen gehoeren in den skin! :)
	applyGUIskin(components["$002"], None, "clockDialog")
	
# das ist dann schon die echte funktionalitaet ;)
	components["clock"].doClock()
	components["clock"].doClock()


# output as html
	print "--------------------------------------"
	html.create(components["$001"])
	print "--------------------------------------"
	html.create(components["$002"])
	print "--------------------------------------"
	
	
# direkter test der GUI aus python:
#	label1 = eLabel(wnd)
#	label1.setText("hello world!\nfrom python!")
#	label1.move(ePoint(10, 10))
#	label1.resize(eSize(80, 50))
#
#	label2 = eLabel(wnd)
#	label2.setText("the second\nlabel works\nas well!")
#	label2.move(ePoint(90, 10))
#	label2.resize(eSize(80, 50))
#
#	button = eButton(wnd)
#	button.setText("OK")
#	button.move(ePoint(200, 10))
#	button.resize(eSize(80, 50)) 

	wnd.show()
	
	components["$002"].data["okbutton"]["instance"].push()	

	for x in range(200):
		time.sleep(0.1)
		components["clock"].doClock()
		if x > 100:
			r = 200 - x
		else:
			r = x
#		components["$002"]["okbutton"].setValue(r)
		desktop.paint()
	
#	
#	print "delete label1"
#	del button
#	del label2
#	del label1
#	print "delete wnd"
#	del wnd
#	print "bye"

	
	
	return 0

def testI2(a):
	print "PYTHON says: it's a " + str(a) + "!!!"
	return 0

def testI(a = 0):
	print "magic integer is " + str(a)
	
	list = testsignal.get()
	print "list -> " + str(list)
	list.append(testI2)
	return 1
