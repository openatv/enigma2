from os import link, listdir, makedirs, rename, stat, statvfs, system
from os.path import exists, getsize, join, splitext
from random import randint
from time import localtime, strftime, time

from enigma import eBackgroundFileEraser, eEPGCache, eServiceCenter, eServiceReference, eTimer, iPlayableService, iServiceInformation

from RecordTimer import AFTEREVENT, RecordTimerEntry, parseEvent
from ServiceReference import ServiceReference
from timer import TimerEntry
from Components.ActionMap import HelpableActionMap
from Components.config import config
from Components.ServiceEventTracker import ServiceEventTracker
from Components.SystemInfo import BoxInfo
from Components.Task import Job, Task, job_manager as JobManager
from Components.UsageConfig import preferredTimeShiftRecordingPath
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
import Screens.Standby
from Tools.ASCIItranslit import legacyEncode
from Tools.BoundFunction import boundFunction
from Tools.Directories import SCOPE_TIMESHIFT, copyfile, fileExists, fileWriteLine, getRecordingFilename, resolveFilename
from Tools.Notifications import AddNotification

MODULE_NAME = __name__.split(".")[-1]


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
		self.__event_tracker = ServiceEventTracker(screen=self, eventmap={
			iPlayableService.evStart: self.__serviceStarted,
			iPlayableService.evSeekableStatusChanged: self.__seekableStatusChanged,
			iPlayableService.evEnd: self.__serviceEnd,
			iPlayableService.evSOF: self.__evSOF,
			iPlayableService.evUpdatedInfo: self.__evInfoChanged,
			iPlayableService.evUpdatedEventInfo: self.__evEventInfoChanged,
			iPlayableService.evUser + 1: self.ptsTimeshiftFileChanged
		})
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

	def getCurrentEventName(self):
		return self.pts_curevent_name.replace("\n", " ") if self.pts_curevent_name else ""

	currentEventName = property(getCurrentEventName)

	def getCurrentEventDescription(self):
		return self.pts_curevent_description.replace("\n", " ") if self.pts_curevent_description else ""

	currentEventDescription = property(getCurrentEventDescription)

	def __seekableStatusChanged(self):
		# print(f"[Timeshift] PTS_currplaying {self.pts_currplaying}, pts_nextplaying {self.pts_nextplaying}, pts_eventcount {self.pts_eventcount}, pts_firstplayable {self.pts_firstplayable}.")
		self["TimeshiftActivateActions"].setEnabled(not self.isSeekable() and self.timeshiftEnabled())
		state = self.getSeek() is not None and self.timeshiftEnabled()
		self["SeekActionsPTS"].setEnabled(state)
		self["TimeshiftFileActions"].setEnabled(state)
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
		self.service_changed = 1
		self.pts_service_changed = True
		if self.pts_delay_timer.isActive():
			self.pts_delay_timer.stop()
		if config.timeshift.startDelay.value:
			self.pts_delay_timer.start(config.timeshift.startDelay.value * 1000, True)
		# self.__seekableStatusChanged()
		self["TimeshiftActions"].setEnabled(True)

	def __serviceEnd(self):
		if self.save_current_timeshift:
			if self.pts_curevent_end > time():
				self.SaveTimeshift(f"pts_livebuffer_{self.pts_eventcount}", mergelater=True)
				self.ptsRecordCurrentEvent()
			else:
				self.SaveTimeshift(f"pts_livebuffer_{self.pts_eventcount}")
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
			if info and info.getInfo(iServiceInformation.sIsRecoveringStream):
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
					AddNotification(MessageBox, _("First playable time shift file!"), MessageBox.TYPE_INFO, timeout=3)
				if not self.pts_FileJump_timer.isActive():
					self.pts_FileJump_timer.start(5000, True)
				return
			# Switch to previous TS file by seeking backwards to the previous file.
			if fileExists(join(config.timeshift.path.value, f"pts_livebuffer_{self.pts_currplaying}"), "r"):
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
			if info and info.getInfo(iServiceInformation.sIsRecoveringStream):
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
			if fileExists(join(config.timeshift.path.value, f"pts_livebuffer_{self.pts_currplaying}"), "r"):
				self.ptsSetNextPlaybackFile(f"pts_livebuffer_{self.pts_currplaying}")
				self.setSeekState(self.SEEK_STATE_PLAY)
				self.doSeek(3600 * 24 * 90000)
				self.pts_CheckFileChanged_counter = 1
				self.pts_CheckFileChanged_timer.start(1000, False)
				self.pts_file_changed = False
			else:
				if not config.timeshift.startDelay.value and config.timeshift.showLiveTVMsg.value:
					AddNotification(MessageBox, _("Switching to live TV - time shift is still active!"), MessageBox.TYPE_INFO, timeout=3)
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
				self.ptsEventCleanTimerSTOP()
			self.pts_firstplayable = self.pts_eventcount + 1
			if self.pts_eventcount == 0 and not config.timeshift.startDelay.value:
				self.pts_cleanUp_timer.start(1000, True)

	def __evEventInfoChanged(self):
		service = self.session.nav.getCurrentService()  # Get current event info.
		old_begin_time = self.pts_begintime
		info = service and service.info()
		ptr = info and info.getEvent(0)
		self.pts_begintime = ptr and ptr.getBeginTime() or 0
		if info.getInfo(iServiceInformation.sVideoPID) != -1:  # Save current time shift buffer permanently now.
			if self.save_current_timeshift and self.timeshiftEnabled():  # Take care of recording margin time.
				if config.recording.margin_after.value > 0 and len(self.recording) == 0:
					self.SaveTimeshift(mergelater=True)
					recording = RecordTimerEntry(ServiceReference(self.session.nav.getCurrentlyPlayingServiceOrGroup()), time(), time() + (config.recording.margin_after.value * 60), self.pts_curevent_name, self.pts_curevent_description, self.pts_curevent_eventid, afterEvent=AFTEREVENT.AUTO, justplay=False, always_zap=False, dirname=preferredTimeShiftRecordingPath())
					recording.dontSave = True
					self.session.nav.RecordTimer.record(recording)
					self.recording.append(recording)
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
		if ts is None:
			# self.session.open(MessageBox, _("Time shift not possible!"), MessageBox.TYPE_ERROR, timeout=5)
			return self.playpauseService2()
		if ts.isTimeshiftEnabled():
			print("[Timeshift] Time shift already enabled.")
			self.activateTimeshiftEndAndPause()
		else:
			self.activatePermanentTimeshift()
			self.activateTimeshiftEndAndPause()

	def stopTimeshift(self):
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
			return 0

	def stopTimeshiftcheckTimeshiftRunningCallback(self, answer):
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
			ts.stopTimeshift(self.switchToLive if config.timeshift.startDelay.value else not self.event_changed)
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
		from Screens.InfoBarGenerics import isStandardInfoBar
		if isStandardInfoBar(self):
			ServiceEventTracker.setActiveInfoBar(self, None, None)
			self.__serviceStarted()

	def activateTimeshiftEndAndPause(self):  # Same as activateTimeshiftEnd, but pauses afterwards.
		self.activateTimeshiftEnd(False)

	def checkTimeshiftRunning(self, returnFunction):
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
					self.session.openWithCallback(boundFunction(self.checkTimeshiftRunningCallback, returnFunction), MessageBox, message, simple=True, list=choice, timeout=30)
				else:
					message = _("You seem to be in time shift, do you want to leave time shift?")
					choice = [
						(_("Yes, but don't save time shift as movie"), "noSave"),
						(_("Yes, but save time shift as movie and continue recording"), "savetimeshiftandrecord"),
						(_("Yes, but save time shift as movie and stop recording"), "savetimeshift"),
						(_("No"), "no")
					]
					self.session.openWithCallback(boundFunction(self.checkTimeshiftRunningCallback, returnFunction), MessageBox, message, simple=True, list=choice, timeout=30)
			else:
				if self.save_current_timeshift:
					# The user has previously activated "Time shift save recording" of current event - so must be necessarily saved of the timeshift!
					# workaround - without the message box can the box no longer be operated when goes in standby(no freezing - no longer can use - unhandled key screen comes when key press -)
					message = _("You have chosen to save the current time shift buffer")
					choice = [(_("Save time shift buffer now and continue recording"), "savetimeshiftandrecord")]
					self.session.openWithCallback(boundFunction(self.checkTimeshiftRunningCallback, returnFunction), MessageBox, message, simple=True, list=choice, timeout=1)
					# InfoBarTimeshift.saveTimeshiftActions(self, "savetimeshiftandrecord", returnFunction)
				else:
					message = _("You seem to be in time shift, do you want to leave time shift?")
					choice = [
						(_("Yes"), config.timeshift.favoriteSaveAction.value),
						(_("No"), "no")
					]
					self.session.openWithCallback(boundFunction(self.checkTimeshiftRunningCallback, returnFunction), MessageBox, message, simple=True, list=choice, timeout=30)
		elif self.save_current_timeshift:
			# The user has chosen "no warning" when time shift is stopped (config.timeshift.check=False)
			# but the user has previously activated "Time shift save recording" of current event
			# so we silently do "savetimeshiftandrecord" when switching channel independent of config.timeshift.favoriteSaveAction
			# workaround - without the message box can the box no longer be operated when goes in standby(no freezing - no longer can use - unhandled key screen comes when key press -)
			message = _("You have chosen to save the current time shift buffer")
			choice = [(_("Save time shift buffer now and continue recording"), "savetimeshiftandrecord")]
			self.session.openWithCallback(boundFunction(self.checkTimeshiftRunningCallback, returnFunction), MessageBox, message, simple=True, list=choice, timeout=1)
			# InfoBarTimeshift.saveTimeshiftActions(self, "savetimeshiftandrecord", returnFunction)
		else:
			returnFunction(True)

	def checkTimeshiftRunningCallback(self, returnFunction, answer):
		match answer:
			case "savetimeshift" | "savetimeshiftandrecord":
				self.save_current_timeshift = True
			case "noSave":
				self.save_current_timeshift = False
			case "no":  # This is not really needed because the default os "no".
				pass
			case _:  # The user pressed cancel so assume they meant "no". That's probably not always correct, but it seems reasonable.
				answer = "no"
		InfoBarTimeshift.saveTimeshiftActions(self, answer, returnFunction)

	def eraseTimeshiftFile(self):
		for filename in listdir(config.timeshift.path.value):
			if filename.startswith("timeshift.") and not filename.endswith(".del") and not filename.endswith(".copy"):
				self.BgFileEraser.erase(join(config.timeshift.path.value, filename))

	def autostartPermanentTimeshift(self):
		ts = self.getTimeshift()
		if ts is None:
			print("[Timeshift] Error: Tune lock failed, could not start time shift!")
			return 0
		if self.pts_delay_timer.isActive():
			self.pts_delay_timer.stop()
		if (config.timeshift.startDelay.value and not self.timeshiftEnabled()) or self.event_changed:
			self.activatePermanentTimeshift()

	def activatePermanentTimeshift(self):
		self.createTimeshiftFolder()
		if self.pts_eventcount == 0:  # Only cleanup folder after switching channels, not when a new event starts, to allow saving old events from time shift buffer.
			self.ptsCleanTimeshiftFolder(justZapped=True)  # Remove all time shift files.
		else:
			self.ptsCleanTimeshiftFolder(justZapped=False)  # Only delete very old time shift files based on config.timeshift.maxHours.
		if self.ptsCheckTimeshiftPath() is False or self.session.screen["Standby"].boolean is True or self.ptsLiveTVStatus() is False or (config.timeshift.stopWhileRecording.value and self.pts_record_running):
			return
		# (Re)start time shift now.
		if config.timeshift.fileSplitting.value:
			# setNextPlaybackFile() on event change while time shifting.
			if self.isSeekable():
				self.pts_nextplaying = self.pts_currplaying + 1
				self.ptsSetNextPlaybackFile(f"pts_livebuffer_{self.pts_nextplaying}")
				self.switchToLive = False  # Do not switch back to live TV while time shifting.
			else:
				self.switchToLive = True
			self.stopTimeshiftcheckTimeshiftRunningCallback(True)
		else:
			if self.pts_currplaying < self.pts_eventcount:
				self.pts_nextplaying = self.pts_currplaying + 1
				self.ptsSetNextPlaybackFile(f"pts_livebuffer_{self.pts_nextplaying}")
			else:
				self.pts_nextplaying = 0
				self.ptsSetNextPlaybackFile("")
		self.event_changed = False
		ts = self.getTimeshift()
		if ts and (not ts.startTimeshift() or self.pts_eventcount == 0):
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
			self.ptsCreateHardlink()
			self.__seekableStatusChanged()
			self.ptsEventCleanTimerSTART()
		elif ts and ts.startTimeshift():
			self.ptsGetEventInfo()
			try:
				with open(join(config.timeshift.path.value, f"pts_livebuffer_{self.pts_eventcount}.meta", "w")) as metafile:  # Rewrite META and EIT files.
					metafile.write(f"{self.pts_curevent_servicerefname}\n{self.currentEventName}\n{self.currentEventDescription}\n{int(self.pts_starttime)}\n")
				self.ptsCreateEITFile(join(config.timeshift.path.value, f"pts_livebuffer_{self.pts_eventcount}"))
			except OSError as err:
				print(f"[Timeshift] Error {err.errno}: Failed to rewrite META and/or EIT file!  ({err.strerror})")
			self.ptsEventCleanTimerSTART()
		else:
			self.ptsEventCleanTimerSTOP()
			try:
				self.session.open(MessageBox, _("Time shift not possible!"), MessageBox.TYPE_ERROR, timeout=2)
			except Exception:
				print("[Timeshift] Failed to open MessageBox, time shift not possible, probably another MessageBox was active.")
		if self.pts_eventcount < self.pts_firstplayable:
			self.pts_firstplayable = self.pts_eventcount

	def createTimeshiftFolder(self):
		timeshiftdir = resolveFilename(SCOPE_TIMESHIFT)
		if not exists(timeshiftdir):
			try:
				makedirs(timeshiftdir)
			except OSError as err:
				print(f"[Timeshift] Error {err.errno}: Failed to create '{timeshiftdir}'!  ({err.strerror})")

	def restartTimeshift(self):
		self.activatePermanentTimeshift()
		AddNotification(MessageBox, _("[Timeshift] Restarting time shift!"), MessageBox.TYPE_INFO, timeout=5)

	def saveTimeshiftEventPopup(self):
		self.saveTimeshiftEventPopupActive = True
		filecount = 0
		entrylist = [(f"{_("Current Event:")} {self.pts_curevent_name}", "savetimeshift")]
		filelist = listdir(config.timeshift.path.value)
		if filelist is not None:
			try:
				filelist = sorted(filelist, key=lambda x: int(x.split("pts_livebuffer_")[1]) if x.startswith("pts_livebuffer") and not splitext(x)[1] else x)
			except Exception:
				print("[Timeshift] Error: File sorting error, using standard sorting method!")
				filelist.sort()
			for filename in filelist:
				if filename.startswith("pts_livebuffer") and not splitext(filename)[1]:
					statinfo = stat(join(config.timeshift.path.value, filename))
					if statinfo.st_mtime < (time() - 5.0):
						with open(f"{config.timeshift.path.value}{filename}.meta") as readmetafile:  # Get event information from META file.
							servicerefname = readmetafile.readline()[0:-1]
							eventname = readmetafile.readline()[0:-1]
							description = readmetafile.readline()[0:-1]  # noqa F841
							begintime = readmetafile.readline()[0:-1]
						filecount += 1  # Add event to list.
						if config.timeshift.deleteAfterZap.value and servicerefname == self.pts_curevent_servicerefname:
							entrylist.append((f"{_("Record")} #{filecount} ({strftime('%H:%M', localtime(int(begintime)))}): {eventname}", filename))
						else:
							servicename = ServiceReference(servicerefname).getServiceName()
							entrylist.append((f"[{strftime("%H:%M", localtime(int(begintime)))}] {servicename} : {eventname}", filename))
			self.session.openWithCallback(self.recordQuestionCallback, ChoiceBox, title=_("Which time shift buffer event do you want to save?"), list=entrylist)

	def saveTimeshiftActions(self, action=None, returnFunction=None):
		timeshiftfile = None
		if self.pts_currplaying != self.pts_eventcount:
			timeshiftfile = f"pts_livebuffer_{self.pts_currplaying}"
		if action == "savetimeshift":
			self.SaveTimeshift(timeshiftfile)
		elif action == "savetimeshiftandrecord":
			if self.pts_curevent_end > time() and timeshiftfile is None:
				self.SaveTimeshift(mergelater=True)
				self.ptsRecordCurrentEvent()
			else:
				self.SaveTimeshift(timeshiftfile)
		elif action == "noSave":
			config.timeshift.isRecording.value = False
			self.save_current_timeshift = False
		elif action == "no":
			pass
		if returnFunction is not None and action != "no":  # Get rid of old time shift file before E2 truncates its filesize.
			self.eraseTimeshiftFile()
		returnFunction(action and action != "no")

	def SaveTimeshift(self, timeshiftfile=None, mergelater=False):
		recordingPath = preferredTimeShiftRecordingPath()
		self.save_current_timeshift = False
		savefilename = None
		if timeshiftfile is not None:
			savefilename = timeshiftfile
		if savefilename is None:
			for filename in listdir(config.timeshift.path.value):
				if filename.startswith("timeshift.") and not filename.endswith(".del") and not filename.endswith(".copy") and not filename.endswith(".sc"):
					statinfo = stat(join(config.timeshift.path.value, filename))
					if statinfo.st_mtime > (time() - 5.0):
						savefilename = filename
		if savefilename is None:
			AddNotification(MessageBox, _("No time shift buffer found to save as recording!"), MessageBox.TYPE_ERROR, timeout=30)
		else:
			timeshift_saved = True
			timeshift_saveerror1 = ""
			timeshift_saveerror2 = ""
			metamergestring = ""
			config.timeshift.isRecording.value = True
			if mergelater:
				self.pts_mergeRecords_timer.start(120000, True)
				metamergestring = "pts_merge\n"
			try:
				if timeshiftfile is None:
					if self.pts_starttime >= (time() - 60):  # Save current event by creating hard link to its ts file.
						self.pts_starttime -= 60
					eventstarttime = strftime("%Y%m%d %H%M", localtime(self.pts_starttime))
					ptsfilename = f"{eventstarttime} - {self.pts_curevent_station} - {self.currentEventName}"
					try:
						if config.usage.setup_level.index >= 2:
							if config.recording.filename_composition.value == "long" and self.currentEventName != self.currentEventDescription:
								ptsfilename = f"{eventstarttime} - {self.pts_curevent_station} - {self.currentEventName} - {self.currentEventDescription}"
							elif config.recording.filename_composition.value == "short":
								ptsfilename = f"{eventstarttime} - {self.currentEventName}"
							elif config.recording.filename_composition.value == "veryshort":
								ptsfilename = f"{self.currentEventName} - {eventstarttime}"
							elif config.recording.filename_composition.value == "veryveryshort":
								ptsfilename = f"{self.currentEventName} - {eventstarttime}"
					except Exception:
						print("[Timeshift] Using default filename.")
					if config.recording.ascii_filenames.value:
						ptsfilename = legacyEncode(ptsfilename)
					fullname = getRecordingFilename(ptsfilename, recordingPath)
					link(join(config.timeshift.path.value, savefilename), f"{fullname}.ts")
					with open(f"{fullname}.ts.meta", "w") as metafile:
						metafile.write(f"{self.pts_curevent_servicerefname}\n{self.getCurrentEventName}\n{self.currentEventDescription}\n{int(self.pts_starttime)}\n{metamergestring}")
					self.ptsCreateEITFile(fullname)
				elif timeshiftfile.startswith("pts_livebuffer"):
					with open(join(config.timeshift.path.value, f"{timeshiftfile}.meta")) as readmetafile:  # Save stored time shift buffer by creating hard link to ts file.
						servicerefname = readmetafile.readline()[0:-1]
						eventname = readmetafile.readline()[0:-1]
						description = readmetafile.readline()[0:-1]
						begintime = readmetafile.readline()[0:-1]
					if config.timeshift.deleteAfterZap.value and servicerefname == self.pts_curevent_servicerefname:
						servicename = self.pts_curevent_station
					else:
						servicename = ServiceReference(servicerefname).getServiceName()
					ptsfilename = f"{strftime("%Y%m%d %H%M", localtime(int(begintime)))} - {servicename} - {eventname}"
					try:
						if config.usage.setup_level.index >= 2:
							if config.recording.filename_composition.value == "long" and eventname != description:
								ptsfilename = f"{strftime("%Y%m%d %H%M", localtime(int(begintime)))} - {servicename} - {eventname} - {description}"
							elif config.recording.filename_composition.value == "short":
								ptsfilename = f"{strftime("%Y%m%d", localtime(int(begintime)))} - {eventname}"
							elif config.recording.filename_composition.value == "veryshort":
								ptsfilename = f"{eventname} - {strftime("%Y%m%d %H%M", localtime(int(begintime)))}"
							elif config.recording.filename_composition.value == "veryveryshort":
								ptsfilename = f"{eventname} - {strftime("%Y%m%d %H%M", localtime(int(begintime)))}"
					except Exception:
						print("[Timeshift] Using default filename.")
					if config.recording.ascii_filenames.value:
						ptsfilename = legacyEncode(ptsfilename)
					fullname = getRecordingFilename(ptsfilename, recordingPath)
					link(join(config.timeshift.path.value, timeshiftfile), f"{fullname}.ts")
					link(join(config.timeshift.path.value, f"{timeshiftfile}.meta"), f"{fullname}.ts.meta")
					if exists(join(config.timeshift.path.value, f"{timeshiftfile}.eit")):
						link(join(config.timeshift.path.value, f"{timeshiftfile}.eit"), f"{fullname}.eit")
					if mergelater:  # Add merge tag to META file.
						with open(f"{fullname}.ts.meta", "a") as metafile:
							metafile.write(f"{metamergestring}\n")
				if not mergelater:  # Create AP and SC Files when not merging.
					self.ptsCreateAPSCFiles(f"{fullname}.ts")
			except Exception as err:
				timeshift_saved = False
				timeshift_saveerror1 = str(err)
			# Hmpppf! Saving time shift buffer via hard link method failed. Probably another device?
			# Let's try to copy the file in background now! This might take a while.
			if not timeshift_saved:
				try:
					status = statvfs(recordingPath)
					freespace = status.f_bfree / 1000 * status.f_bsize / 1000
					randomint = randint(1, 999)
					if timeshiftfile is None:

						filesize = int(getsize(join(config.timeshift.path.value, savefilename)) / (1024 * 1024))  # Get file size for free space check.
						if filesize <= freespace:  # Save current event by copying it to the other device.
							link(join(config.timeshift.path.value, savefilename), join(config.timeshift.path.value, f"{savefilename}.{randomint}.copy"))
							copy_file = savefilename
							with open(f"{fullname}.ts.meta", "w") as metafile:
								metafile.write(f"{self.pts_curevent_servicerefname}\n{self.currentEventName}\n{self.currentEventDescription}\n{int(self.pts_starttime)}\n{metamergestring}")
							self.ptsCreateEITFile(fullname)
					elif timeshiftfile.startswith("pts_livebuffer"):
						filesize = int(getsize(f"{config.timeshift.path.value}{timeshiftfile}") / (1024 * 1024))  # Get file size for free space check.
						if filesize <= freespace:  # Save stored time shift buffer by copying it to the other device.
							link(join(config.timeshift.path.value, timeshiftfile), join(config.timeshift.path.value, f"{timeshiftfile}.{randomint}.copy"))
							copyfile(join(config.timeshift.path.value, f"{timeshiftfile}.meta"), f"{fullname}.ts.meta")
							if exists(join(config.timeshift.path.value, f"{timeshiftfile}.eit")):
								copyfile(join(config.timeshift.path.value, f"{timeshiftfile}.eit"), f"{fullname}.eit")
							copy_file = timeshiftfile
						if mergelater:  # Add merge tag to META file.
							with open(f"{fullname}.ts.meta", "a") as metafile:
								metafile.write(f"{metamergestring}\n")
					if filesize <= freespace:  # Only copy file when enough disk space is available.
						timeshift_saved = True
						copy_file = f"{copy_file}.{randomint}"
						if exists(f"{fullname}.ts.meta"):  # Get event information from META file.
							with open(f"{fullname}.ts.meta") as readmetafile:
								servicerefname = readmetafile.readline()[0:-1]
								eventname = readmetafile.readline()[0:-1]
						else:
							eventname = ""
						JobManager.AddJob(CopyTimeshiftJob(self, f"mv \"{join(config.timeshift.path.value, {copy_file}.copy)}\" \"{fullname}.ts\"", copy_file, fullname, eventname))
						if not Screens.Standby.inTryQuitMainloop and not Screens.Standby.inStandby and not mergelater and self.save_timeshift_postaction != "standby":
							AddNotification(MessageBox, _("Saving time shift buffer, this might take a while."), MessageBox.TYPE_INFO, timeout=30)
					else:
						timeshift_saved = False
						timeshift_saveerror1 = ""
						timeshift_saveerror2 = _("Not enough free disk space!\n\nFilesize: %sMB\nFree Space: %sMB\nPath: %s" % (filesize, freespace, recordingPath))
				except Exception as err:
					timeshift_saved = False
					timeshift_saveerror2 = str(err)
			if not timeshift_saved:
				config.timeshift.isRecording.value = False
				self.save_timeshift_postaction = None
				errormessage = f"{timeshift_saveerror1}\n{timeshift_saveerror2}"
				AddNotification(MessageBox, f"{_("Time shift save failed!")}\n\n{errormessage}", MessageBox.TYPE_ERROR, timeout=30)

	def ptsAskUser(self, what):
		if self.ptsAskUser_wait:
			return
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
		if what == "time":
			message = message_time
			choice = choice_restart
		elif what == "space":
			message = message_space
			choice = choice_restart
		elif what == "time_and_save":
			message = message_time
			choice = choice_save
		elif what == "space_and_save":
			message = message_space
			choice = choice_save
		elif what == "livetv":
			message = message_livetv
			choice = choice_livetv
		elif what == "nextfile":
			message = message_nextfile
			choice = choice_livetv
		else:
			return
		self.ptsAskUser_wait = True
		self.session.openWithCallback(self.ptsAskUserCallback, MessageBox, message, simple=True, list=choice, timeout=30)

	def ptsAskUserCallback(self, answer):
		self.ptsAskUser_wait = False
		if answer:
			if answer == "restarttimeshift":
				self.ptsEventCleanTimerSTOP()
				self.save_current_timeshift = False
				self.stopTimeshiftAskUserCallback(True)
				self.restartTimeshift()
			elif answer == "noSave":
				self.ptsEventCleanTimerSTOP()
				self.save_current_timeshift = False
				self.stopTimeshiftAskUserCallback(True)
			elif answer == "savetimeshift" or answer == "savetimeshiftandrecord":
				self.ptsEventCleanTimerSTOP()
				self.save_current_timeshift = True
				InfoBarTimeshift.saveTimeshiftActions(self, answer, self.stopTimeshiftAskUserCallback)
			elif answer == "golivetv":
				self.ptsEventCleanTimerSTOP(True)
				self.stopTimeshiftAskUserCallback(True)
				self.restartTimeshift()
			elif answer == "nolivetv":
				if self.pts_lastposition:
					self.setSeekState(self.SEEK_STATE_PLAY)
					self.doSeek(self.pts_lastposition)

	def stopTimeshiftAskUserCallback(self, answer):
		ts = self.getTimeshift()
		if answer and ts:
			ts.stopTimeshift(True)
			self.__seekableStatusChanged()

	def ptsEventCleanTimerSTOP(self, justStop=False):
		if justStop is False:
			self.pts_eventcount = 0
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
		if self.ptsCheckTimeshiftPath() is False or self.session.screen["Standby"].boolean is True:
			self.ptsEventCleanTimerSTOP()
			return
		freespace = config.timeshift.checkFreeSpace.value
		timeshiftEnabled = self.timeshiftEnabled()
		isSeekable = self.isSeekable()
		filecounter = 0
		filesize = 0
		lockedFiles = []
		removeFiles = []
		if timeshiftEnabled:
			if isSeekable:
				for index in range(self.pts_currplaying, self.pts_eventcount + 1):
					lockedFiles.append(f"pts_livebuffer_{index}")
			else:
				if not self.event_changed:
					lockedFiles.append(f"pts_livebuffer_{self.pts_currplaying}")
		if freespace:
			try:
				status = statvfs(config.timeshift.path.value)
				freespace = status.f_bavail * status.f_bsize // 1024 // 1024
			except Exception as err:
				print(f"[Timeshift] Error {err.errno}: Unable to evaluate disk free space with 'statvfs' call!  ({err.strerror})")
		if freespace < config.timeshift.checkFreeSpace.value:
			for index in range(1, self.pts_eventcount + 1):
				removeFiles.append(f"pts_livebuffer_{index}")
			print(f"[Timeshift] Less than {config.timeshift.checkFreeSpace.value}MB disk space available. Try deleting all unused time shift files.")
		elif self.pts_eventcount - config.timeshift.maxEvents.value >= 0:
			offset = 2 if self.event_changed or len(lockedFiles) == 0 else 1
			for index in range(1, self.pts_eventcount - config.timeshift.maxEvents.value + offset):
				removeFiles.append(f"pts_livebuffer_{index}")
		for filename in listdir(config.timeshift.path.value):
			if exists(join(config.timeshift.path.value, filename)) and filename.startswith(("timeshift.", "pts_livebuffer_")):
				try:
					statinfo = stat(join(config.timeshift.path.value, filename))
				except OSError:
					statinfo = None  # A .del file may have been deleted between "exists" and "stat".
				if justZapped and not filename.endswith(".del") and not filename.endswith(".copy"):
					filesize += getsize(join(config.timeshift.path.value, filename))  # After zapping, remove all regular time shift files.
					self.BgFileEraser.erase(join(config.timeshift.path.value, filename))
				elif statinfo and not filename.endswith((".eit", ".meta", ".sc", ".del", ".copy")):
					# Remove old files, but only complete sets of files (base file, EIT, META, SC),
					# and not while saveTimeshiftEventPopup is active (avoid deleting files about to be saved)
					# and don't delete files from currently playing up to the last event.
					if not filename.startswith("timeshift."):
						filecounter += 1
					if ((statinfo.st_mtime < (time() - 3600 * config.timeshift.maxHours.value)) or any(filename in x for x in removeFiles)) and (self.saveTimeshiftEventPopupActive is False) and not any(filename in x for x in lockedFiles):
						# print(f"[Timeshift] Erasing set of old time shift files (base file, EIT, META, SC) '{filename}'.")
						filesize += getsize(join(config.timeshift.path.value, filename))
						self.BgFileEraser.erase(join(config.timeshift.path.value, filename))
						path = join(config.timeshift.path.value, f"{filename}.eit")
						if exists(path):
							filesize += getsize(path)
							self.BgFileEraser.erase(path)
						path = join(config.timeshift.path.value, f"{filename}.meta")
						if exists(path):
							filesize += getsize(path)
							self.BgFileEraser.erase(path)
						path = join(config.timeshift.path.value, f"{filename}.sc")
						if exists(path):
							filesize += getsize(path)
							self.BgFileEraser.erase(path)
						if not filename.startswith("timeshift."):
							filecounter -= 1
				elif statinfo:
					if statinfo.st_mtime < (time() - 3600 * (24 + config.timeshift.maxHours.value)):  # Remove anything left over 24 hours later.
						# print(f"[Timeshift] Erasing very old time shift file '{filename}'.")
						path = join(config.timeshift.path.value, filename)
						if filename.endswith(".del") is True:
							filesize += getsize(path)
							try:
								newPath = join(config.timeshift.path.value, f"{filename}.del_again")
								rename(path, newPath)
								self.BgFileEraser.erase(newPath)
							except Exception as err:
								print(f"[Timeshift] Error {err.errno}: Can't rename '{path}'!  ({err.strerror})")
								self.BgFileEraser.erase(path)
						else:
							filesize += getsize(path)
							self.BgFileEraser.erase(path)
		if filecounter == 0:
			self.ptsEventCleanTimerSTOP()
		else:
			if timeshiftEnabled and not isSeekable:
				if freespace + (filesize // 1024 // 1024) < config.timeshift.checkFreeSpace.value:
					self.ptsAskUser("space")
				elif time() - self.pts_starttime > 3600 * config.timeshift.maxHours.value:
					self.ptsAskUser("time")
			elif isSeekable:
				if freespace + (filesize // 1024 // 1024) < config.timeshift.checkFreeSpace.value:
					self.ptsAskUser("space_and_save")
				elif time() - self.pts_starttime > 3600 * config.timeshift.maxHours.value:
					self.ptsAskUser("time_and_save")
			if self.checkEvents_value != config.timeshift.checkEvents.value:
				if self.pts_cleanEvent_timer.isActive():
					# print("[Timeshift] Clean event timer changed.")
					self.pts_cleanEvent_timer.stop()
					if config.timeshift.checkEvents.value:
						self.ptsEventCleanTimerSTART()
					else:
						print("[Timeshift] Clean event timer deactivated.")
		self.checkEvents_value = config.timeshift.checkEvents.value

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

	def ptsCreateHardlink(self):
		for filename in listdir(config.timeshift.path.value):
			if filename.startswith("timeshift.") and not filename.endswith((".sc", ".del", ".copy", ".ap")):
				path = join(config.timeshift.path.value, f"pts_livebuffer_{self.pts_eventcount}.eit")
				if exists(path):
					self.BgFileEraser.erase(path)
				path = join(config.timeshift.path.value, f"pts_livebuffer_{self.pts_eventcount}.meta")
				if exists(path):
					self.BgFileEraser.erase(path)
				path = join(config.timeshift.path.value, f"pts_livebuffer_{self.pts_eventcount}")
				if exists(path):
					self.BgFileEraser.erase(path)
				path = join(config.timeshift.path.value, f"pts_livebuffer_{self.pts_eventcount}.sc")
				if exists(path):
					self.BgFileEraser.erase(path)
				try:
					link(join(config.timeshift.path.value, filename), join(config.timeshift.path.value, f"pts_livebuffer_{self.pts_eventcount}"))  # Create link to pts_livebuffer file.
					link(join(config.timeshift.path.value, f"{filename}.sc"), join(config.timeshift.path.value, f"pts_livebuffer_{self.pts_eventcount}.sc"))
					with open(f"{config.timeshift.path.value}pts_livebuffer_{self.pts_eventcount}.meta", "w") as metafile:  # Create a META file.
						metafile.write(f"{self.pts_curevent_servicerefname}\n{self.currentEventName}\n{self.currentEventDescription}\n{int(self.pts_starttime)}\n")
				except Exception as errormsg:
					AddNotification(MessageBox, _("Creating hard link to time shift file failed!") + "\n" + _("The file system on your time shift device does not support hard links.\nMake sure it is formatted in EXT2, EXT3 or EXT4!") + f"\n\n{errormsg}", MessageBox.TYPE_ERROR, timeout=30)
				self.ptsCreateEITFile(f"{config.timeshift.path.value}pts_livebuffer_{self.pts_eventcount}")  # Create EIT file.

				if config.timeshift.autorecord.value:  # Autorecord
					try:
						fullname = getRecordingFilename(f"{strftime('%Y%m%d %H%M', localtime(self.pts_starttime))} - {self.pts_curevent_station} - {self.pts_curevent_name}", preferredTimeShiftRecordingPath())
						link(join(config.timeshift.path.value, filename), f"{fullname}.ts")
						with open(f"{fullname}.ts.meta", "w") as metafile:  # Create a META file.
							metafile.write(f"{self.pts_curevent_servicerefname}\n{self.currentEventName}\n{self.currentEventDescription}\n{int(self.pts_starttime)}\nautosaved\n")
					except Exception as errormsg:
						print(f"[Timeshift] autorecord Error: '{errormsg}'")

	def ptsRecordCurrentEvent(self):
		recording = RecordTimerEntry(ServiceReference(self.session.nav.getCurrentlyPlayingServiceOrGroup()), time(), self.pts_curevent_end, self.pts_curevent_name, self.pts_curevent_description, self.pts_curevent_eventid, afterEvent=AFTEREVENT.AUTO, justplay=False, always_zap=False, dirname=preferredTimeShiftRecordingPath())
		recording.dontSave = True
		self.session.nav.RecordTimer.record(recording)
		self.recording.append(recording)

	def ptsMergeRecords(self):
		if self.session.nav.RecordTimer.isRecording():
			self.pts_mergeRecords_timer.start(120000, True)
			return
		recordingPath = preferredTimeShiftRecordingPath()
		ptsmergeSRC = ""
		ptsmergeDEST = ""
		ptsmergeeventname = ""
		ptsgetnextfile = False
		ptsfilemerged = False
		filelist = listdir(recordingPath)
		if filelist is not None:
			filelist.sort()
		for filename in filelist:
			if filename.endswith(".meta"):
				with open(f"{recordingPath}{filename}") as readmetafile:  # Get event information from META file.
					servicerefname = readmetafile.readline()[0:-1]
					eventname = readmetafile.readline()[0:-1]
					eventtitle = readmetafile.readline()[0:-1]
					eventtime = readmetafile.readline()[0:-1]
					eventtag = readmetafile.readline()[0:-1]
				if ptsgetnextfile:
					ptsgetnextfile = False
					ptsmergeSRC = filename[0:-5]
					if legacyEncode(eventname) == legacyEncode(ptsmergeeventname):
						path = join(recordingPath, f"{ptsmergeSRC[0:-3]}.eit")
						if fileExists(path):  # Copy EIT file.
							copyfile(path, join(recordingPath, f"{ptsmergeDEST[0:-3]}.eit"))
						path = join(recordingPath, f"{ptsmergeDEST}.ap")
						if exists(path):  # Delete AP and SC files.
							self.BgFileEraser.erase(path)
						path = join(recordingPath, f"{ptsmergeDEST}.sc")
						if exists(path):
							self.BgFileEraser.erase(path)
						JobManager.AddJob(MergeTimeshiftJob(self, f"cat \"{join(recordingPath, ptsmergeSRC)}\" >> \"{join(recordingPath, ptsmergeDEST)}\"", ptsmergeSRC, ptsmergeDEST, eventname))  # Add merge job to JobManager.
						config.timeshift.isRecording.value = True
						ptsfilemerged = True
					else:
						ptsgetnextfile = True
				if eventtag == "pts_merge" and not ptsgetnextfile:
					ptsgetnextfile = True
					ptsmergeDEST = filename[0:-5]
					ptsmergeeventname = eventname
					ptsfilemerged = False
					path = join(recordingPath, ptsmergeDEST)  # If still recording or transfering, try again later.
					if fileExists(path):
						statinfo = stat(path)
						if statinfo.st_mtime > (time() - 10.0):
							self.pts_mergeRecords_timer.start(120000, True)
							return
					with open(f"{path}.meta", "w") as metafile:  # Rewrite META file to get rid of pts_merge tag.
						metafile.write(f"{servicerefname}\n{eventname.replace("\n", "")}\n{eventtitle.replace("\n", "")}\n{int(eventtime)}\n")
		if not ptsfilemerged and ptsgetnextfile:  # Merging failed! :(
			AddNotification(MessageBox, _("[Timeshift] Merging records failed!"), MessageBox.TYPE_ERROR, timeout=30)

	def ptsCreateAPSCFiles(self, filename):
		if fileExists(filename, "r"):
			if fileExists(f"{filename}.meta", "r"):
				with open(f"{filename}.meta") as readmetafile:  # Get event information from META file.
					servicerefname = readmetafile.readline()[0:-1]  # noqa F841
					eventname = readmetafile.readline()[0:-1]
			else:
				eventname = ""
			JobManager.AddJob(CreateAPSCFilesJob(self, f"/usr/lib/enigma2/python/Components/createapscfiles \"{filename}\" > /dev/null", eventname))
		else:
			self.ptsSaveTimeshiftFinished()

	def ptsCreateEITFile(self, filename):
		if self.pts_curevent_eventid is not None:
			try:
				serviceref = ServiceReference(self.session.nav.getCurrentlyPlayingServiceOrGroup()).ref
				eEPGCache.getInstance().saveEventToFile(f"{filename}.eit", serviceref, self.pts_curevent_eventid, -1, -1)
			except Exception as err:
				print(f"[Timeshift] Error: {str(err)}")

	def ptsCopyFilefinished(self, srcfile, destfile):
		if fileExists(srcfile):  # Erase source file.
			self.BgFileEraser.erase(srcfile)
		if self.pts_mergeRecords_timer.isActive():  # Restart merge timer.
			self.pts_mergeRecords_timer.stop()
			self.pts_mergeRecords_timer.start(15000, True)
		else:
			self.ptsCreateAPSCFiles(destfile)  # Create AP and SC files.

	def ptsMergeFilefinished(self, srcfile, destfile):
		if self.session.nav.RecordTimer.isRecording() or len(JobManager.getPendingJobs()) >= 1:
			self.pts_mergeCleanUp_timer.start(120000, True)  # Rename files and delete them later.
			system(f"echo \"\" > \"{srcfile[0:-3]}.pts.del\"")
		else:
			self.BgFileEraser.erase(srcfile)  # Delete instant recordings permanently now. R.I.P.
			self.BgFileEraser.erase(f"{srcfile}.ap")
			self.BgFileEraser.erase(f"{srcfile}.sc")
			self.BgFileEraser.erase(f"{srcfile}.meta")
			self.BgFileEraser.erase(f"{srcfile}.cuts")
			self.BgFileEraser.erase(f"{srcfile[0:-3]}.eit")
		self.ptsCreateAPSCFiles(destfile)  # Create AP and SC files.
		self.pts_mergeRecords_timer.start(10000, True)  # Run merge process one more time to check if there are more recordings to merge.

	def ptsSaveTimeshiftFinished(self):
		if not self.pts_mergeCleanUp_timer.isActive():
			self.ptsFrontpanelActions("stop")
			config.timeshift.isRecording.value = False
		if Screens.Standby.inTryQuitMainloop:
			self.pts_QuitMainloop_timer.start(30000, True)
		else:
			AddNotification(MessageBox, _("Time shift saved to your hard disk drive!"), MessageBox.TYPE_INFO, timeout=30)

	def ptsMergePostCleanUp(self):
		if self.session.nav.RecordTimer.isRecording() or len(JobManager.getPendingJobs()) >= 1:
			config.timeshift.isRecording.value = True
			self.pts_mergeCleanUp_timer.start(120000, True)
			return
		recordingPath = preferredTimeShiftRecordingPath()
		self.ptsFrontpanelActions("stop")
		config.timeshift.isRecording.value = False
		filelist = listdir(recordingPath)
		for filename in filelist:
			if filename.endswith(".pts.del"):
				srcfile = join(recordingPath, f"{filename[0:-8]}.ts")
				self.BgFileEraser.erase(srcfile)
				self.BgFileEraser.erase(f"{srcfile}.ap")
				self.BgFileEraser.erase(f"{srcfile}.sc")
				self.BgFileEraser.erase(f"{srcfile}.meta")
				self.BgFileEraser.erase(f"{srcfile}.cuts")
				self.BgFileEraser.erase(f"{srcfile[0:-3]}.eit")
				self.BgFileEraser.erase(f"{srcfile[0:-3]}.pts.del")
				if Screens.Standby.inTryQuitMainloop and self.pts_QuitMainloop_timer.isActive():  # Restart QuitMainloop timer to give BgFileEraser enough time.
					self.pts_QuitMainloop_timer.start(60000, True)

	def ptsTryQuitMainloop(self):
		if Screens.Standby.inTryQuitMainloop and (len(JobManager.getPendingJobs()) >= 1 or self.pts_mergeCleanUp_timer.isActive()):
			self.pts_QuitMainloop_timer.start(60000, True)
			return
		if Screens.Standby.inTryQuitMainloop and self.session.ptsmainloopvalue:
			self.session.dialog_stack = []
			self.session.summary_stack = [None]
			self.session.open(Screens.Standby.TryQuitMainloop, self.session.ptsmainloopvalue)

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
				AddNotification(MessageBox, _("Can't play the previous time shift file! You can try again."), MessageBox.TYPE_INFO, timeout=3)
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
			if fileExists(join(config.timeshift.path.value, f"pts_livebuffer_{self.pts_nextplaying}"), "r"):  # Get next PTS file.
				self.ptsSetNextPlaybackFile(f"pts_livebuffer_{self.pts_nextplaying}")
				self.pts_switchtolive = False
			else:
				self.ptsSetNextPlaybackFile("")
				self.pts_switchtolive = True

	def ptsSetNextPlaybackFile(self, nexttsfile):
		ts = self.getTimeshift()
		if ts:
			ts.setNextPlaybackFile(join(config.timeshift.path.value, nexttsfile) if nexttsfile else "")

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

	def ptsCheckTimeshiftPath(self):
		if fileExists(config.timeshift.path.value, "w"):
			return True
		else:
			# AddNotification(MessageBox, _("Could not activate Permanent-Timeshift!\nTimeshift-Path does not exist"), MessageBox.TYPE_ERROR, timeout=15)
			if self.pts_delay_timer.isActive():
				self.pts_delay_timer.stop()
			if self.pts_cleanUp_timer.isActive():
				self.pts_cleanUp_timer.stop()
			return False

	def ptsTimerEntryStateChange(self, timer):
		if config.timeshift.stopWhileRecording.value:
			self.pts_record_running = self.session.nav.RecordTimer.isRecording()
			if not self.session.screen["Standby"].boolean:  # Abort here when box is in standby mode.
				if timer.state == TimerEntry.StateRunning and self.timeshiftEnabled() and self.pts_record_running:  # Stop time shift when recording started.
					if self.seekstate != self.SEEK_STATE_PLAY:
						self.setSeekState(self.SEEK_STATE_PLAY)
					if self.isSeekable():
						AddNotification(MessageBox, _("Recording started, stopping time shift now."), MessageBox.TYPE_INFO, timeout=30)
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
		self.setCmdline(cmdline)
		self.srcfile = join(config.timeshift.path.value, f"{srcfile}.copy")
		self.destfile = f"{destfile}.ts"
		self.ProgressTimer = eTimer()
		self.ProgressTimer.callback.append(self.ProgressUpdate)

	def ProgressUpdate(self):
		if self.srcsize > 0 and fileExists(self.destfile, "r"):
			self.setProgress(int((getsize(self.destfile) / float(self.srcsize)) * 100))
			self.ProgressTimer.start(15000, True)

	def prepare(self):
		if fileExists(self.srcfile, "r"):
			self.srcsize = getsize(self.srcfile)
			self.ProgressTimer.start(15000, True)
		self.toolbox.ptsFrontpanelActions("start")

	def afterRun(self):
		self.setProgress(100)
		self.ProgressTimer.stop()
		self.toolbox.ptsCopyFilefinished(self.srcfile, self.destfile)
		config.timeshift.isRecording.value = True


class MergeTimeshiftJob(Job):
	def __init__(self, toolbox, cmdline, srcfile, destfile, eventname):
		Job.__init__(self, _("Merging time shift files"))
		self.toolbox = toolbox
		AddMergeTimeshiftTask(self, cmdline, srcfile, destfile, eventname)


class AddMergeTimeshiftTask(Task):
	def __init__(self, job, cmdline, srcfile, destfile, eventname):
		Task.__init__(self, job, eventname)
		self.toolbox = job.toolbox
		self.setCmdline(cmdline)
		self.srcfile = join(preferredTimeShiftRecordingPath(), srcfile)
		self.destfile = join(preferredTimeShiftRecordingPath(), destfile)
		self.ProgressTimer = eTimer()
		self.ProgressTimer.callback.append(self.ProgressUpdate)

	def ProgressUpdate(self):
		if self.srcsize <= 0 or not fileExists(self.destfile, "r"):
			return
		self.setProgress(int((getsize(self.destfile) / float(self.srcsize)) * 100))
		self.ProgressTimer.start(7500, True)

	def prepare(self):
		if fileExists(self.srcfile, "r") and fileExists(self.destfile, "r"):
			self.srcsize = getsize(self.srcfile) + getsize(self.destfile)
			self.ProgressTimer.start(7500, True)
		self.toolbox.ptsFrontpanelActions("start")

	def afterRun(self):
		self.setProgress(100)
		self.ProgressTimer.stop()
		config.timeshift.isRecording.value = True
		self.toolbox.ptsMergeFilefinished(self.srcfile, self.destfile)


class CreateAPSCFilesJob(Job):
	def __init__(self, toolbox, cmdline, eventname):
		Job.__init__(self, _("Creating .ap and .sc files"))
		self.toolbox = toolbox
		CreateAPSCFilesTask(self, cmdline, eventname)


class CreateAPSCFilesTask(Task):
	def __init__(self, job, cmdline, eventname):
		Task.__init__(self, job, eventname)
		self.toolbox = job.toolbox
		self.setCmdline(cmdline)

	def prepare(self):
		self.toolbox.ptsFrontpanelActions("start")
		config.timeshift.isRecording.value = True

	def afterRun(self):
		self.setProgress(100)
		self.toolbox.ptsSaveTimeshiftFinished()
