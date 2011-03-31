import eConsoleImpl
import eBaseImpl
import enigma
enigma.eTimer = eBaseImpl.eTimer
enigma.eSocketNotifier = eBaseImpl.eSocketNotifier
enigma.eConsoleAppContainer = eConsoleImpl.eConsoleAppContainer

from Tools.Profile import profile, profile_final

profile("PYTHON_START")

from enigma import runMainloop, eDVBDB, eTimer, quitMainloop, \
	getDesktop, ePythonConfigQuery, eAVSwitch, eServiceEvent, \
	eEPGCache
from tools import *

profile("LANGUAGE")

from Components.Language import language

def setEPGLanguage():
	print "language set to", language.getLanguage()
	eServiceEvent.setEPGLanguage(language.getLanguage())

language.addCallback(setEPGLanguage)

from traceback import print_exc
profile("LOAD:InfoBar")
import Screens.InfoBar
from Screens.SimpleSummary import SimpleSummary

from sys import stdout, exc_info

profile("Bouquets")
eDVBDB.getInstance().reloadBouquets()

profile("ParentalControl")
from Components.ParentalControl import InitParentalControl
InitParentalControl()

profile("LOAD:Navigation")
from Navigation import Navigation

profile("LOAD:skin")
from skin import readSkin

profile("LOAD:Tools")
from Tools.Directories import InitFallbackFiles, resolveFilename, SCOPE_PLUGINS, SCOPE_CURRENT_SKIN
from Components.config import config, configfile, ConfigText, ConfigYesNo, ConfigInteger, NoSave
InitFallbackFiles()

profile("config.misc")

config.misc.radiopic = ConfigText(default = resolveFilename(SCOPE_CURRENT_SKIN, "radio.mvi"))
config.misc.isNextRecordTimerAfterEventActionAuto = ConfigYesNo(default=False)
config.misc.useTransponderTime = ConfigYesNo(default=True)
config.misc.startCounter = ConfigInteger(default=0) # number of e2 starts...
config.misc.standbyCounter = NoSave(ConfigInteger(default=0)) # number of standby
config.misc.epgcache_filename = ConfigText(default = "/hdd/epg.dat")

def setEPGCachePath(configElement):
	eEPGCache.getInstance().setCacheFile(configElement.value)


#demo code for use of standby enter leave callbacks
#def leaveStandby():
#	print "!!!!!!!!!!!!!!!!!leave standby"

#def standbyCountChanged(configElement):
#	print "!!!!!!!!!!!!!!!!!enter standby num", configElement.value
#	from Screens.Standby import inStandby
#	inStandby.onClose.append(leaveStandby)

#config.misc.standbyCounter.addNotifier(standbyCountChanged, initial_call = False)
####################################################

def useTransponderTimeChanged(configElement):
	enigma.eDVBLocalTimeHandler.getInstance().setUseDVBTime(configElement.value)
config.misc.useTransponderTime.addNotifier(useTransponderTimeChanged)

profile("Twisted")
try:
	import twisted.python.runtime
	twisted.python.runtime.platform.supportsThreads = lambda: False

	import e2reactor
	e2reactor.install()

	from twisted.internet import reactor

	def runReactor():
		reactor.run(installSignalHandlers=False)
except ImportError:
	print "twisted not available"
	def runReactor():
		runMainloop()

profile("LOAD:Plugin")

# initialize autorun plugins and plugin menu entries
from Components.PluginComponent import plugins

profile("LOAD:Wizard")
from Screens.Wizard import wizardManager
from Screens.DefaultWizard import *
from Screens.StartWizard import *
from Screens.TutorialWizard import *
import Screens.Rc
from Tools.BoundFunction import boundFunction
from Plugins.Plugin import PluginDescriptor

profile("misc")
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

profile("LOAD:ScreenGlobals")
from Screens.Globals import Globals
from Screens.SessionGlobals import SessionGlobals
from Screens.Screen import Screen

profile("Screen")
Screen.global_screen = Globals()

# Session.open:
# * push current active dialog ('current_dialog') onto stack
# * call execEnd for this dialog
#   * clear in_exec flag
#   * hide screen
# * instantiate new dialog into 'current_dialog'
#   * create screens, components
#   * read, apply skin
#   * create GUI for screen
# * call execBegin for new dialog
#   * set in_exec
#   * show gui screen
#   * call components' / screen's onExecBegin
# ... screen is active, until it calls 'close'...
# Session.close:
# * assert in_exec
# * save return value
# * start deferred close handler ('onClose')
# * execEnd
#   * clear in_exec
#   * hide screen
# .. a moment later:
# Session.doClose:
# * destroy screen

