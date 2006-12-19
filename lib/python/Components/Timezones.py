from xml.sax import make_parser
from xml.sax.handler import ContentHandler

import os
import time

class Timezones:
	class parseTimezones(ContentHandler):
		def __init__(self, timezones):
			self.isPointsElement, self.isReboundsElement = 0, 0
			self.timezones = timezones
	
		def startElement(self, name, attrs):
			if (name == "zone"):
				self.timezones.append((attrs.get('name',""), attrs.get('zone',"")))
	
	def __init__(self):
		self.timezones = []
		
		self.readTimezonesFromFile()

	def readTimezonesFromFile(self):
		parser = make_parser()
		
		try:
			timezonesHandler = self.parseTimezones(self.timezones)
			parser.setContentHandler(timezonesHandler)
			parser.parse('/etc/timezone.xml')
		except:
			pass
		
		if len(self.timezones) == 0:
			self.timezones = [("UTC", "UTC")]
		
	def activateTimezone(self, index):
		if len(self.timezones) <= index:
			return
		
		os.environ['TZ'] = self.timezones[index][1]
		try:
			time.tzset()
		except:
			from enigma import e_tzset
			e_tzset()
		
	def getTimezoneList(self):
		list = []
		for x in self.timezones:
			list.append(str(x[0]))
		return list
	
	def getDefaultTimezone(self):
		# TODO return something more useful - depending on country-settings?
		return "(GMT+01:00) Amsterdam, Berlin, Bern, Rome, Vienna"

timezones = Timezones()
