from xml.sax import make_parser
from xml.sax.handler import ContentHandler

import os
import time

from enigma import *

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
		timezonesHandler = self.parseTimezones(self.timezones)
		parser.setContentHandler(timezonesHandler)
		parser.parse('/etc/timezone.xml')
		
	def activateTimezone(self, index):
		os.environ['TZ'] = self.timezones[index][1]
		try:
			time.tzset()
		except:
			etimezone()
		
	def getTimezoneList(self):
		list = []
		for x in self.timezones:
			list.append(str(x[0]))
		return list
	
	def getDefaultTimezone(self):
		# TODO return something more useful - depending on country-settings?
		return 27

timezones = Timezones()
