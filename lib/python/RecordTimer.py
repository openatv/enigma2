from bisect import insort
from datetime import datetime
from os import access, fsync, makedirs, remove, rename, statvfs, W_OK
from os.path import exists, isdir, realpath, ismount
from threading import Thread, Timer as ThreadTimer
from time import ctime, localtime, strftime, time

from enigma import eEPGCache, getBestPlayableServiceReference, eStreamServer, eServiceEventEnums, eServiceReference, iRecordableService, quitMainloop, eActionMap, setPreferredTuner, pNavigation

import NavigationInstance
from timer import Timer, TimerEntry
from Components.config import config
from Components.Harddisk import findMountPoint
import Components.RecordingConfig
Components.RecordingConfig.InitRecordingConfig()
from Components.SystemInfo import getBoxDisplayName
from Components.TimerSanityCheck import TimerSanityCheck
from Components.UsageConfig import defaultMoviePath, calcFrontendPriorityIntval
from Screens.MessageBox import MessageBox
import Screens.Standby
from ServiceReference import ServiceReference
from Tools.ASCIItranslit import legacyEncode
from Tools.Directories import SCOPE_CONFIG, fileReadXML, getRecordingFilename, resolveFilename
from Tools.Notifications import AddNotification, AddNotificationWithCallback, AddPopup
from Tools import Trashcan
from Tools.XMLTools import stringToXML


# try:  # Import later (no error message on system start)!
# 	from Screens.InfoBar import InfoBar
# except Exception as err:
# 	print("[RecordTimer] Error: Import of 'InfoBar' from 'Screens.InfoBar' failed!  (%s)" % str(err))
# 	InfoBar = False
InfoBar = False

MODULE_NAME = __name__.split(".")[-1]
DEBUG = config.crash.debugTimers.value

TIMER_XML_FILE = resolveFilename(SCOPE_CONFIG, "timers.xml")
TIMER_FLAG_FILE = "/tmp/was_rectimer_wakeup"

wasRecTimerWakeup = False


class AFTEREVENT:
	NONE = 0
	STANDBY = 1
	DEEPSTANDBY = 2
	AUTO = 3
	DEFAULT = int(config.recording.default_afterevent.value)

	def __init__(self):
		pass


class TIMERTYPE:
	RECORD = 0
	ZAP = 1
	ZAP_RECORD = 2
	JUSTPLAY = config.recording.default_timertype.value == "zap"
	ALWAYS_ZAP = config.recording.default_timertype.value == "zap+record"

	def __init__(self):
		pass


# Parses an event, and gives out a basic event data tuple.  The tuple provided
# depends on the newTimerData flag.  By default the legacy tuple will be returned.
# The begin and end will be corrected to include the recording margin padding.
#
def parseEvent(event, description=True, newTimerData=False, isZapTimer=False):  # Make this timerType and use appropriate margin set between Zap and Record timers.
	if description:
		name = event.getEventName()
		description = event.getShortDescription()
		if not description:
			description = event.getExtendedDescription()
	else:
		name = ""
		description = ""
	# Replace linebreak's with spaces to avoid display issues in the text edit screens.
	# Enigma2 does not have a multiline InputBox or VirtualKeyBoard.
	description = description.replace("\n", " ")
	eventBegin = event.getBeginTime()
	eventEnd = eventBegin + event.getDuration()
	eit = event.getEventId()
	if newTimerData:
		cridSeries = event.getCridData(eServiceEventEnums.SERIES_MATCH)
		cridSeries = cridSeries and cridSeries[0][2]
		cridEpisode = event.getCridData(eServiceEventEnums.EPISODE_MATCH)
		cridEpisode = cridEpisode and cridEpisode[0][2]
		cridRecommendation = event.getCridData(eServiceEventEnums.RECOMMENDATION_MATCH)
		cridRecommendation = cridRecommendation and cridRecommendation[0][2]  # DEBUG: (Type, Location, "Value")
	marginBefore = (getattr(config.recording, "zap_margin_before" if isZapTimer else "margin_before").value * 60)
	marginAfter = (getattr(config.recording, "zap_margin_after" if isZapTimer else "margin_after").value * 60)
	# print(f"[RecordTimer] DEBUG: series='{cridSeries}', episode='{cridEpisode}', recommendation='{cridRecommendation}', before={marginBefore}, after={marginAfter}.")
	begin = eventBegin - marginBefore
	end = eventEnd + marginAfter
	if newTimerData:
		return (name, description, marginBefore, eventBegin, eventEnd, marginAfter, eit, cridSeries, cridEpisode, cridRecommendation)
	return (begin, end, name, description, eit)


