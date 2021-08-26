from __future__ import print_function
import sys
import os
from time import time

from Tools.Profile import profile, profile_final  # This facilitates the start up progress counter.
profile("StartPython")
import Tools.RedirectOutput  # Don't remove this line. This import facilitates connecting stdout and stderr redirections to the log files.

import enigma  # Establish enigma2 connections to processing methods.
import eBaseImpl
import eConsoleImpl
enigma.eTimer = eBaseImpl.eTimer
enigma.eSocketNotifier = eBaseImpl.eSocketNotifier
enigma.eConsoleAppContainer = eConsoleImpl.eConsoleAppContainer


# Session.open:
# * Push current active dialog ("current_dialog") onto stack.
# * Call execEnd for this dialog.
#   * Clear in_exec flag.
#   * Hide screen.
# * Instantiate new dialog into "current_dialog".
#   * Create screens, components.
#   * Read and apply skin.
#   * Create GUI for screen.
# * Call execBegin for new dialog.
#   * Set in_exec.
#   * Show GUI screen.
#   * Call components' / screen's onExecBegin.
# ... Screen is active, until it calls "close"...
#
# Session.close:
# * Assert in_exec.
# * Save return value.
# * Start deferred close handler ("onClose").
# * Call execEnd.
#   * Clear in_exec.
#   * Hide screen.
# .. a moment later:
# Session.doClose:
# * Destroy screen.
#
class Session:
	def __init__(self, desktop=None, summaryDesktop=None, navigation=None):
		self.desktop = desktop
		self.summaryDesktop = summaryDesktop
		self.nav = navigation
		self.delay_timer = enigma.eTimer()
		self.delay_timer.callback.append(self.processDelay)
		self.current_dialog = None
		self.dialog_stack = []
		self.summary_stack = []
		self.summary = None
		self.in_exec = False
		self.screen = SessionGlobals(self)
		for plugin in plugins.getPlugins(PluginDescriptor.WHERE_SESSIONSTART):
			try:
				plugin.__call__(reason=0, session=self)
			except:
				print("[StartEnigma] Error: Plugin raised exception at WHERE_SESSIONSTART!")
				import traceback
				traceback.print_exc()

	def processDelay(self):
		callback = self.current_dialog.callback
		retVal = self.current_dialog.returnValue
		if self.current_dialog.isTmp:
			self.current_dialog.doClose()
			# dump(self.current_dialog)
			del self.current_dialog
		else:
			del self.current_dialog.callback
		self.popCurrent()
		if callback is not None:
			callback(*retVal)

	def execBegin(self, first=True, do_show=True):
		if self.in_exec:
			raise AssertionError("[StartEnigma] Error: Already in exec!")
		self.in_exec = True
		currentDialog = self.current_dialog
		# When this is an execbegin after a execEnd of a "higher" dialog,
		# popSummary already did the right thing.
		if first:
			self.instantiateSummaryDialog(currentDialog)
		currentDialog.saveKeyboardMode()
		currentDialog.execBegin()
		# When execBegin opened a new dialog, don't bother showing the old one.
		if currentDialog == self.current_dialog and do_show:
			currentDialog.show()

	def execEnd(self, last=True):
		assert self.in_exec
		self.in_exec = False
		self.current_dialog.execEnd()
		self.current_dialog.restoreKeyboardMode()
		self.current_dialog.hide()
		if last and self.summary is not None:
			self.current_dialog.removeSummary(self.summary)
			self.popSummary()

	def instantiateDialog(self, screen, *arguments, **kwargs):
		return self.doInstantiateDialog(screen, arguments, kwargs, self.desktop)

	def deleteDialog(self, screen):
		screen.hide()
		screen.doClose()

	def deleteDialogWithCallback(self, callback, screen, *retVal):
		screen.hide()
		screen.doClose()
		if callback is not None:
			callback(*retVal)

	def instantiateSummaryDialog(self, screen, **kwargs):
		if self.summaryDesktop is not None:
			self.pushSummary()
			summary = screen.createSummary() or SimpleSummary
			arguments = (screen,)
			self.summary = self.doInstantiateDialog(summary, arguments, kwargs, self.summaryDesktop)
			self.summary.show()
			screen.addSummary(self.summary)

	def doInstantiateDialog(self, screen, arguments, kwargs, desktop):
		dialog = screen(self, *arguments, **kwargs)  # Create dialog.
		if dialog is None:
			return
		readSkin(dialog, None, dialog.skinName, desktop)  # Read skin data.
		dialog.setDesktop(desktop)  # Create GUI view of this dialog.
		dialog.applySkin()
		return dialog

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
		self.current_dialog.callback = None  # Would cause re-entrancy problems.
		self.execBegin()

	def openWithCallback(self, callback, screen, *arguments, **kwargs):
		dialog = self.open(screen, *arguments, **kwargs)
		if dialog != 'config.crash.bsodpython.value=True':
			dialog.callback = callback
			return dialog

	def open(self, screen, *arguments, **kwargs):
		if self.dialog_stack and not self.in_exec:
			raise RuntimeError("[StartEnigma] Error: Modal open are allowed only from a screen which is modal!")  # ...unless it's the very first screen.
		self.pushCurrent()
		if config.crash.bsodpython.value:
			try:
				dialog = self.current_dialog = self.instantiateDialog(screen, *arguments, **kwargs)
			except:
				self.popCurrent()
				raise
				return 'config.crash.bsodpython.value=True'
		else:
			dialog = self.current_dialog = self.instantiateDialog(screen, *arguments, **kwargs)
		dialog.isTmp = True
		dialog.callback = None
		self.execBegin()
		return dialog

	def close(self, screen, *retVal):
		if not self.in_exec:
			print("[StartEnigma] Close after exec!")
			return
		# Be sure that the close is for the right dialog!  If it's
		# not, you probably closed after another dialog was opened.
		# This can happen if you open a dialog onExecBegin, and
		# forget to do this only once.  After close of the top
		# dialog, the underlying dialog will gain focus again (for
		# a short time), thus triggering the onExec, which opens the
		# dialog again, closing the loop.
		if not screen == self.current_dialog:
			raise AssertionError("[StartEnigma] Error: Attempt to close non-current screen!")
		self.current_dialog.returnValue = retVal
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
		if not self.summary_stack:
			self.summary = None
		else:
			self.summary = self.summary_stack.pop()
		if self.summary is not None:
			self.summary.show()


