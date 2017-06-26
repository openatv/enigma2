from enigma import eTimer

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
		if path.exists("/usr/lib/enigma2/python/Plugins/Extensions/AutoTimer/plugin.pyo"):
			from Plugins.Extensions.AutoTimer.AutoTimer import AutoTimer
			from Plugins.Extensions.AutoTimer.AutoPoller import AutoPoller
			self.autopoller = AutoPoller()
			self.autotimer = AutoTimer()
		self.timer = eTimer()
		self.ATupdate = None

	def startATupdate(self):
		if self.ATupdate:
			self.timer.stop()
		if self.query not in self.timer.callback:
			self.timer.callback.append(self.query)
		print "[Timezones] AutoTimer poll will be run in 3 minutes"
		self.timer.startLongTimer(3 * 60)

	def stopATupdate(self):
		self.ATupdate = None
		if self.query in self.timer.callback:
			self.timer.callback.remove(self.query)
		self.timer.stop()

	def query(self):
		print "[Timezones] AutoTimer poll running"
		self.stopATupdate()
		self.autotimer.parseEPG(autoPoll=True)
		self.autopoller.start()

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

	userFriendlyTZNames = {
		"Asia/Ho_Chi_Minh": _("Ho Chi Minh City"),
		"Australia/LHI": None, # Exclude
		"Australia/Lord_Howe": _("Lord Howe Island"),
		"Australia/North": _("Northern Territory"),
		"Australia/South": _("South Australia"),
		"Australia/West": _("Western Australia"),
		"Pacific/Chatham": _("Chatham Islands"),
		"Pacific/Easter": _("Easter Island"),
		"Pacific/Galapagos": _("Galapagos Islands"),
		"Pacific/Gambier": _("Gambier Islands"),
		"Pacific/Johnston": _("Johnston Atoll"),
		"Pacific/Marquesas": _("Marquesas Islands"),
		"Pacific/Midway": _("Midway Islands"),
		"Pacific/Norfolk": _("Norfolk Island"),
		"Pacific/Pitcairn": _("Pitcairn Islands"),
		"Pacific/Wake": _("Wake Island"),
	}

	@staticmethod
	def getUserFriendlyTZName(area, tzname):
		return Timezones.userFriendlyTZNames.get(area + '/' + tzname, tzname.replace('_', ' '))

	# Return all zone entries for an Area, sorted.
	def getTimezoneList(self, area=None):
		if area == None:
			area = config.timezone.area.getValue()
		return [(tzname, self.getUserFriendlyTZName(area, tzname)) for tzname in sorttz(self.timezones[area]) if self.getUserFriendlyTZName(area, tzname)]

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
		return Timezones.default_for_area.setdefault(area, choices[0][0])

	def updateTimezoneChoices(self, area, zone_field):
		choices = self.getTimezoneList(area=area)
		default = self.getTimezoneDefault(area=area, choices=choices)
		zone_field.setChoices(choices = choices, default = default)
		return

	def activateTimezone(self, tz, tzarea):
		if path.exists("/usr/lib/enigma2/python/Plugins/Extensions/AutoTimer/plugin.pyo") and config.plugins.autotimer.autopoll.value:
			print "[Timezones] trying to stop main AutoTimer poller"
			self.autopoller.stop()
			self.ATupdate = True

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
		if path.exists("/usr/lib/enigma2/python/Plugins/Extensions/AutoTimer/plugin.pyo") and config.plugins.autotimer.autopoll.value:
			self.startATupdate()

timezones = Timezones()
