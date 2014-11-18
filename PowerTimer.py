import os
from boxbranding import getMachineBrand, getMachineName
import xml.etree.cElementTree
from time import ctime, time
from bisect import insort

from enigma import eActionMap, quitMainloop

from Components.config import config
from Components.TimerSanityCheck import TimerSanityCheck
from Screens.MessageBox import MessageBox
import Screens.Standby
from Tools import Directories, Notifications
from Tools.XMLTools import stringToXML
import timer
import NavigationInstance

#global variables begin
DSsave = False
RSsave = False
RBsave = False
aeDSsave = False
wasPowerTimerWakeup = False
wakeupEnd = time()
netbytes = 0
netpackets = 0
#global variables end

#reset wakeupstatus
def resetTimerWakeup():
	global wasPowerTimerWakeup
	if os.path.exists("/tmp/was_powertimer_wakeup"):
		os.remove("/tmp/was_powertimer_wakeup")	
	wasPowerTimerWakeup = False

# parses an event, and gives out a (begin, end, name, duration, eit)-tuple.
# begin and end will be corrected
def parseEvent(ev):
	begin = ev.getBeginTime()
	end = begin + ev.getDuration()
	return begin, end

class AFTEREVENT:
	def __init__(self):
		pass

	NONE = 0
	WAKEUPTOSTANDBY = 1
	STANDBY = 2
	DEEPSTANDBY = 3

class TIMERTYPE:
	def __init__(self):
		pass

	NONE = 0
	WAKEUP = 1
	WAKEUPTOSTANDBY = 2
	AUTOSTANDBY = 3
	AUTODEEPSTANDBY = 4
	STANDBY = 5
	DEEPSTANDBY = 6
	REBOOT = 7
	RESTART = 8

