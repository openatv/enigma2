from Tools import RedirectOutput
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
from Tools.Directories import InitFallbackFiles, resolveFilename, SCOPE_PLUGINS
InitFallbackFiles()
eDVBDB.getInstance().reloadBouquets()

try:
	import e2reactor
	e2reactor.install()
	
	from twisted.internet import reactor
	
	def runReactor():
		reactor.run()
except ImportError:
	print "twisted not available"
	def runReactor():
		runMainloop()

# initialize autorun plugins and plugin menu entries
from Components.PluginComponent import plugins
plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))

from Screens.Wizard import wizardManager
from Screens.StartWizard import *
from Screens.TutorialWizard import *
from Tools.BoundFunction import boundFunction
from Plugins.Plugin import PluginDescriptor

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
			c.show()
		
	def execEnd(self):
		self.currentDialog.execEnd()
		self.currentDialog.hide()
	
	def create(self, screen, arguments, **kwargs):
		# creates an instance of 'screen' (which is a class)
		try:
			return screen(self, *arguments, **kwargs)
		except:
			errstr = "Screen %s(%s, %s): %s" % (str(screen), str(arguments), str(kwargs), sys.exc_info()[0])
			print errstr
			traceback.print_exc(file=sys.stdout)
			quitMainloop(5)
			
	
	def instantiateDialog(self, screen, *arguments, **kwargs):
		# create dialog
		
		try:
			dlg = self.create(screen, arguments, **kwargs)
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
		
		z = 0
		for (key, value) in dlg.skinAttributes:
			if key == "zPosition":
				z = int(value)

		dlg.instance = eWindow(self.desktop, z)
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

	def openWithCallback(self, callback, screen, *arguments, **kwargs):
		dlg = self.open(screen, *arguments, **kwargs)
		dlg.callback = callback

	def open(self, screen, *arguments, **kwargs):
		self.pushCurrent()
		dlg = self.currentDialog = self.instantiateDialog(screen, *arguments, **kwargs)
		dlg.isTmp = True
		dlg.callback = None
		self.execBegin()
		return dlg

	def keyEvent(self, code):
		print "code " + str(code)

	def close(self, *retval):
		self.currentDialog.returnValue = retval
		self.delayTimer.start(0, 1)

from Screens.Volume import Volume
from Screens.Mute import Mute
from GlobalActions import globalActionMap
from Components.config import ConfigSubsection, configSequence, configElement, configsequencearg

#TODO .. move this to a own .py file
class VolumeControl:
	"""Volume control, handles volUp, volDown, volMute actions and display
	a corresponding dialog"""
	def __init__(self, session):
		global globalActionMap
		globalActionMap.actions["volumeUp"]=self.volUp
		globalActionMap.actions["volumeDown"]=self.volDown
		globalActionMap.actions["volumeMute"]=self.volMute

		config.audio = ConfigSubsection()
		config.audio.volume = configElement("config.audio.volume", configSequence, [100], configsequencearg.get("INTEGER", (0, 100)))

		self.volumeDialog = session.instantiateDialog(Volume)
		self.muteDialog = session.instantiateDialog(Mute)

		self.hideVolTimer = eTimer()
		self.hideVolTimer.timeout.get().append(self.volHide)

		vol = config.audio.volume.value[0]
		self.volumeDialog.setValue(vol)
		eDVBVolumecontrol.getInstance().setVolume(vol, vol)

	def volSave(self):
		config.audio.volume.value = eDVBVolumecontrol.getInstance().getVolume()
		config.audio.volume.save()

	def	volUp(self):
		if (eDVBVolumecontrol.getInstance().isMuted()):
			self.volMute()
		eDVBVolumecontrol.getInstance().volumeUp()
		self.volumeDialog.show()
		self.volumeDialog.setValue(eDVBVolumecontrol.getInstance().getVolume())
		self.volSave()
		self.hideVolTimer.start(3000, True)

	def	volDown(self):
		if (eDVBVolumecontrol.getInstance().isMuted()):
			self.volMute()
		eDVBVolumecontrol.getInstance().volumeDown()
		self.volumeDialog.show()
		self.volumeDialog.setValue(eDVBVolumecontrol.getInstance().getVolume())
		self.volSave()
		self.hideVolTimer.start(3000, True)

	def volHide(self):
		self.volumeDialog.hide()

	def	volMute(self):
		eDVBVolumecontrol.getInstance().volumeToggleMute()
		self.volumeDialog.setValue(eDVBVolumecontrol.getInstance().getVolume())

		if (eDVBVolumecontrol.getInstance().isMuted()):
			self.muteDialog.show()
		else:
			self.muteDialog.hide()

def runScreenTest():
	session = Session()
	session.desktop = getDesktop()
	
	session.nav = Navigation()
	
	screensToRun = [ ]
	
	for p in plugins.getPlugins(PluginDescriptor.WHERE_WIZARD):
		screensToRun.append(p.__call__)
	
	screensToRun += wizardManager.getWizards()
	
	screensToRun.append(Screens.InfoBar.InfoBar)

	def runNextScreen(session, screensToRun, *result):
		if result:
			quitMainloop(*result)
			return
	
		screen = screensToRun[0]
		
		if len(screensToRun):
			session.openWithCallback(boundFunction(runNextScreen, session, screensToRun[1:]), screen)
		else:
			session.open(screen)
	
	runNextScreen(session, screensToRun)
	
	CONNECT(keyPressedSignal(), session.keyEvent)
	
	vol = VolumeControl(session)
	
	runReactor()
	
	configfile.save()
	
	from Tools.DreamboxHardware import setFPWakeuptime
	from time import time
	nextRecordingTime = session.nav.RecordTimer.getNextRecordingTime()
	if nextRecordingTime != -1:
		if (nextRecordingTime < 330): # no time to switch box back on
			setFPWakeuptime(time() + 30) # so switch back on in 30 seconds
		else:
			setFPWakeuptime(nextRecordingTime - (300))
	
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

import Components.UsageConfig
Components.UsageConfig.InitUsageConfig()

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

	plugins.shutdown()
except:
	print 'EXCEPTION IN PYTHON STARTUP CODE:'
	print '-'*60
	traceback.print_exc(file=sys.stdout)
	quitMainloop(5)
	print '-'*60
