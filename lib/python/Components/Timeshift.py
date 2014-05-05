# -*- coding: utf-8 -*-
# InfoBarTimeshift requires InfoBarSeek, instantiated BEFORE!

# Hrmf.
#
# Timeshift works the following way:
#                                         demux0   demux1                    "TimeshiftActions" "TimeshiftActivateActions" "SeekActions"
# - normal playback                       TUNER    unused      PLAY               enable                disable              disable
# - user presses "yellow" button.         FILE     record      PAUSE              enable                disable              enable
# - user presess pause again              FILE     record      PLAY               enable                disable              enable
# - user fast forwards                    FILE     record      FF                 enable                disable              enable
# - end of timeshift buffer reached       TUNER    record      PLAY               enable                enable               disable
# - user backwards                        FILE     record      BACK  # !!         enable                disable              enable
#

# in other words:
# - when a service is playing, pressing the "timeshiftStart" button ("yellow") enables recording ("enables timeshift"),
# freezes the picture (to indicate timeshift), sets timeshiftMode ("activates timeshift")
# now, the service becomes seekable, so "SeekActions" are enabled, "TimeshiftEnableActions" are disabled.
# - the user can now PVR around
# - if it hits the end, the service goes into live mode ("deactivates timeshift", it's of course still "enabled")
# the service looses it's "seekable" state. It can still be paused, but just to activate timeshift right
# after!
# the seek actions will be disabled, but the timeshiftActivateActions will be enabled
# - if the user rewinds, or press pause, timeshift will be activated again

# note that a timeshift can be enabled ("recording") and
# activated (currently time-shifting).


from Components.ActionMap import ActionMap, HelpableActionMap
from Components.ServiceEventTracker import ServiceEventTracker
from Components.config import config
from Components.SystemInfo import SystemInfo
from Components.Task import job_manager as JobManager

from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
import Screens.Standby
from ServiceReference import ServiceReference

from RecordTimer import RecordTimerEntry, parseEvent
from timer import TimerEntry

from Tools import ASCIItranslit, Notifications
from Tools.BoundFunction import boundFunction
from Tools.Directories import pathExists, fileExists, getRecordingFilename, copyfile, resolveFilename, SCOPE_TIMESHIFT
from Tools.TimeShift import CopyTimeshiftJob, MergeTimeshiftJob, CreateAPSCFilesJob

from enigma import eBackgroundFileEraser, eTimer, eServiceCenter, iServiceInformation, iPlayableService
from boxbranding import getBoxType, getBrandOEM

from time import time, localtime, strftime
from random import randint

import os