class PowerKey:
	"""PowerKey code - Handles the powerkey press and powerkey release actions."""

	def __init__(self, session):
		self.session = session
		globalActionMap.actions["power_down"] = self.powerdown
		globalActionMap.actions["power_up"] = self.powerup
		globalActionMap.actions["power_long"] = self.powerlong
		globalActionMap.actions["deepstandby"] = self.shutdown # frontpanel long power button press
		globalActionMap.actions["discrete_off"] = self.standby
		globalActionMap.actions["sleeptimer"] = self.openSleepTimer
		globalActionMap.actions["powertimer_standby"] = self.sleepStandby
		globalActionMap.actions["powertimer_deepstandby"] = self.sleepDeepStandby
		self.standbyblocked = 1

	def MenuClosed(self, *val):
		self.session.infobar = None

	def shutdown(self):
		recordings = self.session.nav.getRecordingsCheckBeforeActivateDeepStandby()
		if recordings:
			from Screens.MessageBox import MessageBox
			self.session.openWithCallback(self.gotoStandby, MessageBox, _("Recording(s) are in progress or coming up in few seconds!\nEntering standby, after recording the box will shutdown."), type=MessageBox.TYPE_INFO, close_on_any_key=True, timeout=10)
		elif not Screens.Standby.inTryQuitMainloop and self.session.current_dialog and self.session.current_dialog.ALLOW_SUSPEND:
			self.session.open(Screens.Standby.TryQuitMainloop, 1)

	def powerlong(self):
		if Screens.Standby.inTryQuitMainloop or (self.session.current_dialog and not self.session.current_dialog.ALLOW_SUSPEND):
			return
		self.doAction(action=config.usage.on_long_powerpress.value)

	def doAction(self, action):
		if Screens.Standby.TVinStandby.getTVstate('standby'):
			Screens.Standby.TVinStandby.setTVstate('on')
			return

		self.standbyblocked = 1
		if action == "shutdown":
			self.shutdown()
		elif action == "show_menu":
			print("Show shutdown Menu")
			root = mdom.getroot()
			for x in root.findall("menu"):
				y = x.find("id")
				if y is not None:
					id = y.get("val")
					if id and id == "shutdown":
						self.session.infobar = self
						menu_screen = self.session.openWithCallback(self.MenuClosed, MainMenu, x)
						menu_screen.setTitle(_("Standby / restart"))
						return
		elif action == "standby":
			Screens.Standby.TVinStandby.skipHdmiCecNow(False)
			self.standby()
		elif action == "standby_noTVshutdown":
			Screens.Standby.TVinStandby.skipHdmiCecNow(True)
			self.standby()
		elif action == "powertimerStandby":
			val = 3
			self.setSleepTimer(val)
		elif action == "powertimerDeepStandby":
			val = 4
			self.setSleepTimer(val)
		elif action == "sleeptimer":
			self.openSleepTimer()

	def powerdown(self):
		self.standbyblocked = 0

	def powerup(self):
		if self.standbyblocked == 0:
			self.doAction(action=config.usage.on_short_powerpress.value)

	def gotoStandby(self, ret):
		self.standby()

	def standby(self):
		if not Screens.Standby.inStandby and self.session.current_dialog and self.session.current_dialog.ALLOW_SUSPEND and self.session.in_exec:
			self.session.nav.skipWakeup = True
			self.session.open(Screens.Standby.Standby)

	def openSleepTimer(self):
		from Screens.SleepTimerEdit import SleepTimerEdit
		self.session.open(SleepTimerEdit)

	def setSleepTimer(self, val):
		from PowerTimer import PowerTimerEntry
		sleeptime = 15
		data = (int(time() + 60), int(time() + 120))
		self.addSleepTimer(PowerTimerEntry(checkOldTimers=True, *data, timerType=val, autosleepdelay=sleeptime))

	def addSleepTimer(self, timer):
		from Screens.PowerTimerEntry import TimerEntry
		self.session.openWithCallback(self.finishedAdd, TimerEntry, timer)

	def finishedAdd(self, answer):
		if answer[0]:
			entry = answer[1]
			simulTimerList = self.session.nav.PowerTimer.record(entry)

	def sleepStandby(self):
		self.doAction(action="powertimerStandby")

	def sleepDeepStandby(self):
		self.doAction(action="powertimerDeepStandby")


