from xml.sax import make_parser
from xml.sax.handler import ContentHandler

from os import environ, unlink, symlink
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
		
		environ['TZ'] = self.timezones[index][1]
		try:
			unlink("/etc/localtime")
		except OSError:
			pass
		try:
			symlink("/usr/share/zoneinfo/%s" %(self.timezones[index][1]), "/etc/localtime")
		except OSError:
			pass
		try:
			time.tzset()
		except:
			from enigma import e_tzset
			e_tzset()
		
	def getTimezoneList(self):
		return [ str(x[0]) for x in self.timezones ]

	def getDefaultTimezone(self):
		# TODO return something more useful - depending on country-settings?
		t = "(GMT+01:00) Amsterdam, Berlin, Bern, Rome, Vienna"
		for (a,b) in self.timezones:
			if a == t:
				return a
		return self.timezones[0][0]

timezones = Timezones()
