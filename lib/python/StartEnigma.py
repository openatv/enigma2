import os
import sys
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


class PowerKey:
	"""PowerKey code - Handles the powerkey press and powerkey release actions."""

	def __init__(self, session):
		self.session = session
		globalActionMap.actions["power_down"] = self.powerdown
		globalActionMap.actions["power_up"] = self.powerup
		globalActionMap.actions["power_long"] = self.powerlong
		globalActionMap.actions["deepstandby"] = self.shutdown  # Frontpanel long power button press.
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
		from Screens.SleepTimer import SleepTimerButton
		self.session.open(SleepTimerButton)

	def setSleepTimer(self, val):
		from PowerTimer import PowerTimerEntry
		sleeptime = 15
		data = (int(time() + 60), int(time() + 120))
		self.addSleepTimer(PowerTimerEntry(checkOldTimers=True, *data, timerType=val, autosleepdelay=sleeptime))

	def addSleepTimer(self, timer):
		from Screens.Timers import PowerTimerEdit
		self.session.openWithCallback(self.finishedAdd, PowerTimerEdit, timer)

	def finishedAdd(self, answer):
		if not isinstance(answer, bool) and answer[0]:
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
		# print("[StartEnigma] VCR SB changed to '%s'." % value)
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
	profile("ReadPluginList")
	enigma.pauseInit()
	plugins.readPluginList(resolveFilename(SCOPE_PLUGINS))
	enigma.resumeInit()
	profile("Init:Session")
	nav = Navigation(config.misc.nextWakeup.value)
	session = Session(desktop=enigma.getDesktop(0), summaryDesktop=enigma.getDesktop(1), navigation=nav)
	CiHandler.setSession(session)
	from Screens.SwapManager import SwapAutostart
	SwapAutostart()
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
			os.system("rm -f /media/hdd/images/config/autorestore")
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
	if BoxInfo.getItem("VFDSymbols"):
		profile("VFDSYMBOLS")
		import Components.VfdSymbols
		Components.VfdSymbols.SymbolsCheck(session)
	# We need session.scart to access it from within menu.xml.
	session.scart = AutoScartControl(session)
	profile("InitTrashcan")
	import Tools.Trashcan
	Tools.Trashcan.init(session)
	profile("Init:AutoVideoMode")
	import Screens.VideoMode
	Screens.VideoMode.autostart(session)
	profile("Init:VolumeAdjust")
	import Screens.VolumeAdjust
	Screens.VolumeAdjust.autostart(session)
	profile("RunReactor")
	profile_final()
	if BOX_TYPE in ("sf8", "classm", "axodin", "axodinc", "starsatlx", "genius", "evo"):
		f = open("/dev/dbox/oled0", "w")
		f.write("-E2-")
		f.close()
	print("[StartEnigma] Last shutdown=%s.  (True = last shutdown was OK.)" % config.usage.shutdownOK.value)
	print("[StartEnigma] NOK shutdown action=%s." % config.usage.shutdownNOK_action.value)
	print("[StartEnigma] Boot action=%s." % config.usage.boot_action.value)
	if not config.usage.shutdownOK.value and not config.usage.shutdownNOK_action.value == "normal" or not config.usage.boot_action.value == "normal":
		print("[StartEnigma] Last shutdown=%s." % config.usage.shutdownOK.value)
		import Screens.PowerLost
		Screens.PowerLost.PowerLost(session)
	if not RestoreSettings:
		config.usage.shutdownOK.setValue(False)
		config.usage.shutdownOK.save()
		configfile.save()
	# Kill showiframe if it is running.  (sh4 hack...)
	if MODEL in ("spark", "spark7162"):
		os.system("killall -9 showiframe")
	runReactor()
	print("[StartEnigma] Normal shutdown.")
	config.misc.startCounter.save()
	config.usage.shutdownOK.setValue(True)
	config.usage.shutdownOK.save()
	profile("Wakeup")
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
	# Power timer.
	tmp = session.nav.PowerTimer.getNextPowerManagerTime(getNextStbPowerOn=True)
	nextPowerTime = tmp[0]
	nextPowerTimeInStandby = tmp[1]
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
		(nextPowerTime, 2, nextPowerTimeInStandby),
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
			2: "power-timer",
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
		if not BOX_TYPE.startswith("azboxm"):  # Skip for Azbox (mini)ME - setting wakeup time to past reboots box.
			setFPWakeuptime(int(nowTime) - 3600)  # Minus one hour -> overwrite old wakeup time.
		print("[StartEnigma] No next wakeup time set.")
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

from sys import stdout

MODULE_NAME = __name__.split(".")[-1]

profile("Twisted")
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

	logger = log.FileLogObserver(stdout)
	log.FileLogObserver.emit = quietEmit
	stdoutBackup = sys.stdout  # Backup stdout and stderr redirections.
	stderrBackup = sys.stderr
	log.startLoggingWithObserver(logger.emit)
	sys.stdout = stdoutBackup  # Restore stdout and stderr redirections because of twisted redirections.
	sys.stderr = stderrBackup

