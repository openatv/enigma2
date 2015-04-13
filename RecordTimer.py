import os
from enigma import eEPGCache, getBestPlayableServiceReference, \
	eServiceReference, iRecordableService, quitMainloop, eActionMap, setPreferredTuner

from Components.config import config
from Components.UsageConfig import defaultMoviePath
from Components.TimerSanityCheck import TimerSanityCheck

from Screens.MessageBox import MessageBox
import Screens.Standby
import Screens.InfoBar
from Tools import Directories, Notifications, ASCIItranslit, Trashcan
from Tools.XMLTools import stringToXML

import timer
import xml.etree.cElementTree
import NavigationInstance
from ServiceReference import ServiceReference

from time import localtime, strftime, ctime, time
from bisect import insort
from sys import maxint

# ok, for descriptions etc we have:
# service reference  (to get the service name)
# name               (title)
# description        (description)
# event data         (ONLY for time adjustments etc.)


# parses an event, and gives out a (begin, end, name, duration, eit)-tuple.
# begin and end will be corrected
def parseEvent(ev, description = True):
	if description:
		name = ev.getEventName()
		description = ev.getShortDescription()
		if description == "":
			description = ev.getExtendedDescription()
	else:
		name = ""
		description = ""
	begin = ev.getBeginTime()
	end = begin + ev.getDuration()
	eit = ev.getEventId()
	begin -= config.recording.margin_before.value * 60
	end += config.recording.margin_after.value * 60
	return (begin, end, name, description, eit)

class AFTEREVENT:
	NONE = 0
	STANDBY = 1
	DEEPSTANDBY = 2
	AUTO = 3

def findSafeRecordPath(dirname):
	if not dirname:
		return None
	from Components import Harddisk
	dirname = os.path.realpath(dirname)
	mountpoint = Harddisk.findMountPoint(dirname)
	if mountpoint in ('/', '/media'):
		print '[RecordTimer] media is not mounted:', dirname
		return None
	if not os.path.isdir(dirname):
		try:
			os.makedirs(dirname)
		except Exception, ex:
			print '[RecordTimer] Failed to create dir "%s":' % dirname, ex
			return None
	return dirname

def checkForRecordings():
	if NavigationInstance.instance.getRecordings():
		return True
	rec_time = NavigationInstance.instance.RecordTimer.getNextTimerTime(isWakeup=True)
	return rec_time > 0 and (rec_time - time()) < 360

# please do not translate log messages
class RecordTimerEntry(timer.TimerEntry, object):
######### the following static methods and members are only in use when the box is in (soft) standby
	wasInStandby = False
	wasInDeepStandby = False
	receiveRecordEvents = False

	@staticmethod
	def keypress(key=None, flag=1):
		if flag and (RecordTimerEntry.wasInStandby or RecordTimerEntry.wasInDeepStandby):
			RecordTimerEntry.wasInStandby = False
			RecordTimerEntry.wasInDeepStandby = False
			eActionMap.getInstance().unbindAction('', RecordTimerEntry.keypress)

	@staticmethod
	def setWasInDeepStandby():
		RecordTimerEntry.wasInDeepStandby = True
		eActionMap.getInstance().bindAction('', -maxint - 1, RecordTimerEntry.keypress)

	@staticmethod
	def setWasInStandby():
		if not RecordTimerEntry.wasInStandby:
			if not RecordTimerEntry.wasInDeepStandby:
				eActionMap.getInstance().bindAction('', -maxint - 1, RecordTimerEntry.keypress)
			RecordTimerEntry.wasInDeepStandby = False
			RecordTimerEntry.wasInStandby = True

	@staticmethod
	def shutdown():
		quitMainloop(1)

	@staticmethod
	def staticGotRecordEvent(recservice, event):
		if event == iRecordableService.evEnd:
			print "RecordTimer.staticGotRecordEvent(iRecordableService.evEnd)"
			if not checkForRecordings():
				print "No recordings busy of sceduled within 6 minutes so shutdown"
				RecordTimerEntry.shutdown() # immediate shutdown
		elif event == iRecordableService.evStart:
			print "RecordTimer.staticGotRecordEvent(iRecordableService.evStart)"

	@staticmethod
	def stopTryQuitMainloop():
		print "RecordTimer.stopTryQuitMainloop"
		NavigationInstance.instance.record_event.remove(RecordTimerEntry.staticGotRecordEvent)
		RecordTimerEntry.receiveRecordEvents = False

	@staticmethod
	def TryQuitMainloop():
		if not RecordTimerEntry.receiveRecordEvents and Screens.Standby.inStandby:
			print "RecordTimer.TryQuitMainloop"
			NavigationInstance.instance.record_event.append(RecordTimerEntry.staticGotRecordEvent)
			RecordTimerEntry.receiveRecordEvents = True
			# send fake event.. to check if another recordings are running or
			# other timers start in a few seconds
			RecordTimerEntry.staticGotRecordEvent(None, iRecordableService.evEnd)