class RecordTimer(Timer):
	def __init__(self):
		Timer.__init__(self)
		self.onTimerAdded = []
		self.onTimerRemoved = []
		self.onTimerChanged = []
		self.fallbackTimerlist = []

	def loadTimers(self):
		if exists(TIMER_XML_FILE):
			timerDom = fileReadXML(TIMER_XML_FILE, source=MODULE_NAME)
			if timerDom is None:
				AddPopup(_("The timer file '%s' is corrupt and could not be loaded.") % TIMER_XML_FILE, type=MessageBox.TYPE_ERROR, timeout=0, id="TimerLoadFailed")
				try:
					rename(TIMER_XML_FILE, f"{TIMER_XML_FILE}_bad")
				except OSError as err:
					print(f"[RecordTimer] Error {err.errno}: Unable to rename corrupt timer file out of the way!  ({err.strerror})")
				return
		else:
			print(f"[RecordTimer] Note: The timer file '{TIMER_XML_FILE}' was not found!")
			return
		check = True  # Display a message when at least one timer overlaps another one.
		for timer in timerDom.findall("timer"):
			newTimer = self.createTimer(timer)
			if (self.record(newTimer, True, dosave=False) is not None) and (check is True):
				AddPopup(_("Timer overlap in '%s' detected! Please check all the timers.") % TIMER_XML_FILE, type=MessageBox.TYPE_ERROR, timeout=0, id="TimerLoadFailed")
				check = False  # At the moment it is enough if the message is only displayed once.

	def saveTimers(self):
		timerList = ["<?xml version=\"1.0\" ?>", "", "<timers>"]
		for timer in self.timer_list + self.processed_timers:
			if timer.dontSave:
				continue
			timerEntry = ["\t<timer"]
			timerEntry.append(f"begin=\"{int(timer.begin)}\"")
			timerEntry.append(f"end=\"{int(timer.end)}\"")
			timerEntry.append(f"marginBefore=\"{timer.marginBefore}\"")
			timerEntry.append(f"eventBegin=\"{timer.eventBegin}\"")
			timerEntry.append(f"eventEnd=\"{timer.eventEnd}\"")
			timerEntry.append(f"marginAfter=\"{timer.marginAfter}\"")
			timerEntry.append(f"hasEndTime=\"{timer.hasEndTime}\"")
			timerEntry.append(f"serviceref=\"{stringToXML(str(timer.service_ref))}\"")
			if timer.eit:
				timerEntry.append(f"eit=\"{timer.eit}\"")
			if timer.cridSeries or timer.cridEpisode or timer.cridRecommendation:
				timerEntry.append(f"cridSeries=\"{timer.cridSeries}\"")
				timerEntry.append(f"cridEpisode=\"{timer.cridEpisode}\"")
				timerEntry.append(f"cridRecommendation=\"{timer.cridRecommendation}\"")
			timerEntry.append(f"repeated=\"{int(timer.repeated)}\"")
			timerEntry.append(f"rename_repeat=\"{int(timer.rename_repeat)}\"")
			timerEntry.append(f"name=\"{stringToXML(timer.name)}\"")
			timerEntry.append(f"description=\"{stringToXML(timer.description)}\"")
			if timer.dirname:
				timerEntry.append(f"location=\"{stringToXML(timer.dirname)}\"")
			if timer.tags:
				timerEntry.append(f"tags=\"{stringToXML(' '.join(timer.tags))}\"")
			timerEntry.append("afterevent=\"%s\"" % stringToXML({
				AFTEREVENT.NONE: "nothing",
				AFTEREVENT.STANDBY: "standby",
				AFTEREVENT.DEEPSTANDBY: "deepstandby",
				AFTEREVENT.AUTO: "auto"
			}[timer.afterEvent]))
			timerEntry.append(f"disabled=\"{int(timer.disabled)}\"")
			timerEntry.append(f"justplay=\"{int(timer.justplay)}\"")
			timerEntry.append(f"always_zap=\"{int(timer.always_zap)}\"")
			timerEntry.append(f"descramble=\"{int(timer.descramble)}\"")
			timerEntry.append(f"record_ecm=\"{int(timer.record_ecm)}\"")
			if timer.failed:
				timerEntry.append("failed=\"1\"")
			if timer.isAutoTimer:
				# timerEntry.append("isAutoTimer=\"True\"")
				timerEntry.append("isAutoTimer=\"1\"")
			if timer.ice_timer_id:
				timerEntry.append(f"ice_timer_id=\"{timer.ice_timer_id}\"")
			if timer.vpsplugin_enabled:
				timerEntry.append("vps_enabled=\"1\"")
				timerEntry.append(f"vps_overwrite=\"{'1' if timer.vpsplugin_overwrite else '0'}\"")
				timerEntry.append(f"vps_time=\"{timer.vpsplugin_time if timer.vpsplugin_time else '0'}\"")
			timerLog = []
			for logTime, logCode, logMsg in timer.log_entries:
				timerLog.append(f"\t\t<log code=\"{logCode}\" time=\"{int(logTime)}\">{stringToXML(logMsg)}</log>")
			if timerLog:
				timerList.append(f"{' '.join(timerEntry)}>")
				timerList += timerLog
				timerList.append("\t</timer>")
			else:
				timerList.append(f"{' '.join(timerEntry)} />")
		timerList.append("</timers>")
		timerList.append("")
		try:
			with open(f"{TIMER_XML_FILE}.writing", "w") as fd:
				fd.write("\n".join(timerList))
				fd.flush()
				fsync(fd.fileno())
			rename(f"{TIMER_XML_FILE}.writing", TIMER_XML_FILE)
		except OSError as err:
			print(f"[RecordTimer] Error {err.errno}: Unable to save timer entries to '{TIMER_XML_FILE}'!  ({err.strerror})")

	def saveTimer(self):  # Deprecated method name only used by some plug ins.
		return self.saveTimers()

	def createTimer(self, timerDom):
		begin = int(timerDom.get("begin"))
		end = int(timerDom.get("end"))
		justplay = int(timerDom.get("justplay") or "0")
		marginBefore = int(timerDom.get("marginBefore") or "-1")
		eventBegin = int(timerDom.get("eventBegin") or "0")
		eventEnd = int(timerDom.get("eventEnd") or "0")
		marginAfter = int(timerDom.get("marginAfter") or "-1")
		if marginBefore == -1:
			marginBefore = (getattr(config.recording, "zap_margin_before" if justplay else "margin_before").value * 60)
		if marginAfter == -1:
			marginAfter = (getattr(config.recording, "zap_margin_after" if justplay else "margin_after").value * 60)
		if eventBegin == 0:
			eventBegin = begin + marginBefore
		if eventEnd == 0:
			eventEnd = end - marginAfter
		hasEndTime = timerDom.get("hasEndTime", "true").lower() in ("1", "true", "yes")
		serviceRef = ServiceReference(timerDom.get("serviceref"))
		eit = timerDom.get("eit") or "None"
		eit = int(eit) if eit != "None" else None
		cridSeries = timerDom.get("cridSeries")
		cridEpisode = timerDom.get("cridEpisode")
		cridRecommendation = timerDom.get("cridRecommendation")
		description = timerDom.get("description")
		repeated = timerDom.get("repeated")
		renameRepeat = timerDom.get("rename_repeat", "0").lower() in ("1", "true", "yes")
		disabled = int(timerDom.get("disabled") or "0")
		alwaysZap = int(timerDom.get("always_zap") or "0")
		afterevent = str(timerDom.get("afterevent") or "nothing")
		afterevent = {
			"nothing": AFTEREVENT.NONE,
			"standby": AFTEREVENT.STANDBY,
			"deepstandby": AFTEREVENT.DEEPSTANDBY,
			"auto": AFTEREVENT.AUTO
		}[afterevent]
		location = timerDom.get("location") or "None"
		if location == "None":
			location = None
		tags = timerDom.get("tags") or "None"
		tags = tags.split(" ") if tags != "None" else None
		descramble = int(timerDom.get("descramble") or "1")
		recordEcm = int(timerDom.get("record_ecm") or "0")
		isAutoTimer = int(timerDom.get("isAutoTimer") or "0")
		# isAutoTimer = timerDom.get("isAutoTimer", "false").lower() in ("1", "true", "yes")
		iceTimerId = timerDom.get("ice_timer_id")
		vpsOverwrite = timerDom.get("vps_overwrite")
		vpsEnabled = timerDom.get("vps_enabled")
		vpsTime = timerDom.get("vps_time")
		name = timerDom.get("name")
		# filename = timerDom.get("filename").encode("utf-8")
		timer = RecordTimerEntry(
			serviceRef, begin, end, name, description, eit, disabled, justplay, afterevent,
			dirname=location, tags=tags, descramble=descramble, record_ecm=recordEcm,
			isAutoTimer=isAutoTimer, ice_timer_id=iceTimerId, always_zap=alwaysZap, rename_repeat=renameRepeat
		)
		timer.marginBefore = marginBefore
		timer.eventBegin = eventBegin
		timer.eventEnd = eventEnd
		timer.marginAfter = marginAfter
		timer.hasEndTime = hasEndTime
		timer.cridSeries = cridSeries
		timer.cridEpisode = cridEpisode
		timer.cridRecommendation = cridRecommendation
		timer.repeated = int(repeated)
		timer.vpsplugin_overwrite = (vpsOverwrite and vpsOverwrite == "1")
		timer.vpsplugin_enabled = (vpsEnabled and vpsEnabled == "1")
		if vpsTime and vpsTime != "None":
			timer.vpsplugin_time = int(vpsTime)
		for log in timerDom.findall("log"):
			timer.log_entries.append((int(log.get("time")), int(log.get("code")), log.text.strip()))
		timer.failed = int(timerDom.get("failed") or "0")
		return timer

	def timeChanged(self, timer):
		Timer.timeChanged(self, timer)
		for callback in self.onTimerChanged:
			callback(timer)

	# When activating a timer which has already passed, simply
	# abort the timer. Don't run trough all the stages.
	#
	def doActivate(self, timer):
		if timer.shouldSkip():
			timer.state = RecordTimerEntry.StateEnded
		else:
			# When active returns True this means "accepted", otherwise, the current
			# state is kept. The timer entry itself will fix up the delay.
			if timer.activate():
				timer.state += 1
		try:
			self.timer_list.remove(timer)
		except ValueError:
			print("[RecordTimer] Remove timer from timer list failed!")
		if timer.state < RecordTimerEntry.StateEnded:  # Did this timer reach the last state?
			insort(self.timer_list, timer)  # No, sort it into active list.
		else:  # Yes, process repeated, and re-add.
			if timer.repeated:
				timer.processRepeated()
				timer.state = RecordTimerEntry.StateWaiting
				timer.first_try_prepare = 0  # Changed from a Boolean to a counter, not renamed for compatibility with OpenWebif.
				timer.messageBoxAnswerPending = False
				timer.justTriedFreeingTuner = False
				timer.messageString = ""  # Incremental MessageBox string.
				timer.messageStringShow = False
				self.addTimerEntry(timer)
			else:
				self.cleanupDisabled()  # Check for disabled timers, if time has passed set to completed.
				self.cleanupDaily(config.recording.keep_timers.value)  # Remove old timers as set in config.
				insort(self.processed_timers, timer)
		self.stateChanged(timer)

	def cleanup(self):
		for timer in self.processed_timers[:]:
			if not timer.disabled:
				self.processed_timers.remove(timer)
				for callback in self.onTimerRemoved:
					callback(timer)
		self.saveTimers()

	def shutdown(self):
		self.saveTimers()

	def getNextRecordingTimeOld(self, getNextStbPowerOn=False):
		now = int(time())
		if getNextStbPowerOn:
			saveAct = (-1, 0)
			for timer in self.timer_list:
				nextAct = timer.getNextActivation(getNextStbPowerOn)
				if timer.justplay or nextAct + 3 < now:
					continue
				if DEBUG:
					print(f"[RecordTimer] Next STB power up {strftime('%a, %Y/%m/%d %H:%M', localtime(nextAct))}.")
				if saveAct[0] == -1:
					saveAct = (nextAct, int(not timer.always_zap))
				else:
					if nextAct < saveAct[0]:
						saveAct = (nextAct, int(not timer.always_zap))
			return saveAct
		else:
			for timer in self.timer_list:
				nextAct = timer.getNextActivation()
				if timer.justplay or nextAct + 3 < now or timer.end == nextAct:
					continue
				return nextAct
		return -1

	# If getNextStbPowerOn is True returns tuple -> (timer.begin, set standby).
	#
	def getNextRecordingTime(self, getNextStbPowerOn=False):
		nextRecTime = self.getNextRecordingTimeOld(getNextStbPowerOn)
		fakeTime = int(time()) + 300
		if getNextStbPowerOn:
			if config.timeshift.isRecording.value:
				if 0 < nextRecTime[0] < fakeTime:
					return nextRecTime
				else:
					return fakeTime, 0
			else:
				return nextRecTime
		else:
			if config.timeshift.isRecording.value:
				if 0 < nextRecTime < fakeTime:
					return nextRecTime
				else:
					return fakeTime
			else:
				return nextRecTime

	def isNextRecordAfterEventActionAuto(self):
		for timer in self.timer_list:
			return True  # All types needed True for ident in Navigation.py.
			# NOTE: None of the following code is *EVER* run!!!
			if timer.justplay:
				continue
			if timer.afterEvent == AFTEREVENT.AUTO or timer.afterEvent == AFTEREVENT.DEEPSTANDBY:
				return True
		return False

	# DEBUG: Rename "ignoreTSC" to be "ignoreConflict" to be more clear.  This is used by MovieSelection.py.
	def record(self, timer, ignoreTSC=False, dosave=True):  # This is called by loadTimers with dosave=False.
		timer.check_justplay()
		timerSanityCheck = TimerSanityCheck(self.timer_list, timer)
		if not timerSanityCheck.check():
			if not ignoreTSC:
				print("[RecordTimer] Timer conflict detected!")
				return timerSanityCheck.getSimulTimerList()
			else:
				print("[RecordTimer] Ignore timer conflict!")
		elif timerSanityCheck.doubleCheck():
			print("[RecordTimer] Ignore duplicated timer.")
			return None
		timer.timeChanged()
		print(f"[RecordTimer] Timer '{str(timer)}'.")
		timer.Timer = self
		if not timer.log_entries:
			timer.log(0, "Timer created")
		self.addTimerEntry(timer)
		for callback in self.onTimerAdded:  # Trigger onTimerAdded callbacks.
			callback(timer)
		if dosave:
			self.saveTimers()
		return None

	def removeEntry(self, timer):
		print(f"[RecordTimer] Remove timer '{str(timer)}'.")
		timer.repeated = False  # Avoid re-queuing.
		timer.autoincrease = False
		timer.abort()  # Abort timer. This sets the end time to current time, so timer will be stopped.
		if timer.state != timer.StateEnded:
			self.timeChanged(timer)
		# print("[RecordTimer] State: '%s'." % timer.state)
		# print("[RecordTimer] In processed: %s" % timer in self.processed_timers)
		# print("[RecordTimer] In running: %s" % timer in self.timer_list)
		if not timer.dontSave:  # Auto increase instant timer if possible.
			for timerItem in self.timer_list:
				if timerItem.setAutoincreaseEnd():
					self.timeChanged(timerItem)
		if timer in self.processed_timers:  # Now the timer should be in the processed_timers list, remove it from there.
			self.processed_timers.remove(timer)
		for callback in self.onTimerRemoved:  # Trigger onTimerRemoved callbacks.
			callback(timer)
		self.saveTimers()

	def getNextZapTime(self):
		now = int(time())
		for timer in self.timer_list:
			if not timer.justplay or timer.begin < now:
				continue
			return timer.begin
		return -1

	def isRecTimerWakeup(self):
		global wasRecTimerWakeup
		wasRecTimerWakeup = int(open(TIMER_FLAG_FILE).read()) and True or False if exists(TIMER_FLAG_FILE) else False  # DEBUG: Use fileReadLine()
		return wasRecTimerWakeup

	def isRecording(self):
		for timer in self.timer_list:
			if timer.isRunning() and not timer.justplay:
				return True
		return False

	def getStillRecording(self):
		now = int(time())
		for timer in self.timer_list:
			if timer.isStillRecording or (abs(timer.begin - now) <= 10 and abs(timer.end - now) > 10):
				return True
		return False

	def getFallbackTimers(self, service):
		return [timer for timer in self.fallbackTimerlist if timer.serviceRefString == service]

	def getTimers(self, service):
		return [timer for timer in self.timer_list + self.processed_timers if timer.serviceRefString == service] + self.getFallbackTimers(service)

	def hasTimers(self, service):
		return self.getTimers(service) != []

	def isInTimer(self, eventid, begin, duration, service, getTimer=False):
		returnValue = None
		timerType = 0
		timeMatch = 0
		isAutoTimer = 0
		isDisabled = 0
		beginTime = None
		checkOffsetTimeRecord = not config.recording.margin_before.value and not config.recording.margin_after.value
		checkOffsetTimeZap = not config.recording.zap_margin_before.value and not config.recording.zap_margin_after.value
		end = begin + duration
		for timer in self.getTimers(service):
			checkOffsetTime = checkOffsetTimeZap if timer.justplay else checkOffsetTimeRecord
			isAutoTimer = 0
			isDisabled = timer.disabled
			if timer.isAutoTimer == 1:
				isAutoTimer |= 1
			if timer.ice_timer_id:
				isAutoTimer |= 2
			timerEnd = timer.end
			timerBegin = timer.begin
			typeOffset = 0
			if not timer.repeated and checkOffsetTime:
				if 0 < end - timerEnd <= 59:
					timerEnd = end
				elif 0 < timerBegin - begin <= 59:
					timerBegin = begin
			if timer.justplay:
				typeOffset = 5
				if not timer.hasEndTime or (timerEnd - timer.begin) <= 1:
					if timerBegin < end and timerBegin >= begin:
						timerEnd = timerBegin + duration  # Special case for zap timer without endtime
			if timer.always_zap:
				typeOffset = 10
			if timer.repeated:
				if beginTime is None:
					beginTime = localtime(begin)
					beginDay = beginTime.tm_wday
					begin2 = 1440 + beginTime.tm_hour * 60 + beginTime.tm_min
					end2 = begin2 + duration // 60
				xBeginTime = localtime(timer.begin)
				xEndTime = localtime(timerEnd)
				offsetDay = False
				checkingTime = timer.begin < begin or begin <= timer.begin <= end
				if xBeginTime.tm_yday != xEndTime.tm_yday:
					oday = beginDay - 1
					if oday == -1:
						oday = 6
					offsetDay = timer.repeated & (1 << oday)
				xBegin = 1440 + xBeginTime.tm_hour * 60 + xBeginTime.tm_min
				xEnd = xBegin + ((timerEnd - timer.begin) // 60)
				if xEnd < xBegin:
					xEnd += 1440
				if timer.repeated & (1 << beginDay) and checkingTime:
					if begin2 < xBegin <= end2:
						if xEnd < end2:  # Recording within event.
							timeMatch = (xEnd - xBegin) * 60
							timerType = typeOffset + 3
						else:  # Recording last part of event.
							timeMatch = (end2 - xBegin) * 60
							timerType = typeOffset + 1
					elif xBegin <= begin2 <= xEnd:
						if xEnd < end2:  # Recording first part of event.
							timeMatch = (xEnd - begin2) * 60
							timerType = typeOffset + 4
						else:  # Recording whole event.
							timeMatch = (end2 - begin2) * 60
							timerType = typeOffset + 2
					elif offsetDay:
						xBegin -= 1440
						xEnd -= 1440
						if begin2 < xBegin <= end2:
							if xEnd < end2:  # Recording within event.
								timeMatch = (xEnd - xBegin) * 60
								timerType = typeOffset + 3
							else:  # Recording last part of event.
								timeMatch = (end2 - xBegin) * 60
								timerType = typeOffset + 1
						elif xBegin <= begin2 <= xEnd:
							if xEnd < end2:  # Recording first part of event.
								timeMatch = (xEnd - begin2) * 60
								timerType = typeOffset + 4
							else:  # Recording whole event.
								timeMatch = (end2 - begin2) * 60
								timerType = typeOffset + 2
				elif offsetDay and checkingTime:
					xBegin -= 1440
					xEnd -= 1440
					if begin2 < xBegin <= end2:
						if xEnd < end2:  # Recording within event.
							timeMatch = (xEnd - xBegin) * 60
							timerType = typeOffset + 3
						else:  # Recording last part of event.
							timeMatch = (end2 - xBegin) * 60
							timerType = typeOffset + 1
					elif xBegin <= begin2 <= xEnd:
						if xEnd < end2:  # Recording first part of event.
							timeMatch = (xEnd - begin2) * 60
							timerType = typeOffset + 4
						else:  # Recording whole event.
							timeMatch = (end2 - begin2) * 60
							timerType = typeOffset + 2
			else:
				if begin < timerBegin <= end:
					if timerEnd < end:  # Recording within event.
						timeMatch = timerEnd - timerBegin
						timerType = typeOffset + 3
					else:  # Recording last part of event.
						timeMatch = end - timerBegin
						timerType = typeOffset + 1
				elif timerBegin <= begin <= timerEnd:
					if timerEnd < end:  # Recording first part of event.
						timeMatch = timerEnd - begin
						timerType = typeOffset + 4
						if timer.justplay and (not timer.hasEndTime or (timerEnd - timer.begin) <= 1):
							timerType = typeOffset + 2  # Special case for zap timer without end time
					else:  # Recording whole event.
						timeMatch = end - begin
						timerType = typeOffset + 2
			if timeMatch:
				if isDisabled and timerType in (2, 7, 12):
					timerType = 15
				returnValue = (timeMatch, timerType, isAutoTimer, timer) if getTimer else (timeMatch, timerType, isAutoTimer)
				if timerType in (2, 7, 12, 15):  # When full recording do not look further.
					break
		return returnValue

	def setFallbackTimerList(self, timerList):
		self.fallbackTimerlist = [timer for timer in timerList if timer.state != 3]


def findSafeRecordPath(dirname):  # Also called from InfoBarGenerics.
	if not dirname:
		return None
	dirname = realpath(dirname)
	mountPoint = findMountPoint(dirname)
	if not ismount(mountPoint):
		print(f"[RecordTimer] Media is not mounted for '{dirname}'.")
		return None
	if not isdir(dirname):
		try:
			makedirs(dirname)
		except OSError as err:
			print(f"[RecordTimer] Error {err.errno}: Failed to create directory '{dirname}'!  ({err.strerror})")
			return None
	return dirname


def createRecordTimerEntry(timer):
	return RecordTimerEntry(
		timer.service_ref, timer.begin, timer.end, timer.name, timer.description, timer.eit, timer.disabled,
		timer.justplay, timer.afterEvent, dirname=timer.dirname, tags=timer.tags, descramble=timer.descramble,
		record_ecm=timer.record_ecm, always_zap=timer.always_zap, rename_repeat=timer.rename_repeat
	)


class RecordTimerEntry(TimerEntry):
	def __init__(self, serviceref, begin, end, name, description, eit, disabled=False, justplay=TIMERTYPE.JUSTPLAY, afterEvent=AFTEREVENT.DEFAULT, checkOldTimers=False, dirname=None, tags=None, descramble="notset", record_ecm="notset", rename_repeat=True, isAutoTimer=False, ice_timer_id=None, always_zap=TIMERTYPE.ALWAYS_ZAP, MountPath=None, fixDescription=False, cridSeries=None, cridEpisode=None, cridRecommendation=None):
		TimerEntry.__init__(self, int(begin), int(end))
		# print("[RecordTimerEntry] DEBUG: Running init code.")
		self.marginBefore = (getattr(config.recording, "zap_margin_before" if justplay == TIMERTYPE.ZAP else "margin_before").value * 60)
		self.marginAfter = (getattr(config.recording, "zap_margin_after" if justplay == TIMERTYPE.ZAP else "margin_after").value * 60)
		self.eventBegin = begin + self.marginBefore
		self.eventEnd = end - self.marginAfter
		if checkOldTimers and self.begin < int(time()) - 1209600:
			self.begin = int(time())
		if self.end < self.begin:
			self.end = self.begin
		self.hasEndTime = not justplay
		if not isinstance(serviceref, ServiceReference):  # NOTE: Rename "serviceref" and "service_ref" to "serviceRef".
			raise AssertionError("[RecordTimerEntry] Error: Invalid service reference!")
		self.service_ref = serviceref if serviceref and serviceref.isRecordable() else ServiceReference(None)
		self.eit = None
		if not name or not description or not eit or not cridSeries or not cridEpisode or not cridRecommendation:
			event = self.getEventFromEPGId(eit) or self.getEventFromEPG()
			if event:
				if not name:
					name = event.getEventName()
				if not description:
					description = event.getShortDescription()
				if not description:
					description = event.getExtendedDescription()
				if description and fixDescription:
					# Replace line-breaks with spaces to avoid display issues in the text edit screens.
					# Enigma2 does not have a multi-line InputBox or VirtualKeyBoard.
					description = description.replace("\n", " ")
				if not eit:
					eit = event.getEventId()
				if not cridSeries:
					cridSeries = event.getCridData(eServiceEventEnums.SERIES_MATCH)
					cridSeries = cridSeries and cridSeries[0][2]
				if not cridEpisode:
					cridEpisode = event.getCridData(eServiceEventEnums.EPISODE_MATCH)
					cridEpisode = cridEpisode and cridEpisode[0][2]
				if not cridRecommendation:
					cridRecommendation = event.getCridData(eServiceEventEnums.RECOMMENDATION_MATCH)
					cridRecommendation = cridRecommendation and cridRecommendation[0][2]
		self.name = name
		self.description = description
		self.eit = eit
		self.cridSeries = cridSeries
		self.cridEpisode = cridEpisode
		self.cridRecommendation = cridRecommendation
		self.dontSave = False
		self.disabled = disabled
		self.timer = None
		self.__record_service = None
		self.start_prepare = 0
		self.justplay = justplay
		self.always_zap = always_zap
		self.afterEvent = afterEvent
		self.dirname = dirname
		self.dirnameHadToFallback = False
		self.autoincrease = False
		self.autoincreasetime = 3600 * 24  # One day.
		self.tags = tags or []
		self.mountPath = None
		self.messageString = ""
		self.messageStringShow = False
		self.messageBoxAnswerPending = False
		self.justTriedFreeingTuner = False
		self.mountPathRetryCounter = 0
		self.mountPathErrorNumber = 0
		self.lastend = 0
		if descramble == "notset" and record_ecm == "notset":
			if config.recording.ecm_data.value == "descrambled+ecm":
				self.descramble = True
				self.record_ecm = True
			elif config.recording.ecm_data.value == "scrambled+ecm":
				self.descramble = False
				self.record_ecm = True
			elif config.recording.ecm_data.value == "normal":
				self.descramble = True
				self.record_ecm = False
		else:
			self.descramble = descramble
			self.record_ecm = record_ecm
		config.usage.frontend_priority_intval.setValue(calcFrontendPriorityIntval(config.usage.frontend_priority, config.usage.frontend_priority_multiselect, config.usage.frontend_priority_strictly))
		config.usage.recording_frontend_priority_intval.setValue(calcFrontendPriorityIntval(config.usage.recording_frontend_priority, config.usage.recording_frontend_priority_multiselect, config.usage.recording_frontend_priority_strictly))
		self.needChangePriorityFrontend = config.usage.recording_frontend_priority_intval.value != "-2" and config.usage.recording_frontend_priority_intval.value != config.usage.frontend_priority_intval.value
		self.change_frontend = False
		self.rename_repeat = rename_repeat
		self.isAutoTimer = isAutoTimer
		self.ice_timer_id = ice_timer_id
		self.wasInStandby = False
		self.vpsplugin_enabled = None  # Support VPS plugin.
		self.vpsplugin_overwrite = None  # Support VPS plugin.
		self.vpsplugin_time = None  # Support VPS plugin.
		# Workaround for vmc crash - only a dummy entry!!!
		# File "/usr/lib/enigma2/python/Plugins/Extensions/VMC/VMC_Classes.py", line 3704, in TimerChange
		# "Filename") and not timer.justplay and not timer.justremind and timer.state == TimerEntry.StateEnded:
		# AttributeError: 'RecordTimerEntry' object has no attribute 'justremind'
		self.justremind = False
		self.external = False
		self.log_entries = []
		self.check_justplay()
		self.resetState()

	def setServiceRef(self, sref):
		self.serviceRef = sref
		self.serviceRefString = sref.ref.toCompareString()

	def getServiceRef(self):
		return self.serviceRef

	service_ref = property(getServiceRef, setServiceRef)

	def __repr__(self):
		iceTV = f", ice_timer_id={self.ice_timer_id}" if self.ice_timer_id else ""
		disabled = ", Disabled" if self.disabled else ""
		return f"RecordTimerEntry(name={self.name}, begin={ctime(self.begin)}, end={ctime(self.end)}, serviceref={self.service_ref}, justplay={self.justplay}, isAutoTimer={self.isAutoTimer}{iceTV}{disabled})"

	def activate(self):
		global InfoBar, wasRecTimerWakeup
		if not InfoBar:
			try:
				from Screens.InfoBar import InfoBar
			except Exception as err:
				print(f"[RecordTimer] Error: Import 'InfoBar' from 'Screens.InfoBar' failed!  ({str(err)})")
		if exists(TIMER_FLAG_FILE) and not wasRecTimerWakeup:
			wasRecTimerWakeup = int(open(TIMER_FLAG_FILE).read()) and True or False
		nextState = self.state + 1
		if DEBUG:
			self.log(5, f"Activating state {nextState}.")
		# print("[RecordTimer] Activate called", time(), nextState, self.first_try_prepare, " pending ", self.messageBoxAnswerPending, " justTried ", self.justTriedFreeingTuner, " show ", self.messageStringShow, self.messageString)  # DEBUG: remove.
		if nextState == self.StatePrepared:
			if self.messageBoxAnswerPending:
				self.start_prepare = int(time()) + 1  # Call again in 1 second.
				return False
			if self.justTriedFreeingTuner:
				self.start_prepare = int(time()) + 5  # Is it really 5 seconds to tune a service.
				self.justTriedFreeingTuner = False
				return False
			if not self.justplay and not self.freespace():
				if self.mountPathErrorNumber < 3 and self.mountPathRetryCounter < 3:
					self.mountPathRetryCounter += 1
					self.start_prepare = int(time()) + 5  # tryPrepare in 5 seconds.
					self.log(0, f"Next try in 5 seconds.  ({self.mountPathRetryCounter}/3)")
					return False
				message = _("Write error at start of recording. %s\n%s") % ((_("Storage device not found!"), _("Storage device not writable!"), _("Storage device full!"))[self.mountPathErrorNumber - 1], self.name)
				if InfoBar and InfoBar.instance:
					InfoBar.instance.openInfoBarMessage(message, MessageBox.TYPE_ERROR, timeout=20)
				else:
					AddPopup(message, MessageBox.TYPE_ERROR, timeout=20, id="DiskFullMessage")
				self.failed = True
				self.next_activation = int(time())
				self.lastend = self.end
				self.end = int(time()) + 5  # DEBUG: Check that this is the bug for 0Byte recordings!
				self.backoff = 0
				return True
			if self.always_zap:
				Screens.Standby.TVinStandby.skipHdmiCecNow("zapandrecordtimer")
				if Screens.Standby.inStandby:
					self.wasInStandby = True
					# Set service to zap after standby.
					Screens.Standby.inStandby.prev_running_service = self.service_ref.ref
					Screens.Standby.inStandby.paused_service = None
					# Wakeup standby.
					Screens.Standby.inStandby.Power()
					self.log(5, "Wakeup and zap to recording service.")
				else:
					currentZapReference = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
					if currentZapReference and not currentZapReference.getPath():  # We do not zap away if it is no live service.
						self.setRecordingPreferredTuner()
						self.failureCB(True)
						self.log(5, "Zap to recording service.")
			if self.tryPrepare():
				if DEBUG:
					self.log(6, "Prepare okay, waiting for begin.")
				if self.messageStringShow:
					message = "%s%s" % (_("In order to record a timer, a tuner was freed successfully:\n\n"), self.messageString)
					if InfoBar and InfoBar.instance:
						InfoBar.instance.openInfoBarMessage(message, MessageBox.TYPE_INFO, timeout=20)
					else:
						AddNotification(MessageBox, message, MessageBox.TYPE_INFO, timeout=20)
				# Create the recording file to "reserve" the filename as another recording at the same time on another
				# service can try to record the same event (i.e. cable / satellite) then the second recording needs
				# its own extension. When we create the file here that calculateFilename is happy.
				if not self.justplay:
					open(self.Filename + self.record_service.getFilenameExtension(), "w").close()
					# Give the Trashcan a chance to clean up. Need try/except as Trashcan.instance may not exist
					# for a missed recording started at boot-time.
					try:
						Trashcan.instance.cleanIfIdle()
					except Exception as err:
						print(f"[RecordTimer] Error: Failed to call Trashcan.instance.cleanIfIdle!  ({str(err)})")
				# Fine, it worked, resources are allocated.
				self.next_activation = self.begin
				self.backoff = 0
				return True
			self.log(7, "Prepare failed!")
			if eStreamServer.getInstance().getConnectedClients():
				eStreamServer.getInstance().stopStream()
				return False
			if self.first_try_prepare == 0:  # Try to make a tuner available by disabling PiP.
				self.first_try_prepare += 1
				if not InfoBar:
					from Screens.InfoBar import InfoBar
				from Screens.InfoBarGenerics import InfoBarPiP
				from Components.ServiceEventTracker import InfoBarCount
				InfoBarInstance = InfoBarCount == 1 and InfoBar.instance
				if InfoBarInstance and InfoBarPiP.pipShown(InfoBarInstance) is True:
					if config.recording.ask_to_abort_pip.value == "ask":
						self.log(8, "Asking user to disable PiP.")
						self.messageBoxAnswerPending = True
						message = _("A timer failed to record!\nDisable PiP and try again?\n")
						if InfoBar and InfoBar.instance:
							InfoBar.instance.openInfoBarMessageWithCallback(self.failureCB_pip, message, MessageBox.TYPE_YESNO, timeout=20, default=True)
						else:
							AddNotificationWithCallback(self.failureCB_pip, MessageBox, message, MessageBox.TYPE_YESNO, timeout=20, default=True)
					elif config.recording.ask_to_abort_pip.value in ("abort_no_msg", "abort_msg"):
						self.log(8, "Disable PiP without asking.")
						self.setRecordingPreferredTuner()
						self.failureCB_pip(True)
					return False
				else:
					self.log(8, "No PiP active so we don't need to stop it.")
			if self.first_try_prepare == 1:  # Try to make a tuner available by aborting pseudo recordings.
				self.first_try_prepare += 1
				self.backoff = 0
				if len(NavigationInstance.instance.getRecordings(False, pNavigation.isPseudoRecording)) > 0:
					if config.recording.ask_to_abort_pseudo_rec.value == "ask":
						self.log(8, "Asking user to abort pseudo recordings.")
						self.messageBoxAnswerPending = True
						message = _("A timer failed to record!\nAbort pseudo recordings (e.g. EPG refresh) and try again?\n")
						if InfoBar and InfoBar.instance:
							InfoBar.instance.openInfoBarMessageWithCallback(self.failureCB_pseudo_rec, message, MessageBox.TYPE_YESNO, timeout=20, default=True)
						else:
							AddNotificationWithCallback(self.failureCB_pseudo_rec, MessageBox, message, MessageBox.TYPE_YESNO, timeout=20, default=True)
					elif config.recording.ask_to_abort_pseudo_rec.value in ("abort_no_msg", "abort_msg"):
						self.log(8, "Abort pseudo recordings without asking.")
						self.setRecordingPreferredTuner()
						self.failureCB_pseudo_rec(True)
					return False
				else:
					self.log(8, "No pseudo recordings active so we don't need to stop them.")
			if self.first_try_prepare == 2:  # Try to make a tuner available by aborting streaming.
				self.first_try_prepare += 1
				self.backoff = 0
				if len(NavigationInstance.instance.getRecordings(False, pNavigation.isStreaming)) > 0:
					if config.recording.ask_to_abort_streaming.value == "ask":
						self.log(8, "Asking user to abort streaming.")
						self.messageBoxAnswerPending = True
						message = _("A timer failed to record!\nAbort streaming and try again?\n")
						if InfoBar and InfoBar.instance:
							InfoBar.instance.openInfoBarMessageWithCallback(self.failureCB_streaming, message, MessageBox.TYPE_YESNO, timeout=20, default=True)
						else:
							AddNotificationWithCallback(self.failureCB_streaming, MessageBox, message, MessageBox.TYPE_YESNO, timeout=20, default=True)
					elif config.recording.ask_to_abort_streaming.value in ("abort_no_msg", "abort_msg"):
						self.log(8, "Abort streaming without asking.")
						self.setRecordingPreferredTuner()
						self.failureCB_streaming(True)
					return False
				else:
					self.log(8, "No streaming active so we don't need to stop it.")
			if self.first_try_prepare == 3:  # Try to make a tuner available by switching live TV to the recording service.
				self.first_try_prepare += 1
				self.backoff = 0
				currentReference = NavigationInstance.instance.getCurrentlyPlayingServiceReference()
				if currentReference and not currentReference.getPath():
					if Screens.Standby.inStandby:
						self.setRecordingPreferredTuner()
						self.failureCB(True)
					elif not config.recording.asktozap.value:
						self.log(8, "Asking user to zap.")
						self.messageBoxAnswerPending = True
						message = _("A timer failed to record!\nDisable TV and try again?\n")
						if InfoBar and InfoBar.instance:
							InfoBar.instance.openInfoBarMessageWithCallback(self.failureCB, message, MessageBox.TYPE_YESNO, timeout=20, default=True)
						else:
							AddNotificationWithCallback(self.failureCB, MessageBox, message, MessageBox.TYPE_YESNO, timeout=20, default=True)
					else:  # Zap without asking.
						self.log(9, "Zap without asking.")
						self.setRecordingPreferredTuner()
						self.failureCB(True)
					return False
				elif currentReference:
					self.log(8, "Running service is not a live service so stopping it makes no sense.")
				else:
					self.log(8, "No service running so we don't need to stop it.")
			if self.first_try_prepare == 4:  # Freeing a tuner failed.
				self.first_try_prepare += 1
				self.log(8, "Freeing a tuner failed!")
				if self.messageString:
					message = _("No tuner is available for recording a timer!\n\nThe following methods of freeing a tuner were tried without success:\n\n") + self.messageString
				else:
					message = _("No tuner is available for recording a timer!")
				if InfoBar and InfoBar.instance:
					InfoBar.instance.openInfoBarMessage(message, MessageBox.TYPE_INFO, timeout=20)
				else:
					AddNotification(MessageBox, message, MessageBox.TYPE_INFO, timeout=20)
				self.state = 3  # This will prevent error loop beause next state will be failed
			return False
		elif nextState == self.StateRunning:  # If this timer has been canceled, just go to "end" state.
			if self.cancelled:
				return True
			if self.failed:
				return True
			if self.justplay:
				Screens.Standby.TVinStandby.skipHdmiCecNow("zaptimer")
				if Screens.Standby.inStandby:
					self.wasInStandby = True
					# eActionMap.getInstance().bindAction("", -maxsize - 1, self.keypress)
					self.log(11, "Wake up and zap.")
					# Set service to zap after standby.
					Screens.Standby.inStandby.prev_running_service = self.service_ref.ref
					Screens.Standby.inStandby.paused_service = None
					# Wakeup standby.
					Screens.Standby.inStandby.Power()
				else:
					self.log(11, "Zapping.")
					NavigationInstance.instance.isMovieplayerActive()
					if InfoBar and InfoBar.instance and InfoBar.instance.servicelist:
						InfoBar.instance.servicelist.performZap(self.service_ref.ref)
					else:
						NavigationInstance.instance.playService(self.service_ref.ref)
				return True
			else:
				self.log(11, "Start recording.")
				recordRes = self.record_service.start()
				self.setRecordingPreferredTuner(setdefault=True)
				if recordRes:
					self.log(13, f"Start recording error {recordRes}!")
					self.do_backoff()
					# Retry.
					self.begin = int(time()) + self.backoff
					return False
				return True
		elif nextState == self.StateEnded or nextState == self.StateFailed:
			oldEnd = self.end
			if self.setAutoincreaseEnd():
				self.log(12, f"Auto increase recording length {int((self.end - oldEnd) / 60)} minute(s).")
				self.state -= 1
				return True
			if self.justplay:
				self.log(12, "End zapping.")
			else:
				self.log(12, "Stop recording.")
			if not self.justplay:
				if self.record_service:
					NavigationInstance.instance.stopRecordService(self.record_service)
					self.record_service = None
			if self.lastend and self.failed:
				self.end = self.lastend
			NavigationInstance.instance.RecordTimer.saveTimers()
			boxInStandby = Screens.Standby.inStandby
			tvNotActive = Screens.Standby.TVinStandby.getTVstate("notactive")
			nextRecordingTime = NavigationInstance.instance.RecordTimer.getNextRecordingTime()
			isStillRecording = NavigationInstance.instance.RecordTimer.getStillRecording()
			isRecordTime = abs(nextRecordingTime - int(time())) <= 900 or isStillRecording
			if DEBUG:
				print(f"[RecordTimer] boxInStandby='{boxInStandby}', tvNotActive='{tvNotActive}', wasRecTimerWakeup='{wasRecTimerWakeup}', self.wasInStandby='{self.wasInStandby}', self.afterEvent='{self.afterEvent}', isRecordTime='{isRecordTime}', nextRecordingTime='{nextRecordingTime}', isStillRecording='{isStillRecording}'.")
			if self.afterEvent == AFTEREVENT.STANDBY or (self.afterEvent == AFTEREVENT.AUTO and self.wasInStandby and (not wasRecTimerWakeup or (wasRecTimerWakeup and isRecordTime))):
				if not boxInStandby and not tvNotActive:  # Not already in standby.
					message = _("A finished record timer wants to set your\n%s %s to standby. Do that now?") % getBoxDisplayName()
					timeout = int(config.usage.shutdown_msgbox_timeout.value)
					if InfoBar and InfoBar.instance:
						InfoBar.instance.openInfoBarMessageWithCallback(self.sendStandbyNotification, message, MessageBox.TYPE_YESNO, timeout, default=True)
					else:
						AddNotificationWithCallback(self.sendStandbyNotification, MessageBox, message, MessageBox.TYPE_YESNO, timeout=timeout, default=True)
				elif not boxInStandby:
					self.sendStandbyNotification(True)
			if isRecordTime or abs(NavigationInstance.instance.RecordTimer.getNextZapTime() - int(time())) <= 900:
				if self.afterEvent == AFTEREVENT.DEEPSTANDBY or (wasRecTimerWakeup and self.afterEvent == AFTEREVENT.AUTO and self.wasInStandby) or (self.afterEvent == AFTEREVENT.AUTO and wasRecTimerWakeup):
					print("[RecordTimer] Recording is running or due to start within 15 minutes so not returning to deepstandby.")
				self.wasInStandby = False
				return True
			elif abs(NavigationInstance.instance.Scheduler.getNextPowerManagerTime() - int(time())) <= 900 or NavigationInstance.instance.Scheduler.isProcessing(exceptTimer=0) or not NavigationInstance.instance.Scheduler.isAutoDeepstandbyEnabled():
				if self.afterEvent == AFTEREVENT.DEEPSTANDBY or (wasRecTimerWakeup and self.afterEvent == AFTEREVENT.AUTO and self.wasInStandby) or (self.afterEvent == AFTEREVENT.AUTO and wasRecTimerWakeup):
					print("[RecordTimer] Scheduler run due within next 15 minutes or is currently active so not returning to deepstandby.")
				self.wasInStandby = False
				self.resetTimerWakeup()
				return True
			if self.afterEvent == AFTEREVENT.DEEPSTANDBY or (wasRecTimerWakeup and self.afterEvent == AFTEREVENT.AUTO and self.wasInStandby):
				if not Screens.Standby.inTryQuitMainloop:  # No shutdown as message box is open.
					if not boxInStandby and not tvNotActive:  # Not already in standby.
						message = _("A finished record timer wants to shut down\nyour %s %s. Shutdown now?") % getBoxDisplayName()
						timeout = int(config.usage.shutdown_msgbox_timeout.value)
						if InfoBar and InfoBar.instance:
							InfoBar.instance.openInfoBarMessageWithCallback(self.sendTryQuitMainloopNotification, message, MessageBox.TYPE_YESNO, timeout=timeout, default=True)
						else:
							AddNotificationWithCallback(self.sendTryQuitMainloopNotification, MessageBox, message, MessageBox.TYPE_YESNO, timeout=timeout, default=True)
					else:
						print("[RecordTimer] quitMainloop #1.")
						quitMainloop(1)
			elif self.afterEvent == AFTEREVENT.AUTO and wasRecTimerWakeup:
				if not Screens.Standby.inTryQuitMainloop:  # No shutdown message box is open.
					if Screens.Standby.inStandby:  # In standby.
						print("[RecordTimer] quitMainloop #2.")
						quitMainloop(1)
			self.wasInStandby = False
			self.resetTimerWakeup()
			return True

	def resetTimerWakeup(self):  # Reset wakeup state after ending timer.
		global wasRecTimerWakeup
		if exists(TIMER_FLAG_FILE):
			remove(TIMER_FLAG_FILE)
			if DEBUG:
				print("[RecordTimer] Reset wakeup state.")
		wasRecTimerWakeup = False

	def getNextActivation(self, getNextStbPowerOn=False):
		self.isStillRecording = False
		nextState = self.state + 1
		if getNextStbPowerOn:
			if nextState == 3:
				self.isStillRecording = True
				nextDay = 0
				countDay = 0
				weekdayTimer = datetime.fromtimestamp(self.begin).isoweekday() * -1
				weekdayRepeated = bin(128 + int(self.repeated))
				for day in range(weekdayTimer - 1, -8, -1):
					countDay += 1
					if int(weekdayRepeated[day]):
						nextDay = day
						break
				if nextDay == 0:
					for day in range(-1, weekdayTimer - 1, -1):
						countDay += 1
						if int(weekdayRepeated[day]):
							break
				return self.start_prepare + 86400 * countDay
			elif nextState == 2:
				return self.begin
			elif nextState == 1:
				return self.start_prepare
			else:
				return -1
		if self.state == self.StateEnded or self.state == self.StateFailed:
			if self.end > int(time()):
				self.isStillRecording = True
			return self.end
		if nextState == self.StateEnded or nextState == self.StateFailed:
			if self.end > int(time()):
				self.isStillRecording = True
		return {
			self.StatePrepared: self.start_prepare,
			self.StateRunning: self.begin,
			self.StateEnded: self.end
		}[nextState]

	def timeChanged(self):
		oldPrepare = self.start_prepare
		self.start_prepare = int(self.begin) - config.recording.prepare_time.value  # self.prepare_time
		self.backoff = 0
		if oldPrepare > 60 and oldPrepare != self.start_prepare:
			self.log(15, f"Record time changed, start prepare is now {ctime(self.start_prepare)}.")

	def do_backoff(self):
		if self.backoff == 0:
			self.backoff = 5
		else:
			self.backoff *= 2
			if self.backoff > 100:
				self.backoff = 100
		self.log(10, f"Backoff, retry in {self.backoff} seconds.")

	def log(self, code, msg):
		self.log_entries.append((int(time()), code, msg))
		print(f"[RecordTimer] Log: '{msg}'.")

	def setAutoincreaseEnd(self, entry=None):
		if not self.autoincrease:
			return False
		newEnd = int(time()) + self.autoincreasetime if entry is None else entry.begin - 30
		dummyTimer = RecordTimerEntry(
			self.service_ref, self.begin, newEnd, self.name, self.description, self.eit, disabled=True,
			justplay=self.justplay, afterEvent=self.afterEvent, dirname=self.dirname, tags=self.tags
		)
		dummyTimer.disabled = self.disabled
		timerSanityCheck = TimerSanityCheck(NavigationInstance.instance.RecordTimer.timer_list, dummyTimer)
		if not timerSanityCheck.check():
			simulTimerList = timerSanityCheck.getSimulTimerList()
			if simulTimerList is not None and len(simulTimerList) > 1:
				newEnd = simulTimerList[1].begin
				newEnd -= 30  # Allow 30 seconds for prepare.
		if newEnd <= int(time()):
			return False
		self.end = newEnd
		return True

	def sendStandbyNotification(self, answer):
		if answer:
			session = Screens.Standby.Standby
			if InfoBar and InfoBar.instance:
				InfoBar.instance.openInfoBarSession(session, None)
			else:
				AddNotification(session)

	def sendTryQuitMainloopNotification(self, answer):
		if answer:
			session = Screens.Standby.TryQuitMainloop
			if InfoBar and InfoBar.instance:
				InfoBar.instance.openInfoBarSession(session, 1)
			else:
				AddNotification(session, 1)

	def mountTest(self, dirname, cmd):
		if cmd == "writeable":
			if not access(dirname, W_OK):
				self.stopMountText(None, cmd)
		elif cmd == "freespace":
			try:
				s = statvfs(dirname)
				if (s.f_bavail * s.f_bsize) // 1000000 < 1024:
					self.stopMountText(None, cmd)
			except FileNotFoundError:
				self.stopMountText(None, "writeable")

	def stopMountText(self, thread, cmd):
		if thread and thread.is_alive():
			print(f"[RecordTimer] Timeout thread: '{cmd}'.")
			thread.join(timeout=1)
		if cmd == "writeable":
			self.mountPathErrorNumber = 2
		elif cmd == "freespace":
			self.mountPathErrorNumber = 3

	def freespace(self, WRITEERROR=False):
		if WRITEERROR:
			dirname = self.mountPath
			if findSafeRecordPath(dirname) is None:
				return (f"mount '{dirname}' is not available.", 1)
		else:
			self.mountPath = None
			if not self.dirname:
				dirname = findSafeRecordPath(defaultMoviePath())
			else:
				dirname = findSafeRecordPath(self.dirname)
				if dirname is None:
					dirname = findSafeRecordPath(defaultMoviePath())
					self.dirnameHadToFallback = True
			if not dirname:
				dirname = self.dirname
				if not dirname:
					dirname = defaultMoviePath() or "-"
				self.log(0, f"Mount '{dirname}' is not available.")
				self.mountPathErrorNumber = 1
				return False
		self.mountPathErrorNumber = 0
		for cmd in ("writeable", "freespace"):
			print(f"[RecordTimer] Starting thread: '{cmd}'.")
			processThread = Thread(target=self.mountTest, args=(dirname, cmd))
			timerThread = ThreadTimer(5, self.stopMountText, args=(processThread, cmd))
			timerThread.start()
			processThread.start()
			processThread.join()
			timerThread.cancel()
			if self.mountPathErrorNumber:
				print(f"[RecordTimer] Break: Error number {self.mountPathErrorNumber}.")
				break
			print(f"[RecordTimer] Finished thread: '{cmd}'.")
		if WRITEERROR:
			if self.mountPathErrorNumber == 2:
				return (f"mount '{dirname}' is not writable.", 2)
			elif self.mountPathErrorNumber == 3:
				return (f"mount '{dirname}' has not enough free space to record.", 3)
			else:
				return ("unknown error.", 0)
		if self.mountPathErrorNumber == 2:
			self.log(0, f"Mount '{dirname}' is not writable.")
			return False
		elif self.mountPathErrorNumber == 3:
			self.log(0, f"Mount '{dirname}' has insufficient free space to record.")
			return False
		else:
			if DEBUG:
				self.log(0, "Found enough free space to record.")
			self.mountPathRetryCounter = 0
			self.mountPathErrorNumber = 0
			self.mountPath = dirname
			return True

	def calculateFilename(self, name=None):
		beginDate = strftime("%Y%m%d %H%M", localtime(self.begin))
		name = name or self.name
		filename = f"{beginDate} - {self.service_ref.getServiceName()}"
		if name:
			if config.recording.filename_composition.value == "veryveryshort":
				filename = name
			elif config.recording.filename_composition.value == "veryshort":
				filename = f"{name} - {beginDate}"
			elif config.recording.filename_composition.value == "short":
				filename = f"{strftime('%Y%m%d', localtime(self.begin))} - {name}"
			elif config.recording.filename_composition.value == "shortwithtime":
				filename = f"{strftime('%Y%m%d %H%M', localtime(self.begin))} - {name}"
			elif config.recording.filename_composition.value == "long":
				filename = f"{filename} - {name} - {self.description}"
			else:
				filename = f"{filename} - {name}"  # Standard.
		if config.recording.ascii_filenames.value:
			filename = legacyEncode(filename)
		self.Filename = getRecordingFilename(filename, self.mountPath)
		if DEBUG:
			self.log(0, f"Filename calculated as '{self.Filename}'.")
		return self.Filename

	def getEventFromEPGId(self, id=None):
		id = id or self.eit
		epgCache = eEPGCache.getInstance()
		reference = self.service_ref and self.service_ref.ref
		return id and epgCache.lookupEventId(reference, id) or None

	def getEventFromEPG(self):
		epgCache = eEPGCache.getInstance()
		queryTime = self.begin + (self.end - self.begin) // 2
		reference = self.service_ref and self.service_ref.ref
		return epgCache.lookupEventTime(reference, queryTime)

	def tryPrepare(self):
		if self.justplay:
			return True
		else:
			if not self.calculateFilename():
				self.do_backoff()
				self.start_prepare = int(time()) + self.backoff
				return False
			recordingReference = self.service_ref and self.service_ref.ref
			if recordingReference and recordingReference.flags & eServiceReference.isGroup:
				recordingReference = getBestPlayableServiceReference(recordingReference, eServiceReference())
				if not recordingReference:
					self.log(1, "The 'get best playable service for group... record' call failed!")
					return False
			self.setRecordingPreferredTuner()
			self.record_service = recordingReference and NavigationInstance.instance.recordService(recordingReference, False, pNavigation.isRealRecording)
			if not self.record_service:
				self.log(1, "The 'record service' call failed!")
				self.setRecordingPreferredTuner(setdefault=True)
				return False
			name = self.name
			description = self.description
			if self.repeated:
				epgCache = eEPGCache.getInstance()
				queryTime = self.begin + (self.end - self.begin) // 2
				event = epgCache.lookupEventTime(recordingReference, queryTime)
				if event:
					if self.rename_repeat:
						eventDescription = event.getShortDescription()
						if not eventDescription:
							eventDescription = event.getExtendedDescription()
						if eventDescription and eventDescription != description:
							description = eventDescription
						eventName = event.getEventName()
						if eventName and eventName != name:
							name = eventName
							if not self.calculateFilename(eventName):
								self.do_backoff()
								self.start_prepare = int(time()) + self.backoff
								return False
					eventId = event.getEventId()
				else:
					eventId = -1
			else:
				eventId = self.eit
				if eventId is None:
					eventId = -1
			prepareResult = self.record_service.prepare(f"{self.Filename}{self.record_service.getFilenameExtension()}", self.begin, self.end, eventId, name.replace("\n", " "), description.replace("\n", " "), " ".join(self.tags), bool(self.descramble), bool(self.record_ecm))
			if prepareResult:
				if prepareResult == -255:
					self.log(4, "Failed to write meta information!")
				else:
					self.log(2, f"The 'prepare' call failed with error {prepareResult}!")
				# We must calculate only start time before stopRecordService call because in Screens/Standby.py TryQuitMainloop
				# tries to get the next start time in evEnd event handler.
				self.do_backoff()
				self.start_prepare = int(time()) + self.backoff
				NavigationInstance.instance.stopRecordService(self.record_service)
				self.record_service = None
				self.setRecordingPreferredTuner(setdefault=True)
				return False
			return True

	def keypress(self, key=None, flag=1):
		if flag and self.wasInStandby:
			self.wasInStandby = False
			eActionMap.getInstance().unbindAction("", self.keypress)

	def setRecordingPreferredTuner(self, setdefault=False):
		if self.needChangePriorityFrontend:
			tuner = None
			if not self.change_frontend and not setdefault:
				tuner = config.usage.recording_frontend_priority_intval.value
				self.change_frontend = True
			elif self.change_frontend and setdefault:
				tuner = config.usage.frontend_priority_intval.value
				self.change_frontend = False
			if tuner is not None:
				setPreferredTuner(int(tuner))

	def failureCB_pip(self, answer):
		if answer:
			self.log(13, "Okay, disable PiP.")
			global InfoBar
			if not InfoBar:
				from Screens.InfoBar import InfoBar
			from Screens.InfoBarGenerics import InfoBarPiP
			from Components.ServiceEventTracker import InfoBarCount
			InfoBarInstance = InfoBarCount == 1 and InfoBar.instance
			if InfoBarInstance:
				InfoBarPiP.showPiP(InfoBarInstance)
				self.messageString += _("Disabled PiP.\n")
			else:
				self.log(14, "Tried to disable PiP, suddenly found no InfoBar.instance!")
				self.messageString += _("Tried to disable PiP, but found no InfoBar instance!\n")
			if config.recording.ask_to_abort_pip.value in ("ask", "abort_msg"):
				self.messageStringShow = True
			self.justTriedFreeingTuner = True
		else:
			self.log(14, "User didn't want to disable PiP, try other methods of freeing a tuner.")
		self.messageBoxAnswerPending = False

	def failureCB_pseudo_rec(self, answer):
		if answer:
			self.log(13, "Okay, abort pseudo recordings.")
			for rec in NavigationInstance.instance.getRecordings(False, pNavigation.isPseudoRecording):
				NavigationInstance.instance.stopRecordService(rec)
				self.messageString += _("Aborted a pseudo recording.\n")
			if config.recording.ask_to_abort_pseudo_rec.value in ("ask", "abort_msg"):
				self.messageStringShow = True
			self.justTriedFreeingTuner = True
		else:
			self.log(14, "User didn't want to abort pseudo recordings, try other methods of freeing a tuner.")
		self.messageBoxAnswerPending = False

	def failureCB_streaming(self, answer):
		if answer:
			self.log(13, "Okay, abort streaming.")
			for rec in NavigationInstance.instance.getRecordings(False, pNavigation.isStreaming):
				NavigationInstance.instance.stopRecordService(rec)
				self.messageString += _("Aborted a streaming service.\n")
			if config.recording.ask_to_abort_streaming.value in ("ask", "abort_msg"):
				self.messageStringShow = True
			self.justTriedFreeingTuner = True
		else:
			self.log(14, "User didn't want to abort streaming, try other methods of freeing a tuner.")
		self.messageBoxAnswerPending = False

	def failureCB(self, answer):
		if answer:
			self.log(13, "Okay, zapped away.")
			self.messageString += _("The TV was switched to the recording service!\n")
			self.messageStringShow = True
			# NavigationInstance.instance.stopUserServices()
			if InfoBar and InfoBar.instance and InfoBar.instance.servicelist:
				InfoBar.instance.servicelist.performZap(self.service_ref.ref)
			else:
				NavigationInstance.instance.playService(self.service_ref.ref)
			self.justTriedFreeingTuner = True
		else:
			self.log(14, "User didn't want to zap away, recording will probably fail!")
		self.messageBoxAnswerPending = False

	def check_justplay(self):
		if self.justplay:
			self.always_zap = False

	def gotRecordEvent(self, record, event):
		# DEBUG: This is not working (never true), please fix. (Comparing two swig wrapped ePtrs.)
		if self.__record_service.__deref__() != record.__deref__():
			return
		# self.log(16, f"Record event {event}.")
		if event == iRecordableService.evRecordWriteError:
			if self.record_service:
				NavigationInstance.instance.stopRecordService(self.record_service)
				self.record_service = None
			self.failed = True
			self.lastend = self.end
			self.end = int(time()) + 5
			self.backoff = 0
			msg, err = self.freespace(True)
			self.log(16, f"Write error while recording, {msg}")
			print(f"[RecordTimer] Write error while recording, {msg}")
			# Show notification. The 'id' will make sure that it will be displayed only once, even if
			# more timers are failing at the same time which is very likely in case of disk full.
			AddPopup(text=_("Write error while recording. %s") % (_("An unknown error occurred!"), _("Storage device not found!"), _("Storage device not writable!"), _("Storage device full!"))[err], type=MessageBox.TYPE_ERROR, timeout=0, id="DiskFullMessage")
			# Okay, the recording has been stopped. We need to properly note that in our
			# state, with also keeping the possibility to re-try.
			# DEBUG: This has to be done!
		elif event == iRecordableService.evStart:
			text = _("A recording has been started:\n%s") % self.name
			notify = config.usage.show_message_when_recording_starts.value and not Screens.Standby.inStandby
			if self.dirnameHadToFallback:
				text = "\n".join((text, _("Please note that the previously selected media could not be accessed and therefore the default directory is being used instead.")))
				notify = True
			if notify:
				AddPopup(text=text, type=MessageBox.TYPE_INFO, timeout=3)
		elif event == iRecordableService.evRecordAborted:
			NavigationInstance.instance.RecordTimer.removeEntry(self)
		elif event == iRecordableService.evGstRecordEnded:
			if self.repeated:
				self.processRepeated(findRunningEvent=False)
			NavigationInstance.instance.RecordTimer.doActivate(self)

	def setRecordService(self, service):  # We have record_service as property to automatically subscribe to record service events.
		if self.__record_service is not None:
			# print("[RecordTimer] Remove callback.")
			NavigationInstance.instance.record_event.remove(self.gotRecordEvent)
		self.__record_service = service
		if self.__record_service is not None:
			# print("[RecordTimer] Add callback.")
			NavigationInstance.instance.record_event.append(self.gotRecordEvent)

	record_service = property(lambda self: self.__record_service, setRecordService)
