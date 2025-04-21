from errno import ENOENT
from os import remove
from os.path import exists
import sys  # This is needed for the twisted redirection access to stderr and stdout.
from time import time

import Tools.RedirectOutput  # Don't remove this line. This import facilitates connecting stdout and stderr redirections to the log files.

import enigma  # Establish enigma2 connections to processing methods.
import eBaseImpl
import eConsoleImpl
enigma.eTimer = eBaseImpl.eTimer
enigma.eSocketNotifier = eBaseImpl.eSocketNotifier
enigma.eConsoleAppContainer = eConsoleImpl.eConsoleAppContainer

MODULE_NAME = "StartEnigma"  # This is done here as "__name__.split(".")[-1]" returns "__main__" for this module.


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
		self.onShutdown = []
		self.summary = None
		self.in_exec = False
		self.screen = SessionGlobals(self)
		self.shutdown = False
		from Components.FrontPanelLed import frontPanelLed
		frontPanelLed.init(self)
		self.allDialogs = []

		for plugin in plugins.getPlugins(PluginDescriptor.WHERE_SESSIONSTART):
			try:
				plugin.__call__(reason=0, session=self)
			except:
				print("[StartEnigma] Error: Plugin raised exception at WHERE_SESSIONSTART!")
				from traceback import print_exc
				print_exc()

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
		if screen in self.allDialogs:
			self.allDialogs.remove(screen)
		screen.hide()
		screen.doClose()

	def deleteDialogWithCallback(self, callback, screen, *retVal):
		self.deleteDialog(screen)
		if callback is not None:
			callback(*retVal)

	def instantiateSummaryDialog(self, screen, **kwargs):
		if self.summaryDesktop is not None:
			self.pushSummary()
			summary = screen.createSummary() or ScreenSummary
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
		if not hasattr(dialog, "noSkinReload"):
			self.allDialogs.append(dialog)
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
		if dialog != "config.crash.bsodpython.value=True":
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
				return "config.crash.bsodpython.value=True"
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

	def doShutdown(self):
		for callback in self.onShutdown:
			if callable(callback):
				callback()

	def reloadDialogs(self):
		for dialog in self.allDialogs:
			if hasattr(dialog, "desktop"):
				oldDesktop = dialog.desktop
				readSkin(dialog, None, dialog.skinName, oldDesktop)
				dialog.applySkin()


class PowerKey:
	"""PowerKey code - Handles the powerkey press and powerkey release actions."""

	def __init__(self, session):
		self.session = session
		globalActionMap.actions["power_down"] = self.powerdown
		globalActionMap.actions["power_up"] = self.powerup
		globalActionMap.actions["power_long"] = self.powerlong
		globalActionMap.actions["deepstandby"] = self.shutdown  # Front panel long power button press.
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
		if Screens.Standby.TVinStandby.getTVstate("standby"):
			Screens.Standby.TVinStandby.setTVstate("on")
			return

		self.standbyblocked = 1
		if action == "shutdown":
			self.shutdown()
		elif action == "show_menu":
			print("[StartEnigma] Show shutdown menu.")
			menu = findMenu("shutdown")
			if menu:
				self.session.infobar = self
				self.session.openWithCallback(self.MenuClosed, Menu, menu)
				return
		elif action == "standby":
			Screens.Standby.TVinStandby.skipHdmiCecNow(False)
			self.standby()
		elif action == "standby_noTVshutdown":
			Screens.Standby.TVinStandby.skipHdmiCecNow(True)
			self.standby()
		elif action == "schedulerStandby":
			val = 3
			self.setSleepTimer(val)
		elif action == "schedulerDeepStandby":
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
		from Screens.SleepTimer import SleepTimerButton
		self.session.open(SleepTimerButton)

	def setSleepTimer(self, val):
		from Scheduler import SchedulerEntry
		sleeptime = 15
		data = (int(time() + 60), int(time() + 120))
		self.addSleepTimer(SchedulerEntry(checkOldTimers=True, *data, timerType=val, autosleepdelay=sleeptime))

	def addSleepTimer(self, timer):
		from Screens.Timers import SchedulerEdit
		self.session.openWithCallback(self.finishedAdd, SchedulerEdit, timer)

	def finishedAdd(self, answer):
		if not isinstance(answer, bool) and answer[0]:
			entry = answer[1]
			simulTimerList = self.session.nav.Scheduler.record(entry)

	def sleepStandby(self):
		self.doAction(action="schedulerStandby")

	def sleepDeepStandby(self):
		self.doAction(action="schedulerDeepStandby")


