from os import remove
from os.path import exists
from time import ctime, time

from enigma import eServiceCenter, eServiceReference, eTimer, getBestPlayableServiceReference, iPlayableService, iServiceInformation, pNavigation

import NavigationInstance
import RecordTimer
import Scheduler
import ServiceReference
from Components.config import config
from Components.ImportChannels import ImportChannels
from Components.ParentalControl import parentalControl
from Components.PluginComponent import plugins
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
		self.pnav = pNavigation()
		self.pnav.m_event.get().append(self.dispatchEvent)
		self.pnav.m_record_event.get().append(self.dispatchRecordEvent)
		self.event = []
		self.record_event = []
		self.currentBouquetName = ""
		self.currentlyPlayingServiceReference = None
		self.currentlyPlayingServiceOrGroup = None
		self.currentlyPlayingService = None
		Screens.Standby.TVstate()
		self.skipWakeup = False
		self.skipTVWakeup = False
		self.firstStart = True
		self.RecordTimer = None
		self.isRecordTimerImageStandard = False
		self.isCurrentServiceStreamRelay = False
		self.skipServiceReferenceReset = False
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
		# if config.usage.remote_fallback_import_restart.value:
		#	ImportChannels()
		# if config.usage.remote_fallback_import.value and not config.usage.remote_fallback_import_restart.value:
		#	ImportChannels()

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
		for x in self.event:
			x(i)
		if i == iPlayableService.evEnd:
			if not self.skipServiceReferenceReset:
				self.currentlyPlayingServiceReference = None
				self.currentlyPlayingServiceOrGroup = None
			self.currentlyPlayingService = None

	def dispatchRecordEvent(self, rec_service, event):
		# print(f"[Navigation] Record_event {rec_service}, {event}.")
		for x in self.record_event:
			x(rec_service, event)

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

	def playService(self, ref, checkParentalControl=True, forceRestart=False, adjust=True, ignoreStreamRelay=False):
		oldref = self.currentlyPlayingServiceOrGroup
		if ref and oldref and ref == oldref and not forceRestart:
			print("[Navigation] Ignore request to play already running service.  (1)")
			return 1
		print(f"[Navigation] Playing ref '{ref and ref.toString()}'.")
		if exists("/proc/stb/lcd/symbol_signal"):
			signal = "1" if config.lcd.mode.value and ref and "0:0:0:0:0:0:0:0:0" not in ref.toString() else "0"
			fileWriteLine("/proc/stb/lcd/symbol_signal", signal, source=MODULE_NAME)
		if ref is None:
			self.stopService()
			return 0
		from Components.ServiceEventTracker import InfoBarCount
		InfoBarInstance = InfoBarCount == 1 and InfoBar.instance
		isStreamRelay = False
		if not checkParentalControl or parentalControl.isServicePlayable(ref, boundFunction(self.playService, checkParentalControl=False, forceRestart=forceRestart, adjust=adjust)):
			if ref.flags & eServiceReference.isGroup:
				oldref = self.currentlyPlayingServiceReference or eServiceReference()
				playref = getBestPlayableServiceReference(ref, oldref)
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
				self.currentlyPlayingServiceReference = playref
				if not ignoreStreamRelay:
					playref, isStreamRelay = streamrelay.streamrelayChecker(playref)
				if not isStreamRelay:
					playref, wrappererror = self.serviceHook(playref)
					if wrappererror:
						return 1
				print(f"[Navigation] Playref is '{playref.toString()}'.")
				self.currentlyPlayingServiceOrGroup = ref
				if InfoBarInstance and InfoBarInstance.servicelist.servicelist.setCurrent(ref, adjust):
					self.currentlyPlayingServiceOrGroup = InfoBarInstance.servicelist.servicelist.getCurrent()
				# self.skipServiceReferenceReset = True
				if (config.misc.softcam_streamrelay_delay.value and self.isCurrentServiceStreamRelay) or (self.firstStart and isStreamRelay):
					self.skipServiceReferenceReset = False
					self.isCurrentServiceStreamRelay = False
					self.currentlyPlayingServiceReference = None
					self.currentlyPlayingServiceOrGroup = None
					print("[Navigation] Stream relay was active, delay the zap till tuner is freed.")
					self.retryServicePlayTimer = eTimer()
					self.retryServicePlayTimer.callback.append(boundFunction(self.playService, ref, checkParentalControl, forceRestart, adjust))
					delay = 2000 if self.firstStart else config.misc.softcam_streamrelay_delay.value
					self.firstStart = False
					self.retryServicePlayTimer.start(delay, True)
					return 0
				elif self.pnav.playService(playref):
					print(f"[Navigation] Failed to start '{playref.toString()}'.")
					self.currentlyPlayingServiceReference = None
					self.currentlyPlayingServiceOrGroup = None
					if oldref and ("://" in oldref.getPath() or streamrelay.checkService(oldref)):
						print("[Navigation] Streaming was active, try again.")  # Use timer to give the stream server the time to deallocate the tuner.
						self.retryServicePlayTimer = eTimer()
						self.retryServicePlayTimer.callback.append(boundFunction(self.playService, ref, checkParentalControl, forceRestart, adjust))
						self.retryServicePlayTimer.start(500, True)
				self.skipServiceReferenceReset = False
				if isStreamRelay and not self.isCurrentServiceStreamRelay:
					self.isCurrentServiceStreamRelay = True
				return 0
		elif oldref and InfoBarInstance and InfoBarInstance.servicelist.servicelist.setCurrent(oldref, adjust):
			self.currentlyPlayingServiceOrGroup = InfoBarInstance.servicelist.servicelist.getCurrent()
		return 1

	def getCurrentlyPlayingServiceReference(self):
		return self.currentlyPlayingServiceReference

	def getCurrentlyPlayingServiceOrGroup(self):
		return self.currentlyPlayingServiceOrGroup

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

	def recordService(self, ref, simulate=False, type=pNavigation.isUnknownRecording):
		service = None
		if not simulate:
			print(f"[Navigation] Recording service is '{str(ref)}'.")
		if isinstance(ref, ServiceReference.ServiceReference):
			ref = ref.ref
		if ref:
			if ref.flags & eServiceReference.isGroup:
				ref = getBestPlayableServiceReference(ref, eServiceReference(), simulate)
			if type != (pNavigation.isPseudoRecording | pNavigation.isFromEPGrefresh):
				ref, isStreamRelay = streamrelay.streamrelayChecker(ref)
				#if not isStreamRelay:
				#	ref, wrappererror = self.serviceHook(ref)
			service = ref and self.pnav and self.pnav.recordService(ref, simulate, type)
			if service is None:
				print("[Navigation] Record returned non-zero.")
		return service

	def restartService(self):
		self.playService(self.currentlyPlayingServiceOrGroup, forceRestart=True)

	def stopRecordService(self, service):
		ret = self.pnav and self.pnav.stopRecordService(service)
		return ret

	def getRecordings(self, simulate=False, type=pNavigation.isAnyRecording):
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
						if timer.afterEvent < 2:
							timer.afterEvent = 2
							print(f"[Navigation] Set after-event for recording '{timer.name}' to deep standby.")
						if timer.end > lastrecordEnd:
							lastrecordEnd = timer.end + 900
			rec = True
		return rec

	def getCurrentService(self):
		if not self.currentlyPlayingService:
			self.currentlyPlayingService = self.pnav and self.pnav.getCurrentService()
		return self.currentlyPlayingService

	def stopService(self):
		if self.pnav:
			self.pnav.stopService()
		self.currentlyPlayingServiceReference = None
		self.currentlyPlayingServiceOrGroup = None
		if exists("/proc/stb/lcd/symbol_signal"):
			fileWriteLine("/proc/stb/lcd/symbol_signal", "0", source=MODULE_NAME)

	def pause(self, p):
		return self.pnav and self.pnav.pause(p)

	def shutdown(self):
		self.RecordTimer.shutdown()
		self.Scheduler.shutdown()
		self.ServiceHandler = None
		self.pnav = None

	def stopUserServices(self):
		self.stopService()
