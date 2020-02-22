import errno
import time
import xml.etree.cElementTree

from enigma import eTimer
from os import environ, path, symlink, unlink, walk

from Components.config import ConfigSelection, ConfigSubsection, config
from Tools.Geolocation import geolocation
from Tools.StbHardware import setRTCoffset

# The DEFAULT_AREA setting is usable by the image maintainers to select the
# default UI mode and location settings used by their image.  If the value
# of "Classic" is used then images that use the "Timezone area" and 
# "Timezone" settings will have the "Timezone area" set to "Classic" and the
# "Timezone" field will be an expanded version of the classic list of GMT
# related offsets.  Images that only use the "Timezone" setting should use
# "Classic" to maintain their chosen UI for timezone selection.  That is,
# users will only be presented with the list of GMT related offsets.
#
# The DEFAULT_ZONE is used to select the default timezone if the "Timezone
# area" is selected to be "Europe".  This allows OpenViX to have the
# European default of "London" while OpenATV and OpenPLi can select "Berlin",
# etc. (These are only examples.)  Images can select any defaults they deem
# appropriate.
#
# NOTE: Even if the DEFAULT_AREA of "Classic" is selected a DEFAULT_ZONE
# must still be selected.
#
# For images that use both the "Timezone area" and "Timezone" configuration
# options then the DEFAULT_AREA can be set to an area most appropriate for
# the image.  For example, Beyonwiz would use "Australia", OpenATV, OpenViX
# and OpenPLi would use "Europe".  If the "Europe" option is selected then
# the DEFAULT_ZONE can be used to select a more appropriate timezone 
# selection for the image.  For example, OpenATV and OpenPLi may prefer
# "Berlin" while OpenViX may prefer "London".
#
# Please ensure that any defaults selected are valid, unique and available
# in the "/usr/share/zoneinfo/" directory tree.
#
# This version of Timezones.py now incorporates access to a new Geolocation
# feature that will try and determine the appropriate timezone for the user
# based on their WAN IP address.  If the receiver is not connected to the
# Internet the defaults described above and listed below will be used.
#
DEFAULT_AREA = "Classic"  # Use the classic timezone based list of timezones.
# DEFAULT_AREA = "Australia"  # Beyonwiz
# DEFAULT_AREA = "Europe"  # OpenATV, OpenPLi, OpenViX
DEFAULT_ZONE = "Berlin"  # OpenATV, OpenPLi
# DEFAULT_ZONE = "London"  # OpenViX
TIMEZONE_FILE = "/etc/timezone.xml"  # This should be SCOPE_TIMEZONES_FILE!  This file moves arond the filesystem!!!  :(
TIMEZONE_DATA = "/usr/share/zoneinfo/"  # This should be SCOPE_TIMEZONES_DATA!
AT_POLL_DELAY = 3  # Minutes

def InitTimeZones():
	tz = geolocation.get("timezone", None)
	if tz is None:
		area = DEFAULT_AREA
		zone = timezones.getTimezoneDefault(area=area)
		print "[Timezones] Geolocation not available!  (area='%s', zone='%s')" % (area, zone)
	elif DEFAULT_AREA == "Classic":
		area = "Classic"
		zone = tz
		print "[Timezones] Classic mode with geolocation tz='%s', area='%s', zone='%s'." % (tz, area, zone)
	else:
		area, zone = tz.split("/", 1)
		print "[Timezones] Modern mode with geolocation tz='%s', area='%s', zone='%s'." % (tz, area, zone)
	config.timezone = ConfigSubsection()
	config.timezone.area = ConfigSelection(default=area, choices=timezones.getTimezoneAreaList())
	config.timezone.val = ConfigSelection(default=timezones.getTimezoneDefault(), choices=timezones.getTimezoneList())
	if not config.timezone.area.saved_value:
		config.timezone.area.value = area
	if not config.timezone.val.saved_value:
		config.timezone.val.value = zone
	config.timezone.save()

	def timezoneAreaChoices(configElement):
		choices = timezones.getTimezoneList(area=configElement.value)
		config.timezone.val.setChoices(choices=choices, default=timezones.getTimezoneDefault(area=configElement.value, choices=choices))
		if config.timezone.val.saved_value and config.timezone.val.saved_value in [x[0] for x in choices]:
			config.timezone.val.value = config.timezone.val.saved_value

	def timezoneNotifier(configElement):
		timezones.activateTimezone(configElement.value, config.timezone.area.value)

	config.timezone.area.addNotifier(timezoneAreaChoices, initial_call=False, immediate_feedback=True)
	config.timezone.val.addNotifier(timezoneNotifier, initial_call=True, immediate_feedback=True)
	config.timezone.val.callNotifiersOnSaveAndCancel = True