# please do not translate log messages
class PowerTimerEntry(timer.TimerEntry, object):
	def __init__(self, begin, end, disabled = False, afterEvent = AFTEREVENT.NONE, timerType = TIMERTYPE.WAKEUP, checkOldTimers = False, autosleepdelay = 60):
		global wakeupEnd
		timer.TimerEntry.__init__(self, int(begin), int(end))
		if checkOldTimers:
			if self.begin < time() - 1209600:
				self.begin = int(time())

		if self.end < self.begin:
			self.end = self.begin

		self.dontSave = False
		self.disabled = disabled
		self.timer = None
		self.__record_service = None
		self.start_prepare = 0
		self.timerType = timerType
		self.afterEvent = afterEvent
		self.autoincrease = False
		self.autoincreasetime = 3600 * 24 # 1 day
		self.autosleepinstandbyonly = 'no'
		self.autosleepdelay = autosleepdelay
		self.autosleeprepeat = 'once'

		self.log_entries = []
		self.resetState()

		#check autopowertimer
		if (self.timerType == TIMERTYPE.AUTOSTANDBY or self.timerType == TIMERTYPE.AUTODEEPSTANDBY) and not self.disabled and time() > 3600 and self.begin > time():
			self.begin = time()						#the begin is in the future -> set to current time = no start delay of this timer

		#check startuptimer
		if self.timerType == TIMERTYPE.WAKEUP or self.timerType == TIMERTYPE.WAKEUPTOSTANDBY:
			if abs(time() - self.begin) <= 300:		#begin within 5 minutes -> this is wakeuptimer
				if self.end > time():
					wakeupEnd = self.end
				else:
					wakeupEnd = time() + 3600		#no endtime listed, 1hour suppression of autodeepstandby and other overlapping powertimer
		wuEnd = time () + 43200						#limitation to 12hours  suppression of ...
		if wakeupEnd > wuEnd:
			wakeupEnd = wuEnd

	def __repr__(self):
		timertype = {
			TIMERTYPE.WAKEUP: "wakeup",
			TIMERTYPE.WAKEUPTOSTANDBY: "wakeuptostandby",
			TIMERTYPE.AUTOSTANDBY: "autostandby",
			TIMERTYPE.AUTODEEPSTANDBY: "autodeepstandby",
			TIMERTYPE.STANDBY: "standby",
			TIMERTYPE.DEEPSTANDBY: "deepstandby",
			TIMERTYPE.REBOOT: "reboot",
			TIMERTYPE.RESTART: "restart"
			}[self.timerType]
		if not self.disabled:
			return "PowerTimerEntry(type=%s, begin=%s)" % (timertype, ctime(self.begin))
		else:
			return "PowerTimerEntry(type=%s, begin=%s Disabled)" % (timertype, ctime(self.begin))

	def log(self, code, msg):
		self.log_entries.append((int(time()), code, msg))

	def do_backoff(self):
		if Screens.Standby.inStandby:
			self.backoff = 300
		else:
			if self.backoff == 0:
				self.backoff = 5*60
			else:
				self.backoff *= 2
				if self.backoff > 1800:
					self.backoff = 1800
		self.log(10, "backoff: retry in %d minuets" % (int(self.backoff)/60))

	def activate(self):
		global DSsave, RSsave, RBsave, aeDSsave, wasPowerTimerWakeup, wakeupEnd

		next_state = self.state + 1
		self.log(5, "activating state %d" % next_state)

		if next_state == 1 and (self.timerType == TIMERTYPE.AUTOSTANDBY or self.timerType == TIMERTYPE.AUTODEEPSTANDBY):
			eActionMap.getInstance().bindAction('', -0x7FFFFFFF, self.keyPressed)
			self.begin = time() + int(self.autosleepdelay)*60
			if self.end <= self.begin:
				self.end = self.begin

		if next_state == self.StatePrepared:
			self.log(6, "prepare ok, waiting for begin")
			self.next_activation = self.begin
			self.backoff = 0
			return True

		elif next_state == self.StateRunning:

			if os.path.exists("/tmp/was_powertimer_wakeup") and not wasPowerTimerWakeup:
				wasPowerTimerWakeup = int(open("/tmp/was_powertimer_wakeup", "r").read()) and True or False

			if wasPowerTimerWakeup and time() >= wakeupEnd:
				resetTimerWakeup()

			# if this timer has been cancelled, just go to "end" state.
			if self.cancelled:
				return True

			if self.failed:
				return True

			if self.timerType == TIMERTYPE.WAKEUP:
				if Screens.Standby.inStandby:
					Screens.Standby.inStandby.Power()
				return True

			elif self.timerType == TIMERTYPE.WAKEUPTOSTANDBY:
				return True

			elif self.timerType == TIMERTYPE.STANDBY:
				if not Screens.Standby.inStandby: # not already in standby
					Notifications.AddNotificationWithCallback(self.sendStandbyNotification, MessageBox, _("A finished powertimer wants to set your\n%s %s to standby. Do that now?") % (getMachineBrand(), getMachineName()), timeout = 180)
				return True

			elif self.timerType == TIMERTYPE.AUTOSTANDBY:
				if not Screens.Standby.inStandby: # not already in standby
					Notifications.AddNotificationWithCallback(self.sendStandbyNotification, MessageBox, _("A finished powertimer wants to set your\n%s %s to standby. Do that now?") % (getMachineBrand(), getMachineName()), timeout = 180)
					if self.autosleeprepeat == "once":
						eActionMap.getInstance().unbindAction('', self.keyPressed)
						return True
					else:
						self.begin = time() + int(self.autosleepdelay)*60
						if self.end <= self.begin:
							self.end = self.begin
				else:
					self.begin = time() + int(self.autosleepdelay)*60
					if self.end <= self.begin:
						self.end = self.begin

			elif self.timerType == TIMERTYPE.AUTODEEPSTANDBY:
				if self.getNetworkTraffic() or wasPowerTimerWakeup or (NavigationInstance.instance.RecordTimer.isRecording() or abs(NavigationInstance.instance.RecordTimer.getNextRecordingTime() - time()) <= 900 or abs(NavigationInstance.instance.RecordTimer.getNextZapTime() - time()) <= 900) or ((self.autosleepinstandbyonly == 'yesNWno' or self.autosleepinstandbyonly == 'yes') and not Screens.Standby.inStandby):
					self.do_backoff()
					# retry
					self.begin = time() + self.backoff
					if self.end <= self.begin:
						self.end = self.begin
					return False
				if not Screens.Standby.inTryQuitMainloop: # not a shutdown messagebox is open
					if self.autosleeprepeat == "once":
						self.disabled = True
					if Screens.Standby.inStandby: # in standby
						print "[PowerTimer] quitMainloop #1"
						quitMainloop(1)
						return True
					else:
						Notifications.AddNotificationWithCallback(self.sendTryQuitMainloopNotification, MessageBox, _("A finished powertimer wants to shutdown your %s %s.\nDo that now?") % (getMachineBrand(), getMachineName()), timeout = 180)
						if self.autosleeprepeat == "once":
							eActionMap.getInstance().unbindAction('', self.keyPressed)
							return True
						else:
							self.begin = time() + int(self.autosleepdelay)*60
							if self.end <= self.begin:
								self.end = self.begin

			elif self.timerType == TIMERTYPE.DEEPSTANDBY:
				if wasPowerTimerWakeup or NavigationInstance.instance.RecordTimer.isRecording() or abs(NavigationInstance.instance.RecordTimer.getNextRecordingTime() - time()) <= 900 or abs(NavigationInstance.instance.RecordTimer.getNextZapTime() - time()) <= 900:
					if int(self.repeated) > 0 and not DSsave:
						self.DSbegin = self.begin
						self.DSend = self.end
						DSsave = True
					self.do_backoff()
					# retry
					self.begin = time() + self.backoff
					if self.end <= self.begin:
						self.end = self.begin
					return False
				if not Screens.Standby.inTryQuitMainloop: # not a shutdown messagebox is open
					if DSsave:
						DSsave = False
						self.begin = self.DSbegin
						self.end = self.DSend
					if Screens.Standby.inStandby: # in standby
						print "[PowerTimer] quitMainloop #2"
						quitMainloop(1)
					else:
						Notifications.AddNotificationWithCallback(self.sendTryQuitMainloopNotification, MessageBox, _("A finished powertimer wants to shutdown your %s %s.\nDo that now?") % (getMachineBrand(), getMachineName()), timeout = 180)
				return True

			elif self.timerType == TIMERTYPE.REBOOT:
				if wasPowerTimerWakeup or NavigationInstance.instance.RecordTimer.isRecording() or abs(NavigationInstance.instance.RecordTimer.getNextRecordingTime() - time()) <= 900 or abs(NavigationInstance.instance.RecordTimer.getNextZapTime() - time()) <= 900:
					if int(self.repeated) > 0 and not RBsave:
						self.RBbegin = self.begin
						self.RBend = self.end
						RBsave = True
					self.do_backoff()
					# retry
					self.begin = time() + self.backoff
					if self.end <= self.begin:
						self.end = self.begin
					return False
				if not Screens.Standby.inTryQuitMainloop: # not a shutdown messagebox is open
					if RBsave:
						RBsave = False
						self.begin = self.RBbegin
						self.end = self.RBend
					if Screens.Standby.inStandby: # in standby
						print "[PowerTimer] quitMainloop #3"
						quitMainloop(2)
					else:
						Notifications.AddNotificationWithCallback(self.sendTryToRebootNotification, MessageBox, _("A finished powertimer wants to reboot your %s %s.\nDo that now?") % (getMachineBrand(), getMachineName()), timeout = 180)
				return True

			elif self.timerType == TIMERTYPE.RESTART:
				if wasPowerTimerWakeup or NavigationInstance.instance.RecordTimer.isRecording() or abs(NavigationInstance.instance.RecordTimer.getNextRecordingTime() - time()) <= 900 or abs(NavigationInstance.instance.RecordTimer.getNextZapTime() - time()) <= 900:
					if int(self.repeated) > 0 and not RSsave:
						self.RSbegin = self.begin
						self.RSend = self.end
						RSsave = True
					self.do_backoff()
					# retry
					self.begin = time() + self.backoff
					if self.end <= self.begin:
						self.end = self.begin
					return False
				if not Screens.Standby.inTryQuitMainloop: # not a shutdown messagebox is open
					if RSsave:
						RSsave = False
						self.begin = self.RSbegin
						self.end = self.RSend
					if Screens.Standby.inStandby: # in standby
						print "[PowerTimer] quitMainloop #4"
						quitMainloop(3)
					else:
						Notifications.AddNotificationWithCallback(self.sendTryToRestartNotification, MessageBox, _("A finished powertimer wants to restart the user interface.\nDo that now?"), timeout = 180)
				return True

		elif next_state == self.StateEnded:
			resetTimerWakeup()
			NavigationInstance.instance.PowerTimer.saveTimer()
			if self.afterEvent == AFTEREVENT.STANDBY:
				if not Screens.Standby.inStandby: # not already in standby
					Notifications.AddNotificationWithCallback(self.sendStandbyNotification, MessageBox, _("A finished powertimer wants to set your\n%s %s to standby. Do that now?") % (getMachineBrand(), getMachineName()), timeout = 180)
			elif self.afterEvent == AFTEREVENT.DEEPSTANDBY:
				if NavigationInstance.instance.RecordTimer.isRecording() or abs(NavigationInstance.instance.RecordTimer.getNextRecordingTime() - time()) <= 900 or abs(NavigationInstance.instance.RecordTimer.getNextZapTime() - time()) <= 900:
					if int(self.repeated) > 0 and not aeDSsave:
						self.aeDSbegin = self.begin
						self.aeDSend = self.end
						aeDSsave = True
					self.do_backoff()
					# retry
					self.begin = time() + self.backoff
					if self.end <= self.begin:
						self.end = self.begin
					return False
				if not Screens.Standby.inTryQuitMainloop: # not a shutdown messagebox is open
					if aeDSsave:
						aeDSsave = False
						self.begin = self.aeDSbegin
						self.end = self.aeDSend
					if Screens.Standby.inStandby: # in standby
						print "[PowerTimer] quitMainloop #5"
						quitMainloop(1)
					else:
						Notifications.AddNotificationWithCallback(self.sendTryQuitMainloopNotification, MessageBox, _("A finished power timer wants to shut down\nyour %s %s. Shutdown now?") % (getMachineBrand(), getMachineName()), timeout = 180)
			return True

	def setAutoincreaseEnd(self, entry = None):
		if not self.autoincrease:
			return False
		if entry is None:
			new_end =  int(time()) + self.autoincreasetime
		else:
			new_end = entry.begin -30

		dummyentry = PowerTimerEntry(self.begin, new_end, disabled=True, afterEvent = self.afterEvent, timerType = self.timerType)
		dummyentry.disabled = self.disabled
		timersanitycheck = TimerSanityCheck(NavigationInstance.instance.PowerManager.timer_list, dummyentry)
		if not timersanitycheck.check():
			simulTimerList = timersanitycheck.getSimulTimerList()
			if simulTimerList is not None and len(simulTimerList) > 1:
				new_end = simulTimerList[1].begin
				new_end -= 30				# 30 Sekunden Prepare-Zeit lassen
		if new_end <= time():
			return False
		self.end = new_end
		return True

	def sendStandbyNotification(self, answer):
		if answer:
			Notifications.AddNotification(Screens.Standby.Standby)

	def sendTryQuitMainloopNotification(self, answer):
		if answer:
			Notifications.AddNotification(Screens.Standby.TryQuitMainloop, 1)

	def sendTryToRebootNotification(self, answer):
		if answer:
			Notifications.AddNotification(Screens.Standby.TryQuitMainloop, 2)

	def sendTryToRestartNotification(self, answer):
		if answer:
			Notifications.AddNotification(Screens.Standby.TryQuitMainloop, 3)

	def keyPressed(self, key, tag):
		self.begin = time() + int(self.autosleepdelay)*60
		if self.end <= self.begin:
			self.end = self.begin

	def getNextActivation(self):
		if self.state == self.StateEnded or self.state == self.StateFailed:
			return self.end

		next_state = self.state + 1

		return {self.StatePrepared: self.start_prepare,
				self.StateRunning: self.begin,
				self.StateEnded: self.end }[next_state]

	def getNextWakeup(self):
		if self.state == self.StateEnded or self.state == self.StateFailed:
			return self.end

		if self.timerType != TIMERTYPE.WAKEUP and self.timerType != TIMERTYPE.WAKEUPTOSTANDBY and not self.afterEvent:
			return -1
		elif self.timerType != TIMERTYPE.WAKEUP and self.timerType != TIMERTYPE.WAKEUPTOSTANDBY and self.afterEvent:
			return self.end
		next_state = self.state + 1
		return {self.StatePrepared: self.start_prepare,
				self.StateRunning: self.begin,
				self.StateEnded: self.end }[next_state]

	def timeChanged(self):
		old_prepare = self.start_prepare
		self.start_prepare = self.begin - self.prepare_time
		self.backoff = 0

		if int(old_prepare) > 60 and int(old_prepare) != int(self.start_prepare):
			self.log(15, "time changed, start prepare is now: %s" % ctime(self.start_prepare))

	def getNetworkTraffic(self):
		global netbytes, netpackets
		oldbytes = netbytes
		oldpackets = netpackets
		newbytes = 0
		newpackets = 0
		if Screens.Standby.inStandby and self.autosleepinstandbyonly == 'yesNWno':
			try:
				if os.path.exists('/proc/net/dev'):
					f = open('/proc/net/dev', 'r')
					temp = f.readlines()
					f.close()
					for lines in temp:
						lisp = lines.split()
						if lisp[0].endswith(':') and (lisp[0].startswith('eth') or lisp[0].startswith('wlan')):
							newbytes += int(lisp[1]) + int(lisp[9])
							newpackets += int(lisp[2]) + int(lisp[10])
					netbytes = newbytes
					netpackets = newpackets
					print '[PowerTimer] Receive/Transmit Bytes : ', str(newbytes - oldbytes), '(' + str(int((newbytes - oldbytes)/1024/1024)) + ' MBytes)'
					#print '[PowerTimer] Receive/Transmit Packets : ', str(newpackets - oldpackets)
					if (newbytes - oldbytes) > 1000000:	# or (newpackets - oldpackets) > 3000:	#packets deactivated
						return True
			except:
				print '[PowerTimer] Receive/Transmit Bytes or Packets : Error reading values! Use "cat /proc/net/dev" for testing on command line.'
		return False