#################################################################

	def __init__(self, serviceref, begin, end, name, description, eit, disabled = False, justplay = False, afterEvent = AFTEREVENT.AUTO, checkOldTimers = False, dirname = None, tags = None, descramble = True, record_ecm = False, always_zap = False, zap_wakeup = "always", rename_repeat = True):
		timer.TimerEntry.__init__(self, int(begin), int(end))

		if checkOldTimers == True:
			if self.begin < time() - 1209600:
				self.begin = int(time())

		if self.end < self.begin:
			self.end = self.begin

		assert isinstance(serviceref, ServiceReference)

		if serviceref and serviceref.isRecordable():
			self.service_ref = serviceref
		else:
			self.service_ref = ServiceReference(None)
		self.eit = eit
		self.dontSave = False
		self.name = name
		self.description = description
		self.disabled = disabled
		self.timer = None
		self.__record_service = None
		self.start_prepare = 0
		self.justplay = justplay
		self.always_zap = always_zap
		self.zap_wakeup = zap_wakeup
		self.afterEvent = afterEvent
		self.dirname = dirname
		self.dirnameHadToFallback = False
		self.autoincrease = False
		self.autoincreasetime = 3600 * 24 # 1 day
		self.tags = tags or []
		self.descramble = descramble
		self.record_ecm = record_ecm
		self.rename_repeat = rename_repeat
		self.needChangePriorityFrontend = config.usage.recording_frontend_priority.value != "-2" and config.usage.recording_frontend_priority.value != config.usage.frontend_priority.value
		self.change_frontend = False
		self.InfoBarInstance = Screens.InfoBar.InfoBar.instance
		self.ts_dialog = None
		self.log_entries = []
		self.resetState()

	def __repr__(self):
		return "RecordTimerEntry(name=%s, begin=%s, serviceref=%s, justplay=%s)" % (self.name, ctime(self.begin), self.service_ref, self.justplay)

	def log(self, code, msg):
		self.log_entries.append((int(time()), code, msg))
		print "[TIMER]", msg

	def calculateFilename(self, name=None):
		service_name = self.service_ref.getServiceName()
		begin_date = strftime("%Y%m%d %H%M", localtime(self.begin))
		name = name or self.name
		filename = begin_date + " - " + service_name
		if name:
			if config.recording.filename_composition.value == "short":
				filename = strftime("%Y%m%d", localtime(self.begin)) + " - " + name
			elif config.recording.filename_composition.value == "long":
				filename += " - " + name + " - " + self.description
			else:
				filename += " - " + name # standard

		if config.recording.ascii_filenames.value:
			filename = ASCIItranslit.legacyEncode(filename)
		if not self.dirname:
			dirname = findSafeRecordPath(defaultMoviePath())
		else:
			dirname = findSafeRecordPath(self.dirname)
			if dirname is None:
				dirname = findSafeRecordPath(defaultMoviePath())
				self.dirnameHadToFallback = True
		if not dirname:
			return None
		self.Filename = Directories.getRecordingFilename(filename, dirname)
		self.log(0, "Filename calculated as: '%s'" % self.Filename)
		return self.Filename

	def tryPrepare(self):
		if self.justplay:
			return True
		else:
			if not self.calculateFilename():
				self.do_backoff()
				self.start_prepare = time() + self.backoff
				return False
			rec_ref = self.service_ref and self.service_ref.ref
			if rec_ref and rec_ref.flags & eServiceReference.isGroup:
				rec_ref = getBestPlayableServiceReference(rec_ref, eServiceReference())
				if not rec_ref:
					self.log(1, "'get best playable service for group... record' failed")
					return False
			self.setRecordingPreferredTuner()
			self.record_service = rec_ref and NavigationInstance.instance.recordService(rec_ref)

			if not self.record_service:
				self.log(1, "'record service' failed")
				self.setRecordingPreferredTuner(setdefault=True)
				return False

			name = self.name
			description = self.description
			if self.repeated:
				epgcache = eEPGCache.getInstance()
				queryTime=self.begin+(self.end-self.begin)/2
				evt = epgcache.lookupEventTime(rec_ref, queryTime)
				if evt:
					if self.rename_repeat:
						event_description = evt.getShortDescription()
						if not event_description:
							event_description = evt.getExtendedDescription()
						if event_description and event_description != description:
							description = event_description
						event_name = evt.getEventName()
						if event_name and event_name != name:
							name = event_name
							if not self.calculateFilename(event_name):
								self.do_backoff()
								self.start_prepare = time() + self.backoff
								return False
					event_id = evt.getEventId()
				else:
					event_id = -1
			else:
				event_id = self.eit
				if event_id is None:
					event_id = -1

			prep_res=self.record_service.prepare(self.Filename + ".ts", self.begin, self.end, event_id, name.replace("\n", ""), description.replace("\n", ""), ' '.join(self.tags), bool(self.descramble), bool(self.record_ecm))
			if prep_res:
				if prep_res == -255:
					self.log(4, "failed to write meta information")
				else:
					self.log(2, "'prepare' failed: error %d" % prep_res)

				# we must calc nur start time before stopRecordService call because in Screens/Standby.py TryQuitMainloop tries to get
				# the next start time in evEnd event handler...
				self.do_backoff()
				self.start_prepare = time() + self.backoff

				NavigationInstance.instance.stopRecordService(self.record_service)
				self.record_service = None
				self.setRecordingPreferredTuner(setdefault=True)
				return False
			return True

	def do_backoff(self):
		if self.backoff == 0:
			self.backoff = 5
		else:
			self.backoff *= 2
			if self.backoff > 100:
				self.backoff = 100
		self.log(10, "backoff: retry in %d seconds" % self.backoff)

	def activate(self):
		next_state = self.state + 1
		self.log(5, "activating state %d" % next_state)

		if next_state == 1:
			if self.always_zap:
				if Screens.Standby.inStandby:
					self.log(5, "wakeup and zap to recording service")
					RecordTimerEntry.setWasInStandby()
					#set service to zap after standby
					Screens.Standby.inStandby.prev_running_service = self.service_ref.ref
					Screens.Standby.inStandby.paused_service = None
					#wakeup standby
					Screens.Standby.inStandby.Power()
				else:
					if RecordTimerEntry.wasInDeepStandby:
						RecordTimerEntry.setWasInStandby()
					cur_zap_ref = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
					if cur_zap_ref and not cur_zap_ref.getPath():# we do not zap away if it is no live service
						if self.checkingTimeshiftRunning():
							if self.ts_dialog is None:
								self.openChoiceActionBeforeZap()
						else:
							Notifications.AddNotification(MessageBox, _("In order to record a timer, the TV was switched to the recording service!\n"), type=MessageBox.TYPE_INFO, timeout=20)
							self.setRecordingPreferredTuner()
							self.failureCB(True)
							self.log(5, "zap to recording service")

		if next_state == self.StatePrepared:
			if self.tryPrepare():
				self.log(6, "prepare ok, waiting for begin")
				# create file to "reserve" the filename
				# because another recording at the same time on another service can try to record the same event
				# i.e. cable / sat.. then the second recording needs an own extension... when we create the file
				# here than calculateFilename is happy
				if not self.justplay:
					open(self.Filename + ".ts", "w").close()
					# Give the Trashcan a chance to clean up
					try:
						Trashcan.instance.cleanIfIdle(self.Filename)
					except Exception, e:
						 print "[TIMER] Failed to call Trashcan.instance.cleanIfIdle()"
						 print "[TIMER] Error:", e
				# fine. it worked, resources are allocated.
				self.next_activation = self.begin
				self.backoff = 0
				return True

			self.log(7, "prepare failed")
			if self.first_try_prepare or (self.ts_dialog is not None and not self.checkingTimeshiftRunning()):
				self.first_try_prepare = False
				cur_ref = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
				if cur_ref and not cur_ref.getPath():
					if self.always_zap:
						return False
					if Screens.Standby.inStandby:
						self.setRecordingPreferredTuner()
						self.failureCB(True)
					elif self.checkingTimeshiftRunning():
						if self.ts_dialog is None:
							self.openChoiceActionBeforeZap()
					elif not config.recording.asktozap.value:
						self.log(8, "asking user to zap away")
						Notifications.AddNotificationWithCallback(self.failureCB, MessageBox, _("A timer failed to record!\nDisable TV and try again?\n"), timeout=20, default=True)
					else: # zap without asking
						self.log(9, "zap without asking")
						Notifications.AddNotification(MessageBox, _("In order to record a timer, the TV was switched to the recording service!\n"), type=MessageBox.TYPE_INFO, timeout=20)
						self.setRecordingPreferredTuner()
						self.failureCB(True)
				elif cur_ref:
					self.log(8, "currently running service is not a live service.. so stop it makes no sense")
				else:
					self.log(8, "currently no service running... so we dont need to stop it")
			return False

		elif next_state == self.StateRunning:
			# if this timer has been cancelled, just go to "end" state.
			if self.cancelled:
				return True
			if self.justplay:
				if Screens.Standby.inStandby:
					if RecordTimerEntry.wasInDeepStandby and self.zap_wakeup in ("always", "from_deep_standby") or self.zap_wakeup in ("always", "from_standby"):
						self.log(11, "wakeup and zap")
						RecordTimerEntry.setWasInStandby()
						#set service to zap after standby
						Screens.Standby.inStandby.prev_running_service = self.service_ref.ref
						Screens.Standby.inStandby.paused_service = None
						#wakeup standby
						Screens.Standby.inStandby.Power()
				else:
					if RecordTimerEntry.wasInDeepStandby:
						RecordTimerEntry.setWasInStandby()
					if self.checkingTimeshiftRunning():
						if self.ts_dialog is None:
							self.openChoiceActionBeforeZap()
					else:
						self.log(11, "zapping")
						NavigationInstance.instance.playService(self.service_ref.ref)
				return True
			else:
				self.log(11, "start recording")

				if RecordTimerEntry.wasInDeepStandby:
					RecordTimerEntry.keypress()
					if Screens.Standby.inStandby: #In case some plugin did put the receiver already in standby
						config.misc.standbyCounter.value = 0
					else:
						Notifications.AddNotification(Screens.Standby.Standby, StandbyCounterIncrease=False)
				record_res = self.record_service.start()
				self.setRecordingPreferredTuner(setdefault=True)
				if record_res:
					self.log(13, "start record returned %d" % record_res)
					self.do_backoff()
					# retry
					self.begin = time() + self.backoff
					return False

				# Tell the trashcan we started recording. The trashcan gets events,
				# but cannot tell what the associated path is.
				Trashcan.instance.markDirty(self.Filename)

				return True

		elif next_state == self.StateEnded:
			old_end = self.end
			self.ts_dialog = None
			if self.setAutoincreaseEnd():
				self.log(12, "autoincrase recording %d minute(s)" % int((self.end - old_end)/60))
				self.state -= 1
				return True
			self.log(12, "stop recording")
			if not self.justplay:
				NavigationInstance.instance.stopRecordService(self.record_service)
				self.record_service = None
			if not checkForRecordings():
				if self.afterEvent == AFTEREVENT.DEEPSTANDBY or self.afterEvent == AFTEREVENT.AUTO and (Screens.Standby.inStandby or RecordTimerEntry.wasInStandby) and not config.misc.standbyCounter.value:
					if not Screens.Standby.inTryQuitMainloop:
						if Screens.Standby.inStandby:
							RecordTimerEntry.TryQuitMainloop()
						else:
							Notifications.AddNotificationWithCallback(self.sendTryQuitMainloopNotification, MessageBox, _("A finished record timer wants to shut down\nyour receiver. Shutdown now?"), timeout=20, default=True)
				elif self.afterEvent == AFTEREVENT.STANDBY or self.afterEvent == AFTEREVENT.AUTO and RecordTimerEntry.wasInStandby:
					if not Screens.Standby.inStandby:
						Notifications.AddNotificationWithCallback(self.sendStandbyNotification, MessageBox, _("A finished record timer wants to set your\nreceiver to standby. Do that now?"), timeout=20, default=True)
				else:
					RecordTimerEntry.keypress()
			return True

	def setAutoincreaseEnd(self, entry = None):
		if not self.autoincrease:
			return False
		if entry is None:
			new_end =  int(time()) + self.autoincreasetime
		else:
			new_end = entry.begin - 30

		dummyentry = RecordTimerEntry(self.service_ref, self.begin, new_end, self.name, self.description, self.eit, disabled=True, justplay = self.justplay, afterEvent = self.afterEvent, dirname = self.dirname, tags = self.tags)
		dummyentry.disabled = self.disabled
		timersanitycheck = TimerSanityCheck(NavigationInstance.instance.RecordTimer.timer_list, dummyentry)
		if not timersanitycheck.check():
			simulTimerList = timersanitycheck.getSimulTimerList()
			if simulTimerList is not None and len(simulTimerList) > 1:
				new_end = simulTimerList[1].begin
				new_end -= 30				# 30 Sekunden Prepare-Zeit lassen
		if new_end <= time():
			return False
		self.end = new_end
		return True

	def setRecordingPreferredTuner(self, setdefault=False):
		if self.needChangePriorityFrontend:
			elem = None
			if not self.change_frontend and not setdefault:
				elem = config.usage.recording_frontend_priority.value
				self.change_frontend = True
			elif self.change_frontend and setdefault:
				elem = config.usage.frontend_priority.value
				self.change_frontend = False
			if elem is not None:
				setPreferredTuner(int(elem))

	def checkingTimeshiftRunning(self):
		return config.usage.check_timeshift.value and self.InfoBarInstance and self.InfoBarInstance.timeshiftEnabled() and self.InfoBarInstance.timeshift_was_activated

	def openChoiceActionBeforeZap(self):
		if self.ts_dialog is None:
			type = _("record")
			if self.justplay:
				type = _("zap")
			elif self.always_zap:
				type = _("zap and record")
			message = _("You must switch to the service %s (%s - '%s')!\n") % (type, self.service_ref.getServiceName(), self.name)
			if self.repeated:
				message += _("Attention, this is repeated timer!\n")
			message += _("Timeshift is running. Select an action.\n")
			choice = [(_("Zap"), "zap"), (_("Don't zap and disable timer"), "disable"), (_("Don't zap and remove timer"), "remove")]
			if not self.InfoBarInstance.save_timeshift_file:
				choice.insert(1, (_("Save timeshift in movie dir and zap"), "save_movie"))
				if self.InfoBarInstance.timeshiftActivated():
					choice.insert(0, (_("Save timeshift and zap"), "save"))
				else:
					choice.insert(1, (_("Save timeshift and zap"), "save"))
			else:
				message += _("Reminder, you have chosen to save timeshift file.")
			#if self.justplay or self.always_zap:
			#	choice.insert(2, (_("Don't zap"), "continue"))
			choice.insert(2, (_("Don't zap"), "continue"))
			def zapAction(choice):
				start_zap = True
				if choice:
					if choice in ("zap", "save", "save_movie"):
						self.log(8, "zap to recording service")
						if choice in ("save", "save_movie"):
							ts = self.InfoBarInstance.getTimeshift()
							if ts and ts.isTimeshiftEnabled():
								if choice =="save_movie":
									self.InfoBarInstance.save_timeshift_in_movie_dir = True
								self.InfoBarInstance.save_timeshift_file = True
								ts.saveTimeshiftFile()
								del ts
								self.InfoBarInstance.saveTimeshiftFiles()
					elif choice == "disable":
						self.disable()
						NavigationInstance.instance.RecordTimer.timeChanged(self)
						start_zap = False
						self.log(8, "zap canceled by the user, timer disabled")
					elif choice == "remove":
						start_zap = False
						self.afterEvent = AFTEREVENT.NONE
						NavigationInstance.instance.RecordTimer.removeEntry(self)
						self.log(8, "zap canceled by the user, timer removed")
					elif choice == "continue":
						if self.justplay:
							self.end = self.begin
						start_zap = False
						self.log(8, "zap canceled by the user")
				if start_zap:
					if not self.justplay:
						self.setRecordingPreferredTuner()
						self.failureCB(True)
					else:
						self.log(8, "zapping")
						NavigationInstance.instance.playService(self.service_ref.ref)
			self.ts_dialog = self.InfoBarInstance.session.openWithCallback(zapAction, MessageBox, message, simple=True, list=choice, timeout=20)

	def sendStandbyNotification(self, answer):
		RecordTimerEntry.keypress()
		if answer:
			Notifications.AddNotification(Screens.Standby.Standby)

	def sendTryQuitMainloopNotification(self, answer):
		RecordTimerEntry.keypress()
		if answer:
			Notifications.AddNotification(Screens.Standby.TryQuitMainloop, 1)

	def getNextActivation(self):
		if self.state == self.StateEnded:
			return self.end

		next_state = self.state + 1

		return {self.StatePrepared: self.start_prepare,
				self.StateRunning: self.begin,
				self.StateEnded: self.end }[next_state]

	def failureCB(self, answer):
		self.ts_dialog = None
		if answer == True:
			self.log(13, "ok, zapped away")
			#NavigationInstance.instance.stopUserServices()
			NavigationInstance.instance.playService(self.service_ref.ref)
		else:
			self.log(14, "user didn't want to zap away, record will probably fail")

	def timeChanged(self):
		old_prepare = self.start_prepare
		self.start_prepare = self.begin - self.prepare_time
		self.backoff = 0

		if int(old_prepare) != int(self.start_prepare):
			self.log(15, "record time changed, start prepare is now: %s" % ctime(self.start_prepare))

	def gotRecordEvent(self, record, event):
		# TODO: this is not working (never true), please fix. (comparing two swig wrapped ePtrs)
		if self.__record_service.__deref__() != record.__deref__():
			return
		self.log(16, "record event %d" % event)
		if event == iRecordableService.evRecordWriteError:
			print "WRITE ERROR on recording, disk full?"
			# show notification. the 'id' will make sure that it will be
			# displayed only once, even if more timers are failing at the
			# same time. (which is very likely in case of disk fullness)
			Notifications.AddPopup(text = _("Write error while recording. Disk full?\n"), type = MessageBox.TYPE_ERROR, timeout = 0, id = "DiskFullMessage")
			# ok, the recording has been stopped. we need to properly note
			# that in our state, with also keeping the possibility to re-try.
			# TODO: this has to be done.
		elif event == iRecordableService.evStart:
			text = _("A record has been started:\n%s") % self.name
			notify = config.usage.show_message_when_recording_starts.value and not Screens.Standby.inStandby and self.InfoBarInstance and self.InfoBarInstance.execing
			if self.dirnameHadToFallback:
				text = '\n'.join((text, _("Please note that the previously selected media could not be accessed and therefore the default directory is being used instead.")))
				notify = True
			if notify:
				Notifications.AddPopup(text = text, type = MessageBox.TYPE_INFO, timeout = 3)
		elif event == iRecordableService.evRecordAborted:
			NavigationInstance.instance.RecordTimer.removeEntry(self)

	# we have record_service as property to automatically subscribe to record service events
	def setRecordService(self, service):
		if self.__record_service is not None:
			print "[remove callback]"
			NavigationInstance.instance.record_event.remove(self.gotRecordEvent)

		self.__record_service = service

		if self.__record_service is not None:
			print "[add callback]"
			NavigationInstance.instance.record_event.append(self.gotRecordEvent)

	record_service = property(lambda self: self.__record_service, setRecordService)