class Session:
	def __init__(self, desktop = None, summary_desktop = None, navigation = None):
		self.desktop = desktop
		self.summary_desktop = summary_desktop
		self.nav = navigation
		self.delay_timer = eTimer()
		self.delay_timer.callback.append(self.processDelay)

		self.current_dialog = None

		self.dialog_stack = [ ]
		self.summary_stack = [ ]
		self.summary = None

		self.in_exec = False

		self.screen = SessionGlobals(self)

		for p in plugins.getPlugins(PluginDescriptor.WHERE_SESSIONSTART):
			p(reason=0, session=self)

	def processDelay(self):
		callback = self.current_dialog.callback

		retval = self.current_dialog.returnValue

		if self.current_dialog.isTmp:
			self.current_dialog.doClose()
#			dump(self.current_dialog)
			del self.current_dialog
		else:
			del self.current_dialog.callback

		self.popCurrent()
		if callback is not None:
			callback(*retval)

	def execBegin(self, first=True, do_show = True):
		assert not self.in_exec 
		self.in_exec = True
		c = self.current_dialog

		# when this is an execbegin after a execend of a "higher" dialog,
		# popSummary already did the right thing.
		if first:
			self.pushSummary()
			summary = c.createSummary() or SimpleSummary
			self.summary = self.instantiateSummaryDialog(summary, c)
			self.summary.show()
			c.addSummary(self.summary)

		c.saveKeyboardMode()
		c.execBegin()

		# when execBegin opened a new dialog, don't bother showing the old one.
		if c == self.current_dialog and do_show:
			c.show()

	def execEnd(self, last=True):
		assert self.in_exec
		self.in_exec = False

		self.current_dialog.execEnd()
		self.current_dialog.restoreKeyboardMode()
		self.current_dialog.hide()

		if last:
			self.current_dialog.removeSummary(self.summary)
			self.popSummary()

	def create(self, screen, arguments, **kwargs):
		# creates an instance of 'screen' (which is a class)
		try:
			return screen(self, *arguments, **kwargs)
		except:
			errstr = "Screen %s(%s, %s): %s" % (str(screen), str(arguments), str(kwargs), exc_info()[0])
			print errstr
			print_exc(file=stdout)
			quitMainloop(5)

	def instantiateDialog(self, screen, *arguments, **kwargs):
		return self.doInstantiateDialog(screen, arguments, kwargs, self.desktop)

	def deleteDialog(self, screen):
		screen.hide()
		screen.doClose()

	def instantiateSummaryDialog(self, screen, *arguments, **kwargs):
		return self.doInstantiateDialog(screen, arguments, kwargs, self.summary_desktop)

	def doInstantiateDialog(self, screen, arguments, kwargs, desktop):
		# create dialog

		try:
			dlg = self.create(screen, arguments, **kwargs)
		except:
			print 'EXCEPTION IN DIALOG INIT CODE, ABORTING:'
			print '-'*60
			print_exc(file=stdout)
			quitMainloop(5)
			print '-'*60

		if dlg is None:
			return

		# read skin data
		readSkin(dlg, None, dlg.skinName, desktop)

		# create GUI view of this dialog
		assert desktop is not None

		dlg.setDesktop(desktop)
		dlg.applySkin()

		return dlg

	def pushCurrent(self):
		if self.current_dialog is not None:
			self.dialog_stack.append((self.current_dialog, self.current_dialog.shown))
			self.execEnd(last=False)

	def popCurrent(self):
		if self.dialog_stack:
			(self.current_dialog, do_show) = self.dialog_stack.pop()
			self.execBegin(first=False, do_show=do_show)
		else:
			self.current_dialog = None

	def execDialog(self, dialog):
		self.pushCurrent()
		self.current_dialog = dialog
		self.current_dialog.isTmp = False
		self.current_dialog.callback = None # would cause re-entrancy problems.
		self.execBegin()

	def openWithCallback(self, callback, screen, *arguments, **kwargs):
		dlg = self.open(screen, *arguments, **kwargs)
		dlg.callback = callback
		return dlg

	def open(self, screen, *arguments, **kwargs):
		if self.dialog_stack and not self.in_exec:
			raise RuntimeError("modal open are allowed only from a screen which is modal!")
			# ...unless it's the very first screen.

		self.pushCurrent()
		dlg = self.current_dialog = self.instantiateDialog(screen, *arguments, **kwargs)
		dlg.isTmp = True
		dlg.callback = None
		self.execBegin()
		return dlg

	def close(self, screen, *retval):
		if not self.in_exec:
			print "close after exec!"
			return

		# be sure that the close is for the right dialog!
		# if it's not, you probably closed after another dialog
		# was opened. this can happen if you open a dialog
		# onExecBegin, and forget to do this only once.
		# after close of the top dialog, the underlying will
		# gain focus again (for a short time), thus triggering
		# the onExec, which opens the dialog again, closing the loop.
		assert screen == self.current_dialog

		self.current_dialog.returnValue = retval
		self.delay_timer.start(0, 1)
		self.execEnd()

	def pushSummary(self):
		if self.summary is not None:
			self.summary.hide()
		self.summary_stack.append(self.summary)
		self.summary = None

	def popSummary(self):
		if self.summary is not None:
			self.summary.doClose()
		self.summary = self.summary_stack.pop()
		if self.summary is not None:
			self.summary.show()