class AutoScartControl:
	def __init__(self, session):
		self.force = False
		self.current_vcr_sb = enigma.eAVSwitch.getInstance().getVCRSlowBlanking()
		if self.current_vcr_sb and config.av.vcrswitch.value:
			self.scartDialog = session.instantiateDialog(Scart, True)
		else:
			self.scartDialog = session.instantiateDialog(Scart, False)
		config.av.vcrswitch.addNotifier(self.recheckVCRSb)
		enigma.eAVSwitch.getInstance().vcr_sb_notifier.get().append(self.VCRSbChanged)

	def recheckVCRSb(self, configelement):
		self.VCRSbChanged(self.current_vcr_sb)

	def VCRSbChanged(self, value):
		# print("VCR SB changed to '%s'." % value)
		self.current_vcr_sb = value
		if config.av.vcrswitch.value or value > 2:
			if value:
				self.scartDialog.showMessageBox()
			else:
				self.scartDialog.switchToTV()


def autorestoreLoop():
	# Check if auto restore settings fails, just start the wizard (avoid a endless loop)
	count = 0
	if os.path.exists("/media/hdd/images/config/autorestore"):
		f = open("/media/hdd/images/config/autorestore", "r")
		try:
			count = int(f.read())
		except:
			count = 0
		f.close()
		if count >= 3:
			return False
	count += 1
	f = open("/media/hdd/images/config/autorestore", "w")
	f.write(str(count))
	f.close()
	return True


