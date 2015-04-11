import xml.etree.cElementTree

from os import environ, unlink, symlink
import time
from Tools.Directories import SCOPE_SKIN, resolveFilename

class Timezones:
	def __init__(self):
		self.timezones = []
		self.readTimezonesFromFile()

	def readTimezonesFromFile(self):
		try:
			root = xml.etree.cElementTree.parse(resolveFilename(SCOPE_SKIN, 'timezone.xml')).getroot()
			for zone in root.findall("zone"):
				self.timezones.append((zone.get('name',""), zone.get('zone',"")))
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
