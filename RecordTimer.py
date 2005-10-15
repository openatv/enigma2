import time
import codecs
#from time import datetime
from Tools import Directories

import timer
import xml.dom.minidom

import NavigationInstance

from Tools.XMLTools import elementsWithTag
from ServiceReference import ServiceReference

class RecordTimerEntry(timer.TimerEntry):
	def __init__(self, begin, end, serviceref, epg, description):
		timer.TimerEntry.__init__(self, int(begin), int(end))
		
		assert isinstance(serviceref, ServiceReference)
		
		self.service_ref = serviceref
		
		if epg is not None:
			self.epg_data = ""
			#str(epg.m_event_name)
		else:
			self.epg_data = ""
		
		self.description = description
		self.timer = None
		self.record_service = None
		
	def calculateFilename(self):
		service_name = self.service_ref.getServiceName()
#		begin_date = datetime.fromtimestamp(begin).strf...
		begin_date = ""
		if self.epg_data is not None:
			description = " - " + self.epg_data
		else:
			description = ""
		
		print begin_date
		print service_name
		print description
		self.Filename = Directories.getRecordingFilename(service_name)
		#begin_date + " - " + service_name + description)
		
		# build filename from epg
		
		# pff das geht noch nicht...
#		if epg == None:
#			self.Filename = "recording.ts"
#		else:
#			self.Filename = "record_" + str(epg.m_event_name) + ".ts"
#		
#		print "------------ record filename: %s" % (self.Filename)
	
	
	def activate(self, event):
		if event == self.EventPrepare:
			self.calculateFilename()
			self.record_service = NavigationInstance.instance.recordService(self.service_ref)
			if self.record_service == None:
				print "timer record failed."
			else:	
				self.record_service.prepare(self.Filename + ".ts")
				f = open(self.Filename + ".ts.meta", "w")
				f.write(str(self.service_ref) + "\n")
				f.write(self.epg_data + "\n")
				del f
				
		elif self.record_service == None:
			if event != self.EventAbort:
				print "timer record start failed, can't finish recording."
		elif event == self.EventStart:
			self.record_service.start()
			print "timer started!"
		elif event == self.EventEnd or event == self.EventAbort:
			self.record_service.stop()
			self.record_service = None
			print "Timer successfully ended"


def createTimer(xml):
	begin = int(xml.getAttribute("begin"))
	end = int(xml.getAttribute("end"))
	serviceref = ServiceReference(str(xml.getAttribute("serviceref")))
	description = xml.getAttribute("description")
	epgdata = xml.getAttribute("epgdata")
	#filename = xml.getAttribute("filename")
	return RecordTimerEntry(begin, end, serviceref, epgdata, description)

class RecordTimer(timer.Timer):
	def __init__(self):
		timer.Timer.__init__(self)
		
		self.Filename = Directories.resolveFilename(Directories.SCOPE_USERETC, "timers.xml")
		
		try:
			self.loadTimer()
		except:
			print "unable to load timers from file!"
	
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
			t = doc.createTextNode("\t")
			root_element.appendChild(t)
			t = doc.createElement('timer')
			t.setAttribute("begin", str(timer.begin))
			t.setAttribute("end", str(timer.end))
			t.setAttribute("serviceref", str(timer.service_ref))
			#t.setAttribute("epgdata", timer.)
			t.setAttribute("description", timer.description)
			root_element.appendChild(t)
			t = doc.createTextNode("\n")
			root_element.appendChild(t)
		
		file = open(self.Filename, "w")
		doc.writexml(codecs.getwriter('UTF-8')(file))
		file.close()
	
	def record(self, entry):
		entry.Timer = self
		self.addTimerEntry(entry)

	def removeEntry(self, entry):
		if entry.state == timer.TimerEntry.StateRunning:
			entry.end = time.time()
			self.timeChanged(entry)
		elif entry.state != timer.TimerEntry.StateEnded:
			entry.activate(timer.TimerEntry.EventAbort)
			self.timer_list.remove(entry)
			print "timer did not yet start - removing"
		else:
			print "timer did already end - doing nothing."

		self.calcNextActivation()


	def shutdown(self):
		self.saveTimer()