def runScreenTest():
	def runNextScreen(session, screensToRun, *result):
		if result:
			print("[StartEnigma.py] quitMainloop #3")
			enigma.quitMainloop(*result)
			return
		screen = screensToRun[0][1]
		args = screensToRun[0][2:]
		if screensToRun:
			session.openWithCallback(boundFunction(runNextScreen, session, screensToRun[1:]), screen, *args)
		else:
			session.open(screen, *args)

	config.misc.startCounter.value += 1
	profile("ReadPluginList")
	enigma.pauseInit()
	plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))
	enigma.resumeInit()

	profile("Init:Session")
	nav = Navigation(config.misc.nextWakeup.value)
	session = Session(desktop=enigma.getDesktop(0), summaryDesktop=enigma.getDesktop(1), navigation=nav)

	CiHandler.setSession(session)

	profile("InitWizards")
	screensToRun = []
	RestoreSettings = None
	if os.path.exists("/media/hdd/images/config/settings") and config.misc.firstrun.value:
		if autorestoreLoop():
			RestoreSettings = True
			from Plugins.SystemPlugins.SoftwareManager.BackupRestore import RestoreScreen
			session.open(RestoreScreen, runRestore=True)
		else:
			screensToRun = [p.__call__ for p in plugins.getPlugins(PluginDescriptor.WHERE_WIZARD)]
			screensToRun += wizardManager.getWizards()
	else:
		if os.path.exists("/media/hdd/images/config/autorestore"):
			os.system('rm -f /media/hdd/images/config/autorestore')
		screensToRun = [p.__call__ for p in plugins.getPlugins(PluginDescriptor.WHERE_WIZARD)]
		screensToRun += wizardManager.getWizards()

	screensToRun.append((100, InfoBar.InfoBar))
	screensToRun.sort()
	print(screensToRun)

	enigma.ePythonConfigQuery.setQueryFunc(configfile.getResolvedKey)

	if not RestoreSettings:
		runNextScreen(session, screensToRun)

	profile("InitVolumeControl")
	vol = VolumeControl(session)
	profile("InitPowerKey")
	power = PowerKey(session)

	if boxtype in ('alien5', 'osninopro', 'osnino', 'osninoplus', 'alphatriple', 'spycat4kmini', 'tmtwin4k', 'mbmicrov2', 'revo4k', 'force3uhd', 'wetekplay', 'wetekplay2', 'wetekhub', 'dm7020hd', 'dm7020hdv2', 'osminiplus', 'osmega', 'sf3038', 'spycat', 'e4hd', 'e4hdhybrid', 'mbmicro', 'et7500', 'mixosf5', 'mixosf7', 'mixoslumi', 'gi9196m', 'maram9', 'ixussone', 'ixusszero', 'uniboxhd1', 'uniboxhd2', 'uniboxhd3', 'sezam5000hd', 'mbtwin', 'sezam1000hd', 'mbmini', 'atemio5x00', 'beyonwizt3', '9910lx', '9911lx', '9920lx', 'dual') or getBrandOEM() in ('fulan') or getMachineBuild() in ('u41', 'dags7362', 'dags73625', 'dags5', 'ustym4kpro', 'beyonwizv2', 'viper4k', 'sf8008', 'sf8008m', 'sf8008opt', 'cc1', 'gbmv200'):
		profile("VFDSYMBOLS")
		import Components.VfdSymbols
		Components.VfdSymbols.SymbolsCheck(session)

	# we need session.scart to access it from within menu.xml
	session.scart = AutoScartControl(session)

	profile("InitTrashcan")
	import Tools.Trashcan
	Tools.Trashcan.init(session)

	profile("Init:AutoVideoMode")
	import Screens.VideoMode
	Screens.VideoMode.autostart(session)

	profile("RunReactor")
	profile_final()

	if boxtype in ('sf8', 'classm', 'axodin', 'axodinc', 'starsatlx', 'genius', 'evo'):
		f = open("/dev/dbox/oled0", "w")
		f.write('-E2-')
		f.close()

	print("lastshutdown=%s		(True = last shutdown was OK)" % config.usage.shutdownOK.value)
	print("NOK shutdown action=%s" % config.usage.shutdownNOK_action.value)
	print("bootup action=%s" % config.usage.boot_action.value)
	if not config.usage.shutdownOK.value and not config.usage.shutdownNOK_action.value == 'normal' or not config.usage.boot_action.value == 'normal':
		print("last shutdown = %s" % config.usage.shutdownOK.value)
		import Screens.PowerLost
		Screens.PowerLost.PowerLost(session)

	if not RestoreSettings:
		config.usage.shutdownOK.setValue(False)
		config.usage.shutdownOK.save()
		configfile.save()

	# kill showiframe if it is running (sh4 hack...)
	if getMachineBuild() in ('spark', 'spark7162'):
		os.system("killall -9 showiframe")

	runReactor()

	print("[StartEnigma.py] normal shutdown")
	config.misc.startCounter.save()
	config.usage.shutdownOK.setValue(True)
	config.usage.shutdownOK.save()

	profile("Wakeup")

	nowTime = time()  # Get currentTime.