def createTimer(xml):
	begin = int(xml.get("begin"))
	end = int(xml.get("end"))
	serviceref = ServiceReference(xml.get("serviceref").encode("utf-8"))
	description = xml.get("description").encode("utf-8")
	repeated = xml.get("repeated").encode("utf-8")
	rename_repeat = long(xml.get("rename_repeat") or "1")
	disabled = long(xml.get("disabled") or "0")
	justplay = long(xml.get("justplay") or "0")
	always_zap = long(xml.get("always_zap") or "0")
	zap_wakeup = str(xml.get("zap_wakeup") or "always")
	afterevent = str(xml.get("afterevent") or "nothing")
	afterevent = {
		"nothing": AFTEREVENT.NONE,
		"standby": AFTEREVENT.STANDBY,
		"deepstandby": AFTEREVENT.DEEPSTANDBY,
		"auto": AFTEREVENT.AUTO
		}[afterevent]
	eit = xml.get("eit")
	if eit and eit != "None":
		eit = long(eit)
	else:
		eit = None
	location = xml.get("location")
	if location and location != "None":
		location = location.encode("utf-8")
	else:
		location = None
	tags = xml.get("tags")
	if tags and tags != "None":
		tags = tags.encode("utf-8").split(' ')
	else:
		tags = None
	descramble = int(xml.get("descramble") or "1")
	record_ecm = int(xml.get("record_ecm") or "0")

	name = xml.get("name").encode("utf-8")
	#filename = xml.get("filename").encode("utf-8")
	entry = RecordTimerEntry(serviceref, begin, end, name, description, eit, disabled, justplay, afterevent, dirname = location, tags = tags, descramble = descramble, record_ecm = record_ecm, always_zap = always_zap, zap_wakeup = zap_wakeup, rename_repeat = rename_repeat)
	entry.repeated = int(repeated)

	for l in xml.findall("log"):
		time = int(l.get("time"))
		code = int(l.get("code"))
		msg = l.text.strip().encode("utf-8")
		entry.log_entries.append((time, code, msg))

	return entry