class AutoScartControl:
	def __init__(self, session):
		self.hasScart = BoxInfo.getItem("scart")
		if self.hasScart:
			self.force = False
			self.current_vcr_sb = enigma.eAVControl.getInstance().getVCRSlowBlanking()
			if self.current_vcr_sb and config.av.vcrswitch.value:
				self.scartDialog = session.instantiateDialog(Scart, True)
			else:
				self.scartDialog = session.instantiateDialog(Scart, False)
			config.av.vcrswitch.addNotifier(self.recheckVCRSb)
			enigma.eAVControl.getInstance().vcr_sb_notifier.get().append(self.VCRSbChanged)

	def recheckVCRSb(self, configelement):
		self.VCRSbChanged(self.current_vcr_sb)

	def VCRSbChanged(self, value):
		if self.hasScart:
			# print("[StartEnigma] VCR SB changed to '%s'." % value)
			self.current_vcr_sb = value
			if config.av.vcrswitch.value or value > 2:
				if value:
					self.scartDialog.showMessageBox()
				else:
					self.scartDialog.switchToTV()


def runScreenTest():
	def autorestoreLoop():  # Check if auto restore settings fails, just start the wizard (avoid a endless loop).
		count = 0
		filename = "/media/hdd/images/config/autorestore"
		if exists(filename):
			try:
				with open(filename) as fd:
					line = fd.read().strip().replace("\0", "")
					count = int(line) if line.isdecimal() else 0
				if count >= 3:
					return False
			except OSError as err:
				print("[StartEnigma] Error %d: Unable to read a line from file '%s'!  (%s)" % (err.errno, filename, err.strerror))
		count += 1
		try:
			with open(filename, "w") as fd:
				fd.write(str(count))
		except OSError as err:
			print("[StartEnigma] Error %d: Unable to write a line to file '%s'!  (%s)" % (err.errno, filename, err.strerror))
			return False
		return True

	def runNextScreen(session, screensToRun, *result):
		if result:
			print("[StartEnigma] Exiting via quitMainloop #3.")
			enigma.quitMainloop(*result)
			return
		screen = screensToRun[0][1]
		args = screensToRun[0][2:]
		if screensToRun:
			session.openWithCallback(boundFunction(runNextScreen, session, screensToRun[1:]), screen, *args)
		else:
			session.open(screen, *args)

	config.misc.startCounter.value += 1
	enigma.eProfileWrite("ReadPluginList")
	enigma.pauseInit()
	plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))
	enigma.resumeInit()
	enigma.eProfileWrite("Session")
	nav = Navigation(config.misc.nextWakeup.value)
	session = Session(desktop=enigma.getDesktop(0), summaryDesktop=enigma.getDesktop(1), navigation=nav)
	CiHandler.setSession(session)
	from Screens.SwapManager import SwapAutostart
	SwapAutostart()
	enigma.eProfileWrite("Wizards")
	screensToRun = []
	RestoreSettings = None
	if exists("/media/hdd/images/config/settings") and config.misc.firstrun.value:
		if autorestoreLoop():
			RestoreSettings = True
			from Plugins.SystemPlugins.SoftwareManager.BackupRestore import RestoreScreen
			session.open(RestoreScreen, runRestore=True)
		else:
			screensToRun = [p.__call__ for p in plugins.getPlugins(PluginDescriptor.WHERE_WIZARD)]
			screensToRun += wizardManager.getWizards()
	else:
		filename = "/media/hdd/images/config/autorestore"
		try:
			remove(filename)
		except OSError as err:
			if err.errno != ENOENT:  # ENOENT - No such file or directory.
				print("[StartEnigma] Error %d: Unable to delete file '%s'!  (%s)" % (err.errno, filename, err.strerror))
		screensToRun = [p.__call__ for p in plugins.getPlugins(PluginDescriptor.WHERE_WIZARD)]
		screensToRun += wizardManager.getWizards()
	screensToRun.append((100, InfoBar.InfoBar))
	screensToRun.sort()
	print(screensToRun)
	enigma.ePythonConfigQuery.setQueryFunc(configfile.getResolvedKey)
	if not RestoreSettings:
		runNextScreen(session, screensToRun)
	enigma.eProfileWrite("VolumeControl Screen")
	vol = VolumeControl(session)
	enigma.eProfileWrite("VolumeAdjust")
	vol = VolumeAdjust(session)
	enigma.eProfileWrite("Processing Screen")
	processing = Processing(session)
	enigma.eProfileWrite("Global MessageBox Screen")
	modalmessagebox = ModalMessageBox(session)
	enigma.eProfileWrite("PowerKey")
	power = PowerKey(session)
	if enigma.getVFDSymbolsPoll():
		enigma.eProfileWrite("VFDSymbolsCheck")
		from Components.VfdSymbols import SymbolsCheck
		SymbolsCheck(session)
	# We need session.scart to access it from within menu.xml.
	session.scart = AutoScartControl(session)
	enigma.eProfileWrite("InitTrashcan")
	from Tools.Trashcan import initTrashcan
	initTrashcan(session)
	enigma.eProfileWrite("VideoModeAutoStart")
	from Screens.VideoMode import autostart
	autostart(session)
	enigma.eProfileWrite("RunReactor")
	enigma.eProfileDone()
	if BOX_TYPE in ("sf8", "classm", "axodin", "axodinc", "starsatlx", "genius", "evo"):
		fileUpdateLine("/dev/dbox/oled0", conditionValue=None, replacementValue="-E2-", create=True, source=MODULE_NAME)
	print("[StartEnigma] Last shutdown=%s.  (True = last shutdown was OK.)" % config.usage.shutdownOK.value)
	print("[StartEnigma] NOK shutdown action=%s." % config.usage.shutdownNOK_action.value)
	print("[StartEnigma] Boot action=%s." % config.usage.boot_action.value)
	if not config.usage.shutdownOK.value and not config.usage.shutdownNOK_action.value == "normal" or not config.usage.boot_action.value == "normal":
		print("[StartEnigma] Last shutdown=%s." % config.usage.shutdownOK.value)
		from Screens.PowerLost import PowerLost
		PowerLost(session)
	if not RestoreSettings:
		config.usage.shutdownOK.setValue(False)
		config.usage.shutdownOK.save()
		configfile.save()
	from Components.FrontPanelLed import FrontPanelLed
	runReactor()
	session.shutdown = True
	FrontPanelLed.shutdown()
	print("[StartEnigma] Normal shutdown.")
	config.misc.startCounter.save()
	config.usage.shutdownOK.setValue(True)
	config.usage.shutdownOK.save()
	nowTime = time()  # Get currentTime.
	# if config.misc.SyncTimeUsing.value != "0" or BRAND == "gigablue":
	if config.misc.SyncTimeUsing.value != "0" or BOX_TYPE.startswith("gb") or BRAND.startswith("ini"):
		print("[StartEnigma] DVB time sync disabled, so set RTC now to current Linux time!  (%s)" % strftime("%Y/%m/%d %H:%M", localtime(nowTime)))
		setRTCtime(nowTime)
	# Record timer.
	if session.nav.isRecordTimerImageStandard:  # Check RecordTimer instance.
		tmp = session.nav.RecordTimer.getNextRecordingTime(getNextStbPowerOn=True)
		nextRecordTime = tmp[0]
		nextRecordTimeInStandby = tmp[1]
	else:
		nextRecordTime = session.nav.RecordTimer.getNextRecordingTime()
		nextRecordTimeInStandby = session.nav.RecordTimer.isNextRecordAfterEventActionAuto()
	# Zap timer.
	nextZapTime = session.nav.RecordTimer.getNextZapTime()
	nextZapTimeInStandby = 0
	# Scheduler timer.
	tmp = session.nav.Scheduler.getNextPowerManagerTime(getNextStbPowerOn=True)
	nextScheduler = tmp[0]
	nextSchedulerInStandby = tmp[1]
	# Plugin timer.
	tmp = plugins.getNextWakeupTime(getPluginIdent=True)
	nextPluginTime = tmp[0]
	nextPluginIdent = tmp[1]  # "pluginname | pluginfolder"
	tmp = tmp[1].lower()
	# Start in standby, depending on plugin type.
	if "epgrefresh" in tmp:
		nextPluginName = "EPGRefresh"
		nextPluginTimeInStandby = 1
	elif "vps" in tmp:
		nextPluginName = "VPS"
		nextPluginTimeInStandby = 1
	elif "serienrecorder" in tmp:
		nextPluginName = "SerienRecorder"
		nextPluginTimeInStandby = 0  # Plugin function for deep standby from standby not compatible (not available).
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
		# Default for plugins.
		nextPluginName = nextPluginIdent
		nextPluginTimeInStandby = 0
	wakeupList = [x for x in (
		(nextRecordTime, 0, nextRecordTimeInStandby),
		(nextZapTime, 1, nextZapTimeInStandby),
		(nextScheduler, 2, nextSchedulerInStandby),
		(nextPluginTime, 3, nextPluginTimeInStandby)
	) if x[0] != -1]
	wakeupList.sort()
	print("=" * 100)
	if wakeupList and wakeupList[0][0] > 0:
		startTime = wakeupList[0]
		# Wakeup time before timer begins.
		wptime = startTime[0] - (config.workaround.wakeuptime.value * 60)
		if (wptime - nowTime) < 120:  # No time to switch box back on.
			wptime = int(nowTime) + 120  # So switch back on in 120 seconds.
		# Check for plugin-, zap- or power-timer to enable the 'forced' record-timer wakeup.
		forceNextRecord = 0
		setStandby = startTime[2]
		if startTime[1] != 0 and nextRecordTime > 0:
			# When next record starts in 15 mins.
			if abs(nextRecordTime - startTime[0]) <= 900:
				setStandby = forceNextRecord = 1
			# By vps-plugin.
			elif startTime[1] == 3 and nextPluginName == "VPS":
				setStandby = forceNextRecord = 1
		if startTime[1] == 3:
			nextPluginName = " (%s)" % nextPluginName
		else:
			nextPluginName = ""
		print("[StartEnigma] Set next wakeup type to '%s'%s %s" % ({
			0: "record-timer",
			1: "zap-timer",
			2: "scheduler",
			3: "plugin-timer"
		}[startTime[1]], nextPluginName, {
			0: "and starts normal",
			1: "and starts in standby"
		}[setStandby]))
		if forceNextRecord:
			print("[StartEnigma] Set from 'vps-plugin' or just before a 'record-timer' starts, set 'record-timer' wakeup flag.")
		print("[StartEnigma] Set next wakeup time to %s." % strftime("%a, %Y/%m/%d %H:%M:%S", localtime(wptime)))
		# Set next wakeup.
		setFPWakeuptime(wptime)
		# Set next standby only after shutdown in deep standby.
		if Screens.Standby.quitMainloopCode != 1 and Screens.Standby.quitMainloopCode != 45:
			setStandby = 2  # 0=no standby, but get in standby if wakeup to timer start > 60 sec (not for plugin-timer, here is no standby), 1=standby, 2=no standby, when before was not in deep-standby.
		config.misc.nextWakeup.value = "%d,%d,%d,%d,%d,%d,%d" % (int(nowTime), wptime, startTime[0], startTime[1], setStandby, nextRecordTime, forceNextRecord)
	else:
		config.misc.nextWakeup.value = "%d,-1,-1,0,0,-1,0" % (int(nowTime))
		setFPWakeuptime(int(nowTime) - 3600)  # Minus one hour -> overwrite old wakeup time.
		print("[StartEnigma] No next wakeup time set.")
	config.misc.nextWakeup.save()
	print("=" * 100)
	session.nav.stopService()
	session.nav.shutdown()
	session.doShutdown()
	configfile.save()
	from Screens.InfoBarGenerics import saveResumePoints
	saveResumePoints()
	return 0


