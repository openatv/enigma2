from errno import ENOENT
from os import symlink, unlink, walk
from os.path import exists, isfile, join as pathjoin, realpath
from time import gmtime, localtime, strftime, time, tzset

from Components.config import ConfigSelection, ConfigSubsection, config
from Tools.Directories import fileReadXML, fileWriteLine
from Tools.StbHardware import setRTCoffset

MODULE_NAME = __name__.split(".")[-1]

# The DEFAULT_AREA setting is usable by the image maintainers to select the
# default UI mode and location settings used by their image.  If the value
# of "Classic" is used then images that use the "Time zone area" and
# "Time zone" settings will have the "Time zone area" set to "Classic" and the
# "Time zone" field will be an expanded version of the classic list of GMT
# related offsets.  Images that only use the "Time zone" setting should use
# "Classic" to maintain their chosen UI for time zone selection.  That is,
# users will only be presented with the list of GMT related offsets.
#
# The DEFAULT_ZONE is used to select the default time zone if the "Time zone
# area" is selected to be "Europe".  This allows OpenViX to have the
# European default of "London" while OpenATV and OpenPLi can select "Berlin",
# etc. (These are only examples.)  Images can select any defaults they deem
# appropriate.
#
# NOTE: Even if the DEFAULT_AREA of "Classic" is selected a DEFAULT_ZONE
# must still be selected.
#
# For images that use both the "Time zone area" and "Time zone" configuration
# options then the DEFAULT_AREA can be set to an area most appropriate for
# the image.  For example, Beyonwiz would use "Australia", OpenATV, OpenViX
# and OpenPLi would use "Europe".  If the "Europe" option is selected then
# the DEFAULT_ZONE can be used to select a more appropriate time zone
# selection for the image.  For example, OpenATV and OpenPLi may prefer
# "Berlin" while OpenViX may prefer "London".
#
# Please ensure that any defaults selected are valid, unique and available
# in the "/usr/share/zoneinfo/" directory tree.
#
# This version of Timezones.py now incorporates access to a new Geolocation
# feature that will try and determine the appropriate time zone for the user
# based on their WAN IP address.  If the receiver is not connected to the
# Internet the defaults described above and listed below will be used.
#
# DEFAULT_AREA = "Classic"  # Use the classic time zone based list of time zones.
# DEFAULT_AREA = "Australia"  # Beyonwiz
DEFAULT_AREA = "Europe"  # OpenATV, OpenPLi, OpenViX
# DEFAULT_ZONE = "Amsterdam"  # OpenPLi
DEFAULT_ZONE = "Berlin"  # OpenATV
# DEFAULT_ZONE = "London"  # OpenViX
TIMEZONE_FILE = "/etc/timezone.xml"  # This should be SCOPE_TIMEZONES_FILE!  This file moves arond the file system!!!  :(
TIMEZONE_DATA = "/usr/share/zoneinfo/"  # This should be SCOPE_TIMEZONES_DATA!


def InitTimeZones():
	config.timezone = ConfigSubsection()
	config.timezone.area = ConfigSelection(default=DEFAULT_AREA, choices=timezones.getTimezoneAreaList())
	config.timezone.val = ConfigSelection(default=DEFAULT_ZONE, choices=timezones.getTimezoneList())
	if not config.timezone.area.value and config.timezone.val.value.find("/") == -1:
		config.timezone.area.value = "Generic"
	try:
		tzLink = realpath("/etc/localtime")[20:]
		msgs = []
		if config.timezone.area.value == "Classic":
			if config.timezone.val.value != tzLink:
				msgs.append("time zone '%s' != '%s'" % (config.timezone.val.value, tzLink))
		else:
			tzSplit = tzLink.find("/")
			if tzSplit == -1:
				tzArea = "Generic"
				tzVal = tzLink
			else:
				tzArea = tzLink[:tzSplit]
				tzVal = tzLink[tzSplit + 1:]
			if config.timezone.area.value != tzArea:
				msgs.append("area '%s' != '%s'" % (config.timezone.area.value, tzArea))
			if config.timezone.val.value != tzVal:
				msgs.append("zone '%s' != '%s'" % (config.timezone.val.value, tzVal))
		if len(msgs):
			print("[Timezones] Warning: Enigma2 time zone does not match system time zone (%s), setting system to Enigma2 time zone!" % ",".join(msgs))
	except OSError as err:
		print("[Timezones] Error %d: Unable to resolve current time zone from '/etc/localtime'!  (%s)" % (err.errno, err.strerror))

	def timezoneAreaChoices(configElement):
		choices = timezones.getTimezoneList(area=configElement.value)
		config.timezone.val.setChoices(choices=choices, default=timezones.getTimezoneDefault(area=configElement.value, choices=choices))
		if config.timezone.val.saved_value and config.timezone.val.saved_value in [x[0] for x in choices]:
			config.timezone.val.value = config.timezone.val.saved_value

	def timezoneNotifier(configElement):
		timezones.activateTimezone(configElement.value, config.timezone.area.value)

	config.timezone.area.addNotifier(timezoneAreaChoices, initial_call=False)
	config.timezone.val.addNotifier(timezoneNotifier)