class Timezones:
	def __init__(self):
		self.timezones = {}
		self.loadTimezones()
		self.readTimezones()
		self.autotimerCheck()
		if self.autotimerPollDelay is None:
			self.autotimerPollDelay = AT_POLL_DELAY
		self.timer = eTimer()
		self.autotimerUpdate = False

	# Scan the zoneinfo directory tree and all load all timezones found.
	#
	def loadTimezones(self):
		commonTimezoneNames = {
			"Antarctica/DumontDUrville": "Dumont d'Urville",
			"Asia/Ho_Chi_Minh": "Ho Chi Minh City",
			"Australia/LHI": None,  # Exclude
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
			if base in ("posix", "right"):  # Skip these alternate copies of the timezone data if they exist.
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
				zones.append((zone, name.replace("_", " ")))
			if area:
				if area in self.timezones:
					zones = self.timezones[area] + zones
				self.timezones[area] = self.gmtSort(zones)
		if len(self.timezones) == 0:
			print "[Timezones] Warning: No areas or zones found in '%s'!" % TIMEZONE_DATA
			self.timezones["Generic"] = [("UTC", "UTC")]

	# Return the list of Zones sorted alphabetically.  If the Zone
	# starts with "GMT" then those Zones will be sorted in GMT order
	# with GMT-14 first and GMT+12 last.
	#
	def gmtSort(self, zones):
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

	# Read the timezones.xml file and load all timezones found.
	#
	def readTimezones(self, filename=TIMEZONE_FILE):
		root = None
		try:
			# This open gets around a possible file handle leak in Python's XML parser.
			with open(filename, "r") as fd:
				try:
					root = xml.etree.cElementTree.parse(fd).getroot()
				except xml.etree.cElementTree.ParseError as err:
					root = None
					fd.seek(0)
					content = fd.readlines()
					line, column = err.position
					print "[Timezones] XML Parse Error: '%s' in '%s'!" % (err, filename)
					data = content[line - 1].replace("\t", " ").rstrip()
					print "[Timezones] XML Parse Error: '%s'" % data
					print "[Timezones] XML Parse Error: '%s^%s'" % ("-" * column, " " * (len(data) - column - 1))
				except Exception as err:
					root = None
					print "[Timezones] Error: Unable to parse timezone data in '%s' - '%s'!" % (filename, err)
		except (IOError, OSError) as err:
			if err.errno == errno.ENOENT:  # No such file or directory
				print "[Timezones] Note: Classic timezones in '%s' are not available." % filename
			else:
				print "[Timezones] Error %d: Opening timezone file '%s'! (%s)" % (err.errno, filename, err.strerror)
		except Exception as err:
			print "[Timezones] Error: Unexpected error opening timezone file '%s'! (%s)" % (filename, err)
		zones = []
		if root is not None:
			for zone in root.findall("zone"):
				name = zone.get("name", "")
				zonePath = zone.get("zone", "")
				if path.exists(path.join(TIMEZONE_DATA, zonePath)):
					zones.append((zonePath, name))
				else:
					print "[Timezones] Warning: Classic timezone '%s' (%s) is not available in '%s'!" % (name, zonePath, TIMEZONE_DATA)
				# print "[Timezones] DEBUG: Count=%2d, Name='%-50s', Zone='%s'%s" % (len(zones), name, zonePath)
			self.timezones["Classic"] = zones
		if len(zones) == 0:
			self.timezones["Classic"] = [("UTC", "UTC")]

	# Return a sorted list of all Area entries.
	#
	def getTimezoneAreaList(self):
		return sorted(self.timezones.keys())

	# Return a sorted list of all Zone entries for an Area.
	#
	def getTimezoneList(self, area=None):
		if area is None:
			area = config.timezone.area.value
		return self.timezones.get(area, [("UTC", "UTC")])

	# Return a default Zone for any given Area.  If there is no specific
	# default then the first Zone in the Area will be returned.
	#
	def getTimezoneDefault(self, area=None, choices=None):
		areaDefaultZone = {
			"Australia": "Sydney",
			"Classic": "Europe/London",
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

	def activateTimezone(self, zone, area):
		# print "[Timezones] activateTimezone DEBUG: Area='%s', Zone='%s'" % (area, zone)
		self.autotimerCheck()
		if self.autotimerAvailable and config.plugins.autotimer.autopoll.value:
			print "[Timezones] Trying to stop main AutoTimer poller."
			if self.autotimerPoller is not None:
				self.autotimerPoller.stop()
			self.autotimerUpdate = True
		tz = zone if area in ("Classic", "Generic") else path.join(area, zone)
		file = path.join(TIMEZONE_DATA, tz)
		if not path.isfile(file):
			print "[Timezones] Error: The timezone '%s' is not available!  Using 'UTC' instead." % tz
			tz = "UTC"
			file = path.join(TIMEZONE_DATA, tz)
		print "[Timezones] Setting timezone to '%s'." % tz
		environ["TZ"] = tz
		try:
			unlink("/etc/localtime")
		except (IOError, OSError) as err:
			if err.errno != errno.ENOENT:  # No such file or directory
				print "[Directories] Error %d: Unlinking '/etc/localtime'! (%s)" % (err.errno, err.strerror)
			pass
		try:
			symlink(file, "/etc/localtime")
		except (IOError, OSError) as err:
			print "[Directories] Error %d: Linking '%s' to '/etc/localtime'! (%s)" % (err.errno, file, err.strerror)
			pass
		try:
			time.tzset()
		except Exception:
			from enigma import e_tzset
			e_tzset()
		if path.exists("/proc/stb/fp/rtc_offset"):
			setRTCoffset()
		if self.autotimerAvailable and config.plugins.autotimer.autopoll.value:
			if self.autotimerUpdate:
				self.timer.stop()
			if self.autotimeQuery not in self.timer.callback:
				self.timer.callback.append(self.autotimeQuery)
			print "[Timezones] AutoTimer poller will be run in %d minutes." % AT_POLL_DELAY
			self.timer.startLongTimer(AT_POLL_DELAY * 60)

	def autotimerCheck(self):
		self.autotimerAvailable = False
		self.autotimerPollDelay = None
		return None
		try:
			# Create attributes autotimer & autopoller for backwards compatibility.
			# Their use is deprecated.
			from Plugins.Extensions.AutoTimer.plugin import autotimer, autopoller
			self.autotimerPoller = autopoller
			self.autotimerTimer = autotimer
			self.autotimerAvailable = True
		except ImportError:
			self.autotimerPoller = None
			self.autotimerTimer = None
			self.autotimerAvailable = False
		try:
			self.autotimerPollDelay = config.plugins.autotimer.delay.value
		except AttributeError:
			self.autotimerPollDelay = None

	def autotimeQuery(self):
		print "[Timezones] AutoTimer poll is running."
		self.autotimerUpdate = False
		if self.autotimeQuery in self.timer.callback:
			self.timer.callback.remove(self.autotimeQuery)
		self.timer.stop()
		self.autotimerCheck()
		if self.autotimerAvailable:
			if self.autotimerTimer is not None:
				print "[Timezones] AutoTimer is parseing the EPG."
				self.autotimerTimer.parseEPG(autoPoll=True)
			if self.autotimerPoller is not None:
				self.autotimerPoller.start()


timezones = Timezones()
