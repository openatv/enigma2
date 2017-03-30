from config import config, ConfigSelection, ConfigSubsection
from os import environ, unlink, symlink, walk, path
import time

def InitTimeZones():
	config.timezone = ConfigSubsection()
	config.timezone.area = ConfigSelection(default = "Europe", choices = timezones.getTimezoneAreaList())
	def timezoneAreaChoices(configElement):
		timezones.updateTimezoneChoices(configElement.getValue(), config.timezone.val)
	config.timezone.area.addNotifier(timezoneAreaChoices, initial_call = False, immediate_feedback = True)

	config.timezone.val = ConfigSelection(default = timezones.getTimezoneDefault(), choices = timezones.getTimezoneList())
	def timezoneNotifier(configElement):
		timezones.activateTimezone(configElement.getValue(), config.timezone.area.getValue())
	config.timezone.val.addNotifier(timezoneNotifier, initial_call = True, immediate_feedback = True)
	config.timezone.val.callNotifiersOnSaveAndCancel = True

def sorttz(tzlist):
	sort_list = []
	for tzitem in tzlist:
		if tzitem.startswith("GMT"):
			if len(tzitem[3:]) > 1 and (tzitem[3:4] == "-" or tzitem[3:4] == "+") and tzitem[4:].isdigit():
				sortkey = int(tzitem[3:])
			else:
				sortkey = 0
		else:
			sortkey = tzitem
		sort_list.append((tzitem, sortkey))
	sort_list = sorted(sort_list, key=lambda listItem: listItem[1])
	return [i[0] for i in sort_list]

class Timezones:
	tzbase = "/usr/share/zoneinfo"
	gen_label = "Generic"

	def __init__(self):
		self.timezones = {}
		self.readTimezonesFromSystem()

	def readTimezonesFromSystem(self):
		tzfiles = [];
		for (root, dirs, files) in walk(Timezones.tzbase):
			root = root[len(Timezones.tzbase):]
			if root == "":
				root = "/" + Timezones.gen_label
			for f in files:
				if f[-4:] == '.tab' or f[-2:] == '-0' or f[-2:] == '+0': # no need for '.tab', -0, +0
					files.remove(f)

			for f in files:
				fp = "%s/%s" % (root, f)
				fp = fp[1:]	# Remove leading "/"
				(section, zone) = fp.split("/", 1)
				if not section in self.timezones:
					self.timezones[section] = []
				self.timezones[section].append(zone)

			if len(self.timezones) == 0:
				self.timezones[Timezones.gen_label] = ['UTC']

	# Return all Area options
	def getTimezoneAreaList(self):
		return sorted(self.timezones.keys())

	# Return all zone entries for an Area, sorted.
	def getTimezoneList(self, area=None):
		if area == None:
			area = config.timezone.area.getValue()
		return sorttz(self.timezones[area])

	default_for_area = {
		'Europe': 'London',
		'Generic': 'UTC',
	}
	def getTimezoneDefault(self, area=None, choices=None):
		if area == None:
			try:
				area = config.timezone.area.getValue()
			except:
				print "[Timezones] getTimezoneDefault, no area found, using Europe"
				area = "Europe"
		if choices == None:
			choices = self.getTimezoneList(area=area)
		return Timezones.default_for_area.setdefault(area, choices[0])

	def updateTimezoneChoices(self, area, zone_field):
		choices = self.getTimezoneList(area=area)
		default = self.getTimezoneDefault(area=area, choices=choices)
		zone_field.setChoices(choices = choices, default = default)
		return

	def activateTimezone(self, tz, tzarea):
		if tzarea == Timezones.gen_label:
			fulltz = tz
		else:
			fulltz = "%s/%s" % (tzarea, tz)

		tzneed = "%s/%s" % (Timezones.tzbase, fulltz)
		if not path.isfile(tzneed):
			print "[Timezones] Attempt to set timezone", fulltz, "ignored. UTC used"
			fulltz = "UTC"
			tzneed = "%s/%s" % (Timezones.tzbase, fulltz)

		print "[Timezones] setting timezone to", fulltz
		environ['TZ'] = fulltz
		try:
			unlink("/etc/localtime")
		except OSError:
			pass
		try:
			symlink(tzneed, "/etc/localtime")
		except OSError:
			pass
		try:
			time.tzset()
		except:
			from enigma import e_tzset
			e_tzset()

timezones = Timezones()