def localeNotifier(configElement):
	international.activateLocale(configElement.value)


def setLoadUnlinkedUserbouquets(configElement):
	enigma.eDVBDB.getInstance().setLoadUnlinkedUserbouquets(configElement.value)


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
				print("[StartEnigma] Dump: %s/%s:%s(cycle)" % (p, str(name), str(dir.__class__)))
	else:
		print("[StartEnigma] Dump: %s:%s" % (p, str(dir)))  # + ":" + str(dir.__class__)


# Demo code for use of standby enter leave callbacks.
#
# def leaveStandby():
# 	print("[StartEnigma] Leaving standby.")
#
#
# def standbyCountChanged(configElement):
# 	print("[StartEnigma] Enter standby number %s." % configElement.value)
# 	from Screens.Standby import inStandby
# 	inStandby.onClose.append(leaveStandby)
#
#
# config.misc.standbyCounter.addNotifier(standbyCountChanged, initial_call=False)

#################################
#                               #
#  Code execution starts here!  #
#                               #
#################################

enigma.eProfileWrite("Twisted")
print("[StartEnigma] Initializing Twisted.")
try:  # Configure the twisted processor.
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

try:  # Configure the twisted logging.
	from twisted.python import log, util

	def quietEmit(self, eventDict):
		text = log.textFromEventDict(eventDict)
		if text is None:
			return
		if "/api/statusinfo" in text:  # Do not log OpenWebif status info.
			return
		# Log with time stamp.
		#
		# timeStr = self.formatTime(eventDict["time"])
		# fmtDict = {
		# 	"ts": timeStr,
		# 	"system": eventDict["system"],
		# 	"text": text.replace("\n", "\n\t")
		# }
		# msgStr = log._safeFormat("%(ts)s [%(system)s] %(text)s\n", fmtDict)
		#
		# Log without time stamp.
		#
		fmtDict = {
			"text": text.replace("\n", "\n\t")
		}
		msgStr = log._safeFormat("%(text)s\n", fmtDict)
		util.untilConcludes(self.write, msgStr)
		util.untilConcludes(self.flush)

	logger = log.FileLogObserver(sys.stdout)
	log.FileLogObserver.emit = quietEmit
	stdoutBackup = sys.stdout  # Backup stdout and stderr redirections.
	stderrBackup = sys.stderr
	log.startLoggingWithObserver(logger.emit)
	sys.stdout = stdoutBackup  # Restore stdout and stderr redirections because of twisted redirections.
	sys.stderr = stderrBackup