def createTimer(xml):
	timertype = str(xml.get("timertype") or "wakeup")
	timertype = {
		"wakeup": TIMERTYPE.WAKEUP,
		"wakeuptostandby": TIMERTYPE.WAKEUPTOSTANDBY,
		"autostandby": TIMERTYPE.AUTOSTANDBY,
		"autodeepstandby": TIMERTYPE.AUTODEEPSTANDBY,
		"standby": TIMERTYPE.STANDBY,
		"deepstandby": TIMERTYPE.DEEPSTANDBY,
		"reboot": TIMERTYPE.REBOOT,
		"restart": TIMERTYPE.RESTART
		}[timertype]
	begin = int(xml.get("begin"))
	end = int(xml.get("end"))
	repeated = xml.get("repeated").encode("utf-8")
	disabled = long(xml.get("disabled") or "0")
	afterevent = str(xml.get("afterevent") or "nothing")
	afterevent = {
		"nothing": AFTEREVENT.NONE,
		"wakeuptostandby": AFTEREVENT.WAKEUPTOSTANDBY,
		"standby": AFTEREVENT.STANDBY,
		"deepstandby": AFTEREVENT.DEEPSTANDBY
		}[afterevent]
	autosleepinstandbyonly = str(xml.get("autosleepinstandbyonly") or "no")
	autosleepdelay = str(xml.get("autosleepdelay") or "0")
	autosleeprepeat = str(xml.get("autosleeprepeat") or "once")

	entry = PowerTimerEntry(begin, end, disabled, afterevent, timertype)
	entry.repeated = int(repeated)
	entry.autosleepinstandbyonly = autosleepinstandbyonly
	entry.autosleepdelay = int(autosleepdelay)
	entry.autosleeprepeat = autosleeprepeat

	for l in xml.findall("log"):
		ltime = int(l.get("time"))
		code = int(l.get("code"))
		msg = l.text.strip().encode("utf-8")
		entry.log_entries.append((ltime, code, msg))

	return entry