class RecordTimer(timer.Timer):
	def __init__(self):
		timer.Timer.__init__(self)

		self.Filename = Directories.resolveFilename(Directories.SCOPE_CONFIG, "timers.xml")

		try:
			self.loadTimer()
		except IOError:
			print "unable to load timers from file!"

	def doActivate(self, w):
		# when activating a timer which has already passed,
		# simply abort the timer. don't run trough all the stages.
		if w.shouldSkip():
			w.state = RecordTimerEntry.StateEnded
		else:
			# when active returns true, this means "accepted".
			# otherwise, the current state is kept.
			# the timer entry itself will fix up the delay then.
			if w.activate():
				w.state += 1

		self.timer_list.remove(w)

		# did this timer reached the last state?
		if w.state < RecordTimerEntry.StateEnded:
			# no, sort it into active list
			insort(self.timer_list, w)
		else:
			# yes. Process repeated, and re-add.
			if w.repeated:
				w.processRepeated()
				w.state = RecordTimerEntry.StateWaiting
				w.first_try_prepare = True
				self.addTimerEntry(w)
			else:
				# Remove old timers as set in config
				self.cleanupDaily(config.recording.keep_timers.value)
				insort(self.processed_timers, w)
		self.stateChanged(w)

	def isRecording(self):
		for timer in self.timer_list:
			if timer.isRunning() and not timer.justplay:
				return True
		return False

	def loadTimer(self):
		# TODO: PATH!
		if not Directories.fileExists(self.Filename):
			return
		try:
			doc = xml.etree.cElementTree.parse(self.Filename)
		except SyntaxError:
			from Tools.Notifications import AddPopup
			from Screens.MessageBox import MessageBox

			AddPopup(_("The timer file (timers.xml) is corrupt and could not be loaded."), type = MessageBox.TYPE_ERROR, timeout = 0, id = "TimerLoadFailed")

			print "timers.xml failed to load!"
			try:
				import os
				os.rename(self.Filename, self.Filename + "_old")
			except (IOError, OSError):
				print "renaming broken timer failed"
			return
		except IOError:
			print "timers.xml not found!"
			return

		root = doc.getroot()

		# put out a message when at least one timer overlaps
		checkit = True
		for timer in root.findall("timer"):
			newTimer = createTimer(timer)
			if (self.record(newTimer, True, dosave=False) is not None) and (checkit == True):
				from Tools.Notifications import AddPopup
				from Screens.MessageBox import MessageBox
				AddPopup(_("Timer overlap in timers.xml detected!\nPlease recheck it!"), type = MessageBox.TYPE_ERROR, timeout = 0, id = "TimerLoadFailed")
				checkit = False # at moment it is enough when the message is displayed one time

	def saveTimer(self):
		#root_element = xml.etree.cElementTree.Element('timers')
		#root_element.text = "\n"

		#for timer in self.timer_list + self.processed_timers:
			# some timers (instant records) don't want to be saved.
			# skip them
			#if timer.dontSave:
				#continue
			#t = xml.etree.cElementTree.SubElement(root_element, 'timers')
			#t.set("begin", str(int(timer.begin)))
			#t.set("end", str(int(timer.end)))
			#t.set("serviceref", str(timer.service_ref))
			#t.set("repeated", str(timer.repeated))
			#t.set("name", timer.name)
			#t.set("description", timer.description)
			#t.set("afterevent", str({
			#	AFTEREVENT.NONE: "nothing",
			#	AFTEREVENT.STANDBY: "standby",
			#	AFTEREVENT.DEEPSTANDBY: "deepstandby",
			#	AFTEREVENT.AUTO: "auto"}))
			#if timer.eit is not None:
			#	t.set("eit", str(timer.eit))
			#if timer.dirname is not None:
			#	t.set("location", str(timer.dirname))
			#t.set("disabled", str(int(timer.disabled)))
			#t.set("justplay", str(int(timer.justplay)))
			#t.text = "\n"
			#t.tail = "\n"

			#for time, code, msg in timer.log_entries:
				#l = xml.etree.cElementTree.SubElement(t, 'log')
				#l.set("time", str(time))
				#l.set("code", str(code))
				#l.text = str(msg)
				#l.tail = "\n"

		#doc = xml.etree.cElementTree.ElementTree(root_element)
		#doc.write(self.Filename)

		list = []

		list.append('<?xml version="1.0" ?>\n')
		list.append('<timers>\n')

		for timer in self.timer_list + self.processed_timers:
			if timer.dontSave:
				continue

			list.append('<timer')
			list.append(' begin="' + str(int(timer.begin)) + '"')
			list.append(' end="' + str(int(timer.end)) + '"')
			list.append(' serviceref="' + stringToXML(str(timer.service_ref)) + '"')
			list.append(' repeated="' + str(int(timer.repeated)) + '"')
			list.append(' name="' + str(stringToXML(timer.name)) + '"')
			list.append(' description="' + str(stringToXML(timer.description)) + '"')
			list.append(' afterevent="' + str(stringToXML({
				AFTEREVENT.NONE: "nothing",
				AFTEREVENT.STANDBY: "standby",
				AFTEREVENT.DEEPSTANDBY: "deepstandby",
				AFTEREVENT.AUTO: "auto"
				}[timer.afterEvent])) + '"')
			if timer.eit is not None:
				list.append(' eit="' + str(timer.eit) + '"')
			if timer.dirname is not None:
				list.append(' location="' + str(stringToXML(timer.dirname)) + '"')
			if timer.tags is not None:
				list.append(' tags="' + str(stringToXML(' '.join(timer.tags))) + '"')
			list.append(' disabled="' + str(int(timer.disabled)) + '"')
			list.append(' justplay="' + str(int(timer.justplay)) + '"')
			list.append(' always_zap="' + str(int(timer.always_zap)) + '"')
			list.append(' zap_wakeup="' + str(timer.zap_wakeup) + '"')
			list.append(' rename_repeat="' + str(int(timer.rename_repeat)) + '"')
			list.append(' descramble="' + str(int(timer.descramble)) + '"')
			list.append(' record_ecm="' + str(int(timer.record_ecm)) + '"')
			list.append('>\n')

			if config.recording.debug.value:
				for time, code, msg in timer.log_entries:
					list.append('<log')
					list.append(' code="' + str(code) + '"')
					list.append(' time="' + str(time) + '"')
					list.append('>')
					list.append(str(stringToXML(msg)))
					list.append('</log>\n')

			list.append('</timer>\n')

		list.append('</timers>\n')

		file = open(self.Filename + ".writing", "w")
		for x in list:
			file.write(x)
		file.flush()

		import os
		os.fsync(file.fileno())
		file.close()
		os.rename(self.Filename + ".writing", self.Filename)

	def getNextZapTime(self, isWakeup=False):
		now = time()
		for timer in self.timer_list:
			if not timer.justplay or timer.begin < now or isWakeup and timer.zap_wakeup in ("from_standby", "never"):
				continue
			return timer.begin
		return -1

	def getNextRecordingTime(self):
		now = time()
		for timer in self.timer_list:
			next_act = timer.getNextActivation()
			if timer.justplay or next_act < now:
				continue
			return next_act
		return -1

	def getNextTimerTime(self, isWakeup=False):
		now = time()
		for timer in self.timer_list:
			next_act = timer.getNextActivation()
			if next_act < now or isWakeup and timer.justplay and timer.zap_wakeup in ("from_standby", "never"):
				continue
			return next_act
		return -1

	def isNextRecordAfterEventActionAuto(self):
		now = time()
		t = None
		for timer in self.timer_list:
			if timer.justplay or timer.begin < now:
				continue
			if t is None or t.begin == timer.begin:
				t = timer
				if t.afterEvent == AFTEREVENT.AUTO:
					return True
		return False

	def record(self, entry, ignoreTSC=False, dosave=True): # wird von loadTimer mit dosave=False aufgerufen
		timersanitycheck = TimerSanityCheck(self.timer_list,entry)
		if not timersanitycheck.check():
			if ignoreTSC != True:
				print "timer conflict detected!"
				print timersanitycheck.getSimulTimerList()
				return timersanitycheck.getSimulTimerList()
			else:
				print "ignore timer conflict"
		elif timersanitycheck.doubleCheck():
			print "ignore double timer"
			return None
		entry.timeChanged()
		print "[Timer] Record " + str(entry)
		entry.Timer = self
		self.addTimerEntry(entry)
		if dosave:
			self.saveTimer()
		return None

	def isInRepeatTimer(self, timer, event):
		time_match = 0
		is_editable = False
		begin = event.getBeginTime()
		duration = event.getDuration()
		end = begin + duration
		timer_end = timer.end
		if timer.disabled and timer.isRunning():
			if begin < timer.begin <= end or timer.begin <= begin <= timer_end:
				return True
			else:
				return False
		if timer.justplay and (timer_end - timer.begin) <= 1:
			timer_end += 60
		bt = localtime(begin)
		bday = bt.tm_wday
		begin2 = 1440 + bt.tm_hour * 60 + bt.tm_min
		end2 = begin2 + duration / 60
		xbt = localtime(timer.begin)
		xet = localtime(timer_end)
		offset_day = False
		checking_time = timer.begin < begin or begin <= timer.begin <= end
		if xbt.tm_yday != xet.tm_yday:
			oday = bday - 1
			if oday == -1: oday = 6
			offset_day = timer.repeated & (1 << oday)
		xbegin = 1440 + xbt.tm_hour * 60 + xbt.tm_min
		xend = xbegin + ((timer_end - timer.begin) / 60)
		if xend < xbegin:
			xend += 1440
		if timer.repeated & (1 << bday) and checking_time:
			if begin2 < xbegin <= end2:
				if xend < end2:
					# recording within event
					time_match = (xend - xbegin) * 60
					is_editable = True
				else:
					# recording last part of event
					time_match = (end2 - xbegin) * 60
					summary_end = (xend - end2) * 60
					is_editable = not summary_end and True or time_match >= summary_end
			elif xbegin <= begin2 <= xend:
				if xend < end2:
					# recording first part of event
					time_match = (xend - begin2) * 60
					summary_end = (begin2 - xbegin) * 60
					is_editable = not summary_end and True or time_match >= summary_end
				else:
					# recording whole event
					time_match = (end2 - begin2) * 60
					is_editable = True
			elif offset_day:
				xbegin -= 1440
				xend -= 1440
				if begin2 < xbegin <= end2:
					if xend < end2:
						# recording within event
						time_match = (xend - xbegin) * 60
						is_editable = True
					else:
						# recording last part of event
						time_match = (end2 - xbegin) * 60
						summary_end = (xend - end2) * 60
						is_editable = not summary_end and True or time_match >= summary_end
				elif xbegin <= begin2 <= xend:
					if xend < end2:
						# recording first part of event
						time_match = (xend - begin2) * 60
						summary_end = (begin2 - xbegin) * 60
						is_editable = not summary_end and True or time_match >= summary_end
					else:
						# recording whole event
						time_match = (end2 - begin2) * 60
						is_editable = True
		elif offset_day and checking_time:
			xbegin -= 1440
			xend -= 1440
			if begin2 < xbegin <= end2:
				if xend < end2:
					# recording within event
					time_match = (xend - xbegin) * 60
					is_editable = True
				else:
					# recording last part of event
					time_match = (end2 - xbegin) * 60
					summary_end = (xend - end2) * 60
					is_editable = not summary_end and True or time_match >= summary_end
			elif xbegin <= begin2 <= xend:
				if xend < end2:
					# recording first part of event
					time_match = (xend - begin2) * 60
					summary_end = (begin2 - xbegin) * 60
					is_editable = not summary_end and True or time_match >= summary_end
				else:
					# recording whole event
					time_match = (end2 - begin2) * 60
					is_editable = True
		return time_match and is_editable

	def isInTimer(self, eventid, begin, duration, service):
		returnValue = None
		type = 0
		time_match = 0
		bt = None
		check_offset_time = not config.recording.margin_before.value and not config.recording.margin_after.value
		end = begin + duration
		refstr = ':'.join(service.split(':')[:11])
		for x in self.timer_list:
			check = ':'.join(x.service_ref.ref.toString().split(':')[:11]) == refstr
			if not check:
				sref = x.service_ref.ref
				parent_sid = sref.getUnsignedData(5)
				parent_tsid = sref.getUnsignedData(6)
				if parent_sid and parent_tsid:
					# check for subservice
					sid = sref.getUnsignedData(1)
					tsid = sref.getUnsignedData(2)
					sref.setUnsignedData(1, parent_sid)
					sref.setUnsignedData(2, parent_tsid)
					sref.setUnsignedData(5, 0)
					sref.setUnsignedData(6, 0)
					check = sref.toCompareString() == refstr
					num = 0
					if check:
						check = False
						event = eEPGCache.getInstance().lookupEventId(sref, eventid)
						num = event and event.getNumOfLinkageServices() or 0
					sref.setUnsignedData(1, sid)
					sref.setUnsignedData(2, tsid)
					sref.setUnsignedData(5, parent_sid)
					sref.setUnsignedData(6, parent_tsid)
					for cnt in range(num):
						subservice = event.getLinkageService(sref, cnt)
						if sref.toCompareString() == subservice.toCompareString():
							check = True
							break
			if check:
				timer_end = x.end
				timer_begin = x.begin
				type_offset = 0
				if not x.repeated and check_offset_time:
					if 0 < end - timer_end <= 59:
						timer_end = end
					elif 0 < timer_begin - begin <= 59:
						timer_begin = begin
				if x.justplay:
					type_offset = 5
					if (timer_end - x.begin) <= 1:
						timer_end += 60
				if x.always_zap:
					type_offset = 10

				timer_repeat = x.repeated
				# if set 'don't stop current event but disable coming events' for repeat timer
				running_only_curevent = x.disabled and x.isRunning() and timer_repeat
				if running_only_curevent:
					timer_repeat = 0
					type_offset += 15

				if timer_repeat != 0:
					type_offset += 15
					if bt is None:
						bt = localtime(begin)
						bday = bt.tm_wday
						begin2 = 1440 + bt.tm_hour * 60 + bt.tm_min
						end2 = begin2 + duration / 60
					xbt = localtime(x.begin)
					xet = localtime(timer_end)
					offset_day = False
					checking_time = x.begin < begin or begin <= x.begin <= end
					if xbt.tm_yday != xet.tm_yday:
						oday = bday - 1
						if oday == -1: oday = 6
						offset_day = x.repeated & (1 << oday)
					xbegin = 1440 + xbt.tm_hour * 60 + xbt.tm_min
					xend = xbegin + ((timer_end - x.begin) / 60)
					if xend < xbegin:
						xend += 1440
					if x.repeated & (1 << bday) and checking_time:
						if begin2 < xbegin <= end2:
							if xend < end2:
								# recording within event
								time_match = (xend - xbegin) * 60
								type = type_offset + 3
							else:
								# recording last part of event
								time_match = (end2 - xbegin) * 60
								type = type_offset + 1
						elif xbegin <= begin2 <= xend:
							if xend < end2:
								# recording first part of event
								time_match = (xend - begin2) * 60
								type = type_offset + 4
							else:
								# recording whole event
								time_match = (end2 - begin2) * 60
								type = type_offset + 2
						elif offset_day:
							xbegin -= 1440
							xend -= 1440
							if begin2 < xbegin <= end2:
								if xend < end2:
									# recording within event
									time_match = (xend - xbegin) * 60
									type = type_offset + 3
								else:
									# recording last part of event
									time_match = (end2 - xbegin) * 60
									type = type_offset + 1
							elif xbegin <= begin2 <= xend:
								if xend < end2:
									# recording first part of event
									time_match = (xend - begin2) * 60
									type = type_offset + 4
								else:
									# recording whole event
									time_match = (end2 - begin2) * 60
									type = type_offset + 2
					elif offset_day and checking_time:
						xbegin -= 1440
						xend -= 1440
						if begin2 < xbegin <= end2:
							if xend < end2:
								# recording within event
								time_match = (xend - xbegin) * 60
								type = type_offset + 3
							else:
								# recording last part of event
								time_match = (end2 - xbegin) * 60
								type = type_offset + 1
						elif xbegin <= begin2 <= xend:
							if xend < end2:
								# recording first part of event
								time_match = (xend - begin2) * 60
								type = type_offset + 4
							else:
								# recording whole event
								time_match = (end2 - begin2) * 60
								type = type_offset + 2
				else:
					if begin < timer_begin <= end:
						if timer_end < end:
							# recording within event
							time_match = timer_end - timer_begin
							type = type_offset + 3
						else:
							# recording last part of event
							time_match = end - timer_begin
							type = type_offset + 1
					elif timer_begin <= begin <= timer_end:
						if timer_end < end:
							# recording first part of event
							time_match = timer_end - begin
							type = type_offset + 4
						else:
							# recording whole event
							time_match = end - begin
							type = type_offset + 2
				if time_match:
					if type in (2,7,12,17,22,27):
						# When full recording do not look further
						returnValue = (time_match, [type])
						break
					elif returnValue:
						if type not in returnValue[1]:
							returnValue[1].append(type)
					else:
						returnValue = (time_match, [type])

		return returnValue

	def removeEntry(self, entry):
		print "[Timer] Remove " + str(entry)

		# avoid re-enqueuing
		entry.repeated = False

		# abort timer.
		# this sets the end time to current time, so timer will be stopped.
		entry.autoincrease = False
		entry.abort()

		if entry.state != entry.StateEnded:
			self.timeChanged(entry)

		print "state: ", entry.state
		print "in processed: ", entry in self.processed_timers
		print "in running: ", entry in self.timer_list
		# autoincrease instanttimer if possible
		if not entry.dontSave:
			for x in self.timer_list:
				if x.setAutoincreaseEnd():
					self.timeChanged(x)
		# now the timer should be in the processed_timers list. remove it from there.
		self.processed_timers.remove(entry)
		self.saveTimer()

	def shutdown(self):
		self.saveTimer()