except ImportError:
	print("[StartEnigma] Error: Twisted not available!")

# Initialize the country, language and locale data.
#
enigma.eProfileWrite("International")
from Components.International import international

enigma.eProfileWrite("BoxInfo")
from enigma import getE2Rev
from Components.SystemInfo import BoxInfo

BRAND = BoxInfo.getItem("brand")
BOX_TYPE = BoxInfo.getItem("machinebuild")
MODEL = BoxInfo.getItem("model")
DISPLAYBRAND = BoxInfo.getItem("displaybrand")

print("[StartEnigma] Receiver name = %s %s" % (DISPLAYBRAND, BoxInfo.getItem("displaymodel")))
print("[StartEnigma] %s version = %s" % (BoxInfo.getItem("displaydistro"), BoxInfo.getItem("imgversion")))
print("[StartEnigma] %s revision = %s" % (BoxInfo.getItem("displaydistro"), BoxInfo.getItem("imgrevision")))
print("[StartEnigma] Build Brand = %s" % BRAND)
print("[StartEnigma] Build Model = %s" % MODEL)
print("[StartEnigma] Platform = %s" % BoxInfo.getItem("platform"))
print("[StartEnigma] SoC family = %s" % BoxInfo.getItem("socfamily"))
print("[StartEnigma] Enigma2 revision = %s" % getE2Rev())

