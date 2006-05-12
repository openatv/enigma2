import time
import codecs
#from time import datetime
from Tools import Directories, Notifications

from Components.config import config
import timer
import xml.dom.minidom

from enigma import quitMainloop, eEPGCache, eEPGCachePtr

from Screens.MessageBox import MessageBox
import NavigationInstance
from time import localtime

from Tools.XMLTools import elementsWithTag, mergeText, stringToXML
from ServiceReference import ServiceReference

# ok, for descriptions etc we have:
# service reference  (to get the service name)
# name               (title)
# description        (description)
# event data         (ONLY for time adjustments etc.)


# parses an event, and gives out a (begin, end, name, duration, eit)-tuple.
# begin and end will be corrected
def parseEvent(ev):
	name = ev.getEventName()
	description = ev.getShortDescription()
	begin = ev.getBeginTime()
	end = begin + ev.getDuration()
	eit = ev.getEventId()
	begin -= config.recording.margin_before.value[0] * 60
	end += config.recording.margin_after.value[0] * 60
	return (begin, end, name, description, eit)

class AFTEREVENT:
	NONE = 0
	STANDBY = 1
	DEEPSTANDBY = 2

# please do not translate log messages
class RecordTimerEntry(timer.TimerEntry):
	def __init__(self, serviceref, begin, end, name, description, eit, disabled = False, justplay = False, afterEvent = AFTEREVENT.NONE, checkOldTimers = False):
		timer.TimerEntry.__init__(self, int(begin), int(end))
		
		if checkOldTimers == True:
			if self.begin < time.time() - 1209600:
				self.begin = int(time.time())
		
		if self.end < self.begin:
			self.end = self.begin
		
		assert isinstance(serviceref, ServiceReference)
		
		self.service_ref = serviceref
		self.eit = eit
		self.dontSave = False
		self.name = name
		self.description = description
		self.disabled = disabled
		self.timer = None
		self.record_service = None
		self.start_prepare = 0
		self.justplay = justplay
		self.afterEvent = afterEvent
		self.session = None
		
		self.log_entries = []
		self.resetState()
	
	def log(self, code, msg):
		self.log_entries.append((int(time.time()), code, msg))
		print "[TIMER]", msg
	
	def resetState(self):
		self.state = self.StateWaiting
		self.cancelled = False
		self.first_try_prepare = True
		self.timeChanged()
	
	def calculateFilename(self):
		service_name = self.service_ref.getServiceName()
		begin_date = time.strftime("%Y%m%d %H%M", time.localtime(self.begin))
		
		print "begin_date: ", begin_date
		print "service_name: ", service_name
		print "name:", self.name
		print "description: ", self.description
		
		filename = begin_date + " - " + service_name
		if self.name:
			filename += " - " + self.name

		self.Filename = Directories.getRecordingFilename(filename)
		self.log(0, "Filename calculated as: '%s'" % self.Filename)
		#begin_date + " - " + service_name + description)
	
	def tryPrepare(self):
		if self.justplay:
			return True
		else:
			self.calculateFilename()
			self.record_service = NavigationInstance.instance.recordService(self.service_ref)
			if self.record_service == None:
				self.log(1, "'record service' failed")
				return False
			else:
				event_id = self.eit
				if event_id is None:
					event_id = -1
				prep_res = self.record_service.prepare(self.Filename + ".ts", self.begin, self.end, event_id )
				if prep_res:
					self.log(2, "'prepare' failed: error %d" % prep_res)
					self.record_service = None
					return False

				if self.repeated:
					epgcache = eEPGCache.getInstance()
					queryTime=self.begin+(self.end-self.begin)/2
					evt = epgcache.lookupEventTime(self.service_ref.ref, queryTime)
					if evt:
						self.description = evt.getShortDescription()
				self.log(3, "prepare ok, writing meta information to %s" % self.Filename)
				try:
					f = open(self.Filename + ".ts.meta", "w")
					f.write(str(self.service_ref) + "\n")
					f.write(self.name + "\n")
					f.write(self.description + "\n")
					f.write(str(self.begin) + "\n")
					f.close()
				except IOError:
					self.log(4, "failed to write meta information")
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
		
		if next_state == self.StatePrepared:
			if self.tryPrepare():
				self.log(6, "prepare ok, waiting for begin")
				# fine. it worked, resources are allocated.
				self.next_activation = self.begin
				self.backoff = 0
				return True
			
			self.log(7, "prepare failed")
			if self.first_try_prepare:
				self.first_try_prepare = False
				if config.recording.asktozap.value == 0:
					self.log(8, "asking user to zap away")
					Notifications.AddNotificationWithCallback(self.failureCB, MessageBox, _("A timer failed to record!\nDisable TV and try again?\n"))
				else: # zap without asking
					self.log(9, "zap without asking")
					Notifications.AddNotification(MessageBox, _("In order to record a timer, the TV was switched to the recording service!\n"), type=MessageBox.TYPE_WARNING)
					self.failureCB(True)

			self.do_backoff()
			# retry
			self.start_prepare = time.time() + self.backoff
			return False
		elif next_state == self.StateRunning:
			# if this timer has been cancelled, just go to "end" state.
			if self.cancelled:
				return True

			if self.justplay:
				self.log(11, "zapping")
				NavigationInstance.instance.playService(self.service_ref.ref)
				return True
			else:
				self.log(11, "start recording")
				record_res = self.record_service.start()
				
				if record_res:
					self.log(13, "start record returned %d" % record_res)
					self.do_backoff()
					# retry
					self.begin = time.time() + self.backoff
					return False
				
				return True
		elif next_state == self.StateEnded:
			self.log(12, "stop recording")
			if not self.justplay:
				self.record_service.stop()
				self.record_service = None
			if self.afterEvent == AFTEREVENT.STANDBY:
				if self.session is not None:
					self.session.open(Standby, self)
			elif self.afterEvent == AFTEREVENT.DEEPSTANDBY:
				quitMainloop(1)
			return True

	def getNextActivation(self):
		if self.state == self.StateEnded:
			return self.end
		
		next_state = self.state + 1
		
		return {self.StatePrepared: self.start_prepare, 
				self.StateRunning: self.begin, 
				self.StateEnded: self.end }[next_state]

	def failureCB(self, answer):
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
		
		if old_prepare != self.start_prepare:
			self.log(15, "record time changed, start prepare is now: %s" % time.ctime(self.start_prepare))