#	if not config.misc.SyncTimeUsing.value == "0" or getBrandOEM() == 'gigablue':
	if not config.misc.SyncTimeUsing.value == "0" or boxtype.startswith('gb') or getBrandOEM().startswith('ini'):
		print("dvb time sync disabled... so set RTC now to current linux time!", strftime("%Y/%m/%d %H:%M", localtime(nowTime)))
		setRTCtime(nowTime)

	#recordtimer
	if session.nav.isRecordTimerImageStandard:	#check RecordTimer instance
		tmp = session.nav.RecordTimer.getNextRecordingTime(getNextStbPowerOn=True)
		nextRecordTime = tmp[0]
		nextRecordTimeInStandby = tmp[1]
	else:
		nextRecordTime = session.nav.RecordTimer.getNextRecordingTime()
		nextRecordTimeInStandby = session.nav.RecordTimer.isNextRecordAfterEventActionAuto()
	#zaptimer
	nextZapTime = session.nav.RecordTimer.getNextZapTime()
	nextZapTimeInStandby = 0
	#powertimer
	tmp = session.nav.PowerTimer.getNextPowerManagerTime(getNextStbPowerOn=True)
	nextPowerTime = tmp[0]
	nextPowerTimeInStandby = tmp[1]
	#plugintimer
	tmp = plugins.getNextWakeupTime(getPluginIdent=True)
	nextPluginTime = tmp[0]
	nextPluginIdent = tmp[1] #"pluginname | pluginfolder"
	tmp = tmp[1].lower()
	#start in standby, depending on plugin type
	if "epgrefresh" in tmp:
		nextPluginName = "EPGRefresh"
		nextPluginTimeInStandby = 1
	elif "vps" in tmp:
		nextPluginName = "VPS"
		nextPluginTimeInStandby = 1
	elif "serienrecorder" in tmp:
		nextPluginName = "SerienRecorder"
		nextPluginTimeInStandby = 0 # plugin function for deep standby from standby not compatible (not available)
	elif "elektro" in tmp:
		nextPluginName = "Elektro"
		nextPluginTimeInStandby = 1
	elif "minipowersave" in tmp:
		nextPluginName = "MiniPowersave"
		nextPluginTimeInStandby = 1
	elif "enhancedpowersave" in tmp:
		nextPluginName = "EnhancedPowersave"
		nextPluginTimeInStandby = 1
	else:
		#default for plugins
		nextPluginName = nextPluginIdent
		nextPluginTimeInStandby = 0

	wakeupList = [
		x for x in ((nextRecordTime, 0, nextRecordTimeInStandby),
					(nextZapTime, 1, nextZapTimeInStandby),
					(nextPowerTime, 2, nextPowerTimeInStandby),
					(nextPluginTime, 3, nextPluginTimeInStandby))
		if x[0] != -1
	]
	wakeupList.sort()

	print("=" * 100)
	if wakeupList and wakeupList[0][0] > 0:
		startTime = wakeupList[0]
		# wakeup time before timer begins
		wptime = startTime[0] - (config.workaround.wakeuptime.value * 60)
		if (wptime - nowTime) < 120: # no time to switch box back on
			wptime = int(nowTime) + 120  # so switch back on in 120 seconds

		#check for plugin-, zap- or power-timer to enable the 'forced' record-timer wakeup
		forceNextRecord = 0
		setStandby = startTime[2]
		if startTime[1] != 0 and nextRecordTime > 0:
			#when next record starts in 15 mins
			if abs(nextRecordTime - startTime[0]) <= 900:
				setStandby = forceNextRecord = 1
			#by vps-plugin
			elif startTime[1] == 3 and nextPluginName == "VPS":
				setStandby = forceNextRecord = 1

		if startTime[1] == 3:
			nextPluginName = " (%s)" % nextPluginName
		else:
			nextPluginName = ""
		print("[StartEnigma.py] set next wakeup type to '%s'%s %s" % ({0: "record-timer", 1: "zap-timer", 2: "power-timer", 3: "plugin-timer"}[startTime[1]], nextPluginName, {0: "and starts normal", 1: "and starts in standby"}[setStandby]))
		if forceNextRecord:
			print("[StartEnigma.py] set from 'vps-plugin' or just before a 'record-timer' starts, set 'record-timer' wakeup flag")
		print("[StartEnigma.py] set next wakeup time to", strftime("%a, %Y/%m/%d %H:%M:%S", localtime(wptime)))
		#set next wakeup
		setFPWakeuptime(wptime)
		#set next standby only after shutdown in deep standby
		if Screens.Standby.quitMainloopCode != 1 and Screens.Standby.quitMainloopCode != 45:
			setStandby = 2 # 0=no standby, but get in standby if wakeup to timer start > 60 sec (not for plugin-timer, here is no standby), 1=standby, 2=no standby, when before was not in deep-standby
		config.misc.nextWakeup.value = "%d,%d,%d,%d,%d,%d,%d" % (int(nowTime), wptime, startTime[0], startTime[1], setStandby, nextRecordTime, forceNextRecord)
	else:
		config.misc.nextWakeup.value = "%d,-1,-1,0,0,-1,0" % (int(nowTime))
		if not boxtype.startswith('azboxm'): #skip for Azbox (mini)ME - setting wakeup time to past reboots box
			setFPWakeuptime(int(nowTime) - 3600) #minus one hour -> overwrite old wakeup time
		print("[StartEnigma.py] no set next wakeup time")
	config.misc.nextWakeup.save()
	print("=" * 100)

	profile("stopService")
	session.nav.stopService()
	profile("nav shutdown")
	session.nav.shutdown()

	profile("configfile.save")
	configfile.save()
	from Screens import InfoBarGenerics
	InfoBarGenerics.saveResumePoints()

	return 0


