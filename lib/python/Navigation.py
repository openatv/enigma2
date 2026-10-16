from os import remove
from os.path import exists
from time import ctime, time

from enigma import eServiceCenter, eServiceReference, eStreamServer, eTimer, getBestPlayableServiceReference, iPlayableService, iServiceInformation, iRecordableService, iRecordableServicePtr, pNavigation
from enigma import canDVBIFallbackReleaseForRecording, getDVBIFallbackService, getDVBIPlaybackService, getDVBIServiceAvailability

import NavigationInstance
import RecordTimer
import Scheduler
import ServiceReference
from Components.config import config
from Components.ImportChannels import ImportChannels  # noqa F401
from Components.ParentalControl import parentalControl
from Components.PluginComponent import plugins
from Components.RecordingConfig import recType
from Components.ServiceEventTracker import ServiceEventTracker
from Components.SystemInfo import BoxInfo
from Plugins.Plugin import PluginDescriptor
from Screens.InfoBar import InfoBar, MoviePlayer
from Screens.InfoBarGenerics import streamrelay
from Screens.MessageBox import MessageBox
import Screens.Standby
from Tools.BoundFunction import boundFunction
from Tools.Directories import fileWriteLine
from Tools.StbHardware import getFPWasTimerWakeup
from Tools.Notifications import AddPopup

MODULE_NAME = __name__.split(".")[-1]