except ImportError:
	print("[StartEnigma] Error: Twisted not available!")

profile("SystemInfo")
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
	import usb.core
	import usb.backend.libusb1
	usb.backend.libusb1.get_backend(find_library=lambda x: "/lib64/libusb-1.0.so.0")

from traceback import print_exc
from Components.config import config, ConfigYesNo, ConfigSubsection, ConfigInteger, ConfigText, ConfigOnOff, ConfigSelection

# Initialize the country, language and locale data.
#
profile("InternationalLocalization")
from Components.International import international

config.osd = ConfigSubsection()

if DISPLAYBRAND == "Atto.TV":
	defaultLocale = "pt_BR"
elif DISPLAYBRAND == "Zgemma":
	defaultLocale = "en_US"
elif DISPLAYBRAND == "Beyonwiz":
	defaultLocale = "en_AU"
else:
	defaultLocale = "de_DE"
config.misc.locale = ConfigText(default=defaultLocale)
config.misc.language = ConfigText(default=international.getLanguage(defaultLocale))
config.misc.country = ConfigText(default=international.getCountry(defaultLocale))
config.osd.language = ConfigText(default=defaultLocale)
config.osd.language.addNotifier(localeNotifier)
# TODO
# config.misc.locale.addNotifier(localeNotifier)

# These entries should be moved back to UsageConfig.py when it is safe to bring UsageConfig init to this location in StartEnigma.py.
#
config.crash = ConfigSubsection()
config.crash.debugMultiBoot = ConfigYesNo(default=False)
config.crash.debugActionMaps = ConfigYesNo(default=False)
config.crash.debugKeyboards = ConfigYesNo(default=False)
config.crash.debugOpkg = ConfigYesNo(default=False)
config.crash.debugRemoteControls = ConfigYesNo(default=False)
config.crash.debugScreens = ConfigYesNo(default=False)
config.crash.debugEPG = ConfigYesNo(default=False)
config.crash.debugDVBScan = ConfigYesNo(default=False)
config.crash.debugTimers = ConfigYesNo(default=False)

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

profile("Keyboard")
from Components.InputDevice import keyboard


def keyboardNotifier(configElement):
	keyboard.activateKeyboardMap(configElement.index)


config.keyboard = ConfigSubsection()
config.keyboard.keymap = ConfigSelection(default=keyboard.getDefaultKeyboardMap(), choices=keyboard.getKeyboardMaplist())
config.keyboard.keymap.addNotifier(keyboardNotifier)

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
from Components.config import ConfigSubsection, NoSave, configfile
from Tools.Directories import InitDefaultPaths, SCOPE_CONFIG, SCOPE_GUISKIN, SCOPE_PLUGINS, resolveFilename
import Components.RecordingConfig
InitDefaultPaths()

profile("config.misc")
config.misc.boxtype = ConfigText(default=BOX_TYPE)
config.misc.blackradiopic = ConfigText(default=resolveFilename(SCOPE_GUISKIN, "black.mvi"))
radiopic = resolveFilename(SCOPE_GUISKIN, "radio.mvi")
if os.path.exists(resolveFilename(SCOPE_CONFIG, "radio.mvi")):
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

profile("LOAD:Plugin")
# Initialize autorun plugins and plugin menu entries.
from Components.PluginComponent import plugins

profile("LOAD:Wizard")
config.misc.rcused = ConfigInteger(default=1)
from Screens.StartWizard import *
from Tools.BoundFunction import boundFunction
from Plugins.Plugin import PluginDescriptor

# Display.
profile("LOAD:ScreenGlobals")
from Screens.Globals import Globals
from Screens.SessionGlobals import SessionGlobals
from Screens.Screen import Screen

profile("Screen")
Screen.globalScreen = Globals()

profile("Standby,PowerKey")
import Screens.Standby
from Screens.Menu import Menu, findMenu
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

profile("Init:NTPSync")
from Components.NetworkTime import ntpSyncPoller
ntpSyncPoller.startTimer()

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
# Disable internal clock vfd for ini5000 until we can adjust it for standby.
if BOX_TYPE in ("uniboxhd1", "uniboxhd2", "uniboxhd3", "sezam5000hd", "mbtwin", "beyonwizt3"):
	try:
		f = open("/proc/stb/fp/enable_clock", "r").readline()[:-1]
		if f != "0":
			f = open("/proc/stb/fp/enable_clock", "w")
			f.write("0")
			f.close()
	except:
		print("[StartEnigma] Error: Disable enable_clock for ini5000 boxes!")

if BOX_TYPE in ("dm7080", "dm820", "dm900", "dm920", "gb7252"):
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
	Components.ParentalControl.parentalControl.save()  # Save parental control settings.
except Exception:
	print("Error: Exception in Python StartEnigma startup code:")
	print("=" * 52)
	print_exc(file=stdout)
	print("[StartEnigma] Exiting via quitMainloop #4.")
	enigma.quitMainloop(5)  # QUIT_ERROR_RESTART
	print("-" * 52)
