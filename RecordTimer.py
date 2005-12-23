import time
import codecs
#from time import datetime
from Tools import Directories, Notifications

from Components.config import config
import timer
import xml.dom.minidom

from Screens.MessageBox import MessageBox
import NavigationInstance

from Tools.XMLTools import elementsWithTag
from ServiceReference import ServiceReference

# ok, for descriptions etc we have:
# service reference  (to get the service name)
# name               (title)
# description        (description)
# event data         (ONLY for time adjustments etc.)


# parses an event, and gives out a (begin, end, name, duration, eit)-tuple.
def parseEvent(ev):
	name = ev.getEventName()
	description = ev.getShortDescription()
	begin = ev.getBeginTime()
	end = begin + ev.getDuration()
	eit = None
	return (begin, end, name, description, eit)

class RecordTimerEntry(timer.TimerEntry):
	def __init__(self, serviceref, begin, end, name, description, eit):
		timer.TimerEntry.__init__(self, int(begin), int(end))
		
		assert isinstance(serviceref, ServiceReference)
		
		self.service_ref = serviceref
		
		self.eit = eit
		
		self.dontSave = False
		self.name = name
		self.description = description
		self.timer = None
		self.record_service = None
		self.wantStart = False
		self.prepareOK = False
		
	def calculateFilename(self):
		service_name = self.service_ref.getServiceName()
#		begin_date = datetime.fromtimestamp(begin).strf...
		begin_date = ""
		
		print "begin_date: ", begin_date
		print "service_name: ", service_name
		print "name:", self.name
		print "description: ", self.description

		self.Filename = Directories.getRecordingFilename(service_name)
		#begin_date + " - " + service_name + description)
		
	
	def tryPrepare(self):
		self.calculateFilename()
		self.record_service = NavigationInstance.instance.recordService(self.service_ref)
		if self.record_service == None:
			return False
		else:
			if self.record_service.prepare(self.Filename + ".ts"):
				self.record_service = None
				return False

			f = open(self.Filename + ".ts.meta", "w")
			f.write(str(self.service_ref) + "\n")
			f.write(self.name + "\n")
			f.write(self.description + "\n")
			f.write(str(self.begin) + "\n")
			del f
			return True

	def activate(self, event):
		if event == self.EventPrepare:
			self.prepareOK = False
			if self.tryPrepare():
				self.prepareOK = True
			else:
				# error.
				if config.recording.asktozap.value == 0:
					Notifications.AddNotificationWithCallback(self.failureCB, MessageBox, _("A timer failed to record!\nDisable TV and try again?\n"))
				else: # zap without asking
					self.failureCB(True)
		elif event == self.EventStart:
			if self.prepareOK:
				self.record_service.start()
				print "timer started!"
			else:
				print "prepare failed, thus start failed, too."
				self.wantStart = True
		elif event == self.EventEnd or event == self.EventAbort:
			self.wantStart = False
			if self.prepareOK:
				self.record_service.stop()
				self.record_service = None
				print "Timer successfully ended"
			else:
				print "prepare failed, thus nothing was recorded."

	def abort():
		# fixme
		pass

	def failureCB(self, answer):
		if answer == True:
			NavigationInstance.instance.stopUserServices()
			self.activate(self.EventPrepare)
			if self.wantStart:
				print "post-activating record"
				NavigationInstance.instance.playService(self.serviceref)
				self.activate(self.EventStart)
		else:
			print "user killed record"

def createTimer(xml):
	begin = int(xml.getAttribute("begin"))
	end = int(xml.getAttribute("end"))
	serviceref = ServiceReference(str(xml.getAttribute("serviceref")))
	description = xml.getAttribute("description").encode("utf-8")
	repeated = xml.getAttribute("repeated").encode("utf-8")
	eit = xml.getAttribute("eit").encode("utf-8")
	name = xml.getAttribute("name").encode("utf-8")
	#filename = xml.getAttribute("filename").encode("utf-8")
	entry = RecordTimerEntry(serviceref, begin, end, name, description, eit)
	entry.repeated = int(repeated)
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
			if timer.isRunning():
				isRunning = True
		return isRunning
	
	def loadTimer(self):
		# TODO: PATH!
		doc = xml.dom.minidom.parse(self.Filename)
		
		root = doc.childNodes[0]
		for timer in elementsWithTag(root.childNodes, "timer"):
			self.record(createTimer(timer))
	
	def saveTimer(self):
		doc = xml.dom.minidom.Document()
		root_element = doc.createElement('timers')
		doc.appendChild(root_element)
		root_element.appendChild(doc.createTextNode("\n"))
		
		for timer in self.timer_list + self.processed_timers:
			# some timers (instant records) don't want to be saved.
			# skip them
			if timer.dontSave:
				continue
			t = doc.createTextNode("\t")
			root_element.appendChild(t)
			t = doc.createElement('timer')
			t.setAttribute("begin", str(timer.begin))
			t.setAttribute("end", str(timer.end))
			t.setAttribute("serviceref", str(timer.service_ref))
			t.setAttribute("repeated", str(timer.repeated))			
			t.setAttribute("name", timer.name)
			t.setAttribute("description", timer.description)
			t.setAttribute("eit", str(timer.eit))
			
			root_element.appendChild(t)
			t = doc.createTextNode("\n")
			root_element.appendChild(t)

		file = open(self.Filename, "w")
		doc.writexml(file)
		file.write("\n")
		file.close()
	
	def record(self, entry):
		print "[Timer] Record " + str(entry)
		entry.Timer = self
		self.addTimerEntry(entry)

	def removeEntry(self, entry):
		print "[Timer] Remove " + str(entry)
		
		entry.repeated = False

		if entry.state == timer.TimerEntry.StateRunning:
			print "remove running timer."
			entry.end = time.time()
			self.timeChanged(entry)
		elif entry.state != timer.TimerEntry.StateEnded:
			entry.activate(timer.TimerEntry.EventAbort)
			self.timer_list.remove(entry)

			self.calcNextActivation()
			print "timer did not yet start - removing"

			# the timer was aborted, and removed.
			return
		else:
			print "timer did already end - doing nothing."
		
		print "state: ", entry.state
		print "in processed: ", entry in self.processed_timers
		print "in running: ", entry in self.timer_list
		# now the timer should be in the processed_timers list. remove it from there.
		self.processed_timers.remove(entry)

	def shutdown(self):
		self.saveTimer()