def createTimer(xml):
	begin = int(xml.getAttribute("begin"))
	end = int(xml.getAttribute("end"))
	serviceref = ServiceReference(str(xml.getAttribute("serviceref")))
	description = xml.getAttribute("description").encode("utf-8")
	repeated = xml.getAttribute("repeated").encode("utf-8")
	disabled = long(xml.getAttribute("disabled") or "0")
	justplay = long(xml.getAttribute("justplay") or "0")
	afterevent = str(xml.getAttribute("afterevent") or "nothing")
	afterevent = { "nothing": AFTEREVENT.NONE, "standby": AFTEREVENT.STANDBY, "deepstandby": AFTEREVENT.DEEPSTANDBY }[afterevent]
	if xml.hasAttribute("eit") and xml.getAttribute("eit") != "None":
		eit = long(xml.getAttribute("eit"))
	else:
		eit = None
	
	name = xml.getAttribute("name").encode("utf-8")
	#filename = xml.getAttribute("filename").encode("utf-8")
	entry = RecordTimerEntry(serviceref, begin, end, name, description, eit, disabled, justplay, afterevent)
	entry.repeated = int(repeated)
	
	for l in elementsWithTag(xml.childNodes, "log"):
		time = int(l.getAttribute("time"))
		code = int(l.getAttribute("code"))
		msg = mergeText(l.childNodes).strip().encode("utf-8")
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
			
	def isRecording(self):
		isRunning = False
		for timer in self.timer_list:
			if timer.isRunning() and not timer.justplay:
				isRunning = True
		return isRunning
	
	def loadTimer(self):
		# TODO: PATH!
		doc = xml.dom.minidom.parse(self.Filename)
		
		root = doc.childNodes[0]
		for timer in elementsWithTag(root.childNodes, "timer"):
			self.record(createTimer(timer))

	def saveTimer(self):
		#doc = xml.dom.minidom.Document()
		#root_element = doc.createElement('timers')
		#doc.appendChild(root_element)
		#root_element.appendChild(doc.createTextNode("\n"))
		
		#for timer in self.timer_list + self.processed_timers:
			# some timers (instant records) don't want to be saved.
			# skip them
			#if timer.dontSave:
				#continue
			#t = doc.createTextNode("\t")
			#root_element.appendChild(t)
			#t = doc.createElement('timer')
			#t.setAttribute("begin", str(int(timer.begin)))
			#t.setAttribute("end", str(int(timer.end)))
			#t.setAttribute("serviceref", str(timer.service_ref))
			#t.setAttribute("repeated", str(timer.repeated))			
			#t.setAttribute("name", timer.name)
			#t.setAttribute("description", timer.description)
			#t.setAttribute("eit", str(timer.eit))
			
			#for time, code, msg in timer.log_entries:
				#t.appendChild(doc.createTextNode("\t\t"))
				#l = doc.createElement('log')
				#l.setAttribute("time", str(time))
				#l.setAttribute("code", str(code))
				#l.appendChild(doc.createTextNode(msg))
				#t.appendChild(l)
				#t.appendChild(doc.createTextNode("\n"))

			#root_element.appendChild(t)
			#t = doc.createTextNode("\n")
			#root_element.appendChild(t)


		#file = open(self.Filename, "w")
		#doc.writexml(file)
		#file.write("\n")
		#file.close()

		list = []

		list.append('<?xml version="1.0" ?>\n')
		list.append('<timers>\n')
		
		for timer in self.timer_list + self.processed_timers:
			if timer.dontSave:
				continue

			list.append('<timer')
			list.append(' begin="' + str(int(timer.begin)) + '"')
			list.append(' end="' + str(int(timer.end)) + '"')
			list.append(' serviceref="' + str(timer.service_ref) + '"')
			list.append(' repeated="' + str(int(timer.repeated)) + '"')
			list.append(' name="' + str(stringToXML(timer.name)) + '"')
			list.append(' description="' + str(stringToXML(timer.description)) + '"')
			list.append(' afterevent="' + str(stringToXML({ AFTEREVENT.NONE: "nothing", AFTEREVENT.STANDBY: "standby", AFTEREVENT.DEEPSTANDBY: "deepstandby" }[timer.afterEvent])) + '"')
			if timer.eit is not None:
				list.append(' eit="' + str(timer.eit) + '"')
			list.append(' disabled="' + str(int(timer.disabled)) + '"')
			list.append(' justplay="' + str(int(timer.justplay)) + '"')
			list.append('>\n')
			
			#for time, code, msg in timer.log_entries:
				#list.append('<log')
				#list.append(' code="' + str(code) + '"')
				#list.append(' time="' + str(time) + '"')
				#list.append('>')
				#list.append(str(msg))
				#list.append('</log>\n')

			
			list.append('</timer>\n')

		list.append('</timers>\n')

		file = open(self.Filename, "w")
		for x in list:
			file.write(x)
		file.close()

	def record(self, entry):
		entry.timeChanged()
		print "[Timer] Record " + str(entry)
		entry.Timer = self
		self.addTimerEntry(entry)
		
	def isInTimer(self, eventid, begin, duration, service):
		time_match = 0
		chktime = None
		chktimecmp = None
		chktimecmp_end = None
		end = begin + duration
		for x in self.timer_list:
			if str(x.service_ref) == str(service):
				#if x.eit is not None and x.repeated == 0:
				#	if x.eit == eventid:
				#		return duration
				if x.repeated != 0:
					if chktime is None:
						chktime = localtime(begin)
						chktimecmp = chktime.tm_wday * 1440 + chktime.tm_hour * 60 + chktime.tm_min
						chktimecmp_end = chktimecmp + (duration / 60)
					time = localtime(x.begin)
					for y in range(7):
						if x.repeated & (2 ** y):
							timecmp = y * 1440 + time.tm_hour * 60 + time.tm_min
							if timecmp <= chktimecmp < (timecmp + ((x.end - x.begin) / 60)):
								time_match = ((timecmp + ((x.end - x.begin) / 60)) - chktimecmp) * 60
							elif chktimecmp <= timecmp < chktimecmp_end:
								time_match = (chktimecmp_end - timecmp) * 60
				else: #if x.eit is None:
					if begin <= x.begin <= end:
						diff = end - x.begin
						if time_match < diff:
							time_match = diff
					elif x.begin <= begin <= x.end:
						diff = x.end - begin
						if time_match < diff:
							time_match = diff
		return time_match

	def removeEntry(self, entry):
		print "[Timer] Remove " + str(entry)
		
		# avoid re-enqueuing
		entry.repeated = False

		# abort timer.
		# this sets the end time to current time, so timer will be stopped.
		entry.abort()
		
		if entry.state != entry.StateEnded:
			self.timeChanged(entry)
		
		print "state: ", entry.state
		print "in processed: ", entry in self.processed_timers
		print "in running: ", entry in self.timer_list
		# now the timer should be in the processed_timers list. remove it from there.
		self.processed_timers.remove(entry)

	def shutdown(self):
		self.saveTimer()
