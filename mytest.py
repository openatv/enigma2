from enigma import *
from tools import *

from Components.Language import language

import traceback
import Screens.InfoBar

import sys
import time

import ServiceReference

from Navigation import Navigation

from skin import readSkin, applyAllAttributes

from Components.config import configfile
from Screens.Wizard import wizardManager
from Screens.StartWizard import *
from Screens.TutorialWizard import *
from Tools.BoundFunction import boundFunction

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
		
		callback = self.currentDialog.callback

		retval = self.currentDialog.returnValue

		if self.currentDialog.isTmp:
			self.currentDialog.doClose()
#			dump(self.currentDialog)
			del self.currentDialog
		else:
			del self.currentDialog.callback
		
		self.popCurrent()
		if callback is not None:
			callback(*retval)

	def execBegin(self):
		c = self.currentDialog
		c.execBegin()

		# when execBegin opened a new dialog, don't bother showing the old one.
		if c == self.currentDialog:
			c.instance.show()
		
	def execEnd(self):
		self.currentDialog.execEnd()
		self.currentDialog.instance.hide()
	
	def create(self, screen, arguments):
		# creates an instance of 'screen' (which is a class)
		try:
			return screen(self, *arguments)
		except:
			errstr = "Screen %s(%s): %s" % (str(screen), str(arguments), sys.exc_info()[0])
			print errstr
			traceback.print_exc(file=sys.stdout)
			quitMainloop(5)
			
	
	def instantiateDialog(self, screen, *arguments):
		# create dialog
		
		try:
			dlg = self.create(screen, arguments)
		except:
			print 'EXCEPTION IN DIALOG INIT CODE, ABORTING:'
			print '-'*60
			traceback.print_exc(file=sys.stdout)
			quitMainloop(5)
			print '-'*60
		
		if dlg is None:
			return

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
		else:
			self.currentDialog = None

	def execDialog(self, dialog):
		self.pushCurrent()
		self.currentDialog = dialog
		self.currentDialog.isTmp = False
		self.currentDialog.callback = None # would cause re-entrancy problems.
		self.execBegin()

	def openWithCallback(self, callback, screen, *arguments):
		dlg = self.open(screen, *arguments)
		dlg.callback = callback

	def open(self, screen, *arguments):
		self.pushCurrent()
		dlg = self.currentDialog = self.instantiateDialog(screen, *arguments)
		dlg.isTmp = True
		dlg.callback = None
		self.execBegin()
		return dlg

	def keyEvent(self, code):
		print "code " + str(code)

	def close(self, *retval):
		self.currentDialog.returnValue = retval
		self.delayTimer.start(0, 1)

def runScreenTest():
	session = Session()
	session.desktop = getDesktop()
	
	session.nav = Navigation()
	
	screensToRun = wizardManager.getWizards()
	screensToRun.append(Screens.InfoBar.InfoBar)
	
	def runNextScreen(session, screensToRun, *result):
		if result:
			quitMainloop(result)

		screen = screensToRun[0]
		
		if len(screensToRun):
			session.openWithCallback(boundFunction(runNextScreen, session, screensToRun[1:]), screen)
		else:
			session.open(screen)
	
	runNextScreen(session, screensToRun)

	CONNECT(keyPressedSignal(), session.keyEvent)
	
	runMainloop()
	
	configfile.save()
	
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

import Components.RecordingConfig
Components.RecordingConfig.InitRecordingConfig()

import Components.Network
Components.Network.InitNetwork()

import Components.Lcd
Components.Lcd.InitLcd()

import Components.SetupDevices
Components.SetupDevices.InitSetupDevices()

import Components.RFmod
Components.RFmod.InitRFmod()

import Components.NimManager

# first, setup a screen
try:
	runScreenTest()
except:
	print 'EXCEPTION IN PYTHON STARTUP CODE:'
	print '-'*60
	traceback.print_exc(file=sys.stdout)
	quitMainloop(5)
	print '-'*60