if BoxInfo.getItem("architecture") in ("aarch64"):
	# import usb.core
	from usb.backend.libusb1 import get_backend
	get_backend(find_library=lambda x: "/lib64/libusb-1.0.so.0")

from traceback import print_exc
from Components.config import config, ConfigYesNo, ConfigSubsection, ConfigInteger, ConfigText, ConfigOnOff, ConfigSelection

defaultLocale = {
	"Atto.TV": "pt_BR",
	"Zgemma": "en_US",
	"Beyonwiz": "en_AU"
}.get(DISPLAYBRAND, "de_DE")
config.misc.locale = ConfigText(default=defaultLocale)
config.misc.locale.addNotifier(localeNotifier)
config.misc.language = ConfigText(default=international.getLanguage(defaultLocale))
config.misc.country = ConfigText(default=international.getCountry(defaultLocale))

# These entries should be moved back to UsageConfig.py when it is safe to bring UsageConfig init to this location in StartEnigma.py.
#
config.crash = ConfigSubsection()
config.crash.debugInternational = ConfigYesNo(default=False)
config.crash.debugMultiBoot = ConfigYesNo(default=False)
config.crash.debugActionMaps = ConfigYesNo(default=False)
config.crash.debugKeyboards = ConfigYesNo(default=False)
config.crash.debugOpkg = ConfigYesNo(default=False)
config.crash.debugRemoteControls = ConfigYesNo(default=False)
config.crash.debugScreens = ConfigYesNo(default=False)
config.crash.debugEPG = ConfigYesNo(default=False)
config.crash.debugDVBScan = ConfigYesNo(default=False)
config.crash.debugDVBTime = ConfigYesNo(default=False)
config.crash.debugDVB = ConfigYesNo(default=False)
config.crash.debugTimers = ConfigYesNo(default=False)
config.crash.debugTeletext = ConfigYesNo(default=False)
config.crash.debugStorage = ConfigYesNo(default=False)

