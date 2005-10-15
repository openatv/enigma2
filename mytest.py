from enigma import *
from tools import *

import traceback
import Screens.InfoBar

import sys
import time

import ServiceReference

from Navigation import Navigation

from skin import readSkin, applyAllAttributes


# A screen is a function which instanciates all components of a screen into a temporary component.
# Thus, the global stuff is a screen, too.
# In a screen, components can either be instanciated from the class-tree, cloned (copied) or
# "linked" from the instance tree.
# A screen itself lives as the container of the components, so a screen is a component, too.

# we thus have one (static) hierarchy of screens (classes, not instances)
# and one with the instanciated components itself (both global and dynamic)

had = dict()

def dump(dir, p = ""):
	if isinstance(dir, dict):
		for (entry, val) in dir.items():
			dump(val, p + "(dict)/" + entry)
	if hasattr(dir, "__dict__"):
		for name, value in dir.__dict__.items():
			if not had.has_key(str(value)):
				had[str(value)] = 1
				dump(value, p + "/" + str(name))
			else:
				print p + "/" + str(name) + ":" + str(dir.__class__) + "(cycle)"
	else:
		print p + ":" + str(dir)

# + ":" + str(dir.__class__)

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
	def create(self, comp, desktop):
		comp.createGUIScreen(self.parent, desktop)

class Session:
	def __init__(self):
		self.desktop = None
		self.delayTimer = eTimer()
		self.delayTimer.timeout.get().append(self.processDelay)
		
		self.currentDialog = None
		
		self.dialogStack = [ ]
	
	def processDelay(self):
		self.execEnd()
		
		if self.currentDialog.isTmp:
			self.currentDialog.doClose()
		
			print sys.getrefcount(self.currentDialog)
			del self.currentDialog.instance
#			dump(self.currentDialog)
			del self.currentDialog
		
		self.popCurrent()
			
	def execBegin(self):
			self.currentDialog.execBegin()
			self.currentDialog.instance.show()
		
	def execEnd(self):
			self.currentDialog.execEnd()
			self.currentDialog.instance.hide()
	
	def create(self, screen, arguments):
		# creates an instance of 'screen' (which is a class)
		return screen(self, *arguments)
	
	def instantiateDialog(self, screen, *arguments):
		# create dialog
		
		try:
			dlg = self.create(screen, arguments)
		except:
			print 'EXCEPTION IN DIALOG INIT CODE, ABORTING:'
			print '-'*60
			traceback.print_exc(file=sys.stdout)
			quitMainloop()
			print '-'*60
		
		# read skin data
		readSkin(dlg, None, dlg.skinName, self.desktop)

		# create GUI view of this dialog
		assert self.desktop != None
		dlg.instance = eWindow(self.desktop)
		applyAllAttributes(dlg.instance, self.desktop, dlg.skinAttributes)
		gui = GUIOutputDevice()
		gui.parent = dlg.instance
		gui.create(dlg, self.desktop)
		
		return dlg
	 
	def pushCurrent(self):
		if self.currentDialog:
			self.dialogStack.append(self.currentDialog)
			self.execEnd()
	
	def popCurrent(self):
		if len(self.dialogStack):
			self.currentDialog = self.dialogStack.pop()
			self.execBegin()
	
	def execDialog(self, dialog):
		self.pushCurrent()
		self.currentDialog = dialog
		self.currentDialog.isTmp = False
		self.execBegin()

	def open(self, screen, *arguments):
		self.pushCurrent()
		self.currentDialog = self.instantiateDialog(screen, *arguments)
		self.currentDialog.isTmp = True
		self.execBegin()

	def keyEvent(self, code):
		print "code " + str(code)

	def close(self):
		self.delayTimer.start(0, 1)


def runScreenTest():
	session = Session()
	session.desktop = getDesktop()
	
	session.nav = Navigation()
	
	session.open(Screens.InfoBar.InfoBar)

	CONNECT(keyPressedSignal(), session.keyEvent)
	
	runMainloop()
	
	session.nav.shutdown()
	
	return 0

import keymapparser
keymapparser.readKeymap()
import skin
skin.loadSkin(getDesktop())

import Components.InputDevice
Components.InputDevice.InitInputDevices()

import Components.AVSwitch
Components.AVSwitch.InitAVSwitch()

import Components.Network
Components.Network.InitNetwork()

import Components.SetupDevices
Components.SetupDevices.InitSetupDevices()

import Components.NimManager

# first, setup a screen
try:
	runScreenTest()
except:
	print 'EXCEPTION IN PYTHON STARTUP CODE:'
	print '-'*60
	traceback.print_exc(file=sys.stdout)
	quitMainloop()
	print '-'*60

# now, run the mainloop

#pt = eDebugClassPtr()
#eDebugClass.getDebug(pt, 12)
#p = pt.__deref__()
#print pt.x
#print p.x
#print "removing ptr..."
#pt = 0
#print "now"
#print "p is " + str(p)
#print p.x
#p = 0
#
#bla = eDebugClass()
#bla = eDebugClass(2)
#

