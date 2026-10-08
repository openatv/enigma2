from os import makedirs, stat, statvfs
from os.path import dirname, exists, isabs, join, realpath
from shlex import split as splitCommand
from time import localtime, strftime, time
from twisted.internet.threads import deferToThread
from twisted.python.failure import Failure
from enigma import eBackgroundFileEraser, eConsoleAppContainer, eEPGCache, eServiceCenter, eServiceReference, eTimer, iPlayableService, iServiceInformation
from Components.ActionMap import HelpableActionMap
from Components.config import config
from Components.Harddisk import getProcMounts, harddiskmanager
from Components.ServiceEventTracker import ServiceEventTracker
from Components.SystemInfo import BoxInfo
from Components.Task import FailedPostcondition, Job, Task, job_manager as JobManager
from Components.TimeshiftStorage import EXPORT_PART_SIZE, TimeshiftExport, TimeshiftRegistry, TimeshiftSaveJournal, formatTimeshiftMetadata, getTimeshiftParts, parseTimeshiftMetadata, removeTimeshiftRecording
from Components.UsageConfig import preferredTimeShiftRecordingPath
from RecordTimer import AFTEREVENT, RecordTimerEntry, parseEvent
from Screens import Standby
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from ServiceReference import ServiceReference
from timer import TimerEntry
from Tools.ASCIItranslit import legacyEncode
from Tools.BoundFunction import boundFunction
from Tools.Directories import SCOPE_CONFIG, fileExists, fileWriteLine, getRecordingFilename, resolveFilename
from Tools.Notifications import AddNotification

MODULE_NAME = __name__.split(".")[-1]


class TimeshiftContinuation:
	def __init__(self, timer):
		self.timer = timer
		self.path = None
		self.destination = None
		self.invalid = False

	def capture(self):
		timer = self.timer
		if timer.failed or timer.cancelled or timer.repeated:
			self.invalid = True
		elif timer.state == TimerEntry.StateRunning:
			# Preparation may be asynchronous and may recalculate Filename.
			# Only a successfully started, exact timer owns this recording.
			filename = getattr(timer, "Filename", "")
			service = timer.record_service
			if not filename or not isabs(filename) or service is None or service.getFilenameExtension() != ".ts":
				self.invalid = True
			elif self.path is not None and self.path != f"{filename}.ts":
				self.invalid = True
			else:
				self.path = f"{filename}.ts"
		elif self.path and self.path != f'{getattr(timer, "Filename", "")}.ts':
			self.invalid = True