class Timezones:
	def __init__(self):
		self.timezones = {}
		self.loadTimezones()
		self.readTimezones()
		self.callbacks = []

	def loadTimezones(self):  # Scan the zoneinfo directory tree and all load all time zones found.
		commonTimezoneNames = {
			"Antarctica/DumontDUrville": "Dumont d'Urville",
			"Asia/Ho_Chi_Minh": "Ho Chi Minh City",
			"Atlantic/Canary": "Canary Islands",
			"Australia/LHI": None,  # Duplicate entry - Exclude from list.
			"Australia/Lord_Howe": "Lord Howe Island",
			"Australia/North": "Northern Territory",
			"Australia/South": "South Australia",
			"Australia/West": "Western Australia",
			"Brazil/DeNoronha": "Fernando de Noronha",
			"Pacific/Chatham": "Chatham Islands",
			"Pacific/Easter": "Easter Island",
			"Pacific/Galapagos": "Galapagos Islands",
			"Pacific/Gambier": "Gambier Islands",
			"Pacific/Johnston": "Johnston Atoll",
			"Pacific/Marquesas": "Marquesas Islands",
			"Pacific/Midway": "Midway Islands",
			"Pacific/Norfolk": "Norfolk Island",
			"Pacific/Pitcairn": "Pitcairn Islands",
			"Pacific/Wake": "Wake Island",
		}
		for (root, dirs, files) in walk(TIMEZONE_DATA):
			base = root[len(TIMEZONE_DATA):]
			if base.startswith("posix") or base.startswith("right"):  # Skip these alternate copies of the time zone data if they exist.
				continue
			if base == "":
				base = "Generic"
			area = None
			zones = []
			for file in files:
				if file[-4:] == ".tab" or file[-2:] == "-0" or file[-1:] == "0" or file[-2:] == "+0":  # No need for ".tab", "-0", "0", "+0" files.
					continue
				tz = "%s/%s" % (base, file)
				area, zone = tz.split("/", 1)
				name = commonTimezoneNames.get(tz, zone)  # Use the more common name if one is defined.
				if name is None:
					continue
				if isinstance(name, str):
					name = name.encode(encoding="UTF-8", errors="ignore").decode()
				if isinstance(area, str):
					area = area.encode(encoding="UTF-8", errors="ignore").decode()
				if isinstance(zone, str):
					zone = zone.encode(encoding="UTF-8", errors="ignore").decode()
				zones.append((zone, name.replace("_", " ")))
			if area:
				if area in self.timezones:
					zones = self.timezones[area] + zones
				self.timezones[area] = self.gmtSort(zones)
		if len(self.timezones) == 0:
			print("[Timezones] Warning: No areas or zones found in '%s'!" % TIMEZONE_DATA)
			self.timezones["Generic"] = [("UTC", "UTC")]

	def gmtSort(self, zones):  # If the Zone starts with "GMT" then those Zones will be sorted in GMT order with GMT-14 first and GMT+12 last.
		data = {}
		for (zone, name) in zones:
			if name.startswith("GMT"):
				try:
					key = int(name[4:])
					key = (key * -1) + 15 if name[3:4] == "-" else key + 15
					key = "GMT%02d" % key
				except ValueError:
					key = "GMT15"
			else:
				key = name
			data[key] = (zone, name)
		return [data[x] for x in sorted(data.keys())]

	def readTimezones(self, filename=TIMEZONE_FILE):  # Read the timezones.xml file and load all time zones found.
		fileDom = fileReadXML(filename, source=MODULE_NAME)
		zones = []
		if fileDom is not None:
			for zone in fileDom.findall("zone"):
				name = zone.get("name", "")
				if isinstance(name, str):
					name = name.encode(encoding="UTF-8", errors="ignore").decode()
				zonePath = zone.get("zone", "")
				if isinstance(zonePath, str):
					zonePath = zonePath.encode(encoding="UTF-8", errors="ignore").decode()
				if exists(pathjoin(TIMEZONE_DATA, zonePath)):
					zones.append((zonePath, name))
				else:
					print("[Timezones] Warning: Classic time zone '%s' (%s) is not available in '%s'!" % (name, zonePath, TIMEZONE_DATA))
			self.timezones["Classic"] = zones
		if len(zones) == 0:
			self.timezones["Classic"] = [("UTC", "UTC")]

	def getTimezoneAreaList(self):  # Return a sorted list of all Area entries.
		return sorted(list(self.timezones.keys()))

	def getTimezoneList(self, area=None):  # Return a sorted list of all Zone entries for an Area.
		if area is None:
			area = config.timezone.area.value
		return self.timezones.get(area, [("UTC", "UTC")])

	# Return a default Zone for any given Area.  If there is no specific
	# default then the first Zone in the Area will be returned.
	#
	def getTimezoneDefault(self, area=None, choices=None):
		areaDefaultZone = {
			"Australia": "Sydney",
			"Classic": "Europe/%s" % DEFAULT_ZONE,
			"Etc": "GMT",
			"Europe": DEFAULT_ZONE,
			"Generic": "UTC",
			"Pacific": "Auckland"
		}
		if area is None:
			area = config.timezone.area.value
		if choices is None:
			choices = self.getTimezoneList(area=area)
		return areaDefaultZone.setdefault(area, choices[0][0])

	def activateTimezone(self, zone, area, runCallbacks=True):
		tz = zone if area in ("Classic", "Generic") else pathjoin(area, zone)
		file = pathjoin(TIMEZONE_DATA, tz)
		if not isfile(file):
			print("[Timezones] Error: The time zone '%s' is not available!  Using 'UTC' instead." % tz)
			tz = "UTC"
			file = pathjoin(TIMEZONE_DATA, tz)
		print("[Timezones] Setting time zone to '%s'." % tz)
		try:
			unlink("/etc/localtime")
		except OSError as err:
			if err.errno != ENOENT:  # No such file or directory.
				print("[Timezones] Error %d: Unlinking '/etc/localtime'!  (%s)" % (err.errno, err.strerror))
		try:
			symlink(file, "/etc/localtime")
		except OSError as err:
			print("[Timezones] Error %d: Linking '%s' to '/etc/localtime'! (%s)" % (err.errno, file, err.strerror))
		try:
			with open("/etc/timezone", "w") as fd:
				fd.write("%s\n" % tz)
		except OSError as err:
			print("[Timezones] Error %d: Linking '%s' to '/etc/localtime'!  (%s)" % (err.errno, file, err.strerror))
		fileWriteLine("/etc/timezone", "%s\n" % tz, source=MODULE_NAME)
		try:
			tzset()
		except Exception:
			from enigma import e_tzset
			e_tzset()
		if exists("/proc/stb/fp/rtc_offset"):
			setRTCoffset()
		timeFormat = "%a %d-%b-%Y %H:%M:%S"
		print("[Timezones] Local time is '%s'  -  UTC time is '%s'." % (strftime(timeFormat, localtime(None)), strftime(timeFormat, gmtime(None))))
		if runCallbacks:
			for callback in self.callbacks:
				callback()

	def addCallback(self, callback):
		if callback not in self.callbacks:
			self.callbacks.append(callback)

	def removeCallback(self, callback):
		if callable(callback) and callback not in self.callbacks:
			self.callbacks.remove(callback)


timezones = Timezones()