# config.plugins needs to be defined before InputDevice < HelpMenu < MessageBox < InfoBar.
config.plugins = ConfigSubsection()
config.plugins.remotecontroltype = ConfigSubsection()
config.plugins.remotecontroltype.rctype = ConfigInteger(default=0)

config.parental = ConfigSubsection()
config.parental.lock = ConfigOnOff(default=False)
config.parental.setuplock = ConfigOnOff(default=False)

config.expert = ConfigSubsection()
config.expert.satpos = ConfigOnOff(default=True)
config.expert.fastzap = ConfigOnOff(default=True)
config.expert.skipconfirm = ConfigOnOff(default=False)
config.expert.hideerrors = ConfigOnOff(default=False)
config.expert.autoinfo = ConfigOnOff(default=True)

enigma.eProfileWrite("Keyboard")
from Components.InputDevice import keyboard

# These autocam settings need to defined before InfoBar and ChannelSelection are loaded.
config.misc.autocamEnabled = ConfigYesNo(default=False)
config.misc.autocamDefault = ConfigText(default="")

enigma.eProfileWrite("InfoBar")
from Screens import InfoBar

enigma.eProfileWrite("ScreenSummary")
# from Screens.SimpleSummary import SimpleSummary
from Screens.Screen import ScreenSummary