def localeNotifier(configElement):
	international.activateLocale(configElement.value)


def setLoadUnlinkedUserbouquets(configElement):
	enigma.eDVBDB.getInstance().setLoadUnlinkedUserbouquets(configElement.value)


def useSyncUsingChanged(configelement):
	if config.misc.SyncTimeUsing.value == "0":
		print("[Time By]: Transponder")
		enigma.eDVBLocalTimeHandler.getInstance().setUseDVBTime(True)
		enigma.eEPGCache.getInstance().timeUpdated()
	else:
		print("[Time By]: NTP")
		enigma.eDVBLocalTimeHandler.getInstance().setUseDVBTime(False)
		enigma.eEPGCache.getInstance().timeUpdated()


def NTPserverChanged(configelement):
	if config.misc.NTPserver.value == "pool.ntp.org":
		return
	print("[NTPDATE] save /etc/default/ntpdate")
	f = open("/etc/default/ntpdate", "w")
	f.write('NTPSERVERS="' + config.misc.NTPserver.value + '"')
	f.close()
	os.chmod("/etc/default/ntpdate", 0o755)
	from Components.Console import Console
	Console = Console()
	Console.ePopen('/usr/bin/ntpdate-sync')


def dump(dir, p=""):
	had = dict()
	if isinstance(dir, dict):
		for (entry, val) in dir.items():
			dump(val, p + "(dict)/" + entry)
	if hasattr(dir, "__dict__"):
		for name, value in dir.__dict__.items():
			if str(value) not in had:
				had[str(value)] = 1
				dump(value, p + "/" + str(name))
			else:
				print("%s/%s:%s(cycle)" % (p, str(name), str(dir.__class__)))
	else:
		print("%s:%s" % (p, str(dir)))
		# + ":" + str(dir.__class__)

#demo code for use of standby enter leave callbacks
#def leaveStandby():
#	print "!!!!!!!!!!!!!!!!!leave standby"

#def standbyCountChanged(configelement):
#	print "!!!!!!!!!!!!!!!!!enter standby num", configelement.value
#	from Screens.Standby import inStandby
#	inStandby.onClose.append(leaveStandby)

#config.misc.standbyCounter.addNotifier(standbyCountChanged, initial_call = False)
####################################################

#################################
#                               #
#  Code execution starts here!  #
#                               #
#################################

from sys import stdout
from Components.config import config, ConfigYesNo, ConfigSubsection, ConfigInteger, ConfigText

MODULE_NAME = __name__.split(".")[-1]

profile("Twisted")
try:  # Configure the twisted processor
	from twisted.python.runtime import platform
	platform.supportsThreads = lambda: True
	from e2reactor import install
	install()
	from twisted.internet import reactor

	def runReactor():
		reactor.run(installSignalHandlers=False)

except ImportError:
	print("[StartEnigma] Error: Twisted not available!")

	def runReactor():
		enigma.runMainloop()

from twisted.python import log
config.misc.enabletwistedlog = ConfigYesNo(default=False)
if config.misc.enabletwistedlog.value == True:
	log.startLogging(open('/tmp/twisted.log', 'w'))
else:
	log.startLogging(stdout)


from boxbranding import getBoxType, getBrandOEM, getMachineBuild, getImageArch, getMachineBrand
boxtype = getBoxType()

if getImageArch() in ("aarch64"):
	import usb.core
	import usb.backend.libusb1
	usb.backend.libusb1.get_backend(find_library=lambda x: "/lib64/libusb-1.0.so.0")

from traceback import print_exc

profile("Geolocation")
import Tools.Geolocation
Tools.Geolocation.InitGeolocation()

profile("SetupDevices")
import Components.SetupDevices
Components.SetupDevices.InitSetupDevices()

# Initialize the country, language and locale data.
#
profile("InternationalLocalization")
from Components.International import international

config.osd = ConfigSubsection()
if getMachineBrand() == 'Atto.TV':
	defaultLanguage = "pt_BR"
elif getMachineBrand() == 'Zgemma':
	defaultLanguage = "en_US"