profile("Standby,PowerKey")
import Screens.Standby
from Screens.Menu import MainMenu, mdom
from GlobalActions import globalActionMap

class PowerKey:
	""" PowerKey stuff - handles the powerkey press and powerkey release actions"""

	def __init__(self, session):
		self.session = session
		globalActionMap.actions["power_down"]=self.powerdown
		globalActionMap.actions["power_up"]=self.powerup
		globalActionMap.actions["power_long"]=self.powerlong
		globalActionMap.actions["deepstandby"]=self.shutdown # frontpanel long power button press
		self.standbyblocked = 1

	def MenuClosed(self, *val):
		self.session.infobar = None

	def shutdown(self):
		print "PowerOff - Now!"
		if not Screens.Standby.inTryQuitMainloop and self.session.current_dialog and self.session.current_dialog.ALLOW_SUSPEND:
			self.session.open(Screens.Standby.TryQuitMainloop, 1)

	def powerlong(self):
		if Screens.Standby.inTryQuitMainloop or (self.session.current_dialog and not self.session.current_dialog.ALLOW_SUSPEND):
			return
		self.doAction(action = config.usage.on_long_powerpress.value)

	def doAction(self, action):
		self.standbyblocked = 1
		if action == "shutdown":
			self.shutdown()
		elif action == "show_menu":
			print "Show shutdown Menu"
			root = mdom.getroot()
			for x in root.findall("menu"):
				y = x.find("id")
				if y is not None:
					id = y.get("val")
					if id and id == "shutdown":
						self.session.infobar = self
						menu_screen = self.session.openWithCallback(self.MenuClosed, MainMenu, x)
						menu_screen.setTitle(_("Standby / Restart"))
						return
		elif action == "standby":
			self.standby()

	def powerdown(self):
		self.standbyblocked = 0

	def powerup(self):
		if self.standbyblocked == 0:
			self.doAction(action = config.usage.on_short_powerpress.value)

	def standby(self):
		if not Screens.Standby.inStandby and self.session.current_dialog and self.session.current_dialog.ALLOW_SUSPEND and self.session.in_exec:
			self.session.open(Screens.Standby.Standby)

profile("Scart")
from Screens.Scart import Scart

class AutoScartControl:
	def __init__(self, session):
		self.force = False
		self.current_vcr_sb = eAVSwitch.getInstance().getVCRSlowBlanking()
		if self.current_vcr_sb and config.av.vcrswitch.value:
			self.scartDialog = session.instantiateDialog(Scart, True)
		else:
			self.scartDialog = session.instantiateDialog(Scart, False)
		config.av.vcrswitch.addNotifier(self.recheckVCRSb)
		eAVSwitch.getInstance().vcr_sb_notifier.get().append(self.VCRSbChanged)

	def recheckVCRSb(self, configElement):
		self.VCRSbChanged(self.current_vcr_sb)

	def VCRSbChanged(self, value):
		#print "vcr sb changed to", value
		self.current_vcr_sb = value
		if config.av.vcrswitch.value or value > 2:
			if value:
				self.scartDialog.showMessageBox()
			else:
				self.scartDialog.switchToTV()

profile("Load:CI")
from enigma import eDVBCIInterfaces
from Screens.Ci import CiHandler

profile("Load:VolumeControl")
from Components.VolumeControl import VolumeControl

def runScreenTest():
	config.misc.startCounter.value += 1

	profile("readPluginList")
	plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))

	profile("Init:Session")
	nav = Navigation(config.misc.isNextRecordTimerAfterEventActionAuto.value)
	session = Session(desktop = getDesktop(0), summary_desktop = getDesktop(1), navigation = nav)

	CiHandler.setSession(session)

	screensToRun = [ p.__call__ for p in plugins.getPlugins(PluginDescriptor.WHERE_WIZARD) ]

	profile("wizards")
	screensToRun += wizardManager.getWizards()

	screensToRun.append((100, Screens.InfoBar.InfoBar))

	screensToRun.sort()

	ePythonConfigQuery.setQueryFunc(configfile.getResolvedKey)