enigma.eProfileWrite("LoadBouquets")
config.misc.load_unlinked_userbouquets = ConfigYesNo(default=False)
config.misc.load_unlinked_userbouquets.addNotifier(setLoadUnlinkedUserbouquets)
enigma.eDVBDB.getInstance().reloadBouquets()

enigma.eProfileWrite("Navigation")
from Navigation import Navigation

enigma.eProfileWrite("ReadSkin")
from skin import readSkin

enigma.eProfileWrite("InitDefaultPaths")
from Components.config import ConfigSubsection, NoSave, configfile
from Tools.Directories import InitDefaultPaths, SCOPE_CONFIG, SCOPE_GUISKIN, SCOPE_PLUGINS, fileUpdateLine, resolveFilename
InitDefaultPaths()

enigma.eProfileWrite("ConfigMisc")
config.misc.boxtype = ConfigText(default=BOX_TYPE)
config.misc.blackradiopic = ConfigText(default=resolveFilename(SCOPE_GUISKIN, "black.mvi"))
radiopic = resolveFilename(SCOPE_GUISKIN, "radio.mvi")
if exists(resolveFilename(SCOPE_CONFIG, "radio.mvi")):
	radiopic = resolveFilename(SCOPE_CONFIG, "radio.mvi")
config.misc.radiopic = ConfigText(default=radiopic)
# config.misc.isNextRecordTimerAfterEventActionAuto = ConfigYesNo(default=False)
# config.misc.isNextPowerTimerAfterEventActionAuto = ConfigYesNo(default=False)
config.misc.nextWakeup = ConfigText(default="-1,-1,-1,0,0,-1,0")  # Last shutdown time, wakeup time, timer begins, set by (0=rectimer,1=zaptimer, 2=powertimer or 3=plugin), go in standby, next rectimer, force rectimer.
config.misc.SyncTimeUsing = ConfigSelection(default="0", choices=[
	("0", _("Transponder Time")),
	("1", _("NTP"))
])
config.misc.NTPserver = ConfigText(default="pool.ntp.org", fixed_size=False)

config.misc.startCounter = ConfigInteger(default=0)  # Number of e2 starts.
config.misc.standbyCounter = NoSave(ConfigInteger(default=0))  # Number of standby.
config.misc.DeepStandby = NoSave(ConfigYesNo(default=False))  # Detect deep standby.

enigma.eProfileWrite("AutoRunPlugins")
# Initialize autorun plugins and plugin menu entries.
from Components.PluginComponent import plugins

enigma.eProfileWrite("StartWizard")
config.misc.rcused = ConfigInteger(default=1)
from Screens.StartWizard import *
from Tools.BoundFunction import boundFunction
from Plugins.Plugin import PluginDescriptor

# Display.
enigma.eProfileWrite("ScreenGlobals")
from Screens.Globals import Globals
from Screens.SessionGlobals import SessionGlobals
from Screens.Screen import Screen
Screen.globalScreen = Globals()

enigma.eProfileWrite("Standby")
import Screens.Standby
from Screens.Menu import Menu, findMenu

enigma.eProfileWrite("GlobalActionMap")
from GlobalActions import globalActionMap

enigma.eProfileWrite("Scart")
from Screens.Scart import Scart

enigma.eProfileWrite("CIHandler")
from Screens.Ci import CiHandler

enigma.eProfileWrite("VolumeControl")
from Screens.VolumeControl import VolumeAdjust, VolumeControl

enigma.eProfileWrite("Processing")
from Screens.Processing import Processing

enigma.eProfileWrite("ModalMessageBox")
from Screens.MessageBox import ModalMessageBox

enigma.eProfileWrite("StackTracePrinter")
from Components.StackTrace import StackTracePrinter
StackTracePrinterInst = StackTracePrinter()

from time import localtime, strftime
from Tools.StbHardware import setFPWakeuptime, setRTCtime

enigma.eProfileWrite("InitSkins")
from skin import InitSkins
InitSkins()