elif getMachineBrand() == 'Beyonwiz':
	defaultLanguage = "en_GB"
else:
	defaultLanguage = "de_DE"

defaultCountry = defaultLanguage[-2:]
defaultShortLanguage = defaultLanguage[0:2]

config.osd.language = ConfigText(default=defaultLanguage)
config.osd.language.addNotifier(localeNotifier)

config.misc.country = ConfigText(default=defaultCountry)
config.misc.language = ConfigText(default=defaultShortLanguage)
config.misc.locale = ConfigText(default=defaultLanguage)
# TODO
# config.misc.locale.addNotifier(localeNotifier)


# These entries should be moved back to UsageConfig.py when it is safe to bring UsageConfig init to this location in StartEnigma2.py.
#
config.crash = ConfigSubsection()
config.crash.debugActionMaps = ConfigYesNo(default=False)
config.crash.debugKeyboards = ConfigYesNo(default=False)
config.crash.debugRemoteControls = ConfigYesNo(default=False)
config.crash.debugScreens = ConfigYesNo(default=False)

# config.plugins needs to be defined before InputDevice < HelpMenu < MessageBox < InfoBar
config.plugins = ConfigSubsection()
config.plugins.remotecontroltype = ConfigSubsection()
config.plugins.remotecontroltype.rctype = ConfigInteger(default=0)


profile("SimpleSummary")
from Screens import InfoBar
from Screens.SimpleSummary import SimpleSummary

profile("Bouquets")
config.misc.load_unlinked_userbouquets = ConfigYesNo(default=False)
config.misc.load_unlinked_userbouquets.addNotifier(setLoadUnlinkedUserbouquets)
enigma.eDVBDB.getInstance().reloadBouquets()

profile("ParentalControl")
import Components.ParentalControl
Components.ParentalControl.InitParentalControl()

profile("LOAD:Navigation")
from Navigation import Navigation

profile("LOAD:skin")
from skin import readSkin

profile("LOAD:Tools")
from Components.config import configfile, ConfigSelection, NoSave, ConfigSubsection
from Tools.Directories import InitFallbackFiles, resolveFilename, SCOPE_PLUGINS, SCOPE_ACTIVE_SKIN, SCOPE_CURRENT_SKIN, SCOPE_CONFIG
import Components.RecordingConfig
InitFallbackFiles()

profile("config.misc")
config.misc.boxtype = ConfigText(default=boxtype)
config.misc.blackradiopic = ConfigText(default=resolveFilename(SCOPE_ACTIVE_SKIN, "black.mvi"))
radiopic = resolveFilename(SCOPE_ACTIVE_SKIN, "radio.mvi")
if os.path.exists(resolveFilename(SCOPE_CONFIG, "radio.mvi")):
	radiopic = resolveFilename(SCOPE_CONFIG, "radio.mvi")
config.misc.radiopic = ConfigText(default=radiopic)
#config.misc.isNextRecordTimerAfterEventActionAuto = ConfigYesNo(default=False)
#config.misc.isNextPowerTimerAfterEventActionAuto = ConfigYesNo(default=False)
config.misc.nextWakeup = ConfigText(default="-1,-1,-1,0,0,-1,0")	#last shutdown time, wakeup time, timer begins, set by (0=rectimer,1=zaptimer, 2=powertimer or 3=plugin), go in standby, next rectimer, force rectimer
config.misc.SyncTimeUsing = ConfigSelection(default="0", choices=[("0", _("Transponder Time")), ("1", _("NTP"))])
config.misc.NTPserver = ConfigText(default='pool.ntp.org', fixed_size=False)

config.misc.startCounter = ConfigInteger(default=0) # number of e2 starts...
config.misc.standbyCounter = NoSave(ConfigInteger(default=0)) # number of standby
config.misc.DeepStandby = NoSave(ConfigYesNo(default=False)) # detect deepstandby

config.misc.SyncTimeUsing.addNotifier(useSyncUsingChanged)
config.misc.NTPserver.addNotifier(NTPserverChanged, immediate_feedback=True)

profile("LOAD:Plugin")
# initialize autorun plugins and plugin menu entries
from Components.PluginComponent import plugins

profile("LOAD:Wizard")
config.misc.rcused = ConfigInteger(default=1)
from Screens.StartWizard import *
from Tools.BoundFunction import boundFunction
from Plugins.Plugin import PluginDescriptor

# display
profile("LOAD:ScreenGlobals")
from Screens.Globals import Globals
from Screens.SessionGlobals import SessionGlobals
from Screens.Screen import Screen