#	eDVBCIInterfaces.getInstance().setDescrambleRules(0 # Slot Number
#		,(	["1:0:1:24:4:85:C00000:0:0:0:"], #service_list
#			["PREMIERE"], #provider_list,
#			[] #caid_list
#		));

	def runNextScreen(session, screensToRun, *result):
		if result:
			quitMainloop(*result)
			return

		screen = screensToRun[0][1]
		args = screensToRun[0][2:]

		if screensToRun:
			session.openWithCallback(boundFunction(runNextScreen, session, screensToRun[1:]), screen, *args)
		else:
			session.open(screen, *args)

	config.misc.epgcache_filename.addNotifier(setEPGCachePath)

	runNextScreen(session, screensToRun)

	profile("Init:VolumeControl")
	vol = VolumeControl(session)
	profile("Init:PowerKey")
	power = PowerKey(session)

	# we need session.scart to access it from within menu.xml
	session.scart = AutoScartControl(session)

	profile("RunReactor")
	profile_final()
	runReactor()

	config.misc.startCounter.save()

	profile("wakeup")
	from time import time, strftime, localtime
	from Tools.DreamboxHardware import setFPWakeuptime, getFPWakeuptime, setRTCtime
	#get currentTime
	nowTime = time()
	wakeupList = [
		x for x in ((session.nav.RecordTimer.getNextRecordingTime(), 0, session.nav.RecordTimer.isNextRecordAfterEventActionAuto()),
					(session.nav.RecordTimer.getNextZapTime(), 1),
					(plugins.getNextWakeupTime(), 2))
		if x[0] != -1
	]
	wakeupList.sort()
	recordTimerWakeupAuto = False
	if wakeupList:
		from time import strftime
		startTime = wakeupList[0]
		if (startTime[0] - nowTime) < 270: # no time to switch box back on
			wptime = nowTime + 30  # so switch back on in 30 seconds
		else:
			wptime = startTime[0] - 240
		if not config.misc.useTransponderTime.value:
			print "dvb time sync disabled... so set RTC now to current linux time!", strftime("%Y/%m/%d %H:%M", localtime(nowTime))
			setRTCtime(nowTime)
		print "set wakeup time to", strftime("%Y/%m/%d %H:%M", localtime(wptime))
		setFPWakeuptime(wptime)
		recordTimerWakeupAuto = startTime[1] == 0 and startTime[2]
	config.misc.isNextRecordTimerAfterEventActionAuto.value = recordTimerWakeupAuto
	config.misc.isNextRecordTimerAfterEventActionAuto.save()

	profile("stopService")
	session.nav.stopService()
	profile("nav shutdown")
	session.nav.shutdown()

	profile("configfile.save")
	configfile.save()

	return 0

profile("Init:skin")
import skin
skin.loadSkinData(getDesktop(0))

profile("InputDevice")
import Components.InputDevice
Components.InputDevice.InitInputDevices()

profile("AVSwitch")
import Components.AVSwitch
Components.AVSwitch.InitAVSwitch()

profile("RecordingConfig")
import Components.RecordingConfig
Components.RecordingConfig.InitRecordingConfig()

profile("UsageConfig")
import Components.UsageConfig
Components.UsageConfig.InitUsageConfig()

profile("keymapparser")
import keymapparser
keymapparser.readKeymap(config.usage.keymap.value)

profile("Network")
import Components.Network
Components.Network.InitNetwork()

profile("LCD")
import Components.Lcd
Components.Lcd.InitLcd()

profile("SetupDevices")
import Components.SetupDevices
Components.SetupDevices.InitSetupDevices()

profile("RFMod")
import Components.RFmod
Components.RFmod.InitRFmod()

profile("Init:CI")
import Screens.Ci
Screens.Ci.InitCiConfig()

#from enigma import dump_malloc_stats
#t = eTimer()
#t.callback.append(dump_malloc_stats)
#t.start(1000)

# first, setup a screen
try:
	runScreenTest()

	plugins.shutdown()

	from Components.ParentalControl import parentalControl
	parentalControl.save()
except:
	print 'EXCEPTION IN PYTHON STARTUP CODE:'
	print '-'*60
	print_exc(file=stdout)
	quitMainloop(5)
	print '-'*60