class InfoBarTimeshift:
	def __init__(self):
		self["TimeshiftActions"] = HelpableActionMap(self, "InfobarTimeshiftActions",
			{
				"timeshiftStart": (self.startTimeshift, _("Start timeshift")),  # the "yellow key"
				"timeshiftStop": (self.stopTimeshift, _("Stop timeshift")),     # currently undefined :), probably 'TV'
				"instantRecord": self.instantRecord,
				"restartTimeshift": self.restartTimeshift
			}, prio=1)
		self["TimeshiftActivateActions"] = ActionMap(["InfobarTimeshiftActivateActions"],
			{
				"timeshiftActivateEnd": self.activateTimeshiftEnd, # something like "rewind key"
				"timeshiftActivateEndAndPause": self.activateTimeshiftEndAndPause  # something like "pause key"
			}, prio=-1) # priority over record

		self["TimeshiftSeekPointerActions"] = ActionMap(["InfobarTimeshiftSeekPointerActions"],
			{
				"SeekPointerOK": self.ptsSeekPointerOK,
				"SeekPointerLeft": self.ptsSeekPointerLeft,
				"SeekPointerRight": self.ptsSeekPointerRight
			}, prio=-1)

		self["TimeshiftFileActions"] = ActionMap(["InfobarTimeshiftActions"],
			{
				"jumpPreviousFile": self.__evSOF,
				"jumpNextFile": self.__evEOF
			}, prio=-1) # priority over history

		self["TimeshiftActions"].setEnabled(False)
		self["TimeshiftActivateActions"].setEnabled(False)
		self["TimeshiftSeekPointerActions"].setEnabled(False)
		self["TimeshiftFileActions"].setEnabled(False)

		self.switchToLive = True
		self.ptsStop = False
		self.ts_rewind_timer = eTimer()
		self.ts_rewind_timer.callback.append(self.rewindService)
		self.save_timeshift_file = False

		self.__event_tracker = ServiceEventTracker(screen = self, eventmap =
			{
				iPlayableService.evStart: self.__serviceStarted,
				iPlayableService.evSeekableStatusChanged: self.__seekableStatusChanged,
				iPlayableService.evEnd: self.__serviceEnd,
				iPlayableService.evSOF: self.__evSOF,
				iPlayableService.evUpdatedInfo: self.__evInfoChanged,
				iPlayableService.evUpdatedEventInfo: self.__evEventInfoChanged,
				iPlayableService.evUser+1: self.ptsTimeshiftFileChanged
			})

		self.pts_begintime = 0
		self.pts_switchtolive = False
		self.pts_currplaying = 1
		self.pts_nextplaying = 0
		self.pts_lastseekspeed = 0
		self.pts_service_changed = False
		self.pts_record_running = self.session.nav.RecordTimer.isRecording()
		self.save_current_timeshift = False
		self.save_timeshift_postaction = None
		self.service_changed = 0

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
		# self.pts_cleanUp_timer.start(1000, True)

		# Init PTS SeekBack-Timer
		self.pts_SeekBack_timer = eTimer()
		self.pts_SeekBack_timer.callback.append(self.ptsSeekBackTimer)
		self.pts_StartSeekBackTimer = eTimer()
		self.pts_StartSeekBackTimer.callback.append(self.ptsStartSeekBackTimer)

		# Init Block-Zap Timer
		self.pts_blockZap_timer = eTimer()

		# Record Event Tracker
		self.session.nav.RecordTimer.on_state_change.append(self.ptsTimerEntryStateChange)

		# Keep Current Event Info for recordings
		self.pts_eventcount = 1
		self.pts_curevent_begin = int(time())
		self.pts_curevent_end = 0
		self.pts_curevent_name = _("Timeshift")
		self.pts_curevent_description = ""
		self.pts_curevent_servicerefname = ""
		self.pts_curevent_station = ""
		self.pts_curevent_eventid = None

		# Init PTS Infobar

	def __seekableStatusChanged(self):
		# print '__seekableStatusChanged'
		self["TimeshiftActivateActions"].setEnabled(not self.isSeekable() and self.timeshiftEnabled() and int(config.timeshift.startdelay.value))
		state = self.getSeek() is not None and self.timeshiftEnabled()
		self["SeekActionsPTS"].setEnabled(state)
		self["TimeshiftFileActions"].setEnabled(state)
		
		if not state:
			self.setSeekState(self.SEEK_STATE_PLAY)

		self.restartSubtitle()

		if self.timeshiftEnabled() and not self.isSeekable():
			self.ptsSeekPointerReset()
			if int(config.timeshift.startdelay.value):
				if self.pts_starttime <= (time()-5):
					self.pts_blockZap_timer.start(3000, True)
			self.pts_currplaying = self.pts_eventcount
			self.pts_nextplaying = 0
			self.ptsSetNextPlaybackFile("pts_livebuffer_%s" % self.pts_eventcount)

	def __serviceStarted(self):
		# print '__serviceStarted'
		self.createTimeshiftFolder()
		self.service_changed = 1
		self.pts_service_changed = True
		self.ptsCleanTimeshiftFolder()
		# print 'self.timeshiftEnabled1',self.timeshiftEnabled()
		if self.pts_delay_timer.isActive():
			# print 'TS AUTO START TEST1'
			self.pts_delay_timer.stop()
		if int(config.timeshift.startdelay.value) and not self.pts_delay_timer.isActive():
			# print 'TS AUTO START TEST2'
			self.pts_delay_timer.start(int(config.timeshift.startdelay.value) * 1000, True)

		self.__seekableStatusChanged()

	def __serviceEnd(self):
		self.service_changed = 0
		if not config.timeshift.isRecording.value:
			self.__seekableStatusChanged()

	def __evSOF(self):
		# print '!!!!! jumpToPrevTimeshiftedEvent'
		if not self.timeshiftEnabled():
			return

		# print 'self.pts_currplaying',self.pts_currplaying
		self.pts_nextplaying = 0
		if self.pts_currplaying > 1:
			self.pts_currplaying -= 1
		else:
			self.setSeekState(self.SEEK_STATE_PLAY)
			self.doSeek(0)
			return

		# Switch to previous TS file by seeking forward to next file
		# print 'self.pts_currplaying2',self.pts_currplaying
		# print ("'!!!!! %spts_livebuffer_%s" % (config.usage.timeshift_path.value, self.pts_currplaying))
		if fileExists("%spts_livebuffer_%s" % (config.usage.timeshift_path.value, self.pts_currplaying), 'r'):
			self.ptsSetNextPlaybackFile("pts_livebuffer_%s" % self.pts_currplaying)
			self.setSeekState(self.SEEK_STATE_PLAY)
			self.doSeek(3600 * 24 * 90000)
			self.pts_SeekBack_timer.start(1000, True)

	def __evEOF(self):
		# print '!!!!! jumpToNextTimeshiftedEvent'
		if not self.timeshiftEnabled():
			return

		# print 'self.pts_currplaying',self.pts_currplaying
		self.pts_nextplaying = 0
		self.pts_currplaying += 1

		# Switch to next TS file by seeking forward to next file
		# print 'self.pts_currplaying2',self.pts_currplaying
		# print ("'!!!!! %spts_livebuffer_%s" % (config.usage.timeshift_path.value, self.pts_currplaying))
		if fileExists("%spts_livebuffer_%s" % (config.usage.timeshift_path.value, self.pts_currplaying), 'r'):
			self.ptsSetNextPlaybackFile("pts_livebuffer_%s" % self.pts_currplaying)
		else:
			self.pts_switchtolive = True
			self.ptsSetNextPlaybackFile("")
		self.setSeekState(self.SEEK_STATE_PLAY)
		self.doSeek(3600 * 24 * 90000)

	def __evInfoChanged(self):
		# print '__evInfoChanged'
		# print 'service_changed',self.service_changed
		if self.service_changed:
			self.service_changed = 0

			# We zapped away before saving the file, save it now!
			if self.save_current_timeshift:
				self.SaveTimeshift("pts_livebuffer_%s" % self.pts_eventcount)

			# Delete Timeshift Records on zap
			self.pts_eventcount = 0
			# print 'AAAAAAAAAAAAAAAAAAAAAA'
			# self.pts_cleanUp_timer.start(1000, True)

	def __evEventInfoChanged(self):
		# print '__evEventInfoChanged'
		# if not int(config.timeshift.startdelay.value):
		# 	return

		# Get Current Event Info
		service = self.session.nav.getCurrentService()
		old_begin_time = self.pts_begintime
		info = service and service.info()
		ptr = info and info.getEvent(0)
		self.pts_begintime = ptr and ptr.getBeginTime() or 0

		# Save current TimeShift permanently now ...
		if info.getInfo(iServiceInformation.sVideoPID) != -1:
			# Take care of Record Margin Time ...
			if self.save_current_timeshift and self.timeshiftEnabled():
				if config.recording.margin_after.value > 0 and len(self.recording) == 0:
					self.SaveTimeshift(mergelater=True)
					recording = RecordTimerEntry(ServiceReference(self.session.nav.getCurrentlyPlayingServiceOrGroup()), time(), time()+(config.recording.margin_after.value * 60), self.pts_curevent_name, self.pts_curevent_description, self.pts_curevent_eventid, dirname = config.usage.default_path.value)
					recording.dontSave = True
					self.session.nav.RecordTimer.record(recording)
					self.recording.append(recording)
				else:
					self.SaveTimeshift()


			# print 'self.timeshiftEnabled2',self.timeshiftEnabled()

			# # Restarting active timers after zap ...
			# if self.pts_delay_timer.isActive() and not self.timeshiftEnabled():
			# 	print 'TS AUTO START TEST3'
			# 	self.pts_delay_timer.start(int(config.timeshift.startdelay.value) * 1000, True)
			# if self.pts_cleanUp_timer.isActive() and not self.timeshiftEnabled():
			# 	print 'BBBBBBBBBBBBBBBBBBBBB'
			# 	self.pts_cleanUp_timer.start(3000, True)

			# # (Re)Start TimeShift
			# print 'self.pts_delay_timer.isActive',self.pts_delay_timer.isActive()
			if not self.pts_delay_timer.isActive():
				# print 'TS AUTO START TEST4'
				if not self.timeshiftEnabled() or old_begin_time != self.pts_begintime or old_begin_time == 0:
					# print 'TS AUTO START TEST5'
					self.pts_delay_timer.start(1000, True)

	def getTimeshift(self):
		service = self.session.nav.getCurrentService()
		return service and service.timeshift()

	def timeshiftEnabled(self):
		ts = self.getTimeshift()
		return ts and ts.isTimeshiftEnabled()

	def startTimeshift(self):
		ts = self.getTimeshift()
		if ts is None:
			# self.session.open(MessageBox, _("Timeshift not possible!"), MessageBox.TYPE_ERROR, timeout=5)
			return 0

		if ts.isTimeshiftEnabled():
			print "hu, timeshift already enabled?"
		else:
			self.pts_eventcount = 0
			self.activatePermanentTimeshift()
			self.activateTimeshiftEndAndPause()

	def stopTimeshift(self):
		# print 'stopTimeshift'
		ts = self.getTimeshift()
		if ts and ts.isTimeshiftEnabled():
			# print 'TEST1'
			if int(config.timeshift.startdelay.value) and self.isSeekable():
				# print 'TEST2'
				self.switchToLive = True
				self.ptsStop = True
				self.checkTimeshiftRunning(self.stopTimeshiftcheckTimeshiftRunningCallback)
			elif not int(config.timeshift.startdelay.value):
				# print 'TEST2b'
				self.checkTimeshiftRunning(self.stopTimeshiftcheckTimeshiftRunningCallback)
			else:
				# print 'TES2c'
				return 0
		else:
			# print 'TEST3'
			return 0

	def stopTimeshiftcheckTimeshiftRunningCallback(self, answer):
		# print 'stopTimeshiftcheckTimeshiftRunningCallback'
		# print ' answer', answer
		if answer and int(config.timeshift.startdelay.value) and self.switchToLive and self.isSeekable():
			# print 'TEST4'
			self.ptsStop = False
			self.pts_nextplaying = 0
			self.pts_switchtolive = True
			self.setSeekState(self.SEEK_STATE_PLAY)
			self.ptsSetNextPlaybackFile("")
			self.doSeek(3600 * 24 * 90000)
			self.__seekableStatusChanged()
			return 0

		was_enabled = False
		ts = self.getTimeshift()
		if ts and ts.isTimeshiftEnabled():
			# print 'TEST5'
			was_enabled = ts.isTimeshiftEnabled()
		if answer and ts:
			# print 'TEST6'
			if int(config.timeshift.startdelay.value):
				# print 'TEST7'
				ts.stopTimeshift(self.switchToLive)
			else:
				# print 'TEST8'
				ts.stopTimeshift()
				self.service_changed = 1
			self.__seekableStatusChanged()

	# activates timeshift, and seeks to (almost) the end
	def activateTimeshiftEnd(self, back = True):
		ts = self.getTimeshift()
		if ts is None:
			return

		if ts.isTimeshiftActive():
			self.pauseService()
		else:
			ts.activateTimeshift() # activate timeshift will automatically pause
			self.setSeekState(self.SEEK_STATE_PAUSE)
			seekable = self.getSeek()
			if seekable is not None:
				seekable.seekTo(-90000) # seek approx. 1 sec before end
		if back:
			if getBrandOEM() == 'xtrend':
				self.ts_rewind_timer.start(1000, 1)
			else:
				self.ts_rewind_timer.start(100, 1)

	def rewindService(self):
		if getBrandOEM() in ('gigablue', 'xp'):
			self.setSeekState(self.SEEK_STATE_PLAY)
		self.setSeekState(self.makeStateBackward(int(config.seek.enter_backward.value)))

	# same as activateTimeshiftEnd, but pauses afterwards.
	def activateTimeshiftEndAndPause(self):
		self.activateTimeshiftEnd(False)

	def checkTimeshiftRunning(self, returnFunction):
		# print 'checkTimeshiftRunning'
		# print 'self.switchToLive',self.switchToLive
		if self.ptsStop:
			returnFunction(True)
		elif (self.isSeekable() and self.timeshiftEnabled() or self.save_current_timeshift) and config.usage.check_timeshift.value:
			# print 'TEST1'
			if config.timeshift.favoriteSaveAction.value == "askuser":
				# print 'TEST2'
				if self.save_current_timeshift:
					# print 'TEST3'
					message = _("You have chosen to save the current timeshift event, but the event has not yet finished\nWhat do you want to do ?")
					choice = [(_("Save timeshift as movie and stop recording"), "savetimeshift"),
							  (_("Save timeshift as movie and continue recording"), "savetimeshiftandrecord"),
							  (_("Cancel save timeshift as movie"), "noSave"),
							  (_("Nothing, just leave this menu"), "no")]
					self.session.openWithCallback(boundFunction(self.checkTimeshiftRunningCallback, returnFunction), MessageBox, message, simple = True, list = choice)
				else:
					# print 'TEST4'
					message =  _("You seem to be in timeshift, Do you want to leave timeshift ?")
					choice = [(_("Yes, but save timeshift as movie and stop recording"), "savetimeshift"),
							  (_("Yes, but save timeshift as movie and continue recording"), "savetimeshiftandrecord"),
							  (_("Yes, but don't save timeshift as movie"), "noSave"),
							  (_("No"), "no")]
					self.session.openWithCallback(boundFunction(self.checkTimeshiftRunningCallback, returnFunction), MessageBox, message, simple = True, list = choice)
			else:
				# print 'TEST5'
				if self.save_current_timeshift:
					# print 'TEST6'
					InfoBarTimeshift.saveTimeshiftActions(self, config.timeshift.favoriteSaveAction.value, returnFunction)
				else:
					# print 'TEST7'
					message =  _("You seem to be in timeshift, Do you want to leave timeshift ?")
					choice = [(_("Yes"), config.timeshift.favoriteSaveAction.value), (_("No"), "no")]
					self.session.openWithCallback(boundFunction(self.checkTimeshiftRunningCallback, returnFunction), MessageBox, message, simple = True, list = choice)
		else:
			returnFunction(True)

	def checkTimeshiftRunningCallback(self, returnFunction, answer):
		# print 'checkTimeshiftRunningCallback'
		# print 'returnFunction',returnFunction
		# print 'answer',answer
		if answer:
			if answer == "savetimeshift" or answer == "savetimeshiftandrecord":
				self.save_current_timeshift = True
			elif answer == "noSave" or answer == "no":
				self.save_current_timeshift = False
			InfoBarTimeshift.saveTimeshiftActions(self, answer, returnFunction)

	def eraseTimeshiftFile(self):
		for filename in os.listdir(config.usage.timeshift_path.value):
			if filename.startswith("timeshift.") and not filename.endswith(".del") and not filename.endswith(".copy"):
				self.BgFileEraser.erase("%s%s" % (config.usage.timeshift_path.value,filename))

	def autostartPermanentTimeshift(self):
		# print '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!autostartPermanentTimeshift'
		self["TimeshiftActions"].setEnabled(True)
		ts = self.getTimeshift()
		if ts is None:
			# print '[TimeShift] tune lock failed, so could not start.'
			return 0

		if int(config.timeshift.startdelay.value):
			self.activatePermanentTimeshift()

	def activatePermanentTimeshift(self):
		if self.ptsCheckTimeshiftPath() is False or self.session.screen["Standby"].boolean is True or self.ptsLiveTVStatus() is False or (config.timeshift.stopwhilerecording.value and self.pts_record_running):
			return

		# Set next-file on event change only when watching latest timeshift ...
		if self.isSeekable() and self.pts_eventcount == self.pts_currplaying:
			pts_setnextfile = True
		else:
			pts_setnextfile = False

		# Update internal Event Counter
		self.pts_eventcount += 1

		# setNextPlaybackFile() on event change while timeshifting
		if self.pts_eventcount > 1 and self.isSeekable() and pts_setnextfile:
			self.ptsSetNextPlaybackFile("pts_livebuffer_%s" % self.pts_eventcount)

		# Do not switch back to LiveTV while timeshifting
		if self.isSeekable():
			self.switchToLive = False
		else:
			self.switchToLive = True

		# (Re)start Timeshift now
		self.stopTimeshiftcheckTimeshiftRunningCallback(True)
		ts = self.getTimeshift()
		if ts and not ts.startTimeshift():
			if (getBoxType() == 'vuuno' or getBoxType() == 'vuduo') and os.path.exists("/proc/stb/lcd/symbol_timeshift"):
				if self.session.nav.RecordTimer.isRecording():
					f = open("/proc/stb/lcd/symbol_timeshift", "w")
					f.write("0")
					f.close()
			self.pts_starttime = time()
			self.save_timeshift_postaction = None
			self.ptsGetEventInfo()
			self.ptsCreateHardlink()
			self.__seekableStatusChanged()
		else:
			self.session.open(MessageBox, _("Timeshift not possible!"), MessageBox.TYPE_ERROR, timeout=5)
			self.pts_eventcount = 0

	def createTimeshiftFolder(self):
		timeshiftdir = resolveFilename(SCOPE_TIMESHIFT)
		if not pathExists(timeshiftdir):
			try:
				os.makedirs(timeshiftdir)
			except:
				print "[TimeShift] Failed to create %s !!" %timeshiftdir

	def restartTimeshift(self):
		self.activatePermanentTimeshift()
		Notifications.AddNotification(MessageBox, _("[TimeShift] Restarting Timeshift!"), MessageBox.TYPE_INFO, timeout=5)

	def saveTimeshiftEventPopup(self):
		filecount = 0
		entrylist = [(_("Current Event:") + " %s" % self.pts_curevent_name, "savetimeshift")]

		filelist = os.listdir(config.usage.timeshift_path.value)

		if filelist is not None:
			filelist.sort()

			for filename in filelist:
				if filename.startswith("pts_livebuffer") and not os.path.splitext(filename)[1]:
					# print "TRUE"
					statinfo = os.stat("%s%s" % (config.usage.timeshift_path.value,filename))
					if statinfo.st_mtime < (time()-5.0):
						# Get Event Info from meta file
						readmetafile = open("%s%s.meta" % (config.usage.timeshift_path.value,filename), "r")
						servicerefname = readmetafile.readline()[0:-1]
						eventname = readmetafile.readline()[0:-1]
						description = readmetafile.readline()[0:-1]
						begintime = readmetafile.readline()[0:-1]
						readmetafile.close()

						# Add Event to list
						filecount += 1
						entrylist.append((_("Record") + " #%s (%s): %s" % (filecount,strftime("%H:%M",localtime(int(begintime))),eventname), "%s" % filename))

			self.session.openWithCallback(self.recordQuestionCallback, ChoiceBox, title=_("Which event do you want to save permanently?"), list=entrylist)

	def saveTimeshiftActions(self, action=None, returnFunction=None):
		# print 'saveTimeshiftActions'
		# print 'action',action
		if action == "savetimeshift":
			self.SaveTimeshift()
		elif action == "savetimeshiftandrecord":
			if self.pts_curevent_end > time():
				self.SaveTimeshift(mergelater=True)
				self.ptsRecordCurrentEvent()
			else:
				self.SaveTimeshift()
		elif action == "noSave" or action == "no":
			config.timeshift.isRecording.value = False
			self.save_current_timeshift = False

		# Get rid of old timeshift file before E2 truncates its filesize
		if returnFunction is not None and action != "no":
			self.eraseTimeshiftFile()

		# print 'action returnFunction'
		returnFunction(action and action != "no")

	def SaveTimeshift(self, timeshiftfile=None, mergelater=False):
		# print 'SaveTimeshift'
		self.save_current_timeshift = False
		savefilename = None
		if timeshiftfile is not None:
			savefilename = timeshiftfile
		# print 'savefilename',savefilename
		if savefilename is None:
			# print 'TEST1'
			for filename in os.listdir(config.usage.timeshift_path.value):
				# print 'filename',filename
				if filename.startswith("timeshift.") and not filename.endswith(".del") and not filename.endswith(".copy"):
					statinfo = os.stat("%s%s" % (config.usage.timeshift_path.value,filename))
					if statinfo.st_mtime > (time()-5.0):
						savefilename=filename

		# print 'savefilename',savefilename
		if savefilename is None:
			Notifications.AddNotification(MessageBox, _("No Timeshift found to save as recording!"), MessageBox.TYPE_ERROR)
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
					if self.pts_starttime >= (time()-60):
						self.pts_starttime -= 60

					ptsfilename = "%s - %s - %s" % (strftime("%Y%m%d %H%M",localtime(self.pts_starttime)),self.pts_curevent_station,self.pts_curevent_name.replace("\n", ""))
					try:
						if config.usage.setup_level.index >= 2:
							if config.recording.filename_composition.value == "long" and self.pts_curevent_name.replace("\n", "") != pts_curevent_description.replace("\n", ""):
								ptsfilename = "%s - %s - %s - %s" % (strftime("%Y%m%d %H%M",localtime(self.pts_starttime)),self.pts_curevent_station,self.pts_curevent_name.replace("\n", ""),self.pts_curevent_description.replace("\n", ""))
							elif config.recording.filename_composition.value == "short":
								ptsfilename = "%s - %s" % (strftime("%Y%m%d",localtime(self.pts_starttime)),self.pts_curevent_name.replace("\n", ""))
					except Exception, errormsg:
						print "[TimeShift] Using default filename"

					if config.recording.ascii_filenames.value:
						ptsfilename = ASCIItranslit.legacyEncode(ptsfilename)

					# print 'ptsfilename',ptsfilename
					fullname = getRecordingFilename(ptsfilename,config.usage.default_path.value)
					# print 'fullname',fullname
					os.link("%s%s" % (config.usage.timeshift_path.value,savefilename), "%s.ts" % fullname)
					metafile = open("%s.ts.meta" % fullname, "w")
					metafile.write("%s\n%s\n%s\n%i\n%s" % (self.pts_curevent_servicerefname,self.pts_curevent_name.replace("\n", ""),self.pts_curevent_description.replace("\n", ""),int(self.pts_starttime),metamergestring))
					metafile.close()
					self.ptsCreateEITFile(fullname)
				elif timeshiftfile.startswith("pts_livebuffer"):
					# Save stored timeshift by creating hardlink to ts file
					readmetafile = open("%s%s.meta" % (config.usage.timeshift_path.value,timeshiftfile), "r")
					servicerefname = readmetafile.readline()[0:-1]
					eventname = readmetafile.readline()[0:-1]
					description = readmetafile.readline()[0:-1]
					begintime = readmetafile.readline()[0:-1]
					readmetafile.close()

					ptsfilename = "%s - %s - %s" % (strftime("%Y%m%d %H%M",localtime(int(begintime))),self.pts_curevent_station,eventname)
					try:
						if config.usage.setup_level.index >= 2:
							if config.recording.filename_composition.value == "long" and eventname != description:
								ptsfilename = "%s - %s - %s - %s" % (strftime("%Y%m%d %H%M",localtime(int(begintime))),self.pts_curevent_station,eventname,description)
							elif config.recording.filename_composition.value == "short":
								ptsfilename = "%s - %s" % (strftime("%Y%m%d",localtime(int(begintime))),eventname)
					except Exception, errormsg:
						print "[TimeShift] Using default filename"

					if config.recording.ascii_filenames.value:
						ptsfilename = ASCIItranslit.legacyEncode(ptsfilename)

					fullname=getRecordingFilename(ptsfilename,config.usage.default_path.value)
					os.link("%s%s" % (config.usage.timeshift_path.value,timeshiftfile),"%s.ts" % fullname)
					os.link("%s%s.meta" % (config.usage.timeshift_path.value,timeshiftfile),"%s.ts.meta" % fullname)
					if os.path.exists("%s%s.eit" % (config.usage.timeshift_path.value,timeshiftfile)):
						os.link("%s%s.eit" % (config.usage.timeshift_path.value,timeshiftfile),"%s.eit" % fullname)

					# Add merge-tag to metafile
					if mergelater:
						metafile = open("%s.ts.meta" % fullname, "a")
						metafile.write("%s\n" % metamergestring)
						metafile.close()

				# Create AP and SC Files when not merging
				if not mergelater:
					self.ptsCreateAPSCFiles(fullname+".ts")

			except Exception, errormsg:
				timeshift_saved = False
				timeshift_saveerror1 = errormsg

			# Hmpppf! Saving Timeshift via Hardlink-Method failed. Probably other device?
			# Let's try to copy the file in background now! This might take a while ...
			if not timeshift_saved:
				try:
					stat = os.statvfs(config.usage.default_path.value)
					freespace = stat.f_bfree / 1000 * stat.f_bsize / 1000
					randomint = randint(1, 999)

					if timeshiftfile is None:
						# Get Filesize for Free Space Check
						filesize = int(os.path.getsize("%s%s" % (config.usage.timeshift_path.value,savefilename)) / (1024*1024))

						# Save Current Event by copying it to the other device
						if filesize <= freespace:
							os.link("%s%s" % (config.usage.timeshift_path.value,savefilename), "%s%s.%s.copy" % (config.usage.timeshift_path.value,savefilename,randomint))
							copy_file = savefilename
							metafile = open("%s.ts.meta" % fullname, "w")
							metafile.write("%s\n%s\n%s\n%i\n%s" % (self.pts_curevent_servicerefname,self.pts_curevent_name.replace("\n", ""),self.pts_curevent_description.replace("\n", ""),int(self.pts_starttime),metamergestring))
							metafile.close()
							self.ptsCreateEITFile(fullname)
					elif timeshiftfile.startswith("pts_livebuffer"):
						# Get Filesize for Free Space Check
						filesize = int(os.path.getsize("%s%s" % (config.usage.timeshift_path.value, timeshiftfile)) / (1024*1024))

						# Save stored timeshift by copying it to the other device
						if filesize <= freespace:
							os.link("%s%s" % (config.usage.timeshift_path.value,timeshiftfile), "%s%s.%s.copy" % (config.usage.timeshift_path.value,timeshiftfile,randomint))
							copyfile("%s%s.meta" % (config.usage.timeshift_path.value,timeshiftfile),"%s.ts.meta" % fullname)
							if os.path.exists("%s%s.eit" % (config.usage.timeshift_path.value,timeshiftfile)):
								copyfile("%s%s.eit" % (config.usage.timeshift_path.value,timeshiftfile),"%s.eit" % fullname)
							copy_file = timeshiftfile

						# Add merge-tag to metafile
						if mergelater:
							metafile = open("%s.ts.meta" % fullname, "a")
							metafile.write("%s\n" % metamergestring)
							metafile.close()

					# Only copy file when enough disk-space available!
					if filesize <= freespace:
						timeshift_saved = True
						copy_file = copy_file+"."+str(randomint)

						# Get Event Info from meta file
						if os.path.exists("%s.ts.meta" % fullname):
							readmetafile = open("%s.ts.meta" % fullname, "r")
							servicerefname = readmetafile.readline()[0:-1]
							eventname = readmetafile.readline()[0:-1]
							readmetafile.close()
						else:
							eventname = ""

						JobManager.AddJob(CopyTimeshiftJob(self, "mv \"%s%s.copy\" \"%s.ts\"" % (config.usage.timeshift_path.value,copy_file,fullname), copy_file, fullname, eventname))
						if not Screens.Standby.inTryQuitMainloop and not Screens.Standby.inStandby and not mergelater and self.save_timeshift_postaction != "standby":
							Notifications.AddNotification(MessageBox, _("Saving timeshift as movie now. This might take a while!"), MessageBox.TYPE_INFO, timeout=5)
					else:
						timeshift_saved = False
						timeshift_saveerror1 = ""
						timeshift_saveerror2 = _("Not enough free Diskspace!\n\nFilesize: %sMB\nFree Space: %sMB\nPath: %s" % (filesize,freespace,config.usage.default_path.value))

				except Exception, errormsg:
					timeshift_saved = False
					timeshift_saveerror2 = errormsg

			if not timeshift_saved:
				config.timeshift.isRecording.value = False
				self.save_timeshift_postaction = None
				errormessage = str(timeshift_saveerror1) + "\n" + str(timeshift_saveerror2)
				Notifications.AddNotification(MessageBox, _("Timeshift save failed!")+"\n\n%s" % errormessage, MessageBox.TYPE_ERROR)
		# print 'SAVE COMPLETED'

	def ptsCleanTimeshiftFolder(self):
		# print '!!!!!!!!!!!!!!!!!!!!! ptsCleanTimeshiftFolder'
		if self.ptsCheckTimeshiftPath() is False or self.session.screen["Standby"].boolean is True:
			return

		for filename in os.listdir(config.usage.timeshift_path.value):
			if (filename.startswith("timeshift.") or filename.startswith("pts_livebuffer_")) and (filename.endswith(".del") is False and filename.endswith(".copy") is False):
				# print 'filename:',filename
				statinfo = os.stat("%s%s" % (config.usage.timeshift_path.value,filename)) # if no write for 3 sec = stranded timeshift
				if statinfo.st_mtime < (time()-3.0):
				# try:
					# print "[TimeShift] Erasing stranded timeshift %s" % filename
					self.BgFileEraser.erase("%s%s" % (config.usage.timeshift_path.value,filename))

					# Delete Meta and EIT File too
					# if filename.startswith("pts_livebuffer_") is True:
					# 	self.BgFileEraser.erase("%s%s.meta" % (config.usage.timeshift_path.value,filename))
					# 	self.BgFileEraser.erase("%s%s.eit" % (config.usage.timeshift_path.value,filename))
				# except:
				# 	print "[TimeShift] IO-Error while cleaning Timeshift Folder ..."

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
		except Exception, errormsg:
			Notifications.AddNotification(MessageBox, _("Getting Event Info failed!")+"\n\n%s" % errormsg, MessageBox.TYPE_ERROR, timeout=10)

		if event is not None:
			curEvent = parseEvent(event)
			self.pts_curevent_begin = int(curEvent[0])
			self.pts_curevent_end = int(curEvent[1])
			self.pts_curevent_name = curEvent[2]
			self.pts_curevent_description = curEvent[3]
			self.pts_curevent_eventid = curEvent[4]

	def ptsFrontpanelActions(self, action=None):
		if self.session.nav.RecordTimer.isRecording() or SystemInfo.get("NumFrontpanelLEDs", 0) == 0:
			return

		if action == "start":
			if os.path.exists("/proc/stb/fp/led_set_pattern"):
				f = open("/proc/stb/fp/led_set_pattern", "w")
				f.write("0xa7fccf7a")
				f.close()
			elif os.path.exists("/proc/stb/fp/led0_pattern"):
				f = open("/proc/stb/fp/led0_pattern", "w")
				f.write("0x55555555")
				f.close()
			if os.path.exists("/proc/stb/fp/led_pattern_speed"):
				f = open("/proc/stb/fp/led_pattern_speed", "w")
				f.write("20")
				f.close()
			elif os.path.exists("/proc/stb/fp/led_set_speed"):
				f = open("/proc/stb/fp/led_set_speed", "w")
				f.write("20")
				f.close()
		elif action == "stop":
			if os.path.exists("/proc/stb/fp/led_set_pattern"):
				f = open("/proc/stb/fp/led_set_pattern", "w")
				f.write("0")
				f.close()
			elif os.path.exists("/proc/stb/fp/led0_pattern"):
				f = open("/proc/stb/fp/led0_pattern", "w")
				f.write("0")
				f.close()

	def ptsCreateHardlink(self):
		# print 'ptsCreateHardlink'
		for filename in os.listdir(config.usage.timeshift_path.value):
			# if filename.startswith("timeshift") and not os.path.splitext(filename)[1]:
			if filename.startswith("timeshift") and not filename.endswith(".sc") and not filename.endswith(".del") and not filename.endswith(".copy"):
				if os.path.exists("%spts_livebuffer_%s.eit" % (config.usage.timeshift_path.value,self.pts_eventcount)):
					self.BgFileEraser.erase("%spts_livebuffer_%s.eit" % (config.usage.timeshift_path.value,self.pts_eventcount))
				if os.path.exists("%spts_livebuffer_%s.meta" % (config.usage.timeshift_path.value,self.pts_eventcount)):
					self.BgFileEraser.erase("%spts_livebuffer_%s.meta" % (config.usage.timeshift_path.value,self.pts_eventcount))
				if os.path.exists("%spts_livebuffer_%s" % (config.usage.timeshift_path.value,self.pts_eventcount)):
					self.BgFileEraser.erase("%spts_livebuffer_%s" % (config.usage.timeshift_path.value,self.pts_eventcount))
				if os.path.exists("%spts_livebuffer_%s.sc" % (config.usage.timeshift_path.value,self.pts_eventcount)):
					self.BgFileEraser.erase("%spts_livebuffer_%s.sc" % (config.usage.timeshift_path.value,self.pts_eventcount))
				try:
					# Create link to pts_livebuffer file
					os.link("%s%s" % (config.usage.timeshift_path.value,filename), "%spts_livebuffer_%s" % (config.usage.timeshift_path.value,self.pts_eventcount))
					os.link("%s%s.sc" % (config.usage.timeshift_path.value,filename), "%spts_livebuffer_%s.sc" % (config.usage.timeshift_path.value,self.pts_eventcount))

					# Create a Meta File
					metafile = open("%spts_livebuffer_%s.meta" % (config.usage.timeshift_path.value,self.pts_eventcount), "w")
					metafile.write("%s\n%s\n%s\n%i\n" % (self.pts_curevent_servicerefname,self.pts_curevent_name.replace("\n", ""),self.pts_curevent_description.replace("\n", ""),int(self.pts_starttime)))
					metafile.close()
				except Exception, errormsg:
					Notifications.AddNotification(MessageBox, _("Creating Hardlink to Timeshift file failed!")+"\n"+_("The Filesystem on your Timeshift-Device does not support hardlinks.\nMake sure it is formatted in EXT2 or EXT3!")+"\n\n%s" % errormsg, MessageBox.TYPE_ERROR)

				# Create EIT File
				self.ptsCreateEITFile("%spts_livebuffer_%s" % (config.usage.timeshift_path.value,self.pts_eventcount))

				# Permanent Recording Hack
				if config.timeshift.permanentrecording.value:
					try:
						fullname = getRecordingFilename("%s - %s - %s" % (strftime("%Y%m%d %H%M",localtime(self.pts_starttime)),self.pts_curevent_station,self.pts_curevent_name),config.usage.default_path.value)
						os.link("%s%s" % (config.usage.timeshift_path.value,filename), "%s.ts" % fullname)
						# Create a Meta File
						metafile = open("%s.ts.meta" % fullname, "w")
						metafile.write("%s\n%s\n%s\n%i\nautosaved\n" % (self.pts_curevent_servicerefname,self.pts_curevent_name.replace("\n", ""),self.pts_curevent_description.replace("\n", ""),int(self.pts_starttime)))
						metafile.close()
					except Exception, errormsg:
						print "[Timeshift] %s" % errormsg

	def ptsRecordCurrentEvent(self):
		recording = RecordTimerEntry(ServiceReference(self.session.nav.getCurrentlyPlayingServiceOrGroup()), time(), self.pts_curevent_end, self.pts_curevent_name, self.pts_curevent_description, self.pts_curevent_eventid, dirname = config.usage.default_path.value)
		recording.dontSave = True
		self.session.nav.RecordTimer.record(recording)
		self.recording.append(recording)

	def ptsMergeRecords(self):
		if self.session.nav.RecordTimer.isRecording():
			self.pts_mergeRecords_timer.start(120000, True)
			return

		ptsmergeSRC = ""
		ptsmergeDEST = ""
		ptsmergeeventname = ""
		ptsgetnextfile = False
		ptsfilemerged = False

		filelist = os.listdir(config.usage.default_path.value)

		if filelist is not None:
			filelist.sort()

		for filename in filelist:
			if filename.endswith(".meta"):
				# Get Event Info from meta file
				readmetafile = open("%s%s" % (config.usage.default_path.value,filename), "r")
				servicerefname = readmetafile.readline()[0:-1]
				eventname = readmetafile.readline()[0:-1]
				eventtitle = readmetafile.readline()[0:-1]
				eventtime = readmetafile.readline()[0:-1]
				eventtag = readmetafile.readline()[0:-1]
				readmetafile.close()

				if ptsgetnextfile:
					ptsgetnextfile = False
					ptsmergeSRC = filename[0:-5]

					if ASCIItranslit.legacyEncode(eventname) == ASCIItranslit.legacyEncode(ptsmergeeventname):
						# Copy EIT File
						if fileExists("%s%s.eit" % (config.usage.default_path.value, ptsmergeSRC[0:-3])):
							copyfile("%s%s.eit" % (config.usage.default_path.value, ptsmergeSRC[0:-3]),"%s%s.eit" % (config.usage.default_path.value, ptsmergeDEST[0:-3]))

						# Delete AP and SC Files
						if os.path.exists("%s%s.ap" % (config.usage.default_path.value, ptsmergeDEST)):
							self.BgFileEraser.erase("%s%s.ap" % (config.usage.default_path.value, ptsmergeDEST))
						if os.path.exists("%s%s.sc" % (config.usage.default_path.value, ptsmergeDEST)):
							self.BgFileEraser.erase("%s%s.sc" % (config.usage.default_path.value, ptsmergeDEST))

						# Add Merge Job to JobManager
						JobManager.AddJob(MergeTimeshiftJob(self, "cat \"%s%s\" >> \"%s%s\"" % (config.usage.default_path.value,ptsmergeSRC,config.usage.default_path.value,ptsmergeDEST), ptsmergeSRC, ptsmergeDEST, eventname))
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
					if fileExists("%s%s" % (config.usage.default_path.value,ptsmergeDEST)):
						statinfo = os.stat("%s%s" % (config.usage.default_path.value,ptsmergeDEST))
						if statinfo.st_mtime > (time()-10.0):
							self.pts_mergeRecords_timer.start(120000, True)
							return

					# Rewrite Meta File to get rid of pts_merge tag
					metafile = open("%s%s.meta" % (config.usage.default_path.value,ptsmergeDEST), "w")
					metafile.write("%s\n%s\n%s\n%i\n" % (servicerefname,eventname.replace("\n", ""),eventtitle.replace("\n", ""),int(eventtime)))
					metafile.close()

		# Merging failed :(
		if not ptsfilemerged and ptsgetnextfile:
			Notifications.AddNotification(MessageBox,_("[Timeshift] Merging records failed!"), MessageBox.TYPE_ERROR)

	def ptsCreateAPSCFiles(self, filename):
		if fileExists(filename, 'r'):
			if fileExists(filename+".meta", 'r'):
				# Get Event Info from meta file
				readmetafile = open(filename+".meta", "r")
				servicerefname = readmetafile.readline()[0:-1]
				eventname = readmetafile.readline()[0:-1]
				readmetafile.close()
			else:
				eventname = ""
			JobManager.AddJob(CreateAPSCFilesJob(self, "/usr/lib/enigma2/python/Components/createapscfiles \"%s\"" % filename, eventname))
		else:
			self.ptsSaveTimeshiftFinished()

	def ptsCreateEITFile(self, filename):
		if self.pts_curevent_eventid is not None:
			try:
				import Components.eitsave
				serviceref = ServiceReference(self.session.nav.getCurrentlyPlayingServiceOrGroup()).ref.toString()
				Components.eitsave.SaveEIT(serviceref, filename+".eit", self.pts_curevent_eventid, -1, -1)
			except Exception, errormsg:
				print "[Timeshift] %s" % errormsg

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
			os.system("echo \"\" > \"%s.pts.del\"" % (srcfile[0:-3]))
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
			Notifications.AddNotification(MessageBox, _("Timeshift saved to your harddisk!"), MessageBox.TYPE_INFO, timeout = 5)

	def ptsMergePostCleanUp(self):
		if self.session.nav.RecordTimer.isRecording() or len(JobManager.getPendingJobs()) >= 1:
			config.timeshift.isRecording.value = True
			self.pts_mergeCleanUp_timer.start(120000, True)
			return

		self.ptsFrontpanelActions("stop")
		config.timeshift.isRecording.value = False

		filelist = os.listdir(config.usage.default_path.value)
		for filename in filelist:
			if filename.endswith(".pts.del"):
				srcfile = config.usage.default_path.value + "/" + filename[0:-8] + ".ts"
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
		if (self.isSeekable() and self.timeshiftEnabled() or self.save_current_timeshift) and config.usage.check_timeshift.value:
			return True
		else:
			return False

	def ptsSeekPointerOK(self):
		if self.pvrStateDialog.has_key("PTSSeekPointer") and self.timeshiftEnabled() and self.isSeekable():
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
			jumptox = int(cur_pos[0]) - (int(self.pvrStateDialog["PTSSeekBack"].instance.position().x())+8)
			jumptoperc = round((jumptox / float(self.pvrStateDialog["PTSSeekBack"].instance.size().width())) * 100, 0)
			jumptotime = int((length / 100) * jumptoperc)
			jumptodiff = position - jumptotime

			self.doSeekRelative(-jumptodiff)
		else:
			return

	def ptsSeekPointerLeft(self):
		if self.pvrStateDialog.has_key("PTSSeekPointer") and self.pvrStateDialog.shown and self.timeshiftEnabled() and self.isSeekable():
			self.ptsMoveSeekPointer(direction="left")
		else:
			return

	def ptsSeekPointerRight(self):
		if self.pvrStateDialog.has_key("PTSSeekPointer") and  self.pvrStateDialog.shown and self.timeshiftEnabled() and self.isSeekable():
			self.ptsMoveSeekPointer(direction="right")
		else:
			return

	def ptsSeekPointerReset(self):
		if self.pvrStateDialog.has_key("PTSSeekPointer") and self.timeshiftEnabled():
			self.pvrStateDialog["PTSSeekPointer"].setPosition(int(self.pvrStateDialog["PTSSeekBack"].instance.position().x())+8,self.pvrStateDialog["PTSSeekPointer"].position[1])

	def ptsSeekPointerSetCurrentPos(self):
		if not self.pvrStateDialog.has_key("PTSSeekPointer") or not self.timeshiftEnabled() or not self.isSeekable():
			return

		position = self.ptsGetPosition()
		length = self.ptsGetLength()

		if length >= 1:
			tpixels = int((float(int((position*100)/length))/100)*self.pvrStateDialog["PTSSeekBack"].instance.size().width())
			self.pvrStateDialog["PTSSeekPointer"].setPosition(int(self.pvrStateDialog["PTSSeekBack"].instance.position().x())+8+tpixels, self.pvrStateDialog["PTSSeekPointer"].position[1])

	def ptsMoveSeekPointer(self, direction=None):
		if direction is None or not self.pvrStateDialog.has_key("PTSSeekPointer"):
			return
		isvalidjump = False
		cur_pos = self.pvrStateDialog["PTSSeekPointer"].position
		self.doShow()

		if direction == "left":
			minmaxval = int(self.pvrStateDialog["PTSSeekBack"].instance.position().x())+8
			movepixels = -15
			if cur_pos[0]+movepixels > minmaxval:
				isvalidjump = True
		elif direction == "right":
			minmaxval = int(self.pvrStateDialog["PTSSeekBack"].instance.size().width()*0.96)
			movepixels = 15
			if cur_pos[0]+movepixels < minmaxval:
				isvalidjump = True
		else:
			return 0

		if isvalidjump:
			self.pvrStateDialog["PTSSeekPointer"].setPosition(cur_pos[0]+movepixels,cur_pos[1])
		else:
			self.pvrStateDialog["PTSSeekPointer"].setPosition(minmaxval,cur_pos[1])

	def ptsTimeshiftFileChanged(self):
		# print '!!!!! ptsTimeshiftFileChanged'
		# Reset Seek Pointer
		self.ptsSeekPointerReset()

		# print 'self.pts_switchtolive',self.pts_switchtolive
		if self.pts_switchtolive:
			# print '!!!!! TEST1'
			self.pts_switchtolive = False
			return
		
		if self.pts_nextplaying:
			self.pts_currplaying = self.pts_nextplaying
		self.pts_nextplaying = self.pts_currplaying+1
		
		# Get next pts file ...
		# print '!!!!! TEST3'
		# print ("!!! %spts_livebuffer_%s" % (config.usage.timeshift_path.value,self.pts_nextplaying))
		if fileExists("%spts_livebuffer_%s" % (config.usage.timeshift_path.value,self.pts_nextplaying), 'r'):
			# print '!!!!! TEST4'
			self.ptsSetNextPlaybackFile("pts_livebuffer_%s" % self.pts_nextplaying)
			self.pts_switchtolive = False
		else:
			self.ptsSetNextPlaybackFile("")
			self.pts_switchtolive = True

	def ptsSetNextPlaybackFile(self, nexttsfile):
		# print '!!!!! ptsSetNextPlaybackFile'
		ts = self.getTimeshift()
		if ts is None:
			return
		# print ("!!! SET NextPlaybackFile%s%s" % (config.usage.timeshift_path.value,nexttsfile))
		ts.setNextPlaybackFile("%s%s" % (config.usage.timeshift_path.value,nexttsfile))

	def ptsSeekBackTimer(self):
		# print '!!!!! ptsSeekBackTimer RUN'
		self.doSeek(-90000*10) # seek ~10s before end
		self.setSeekState(self.SEEK_STATE_PAUSE)
		self.pts_StartSeekBackTimer.start(1000, True)

	def ptsStartSeekBackTimer(self):
		# print '!!!!! ptsStartSeekBackTimer RUN'
		if self.pts_lastseekspeed == 0:
			self.setSeekState(self.makeStateBackward(int(config.seek.enter_backward.value)))
		else:
			self.setSeekState(self.makeStateBackward(int(-self.pts_lastseekspeed)))

	def ptsCheckTimeshiftPath(self):
		if fileExists(config.usage.timeshift_path.value, 'w'):
			return True
		else:
			# Notifications.AddNotification(MessageBox, _("Could not activate Permanent-Timeshift!\nTimeshift-Path does not exist"), MessageBox.TYPE_ERROR, timeout=15)
			if self.pts_delay_timer.isActive():
				self.pts_delay_timer.stop()
			if self.pts_cleanUp_timer.isActive():
				# print 'CCCCCCCCCCCCCCCCCCCCCCCC'
				self.pts_cleanUp_timer.stop()
			return False

	def ptsTimerEntryStateChange(self, timer):
		# print 'ptsTimerEntryStateChange'
		if not config.timeshift.stopwhilerecording.value:
			return

		self.pts_record_running = self.session.nav.RecordTimer.isRecording()

		# Abort here when box is in standby mode
		if self.session.screen["Standby"].boolean is True:
			return

		# Stop Timeshift when Record started ...
		if timer.state == TimerEntry.StateRunning and self.timeshiftEnabled() and self.pts_record_running:
			if self.seekstate != self.SEEK_STATE_PLAY:
				self.setSeekState(self.SEEK_STATE_PLAY)

			if self.isSeekable():
				Notifications.AddNotification(MessageBox,_("Record started! Stopping timeshift now ..."), MessageBox.TYPE_INFO, timeout=5)

			self.switchToLive = False
			self.stopTimeshiftcheckTimeshiftRunningCallback(True)

		# Restart Timeshift when all records stopped
		if timer.state == TimerEntry.StateEnded and not self.timeshiftEnabled() and not self.pts_record_running:
			self.autostartPermanentTimeshift()

		# Restart Merge-Timer when all records stopped
		if timer.state == TimerEntry.StateEnded and self.pts_mergeRecords_timer.isActive():
			self.pts_mergeRecords_timer.stop()
			self.pts_mergeRecords_timer.start(15000, True)

		# Restart FrontPanel LED when still copying or merging files
		# ToDo: Only do this on PTS Events and not events from other jobs
		if timer.state == TimerEntry.StateEnded and (len(JobManager.getPendingJobs()) >= 1 or self.pts_mergeRecords_timer.isActive()):
			self.ptsFrontpanelActions("start")
			config.timeshift.isRecording.value = True

	def ptsLiveTVStatus(self):
		service = self.session.nav.getCurrentService()
		info = service and service.info()
		sTSID = info and info.getInfo(iServiceInformation.sTSID) or -1

		if sTSID is None or sTSID == -1:
			return False
		else:
			return True