profile("Screen")
Screen.globalScreen = Globals()

profile("Standby,PowerKey")
import Screens.Standby
from Screens.Menu import MainMenu, mdom
from GlobalActions import globalActionMap

profile("Scart")
from Screens.Scart import Scart

profile("Load:CI")
from Screens.Ci import CiHandler

profile("Load:VolumeControl")
from Components.VolumeControl import VolumeControl

profile("Load:StackTracePrinter")
from Components.StackTrace import StackTracePrinter
StackTracePrinterInst = StackTracePrinter()

from time import time, localtime, strftime
from Tools.StbHardware import setFPWakeuptime, setRTCtime

profile("Init:skin")
from skin import InitSkins
InitSkins()

profile("InputDevice")
import Components.InputDevice
Components.InputDevice.InitInputDevices()
import Components.InputHotplug

profile("AVSwitch")
import Components.AVSwitch
Components.AVSwitch.InitAVSwitch()
Components.AVSwitch.InitiVideomodeHotplug()

profile("HdmiRecord")
import Components.HdmiRecord
Components.HdmiRecord.InitHdmiRecord()

profile("RecordingConfig")
import Components.RecordingConfig
Components.RecordingConfig.InitRecordingConfig()

profile("UsageConfig")
import Components.UsageConfig
Components.UsageConfig.InitUsageConfig()

profile("TimeZones")
import Components.Timezones
Components.Timezones.InitTimeZones()

profile("Init:DebugLogCheck")
import Screens.LogManager
Screens.LogManager.AutoLogManager()

#profile("Init:OnlineCheckState")
#import Components.OnlineUpdateCheck
#Components.OnlineUpdateCheck.OnlineUpdateCheck()

profile("Init:NTPSync")
import Components.NetworkTime
Components.NetworkTime.AutoNTPSync()

profile("keymapparser")
import keymapparser
keymapparser.readKeymap(config.usage.keymap.value)
keymapparser.readKeymap(config.usage.keytrans.value)
if os.path.exists(config.usage.keymap_usermod.value):
	keymapparser.readKeymap(config.usage.keymap_usermod.value)

profile("Network")
import Components.Network
Components.Network.InitNetwork()

profile("LCD")
import Components.Lcd
Components.Lcd.InitLcd()
Components.Lcd.IconCheck()
# Disable internal clock vfd for ini5000 until we can adjust it for standby
if boxtype in ('uniboxhd1', 'uniboxhd2', 'uniboxhd3', 'sezam5000hd', 'mbtwin', 'beyonwizt3'):
	try:
		f = open("/proc/stb/fp/enable_clock", "r").readline()[:-1]
		if f != '0':
			f = open("/proc/stb/fp/enable_clock", "w")
			f.write('0')
			f.close()
	except:
		print("Error disable enable_clock for ini5000 boxes")

if boxtype in ('dm7080', 'dm820', 'dm900', 'dm920', 'gb7252'):
	f = open("/proc/stb/hdmi-rx/0/hdmi_rx_monitor", "r")
	check = f.read()
	f.close()
	if check.startswith("on"):
		f = open("/proc/stb/hdmi-rx/0/hdmi_rx_monitor", "w")
		f.write("off")
		f.close()
	f = open("/proc/stb/audio/hdmi_rx_monitor", "r")
	check = f.read()
	f.close()
	if check.startswith("on"):
		f = open("/proc/stb/audio/hdmi_rx_monitor", "w")
		f.write("off")
		f.close()

profile("UserInterface")
import Screens.UserInterfacePositioner
Screens.UserInterfacePositioner.InitOsd()

profile("EpgCacheSched")
import Components.EpgLoadSave
Components.EpgLoadSave.EpgCacheSaveCheck()
Components.EpgLoadSave.EpgCacheLoadCheck()

profile("RFMod")
import Components.RFmod
Components.RFmod.InitRFmod()

profile("Init:CI")
import Screens.Ci
Screens.Ci.InitCiConfig()

profile("RcModel")
import Components.RcModel

#from enigma import dump_malloc_stats
#t = eTimer()
#t.callback.append(dump_malloc_stats)
#t.start(1000)

# first, setup a screen
try:
	runScreenTest()

	plugins.shutdown()

	Components.ParentalControl.parentalControl.save()
except:
	print('EXCEPTION IN PYTHON STARTUP CODE:')
	print('-' * 60)
	print_exc(file=stdout)
	print("[StartEnigma.py] quitMainloop #4")
	enigma.quitMainloop(5)
	print('-' * 60)