enigma.eProfileWrite("InitInputDevices")
from Components.InputDevice import InitInputDevices
InitInputDevices()
import Components.InputHotplug

enigma.eProfileWrite("InitAVSwitch")
from Components.AVSwitch import InitAVSwitch, InitiVideomodeHotplug
InitAVSwitch()
InitiVideomodeHotplug()

enigma.eProfileWrite("InitHDMIRecord")
from Components.HdmiRecord import InitHdmiRecord
InitHdmiRecord()

enigma.eProfileWrite("InitRecordingConfig")
from Components.RecordingConfig import InitRecordingConfig
InitRecordingConfig()

enigma.eProfileWrite("InitUsageConfig")
from Components.UsageConfig import InitUsageConfig, DEFAULTKEYMAP
InitUsageConfig()

enigma.eProfileWrite("InitPvrDescrambleConvert")
from Components.PvrDescrambleConvert import pvr_descramble_convert

enigma.eProfileWrite("InitTimeZones")
from Components.Timezones import InitTimeZones
InitTimeZones()

enigma.eProfileWrite("AutoLogManager")
from Screens.LogManager import AutoLogManager
AutoLogManager()

enigma.eProfileWrite("NTPSyncPoller")
from Components.NetworkTime import ntpSyncPoller
ntpSyncPoller.startTimer()

enigma.eProfileWrite("KeymapParser")
from Components.ActionMap import loadKeymap
loadKeymap(DEFAULTKEYMAP)
if config.usage.keymap.value != DEFAULTKEYMAP:
	if exists(config.usage.keymap.value):
		loadKeymap(config.usage.keymap.value, replace=True)
if exists(config.usage.keymap_usermod.value):
	loadKeymap(config.usage.keymap_usermod.value)

enigma.eProfileWrite("InitNetwork")
from Components.Network import InitNetwork
InitNetwork()

enigma.eProfileWrite("InitLCD")
from Components.Lcd import IconCheck, InitLcd
InitLcd()
IconCheck()
# Disable internal clock vfd for ini5000 until we can adjust it for standby.
if BOX_TYPE in ("uniboxhd1", "uniboxhd2", "uniboxhd3", "sezam5000hd", "mbtwin", "beyonwizt3"):
	fileUpdateLine("/proc/stb/fp/enable_clock", conditionValue="1", replacementValue="0", source=MODULE_NAME)

enigma.eAVControl.getInstance().disableHDMIIn()

enigma.eProfileWrite("InitOSDCalibration")
from Screens.OSDCalibration import InitOSDCalibration
InitOSDCalibration()

enigma.eProfileWrite("EPGCacheCheck")
from Components.EpgLoadSave import EpgCacheLoadCheck, EpgCacheSaveCheck
EpgCacheSaveCheck()
EpgCacheLoadCheck()

enigma.eProfileWrite("InitRFmod")
from Components.RFmod import InitRFmod
InitRFmod()

enigma.eProfileWrite("InitCiConfig")
from Screens.Ci import InitCiConfig
InitCiConfig()

# ###############################################################################
# NOTE: This migration helper can be used to update Enigma2 settings, files etc #
#       etc that may need to change based on recent code changes.               #
# ###############################################################################
#
from Tools.Migration import migrateSettings  # Migrate settings from older versions of enigma.
migrateSettings()

# from enigma import dump_malloc_stats
# t = eTimer()
# t.callback.append(dump_malloc_stats)
# t.start(1000)

# Lets get going and load a screen.
#
try:
	runScreenTest()  # Start running the first screen.
	plugins.shutdown()  # Shutdown all plugins.
	from Components.ParentalControl import parentalControl
	parentalControl.save()  # Save parental control settings.
except Exception:
	print("Error: Exception in Python StartEnigma startup code:")
	print("=" * 52)
	print_exc(file=sys.stdout)
	print("[StartEnigma] Exiting via quitMainloop #4.")
	enigma.quitMainloop(5)  # QUIT_ERROR_RESTART
	print("-" * 52)
