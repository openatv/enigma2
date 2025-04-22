from os import link, listdir, makedirs, rename, stat, statvfs, system as ossystem
from os.path import exists, getsize, join as pathjoin, splitext
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
from Tools.Directories import SCOPE_TIMESHIFT, copyfile, fileExists, getRecordingFilename, resolveFilename
from Tools.Notifications import AddNotification


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
		# Init Global Variables
		self.session.ptsmainloopvalue = 0
		config.timeshift.isRecording.value = False
		# Init eBackgroundFileEraser
		self.BgFileEraser = eBackgroundFileEraser.getInstance()
		# Init PTS Delay-Timer
		self.pts_delay_timer = eTimer()
		self.pts_delay_timer.callback.append(self.autostartPermanentTimeshift)
		# Init PTS MergeRecords-Timer
		self.pts_mergeRecords_timer = eTimer()
		self.pts_mergeRecords_timer.callback.append(self.ptsMergeRecords)
		# Init PTS Merge Cleanup-Timer
		self.pts_mergeCleanUp_timer = eTimer()
		self.pts_mergeCleanUp_timer.callback.append(self.ptsMergePostCleanUp)
		# Init PTS QuitMainloop-Timer
		self.pts_QuitMainloop_timer = eTimer()
		self.pts_QuitMainloop_timer.callback.append(self.ptsTryQuitMainloop)
		# Init PTS CleanUp-Timer
		self.pts_cleanUp_timer = eTimer()
		self.pts_cleanUp_timer.callback.append(self.ptsCleanTimeshiftFolder)
		# Init PTS CleanEvent-Timer
		self.pts_cleanEvent_timer = eTimer()
		self.pts_cleanEvent_timer.callback.append(self.ptsEventCleanTimeshiftFolder)
		# Init PTS SeekBack-Timer
		self.pts_SeekBack_timer = eTimer()
		self.pts_SeekBack_timer.callback.append(self.ptsSeekBackTimer)
		self.pts_StartSeekBackTimer = eTimer()
		self.pts_StartSeekBackTimer.callback.append(self.ptsStartSeekBackTimer)
		# Init PTS SeekToPos-Timer
		self.pts_SeekToPos_timer = eTimer()
		self.pts_SeekToPos_timer.callback.append(self.ptsSeekToPos)
		# Init PTS CheckFileChanged-Timer
		self.pts_CheckFileChanged_counter = 1
		self.pts_CheckFileChanged_timer = eTimer()
		self.pts_CheckFileChanged_timer.callback.append(self.ptsCheckFileChanged)
		# Init Block-Zap Timer
		self.pts_blockZap_timer = eTimer()
		# Init PTS FileJump-Timer
		self.pts_FileJump_timer = eTimer()
		# Record Event Tracker
		self.session.nav.RecordTimer.on_state_change.append(self.ptsTimerEntryStateChange)
		# Keep Current Event Info for recordings
		self.pts_eventcount = 0
		self.pts_curevent_begin = int(time())
		self.pts_curevent_end = 0
		self.pts_curevent_name = _("Timeshift")
		self.pts_curevent_description = ""
		self.pts_curevent_servicerefname = ""
		self.pts_curevent_station = ""
		self.pts_curevent_eventid = None
		# Init PTS Infobar

	def __seekableStatusChanged(self):
		# print("[Timeshift] pts_currplaying %s, pts_nextplaying %s, pts_eventcount %s, pts_firstplayable %s." % (self.pts_currplaying, self.pts_nextplaying, self.pts_eventcount, self.pts_firstplayable))
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
			self.ptsSetNextPlaybackFile("pts_livebuffer_%s" % self.pts_eventcount)

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
				self.SaveTimeshift("pts_livebuffer_%s" % self.pts_eventcount, mergelater=True)
				self.ptsRecordCurrentEvent()
			else:
				self.SaveTimeshift("pts_livebuffer_%s" % self.pts_eventcount)
		self.service_changed = 0
		# if not config.timeshift.isRecording.value:
		# 	self.__seekableStatusChanged()
		self.__seekableStatusChanged()  # fix: enable ready to start for standard time shift after saving the event
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
		if not self.timeshiftEnabled() or self.pts_CheckFileChanged_timer.isActive() or self.pts_SeekBack_timer.isActive() or self.pts_StartSeekBackTimer.isActive() or self.pts_SeekToPos_timer.isActive():
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
		# Switch to previous TS file by seeking forward to next file.
		if fileExists("%spts_livebuffer_%s" % (config.timeshift.path.value, self.pts_currplaying), "r"):
			self.ptsSetNextPlaybackFile("pts_livebuffer_%s" % self.pts_currplaying)
			self.setSeekState(self.SEEK_STATE_PLAY)
			self.doSeek(3600 * 24 * 90000)
			self.pts_CheckFileChanged_counter = 1
			self.pts_CheckFileChanged_timer.start(1000, False)
			self.pts_file_changed = False
		else:
			print("[Timeshift] 'pts_livebuffer_%s' file was not found -> Put pointer to the first (current) 'pts_livebuffer_%s' file." % (self.pts_currplaying, self.pts_currplaying + 1))
			self.pts_currplaying += 1
			self.pts_firstplayable += 1
			self.setSeekState(self.SEEK_STATE_PLAY)
			self.doSeek(0)
			self.posDiff = 0

	def evEOF(self, posDiff=0):  # Called from InfoBarGenerics.py.
		self.posDiff = posDiff
		self.__evEOF()

	def __evEOF(self):
		if not self.timeshiftEnabled() or self.pts_CheckFileChanged_timer.isActive() or self.pts_SeekBack_timer.isActive() or self.pts_StartSeekBackTimer.isActive() or self.pts_SeekToPos_timer.isActive():
			return
		self.pts_switchtolive = False
		self.pts_lastposition = self.ptsGetPosition()
		self.pts_lastplaying = self.pts_currplaying
		self.pts_nextplaying = 0
		self.pts_currplaying += 1
		# Switch to next TS file by seeking forward to next file.
		if fileExists("%spts_livebuffer_%s" % (config.timeshift.path.value, self.pts_currplaying), "r"):
			self.ptsSetNextPlaybackFile("pts_livebuffer_%s" % self.pts_currplaying)
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
			# We zapped away before saving the file, save it now!
			if self.save_current_timeshift:
				self.SaveTimeshift("pts_livebuffer_%s" % self.pts_eventcount)
			# Delete time shift recordings on zap.
			if config.timeshift.deleteAfterZap.value:
				self.ptsEventCleanTimerSTOP()
			self.pts_firstplayable = self.pts_eventcount + 1
			if self.pts_eventcount == 0 and not config.timeshift.startDelay.value:
				self.pts_cleanUp_timer.start(1000, True)

	def __evEventInfoChanged(self):
		# Get Current Event Info
		service = self.session.nav.getCurrentService()
		old_begin_time = self.pts_begintime
		info = service and service.info()
		ptr = info and info.getEvent(0)
		self.pts_begintime = ptr and ptr.getBeginTime() or 0
		# Save current TimeShift permanently now.
		if info.getInfo(iServiceInformation.sVideoPID) != -1:
			# Take care of Record Margin Time.
			if self.save_current_timeshift and self.timeshiftEnabled():
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
			# (Re)Start TimeShift
			if not self.pts_delay_timer.isActive():
				if old_begin_time != self.pts_begintime or old_begin_time == 0:
					if config.timeshift.startDelay.value or self.timeshiftEnabled():
						self.event_changed = True
					self.pts_delay_timer.start(1000, True)

	def seekdef(self, key):
		if self.seekstate == self.SEEK_STATE_PLAY:
			return 0  # trade as unhandled action
		time = (-config.seek.selfdefined_13.value, False, config.seek.selfdefined_13.value,
			-config.seek.selfdefined_46.value, False, config.seek.selfdefined_46.value,
			-config.seek.selfdefined_79.value, False, config.seek.selfdefined_79.value)[key - 1]
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
			if config.timeshift.startDelay.value:
				ts.stopTimeshift(self.switchToLive)
			else:
				ts.stopTimeshift(not self.event_changed)
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
				seekable.seekTo(-90000)  # Seek approx. 1 sec before end.
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
					choice = [(_("Yes"), config.timeshift.favoriteSaveAction.value), (_("No"), "no")]
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
				self.BgFileEraser.erase("%s%s" % (config.timeshift.path.value, filename))

	def autostartPermanentTimeshift(self):
		ts = self.getTimeshift()
		if ts is None:
			print("[Timeshift] Tune lock failed, could not start time shift.")
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
				self.ptsSetNextPlaybackFile("pts_livebuffer_%s" % self.pts_nextplaying)
				# Do not switch back to LiveTV while time shifting.
				self.switchToLive = False
			else:
				self.switchToLive = True
			self.stopTimeshiftcheckTimeshiftRunningCallback(True)
		else:
			if self.pts_currplaying < self.pts_eventcount:
				self.pts_nextplaying = self.pts_currplaying + 1
				self.ptsSetNextPlaybackFile("pts_livebuffer_%s" % self.pts_nextplaying)
			else:
				self.pts_nextplaying = 0
				self.ptsSetNextPlaybackFile("")
		self.event_changed = False
		ts = self.getTimeshift()
		if ts and (not ts.startTimeshift() or self.pts_eventcount == 0):
			# Update internal Event Counter.
			self.pts_eventcount += 1
			if (BoxInfo.getItem("machinebuild") == "vuuno" or BoxInfo.getItem("machinebuild") == "vuduo") and exists("/proc/stb/lcd/symbol_timeshift"):
				if self.session.nav.RecordTimer.isRecording():
					f = open("/proc/stb/lcd/symbol_timeshift", "w")
					f.write("0")
					f.close()
			elif BoxInfo.getItem("model") == "u41" and exists("/proc/stb/lcd/symbol_record"):
				if self.session.nav.RecordTimer.isRecording():
					f = open("/proc/stb/lcd/symbol_record", "w")
					f.write("0")
					f.close()
			self.pts_starttime = time()
			self.save_timeshift_postaction = None
			self.ptsGetEventInfo()
			self.ptsCreateHardlink()
			self.__seekableStatusChanged()
			self.ptsEventCleanTimerSTART()
		elif ts and ts.startTimeshift():
			self.ptsGetEventInfo()
			try:
				# Rewrite .meta and .eit files.
				metafile = open("%spts_livebuffer_%s.meta" % (config.timeshift.path.value, self.pts_eventcount), "w")
				metafile.write("%s\n%s\n%s\n%i\n" % (self.pts_curevent_servicerefname, self.pts_curevent_name.replace("\n", ""), self.pts_curevent_description.replace("\n", ""), int(self.pts_starttime)))
				metafile.close()
				self.ptsCreateEITFile("%spts_livebuffer_%s" % (config.timeshift.path.value, self.pts_eventcount))
			except Exception:
				print("[Timeshift] Failed to rewrite meta and eit files.")
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
				print("[Timeshift] Error %d: Failed to create '%s'!  (%s)" % (err.errno, timeshiftdir, err.strerror))

	def restartTimeshift(self):
		self.activatePermanentTimeshift()
		AddNotification(MessageBox, _("[Timeshift] Restarting time shift!"), MessageBox.TYPE_INFO, timeout=5)

	def saveTimeshiftEventPopup(self):
		self.saveTimeshiftEventPopupActive = True
		filecount = 0
		entrylist = [(_("Current Event:") + " %s" % self.pts_curevent_name, "savetimeshift")]
		filelist = listdir(config.timeshift.path.value)
		if filelist is not None:
			try:
				filelist = sorted(filelist, key=lambda x: int(x.split("pts_livebuffer_")[1]) if x.startswith("pts_livebuffer") and not splitext(x)[1] else x)
			except Exception:
				print("[Timeshift] Error: File sorting error, using standard sorting method.")
				filelist.sort()
			for filename in filelist:
				if filename.startswith("pts_livebuffer") and not splitext(filename)[1]:
					statinfo = stat("%s%s" % (config.timeshift.path.value, filename))
					if statinfo.st_mtime < (time() - 5.0):
						# Get Event Info from meta file
						readmetafile = open("%s%s.meta" % (config.timeshift.path.value, filename))
						servicerefname = readmetafile.readline()[0:-1]
						eventname = readmetafile.readline()[0:-1]
						description = readmetafile.readline()[0:-1]
						begintime = readmetafile.readline()[0:-1]
						readmetafile.close()
						# Add Event to list
						filecount += 1
						if config.timeshift.deleteAfterZap.value and servicerefname == self.pts_curevent_servicerefname:
							entrylist.append((_("Record") + " #%s (%s): %s" % (filecount, strftime("%H:%M", localtime(int(begintime))), eventname), "%s" % filename))
						else:
							servicename = ServiceReference(servicerefname).getServiceName()
							entrylist.append(("[%s] %s : %s" % (strftime("%H:%M", localtime(int(begintime))), servicename, eventname), "%s" % filename))
			self.session.openWithCallback(self.recordQuestionCallback, ChoiceBox, title=_("Which time shift buffer event do you want to save?"), list=entrylist)

	def saveTimeshiftActions(self, action=None, returnFunction=None):
		timeshiftfile = None
		if self.pts_currplaying != self.pts_eventcount:
			timeshiftfile = "pts_livebuffer_%s" % self.pts_currplaying
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
		# Get rid of old time shift file before E2 truncates its filesize
		if returnFunction is not None and action != "no":
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
					statinfo = stat("%s%s" % (config.timeshift.path.value, filename))
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
					# Save Current Event by creating hardlink to ts file
					if self.pts_starttime >= (time() - 60):
						self.pts_starttime -= 60
					ptsfilename = "%s - %s - %s" % (strftime("%Y%m%d %H%M", localtime(self.pts_starttime)), self.pts_curevent_station, self.pts_curevent_name.replace("\n", ""))
					try:
						if config.usage.setup_level.index >= 2:
							if config.recording.filename_composition.value == "long" and self.pts_curevent_name.replace("\n", "") != self.pts_curevent_description.replace("\n", ""):
								ptsfilename = "%s - %s - %s - %s" % (strftime("%Y%m%d %H%M", localtime(self.pts_starttime)), self.pts_curevent_station, self.pts_curevent_name.replace("\n", ""), self.pts_curevent_description.replace("\n", ""))
							elif config.recording.filename_composition.value == "short":
								ptsfilename = "%s - %s" % (strftime("%Y%m%d", localtime(self.pts_starttime)), self.pts_curevent_name.replace("\n", ""))
							elif config.recording.filename_composition.value == "veryshort":
								ptsfilename = "%s - %s" % (self.pts_curevent_name.replace("\n", ""), strftime("%Y%m%d %H%M", localtime(self.pts_starttime)))
							elif config.recording.filename_composition.value == "veryveryshort":
								ptsfilename = "%s - %s" % (self.pts_curevent_name.replace("\n", ""), strftime("%Y%m%d %H%M", localtime(self.pts_starttime)))
					except Exception as errormsg:
						print("[Timeshift] Using default filename.")
					if config.recording.ascii_filenames.value:
						ptsfilename = legacyEncode(ptsfilename)
					fullname = getRecordingFilename(ptsfilename, recordingPath)
					link("%s%s" % (config.timeshift.path.value, savefilename), "%s.ts" % fullname)
					metafile = open("%s.ts.meta" % fullname, "w")
					metafile.write("%s\n%s\n%s\n%i\n%s" % (self.pts_curevent_servicerefname, self.pts_curevent_name.replace("\n", ""), self.pts_curevent_description.replace("\n", ""), int(self.pts_starttime), metamergestring))
					metafile.close()
					self.ptsCreateEITFile(fullname)
				elif timeshiftfile.startswith("pts_livebuffer"):
					# Save stored time shift by creating hardlink to ts file.
					readmetafile = open("%s%s.meta" % (config.timeshift.path.value, timeshiftfile))
					servicerefname = readmetafile.readline()[0:-1]
					eventname = readmetafile.readline()[0:-1]
					description = readmetafile.readline()[0:-1]
					begintime = readmetafile.readline()[0:-1]
					readmetafile.close()
					if config.timeshift.deleteAfterZap.value and servicerefname == self.pts_curevent_servicerefname:
						servicename = self.pts_curevent_station
					else:
						servicename = ServiceReference(servicerefname).getServiceName()
					ptsfilename = "%s - %s - %s" % (strftime("%Y%m%d %H%M", localtime(int(begintime))), servicename, eventname)
					try:
						if config.usage.setup_level.index >= 2:
							if config.recording.filename_composition.value == "long" and eventname != description:
								ptsfilename = "%s - %s - %s - %s" % (strftime("%Y%m%d %H%M", localtime(int(begintime))), servicename, eventname, description)
							elif config.recording.filename_composition.value == "short":
								ptsfilename = "%s - %s" % (strftime("%Y%m%d", localtime(int(begintime))), eventname)
							elif config.recording.filename_composition.value == "veryshort":
								ptsfilename = "%s - %s" % (eventname, strftime("%Y%m%d %H%M", localtime(int(begintime))))
							elif config.recording.filename_composition.value == "veryveryshort":
								ptsfilename = "%s - %s" % (eventname, strftime("%Y%m%d %H%M", localtime(int(begintime))))
					except Exception as errormsg:
						print("[Timeshift] Using default filename.")
					if config.recording.ascii_filenames.value:
						ptsfilename = legacyEncode(ptsfilename)
					fullname = getRecordingFilename(ptsfilename, recordingPath)
					link("%s%s" % (config.timeshift.path.value, timeshiftfile), "%s.ts" % fullname)
					link("%s%s.meta" % (config.timeshift.path.value, timeshiftfile), "%s.ts.meta" % fullname)
					if exists("%s%s.eit" % (config.timeshift.path.value, timeshiftfile)):
						link("%s%s.eit" % (config.timeshift.path.value, timeshiftfile), "%s.eit" % fullname)
					# Add merge-tag to meta file.
					if mergelater:
						metafile = open("%s.ts.meta" % fullname, "a")
						metafile.write("%s\n" % metamergestring)
						metafile.close()
				# Create AP and SC Files when not merging
				if not mergelater:
					self.ptsCreateAPSCFiles(fullname + ".ts")
			except Exception as errormsg:
				timeshift_saved = False
				timeshift_saveerror1 = errormsg
			# Hmpppf! Saving Timeshift via Hardlink-Method failed. Probably other device?
			# Let's try to copy the file in background now! This might take a while ...
			if not timeshift_saved:
				try:
					status = statvfs(recordingPath)
					freespace = status.f_bfree / 1000 * status.f_bsize / 1000
					randomint = randint(1, 999)
					if timeshiftfile is None:
						# Get Filesize for Free Space Check
						filesize = int(getsize("%s%s" % (config.timeshift.path.value, savefilename)) / (1024 * 1024))
						# Save Current Event by copying it to the other device
						if filesize <= freespace:
							link("%s%s" % (config.timeshift.path.value, savefilename), "%s%s.%s.copy" % (config.timeshift.path.value, savefilename, randomint))
							copy_file = savefilename
							metafile = open("%s.ts.meta" % fullname, "w")
							metafile.write("%s\n%s\n%s\n%i\n%s" % (self.pts_curevent_servicerefname, self.pts_curevent_name.replace("\n", ""), self.pts_curevent_description.replace("\n", ""), int(self.pts_starttime), metamergestring))
							metafile.close()
							self.ptsCreateEITFile(fullname)
					elif timeshiftfile.startswith("pts_livebuffer"):
						# Get Filesize for Free Space Check
						filesize = int(getsize("%s%s" % (config.timeshift.path.value, timeshiftfile)) / (1024 * 1024))
						# Save stored time shift by copying it to the other device
						if filesize <= freespace:
							link("%s%s" % (config.timeshift.path.value, timeshiftfile), "%s%s.%s.copy" % (config.timeshift.path.value, timeshiftfile, randomint))
							copyfile("%s%s.meta" % (config.timeshift.path.value, timeshiftfile), "%s.ts.meta" % fullname)
							if exists("%s%s.eit" % (config.timeshift.path.value, timeshiftfile)):
								copyfile("%s%s.eit" % (config.timeshift.path.value, timeshiftfile), "%s.eit" % fullname)
							copy_file = timeshiftfile
						# Add merge-tag to metafile
						if mergelater:
							metafile = open("%s.ts.meta" % fullname, "a")
							metafile.write("%s\n" % metamergestring)
							metafile.close()
					# Only copy file when enough disk-space available!
					if filesize <= freespace:
						timeshift_saved = True
						copy_file = copy_file + "." + str(randomint)
						# Get Event Info from meta file
						if exists("%s.ts.meta" % fullname):
							readmetafile = open("%s.ts.meta" % fullname)
							servicerefname = readmetafile.readline()[0:-1]
							eventname = readmetafile.readline()[0:-1]
							readmetafile.close()
						else:
							eventname = ""
						JobManager.AddJob(CopyTimeshiftJob(self, "mv \"%s%s.copy\" \"%s.ts\"" % (config.timeshift.path.value, copy_file, fullname), copy_file, fullname, eventname))
						if not Screens.Standby.inTryQuitMainloop and not Screens.Standby.inStandby and not mergelater and self.save_timeshift_postaction != "standby":
							AddNotification(MessageBox, _("Saving time shift buffer, this might take a while."), MessageBox.TYPE_INFO, timeout=30)
					else:
						timeshift_saved = False
						timeshift_saveerror1 = ""
						timeshift_saveerror2 = _("Not enough free disk space!\n\nFilesize: %sMB\nFree Space: %sMB\nPath: %s" % (filesize, freespace, recordingPath))
				except Exception as errormsg:
					timeshift_saved = False
					timeshift_saveerror2 = errormsg
			if not timeshift_saved:
				config.timeshift.isRecording.value = False
				self.save_timeshift_postaction = None
				errormessage = str(timeshift_saveerror1) + "\n" + str(timeshift_saveerror2)
				AddNotification(MessageBox, _("Time shift save failed!") + "\n\n%s" % errormessage, MessageBox.TYPE_ERROR, timeout=30)

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
			print("[Timeshift] 'cleanEvent_timer' is stopped.")

	def ptsEventCleanTimerSTART(self):
		if not self.pts_cleanEvent_timer.isActive() and config.timeshift.checkEvents.value:
			# self.pts_cleanEvent_timer.start(60000 * config.timeshift.checkEvents.value, False)
			self.pts_cleanEvent_timer.startLongTimer(60 * config.timeshift.checkEvents.value)
			print("[Timeshift] 'cleanEvent_timer' is starting.")

	def ptsEventCleanTimeshiftFolder(self):
		print("[Timeshift] 'cleanEvent_timer' is running.")
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
				for i in list(range(self.pts_currplaying, self.pts_eventcount + 1)):
					lockedFiles.append(("pts_livebuffer_%s") % i)
			else:
				if not self.event_changed:
					lockedFiles.append(("pts_livebuffer_%s") % self.pts_currplaying)
		if freespace:
			try:
				status = statvfs(config.timeshift.path.value)
				freespace = status.f_bavail * status.f_bsize / 1024 / 1024
			except Exception:
				print("[Timeshift] Error reading disk space - function 'checking for free space' can't used.")
		if freespace < config.timeshift.checkFreeSpace.value:
			for i in list(range(1, self.pts_eventcount + 1)):
				removeFiles.append(("pts_livebuffer_%s") % i)
			print("[Timeshift] Less than %s MByte disk space available. Try deleting all unused time shift files." % config.timeshift.checkFreeSpace.value)
		elif self.pts_eventcount - config.timeshift.maxEvents.value >= 0:
			if self.event_changed or len(lockedFiles) == 0:
				for i in list(range(1, self.pts_eventcount - config.timeshift.maxEvents.value + 2)):
					removeFiles.append(("pts_livebuffer_%s") % i)
			else:
				for i in list(range(1, self.pts_eventcount - config.timeshift.maxEvents.value + 1)):
					removeFiles.append(("pts_livebuffer_%s") % i)
		for filename in listdir(config.timeshift.path.value):
			if (exists("%s%s" % (config.timeshift.path.value, filename))) and ((filename.startswith("timeshift.") or filename.startswith("pts_livebuffer_"))):
				try:
					statinfo = stat("%s%s" % (config.timeshift.path.value, filename))
				except OSError:
					statinfo = None  # a .del file may have been deleted between "exists" and "stat"
				if (justZapped is True) and (filename.endswith(".del") is False) and (filename.endswith(".copy") is False):
					# after zapping, remove all regular time shift files
					filesize += getsize("%s%s" % (config.timeshift.path.value, filename))
					self.BgFileEraser.erase("%s%s" % (config.timeshift.path.value, filename))
				elif (statinfo is not None) and (filename.endswith(".eit") is False) and (filename.endswith(".meta") is False) and (filename.endswith(".sc") is False) and (filename.endswith(".del") is False) and (filename.endswith(".copy") is False):
					# remove old files, but only complete sets of files (base file, .eit, .meta, .sc),
					# and not while saveTimeshiftEventPopup is active (avoid deleting files about to be saved)
					# and don't delete files from currently playing up to the last event
					if not filename.startswith("timeshift."):
						filecounter += 1
					if ((statinfo.st_mtime < (time() - 3600 * config.timeshift.maxHours.value)) or any(filename in s for s in removeFiles)) and (self.saveTimeshiftEventPopupActive is False) and not any(filename in s for s in lockedFiles):
						# print("[Timeshift] Erasing set of old time shift files (base file, .eit, .meta, .sc) '%s'." % filename)
						filesize += getsize("%s%s" % (config.timeshift.path.value, filename))
						self.BgFileEraser.erase("%s%s" % (config.timeshift.path.value, filename))
						if exists("%s%s.eit" % (config.timeshift.path.value, filename)):
							filesize += getsize("%s%s.eit" % (config.timeshift.path.value, filename))
							self.BgFileEraser.erase("%s%s.eit" % (config.timeshift.path.value, filename))
						if exists("%s%s.meta" % (config.timeshift.path.value, filename)):
							filesize += getsize("%s%s.meta" % (config.timeshift.path.value, filename))
							self.BgFileEraser.erase("%s%s.meta" % (config.timeshift.path.value, filename))
						if exists("%s%s.sc" % (config.timeshift.path.value, filename)):
							filesize += getsize("%s%s.sc" % (config.timeshift.path.value, filename))
							self.BgFileEraser.erase("%s%s.sc" % (config.timeshift.path.value, filename))
						if not filename.startswith("timeshift."):
							filecounter -= 1
				elif (statinfo is not None):
					# remove anything still left over another 24h later
					if statinfo.st_mtime < (time() - 3600 * (24 + config.timeshift.maxHours.value)):
						# print("[Timeshift] Erasing very old time shift file '%s'." % filename)
						if filename.endswith(".del") is True:
							filesize += getsize("%s%s" % (config.timeshift.path.value, filename))
							try:
								rename("%s%s" % (config.timeshift.path.value, filename), "%s%s.del_again" % (config.timeshift.path.value, filename))
								self.BgFileEraser.erase("%s%s.del_again" % (config.timeshift.path.value, filename))
							except Exception:
								print("[Timeshift] - can't rename %s%s." % (config.timeshift.path.value, filename))
								self.BgFileEraser.erase("%s%s" % (config.timeshift.path.value, filename))
						else:
							filesize += getsize("%s%s" % (config.timeshift.path.value, filename))
							self.BgFileEraser.erase("%s%s" % (config.timeshift.path.value, filename))
		if filecounter == 0:
			self.ptsEventCleanTimerSTOP()
		else:
			if timeshiftEnabled and not isSeekable:
				if freespace + (filesize / 1024 / 1024) < config.timeshift.checkFreeSpace.value:
					self.ptsAskUser("space")
				elif time() - self.pts_starttime > 3600 * config.timeshift.maxHours.value:
					self.ptsAskUser("time")
			elif isSeekable:
				if freespace + (filesize / 1024 / 1024) < config.timeshift.checkFreeSpace.value:
					self.ptsAskUser("space_and_save")
				elif time() - self.pts_starttime > 3600 * config.timeshift.maxHours.value:
					self.ptsAskUser("time_and_save")
			if self.checkEvents_value != config.timeshift.checkEvents.value:
				if self.pts_cleanEvent_timer.isActive():
					# print("[Timeshift] 'cleanEvent_timer' was changed.")
					self.pts_cleanEvent_timer.stop()
					if config.timeshift.checkEvents.value:
						self.ptsEventCleanTimerSTART()
					else:
						print("[Timeshift] 'cleanEvent_timer' is deactivated.")
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
		except Exception as errormsg:
			AddNotification(MessageBox, _("Getting event information failed!") + "\n\n%s" % errormsg, MessageBox.TYPE_ERROR, timeout=10)
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
				f = open("/proc/stb/fp/led_set_pattern", "w")
				f.write("0xa7fccf7a")
				f.close()
			elif exists("/proc/stb/fp/led0_pattern"):
				f = open("/proc/stb/fp/led0_pattern", "w")
				f.write("0x55555555")
				f.close()
			if exists("/proc/stb/fp/led_pattern_speed"):
				f = open("/proc/stb/fp/led_pattern_speed", "w")
				f.write("20")
				f.close()
			elif exists("/proc/stb/fp/led_set_speed"):
				f = open("/proc/stb/fp/led_set_speed", "w")
				f.write("20")
				f.close()
		elif action == "stop":
			if exists("/proc/stb/fp/led_set_pattern"):
				f = open("/proc/stb/fp/led_set_pattern", "w")
				f.write("0")
				f.close()
			elif exists("/proc/stb/fp/led0_pattern"):
				f = open("/proc/stb/fp/led0_pattern", "w")
				f.write("0")
				f.close()

	def ptsCreateHardlink(self):
		for filename in listdir(config.timeshift.path.value):
			if filename.startswith("timeshift.") and not filename.endswith(".sc") and not filename.endswith(".del") and not filename.endswith(".copy") and not filename.endswith(".ap"):
				if exists("%spts_livebuffer_%s.eit" % (config.timeshift.path.value, self.pts_eventcount)):
					self.BgFileEraser.erase("%spts_livebuffer_%s.eit" % (config.timeshift.path.value, self.pts_eventcount))
				if exists("%spts_livebuffer_%s.meta" % (config.timeshift.path.value, self.pts_eventcount)):
					self.BgFileEraser.erase("%spts_livebuffer_%s.meta" % (config.timeshift.path.value, self.pts_eventcount))
				if exists("%spts_livebuffer_%s" % (config.timeshift.path.value, self.pts_eventcount)):
					self.BgFileEraser.erase("%spts_livebuffer_%s" % (config.timeshift.path.value, self.pts_eventcount))
				if exists("%spts_livebuffer_%s.sc" % (config.timeshift.path.value, self.pts_eventcount)):
					self.BgFileEraser.erase("%spts_livebuffer_%s.sc" % (config.timeshift.path.value, self.pts_eventcount))
				try:
					# Create link to pts_livebuffer file
					link("%s%s" % (config.timeshift.path.value, filename), "%spts_livebuffer_%s" % (config.timeshift.path.value, self.pts_eventcount))
					link("%s%s.sc" % (config.timeshift.path.value, filename), "%spts_livebuffer_%s.sc" % (config.timeshift.path.value, self.pts_eventcount))
					# Create a Meta File
					metafile = open("%spts_livebuffer_%s.meta" % (config.timeshift.path.value, self.pts_eventcount), "w")
					metafile.write("%s\n%s\n%s\n%i\n" % (self.pts_curevent_servicerefname, self.pts_curevent_name.replace("\n", ""), self.pts_curevent_description.replace("\n", ""), int(self.pts_starttime)))
					metafile.close()
				except Exception as errormsg:
					AddNotification(MessageBox, _("Creating hard link to time shift file failed!") + "\n" + _("The file system on your time shift device does not support hard links.\nMake sure it is formatted in EXT2, EXT3 or EXT4!") + "\n\n%s" % errormsg, MessageBox.TYPE_ERROR, timeout=30)
				# Create EIT File
				self.ptsCreateEITFile("%spts_livebuffer_%s" % (config.timeshift.path.value, self.pts_eventcount))

				# Autorecord
				if config.timeshift.autorecord.value:
					try:
						fullname = getRecordingFilename("%s - %s - %s" % (strftime("%Y%m%d %H%M", localtime(self.pts_starttime)), self.pts_curevent_station, self.pts_curevent_name), preferredTimeShiftRecordingPath())
						link("%s%s" % (config.timeshift.path.value, filename), "%s.ts" % fullname)
						# Create a Meta File
						metafile = open("%s.ts.meta" % fullname, "w")
						metafile.write("%s\n%s\n%s\n%i\nautosaved\n" % (self.pts_curevent_servicerefname, self.pts_curevent_name.replace("\n", ""), self.pts_curevent_description.replace("\n", ""), int(self.pts_starttime)))
						metafile.close()
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
				# Get Event Info from meta file.
				readmetafile = open("%s%s" % (recordingPath, filename))
				servicerefname = readmetafile.readline()[0:-1]
				eventname = readmetafile.readline()[0:-1]
				eventtitle = readmetafile.readline()[0:-1]
				eventtime = readmetafile.readline()[0:-1]
				eventtag = readmetafile.readline()[0:-1]
				readmetafile.close()
				if ptsgetnextfile:
					ptsgetnextfile = False
					ptsmergeSRC = filename[0:-5]
					if legacyEncode(eventname) == legacyEncode(ptsmergeeventname):
						# Copy EIT File
						if fileExists("%s%s.eit" % (recordingPath, ptsmergeSRC[0:-3])):
							copyfile("%s%s.eit" % (recordingPath, ptsmergeSRC[0:-3]), "%s%s.eit" % (recordingPath, ptsmergeDEST[0:-3]))
						# Delete AP and SC Files
						if exists("%s%s.ap" % (recordingPath, ptsmergeDEST)):
							self.BgFileEraser.erase("%s%s.ap" % (recordingPath, ptsmergeDEST))
						if exists("%s%s.sc" % (recordingPath, ptsmergeDEST)):
							self.BgFileEraser.erase("%s%s.sc" % (recordingPath, ptsmergeDEST))
						# Add Merge Job to JobManager
						JobManager.AddJob(MergeTimeshiftJob(self, "cat \"%s%s\" >> \"%s%s\"" % (recordingPath, ptsmergeSRC, recordingPath, ptsmergeDEST), ptsmergeSRC, ptsmergeDEST, eventname))
						config.timeshift.isRecording.value = True
						ptsfilemerged = True
					else:
						ptsgetnextfile = True
				if eventtag == "pts_merge" and not ptsgetnextfile:
					ptsgetnextfile = True
					ptsmergeDEST = filename[0:-5]
					ptsmergeeventname = eventname
					ptsfilemerged = False
					# If still recording or transfering, try again later ...
					if fileExists("%s%s" % (recordingPath, ptsmergeDEST)):
						statinfo = stat("%s%s" % (recordingPath, ptsmergeDEST))
						if statinfo.st_mtime > (time() - 10.0):
							self.pts_mergeRecords_timer.start(120000, True)
							return
					# Rewrite Meta File to get rid of pts_merge tag
					metafile = open("%s%s.meta" % (recordingPath, ptsmergeDEST), "w")
					metafile.write("%s\n%s\n%s\n%i\n" % (servicerefname, eventname.replace("\n", ""), eventtitle.replace("\n", ""), int(eventtime)))
					metafile.close()
		# Merging failed :(
		if not ptsfilemerged and ptsgetnextfile:
			AddNotification(MessageBox, _("[Timeshift] Merging records failed!"), MessageBox.TYPE_ERROR, timeout=30)

	def ptsCreateAPSCFiles(self, filename):
		if fileExists(filename, "r"):
			if fileExists("%s.meta" % filename, "r"):
				# Get Event Info from meta file.
				readmetafile = open(filename + ".meta")
				servicerefname = readmetafile.readline()[0:-1]
				eventname = readmetafile.readline()[0:-1]
				readmetafile.close()
			else:
				eventname = ""
			JobManager.AddJob(CreateAPSCFilesJob(self, "/usr/lib/enigma2/python/Components/createapscfiles \"%s\" > /dev/null" % filename, eventname))
		else:
			self.ptsSaveTimeshiftFinished()

	def ptsCreateEITFile(self, filename):
		if self.pts_curevent_eventid is not None:
			try:
				serviceref = ServiceReference(self.session.nav.getCurrentlyPlayingServiceOrGroup()).ref
				eEPGCache.getInstance().saveEventToFile(filename + ".eit", serviceref, self.pts_curevent_eventid, -1, -1)
			except Exception as err:
				print("[Timeshift] Error: %s" % str(err))

	def ptsCopyFilefinished(self, srcfile, destfile):
		# Erase Source File
		if fileExists(srcfile):
			self.BgFileEraser.erase(srcfile)
		# Restart Merge Timer
		if self.pts_mergeRecords_timer.isActive():
			self.pts_mergeRecords_timer.stop()
			self.pts_mergeRecords_timer.start(15000, True)
		else:
			# Create AP and SC Files
			self.ptsCreateAPSCFiles(destfile)

	def ptsMergeFilefinished(self, srcfile, destfile):
		if self.session.nav.RecordTimer.isRecording() or len(JobManager.getPendingJobs()) >= 1:
			# Rename files and delete them later ...
			self.pts_mergeCleanUp_timer.start(120000, True)
			ossystem("echo \"\" > \"%s.pts.del\"" % (srcfile[0:-3]))
		else:
			# Delete Instant Record permanently now ... R.I.P.
			self.BgFileEraser.erase("%s" % srcfile)
			self.BgFileEraser.erase("%s.ap" % srcfile)
			self.BgFileEraser.erase("%s.sc" % srcfile)
			self.BgFileEraser.erase("%s.meta" % srcfile)
			self.BgFileEraser.erase("%s.cuts" % srcfile)
			self.BgFileEraser.erase("%s.eit" % (srcfile[0:-3]))
		# Create AP and SC Files
		self.ptsCreateAPSCFiles(destfile)
		# Run Merge-Process one more time to check if there are more records to merge
		self.pts_mergeRecords_timer.start(10000, True)

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
				srcfile = recordingPath + "/" + filename[0:-8] + ".ts"
				self.BgFileEraser.erase("%s" % srcfile)
				self.BgFileEraser.erase("%s.ap" % srcfile)
				self.BgFileEraser.erase("%s.sc" % srcfile)
				self.BgFileEraser.erase("%s.meta" % srcfile)
				self.BgFileEraser.erase("%s.cuts" % srcfile)
				self.BgFileEraser.erase("%s.eit" % (srcfile[0:-3]))
				self.BgFileEraser.erase("%s.pts.del" % (srcfile[0:-3]))
				# Restart QuitMainloop Timer to give BgFileEraser enough time
				if Screens.Standby.inTryQuitMainloop and self.pts_QuitMainloop_timer.isActive():
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
		else:
			return

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
		if isvalidjump:
			self.pvrStateDialog["PTSSeekPointer"].setPosition(cur_pos[0] + movepixels, cur_pos[1])
		else:
			self.pvrStateDialog["PTSSeekPointer"].setPosition(minmaxval, cur_pos[1])

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
		# Reset seek pointer.
		self.ptsSeekPointerReset()
		if self.pts_switchtolive:
			self.pts_switchtolive = False
			self.pts_nextplaying = 0
			self.pts_currplaying = self.pts_eventcount
			return
		if self.pts_nextplaying:
			self.pts_currplaying = self.pts_nextplaying
		self.pts_nextplaying = self.pts_currplaying + 1
		# Get next pts file.
		if fileExists("%spts_livebuffer_%s" % (config.timeshift.path.value, self.pts_nextplaying), "r"):
			self.ptsSetNextPlaybackFile("pts_livebuffer_%s" % self.pts_nextplaying)
			self.pts_switchtolive = False
		else:
			self.ptsSetNextPlaybackFile("")
			self.pts_switchtolive = True

	def ptsSetNextPlaybackFile(self, nexttsfile):
		ts = self.getTimeshift()
		if ts is None:
			return
		if nexttsfile:
			ts.setNextPlaybackFile("%s%s" % (config.timeshift.path.value, nexttsfile))
		else:
			ts.setNextPlaybackFile("")

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
		self.doSeek(-90000 * 10)  # Seek ~10s before end.
		self.setSeekState(self.SEEK_STATE_PAUSE)
		self.pts_StartSeekBackTimer.start(1000, True)

	def ptsStartSeekBackTimer(self):
		if self.pts_lastseekspeed == 0:
			self.setSeekState(self.makeStateBackward(int(config.seek.enter_backward.value)))
		else:
			self.setSeekState(self.makeStateBackward(int(-self.pts_lastseekspeed)))

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
		if not config.timeshift.stopWhileRecording.value:
			return
		self.pts_record_running = self.session.nav.RecordTimer.isRecording()
		# Abort here when box is in standby mode.
		if self.session.screen["Standby"].boolean is True:
			return
		# Stop time shift when recording started.
		if timer.state == TimerEntry.StateRunning and self.timeshiftEnabled() and self.pts_record_running:
			if self.seekstate != self.SEEK_STATE_PLAY:
				self.setSeekState(self.SEEK_STATE_PLAY)
			if self.isSeekable():
				AddNotification(MessageBox, _("Recording started, stopping time shift now."), MessageBox.TYPE_INFO, timeout=30)
			self.switchToLive = False
			self.stopTimeshiftcheckTimeshiftRunningCallback(True)
		if timer.state == TimerEntry.StateEnded:
			# Restart time shift when all recordings stopped.
			if not self.timeshiftEnabled() and not self.pts_record_running:
				self.autostartPermanentTimeshift()
			if self.pts_mergeRecords_timer.isActive():
				# Restart merge timer when all recordings stopped.
				self.pts_mergeRecords_timer.stop()
				self.pts_mergeRecords_timer.start(15000, True)
				# Restart front panel LED when still copying or merging files.
				self.ptsFrontpanelActions("start")
				config.timeshift.isRecording.value = True
			else:
				# Restart front panel LED when still copying or merging files.
				jobs = JobManager.getPendingJobs()
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
		self.srcfile = pathjoin(config.timeshift.path.value, "%s.copy" % srcfile)
		self.destfile = "%s.ts" % destfile
		self.ProgressTimer = eTimer()
		self.ProgressTimer.callback.append(self.ProgressUpdate)

	def ProgressUpdate(self):
		if self.srcsize <= 0 or not fileExists(self.destfile, "r"):
			return
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
		self.srcfile = pathjoin(preferredTimeShiftRecordingPath(), srcfile)
		self.destfile = pathjoin(preferredTimeShiftRecordingPath(), destfile)
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