# TODO: Move most of the code to pNavgation and remove this stuff from python.
#
class Navigation:
	playServiceExtensions = []
	recordServiceExtensions = []

	TIMER_TYPES = {
		0: "Record-timer",
		1: "Zap-timer",
		2: "Power-timer",
		3: "Plugin-timer"
	}

	def __init__(self, wakeupData=None):
		if NavigationInstance.instance is not None:
			raise NavigationInstance.instance
		NavigationInstance.instance = self  # This is needed to prevent circular imports
		self.ServiceHandler = eServiceCenter.getInstance()
		self.activeStreamings = []
		self.activeStreamingsByClient = {}
		self.indicatorRecordingsCount = None
		self.anyRecordingsCount = None
		self.realRecordingsCount = None
		self.pnav = pNavigation()
		self.pnav.m_event.get().append(self.dispatchEvent)
		self.pnav.m_record_event.get().append(self.dispatchRecordEvent)
		eStreamServer.getInstance().streamStatusChanged.get().append(self.streamStatusChangedCB)
		self.event = []
		self.record_event = []
		self.currentBouquetName = ""
		self.currentlyPlayingServiceReference = None
		self.currentlyPlayingServiceOrGroup = None
		self.currentlyPlayingService = None
		self.originalPlayingServiceReference = None
		Screens.Standby.TVstate()
		self.skipWakeup = False
		self.skipTVWakeup = False
		self.firstStart = True
		self.RecordTimer = None
		self.isRecordTimerImageStandard = False
		self.isCurrentServiceStreamRelay = False
		self.isCurrentServiceDVBI = False
		self.hybridPlaybackService = None
		self.dvbiFailureTimer = None
		self.dvbiFailureService = None
		self.dvbiPlaybackService = None
		self.skipServiceReferenceReset = False
		self.retryServicePlayCount = 0
		self.streamRetryTimer = None
		self.streamRetryService = None
		self.streamRetryCount = 0
		for p in plugins.getPlugins(PluginDescriptor.WHERE_RECORDTIMER):  # Do we really need this?
			self.RecordTimer = p()
			if self.RecordTimer:
				break
		self.Scheduler = Scheduler.Scheduler()  # Initialize Scheduler before RecordTimer.loadTimers.
		if not self.RecordTimer:
			self.RecordTimer = RecordTimer.RecordTimer()
			self.RecordTimer.loadTimers()  # Call loadTimers after initialize of self.RecordTimer.
			self.isRecordTimerImageStandard = True
		self.Scheduler.loadTimers()  # Call loadTimers after initialize of self.Scheduler.
		self.__wasTimerWakeup = False
		self.__wasRecTimerWakeup = False
		self.__wasSchedulerWakeup = False
		if not exists("/etc/enigma2/.deep"):  # Flag file comes from "/usr/bin/enigma2.sh".
			print("=" * 100)
			print("[Navigation] Receiver did not start from Deep Standby. Skip wake up detection.")
			print("=" * 100)
			self.gotopower()
			return
		remove("/etc/enigma2/.deep")
		now = time()  # Wakeup data.
		try:
			self.lastshutdowntime, self.wakeuptime, self.timertime, self.wakeuptyp, self.getstandby, self.recordtime, self.forcerecord = (int(n) for n in wakeupData.split(","))
		except Exception:
			print("=" * 100)
			print("[Navigation] Error: Can't read wakeup data!")
			self.lastshutdowntime, self.wakeuptime, self.timertime, self.wakeuptyp, self.getstandby, self.recordtime, self.forcerecord = int(now), -1, -1, 0, 0, -1, 0
		self.syncCount = 0
		hasFakeTime = (now <= 31536000 or now - self.lastshutdowntime <= 120) and self.getstandby < 2  # Set hasFakeTime only if lower than values and was last shutdown to deep standby.
		wasTimerWakeup, wasTimerWakeup_failure = getFPWasTimerWakeup(True)
		# TODO: Verify wakeup-state for boxes where only after shutdown removed the wakeup-state.
		# For boxes where "/proc/stb/fp/was_timer_wakeup" is not writable (clearFPWasTimerWakeup() in StbHardware.py has no effect -> After x hours and restart/reboot is wasTimerWakeup = True)
		if 0:  # Debug.
			print("#" * 100)
			print(f"[Navigation] Time difference from last shutdown to now is {now - self.lastshutdowntime} seconds.")
			print(f"[Navigation] Shutdown time is '{ctime(self.lastshutdowntime)}', wakeup time is '{ctime(self.wakeuptime)}', timer time is '{ctime(self.timertime)}', record time is '{ctime(self.recordtime)}'.")
			value = {
				0: "No standby",
				1: "Standby",
				2: "No standby (Box was not in deepstandby)"
			}[self.getstandby]
			print(f"[Navigation] Wakeup type is '{self.TIMER_TYPES[self.wakeuptyp]}', getstandby is '{value}', force record is '{self.forcerecord}'.")
			print("#" * 100)
		print("=" * 100)
		print(f"[Navigation] Was timer wakeup is '{wasTimerWakeup}'.")
		print(f"[Navigation] Current time is '{ctime(now)}'. Fake-time suspected '{hasFakeTime}'.")
		print("-" * 100)
		timerwakeupmode = BoxInfo.getItem("timerwakeupmode")
		if not config.workaround.deeprecord.value and (wasTimerWakeup_failure or timerwakeupmode == 1):
			print("[Navigation] FORCED DEEPSTANDBY-WORKAROUND!")
			print("-" * 100)
			config.workaround.deeprecord.setValue(True)
			config.workaround.deeprecord.save()
			config.save()
		if config.workaround.deeprecord.value:  # Work-around for boxes where driver not sent was_timer_wakeup signal to Enigma.
			print("[Navigation] Starting deep standby workaround.")
			self.wakeupwindow_plus = self.timertime + 300
			self.wakeupwindow_minus = self.wakeuptime - (config.workaround.wakeupwindow.value * 60)
			wasTimerWakeup = False
			if not hasFakeTime and now >= self.wakeupwindow_minus and now <= self.wakeupwindow_plus:  # if there is a recording scheduled, set the wasTimerWakeup flag.
				wasTimerWakeup = True
				fileWriteLine("/tmp/was_timer_wakeup_workaround.txt", str(wasTimerWakeup), source=MODULE_NAME)
		else:
			# Secure wakeup window to prevent a wrong "wasTimerWakeup" value as timer wakeup detection.
			self.wakeupwindow_plus = self.timertime + 900
			self.wakeupwindow_minus = self.wakeuptime - 3600
		if self.wakeuptime > 0:
			print(f"[Navigation] Wakeup time from deep-standby expected: *** {ctime(self.wakeuptime)} ***")
			if config.workaround.deeprecord.value:
				print(f"[Navigation] Timer wakeup detection window '{ctime(self.wakeupwindow_minus)}' - '{ctime(self.wakeupwindow_plus)}'.")
		else:
			print("[Navigation] Wakeup time was not set.")
		print("-" * 100)
		if wasTimerWakeup:
			self.__wasTimerWakeup = True
			if not hasFakeTime:
				self.wakeupCheck()
				return
		if hasFakeTime and self.wakeuptime > 0:  # Check for NTP-time sync. If no sync, wait for transponder time.
			if Screens.Standby.TVinStandby.getTVstandby("waitfortimesync") and not wasTimerWakeup:
				self.skipTVWakeup = True
				Screens.Standby.TVinStandby.setTVstate("power")
			self.savedOldTime = now
			self.timesynctimer = eTimer()
			self.timesynctimer.callback.append(self.TimeSynctimer)
			self.timesynctimer.start(5000, True)
			print("[Navigation] Wait for time sync.")
			print("~" * 100)
		else:
			self.wakeupCheck(False)
		# TODO
		"""
		if config.usage.remote_fallback_import_restart.value:
			ImportChannels()
		if config.usage.remote_fallback_import.value and not config.usage.remote_fallback_import_restart.value:
			ImportChannels()
		"""

	def wakeupCheck(self, runCheck=True):
		now = time()
		stbytimer = 15  # Original was 15.
		if runCheck and ((self.__wasTimerWakeup or config.workaround.deeprecord.value) and now >= self.wakeupwindow_minus and now <= self.wakeupwindow_plus):
			if self.syncCount > 0:
				stbytimer = stbytimer - (self.syncCount * 5)
				if stbytimer < 0:
					stbytimer = 0
				if not self.__wasTimerWakeup:
					self.__wasTimerWakeup = True
					print("-" * 100)
					print("[Navigation] Was timer wakeup after time sync is True.")
					print(f"[Navigation] Wakeup time was '{ctime(self.wakeuptime)}'.")
			value = {
				0: "as normal",
				1: "in standby",
				2: "not in standby"
			}[self.getstandby]
			print(f"[Navigation] Wakeup type is '{self.TIMER_TYPES[self.getstandby]}' and starts {value}.")
			# Record timer, Zap timer, some plugin timer or next record timer begins in 15 minutes.
			if self.wakeuptyp < 2 or self.forcerecord:
				print(f"[Navigation] Timer starts at '{ctime(self.timertime)}'.")
				if self.forcerecord:
					print(f"[Navigation] Timer is set from 'vps-plugin' or just before a 'record-timer' starts at '{ctime(self.recordtime)}'.")
				print("[Navigation] Was record timer wakeup is True.")
				self.__wasRecTimerWakeup = True
				fileWriteLine(RecordTimer.TIMER_FLAG_FILE, "1", source=MODULE_NAME)
			# Power timer.
			if self.wakeuptyp == 2:
				if not self.forcerecord:
					print(f"[Navigation] Timer starts at '{ctime(self.timertime)}'.")
				print("[Navigation] Was schedule wakeup is True.")
				self.__wasSchedulerWakeup = True
				fileWriteLine(Scheduler.TIMER_FLAG_FILE, "1", source=MODULE_NAME)
			# Plugin timer.
			elif self.wakeuptyp == 3:
				if not self.forcerecord:
					print(f"[Navigation] Timer starts at '{ctime(self.timertime)}'.")
			# Check for standby.
			cec = (
				(self.wakeuptyp == 0 and (Screens.Standby.TVinStandby.getTVstandby("zapandrecordtimer"))) or
				(self.wakeuptyp == 1 and (Screens.Standby.TVinStandby.getTVstandby("zaptimer"))) or
				(self.wakeuptyp == 2 and (Screens.Standby.TVinStandby.getTVstandby("wakeuppowertimer")))
			)
			if self.getstandby != 1 and ((self.wakeuptyp < 3 and self.timertime - now > 60 + stbytimer) or cec):
				self.getstandby = 1
				text = " or special HDMI-CEC setting" if cec else ""
				print(f"[Navigation] More than 60 seconds to wakeup{text}, go to standby now.")
			print("=" * 100)
			# Go to standby.
			if self.getstandby == 1:
				if stbytimer:
					self.standbytimer = eTimer()
					self.standbytimer.callback.append(self.gotostandby)
					self.standbytimer.start(stbytimer * 1000, True)
				else:
					self.gotostandby()
		else:
			if self.__wasTimerWakeup:
				print("+" * 100)
				print("[Navigation] Wrong signal 'was timer wakeup' detected. Please activate the deep standby workaround.")
				print(f"[Navigation] Secure timer wakeup detection window '{ctime(self.wakeupwindow_minus)}' - '{ctime(self.wakeupwindow_plus)}'.")
				print("+" * 100)
			if self.timertime > 0:
				print(f"[Navigation] Next '{self.TIMER_TYPES[self.wakeuptyp]}' starts at '{ctime(self.timertime)}'.")
				if self.recordtime > 0 and self.timertime != self.recordtime:
					print(f"[Navigation] Next 'Record-timer' starts at '{ctime(self.recordtime)}'.")
				else:
					print("[Navigation] No next 'Record-timer'.")
			else:
				print("[Navigation] No next timer.")
			print("=" * 100)
			self.getstandby = 0
		# Workaround for normal operation if no time sync after Enigma starts, box is in standby.
		if self.getstandby != 1 and not self.skipWakeup:
			self.gotopower()

	def wasTimerWakeup(self):
		return self.__wasTimerWakeup

	def wasRecTimerWakeup(self):
		return self.__wasRecTimerWakeup

	def wasSchedulerWakeup(self):
		return self.__wasSchedulerWakeup

	def TimeSynctimer(self):
		now = time()
		self.syncCount += 1
		runNextSync = now <= 31536000 or now - (self.savedOldTime + (self.syncCount * 5)) <= 10
		result = "successful"
		if runNextSync:
			if self.syncCount <= 24:  # Maximum of 2 minutes or when time is in sync.
				self.timesynctimer.start(5000, True)
				return
			else:
				result = "failure or the time was correct"
		print("~" * 100)
		print(f"[Navigation] Time sync {result}, current time is {ctime(now)}, sync time is {self.syncCount * 5} seconds.")
		self.wakeupCheck()

	def gotopower(self):
		if not self.skipTVWakeup:
			Screens.Standby.TVinStandby.setTVstate("power")
		if Screens.Standby.inStandby:
			print("[Navigation] Now entering normal operation.")
			Screens.Standby.inStandby.Power()

	def gotostandby(self):
		if not Screens.Standby.inStandby:
			import Tools.Notifications
			print("[Navigation] Now entering standby.")
			Tools.Notifications.AddNotification(Screens.Standby.Standby)

	def dispatchEvent(self, i):
		if i == iPlayableService.evStreamError:
			self.scheduleStreamRetry()
		elif i == iPlayableService.evEOF and self.streamRetryService is not None:
			return  # Do not let the failed stream's EOF pause the pending retry.
		elif i == iPlayableService.evEnd:
			self.cancelStreamRetry(reset=False)
		if i in (iPlayableService.evEnd, iPlayableService.evTunedIn):
			self.cancelDVBIFailure()
		elif i == iPlayableService.evTuneFailed and self.scheduleDVBIFailure():
			return  # A verified fallback owns this failure, not the zap-error popup.
		if i == iPlayableService.evEnd and not self.skipServiceReferenceReset:
			self.isCurrentServiceDVBI = False
		for x in self.event:
			x(i)
		if i == iPlayableService.evEnd:
			self.hybridPlaybackService = None
			if not self.skipServiceReferenceReset:
				self.currentlyPlayingServiceReference = None
				self.currentlyPlayingServiceOrGroup = None
			self.currentlyPlayingService = None

	def cancelStreamRetry(self, reset=True):
		if self.streamRetryTimer:
			self.streamRetryTimer.stop()
		self.streamRetryService = None
		if reset:
			self.streamRetryCount = 0

	def getStreamRetryService(self):
		bar = InfoBar.instance
		ref = self.currentlyPlayingServiceOrGroup
		streamRef = self.hybridPlaybackService or ref
		if (not bar or ServiceEventTracker.getActiveInfoBar() is not bar or Screens.Standby.inStandby
				or self.isCurrentServiceDVBI or self.isCurrentServiceStreamRelay
				or not ref or ref.flags & eServiceReference.isGroup or streamRef.type != 4097
				or not streamRef.getPath().lower().startswith(("http://", "https://"))
				or bar.seekstate != bar.SEEK_STATE_PLAY):
			return None
		service = self.getCurrentService()
		seek = service and service.seek()
		if not seek:
			return None
		length = seek.getLength()
		if not length[0] and length[1] > 0:
			return None  # A finite HTTP movie must not restart from the beginning.
		timeshift = service.timeshift()
		if timeshift and timeshift.isTimeshiftEnabled():
			return None
		return service, self.currentlyPlayingServiceReference, ref

	def scheduleStreamRetry(self):
		if self.streamRetryService is not None:
			return
		pending = self.getStreamRetryService()
		if pending is None:
			return
		if self.streamRetryCount >= 3:
			if self.streamRetryCount == 3:
				InfoBar.instance.session.showError(_("Unable to reconnect to the stream. Please try the channel again later."))
				self.streamRetryCount += 1
			return
		self.streamRetryService = pending
		if self.streamRetryTimer is None:
			self.streamRetryTimer = eTimer()
			self.streamRetryTimer.callback.append(self.retryStream)
		# Recreate the service outside its native event callback, as on a zap.
		self.streamRetryTimer.start(2000 << self.streamRetryCount, True)

	def retryStream(self):
		pending = self.streamRetryService
		self.cancelStreamRetry(reset=False)
		if pending is None or pending != self.getStreamRetryService():
			return  # Stopped, zapped, paused, in standby or another player took over.
		self.streamRetryCount += 1
		print(f"[Navigation] Reconnecting HTTP stream (attempt {self.streamRetryCount}/3).")
		self.playService(pending[2], forceRestart=True, streamRetry=True)

	def cancelDVBIFailure(self):
		if self.dvbiFailureTimer:
			self.dvbiFailureTimer.stop()
		self.dvbiFailureService = None

	def scheduleDVBIFailure(self):
		live = self.currentlyPlayingServiceReference
		logical = self.currentlyPlayingServiceOrGroup
		ipFailure = self.isCurrentServiceDVBI and self.dvbiPlaybackService and getDVBIServiceAvailability(self.dvbiPlaybackService)
		if not live or not logical or logical.flags & eServiceReference.isGroup or not (ipFailure or getDVBIFallbackService(live, True)):
			return False
		service = self.getCurrentService()
		timeshift = service and service.timeshift()
		if not service or (timeshift and timeshift.isTimeshiftEnabled()):
			return False
		if self.dvbiFailureService is None:
			self.dvbiFailureService = (service, live, logical, self.dvbiPlaybackService if ipFailure else None)
			if self.dvbiFailureTimer is None:
				self.dvbiFailureTimer = eTimer()
				self.dvbiFailureTimer.callback.append(self.retryDVBIFailure)
			# Never destroy the native service inside its own signal callback.
			self.dvbiFailureTimer.start(0, True)
		return True

	def retryDVBIFailure(self):
		pending = self.dvbiFailureService
		self.cancelDVBIFailure()
		if pending is None:
			return
		service, live, logical, failedIp = pending
		if service is not self.getCurrentService() or live != self.currentlyPlayingServiceReference or logical != self.currentlyPlayingServiceOrGroup:
			return  # A zap/stop or another player superseded this failure.
		timeshift = service.timeshift()
		if failedIp and not (timeshift and timeshift.isTimeshiftEnabled()):
			unavailable = getDVBIServiceAvailability(failedIp) < 0
			nextService = getDVBIPlaybackService(logical, eServiceReference() if unavailable else failedIp)
			if nextService is not None:
				self.playService(logical, forceRestart=True, dvbiTarget=nextService)
			else:
				self.stopService()
				if InfoBar.instance:
					InfoBar.instance.session.showInfo(_("This channel is currently off air.") if unavailable else _("No further DVB-I alternative is available."), timeout=8)
			return
		if (timeshift and timeshift.isTimeshiftEnabled()) or not getDVBIFallbackService(live, True):
			for callback in self.event:
				callback(iPlayableService.evTuneFailed)
			return
		print("[Navigation] DVB-I: reception failed, switching live service to its registered IP alternative.")
		self.playService(logical, forceRestart=True, dvbiFallback=True)

	def dispatchRecordEvent(self, rec_service, event):
		# print(f"[Navigation] Record_event {rec_service}, {event}.")
		self.anyRecordingsCount = None
		self.indicatorRecordingsCount = None
		self.realRecordingsCount = None
		for x in self.record_event:
			x(rec_service, event)

	def restartService(self):
		self.playService(self.currentlyPlayingServiceOrGroup, forceRestart=True)

	def playService(self, ref, checkParentalControl=True, forceRestart=False, adjust=True, ignoreStreamRelay=False, event=None, dvbiFallback=False, dvbiTarget=None, streamRetry=False):

		if exists("/proc/stb/lcd/symbol_signal"):
			signal = "1" if config.lcd.mode.value and ref and "0:0:0:0:0:0:0:0:0" not in ref.toString() else "0"
			fileWriteLine("/proc/stb/lcd/symbol_signal", signal, source=MODULE_NAME)

		# Some plugins send None as ref becasue want to shutdown enigma play system.
		# So we have to stop current service if someone send None.
		if ref is None:
			self.stopService()
			return 0

		oldref = self.currentlyPlayingServiceOrGroup
		if oldref is not None:
			self.retryServicePlayCount = 0

		if ref and oldref and ref == oldref and not forceRestart:
			print("[Navigation] Ignore request to play already running service.  (1)")
			return 1

		self.cancelDVBIFailure()
		self.cancelStreamRetry(reset=not streamRetry)

		# from Components.ServiceEventTracker import InfoBarCount
		# InfoBarInstance = InfoBarCount == 1 and InfoBar.instance
		InfoBarInstance = InfoBar.instance
		isAsyncPlay = False

		currentServiceSource = None
		if InfoBarInstance:
			currentServiceSource = InfoBarInstance.session.screen["CurrentService"]

		if "%3a//" in ref.toString():
			self.currentlyPlayingServiceReference = None
			self.currentlyPlayingService = None
			if currentServiceSource:
				currentServiceSource.newService(False)

		print(f"[Navigation] Playing ref '{ref and ref.toString()}'.")
		self.currentlyPlayingServiceReference = ref
		self.currentlyPlayingServiceOrGroup = ref
		self.originalPlayingServiceReference = ref

		isStreamRelay = False

		if InfoBarInstance and currentServiceSource:
			currentServiceSource.newService(ref)
			InfoBarInstance.session.screen["Event_Now"].updateSource(self.currentlyPlayingServiceReference)
			InfoBarInstance.session.screen["Event_Next"].updateSource(self.currentlyPlayingServiceReference)
			InfoBarInstance.serviceStarted()

		if not checkParentalControl or parentalControl.isServicePlayable(ref, boundFunction(self.playService, checkParentalControl=False, forceRestart=forceRestart, adjust=adjust, dvbiTarget=dvbiTarget)):
			if ref.flags & eServiceReference.isGroup:
				oldref = self.currentlyPlayingServiceReference or eServiceReference()
				playref = getBestPlayableServiceReference(ref, oldref)
				if playref:
					if not ignoreStreamRelay:
						playref, isStreamRelay = streamrelay.streamrelayChecker(playref)
					if not isStreamRelay:
						playref, wrappererror = self.serviceHook(playref)
						if wrappererror:
							return 1
				print(f"[Navigation] Playref is '{str(playref)}'.")
				if playref and oldref and playref == oldref and not forceRestart:
					print("[Navigation] Ignore request to play already running service.  (2)")
					return 1
				if not playref:
					alternativeref = getBestPlayableServiceReference(ref, eServiceReference(), True)
					self.stopService()
					if alternativeref and self.pnav:
						self.currentlyPlayingServiceReference = alternativeref
						self.currentlyPlayingServiceOrGroup = ref
						if self.pnav.playService(alternativeref):
							print(f"[Navigation] Failed to start '{alternativeref.toString()}'.")
							self.currentlyPlayingServiceReference = None
							self.currentlyPlayingServiceOrGroup = None
							if oldref and ("://" in oldref.getPath() or streamrelay.checkService(oldref)):
								print("[Navigation] Streaming was active, try again.")  # Use timer to give the stream server the time to deallocate the tuner.
								self.retryServicePlayTimer = eTimer()
								self.retryServicePlayTimer.callback.append(boundFunction(self.playService, ref, checkParentalControl, forceRestart, adjust))
								self.retryServicePlayTimer.start(500, True)
						else:
							print(f"[Navigation] Alternative ref as simulate is '{alternativeref.toString()}'.")
					return 0
				elif checkParentalControl and not parentalControl.isServicePlayable(playref, boundFunction(self.playService, checkParentalControl=False)):
					if self.currentlyPlayingServiceOrGroup and InfoBarInstance and InfoBarInstance.servicelist.servicelist.setCurrent(self.currentlyPlayingServiceOrGroup, adjust):
						self.currentlyPlayingServiceOrGroup = InfoBarInstance.servicelist.servicelist.getCurrent()
					return 1
			else:
				playref = ref
			if self.pnav:
				if not BoxInfo.getItem("FCCactive"):
					self.pnav.stopService()
				else:
					self.skipServiceReferenceReset = True
				# The addon registers only verified equivalents. The native resolver
				# has an empty map by default and performs no I/O on the zap path.
				dvbiRef = dvbiTarget or getDVBIFallbackService(playref, dvbiFallback)
				if playref.getPath().startswith("dvbi://") and dvbiRef is None:
					dvbiRef = getDVBIPlaybackService(playref, eServiceReference())
					if dvbiRef is None and getDVBIServiceAvailability(playref) < 0:
						if InfoBarInstance:
							InfoBarInstance.session.showInfo(_("This channel is currently off air."), timeout=8)
						return 1
				isDVBI = dvbiRef is not None or playref.getPath().startswith("dvbi://")
				playref = dvbiRef or playref
				self.currentlyPlayingServiceReference = playref
				if not ignoreStreamRelay:
					playref, isStreamRelay = streamrelay.streamrelayChecker(playref)
				if not isStreamRelay:
					playref, wrappererror = self.serviceHook(playref)
					if wrappererror:
						return 1

				originalPlayref = playref.toString()
				for extensionFunc in Navigation.playServiceExtensions:
					ret = extensionFunc(self, playref, event, InfoBarInstance)
					if isinstance(ret, (ServiceReference.ServiceReference, eServiceReference)):
						playref = ret
					else:
						playref, isAsyncPlay = ret
					if isAsyncPlay or playref.toString() != originalPlayref:
						break

				print(f"[Navigation] Playref is '{playref.toString()}'.")
				# Keep the delivery route separate from the logical channel used for EPG.
				self.isCurrentServiceDVBI = isDVBI and "://" in playref.getPath()
				self.dvbiPlaybackService = playref if isDVBI else None
				self.currentlyPlayingServiceOrGroup = ref
				if InfoBarInstance and InfoBarInstance.servicelist.servicelist.setCurrent(ref, adjust):
					self.currentlyPlayingServiceOrGroup = InfoBarInstance.servicelist.servicelist.getCurrent()
				# self.skipServiceReferenceReset = True
				if (config.misc.softcam_streamrelay_delay.value and self.isCurrentServiceStreamRelay) or (self.firstStart and isStreamRelay):
					self.skipServiceReferenceReset = False
					self.isCurrentServiceStreamRelay = False
					self.isCurrentServiceDVBI = False
					self.currentlyPlayingServiceReference = None
					self.currentlyPlayingServiceOrGroup = None
					self.retryServicePlayCount = 1  # Pre-arm retry cycle in case play fails after delay.
					print("[Navigation] Stream relay was active, delay the zap till tuner is freed.")
					self.retryServicePlayTimer = eTimer()
					self.retryServicePlayTimer.callback.append(boundFunction(self.playService, ref, checkParentalControl, forceRestart, adjust))
					delay = 2000 if self.firstStart else config.misc.softcam_streamrelay_delay.value
					self.firstStart = False
					self.retryServicePlayTimer.start(delay, True)
					return 0
				elif not isAsyncPlay and self.pnav.playService(playref):
					if self.dvbiFailureService is not None:
						# A synchronous native tune failure already queued recovery.
						# Keep its references alive for the deferred identity check.
						self.skipServiceReferenceReset = False
						return 0
					print(f"[Navigation] Failed to start '{playref.toString()}'.")
					self.isCurrentServiceDVBI = False
					self.currentlyPlayingServiceReference = None
					self.originalPlayingServiceReference = None
					self.currentlyPlayingServiceOrGroup = None
					if oldref and ("://" in oldref.getPath() or streamrelay.checkService(oldref)):
						self.retryServicePlayCount = 1  # Start retry cycle for stream relay tuner deallocation.
					if self.retryServicePlayCount > 0 and self.retryServicePlayCount <= 20:
						print(f"[Navigation] Streaming was active, try again (attempt {self.retryServicePlayCount}).")  # Use timer to give the stream server the time to deallocate the tuner.
						self.retryServicePlayTimer = eTimer()
						self.retryServicePlayTimer.callback.append(boundFunction(self.playService, ref, checkParentalControl, forceRestart, adjust))
						self.retryServicePlayTimer.start(500, True)
						self.retryServicePlayCount += 1
					elif self.retryServicePlayCount > 20:
						print(f"[Navigation] Gave up retrying after {self.retryServicePlayCount - 1} attempts.")
						self.retryServicePlayCount = 0
				else:
					self.retryServicePlayCount = 0
				self.skipServiceReferenceReset = False
				self.isCurrentServiceStreamRelay = isStreamRelay
				if InfoBarInstance and "%3a//" in playref.toString():
					self.originalPlayingServiceReference = None
					InfoBarInstance.serviceStarted()
				return 0
		elif oldref and InfoBarInstance and InfoBarInstance.servicelist.servicelist.setCurrent(oldref, adjust):
			self.currentlyPlayingServiceOrGroup = InfoBarInstance.servicelist.servicelist.getCurrent()
		return 1

	def serviceHook(self, ref):
		wrappererror = None
		nref = ref
		if nref.getPath():
			for p in plugins.getPlugins(PluginDescriptor.WHERE_PLAYSERVICE):
				(newurl, errormsg) = p(service=nref)
				if errormsg:
					wrappererror = _("Error getting link via %s\n%s") % (p.name, errormsg)
					break
				elif newurl:
					nref.setAlternativeUrl(newurl)
					break
			if wrappererror:
				AddPopup(text=wrappererror, type=MessageBox.TYPE_ERROR, timeout=5, id="channelzapwrapper")
		return nref, wrappererror

	def getCurrentlyPlayingServiceReference(self):
		return self.currentlyPlayingServiceReference

	def getCurrentlyPlayingServiceOrGroup(self):
		return self.currentlyPlayingServiceOrGroup

	def getCurrentServiceReferenceOriginal(self):
		return self.originalPlayingServiceReference or self.currentlyPlayingServiceOrGroup

	def getCurrentServiceRef(self):
		curPlayService = self.getCurrentService()
		info = curPlayService and curPlayService.info()
		return info and info.getInfoString(iServiceInformation.sServiceref)

	def isCurrentServiceIPTV(self):
		ref = self.getCurrentServiceRef()
		ref = ref and eServiceReference(ref)
		path = ref and ref.getPath()
		return path and not path.startswith("/") and ref.type in [0x1, 0x1001, 0x138A, 0x1389]

	def isMovieplayerActive(self):
		MoviePlayerInstance = MoviePlayer.instance
		if MoviePlayerInstance is not None and "0:0:0:0:0:0:0:0:0" in self.currentlyPlayingServiceReference.toString():
			from Screens.InfoBarGenerics import setResumePoint
			setResumePoint(MoviePlayer.instance.session)
			MoviePlayerInstance.close()

	def prepareDVBIFallbackForRecording(self, recording):
		live = self.currentlyPlayingServiceReference
		logical = self.currentlyPlayingServiceOrGroup
		if not live or not logical or not recording or not canDVBIFallbackReleaseForRecording(live, recording):
			return False
		service = self.getCurrentService()
		timeshift = service and service.timeshift()
		if timeshift and timeshift.isTimeshiftEnabled():
			return False  # Never discard a user's timeshift buffer automatically.
		self.playService(logical, forceRestart=True, dvbiFallback=True)
		return self.currentlyPlayingServiceReference is not None and self.currentlyPlayingServiceReference != live

	def recordService(self, ref, simulate=False, type=pNavigation.isUnknownRecording):
		service = None
		if not simulate:
			print(f"[Navigation] Recording service is '{str(ref)}'.")
		if isinstance(ref, ServiceReference.ServiceReference):
			ref = ref.ref
		if ref:
			if ref.flags & eServiceReference.isGroup:
				ref = getBestPlayableServiceReference(ref, eServiceReference(), simulate)
			if not simulate and ref and ref.getPath().startswith("dvbi://") and getDVBIServiceAvailability(ref):
				ref = getDVBIPlaybackService(ref, eServiceReference())
				if ref is None:
					return None
			if type != (pNavigation.isPseudoRecording | pNavigation.isFromEPGrefresh):
				ref, is_stream_relay = streamrelay.streamrelayChecker(ref)
				for f in Navigation.recordServiceExtensions:
					ref = f(self, ref)
				if not is_stream_relay and not (simulate and ref.getPath().startswith("dvbi://")):
					ref, wrappererror = self.serviceHook(ref)
					if wrappererror:
						print(f"[Navigation] Error getting link via serviceHook. '{wrappererror}'")
						return None
			service = ref and self.pnav and self.pnav.recordService(ref, simulate, type)
			if service is None:
				print("[Navigation] Record returned non-zero.")
		return service

	def stopRecordService(self, service):
		ret = -1
		if service and isinstance(service, iRecordableServicePtr):
			ret = self.pnav and self.pnav.stopRecordService(service)
		return ret

	def streamStatusChangedCB(self, status, sref, host):
		if "127.0.0.1" in host:  # Ignore local host.
			return
		print(f"[Navigation] Stream status changed: {status}, {sref}, {host}.")
		wasStreaming = bool(self.activeStreamings)
		key = (host or "", sref or "")
		if status == 0:
			ref, count = self.activeStreamingsByClient.get(key, (sref, 0))
			self.activeStreamingsByClient[key] = (ref, count + 1)
		else:
			ref, count = self.activeStreamingsByClient.get(key, (sref, 0))
			if count > 1:
				self.activeStreamingsByClient[key] = (ref, count - 1)
			else:
				self.activeStreamingsByClient.pop(key, None)
		self.activeStreamings = list(dict.fromkeys(ref for ref, count in self.activeStreamingsByClient.values() if ref))

		self.anyRecordingsCount = None
		self.indicatorRecordingsCount = None
		self.realRecordingsCount = None

		if wasStreaming != bool(self.activeStreamings):
			for x in self.record_event:
				x(None, iRecordableService.evStart if self.activeStreamings else iRecordableService.evEnd)

	def getRecordings(self, simulate=False, type=pNavigation.isAnyRecording):
		if ((type == pNavigation.isAnyRecording) or (type & pNavigation.isStreaming == pNavigation.isStreaming)) and self.activeStreamings:
			return self.pnav and self.pnav.getRecordings(simulate, type) + self.activeStreamings
		else:
			return self.pnav and self.pnav.getRecordings(simulate, type)

	def getRecordingsServices(self, type=pNavigation.isAnyRecording):
		return self.pnav and self.pnav.getRecordingsServices(type)

	def getRecordingsServicesOnly(self, type=pNavigation.isAnyRecording):
		return self.pnav and self.pnav.getRecordingsServicesOnly(type)

	def getRecordingsTypesOnly(self, type=pNavigation.isAnyRecording):
		return self.pnav and self.pnav.getRecordingsTypesOnly(type)

	def getRecordingsSlotIDsOnly(self, type=pNavigation.isAnyRecording):
		return self.pnav and self.pnav.getRecordingsSlotIDsOnly(type)

	def getRecordingsServicesAndTypes(self, type=pNavigation.isAnyRecording):
		return self.pnav and self.pnav.getRecordingsServicesAndTypes(type)

	def getRecordingsServicesAndTypesAndSlotIDs(self, type=pNavigation.isAnyRecording):
		return self.pnav and self.pnav.getRecordingsServicesAndTypesAndSlotIDs(type)

	def getRecordingsCheckBeforeActivateDeepStandby(self, modifyTimer=True):  # Only for "real" recordings.
		now = time()
		rec = self.RecordTimer.isRecording()
		next_rec_time = self.RecordTimer.getNextRecordingTime()
		if rec or (next_rec_time > 0 and (next_rec_time - now) < 360):
			print(f"[Navigation] - Recording={rec}, recording in next minutes={next_rec_time - now < 360 and not (config.timeshift.isRecording.value and next_rec_time - now >= 298)}, save time shift={config.timeshift.isRecording.value}.")
			if not self.RecordTimer.isRecTimerWakeup():  # If not timer wake up, enable trigger file for automatic shutdown after recording.
				fileWriteLine(RecordTimer.TIMER_FLAG_FILE, "1", source=MODULE_NAME)
			if modifyTimer:
				lastrecordEnd = 0
				for timer in self.RecordTimer.timer_list:
					if lastrecordEnd == 0 or lastrecordEnd >= timer.begin:
						if timer.afterEvent < 2 and timer.forceDeepStandby is False:
							timer.forceDeepStandby = True
							print(f"[Navigation] Set after-event for recording '{timer.name}' to deep standby.")
						if timer.end > lastrecordEnd:
							lastrecordEnd = timer.end + 900
			rec = True
		return rec

	def getCurrentService(self):
		if not self.currentlyPlayingService:
			self.currentlyPlayingService = self.pnav and self.pnav.getCurrentService()
		return self.currentlyPlayingService

	def getAnyRecordingsCount(self):
		if self.anyRecordingsCount is None:
			self.anyRecordingsCount = len(self.getRecordings(False, pNavigation.isAnyRecording))
		return self.anyRecordingsCount

	def getIndicatorRecordingsCount(self):
		if self.indicatorRecordingsCount is None:
			self.indicatorRecordingsCount = len(self.getRecordings(False, recType(config.recording.show_rec_symbol_for_rec_types.getValue())))
		return self.indicatorRecordingsCount

	def getRealRecordingsCount(self):
		if self.realRecordingsCount is None:
			self.realRecordingsCount = len(self.getRecordings(False, pNavigation.isRealRecording))
		return self.realRecordingsCount

	def stopService(self):
		self.cancelDVBIFailure()
		self.cancelStreamRetry()
		self.isCurrentServiceDVBI = False
		if self.pnav:
			self.pnav.stopService()
		self.currentlyPlayingServiceReference = None
		self.currentlyPlayingServiceOrGroup = None
		if exists("/proc/stb/lcd/symbol_signal"):
			fileWriteLine("/proc/stb/lcd/symbol_signal", "0", source=MODULE_NAME)

	def pause(self, p):
		return self.pnav and self.pnav.pause(p)

	def shutdown(self):
		self.cancelDVBIFailure()
		self.cancelStreamRetry()
		self.RecordTimer.shutdown()
		self.Scheduler.shutdown()
		self.ServiceHandler = None
		self.pnav = None

	def stopUserServices(self):
		self.stopService()