class PowerTimer(timer.Timer):
	def __init__(self):
		timer.Timer.__init__(self)

		self.Filename = Directories.resolveFilename(Directories.SCOPE_CONFIG, "pm_timers.xml")

		try:
			self.loadTimer()
		except IOError:
			print "unable to load timers from file!"

	def doActivate(self, w):
		# when activating a timer which has already passed,
		# simply abort the timer. don't run trough all the stages.
		if w.shouldSkip():
			w.state = PowerTimerEntry.StateEnded
		else:
			# when active returns true, this means "accepted".
			# otherwise, the current state is kept.
			# the timer entry itself will fix up the delay then.
			if w.activate():
				w.state += 1

		try:
			self.timer_list.remove(w)
		except:
			print '[PowerManager]: Remove list failed'

		# did this timer reached the last state?
		if w.state < PowerTimerEntry.StateEnded:
			# no, sort it into active list
			insort(self.timer_list, w)
		else:
			# yes. Process repeated, and re-add.
			if w.repeated:
				w.processRepeated()
				w.state = PowerTimerEntry.StateWaiting
				self.addTimerEntry(w)
			else:
				# Remove old timers as set in config
				self.cleanupDaily(config.recording.keep_timers.value)
				insort(self.processed_timers, w)
		self.stateChanged(w)

	def loadTimer(self):
		# TODO: PATH!
		if not Directories.fileExists(self.Filename):
			return
		try:
			file = open(self.Filename, 'r')
			doc = xml.etree.cElementTree.parse(file)
			file.close()
		except SyntaxError:
			from Tools.Notifications import AddPopup
			from Screens.MessageBox import MessageBox

			AddPopup(_("The timer file (pm_timers.xml) is corrupt and could not be loaded."), type = MessageBox.TYPE_ERROR, timeout = 0, id = "TimerLoadFailed")

			print "pm_timers.xml failed to load!"
			try:
				import os
				os.rename(self.Filename, self.Filename + "_old")
			except (IOError, OSError):
				print "renaming broken timer failed"
			return
		except IOError:
			print "pm_timers.xml not found!"
			return

		root = doc.getroot()

		# put out a message when at least one timer overlaps
		checkit = True
		for timer in root.findall("timer"):
			newTimer = createTimer(timer)
			if (self.record(newTimer, True, dosave=False) is not None) and (checkit == True):
				from Tools.Notifications import AddPopup
				from Screens.MessageBox import MessageBox
				AddPopup(_("Timer overlap in pm_timers.xml detected!\nPlease recheck it!"), type = MessageBox.TYPE_ERROR, timeout = 0, id = "TimerLoadFailed")
				checkit = False # at moment it is enough when the message is displayed one time

	def saveTimer(self):
		savedays = 3600 * 24 * 7	#logs older 7 Days will not saved
		list = ['<?xml version="1.0" ?>\n', '<timers>\n']
		for timer in self.timer_list + self.processed_timers:
			if timer.dontSave:
				continue
			list.append('<timer')
			list.append(' timertype="' + str(stringToXML({
				TIMERTYPE.WAKEUP: "wakeup",
				TIMERTYPE.WAKEUPTOSTANDBY: "wakeuptostandby",
				TIMERTYPE.AUTOSTANDBY: "autostandby",
				TIMERTYPE.AUTODEEPSTANDBY: "autodeepstandby",
				TIMERTYPE.STANDBY: "standby",
				TIMERTYPE.DEEPSTANDBY: "deepstandby",
				TIMERTYPE.REBOOT: "reboot",
				TIMERTYPE.RESTART: "restart"
				}[timer.timerType])) + '"')
			list.append(' begin="' + str(int(timer.begin)) + '"')
			list.append(' end="' + str(int(timer.end)) + '"')
			list.append(' repeated="' + str(int(timer.repeated)) + '"')
			list.append(' afterevent="' + str(stringToXML({
				AFTEREVENT.NONE: "nothing",
				AFTEREVENT.WAKEUPTOSTANDBY: "wakeuptostandby",
				AFTEREVENT.STANDBY: "standby",
				AFTEREVENT.DEEPSTANDBY: "deepstandby"
				}[timer.afterEvent])) + '"')
			list.append(' disabled="' + str(int(timer.disabled)) + '"')
			list.append(' autosleepinstandbyonly="' + str(timer.autosleepinstandbyonly) + '"')
			list.append(' autosleepdelay="' + str(timer.autosleepdelay) + '"')
			list.append(' autosleeprepeat="' + str(timer.autosleeprepeat) + '"')
			list.append('>\n')

			for ltime, code, msg in timer.log_entries:
				if ltime > time() - savedays:
					list.append('<log')
					list.append(' code="' + str(code) + '"')
					list.append(' time="' + str(ltime) + '"')
					list.append('>')
					list.append(str(stringToXML(msg)))
					list.append('</log>\n')

			list.append('</timer>\n')

		list.append('</timers>\n')

		file = open(self.Filename + ".writing", "w")
		for x in list:
			file.write(x)
		file.flush()

		os.fsync(file.fileno())
		file.close()
		os.rename(self.Filename + ".writing", self.Filename)

	def getNextZapTime(self):
		now = time()
		for timer in self.timer_list:
			if timer.begin < now:
				continue
			return timer.begin
		return -1

	def getNextPowerManagerTimeOld(self):
		now = time()
		for timer in self.timer_list:
			if timer.timerType != TIMERTYPE.AUTOSTANDBY and timer.timerType != TIMERTYPE.AUTODEEPSTANDBY:
				next_act = timer.getNextWakeup()
				if next_act < now:
					continue
				return next_act
		return -1

	def getNextPowerManagerTime(self):
		nextrectime = self.getNextPowerManagerTimeOld()
		faketime = time()+300
		if config.timeshift.isRecording.value:
			if 0 < nextrectime < faketime:
				return nextrectime
			else:
				return faketime
		else:
			return nextrectime

	def isNextPowerManagerAfterEventActionAuto(self):
		now = time()
		t = None
		for timer in self.timer_list:
			if timer.timerType == TIMERTYPE.WAKEUPTOSTANDBY or timer.afterEvent == AFTEREVENT.WAKEUPTOSTANDBY:
				return True
		return False

	def record(self, entry, ignoreTSC=False, dosave=True):		#wird von loadTimer mit dosave=False aufgerufen
		entry.timeChanged()
		print "[PowerTimer]",str(entry)
		entry.Timer = self
		self.addTimerEntry(entry)
		if dosave:
			self.saveTimer()
		return None

	def removeEntry(self, entry):
		print "[PowerTimer] Remove",str(entry)

		# avoid re-enqueuing
		entry.repeated = False

		# abort timer.
		# this sets the end time to current time, so timer will be stopped.
		entry.autoincrease = False
		entry.abort()

		if entry.state != entry.StateEnded:
			self.timeChanged(entry)

# 		print "state: ", entry.state
# 		print "in processed: ", entry in self.processed_timers
# 		print "in running: ", entry in self.timer_list
		# disable timer first
		if entry.state != 3:
			entry.disable()
		# autoincrease instanttimer if possible
		if not entry.dontSave:
			for x in self.timer_list:
				if x.setAutoincreaseEnd():
					self.timeChanged(x)
		# now the timer should be in the processed_timers list. remove it from there.
		if entry in self.processed_timers:
			self.processed_timers.remove(entry)
		self.saveTimer()

	def shutdown(self):
		self.saveTimer()