# InfoBarTimeshift requires InfoBarSeek, instantiated BEFORE!
#
# Hrmf.
#
# Time shift works the following way:
#                                         demux0   demux1                    "TimeshiftActions" "TimeshiftActivateActions" "SeekActions"
# - normal playback                       TUNER    unused      PLAY               enable                disable              disable
# - user presses "yellow" button.         FILE     record      PAUSE              enable                disable              enable
# - user presess pause again              FILE     record      PLAY               enable                disable              enable
# - user fast forwards                    FILE     record      FF                 enable                disable              enable
# - end of time shift buffer reached      TUNER    record      PLAY               enable                enable               disable
# - user backwards                        FILE     record      BACK  # !!         enable                disable              enable
#
# in other words:
# - when a service is playing, pressing the "timeshiftStart" button ("yellow") enables recording ("enables timeshift"),
# freezes the picture (to indicate timeshift), sets timeshiftMode ("activates timeshift")
# now, the service becomes seekable, so "SeekActions" are enabled, "TimeshiftEnableActions" are disabled.
# - the user can now PVR around
# - if it hits the end, the service goes into live mode ("deactivates timeshift", it's of course still "enabled")
# the service looses it's "seekable" state. It can still be paused, but just to activate time shift right
# after!
# the seek actions will be disabled, but the timeshiftActivateActions will be enabled
# - if the user rewinds, or press pause, time shift will be activated again
#
# note that a time shift can be enabled ("recording") and activated (currently time-shifting).
#
class InfoBarTimeshift:
	ts_disabled = False

	def __init__(self):
		self["TimeshiftActions"] = HelpableActionMap(self, "InfobarTimeshiftActions", {
			"timeshiftStart": (self.startTimeshift, _("Start time shift")),  # The "yellow key".
			"timeshiftStop": (self.stopTimeshift, _("Stop time shift")),  # Currently undefined :), probably 'TV'.
			"instantRecord": self.instantRecord,
			"restartTimeshift": self.restartTimeshift,
			"seekFwdManual": (self.seekFwdManual, _("Seek forward (enter time)")),
			"seekBackManual": (self.seekBackManual, _("Seek backward (enter time)")),
			"seekdef:1": (boundFunction(self.seekdef, 1), _("Seek")),
			"seekdef:3": (boundFunction(self.seekdef, 3), _("Seek")),
			"seekdef:4": (boundFunction(self.seekdef, 4), _("Seek")),
			"seekdef:6": (boundFunction(self.seekdef, 6), _("Seek")),
			"seekdef:7": (boundFunction(self.seekdef, 7), _("Seek")),
			"seekdef:9": (boundFunction(self.seekdef, 9), _("Seek"))
		}, prio=1)
		self["TimeshiftActivateActions"] = HelpableActionMap(self, ["InfobarTimeshiftActivateActions"], {
			"timeshiftActivateEnd": self.activateTimeshiftEnd,  # Something like "rewind key".
			"timeshiftActivateEndAndPause": self.activateTimeshiftEndAndPause  # Something like "pause key".
		}, prio=-1)  # Priority over record.
		self["TimeshiftSeekPointerActions"] = HelpableActionMap(self, ["InfobarTimeshiftSeekPointerActions"], {
			"SeekPointerOK": self.ptsSeekPointerOK,
			"SeekPointerLeft": self.ptsSeekPointerLeft,
			"SeekPointerRight": self.ptsSeekPointerRight
		}, prio=-1)
		self["TimeshiftFileActions"] = HelpableActionMap(self, ["InfobarTimeshiftActions"], {
			"jumpPreviousFile": self.__evSOFjump,
			"jumpNextFile": self.__evEOF
		}, prio=-1)  # Priority over history.
		self["TimeshiftActions"].setEnabled(False)
		self["TimeshiftActivateActions"].setEnabled(False)
		self["TimeshiftSeekPointerActions"].setEnabled(False)
		self["TimeshiftFileActions"].setEnabled(False)
		self.switchToLive = True
		self.ptsStop = False
		self.ts_rewind_timer = eTimer()
		self.ts_rewind_timer.callback.append(self.rewindService)
		self.save_timeshift_file = False
		self.saveTimeshiftEventPopupActive = False
		eventmap = {
			iPlayableService.evStart: self.__serviceStarted,
			iPlayableService.evSeekableStatusChanged: self.__seekableStatusChanged,
			iPlayableService.evEnd: self.__serviceEnd,
			iPlayableService.evSOF: self.__evSOF,
			iPlayableService.evUpdatedInfo: self.__evInfoChanged,
			iPlayableService.evUpdatedEventInfo: self.__evEventInfoChanged,
			iPlayableService.evUser + 1: self.ptsTimeshiftFileChanged
		}
		# Keep Python-only updates usable with an older Enigma2 binary.
		if hasattr(iPlayableService, "evTimeshiftError"):
			eventmap[iPlayableService.evTimeshiftError] = self.ptsTimeshiftWriteError
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap=eventmap)
		self.pts_begintime = 0
		self.pts_switchtolive = False
		self.pts_firstplayable = 1
		self.pts_lastposition = 0
		self.pts_lastplaying = 1
		self.pts_currplaying = 1
		self.pts_nextplaying = 0
		self.pts_lastseekspeed = 0
		self.pts_service_changed = False
		self.pts_file_changed = False
		self.pts_record_running = self.session.nav.RecordTimer.isRecording()
		self.save_current_timeshift = False
		self.save_timeshift_postaction = None
		self.service_changed = 0
		self.event_changed = False
		self.pts_justzapped = False  # True only when files should be erased due to 'deleteAfterZap', not after a fresh GUI/box restart.
		self.ptsCleanupError = None
		self.ptsStorageError = None
		self.ptsStorage = None
		self.timeshiftRegistry = TimeshiftRegistry()
		self.saveJournal = TimeshiftSaveJournal(resolveFilename(SCOPE_CONFIG, "timeshift-saves"))
		self.cleanupRunning = False
		self.pendingMerges = set()
		self.continuationRecordings = {}
		self.mergeOwners = {}
		self.mergeWarnings = set()
		self.pendingSaveIntents = 0
		self.mergeScanRunning = False
		self.mergeCleanupSources = {}
		self.playbackLeases = {}
		self.pendingPlaybackIdentifier = ""
		self.storagePreparing = False
		self.startGeneration = 0
		self.pauseAfterStart = False
		self.notifyAfterStart = False
		self.requestedStartGeneration = None
		self.checkEvents_value = config.timeshift.checkEvents.value
		self.pts_starttime = time()
		self.ptsAskUser_wait = False
		self.posDiff = 0
		self.session.ptsmainloopvalue = 0  # Initialize Global Variables.
		config.timeshift.isRecording.value = False
		self.BgFileEraser = eBackgroundFileEraser.getInstance()  # Initialize eBackgroundFileEraser.
		self.pts_delay_timer = eTimer()  # Initialize PTS delay timer.
		self.pts_delay_timer.callback.append(self.autostartPermanentTimeshift)
		self.pts_mergeRecords_timer = eTimer()  # Initialize PTS merge recordings timer.
		self.pts_mergeRecords_timer.callback.append(self.ptsMergeRecords)
		self.pts_mergeCleanUp_timer = eTimer()  # Initialize PTS merge cleanup timer.
		self.pts_mergeCleanUp_timer.callback.append(self.ptsMergePostCleanUp)
		self.pts_QuitMainloop_timer = eTimer()  # Initialize PTS quit Mainloop timer.
		self.pts_QuitMainloop_timer.callback.append(self.ptsTryQuitMainloop)
		self.pts_cleanUp_timer = eTimer()  # Initialize PTS cleanup timer.
		self.pts_cleanUp_timer.callback.append(self.ptsCleanTimeshiftFolder)
		self.pts_cleanEvent_timer = eTimer()  # Initialize PTS clean event timer.
		self.pts_cleanEvent_timer.callback.append(self.ptsEventCleanTimeshiftFolder)
		self.pts_SeekBack_timer = eTimer()  # Initialize PTS seek back timer.
		self.pts_SeekBack_timer.callback.append(self.ptsSeekBackTimer)
		self.pts_StartSeekBackTimer = eTimer()
		self.pts_StartSeekBackTimer.callback.append(self.ptsStartSeekBackTimer)
		self.pts_SeekToPos_timer = eTimer()  # Initialize PTS seek to position timer.
		self.pts_SeekToPos_timer.callback.append(self.ptsSeekToPos)
		self.pts_CheckFileChanged_counter = 1
		self.pts_CheckFileChanged_timer = eTimer()  # Initialize PTS check file changed timer.
		self.pts_CheckFileChanged_timer.callback.append(self.ptsCheckFileChanged)
		self.pts_blockZap_timer = eTimer()  # Initialize block zap timer.
		self.pts_FileJump_timer = eTimer()  # Initialize PTS file jump timer.
		self.session.nav.RecordTimer.on_state_change.append(self.ptsTimerEntryStateChange)  # Recording event tracker.
		self.pts_eventcount = 0  # Keep Current Event Info for recordings.
		self.pts_curevent_begin = int(time())
		self.pts_curevent_end = 0
		self.pts_curevent_name = _("Timeshift")
		self.pts_curevent_description = ""
		self.pts_curevent_servicerefname = ""
		self.pts_curevent_station = ""
		self.pts_curevent_eventid = None
		harddiskmanager.on_partition_list_change.append(self.ptsPartitionChanged)
		self.onClose.append(self.ptsStorageClosed)

	@property
	def ptsCurrentEventName(self):
		return self.pts_curevent_name.replace("\n", " ") if self.pts_curevent_name else ""

	@property
	def ptsCurrentEventDescription(self):
		return self.pts_curevent_description.replace("\n", " ") if self.pts_curevent_description else ""

	def resolveTimeshiftFile(self, identifier):
		entry = self.timeshiftRegistry.buffers.get(identifier)
		return entry.path if entry else identifier if isabs(identifier) else join(config.timeshift.path.value, identifier)

	def hasTimeshiftFile(self, identifier):
		entry = self.timeshiftRegistry.buffers.get(identifier)
		if entry is None:
			path = self.resolveTimeshiftFile(identifier)
			entry = next((x for x in self.timeshiftRegistry.buffers.values() if x.path == path), None)
		return entry is not None and not entry.deleting

	def finishTimeshiftBuffer(self):
		entry = self.timeshiftRegistry.buffers.get(f"pts_livebuffer_{self.pts_eventcount}")
		if entry and entry.active:
			if entry.autosave:
				self.timeshiftRegistry.acquire(entry)
			entry.active = False
			if entry.autosave:
				entry.autosave = False
				saveCurrent = self.save_current_timeshift
				try:
					self.SaveTimeshift(f"pts_livebuffer_{self.pts_eventcount}")
				finally:
					self.save_current_timeshift = saveCurrent
					self.timeshiftRegistry.release(entry)

	def releaseTimeshiftPlayback(self):
		for entry in self.playbackLeases.values():
			self.timeshiftRegistry.release(entry)
		self.playbackLeases.clear()
		self.pendingPlaybackIdentifier = ""

	def __seekableStatusChanged(self):
		# print(f"[Timeshift] PTS_currplaying {self.pts_currplaying}, pts_nextplaying {self.pts_nextplaying}, pts_eventcount {self.pts_eventcount}, pts_firstplayable {self.pts_firstplayable}.")
		self["TimeshiftActivateActions"].setEnabled(not self.isSeekable() and self.timeshiftEnabled())
		state = self.getSeek() is not None and self.timeshiftEnabled()
		self["SeekActionsPTS"].setEnabled(state)
		self["TimeshiftFileActions"].setEnabled(state and not self.isRamTimeshift())
		if self.isRamTimeshift():
			self.restartSubtitle()
			return
		if not state and self.pts_currplaying == self.pts_eventcount and self.timeshiftEnabled() and not self.event_changed:
			self.setSeekState(self.SEEK_STATE_PLAY)
			if hasattr(self, "pvrStateDialog"):
				self.pvrStateDialog.hide()
		self.restartSubtitle()
		if self.timeshiftEnabled() and not self.isSeekable():
			self.ptsSeekPointerReset()
			if config.timeshift.startDelay.value:
				if self.pts_starttime <= (time() - 5):
					self.pts_blockZap_timer.start(3000, True)
			self.pts_lastplaying = self.pts_currplaying = self.pts_eventcount
			self.pts_nextplaying = 0
			self.pts_file_changed = True
			self.ptsSetNextPlaybackFile(f"pts_livebuffer_{self.pts_eventcount}")

	def __serviceStarted(self):
		self.startGeneration += 1
		self.service_changed = 1
		self.pts_service_changed = True
		if self.pts_delay_timer.isActive():
			self.pts_delay_timer.stop()
		if config.timeshift.startDelay.value:
			self.pts_delay_timer.start(config.timeshift.startDelay.value * 1000, True)
		# self.__seekableStatusChanged()
		self["TimeshiftActions"].setEnabled(True)

	def __serviceEnd(self):
		priorityHandoff = getattr(self, "recordingPriorityHandoff", None) is not None
		self.startGeneration += 1
		entry = self.timeshiftRegistry.buffers.get(f"pts_livebuffer_{self.pts_eventcount}") if self.save_current_timeshift else None
		if entry:
			self.timeshiftRegistry.acquire(entry)
			if priorityHandoff and entry.active and entry.autosave:
				self.save_current_timeshift = False  # Finalization already saves this buffer.
		self.releaseTimeshiftPlayback()
		self.finishTimeshiftBuffer()
		if self.save_current_timeshift:
			try:
				if self.pts_curevent_end > time() and not priorityHandoff:
					task = self.SaveTimeshift(f"pts_livebuffer_{self.pts_eventcount}", mergelater=True)
					self.ptsRecordCurrentEvent(task)
				else:
					# A priority recording needs the tuner: save the closed buffer,
					# without starting another recording on the old transponder.
					self.SaveTimeshift(f"pts_livebuffer_{self.pts_eventcount}")
			finally:
				if priorityHandoff:
					self.save_current_timeshift = False
		if entry:
			self.timeshiftRegistry.release(entry)
		self.service_changed = 0
		# if not config.timeshift.isRecording.value:
		# 	self.__seekableStatusChanged()
		self.__seekableStatusChanged()  # Fix: Enable ready to start for standard time shift after saving the event.
		self["TimeshiftActions"].setEnabled(False)

	def __evSOFjump(self):
		if not self.timeshiftEnabled() or self.pts_CheckFileChanged_timer.isActive() or self.pts_SeekBack_timer.isActive() or self.pts_StartSeekBackTimer.isActive() or self.pts_SeekToPos_timer.isActive():
			return
		if self.pts_FileJump_timer.isActive():
			self.__evSOF()
		else:
			self.pts_FileJump_timer.start(5000, True)
			self.setSeekState(self.SEEK_STATE_PLAY)
			self.doSeek(0)
			self.posDiff = 0

	def evSOF(self, posDiff=0):  # Called from InfoBarGenerics.py.
		self.posDiff = posDiff
		self.__evSOF()

	def __evSOF(self):
		if self.timeshiftEnabled():
			service = self.session.nav.getCurrentService()
			info = service and service.info()
			if info and info.getInfo(iServiceInformation.sIsRecoveringStream) == 1:
				print("[Timeshift.py] SOF event ignored: C++ is handling stream recovery.")
				return  # Exit immediately, letting C++ take full control.

			if self.pts_CheckFileChanged_timer.isActive() or self.pts_SeekBack_timer.isActive() or self.pts_StartSeekBackTimer.isActive() or self.pts_SeekToPos_timer.isActive():
				return
			self.pts_switchtolive = False
			self.pts_lastplaying = self.pts_currplaying
			self.pts_nextplaying = 0
			if self.pts_currplaying > self.pts_firstplayable:
				self.pts_currplaying -= 1
			else:
				self.setSeekState(self.SEEK_STATE_PLAY)
				self.doSeek(0)
				self.posDiff = 0
				if self.pts_FileJump_timer.isActive():
					self.pts_FileJump_timer.stop()
					self.session.showInfo(_("First playable time shift file!"))
				if not self.pts_FileJump_timer.isActive():
					self.pts_FileJump_timer.start(5000, True)
				return
			# Switch to previous TS file by seeking backwards to the previous file.
			if self.hasTimeshiftFile(f"pts_livebuffer_{self.pts_currplaying}"):
				self.ptsSetNextPlaybackFile(f"pts_livebuffer_{self.pts_currplaying}")
				self.setSeekState(self.SEEK_STATE_PLAY)
				self.doSeek(3600 * 24 * 90000)
				self.pts_CheckFileChanged_counter = 1
				self.pts_CheckFileChanged_timer.start(1000, False)
				self.pts_file_changed = False
			else:
				print(f"[Timeshift] 'pts_livebuffer_{self.pts_currplaying}' file was not found -> Put pointer to the first (current) 'pts_livebuffer_{self.pts_currplaying + 1}' file.")
				self.pts_currplaying += 1
				self.pts_firstplayable += 1
				self.setSeekState(self.SEEK_STATE_PLAY)
				self.doSeek(0)
				self.posDiff = 0

	def evEOF(self, posDiff=0):  # Called from InfoBarGenerics.py.
		self.posDiff = posDiff
		self.__evEOF()

	def __evEOF(self):
		if self.timeshiftEnabled():
			service = self.session.nav.getCurrentService()
			info = service and service.info()
			if info and info.getInfo(iServiceInformation.sIsRecoveringStream) == 1:
				print("[Timeshift.py] EOF event ignored: C++ is handling stream recovery.")
				return  # Exit immediately, letting C++ take full control.

			if self.pts_CheckFileChanged_timer.isActive() or self.pts_SeekBack_timer.isActive() or self.pts_StartSeekBackTimer.isActive() or self.pts_SeekToPos_timer.isActive():
				return
			self.pts_switchtolive = False
			self.pts_lastposition = self.ptsGetPosition()
			self.pts_lastplaying = self.pts_currplaying
			self.pts_nextplaying = 0
			self.pts_currplaying += 1
			# Switch to next TS file by seeking forward to the next file.
			if self.hasTimeshiftFile(f"pts_livebuffer_{self.pts_currplaying}"):
				self.ptsSetNextPlaybackFile(f"pts_livebuffer_{self.pts_currplaying}")
				self.setSeekState(self.SEEK_STATE_PLAY)
				self.doSeek(3600 * 24 * 90000)
				self.pts_CheckFileChanged_counter = 1
				self.pts_CheckFileChanged_timer.start(1000, False)
				self.pts_file_changed = False
			else:
				if not config.timeshift.startDelay.value and config.timeshift.showLiveTVMsg.value:
					self.session.showInfo(_("Switching to live TV - time shift is still active!"), timeout=3)
				self.posDiff = 0
				self.pts_lastposition = 0
				self.pts_currplaying -= 1
				self.pts_switchtolive = True
				self.ptsSetNextPlaybackFile("")
				self.setSeekState(self.SEEK_STATE_PLAY)
				self.doSeek(3600 * 24 * 90000)
				self.pts_CheckFileChanged_counter = 1
				self.pts_CheckFileChanged_timer.start(1000, False)
				self.pts_file_changed = False

	def __evInfoChanged(self):
		if self.service_changed:
			self.service_changed = 0
			if self.save_current_timeshift:  # We zapped away before saving the file, save it now!
				self.SaveTimeshift(f"pts_livebuffer_{self.pts_eventcount}")
			if config.timeshift.deleteAfterZap.value:  # Delete time shift recordings on zap.
				self.pts_justzapped = True
				self.ptsEventCleanTimerSTOP()
			self.pts_firstplayable = self.pts_eventcount + 1
			if self.pts_eventcount == 0 and not config.timeshift.startDelay.value:
				self.pts_cleanUp_timer.start(1000, True)

	def __evEventInfoChanged(self):
		if self.isRamTimeshift():
			return  # A RAM ring spans EPG events; it has no separate event files.
		service = self.session.nav.getCurrentService()  # Get current event info.
		old_begin_time = self.pts_begintime
		info = service and service.info()
		ptr = info and info.getEvent(0)
		self.pts_begintime = ptr and ptr.getBeginTime() or 0
		eventChanged = old_begin_time and self.pts_begintime and old_begin_time != self.pts_begintime
		if info and info.getInfo(iServiceInformation.sVideoPID) != -1:  # Save current time shift buffer permanently now.
			if eventChanged and self.save_current_timeshift and self.timeshiftEnabled():  # Take care of recording margin time.
				if config.recording.margin_after.value > 0 and len(self.recording) == 0:
					task = self.SaveTimeshift(mergelater=True)
					recording = RecordTimerEntry(ServiceReference(self.session.nav.getCurrentlyPlayingServiceOrGroup()), time(), time() + (config.recording.margin_after.value * 60), self.pts_curevent_name, self.pts_curevent_description, self.pts_curevent_eventid, afterEvent=AFTEREVENT.AUTO, justplay=False, always_zap=False, dirname=preferredTimeShiftRecordingPath())
					self.recordTimeshiftContinuation(recording, task)
				else:
					self.SaveTimeshift()
				if not config.timeshift.fileSplitting.value:
					self.stopTimeshiftcheckTimeshiftRunningCallback(True)
			if not self.pts_delay_timer.isActive():  # (Re)Start time shift.
				if old_begin_time != self.pts_begintime or old_begin_time == 0:
					if config.timeshift.startDelay.value or self.timeshiftEnabled():
						self.event_changed = True
					self.pts_delay_timer.start(1000, True)

	def seekdef(self, key):
		if self.seekstate == self.SEEK_STATE_PLAY:
			return 0  # Treat as unhandled action.
		time = (
			-config.seek.selfdefined_13.value, False, config.seek.selfdefined_13.value,
			-config.seek.selfdefined_46.value, False, config.seek.selfdefined_46.value,
			-config.seek.selfdefined_79.value, False, config.seek.selfdefined_79.value
		)[key - 1]
		self.doSeekRelative(time * 90000)
		self.pvrStateDialog.show()
		return 1

	def getTimeshift(self):
		if self.ts_disabled or self.pts_delay_timer.isActive():
			return None
		service = self.session.nav.getCurrentService()
		return service and service.timeshift()

	def timeshiftEnabled(self):
		ts = self.getTimeshift()
		return ts and ts.isTimeshiftEnabled()

	def playpauseService2(self):
		service = self.session.nav.getCurrentService()
		playingref = self.session.nav.getCurrentlyPlayingServiceReference()
		if not playingref or playingref.type < eServiceReference.idUser:
			return 0
		if service and service.streamed():
			pauseable = service.pause()
			if pauseable:
				if self.seekstate == self.SEEK_STATE_PLAY:
					pauseable.pause()
					self.seekstate = self.SEEK_STATE_PAUSE
				else:
					pauseable.unpause()
					self.seekstate = self.SEEK_STATE_PLAY
				return
		return 0

	def startTimeshift(self):
		ts = self.getTimeshift()
		if ts and ts.isTimeshiftEnabled():
			print("[Timeshift] Time shift already enabled.")
			self.activateTimeshiftEndAndPause()
		elif self.ptsLiveTVStatus():
			self.pauseAfterStart = True
			self.activatePermanentTimeshift()
		else:
			return self.playpauseService2()

	def stopTimeshift(self):
		if self.isRamTimeshift():
			ts = self.getTimeshift()
			if ts.isTimeshiftEnabled():
				ts.stopTimeshift(True)
				self.__seekableStatusChanged()
			return
		preparing = self.storagePreparing
		if preparing:
			self.startGeneration += 1
			self.requestedStartGeneration = None
			self.pauseAfterStart = self.notifyAfterStart = False
			self.event_changed = False
			self.pts_delay_timer.stop()
		ts = self.getTimeshift()
		if ts and ts.isTimeshiftEnabled():
			if config.timeshift.startDelay.value and self.isSeekable():
				self.switchToLive = True
				self.ptsStop = True
				self.checkTimeshiftRunning(self.stopTimeshiftcheckTimeshiftRunningCallback)
			elif not config.timeshift.startDelay.value:
				self.checkTimeshiftRunning(self.stopTimeshiftcheckTimeshiftRunningCallback)
			else:
				return 0
		else:
			return 1 if preparing else 0

	def stopTimeshiftcheckTimeshiftRunningCallback(self, answer):
		if answer and self.isRamTimeshift():
			self.getTimeshift().stopTimeshift(True)
			self.__seekableStatusChanged()
			return
		if answer and config.timeshift.startDelay.value and self.switchToLive and self.isSeekable():
			self.posDiff = 0
			self.pts_lastposition = 0
			if self.pts_currplaying != self.pts_eventcount:
				self.pts_lastposition = self.ptsGetPosition()
			self.pts_lastplaying = self.pts_currplaying
			self.ptsStop = False
			self.pts_nextplaying = 0
			self.pts_switchtolive = True
			self.setSeekState(self.SEEK_STATE_PLAY)
			self.ptsSetNextPlaybackFile("")
			self.doSeek(3600 * 24 * 90000)
			self.pts_CheckFileChanged_counter = 1
			self.pts_CheckFileChanged_timer.start(1000, False)
			self.pts_file_changed = False
			# self.__seekableStatusChanged()
			return 0
		ts = self.getTimeshift()
		if answer and ts:
			generation = self.startGeneration
			wasEnabled = ts.isTimeshiftEnabled()
			result = ts.stopTimeshift(self.switchToLive if config.timeshift.startDelay.value else not self.event_changed)
			if wasEnabled and result:
				if generation == self.startGeneration:
					self.ptsTimeshiftWriteError()
				return False
			if generation != self.startGeneration:
				return False
			self.finishTimeshiftBuffer()
			if self.switchToLive:
				self.releaseTimeshiftPlayback()
			self.__seekableStatusChanged()

	def activateTimeshiftEnd(self, back=True):  # Activates time shift, and seeks to (almost) the end.
		ts = self.getTimeshift()
		if ts is None:
			return
		if ts.isTimeshiftActive():
			self.pauseService()
		else:
			ts.activateTimeshift()  # Activate time shift will automatically pause.
			self.setSeekState(self.SEEK_STATE_PAUSE)
			seekable = self.getSeek()
			if seekable is not None:
				seekable.seekTo(-90000)  # Seek approximately 1 second before end.
		if back:
			self.ts_rewind_timer.start(1000 if BoxInfo.getItem("brand") == "xtrend" else 500, 1)

	def rewindService(self):
		if BoxInfo.getItem("brand") in ("gigablue", "xp"):
			self.setSeekState(self.SEEK_STATE_PLAY)
		self.setSeekState(self.makeStateBackward(int(config.seek.enter_backward.value)))

	def callServiceStarted(self):
		from Screens.InfoBarGenerics import isStandardInfoBar  # Avoid circular import.
		if isStandardInfoBar(self):
			ServiceEventTracker.setActiveInfoBar(self, None, None)
			self.__serviceStarted()

	def activateTimeshiftEndAndPause(self):  # Same as activateTimeshiftEnd, but pauses afterwards.
		self.activateTimeshiftEnd(False)

	def checkTimeshiftRunning(self, returnFunction):
		if self.isRamTimeshift():
			returnFunction(True)  # No disk buffer can be offered for export.
			return
		def checkTimeshiftRunningCallback(returnFunction, answer):
			match answer:
				case "savetimeshift" | "savetimeshiftandrecord":
					self.save_current_timeshift = True
				case "noSave":
					self.save_current_timeshift = False
				case "no":  # This is not really needed because the default is "no".
					pass
				case _:  # The user pressed cancel so assume they meant "no". That's probably not always correct, but it seems reasonable.
					answer = "no"
			InfoBarTimeshift.saveTimeshiftActions(self, answer, returnFunction)

		if self.ptsStop:
			returnFunction(True)
		elif (self.isSeekable() or (self.timeshiftEnabled() and not config.timeshift.startDelay.value) or self.save_current_timeshift) and config.timeshift.check.value:
			if config.timeshift.favoriteSaveAction.value == "askuser":
				if self.save_current_timeshift:
					message = _("You have chosen to save the current time shift event, but the event has not yet finished\nWhat do you want to do?")
					choice = [
						(_("Save time shift as movie and continue recording"), "savetimeshiftandrecord"),
						(_("Save time shift as movie and stop recording"), "savetimeshift"),
						(_("Cancel save time shift as movie"), "noSave"),
						(_("Nothing, just leave this menu"), "no")
					]
					self.session.openWithCallback(boundFunction(checkTimeshiftRunningCallback, returnFunction), MessageBox, message, simple=True, list=choice, timeout=30)
				else:
					message = _("You seem to be in time shift, do you want to leave time shift?")
					choice = [
						(_("Yes, but don't save time shift as movie"), "noSave"),
						(_("Yes, but save time shift as movie and continue recording"), "savetimeshiftandrecord"),
						(_("Yes, but save time shift as movie and stop recording"), "savetimeshift"),
						(_("No"), "no")
					]
					self.session.openWithCallback(boundFunction(checkTimeshiftRunningCallback, returnFunction), MessageBox, message, simple=True, list=choice, timeout=30)
			else:
				if self.save_current_timeshift:
					# The user has previously activated "Time shift save recording" of current event - so must be necessarily saved of the timeshift!
					# Workaround - without the message box can the box no longer be operated when goes in standby (no freezing - no longer can use - unhandled key screen comes when key press).
					message = _("You have chosen to save the current time shift buffer")
					choice = [(_("Save time shift buffer now and continue recording"), "savetimeshiftandrecord")]
					self.session.openWithCallback(boundFunction(checkTimeshiftRunningCallback, returnFunction), MessageBox, message, simple=True, list=choice, timeout=1)
					# InfoBarTimeshift.saveTimeshiftActions(self, "savetimeshiftandrecord", returnFunction)
				else:
					message = _("You seem to be in time shift, do you want to leave time shift?")
					choice = [
						(_("Yes"), config.timeshift.favoriteSaveAction.value),
						(_("No"), "no")
					]
					self.session.openWithCallback(boundFunction(checkTimeshiftRunningCallback, returnFunction), MessageBox, message, simple=True, list=choice, timeout=30)
		elif self.save_current_timeshift:
			# The user has chosen "no warning" when time shift is stopped (config.timeshift.check=False)
			# but the user has previously activated "Time shift save recording" of current event
			# so we silently do "savetimeshiftandrecord" when switching channel independent of config.timeshift.favoriteSaveAction.
			# Workaround - without the message box can the box no longer be operated when goes in standby (no freezing - no longer can use - unhandled key screen comes when key press)
			message = _("You have chosen to save the current time shift buffer")
			choice = [(_("Save time shift buffer now and continue recording"), "savetimeshiftandrecord")]
			self.session.openWithCallback(boundFunction(checkTimeshiftRunningCallback, returnFunction), MessageBox, message, simple=True, list=choice, timeout=1)
			# InfoBarTimeshift.saveTimeshiftActions(self, "savetimeshiftandrecord", returnFunction)
		else:
			returnFunction(True)

	def eraseTimeshiftFile(self):
		# Recorder, playback and export leases are checked by the cleanup worker.
		self.ptsCleanTimeshiftFolder(justZapped=False)

	def autostartPermanentTimeshift(self):
		if self.pts_delay_timer.isActive():
			self.pts_delay_timer.stop()
		if (config.timeshift.startDelay.value and not self.timeshiftEnabled()) or self.event_changed:
			self.activatePermanentTimeshift()

	def activatePermanentTimeshift(self):
		if self.session.screen["Standby"].boolean or not self.ptsLiveTVStatus() or (config.timeshift.stopWhileRecording.value and self.pts_record_running):
			return False
		if self.isRamTimeshift():
			ts = self.getTimeshift()
			if not ts.isTimeshiftEnabled() and ts.startTimeshift():
				self.pauseAfterStart = self.notifyAfterStart = False
				self.session.showError(_("Unable to start RAM time shift."))
				return False
			self.event_changed = False
			if self.pauseAfterStart:
				self.activateTimeshiftEndAndPause()
			self.pauseAfterStart = self.notifyAfterStart = False
			return True
		self.requestedStartGeneration = self.startGeneration
		if not self.storagePreparing:
			self.storagePreparing = True
			path = config.timeshift.path.value
			deferToThread(self.prepareTimeshiftFolder, path).addBoth(self.timeshiftStoragePrepared, self.startGeneration, path)
		return True

	def timeshiftStoragePrepared(self, result, generation, path):
		self.storagePreparing = False
		if generation != self.startGeneration or path != config.timeshift.path.value:
			if self.requestedStartGeneration == self.startGeneration:
				self.activatePermanentTimeshift()
			return
		if isinstance(result, Failure):
			self.ptsAbortTimeshift(_("Unable to prepare the time shift storage device."), str(result.value))
			return
		self.ptsStorage = result
		if self.activatePreparedTimeshift():
			if self.pauseAfterStart:
				self.activateTimeshiftEndAndPause()
			if self.notifyAfterStart:
				self.session.showInfo(_("[Timeshift] Restarting time shift!"))
		self.pauseAfterStart = self.notifyAfterStart = False

	def activatePreparedTimeshift(self):
		if self.session.screen["Standby"].boolean or not self.ptsLiveTVStatus() or (config.timeshift.stopWhileRecording.value and self.pts_record_running):
			return False
		if self.pts_justzapped:  # Only cleanup folder after switching channels with 'deleteAfterZap', not after a fresh GUI/box restart.
			if not self.ptsCleanTimeshiftFolder(justZapped=True):  # Remove all time shift files.
				return
			self.pts_justzapped = False
		else:
			if not self.ptsCleanTimeshiftFolder(justZapped=False):  # Only delete very old time shift files based on config.timeshift.maxHours.
				return
		# (Re)start time shift now.
		if config.timeshift.fileSplitting.value:
			generation = self.startGeneration
			# setNextPlaybackFile() on event change while time shifting.
			if self.isSeekable():
				self.pts_nextplaying = self.pts_currplaying + 1
				self.ptsSetNextPlaybackFile(f"pts_livebuffer_{self.pts_nextplaying}")
				self.switchToLive = False  # Do not switch back to live TV while time shifting.
			else:
				self.switchToLive = True
			result = self.stopTimeshiftcheckTimeshiftRunningCallback(True)
			if result is False or generation != self.startGeneration:
				return False
		else:
			if self.pts_currplaying < self.pts_eventcount:
				self.pts_nextplaying = self.pts_currplaying + 1
				self.ptsSetNextPlaybackFile(f"pts_livebuffer_{self.pts_nextplaying}")
			else:
				self.pts_nextplaying = 0
				self.ptsSetNextPlaybackFile("")
		self.event_changed = False
		ts = self.getTimeshift()
		if ts is None:
			self.ptsAbortTimeshift(_("Time shift could not be started. Please check the storage device and available space."))
			return False
		wasEnabled = ts.isTimeshiftEnabled()
		if not wasEnabled and ts.startTimeshift():
			self.ptsAbortTimeshift(_("Time shift could not be started. Please check the storage device and available space."))
			return False
		if not wasEnabled or self.pts_eventcount == 0:
			self.pts_eventcount += 1  # Update internal event counter.
			if (BoxInfo.getItem("machinebuild") == "vuuno" or BoxInfo.getItem("machinebuild") == "vuduo") and exists("/proc/stb/lcd/symbol_timeshift"):
				if self.session.nav.RecordTimer.isRecording():
					fileWriteLine("/proc/stb/lcd/symbol_timeshift", "0", source=MODULE_NAME)
			elif BoxInfo.getItem("model") == "u41" and exists("/proc/stb/lcd/symbol_record"):
				if self.session.nav.RecordTimer.isRecording():
					fileWriteLine("/proc/stb/lcd/symbol_record", "0", source=MODULE_NAME)
			self.pts_starttime = time()
			self.save_timeshift_postaction = None
			self.ptsGetEventInfo()
			if not self.ptsRegisterTimeshiftBuffer():
				return False
			self.__seekableStatusChanged()
			self.ptsEventCleanTimerSTART()
		else:
			self.ptsGetEventInfo()
			entry = self.timeshiftRegistry.buffers.get(f"pts_livebuffer_{self.pts_eventcount}")
			if entry:
				entry.metadata.update(name=self.ptsCurrentEventName, description=self.ptsCurrentEventDescription)
				self.persistTimeshiftMetadata(entry)
				self.ptsCreateEITFile(entry.path)
			self.ptsEventCleanTimerSTART()
		if self.pts_eventcount < self.pts_firstplayable:
			self.pts_firstplayable = self.pts_eventcount
		self.ptsStorageError = None
		return True

	def createTimeshiftFolder(self):
		try:
			self.ptsStorage = self.prepareTimeshiftFolder(config.timeshift.path.value)
			return True
		except OSError as err:
			self.ptsAbortTimeshift(_("Unable to prepare the time shift storage device."), str(err))
			return False

	def prepareTimeshiftFolder(self, path):
		# Runs in a worker: autofs activation and NAS path checks may block.
		path = realpath(path)

		def containingMount():
			mounts = [x for x in getProcMounts() if len(x) >= 4 and (path == x[1] or path.startswith(join(x[1], "")))]
			return max(reversed(mounts), key=lambda x: len(x[1])) if mounts else None

		mount = containingMount()
		if mount and mount[2] == "autofs":
			statvfs(path)
			mount = containingMount()
		if not mount or mount[1] == "/" or mount[2] in ("tmpfs", "ramfs", "rootfs", "autofs", "jffs2", "ubifs", "squashfs") or "ro" in mount[3].split(","):
			raise OSError(_("The time shift storage device is not available. Please check the device and the time shift path."))
		makedirs(path, exist_ok=True)
		if not fileExists(path, "w"):
			raise PermissionError(path)
		return (mount[0], mount[1])

	def ptsAbortTimeshift(self, message, detail=None, stop=True):
		self.startGeneration += 1
		self.requestedStartGeneration = None
		self.pauseAfterStart = self.notifyAfterStart = False
		# Do not stop independent copy/merge jobs or delete previously saved buffers.
		for timer in (self.pts_delay_timer, self.pts_cleanUp_timer, self.pts_cleanEvent_timer, self.ts_rewind_timer,
			self.pts_SeekBack_timer, self.pts_StartSeekBackTimer, self.pts_SeekToPos_timer, self.pts_CheckFileChanged_timer,
			self.pts_blockZap_timer, self.pts_FileJump_timer):
			timer.stop()
		self.save_current_timeshift = False
		self.save_timeshift_file = False
		self.save_timeshift_postaction = None
		self.ptsStop = self.event_changed = self.pts_switchtolive = self.pts_file_changed = False
		self.switchToLive = True
		self.pts_nextplaying = self.pts_lastposition = self.posDiff = 0
		self.pts_firstplayable = self.pts_currplaying = self.pts_lastplaying = self.pts_eventcount + 1
		self.releaseTimeshiftPlayback()
		if stop:
			ts = self.getTimeshift()
			if ts and ts.isTimeshiftEnabled():
				ts.setNextPlaybackFile("")
				generation = self.startGeneration
				result = ts.stopTimeshift(True)
				if result:
					if generation == self.startGeneration:
						self.ptsTimeshiftWriteError()
				elif generation == self.startGeneration:
					self.finishTimeshiftBuffer()
		self.setSeekState(self.SEEK_STATE_PLAY)
		self.__seekableStatusChanged()
		if hasattr(self, "pvrStateDialog"):
			self.pvrStateDialog.hide()
		error = (config.timeshift.path.value, message, detail)
		if self.ptsStorageError != error:
			self.ptsStorageError = error
			print(f"[Timeshift] {message} Path: {error[0]}. {detail or ''}")
			self.session.showError(f"{message}\n{error[0]}" + (f"\n{detail}" if detail else ""), timeout=10)

	def ptsTimeshiftWriteError(self):
		# The native recorder has already stopped and returned to live TV.
		entry = self.timeshiftRegistry.buffers.get(f"pts_livebuffer_{self.pts_eventcount}")
		if entry:
			entry.retained = True
			entry.autosave = False
		self.finishTimeshiftBuffer()
		self.ptsAbortTimeshift(_("Writing to the time shift storage device failed. Time shift has been stopped."), stop=False)

	def ptsPartitionChanged(self, action, partition):
		if action == "remove" and self.ptsStorage and not self.isRamTimeshift():
			source, mountpoint = self.ptsStorage
			if (partition.device and source == join("/dev", partition.device)) or (partition.mountpoint and mountpoint.rstrip("/") == partition.mountpoint.rstrip("/")):
				self.ptsStorage = None
				if self.timeshiftEnabled() or self.save_current_timeshift:
					self.ptsAbortTimeshift(_("The time shift storage device was removed. Time shift has been stopped."))
				else:
					self.pts_delay_timer.stop()
					self.pts_cleanUp_timer.stop()
					self.ptsEventCleanTimerSTOP(justStop=True)

	def ptsStorageClosed(self):
		self.startGeneration += 1
		self.releaseTimeshiftPlayback()
		if self.ptsPartitionChanged in harddiskmanager.on_partition_list_change:
			harddiskmanager.on_partition_list_change.remove(self.ptsPartitionChanged)

	def restartTimeshift(self):
		self.notifyAfterStart = True
		self.activatePermanentTimeshift()

	def saveTimeshiftEventPopup(self):
		self.saveTimeshiftEventPopupActive = True
		entrylist = [(f'{_("Current Event:")} {self.pts_curevent_name}', "savetimeshift")]
		for identifier, entry in sorted(tuple(self.timeshiftRegistry.buffers.items()), key=lambda x: x[1].created):
			if entry.deleting or entry.active or entry.metadata.get("cleanupOnly"):
				continue
			metadata = entry.metadata
			begin = strftime(config.usage.time.short.value, localtime(int(metadata.get("begin", entry.created))))
			station = metadata.get("station") or ServiceReference(metadata.get("service", "")).getServiceName()
			entrylist.append((f'[{begin}] {station} : {metadata.get("name", _("Timeshift"))}', identifier))
		self.session.openWithCallback(self.recordQuestionCallback, ChoiceBox, title=_("Which time shift buffer event do you want to save?"), list=entrylist)

	def saveTimeshiftActions(self, action=None, returnFunction=None):
		timeshiftfile = None
		if self.pts_currplaying != self.pts_eventcount:
			timeshiftfile = f"pts_livebuffer_{self.pts_currplaying}"
		if action == "savetimeshift":
			self.SaveTimeshift(timeshiftfile)
		elif action == "savetimeshiftandrecord":
			if self.pts_curevent_end > time() and timeshiftfile is None:
				task = self.SaveTimeshift(mergelater=True)
				self.ptsRecordCurrentEvent(task)
			else:
				self.SaveTimeshift(timeshiftfile)
		elif action == "noSave":
			config.timeshift.isRecording.value = False
			self.save_current_timeshift = False
		elif action == "no":
			pass
		if returnFunction is not None and action != "no":  # Get rid of old time shift file before E2 truncates its filesize.
			self.eraseTimeshiftFile()
		if returnFunction is not None:
			returnFunction(action and action != "no")

	def SaveTimeshift(self, timeshiftfile=None, mergelater=False):
		identifier = timeshiftfile or f"pts_livebuffer_{self.pts_eventcount}"
		entry = self.timeshiftRegistry.buffers.get(identifier)
		if entry is None:
			path = self.resolveTimeshiftFile(identifier)
			entry = next((x for x in self.timeshiftRegistry.buffers.values() if x.path == path), None)
		if entry is None:
			if self.isRamTimeshift():
				self.session.showInfo(_("RAM time shift cannot be saved as a recording."))
			else:
				self.session.showError(_("No time shift buffer found to save as recording!"))
			return
		try:
			limit = None
			if entry.active:
				ts = self.getTimeshift()
				if ts is None or ts.getTimeshiftFilename() != entry.path:
					raise OSError(_("The current time shift buffer is no longer available."))
				limit = ts.getTimeshiftFileSize() if hasattr(ts, "getTimeshiftFileSize") else -1
				if limit < 0:
					raise OSError(_("The running Enigma2 version cannot safely save an active time shift buffer."))
			metadata = entry.metadata
			eventname = metadata.get("name", _("Timeshift"))
			description = metadata.get("description", "")
			begin = int(metadata.get("begin", self.pts_starttime))
			station = metadata.get("station") or ServiceReference(metadata.get("service", "")).getServiceName()
			eventstarttime = strftime("%Y%m%d %H%M", localtime(begin))
			ptsfilename = f"{eventstarttime} - {station} - {eventname}"
			if config.usage.setup_level.index >= 2:
				composition = config.recording.filename_composition.value
				if composition == "long" and eventname != description:
					ptsfilename = f"{ptsfilename} - {description}"
				elif composition == "short":
					ptsfilename = f"{eventstarttime} - {eventname}"
				elif composition in ("veryshort", "veryveryshort"):
					ptsfilename = f"{eventname} - {eventstarttime}"
			if config.recording.ascii_filenames.value:
				ptsfilename = legacyEncode(ptsfilename)
			self.timeshiftRegistry.acquire(entry)
			job = CopyTimeshiftJob(self, None, entry.path, (preferredTimeShiftRecordingPath(), ptsfilename), eventname)
			task = job.tasks[0]
			task.entry = entry
			task.limit = limit
			task.mergelater = mergelater
			tag = "pts_merge" if mergelater else "autosaved" if metadata.get("autosave") else metadata.get("tags", "")
			task.metadata = formatTimeshiftMetadata(dict(metadata, name=eventname, description=description, begin=begin), tags=tag)
			config.timeshift.isRecording.value = True
			self.save_current_timeshift = False
			self.queueTimeshiftSave(job, entry)
			if mergelater:
				self.pts_mergeRecords_timer.start(120000, True)
			return task
		except (OSError, ValueError) as err:
			entry.retained = True
			self.ptsSaveTimeshiftFailed(str(err))

	def queueTimeshiftSave(self, job, entry=None):
		task = job.tasks[0]
		sources = ((task.destfile, None), (task.srcfile, None)) if isinstance(task, AddMergeTimeshiftTask) else ((task.srcfile, task.limit),)
		intent = {"version": 1, "phase": "queued", "sources": sources, "destination": task.destfile, "metadata": task.metadata}
		self.pendingSaveIntents += 1
		deferToThread(self.saveJournal.create, intent).addBoth(self.timeshiftSaveIntentReady, job, entry)

	def timeshiftSaveIntentReady(self, result, job, entry):
		self.pendingSaveIntents -= 1
		if isinstance(result, Failure):
			if entry:
				self.timeshiftRegistry.release(entry, failed=True)
			self.ptsSaveTimeshiftFailed(str(result.value))
		else:
			job.tasks[0].journalPath = result
			JobManager.AddJob(job)

	def ptsAskUser(self, what):
		def ptsAskUserCallback(answer):
			self.ptsAskUser_wait = False
			match answer:
				case "restarttimeshift":
					self.ptsEventCleanTimerSTOP()
					self.save_current_timeshift = False
					self.stopTimeshiftAskUserCallback(True)
					self.restartTimeshift()
				case "noSave":
					self.ptsEventCleanTimerSTOP()
					self.save_current_timeshift = False
					self.stopTimeshiftAskUserCallback(True)
				case "savetimeshift" | "savetimeshiftandrecord":
					self.ptsEventCleanTimerSTOP()
					self.save_current_timeshift = True
					InfoBarTimeshift.saveTimeshiftActions(self, answer, self.stopTimeshiftAskUserCallback)
				case "golivetv":
					self.ptsEventCleanTimerSTOP(True)
					self.stopTimeshiftAskUserCallback(True)
					self.restartTimeshift()
				case "nolivetv":
					if self.pts_lastposition:
						self.setSeekState(self.SEEK_STATE_PLAY)
						self.doSeek(self.pts_lastposition)

		if not self.ptsAskUser_wait:
			message_time = _("The time shift buffer exceeds the limit specified in the settings.\nWhat do you want to do?")
			message_space = _("The available disk space for time shift buffer is less than specified in the settings.\nWhat do you want to do?")
			message_livetv = _("Can't go to live TV!\nSwitch to live TV and restart time shift?")
			message_nextfile = _("Can't play the next time shift buffer file!\nSwitch to live TV and restart time shift?")
			choice_restart = [
				(_("Delete the current time shift buffer and restart time shift"), "restarttimeshift"),
				(_("Nothing, just leave this menu"), "no")
			]
			choice_save = [
				(_("Stop time shift and save time shift buffer as a movie and start recording of current event"), "savetimeshiftandrecord"),
				(_("Stop time shift and save time shift buffer as a movie"), "savetimeshift"),
				(_("Stop time shift"), "noSave"),
				(_("Nothing, just leave this menu"), "no")
			]
			choice_livetv = [
				(_("No"), "nolivetv"),
				(_("Yes"), "golivetv")
			]
			match what:
				case "time":
					message = message_time
					choice = choice_restart
				case "space":
					message = message_space
					choice = choice_restart
				case "time_and_save":
					message = message_time
					choice = choice_save
				case "space_and_save":
					message = message_space
					choice = choice_save
				case "livetv":
					message = message_livetv
					choice = choice_livetv
				case "nextfile":
					message = message_nextfile
					choice = choice_livetv
				case _:
					message = ""
			if message:
				self.ptsAskUser_wait = True
				self.session.openWithCallback(ptsAskUserCallback, MessageBox, message, simple=True, list=choice, timeout=30)

	def stopTimeshiftAskUserCallback(self, answer):
		ts = self.getTimeshift()
		if answer and ts:
			generation = self.startGeneration
			wasEnabled = ts.isTimeshiftEnabled()
			result = ts.stopTimeshift(True)
			if wasEnabled and result:
				if generation == self.startGeneration:
					self.ptsTimeshiftWriteError()
				return False
			if generation != self.startGeneration:
				return False
			self.finishTimeshiftBuffer()
			self.releaseTimeshiftPlayback()
			self.__seekableStatusChanged()

	def ptsEventCleanTimerSTOP(self, justStop=False):
		if justStop is False:
			self.pts_firstplayable = self.pts_eventcount + 1
		if self.pts_cleanEvent_timer.isActive():
			self.pts_cleanEvent_timer.stop()
			print("[Timeshift] Clean event timer stopped.")

	def ptsEventCleanTimerSTART(self):
		if not self.pts_cleanEvent_timer.isActive() and config.timeshift.checkEvents.value:
			# self.pts_cleanEvent_timer.start(60000 * config.timeshift.checkEvents.value, False)
			self.pts_cleanEvent_timer.startLongTimer(60 * config.timeshift.checkEvents.value)
			print("[Timeshift] Clean event timer starting.")

	def ptsEventCleanTimeshiftFolder(self):
		print("[Timeshift] Clean event timer running.")
		self.ptsEventCleanTimerSTART()
		self.ptsCleanTimeshiftFolder(justZapped=False)

	def ptsCleanTimeshiftFolder(self, justZapped=True):
		if self.isRamTimeshift() or self.cleanupRunning or self.session.screen["Standby"].boolean:
			return True
		self.cleanupRunning = True
		self.cleanupProtected = []
		if self.timeshiftEnabled():
			first = self.pts_currplaying if self.isSeekable() else self.pts_eventcount
			for index in range(first, self.pts_eventcount + 1):
				entry = self.timeshiftRegistry.buffers.get(f"pts_livebuffer_{index}")
				if entry:
					self.cleanupProtected.append(entry.path)
		deferToThread(self.ptsCleanTimeshiftFiles, justZapped).addBoth(self.timeshiftCleanupFinished)
		return True

	def timeshiftCleanupFinished(self, result):
		self.cleanupRunning = False
		if isinstance(result, Failure):
			self.ptsHandleCleanupError(result.value)
		else:
			self.ptsCleanupError = None
			if not self.timeshiftRegistry.buffers:
				self.ptsEventCleanTimerSTOP(justStop=True)
			elif result < config.timeshift.checkFreeSpace.value:
				self.ptsAskUser("space_and_save" if self.isSeekable() else "space")
			elif self.timeshiftEnabled() and time() - self.pts_starttime > 3600 * config.timeshift.maxHours.value:
				self.ptsAskUser("time_and_save" if self.isSeekable() else "time")

	def ptsHandleCleanupError(self, err):
		# A disconnected device may still pass the path/access check. Do not keep
		# retrying the cleanup timer or start a new buffer after an I/O failure.
		error = (config.timeshift.path.value, getattr(err, "errno", None))
		if self.ptsCleanupError != error:
			self.ptsCleanupError = error
			self.ptsStorageError = None
		self.ptsAbortTimeshift(_("The time shift storage device is not available. Please check the device and the time shift path."), str(err))

	def ptsEraseTimeshiftFile(self, path, statinfo=None):
		try:
			if statinfo is None:
				statinfo = stat(path)
			self.BgFileEraser.erase(path)
			return statinfo.st_size
		except FileNotFoundError:
			return 0  # The background eraser may already have removed this file.

	def ptsCleanTimeshiftFiles(self, justZapped):
		registry = self.timeshiftRegistry
		retainedPaths = self.saveJournal.retainedPaths()
		registry.recover(config.timeshift.path.value, retainedPaths)
		status = statvfs(config.timeshift.path.value)
		freespace = status.f_bavail * status.f_bsize // 1024 // 1024
		protected = self.cleanupProtected + list(retainedPaths)
		entries = sorted(tuple(registry.buffers.items()), key=lambda x: x[1].created)
		maximumEvents = config.timeshift.maxEvents.value
		for index, (identifier, entry) in enumerate(entries):
			if self.saveTimeshiftEventPopupActive:
				break
			if justZapped or freespace < config.timeshift.checkFreeSpace.value or index < len(entries) - maximumEvents or entry.created < time() - 3600 * config.timeshift.maxHours.value:
				freespace += registry.remove(identifier, protected) // 1024 // 1024
		return freespace

	def ptsGetEventInfo(self):
		event = None
		try:
			serviceref = self.session.nav.getCurrentlyPlayingServiceOrGroup()
			serviceHandler = eServiceCenter.getInstance()
			info = serviceHandler.info(serviceref)
			self.pts_curevent_servicerefname = serviceref.toString()
			self.pts_curevent_station = info.getName(serviceref)
			service = self.session.nav.getCurrentService()
			info = service and service.info()
			event = info and info.getEvent(0)
		except Exception as err:
			AddNotification(MessageBox, f"{_("Getting event information failed!")}\n\n{str(err)}", MessageBox.TYPE_ERROR, timeout=10)
		if event is not None:
			curEvent = parseEvent(event)
			self.pts_curevent_begin = int(curEvent[0])
			self.pts_curevent_end = int(curEvent[1])
			self.pts_curevent_name = curEvent[2]
			self.pts_curevent_description = curEvent[3]
			self.pts_curevent_eventid = curEvent[4]

	def ptsFrontpanelActions(self, action=None):
		if self.session.nav.RecordTimer.isRecording() or BoxInfo.getItem("NumFrontpanelLEDs", 0) == 0:
			return
		if action == "start":
			if exists("/proc/stb/fp/led_set_pattern"):
				fileWriteLine("/proc/stb/fp/led_set_pattern", "0xa7fccf7a", source=MODULE_NAME)
			elif exists("/proc/stb/fp/led0_pattern"):
				fileWriteLine("/proc/stb/fp/led0_pattern", "0x55555555", source=MODULE_NAME)
			if exists("/proc/stb/fp/led_pattern_speed"):
				fileWriteLine("/proc/stb/fp/led_pattern_speed", "20", source=MODULE_NAME)
			elif exists("/proc/stb/fp/led_set_speed"):
				fileWriteLine("/proc/stb/fp/led_set_speed", "20", source=MODULE_NAME)
		elif action == "stop":
			if exists("/proc/stb/fp/led_set_pattern"):
				fileWriteLine("/proc/stb/fp/led_set_pattern", "0", source=MODULE_NAME)
			elif exists("/proc/stb/fp/led0_pattern"):
				fileWriteLine("/proc/stb/fp/led0_pattern", "0", source=MODULE_NAME)

	def ptsRegisterTimeshiftBuffer(self):
		# Keep recorder/playback/export ownership without a hard-link alias.
		if self.isRamTimeshift():
			return True
		ts = self.getTimeshift()
		filename = ts.getTimeshiftFilename() if ts else ""
		if not filename:
			self.ptsAbortTimeshift(_("The time shift buffer is not available."))
			return False
		ts.saveTimeshiftFile()
		metadata = {
			"service": self.pts_curevent_servicerefname,
			"name": self.ptsCurrentEventName,
			"description": self.ptsCurrentEventDescription,
			"begin": int(self.pts_starttime),
			"station": self.pts_curevent_station,
			"serviceData": ts.getTimeshiftServiceData() if hasattr(ts, "getTimeshiftServiceData") else "",
			"autosave": config.timeshift.autorecord.value
		}
		entry = self.timeshiftRegistry.register(f"pts_livebuffer_{self.pts_eventcount}", filename, metadata)
		entry.autosave = config.timeshift.autorecord.value
		if self.pendingPlaybackIdentifier:
			self.ptsSetNextPlaybackFile(self.pendingPlaybackIdentifier)
		self.persistTimeshiftMetadata(entry)
		self.ptsCreateEITFile(filename)
		return True

	def persistTimeshiftMetadata(self, entry):
		metadata = entry.metadata
		content = formatTimeshiftMetadata(dict(metadata, begin=int(metadata.get("begin", entry.created))))
		self.timeshiftRegistry.acquire(entry)
		entry.pendingWrites += 1
		entry.sidecarsReady.clear()
		deferToThread(self.writeTimeshiftMetadata, entry, content).addBoth(self.timeshiftMetadataWritten, entry)

	def writeTimeshiftMetadata(self, entry, content):
		self.timeshiftRegistry.writeMetadata(entry, content)

	def timeshiftMetadataWritten(self, result, entry):
		if isinstance(result, int) and result != 0:
			result = Failure(OSError(_("Unable to write the time shift event information.")))
		failed = isinstance(result, Failure)
		entry.pendingWrites -= 1
		if not entry.pendingWrites:
			entry.sidecarsReady.set()
		self.timeshiftRegistry.release(entry, failed=failed)
		if failed:
			if entry.active:
				entry.autosave = False
				self.ptsAbortTimeshift(_("Unable to update the time shift buffer."), str(result.value))
			else:
				self.ptsSaveTimeshiftFailed(str(result.value))

	def ptsRecordCurrentEvent(self, task=None):
		recording = RecordTimerEntry(ServiceReference(self.session.nav.getCurrentlyPlayingServiceOrGroup()), time(), self.pts_curevent_end, self.pts_curevent_name, self.pts_curevent_description, self.pts_curevent_eventid, afterEvent=AFTEREVENT.AUTO, justplay=False, always_zap=False, dirname=preferredTimeShiftRecordingPath())
		self.recordTimeshiftContinuation(recording, task)
		return recording

	def recordTimeshiftContinuation(self, recording, task):
		owner = None
		if task is not None and task.mergelater:
			owner = TimeshiftContinuation(recording)
			task.continuation = owner
			self.continuationRecordings[id(recording)] = owner
		recording.dontSave = True
		timers = self.session.nav.RecordTimer
		conflicts = timers.record(recording)
		accepted = not conflicts and any(x is recording for x in (*timers.timer_list, *timers.processed_timers))
		if owner:
			owner.invalid = owner.invalid or not accepted
			owner.capture()
		if accepted:
			self.recording.append(recording)

	def registerTimeshiftMerge(self, destination, owner):
		self.pendingMerges.add(destination)
		if owner is not None and owner.destination is None:
			owner.destination = destination
			self.mergeOwners[destination] = owner
		self.pts_mergeRecords_timer.start(15000, True)

	def ptsMergeRecords(self):
		if self.mergeScanRunning:
			return
		if self.session.nav.RecordTimer.isRecording() or JobManager.getPendingJobs() or self.pendingSaveIntents:
			self.pts_mergeRecords_timer.start(120000, True)
			return
		if self.pendingMerges:
			candidates = []
			for destination in self.pendingMerges:
				owner = self.mergeOwners.get(destination)
				if owner:
					owner.capture()
					if not owner.invalid and owner.timer.state < TimerEntry.StateEnded:
						self.pts_mergeRecords_timer.start(120000, True)
						continue
				if owner and not owner.invalid and owner.path and owner.path != destination and owner.path not in self.pendingMerges and owner.timer.state == TimerEntry.StateEnded:
					candidates.append((owner.path, destination, owner.timer.name))
				else:
					self.notifyUnownedTimeshiftMerge(destination)
			if not candidates:
				return
			self.mergeScanRunning = True
			deferToThread(self.findTimeshiftMerges, tuple(candidates)).addBoth(self.timeshiftMergesFound, tuple(x[1] for x in candidates))

	def findTimeshiftMerges(self, candidates):
		results = []
		for source, destination, eventname in candidates:
			try:
				getTimeshiftParts(source)
				getTimeshiftParts(destination)
				results.append((source, destination, eventname))
			except FileNotFoundError:
				pass
		return results

	def notifyUnownedTimeshiftMerge(self, destination):
		if destination not in self.mergeWarnings:
			self.mergeWarnings.add(destination)
			self.session.showInfo(_("The continuation recording could not be identified safely. Both recordings and the merge information have been retained.") + f"\n{destination}", timeout=30)

	def timeshiftMergesFound(self, result, destinations=()):
		self.mergeScanRunning = False
		if isinstance(result, Failure):
			self.ptsSaveTimeshiftFailed(str(result.value))
		elif self.session.nav.RecordTimer.isRecording():
			self.pts_mergeRecords_timer.start(120000, True)
		else:
			for srcfile, destfile, eventname in result:
				owner = self.mergeOwners.get(destfile)
				if owner:
					owner.capture()
				if owner and not owner.invalid and owner.path == srcfile and owner.timer.state == TimerEntry.StateEnded:
					self.queueTimeshiftSave(MergeTimeshiftJob(self, None, srcfile, destfile, eventname))
				else:
					self.notifyUnownedTimeshiftMerge(destfile)
			found = {x[1] for x in result}
			for destination in destinations:
				if destination not in found:
					self.notifyUnownedTimeshiftMerge(destination)

	def ptsCreateAPSCFiles(self, filename):
		JobManager.AddJob(CreateAPSCFilesJob(self, ("/usr/lib/enigma2/python/Components/createapscfiles", filename), _("Timeshift")))

	def ptsCreateEITFile(self, filename):
		if self.pts_curevent_eventid is not None:
			try:
				serviceref = ServiceReference(self.session.nav.getCurrentlyPlayingServiceOrGroup()).ref
				entry = next((x for x in self.timeshiftRegistry.buffers.values() if x.path == filename), None)
				if entry:
					self.timeshiftRegistry.acquire(entry)
					entry.pendingWrites += 1
					entry.sidecarsReady.clear()
					deferToThread(self.timeshiftRegistry.writeEvent, entry, eEPGCache.getInstance().saveEventToFile, serviceref, self.pts_curevent_eventid, -1, -1).addBoth(self.timeshiftMetadataWritten, entry)
			except Exception as err:
				print(f"[Timeshift] Error: {str(err)}")

	def ptsCopyFilefinished(self, srcfile, destfile):
		# The source remains registry-owned until ordinary retention cleanup.
		if destfile in self.pendingMerges:
			self.pts_mergeRecords_timer.start(15000, True)
		else:
			self.ptsCreateAPSCFiles(destfile)

	def ptsSaveTimeshiftFailed(self, message):
		self.save_timeshift_postaction = None
		self.ptsFrontpanelActions("stop")
		config.timeshift.isRecording.value = False
		AddNotification(MessageBox, _("Time shift save failed! The source buffer has been retained.") + f"\n\n{message}", MessageBox.TYPE_ERROR, timeout=30)

	def ptsMergeFilefinished(self, srcfile, destfile, sourceIdentity=None):
		self.pendingMerges.discard(destfile)
		owner = self.mergeOwners.get(destfile)
		if owner:
			owner.capture()
		if owner and not owner.invalid and owner.path == srcfile and owner.timer.state == TimerEntry.StateEnded and sourceIdentity is not None:
			self.mergeCleanupSources[srcfile] = sourceIdentity
			self.pts_mergeCleanUp_timer.start(1000, True)
			self.continuationRecordings.pop(id(owner.timer), None)
			self.mergeOwners.pop(destfile, None)
		else:
			self.notifyUnownedTimeshiftMerge(destfile)
		self.ptsCreateAPSCFiles(destfile)
		if self.pendingMerges:
			self.pts_mergeRecords_timer.start(10000, True)

	def ptsSaveTimeshiftFinished(self):
		if not self.pts_mergeCleanUp_timer.isActive():
			self.ptsFrontpanelActions("stop")
			config.timeshift.isRecording.value = False
		if Standby.inTryQuitMainloop:
			self.pts_QuitMainloop_timer.start(30000, True)
		else:
			self.session.showInfo(_("Time shift saved!"))

	def ptsMergePostCleanUp(self):
		if self.session.nav.RecordTimer.isRecording() or JobManager.getPendingJobs():
			self.pts_mergeCleanUp_timer.start(120000, True)
			return
		if self.mergeCleanupSources:
			sources = tuple(self.mergeCleanupSources.items())
			self.mergeCleanupSources.clear()
			deferToThread(self.removeMergedTimeshiftSources, sources).addBoth(self.mergedTimeshiftSourcesRemoved)

	def removeMergedTimeshiftSources(self, sources):
		for source, identity in sources:
			removeTimeshiftRecording(source, identity)

	def mergedTimeshiftSourcesRemoved(self, result):
		if isinstance(result, Failure):
			AddNotification(MessageBox, _("The time shift recording was saved, but a temporary recording could not be removed.") + f"\n{result.value}", MessageBox.TYPE_ERROR, timeout=30)
		self.ptsFrontpanelActions("stop")
		config.timeshift.isRecording.value = False

	def ptsTryQuitMainloop(self):
		if Standby.inTryQuitMainloop and (self.pendingSaveIntents or len(JobManager.getPendingJobs()) >= 1 or self.pts_mergeCleanUp_timer.isActive()):
			self.pts_QuitMainloop_timer.start(60000, True)
			return
		if Standby.inTryQuitMainloop and self.session.ptsmainloopvalue:
			self.session.dialog_stack = []
			self.session.summary_stack = [None]
			self.session.open(Standby.TryQuitMainloop, self.session.ptsmainloopvalue)

	def ptsGetSeekInfo(self):
		s = self.session.nav.getCurrentService()
		return s and s.seek()

	def ptsGetPosition(self):
		seek = self.ptsGetSeekInfo()
		if seek is None:
			return None
		pos = seek.getPlayPosition()
		if pos[0]:
			return 0
		return pos[1]

	def ptsGetLength(self):
		seek = self.ptsGetSeekInfo()
		if seek is None:
			return None
		length = seek.getLength()
		if length[0]:
			return 0
		return length[1]

	def ptsGetTimeshiftStatus(self):
		return (self.isSeekable() and self.timeshiftEnabled() or self.save_current_timeshift) and config.timeshift.check.value

	def ptsSeekPointerOK(self):
		if "PTSSeekPointer" in self.pvrStateDialog and self.timeshiftEnabled() and self.isSeekable():
			if not self.pvrStateDialog.shown:
				if self.seekstate != self.SEEK_STATE_PLAY or self.seekstate == self.SEEK_STATE_PAUSE:
					self.setSeekState(self.SEEK_STATE_PLAY)
				self.doShow()
				return
			length = self.ptsGetLength()
			position = self.ptsGetPosition()
			if length is None or position is None:
				return
			cur_pos = self.pvrStateDialog["PTSSeekPointer"].position
			jumptox = int(cur_pos[0]) - (int(self.pvrStateDialog["PTSSeekBack"].instance.position().x()) + 8)
			jumptoperc = round((jumptox / float(self.pvrStateDialog["PTSSeekBack"].instance.size().width())) * 100, 0)
			jumptotime = int((length / 100) * jumptoperc)
			jumptodiff = position - jumptotime
			self.doSeekRelative(-jumptodiff)

	def ptsSeekPointerLeft(self):
		if "PTSSeekPointer" in self.pvrStateDialog and self.pvrStateDialog.shown and self.timeshiftEnabled() and self.isSeekable():
			self.ptsMoveSeekPointer(direction="left")

	def ptsSeekPointerRight(self):
		if "PTSSeekPointer" in self.pvrStateDialog and self.pvrStateDialog.shown and self.timeshiftEnabled() and self.isSeekable():
			self.ptsMoveSeekPointer(direction="right")

	def ptsSeekPointerReset(self):
		if "PTSSeekPointer" in self.pvrStateDialog and self.timeshiftEnabled():
			self.pvrStateDialog["PTSSeekPointer"].setPosition(int(self.pvrStateDialog["PTSSeekBack"].instance.position().x()) + 8, self.pvrStateDialog["PTSSeekPointer"].position[1])

	def ptsSeekPointerSetCurrentPos(self):
		if "PTSSeekPointer" not in self.pvrStateDialog or not self.timeshiftEnabled() or not self.isSeekable():
			return
		position = self.ptsGetPosition()
		length = self.ptsGetLength()
		if length >= 1:
			tpixels = int((float(int((position * 100) / length)) / 100) * self.pvrStateDialog["PTSSeekBack"].instance.size().width())
			self.pvrStateDialog["PTSSeekPointer"].setPosition(int(self.pvrStateDialog["PTSSeekBack"].instance.position().x()) + 8 + tpixels, self.pvrStateDialog["PTSSeekPointer"].position[1])

	def ptsMoveSeekPointer(self, direction=None):
		if direction is None or "PTSSeekPointer" not in self.pvrStateDialog:
			return
		isvalidjump = False
		cur_pos = self.pvrStateDialog["PTSSeekPointer"].position
		self.doShow()
		if direction == "left":
			minmaxval = int(self.pvrStateDialog["PTSSeekBack"].instance.position().x()) + 8
			movepixels = -15
			if cur_pos[0] + movepixels > minmaxval:
				isvalidjump = True
		elif direction == "right":
			minmaxval = int(self.pvrStateDialog["PTSSeekBack"].instance.size().width() * 0.96)
			movepixels = 15
			if cur_pos[0] + movepixels < minmaxval:
				isvalidjump = True
		else:
			return 0
		self.pvrStateDialog["PTSSeekPointer"].setPosition(cur_pos[0] + movepixels if isvalidjump else minmaxval, cur_pos[1])

	def ptsCheckFileChanged(self):
		if not self.timeshiftEnabled():
			self.pts_CheckFileChanged_timer.stop()
			return
		if self.pts_CheckFileChanged_counter >= 5 and not self.pts_file_changed:
			if self.pts_switchtolive:
				if config.timeshift.showLiveTVMsg.value:
					self.ptsAskUser("livetv")
			elif self.pts_lastplaying <= self.pts_currplaying:
				self.ptsAskUser("nextfile")
			else:
				self.session.showWarning(_("Can't play the previous time shift file! You can try again."))
				self.doSeek(0)
				self.setSeekState(self.SEEK_STATE_PLAY)
			self.pts_currplaying = self.pts_lastplaying
			self.pts_CheckFileChanged_timer.stop()
			return
		self.pts_CheckFileChanged_counter += 1
		if self.pts_file_changed:
			self.pts_CheckFileChanged_timer.stop()
			if self.posDiff:
				self.pts_SeekToPos_timer.start(1000, True)
			elif self.pts_FileJump_timer.isActive():
				self.pts_FileJump_timer.stop()
			elif self.pts_lastplaying > self.pts_currplaying:
				self.pts_SeekBack_timer.start(1000, True)
		else:
			self.doSeek(3600 * 24 * 90000)

	def ptsTimeshiftFileChanged(self):
		keep = {f"pts_livebuffer_{self.pts_currplaying}", f"pts_livebuffer_{self.pts_nextplaying}"}
		if self.pts_switchtolive:
			keep.clear()
		for identifier in tuple(self.playbackLeases):
			if identifier not in keep:
				self.timeshiftRegistry.release(self.playbackLeases.pop(identifier))
		self.pts_file_changed = True
		self.ptsSeekPointerReset()  # Reset seek pointer.
		if self.pts_switchtolive:
			self.pts_switchtolive = False
			self.pts_nextplaying = 0
			self.pts_currplaying = self.pts_eventcount
		else:
			if self.pts_nextplaying:
				self.pts_currplaying = self.pts_nextplaying
			self.pts_nextplaying = self.pts_currplaying + 1
			if self.hasTimeshiftFile(f"pts_livebuffer_{self.pts_nextplaying}"):  # Get next PTS file.
				self.ptsSetNextPlaybackFile(f"pts_livebuffer_{self.pts_nextplaying}")
				self.pts_switchtolive = False
			else:
				self.ptsSetNextPlaybackFile("")
				self.pts_switchtolive = True

	def ptsSetNextPlaybackFile(self, nexttsfile):
		ts = self.getTimeshift()
		if ts:
			if nexttsfile:
				entry = self.timeshiftRegistry.buffers.get(nexttsfile)
				if entry is None:
					path = self.resolveTimeshiftFile(nexttsfile)
					entry = next((x for x in self.timeshiftRegistry.buffers.values() if x.path == path), None)
				if entry is None:
					self.pendingPlaybackIdentifier = nexttsfile
					return
				if nexttsfile not in self.playbackLeases:
					try:
						self.timeshiftRegistry.acquire(entry)
					except OSError as err:
						self.session.showWarning(str(err))
						return
					self.playbackLeases[nexttsfile] = entry
			self.pendingPlaybackIdentifier = ""
			ts.setNextPlaybackFile(self.resolveTimeshiftFile(nexttsfile) if nexttsfile else "")

	def ptsSeekToPos(self):
		length = self.ptsGetLength()
		if length is None:
			return
		if self.posDiff < 0:
			if length <= abs(self.posDiff):
				self.posDiff = 0
		else:
			if length <= abs(self.posDiff):
				tmp = length - 90000 * 10
				if tmp < 0:
					tmp = 0
				self.posDiff = tmp
		self.setSeekState(self.SEEK_STATE_PLAY)
		self.doSeek(self.posDiff)
		self.posDiff = 0

	def ptsSeekBackTimer(self):
		self.doSeek(-90000 * 10)  # Seek ~10 seconds before end.
		self.setSeekState(self.SEEK_STATE_PAUSE)
		self.pts_StartSeekBackTimer.start(1000, True)

	def ptsStartSeekBackTimer(self):
		self.setSeekState(self.makeStateBackward(int(config.seek.enter_backward.value) if self.pts_lastseekspeed == 0 else -self.pts_lastseekspeed))

	def isRamTimeshift(self):
		ts = self.getTimeshift()
		return bool(ts and hasattr(ts, "isTimeshiftMemory") and ts.isTimeshiftMemory())

	def ptsCheckTimeshiftPath(self):
		if self.isRamTimeshift():
			return True
		if fileExists(config.timeshift.path.value, "w"):
			return True
		else:
			self.pts_delay_timer.stop()
			self.pts_cleanUp_timer.stop()
			if self.timeshiftEnabled():
				self.ptsAbortTimeshift(_("The time shift storage device is not available. Please check the device and the time shift path."))
			return False

	def ptsTimerEntryStateChange(self, timer):
		owner = self.continuationRecordings.get(id(timer))
		if owner is not None and owner.timer is timer:
			owner.capture()
			if timer.state >= TimerEntry.StateEnded and owner.destination:
				self.pts_mergeRecords_timer.start(15000, True)
		if config.timeshift.stopWhileRecording.value:
			self.pts_record_running = self.session.nav.RecordTimer.isRecording()
			if not self.session.screen["Standby"].boolean:  # Abort here when box is in standby mode.
				if timer.state == TimerEntry.StateRunning and self.timeshiftEnabled() and self.pts_record_running:  # Stop time shift when recording started.
					if self.seekstate != self.SEEK_STATE_PLAY:
						self.setSeekState(self.SEEK_STATE_PLAY)
					if self.isSeekable():
						self.session.showInfo(_("Recording started, stopping time shift now."), timeout=10)
					self.switchToLive = False
					self.stopTimeshiftcheckTimeshiftRunningCallback(True)
				if timer.state == TimerEntry.StateEnded:
					if not self.timeshiftEnabled() and not self.pts_record_running:  # Restart time shift when all recordings stopped.
						self.autostartPermanentTimeshift()
					if self.pts_mergeRecords_timer.isActive():
						self.pts_mergeRecords_timer.stop()  # Restart merge timer when all recordings stopped.
						self.pts_mergeRecords_timer.start(15000, True)
						self.ptsFrontpanelActions("start")  # Restart front panel LED when still copying or merging files.
						config.timeshift.isRecording.value = True
					else:
						jobs = JobManager.getPendingJobs()  # Restart front panel LED when still copying or merging files.
						if len(jobs) >= 1:
							for job in jobs:
								jobname = str(job.name)
								if jobname in (_("Saving time shift files"), _("Creating .ap and .sc files"), _("Merging time shift files")):
									self.ptsFrontpanelActions("start")
									config.timeshift.isRecording.value = True
									break

	def ptsLiveTVStatus(self):
		service = self.session.nav.getCurrentService()
		info = service and service.info()
		sTSID = info and info.getInfo(iServiceInformation.sTSID) or -1
		return not (sTSID is None or sTSID == -1)


