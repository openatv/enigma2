from enigma import *
from tools import *


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
doGlobal(components)

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
		
		self.dialogStack = [ ]
	
	def processDelay(self):
		self.execEnd()
		self.currentDialog.doClose()
		
		del self.currentDialog
		del self.currentWindow
		
		if len(self.dialogStack):
			(self.currentDialog, self.currentWindow) = self.dialogStack.pop()
			self.execBegin()
			
	def execBegin(self):
			self.currentDialog.execBegin()
			self.currentWindow.show()
		
	def execEnd(self):
			self.currentDialog.execEnd()
			self.currentWindow.hide()
	
	def create(self, screen, arguments):
		return screen(self, *arguments)
	
	def open(self, screen, *arguments):
		if self.currentDialog:
			self.dialogStack.append((self.currentDialog, self.currentWindow))
			self.execEnd()
		
		self.currentDialog = self.create(screen, arguments)
		
		if self.desktop != None:
			self.currentWindow = eWindow(self.desktop)

			gui = GUIOutputDevice()
			gui.parent = self.currentWindow
			gui.create(self.currentDialog)

		 	applyGUIskin(self.currentDialog, self.currentWindow, None, self.currentDialog.skinName)

			self.execBegin()
		else:
			self.currentWindow = None

	def keyEvent(self, code):
#		print "code " + str(code)
		if code == 32:
			self.currentDialog["okbutton"].instance.push()

		if code == 33:
			self.currentDialog["channelSwitcher"].instance.push()
		
		if code >= 0x30 and code <= 0x39:
			try:
				self.currentDialog["menu"].instance.moveSelection(code - 0x31)
			except:
				self.currentDialog["list"].instance.moveSelection(code - 0x31)

	def close(self):
		self.delayTimer.start(0, 1)

def runScreenTest():
	session = Session()
	session.desktop = getDesktop()
	
	session.nav = pNavigation()
	
	session.open(infoBar)

	CONNECT(keyPressedSignal(), session.keyEvent)
	
	runMainloop()
	
	return 0

import keymapparser
keymapparser.readKeymap()

# first, setup a screen
runScreenTest()

# now, run the mainloop