class CopyTimeshiftJob(Job):
	def __init__(self, toolbox, cmdline, srcfile, destfile, eventname):
		Job.__init__(self, _("Saving time shift files"))
		self.toolbox = toolbox
		AddCopyTimeshiftTask(self, cmdline, srcfile, destfile, eventname)


class AddCopyTimeshiftTask(Task):
	def __init__(self, job, cmdline, srcfile, destfile, eventname):
		Task.__init__(self, job, eventname)
		self.toolbox = job.toolbox
		self.srcfile = srcfile if isabs(srcfile) else join(config.timeshift.path.value, f"{srcfile}.copy")
		self.destfile = destfile
		self.entry = None
		self.limit = None
		self.metadata = None
		self.mergelater = False
		self.continuation = None
		self.journalPath = None
		self.export = None
		self.aborted = False
		self.completed = False
		self.ProgressTimer = eTimer()
		self.ProgressTimer.callback.append(self.ProgressUpdate)

	def ProgressUpdate(self):
		if self.export and self.export.total:
			self.setProgress(min(99, self.export.copied * 100 // self.export.total))

	def prepare(self):
		self.completed = False
		self.aborted = False
		self.postconditions = []
		self.ProgressTimer.start(1000)
		self.toolbox.ptsFrontpanelActions("start")

	def _run(self):
		deferToThread(self.work).addBoth(self.workFinished)

	def work(self):
		if self.aborted:
			raise InterruptedError("Saving time shift was cancelled")
		while self.entry and not self.entry.sidecarsReady.wait(0.5):
			if self.aborted:
				raise InterruptedError("Saving time shift was cancelled")
		if isinstance(self.destfile, tuple):
			recordingPath, recordingName = self.destfile
			self.destfile = f"{getRecordingFilename(recordingName, recordingPath)}.ts"
		elif not self.destfile.endswith(".ts"):
			self.destfile = f"{self.destfile}.ts"
		immutable = self.entry is not None and not self.entry.active and self.limit is None
		partSize = self.getExportPartSize()
		if immutable:
			parts = getTimeshiftParts(self.srcfile)
			if len(parts) > 1 and all(x[1] == parts[0][1] for x in parts[:-1]) and parts[-1][1] <= parts[0][1] <= partSize:
				partSize = parts[0][1]
		self.export = TimeshiftExport(((self.srcfile, self.limit),), self.destfile, self.metadata, immutable=immutable, partSize=partSize, intentPath=self.journalPath)
		if self.aborted:
			self.export.cancelled.set()
		result = self.export.run()
		self.completeSaveIntent()
		return result

	def completeSaveIntent(self):
		if self.journalPath:
			try:
				self.toolbox.saveJournal.complete(self.journalPath)
				if self.entry and self.limit is None and self.entry.path not in self.toolbox.saveJournal.retainedPaths():
					self.entry.retained = False
			except OSError as err:
				if self.entry:
					self.entry.retained = True
				print(f"[Timeshift] Saved recording; retained local save intent: {err}")

	def getExportPartSize(self):
		path = realpath(dirname(self.destfile))
		mounts = [x for x in getProcMounts() if len(x) >= 3 and (path == x[1] or path.startswith(join(x[1], "")))]
		mount = max(mounts, key=lambda x: len(x[1])) if mounts else None
		unlimited = {"ext2", "ext3", "ext4", "xfs", "btrfs", "f2fs", "exfat", "ntfs", "ntfs3"}
		return ((1 << 63) - 1) // 188 * 188 if mount and mount[2] in unlimited else EXPORT_PART_SIZE

	def workFinished(self, result):
		if self.completed:
			return
		self.completed = True
		self.ProgressTimer.stop()
		if isinstance(result, Failure):
			self.postconditions.append(FailedPostcondition(result.value))
		self.finish(aborted=self.aborted)

	def abort(self):
		self.aborted = True
		if self.export:
			self.export.cancelled.set()
		# Completion waits for the worker to close its files and roll back.

	def cleanup(self, failed):
		if self.entry:
			self.toolbox.timeshiftRegistry.release(self.entry, failed=bool(failed))
		if failed:
			self.toolbox.ptsSaveTimeshiftFailed("\n".join(x.getErrorMessage(self) for x in failed))
		else:
			self.setProgress(100)
			if self.mergelater:
				self.toolbox.registerTimeshiftMerge(self.destfile, self.continuation)
			self.toolbox.ptsCopyFilefinished(self.srcfile, self.destfile)


class MergeTimeshiftJob(Job):
	def __init__(self, toolbox, cmdline, srcfile, destfile, eventname):
		Job.__init__(self, _("Merging time shift files"))
		self.toolbox = toolbox
		AddMergeTimeshiftTask(self, cmdline, srcfile, destfile, eventname)


class AddMergeTimeshiftTask(AddCopyTimeshiftTask):
	def __init__(self, job, cmdline, srcfile, destfile, eventname):
		AddCopyTimeshiftTask.__init__(self, job, None, join(preferredTimeShiftRecordingPath(), srcfile), join(preferredTimeShiftRecordingPath(), destfile), eventname)
		self.sourceIdentity = None

	def work(self):
		with open(f"{self.destfile}.meta", encoding="utf-8") as metadataFile:
			metadata = parseTimeshiftMetadata(metadataFile.read())
		tags = " ".join(x for x in metadata.get("tags", "").split() if x != "pts_merge")
		self.metadata = formatTimeshiftMetadata(metadata, tags=tags)
		self.export = TimeshiftExport(((self.destfile, None), (self.srcfile, None)), self.destfile, metadata=self.metadata, immutable=True, partSize=self.getExportPartSize(), merge=True, intentPath=self.journalPath)
		if self.aborted:
			self.export.cancelled.set()
		result = self.export.run()
		self.sourceIdentity = self.export.sourceIdentities.get(self.srcfile)
		self.completeSaveIntent()
		return result

	def cleanup(self, failed):
		if failed:
			self.toolbox.ptsSaveTimeshiftFailed("\n".join(x.getErrorMessage(self) for x in failed))
		else:
			self.setProgress(100)
			self.toolbox.ptsMergeFilefinished(self.srcfile, self.destfile, self.sourceIdentity)


class CreateAPSCFilesJob(Job):
	def __init__(self, toolbox, cmdline, eventname):
		Job.__init__(self, _("Creating .ap and .sc files"))
		self.toolbox = toolbox
		CreateAPSCFilesTask(self, cmdline, eventname)


class CreateAPSCFilesTask(Task):
	def __init__(self, job, cmdline, eventname):
		Task.__init__(self, job, eventname)
		self.toolbox = job.toolbox
		self.finished = False
		arguments = splitCommand(cmdline) if isinstance(cmdline, str) else list(cmdline)
		self.setTool(arguments[0])
		self.args += arguments[1:arguments.index(">")] if ">" in arguments else arguments[1:]

	def prepare(self):
		self.finished = False
		self.toolbox.ptsFrontpanelActions("start")
		config.timeshift.isRecording.value = True

	def _run(self):
		self.container = eConsoleAppContainer()
		self.container.appClosed.append(self.processFinished)
		self.container.stdoutAvail.append(self.processStdout)
		self.container.stderrAvail.append(self.processStderr)
		if self.container.execute(self.cmd, *self.args):
			self.processFinished(-1)

	def finish(self, aborted=False):
		if not self.finished:
			self.finished = True
			Task.finish(self, aborted=aborted)

	def cleanup(self, failed):
		if failed:
			self.toolbox.ptsSaveTimeshiftFailed("\n".join(x.getErrorMessage(self) for x in failed))
		else:
			self.setProgress(100)
			self.toolbox.ptsSaveTimeshiftFinished()
