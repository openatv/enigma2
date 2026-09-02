from ctypes import CDLL, POINTER, byref, c_char, c_char_p, c_int, c_uint32, c_void_p, create_string_buffer
from glob import glob
from os.path import basename, exists, join
from re import fullmatch, split
from xml.etree.ElementTree import ParseError, parse

from Components.config import ConfigInteger, ConfigSelection, ConfigSelectionNumber, ConfigSubsection, ConfigText, ConfigYesNo, config
from Tools.Directories import SCOPE_CONFIG, SCOPE_SKINS, resolveFilename


RTLSDR_LIBRARY_PATHS = (
	"/usr/lib/librtlsdr.so.0",
	"/usr/lib/librtlsdr.so.2",
	"/usr/lib/librtlsdr.so",
)

RTLSDR_TUNERS = {
	0: "Unknown",
	1: "Elonics E4000",
	2: "Fitipower FC0012",
	3: "Fitipower FC0013",
	4: "FCI FC2580",
	5: "Rafael Micro R820T/R820T2/R860",
	6: "Rafael Micro R828D/R828S",
}

# Keep this table aligned with Osmocom rtl-sdr's known_devices and udev rules.
# It is also used before the optional librtlsdr runtime has been installed.
RTLSDR_USB_DEVICES = {
	("0bda", "2832"): "Generic RTL2832U",
	("0bda", "2838"): "Generic RTL2832U OEM",
	("0413", "6680"): "DigitalNow Quad DVB-T PCI-E card",
	("0413", "6f0f"): "Leadtek WinFast DTV Dongle mini D",
	("0458", "707f"): "Genius TVGo DVB-T03 USB dongle (Ver. B)",
	("0ccd", "00a9"): "Terratec Cinergy T Stick Black rev 1",
	("0ccd", "00b3"): "Terratec NOXON DAB/DAB+ USB dongle (rev 1)",
	("0ccd", "00b4"): "Terratec Deutschlandradio DAB Stick",
	("0ccd", "00b5"): "Terratec NOXON DAB Stick - Radio Energy",
	("0ccd", "00b7"): "Terratec Media Broadcast DAB Stick",
	("0ccd", "00b8"): "Terratec BR DAB Stick",
	("0ccd", "00b9"): "Terratec WDR DAB Stick",
	("0ccd", "00c0"): "Terratec MuellerVerlag DAB Stick",
	("0ccd", "00c6"): "Terratec Fraunhofer DAB Stick",
	("0ccd", "00d3"): "Terratec Cinergy T Stick RC rev 3",
	("0ccd", "00d7"): "Terratec T Stick PLUS",
	("0ccd", "00e0"): "Terratec NOXON DAB/DAB+ USB dongle (rev 2)",
	("1554", "5020"): "PixelView PV-DT235U(RN)",
	("15f4", "0131"): "Astrometa DVB-T/DVB-T2",
	("15f4", "0133"): "HanfTek DAB+FM+DVB-T",
	("185b", "0620"): "Compro Videomate U620F",
	("185b", "0650"): "Compro Videomate U650F",
	("185b", "0680"): "Compro Videomate U680F",
	("1b80", "d393"): "GIGABYTE GT-U7300",
	("1b80", "d394"): "DIKOM USB-DVBT HD",
	("1b80", "d395"): "Peak 102569AGPK",
	("1b80", "d397"): "KWorld KW-UB450-T USB DVB-T Pico TV",
	("1b80", "d398"): "Zaapa ZT-MINDVBZP",
	("1b80", "d39d"): "SVEON STV20 DVB-T USB & FM",
	("1b80", "d3a4"): "Twintech UT-40",
	("1b80", "d3a8"): "ASUS U3100MINI_PLUS_V2",
	("1b80", "d3af"): "SVEON STV27 DVB-T USB & FM",
	("1b80", "d3b0"): "SVEON STV21 DVB-T USB & FM",
	("1d19", "1101"): "Dexatek DK DVB-T Dongle (Logilink VG0002A)",
	("1d19", "1102"): "Dexatek DK DVB-T Dongle (MSI DigiVox mini II V3.0)",
	("1d19", "1103"): "Dexatek Technology Ltd. DK 5217 DVB-T Dongle",
	("1d19", "1104"): "MSI DigiVox Micro HD",
	("1f4d", "a803"): "Sweex DVB-T USB",
	("1f4d", "b803"): "GTek T803",
	("1f4d", "c803"): "Lifeview LV5TDeluxe",
	("1f4d", "d286"): "MyGica TD312",
	("1f4d", "d803"): "PROlectrix DV107669",
}

GENERIC_SERIALS = ("", "0", "00000000", "00000001")


def _dabXMLRoot(terrestrial=False):
	configPath = resolveFilename(SCOPE_CONFIG, "dab.xml")
	packagePath = resolveFilename(SCOPE_SKINS, "dab.xml")
	paths = (configPath, packagePath) if terrestrial and exists(configPath) else ((configPath,) if exists(configPath) else (packagePath,))
	for path in paths:
		try:
			root = parse(path).getroot()
			if root.tag == "dabFeeds" and (not terrestrial or root.find("terrestrial") is not None):
				return root
		except (OSError, ParseError, ValueError) as err:
			print("[RTLSDR] Unable to read DAB configuration '%s': %s" % (path, err))
	return None


def getRTLSDRRegions():
	root = _dabXMLRoot(terrestrial=True)
	terrestrial = root.find("terrestrial") if root is not None else None
	regions = []
	if terrestrial is not None:
		for node in terrestrial.findall("region"):
			regionId = (node.get("id") or "").strip().lower()
			if regionId and not any(item[0] == regionId for item in regions):
				regions.append((regionId, _(node.get("name") or regionId)))
	if not regions or regions[0][0] != "all":
		regions.insert(0, ("all", _("All regions")))
	return regions


def getRTLSDRChannels(region=None):
	root = _dabXMLRoot(terrestrial=True)
	terrestrial = root.find("terrestrial") if root is not None else None
	if terrestrial is None:
		return ()
	region = (region or config.dab.rtlsdr.region.value or "all").lower()
	validRegions = {item[0] for item in getRTLSDRRegions()}
	if region not in validRegions:
		region = "all"
	channels = []
	for node in terrestrial.findall("channel"):
		channel = (node.get("id") or "").strip().upper()
		regions = {value.lower() for value in split(r"[\s,]+", node.get("regions", "")) if value}
		if not fullmatch(r"(?:[5-9][A-D]|1[0-2][A-D]|13[A-F])", channel):
			continue
		if region == "all" or region in regions:
			if channel not in channels:
				channels.append(channel)
	return tuple(channels)


def getRTLSDRChannelFrequency(channel):
	root = _dabXMLRoot(terrestrial=True)
	terrestrial = root.find("terrestrial") if root is not None else None
	if terrestrial is not None:
		channel = (channel or "").strip().upper()
		for node in terrestrial.findall("channel"):
			if (node.get("id") or "").strip().upper() == channel:
				try:
					return int(node.get("frequency", "0"))
				except ValueError:
					break
	return 0


def hasAvailableSatelliteDAB():
	root = _dabXMLRoot()
	if root is None:
		return False
	from Components.NimManager import nimmanager
	for satellite in root.findall("satellite"):
		try:
			orbitalPosition = int(satellite.get("orbitalPosition", "-1"), 10)
		except ValueError:
			continue
		if not nimmanager.getNimListForSat(orbitalPosition):
			continue
		for transponder in satellite.findall("transponder"):
			for feed in transponder.findall("feed"):
				enabled = feed.get("enabled", transponder.get("enabled", satellite.get("enabled", "true")))
				if enabled.lower() not in ("0", "false", "no", "off"):
					return True
	for feed in root.findall("feed"):
		try:
			orbitalPosition = int(feed.get("orbitalPosition", "-1"), 10)
		except ValueError:
			continue
		if feed.get("enabled", "true").lower() not in ("0", "false", "no", "off") and nimmanager.getNimListForSat(orbitalPosition):
			return True
	return False


def _decode(value):
	if not value:
		return ""
	if isinstance(value, bytes):
		return value.decode("utf-8", "replace").strip()
	return str(value).strip()


def _read(path):
	try:
		with open(path, "r", encoding="utf-8", errors="replace") as fd:
			return fd.read().strip()
	except OSError:
		return ""


def _usbDevices():
	devices = []
	for path in sorted(glob("/sys/bus/usb/devices/*")):
		vendor = _read(join(path, "idVendor"))
		productId = _read(join(path, "idProduct"))
		if not vendor or not productId:
			continue
		devices.append({
			"port": basename(path),
			"vendorId": vendor.lower(),
			"productId": productId.lower(),
			"knownModel": RTLSDR_USB_DEVICES.get((vendor.lower(), productId.lower()), ""),
			"manufacturer": _read(join(path, "manufacturer")),
			"product": _read(join(path, "product")),
			"serial": _read(join(path, "serial")),
			"speed": _read(join(path, "speed")),
			"driver": basename(_read(join(path, "driver")))
		})
	return devices


class RTLSDRLibrary:
	def __init__(self):
		self.path = next((path for path in RTLSDR_LIBRARY_PATHS if exists(path)), None)
		if self.path is None:
			raise OSError("librtlsdr is not installed")
		self.lib = CDLL(self.path)
		self.lib.rtlsdr_get_device_count.restype = c_uint32
		self.lib.rtlsdr_get_device_name.argtypes = (c_uint32,)
		self.lib.rtlsdr_get_device_name.restype = c_char_p
		self.lib.rtlsdr_get_device_usb_strings.argtypes = (c_uint32, POINTER(c_char), POINTER(c_char), POINTER(c_char))
		self.lib.rtlsdr_get_device_usb_strings.restype = c_int
		self.lib.rtlsdr_open.argtypes = (POINTER(c_void_p), c_uint32)
		self.lib.rtlsdr_open.restype = c_int
		self.lib.rtlsdr_close.argtypes = (c_void_p,)
		self.lib.rtlsdr_close.restype = c_int
		self.lib.rtlsdr_get_tuner_type.argtypes = (c_void_p,)
		self.lib.rtlsdr_get_tuner_type.restype = c_int
		self.lib.rtlsdr_get_tuner_gains.argtypes = (c_void_p, POINTER(c_int))
		self.lib.rtlsdr_get_tuner_gains.restype = c_int

	def count(self):
		return int(self.lib.rtlsdr_get_device_count())

	def device(self, index, probe=False):
		manufacturer = create_string_buffer(256)
		product = create_string_buffer(256)
		serial = create_string_buffer(256)
		result = self.lib.rtlsdr_get_device_usb_strings(index, manufacturer, product, serial)
		info = {
			"index": index,
			"name": _decode(self.lib.rtlsdr_get_device_name(index)),
			"manufacturer": _decode(manufacturer.value),
			"product": _decode(product.value),
			"serial": _decode(serial.value),
			"tunerType": 0,
			"tuner": RTLSDR_TUNERS[0],
			"gains": [],
			"available": result == 0,
			"errorCode": result,
			"error": "" if result == 0 else "USB string query failed (%d)" % result
		}
		if probe and info["available"]:
			device = c_void_p()
			result = self.lib.rtlsdr_open(byref(device), index)
			if result == 0 and device:
				try:
					tunerType = int(self.lib.rtlsdr_get_tuner_type(device))
					info["tunerType"] = tunerType
					info["tuner"] = RTLSDR_TUNERS.get(tunerType, "Unknown (%d)" % tunerType)
					count = self.lib.rtlsdr_get_tuner_gains(device, None)
					if count > 0:
						values = (c_int * count)()
						if self.lib.rtlsdr_get_tuner_gains(device, values) == count:
							info["gains"] = [int(value) for value in values]
				finally:
					self.lib.rtlsdr_close(device)
			else:
				info["available"] = False
				info["errorCode"] = result
				info["error"] = "Unable to open device (%d)" % result
		return info


def _matchSysfs(devices):
	sysfsDevices = _usbDevices()
	used = set()
	for device in devices:
		matches = []
		for position, candidate in enumerate(sysfsDevices):
			if position in used:
				continue
			serialMatch = device["serial"] and candidate["serial"] == device["serial"]
			productMatch = device["product"] and candidate["product"] == device["product"]
			manufacturerMatch = not device["manufacturer"] or candidate["manufacturer"] == device["manufacturer"]
			if serialMatch and productMatch and manufacturerMatch:
				matches.append((position, candidate))
		if not matches:
			continue
		position, candidate = matches[0]
		used.add(position)
		device.update(candidate)
	return devices


def enumerateRTLSDRDevices(probe=False):
	try:
		library = RTLSDRLibrary()
		devices = [library.device(index, probe=probe) for index in range(library.count())]
	except (AttributeError, OSError, ValueError) as err:
		print("[RTLSDR] Device enumeration failed: %s" % err)
		return []
	_matchSysfs(devices)
	serialCounts = {}
	for device in devices:
		serial = device.get("serial", "")
		serialCounts[serial] = serialCounts.get(serial, 0) + 1
	for device in devices:
		serial = device.get("serial", "")
		port = device.get("port", "")
		if serial not in GENERIC_SERIALS and serialCounts.get(serial) == 1:
			key = "serial:%s" % serial
		elif port:
			key = "port:%s" % port
		else:
			key = "index:%d" % device["index"]
		device["key"] = key
		if probe and device.get("available") and device.get("tunerType"):
			config.dab.rtlsdr.cachedDevice.value = key
			config.dab.rtlsdr.cachedTunerType.value = device["tunerType"]
			config.dab.rtlsdr.cachedTuner.value = device["tuner"]
			config.dab.rtlsdr.cachedGains.value = ",".join(str(value) for value in device.get("gains", ()))
		elif not device.get("available") and config.dab.rtlsdr.cachedDevice.value == key:
			device["tunerType"] = config.dab.rtlsdr.cachedTunerType.value
			device["tuner"] = config.dab.rtlsdr.cachedTuner.value or RTLSDR_TUNERS.get(device["tunerType"], RTLSDR_TUNERS[0])
			try:
				device["gains"] = [int(value) for value in config.dab.rtlsdr.cachedGains.value.split(",") if value]
			except ValueError:
				device["gains"] = []
			device["probeCached"] = True
	return devices


def hasRTLSDRDevice():
	return bool(enumerateRTLSDRDevices(probe=False))


def hasRTLSDRUSBHardware():
	return any((device.get("vendorId"), device.get("productId")) in RTLSDR_USB_DEVICES for device in _usbDevices())


def isRTLSDRInUse(device=None):
	try:
		from NavigationInstance import instance
		reference = instance.getCurrentlyPlayingServiceReference() if instance else None
		path = reference.getPath() if reference else ""
		if not path.startswith("dab://rtlsdr/"):
			return False
		return device is None or int(device.get("index", -1)) == config.dab.rtlsdr.deviceIndex.value
	except (AttributeError, TypeError, ValueError):
		return False


def getActiveRTLSDRTuner():
	try:
		from enigma import iServiceInformation
		from NavigationInstance import instance
		reference = instance.getCurrentlyPlayingServiceReference() if instance else None
		if not reference or not reference.getPath().startswith("dab://rtlsdr/"):
			return ""
		service = instance.getCurrentService()
		info = service and service.info()
		field = getattr(iServiceInformation, "sDABReceiverName", None)
		return info.getInfoString(field).strip() if info and field is not None else ""
	except (AttributeError, TypeError, ValueError):
		return ""


def cacheRTLSDRTuner(device, tuner):
	if not device or not tuner:
		return False
	tunerAliases = (
		("Elonics E4000", 1),
		("Fitipower FC0012", 2),
		("Fitipower FC0013", 3),
		("FCI 2580", 4),
		("FCI FC2580", 4),
		("Rafael Micro R820T", 5),
		("Rafael Micro R828D", 6),
	)
	tunerType = next((number for prefix, number in tunerAliases if tuner.startswith(prefix)), 0)
	canonical = RTLSDR_TUNERS.get(tunerType, tuner)
	changed = (config.dab.rtlsdr.cachedDevice.value != device.get("key", "") or
		config.dab.rtlsdr.cachedTunerType.value != tunerType or
		config.dab.rtlsdr.cachedTuner.value != canonical)
	config.dab.rtlsdr.cachedDevice.value = device.get("key", "")
	config.dab.rtlsdr.cachedTunerType.value = tunerType
	config.dab.rtlsdr.cachedTuner.value = canonical
	device["tunerType"] = tunerType
	device["tuner"] = canonical
	device["probeCached"] = True
	if changed:
		from Components.config import configfile
		config.dab.rtlsdr.cachedDevice.save()
		config.dab.rtlsdr.cachedTunerType.save()
		config.dab.rtlsdr.cachedTuner.save()
		configfile.save()
	return changed


def isRTLSDREnabled():
	return config.dab.rtlsdr.enabled.value and hasRTLSDRDevice()


def hasRTLSDRBackend():
	return exists("/usr/bin/dab-rtlsdr-welle-e2")


def hasRTLSDRRuntime():
	return hasRTLSDRBackend() and any(exists(path) for path in RTLSDR_LIBRARY_PATHS)


def canScanRTLSDR():
	return isRTLSDREnabled() and hasRTLSDRBackend()


if not hasattr(config, "dab"):
	config.dab = ConfigSubsection()
if not hasattr(config.dab, "rtlsdr"):
	config.dab.rtlsdr = ConfigSubsection()
	config.dab.rtlsdr.enabled = ConfigYesNo(default=False)
	config.dab.rtlsdr.device = ConfigSelection(default="auto", choices=[("auto", _("Automatic"))])
	config.dab.rtlsdr.deviceIndex = ConfigInteger(default=0, limits=(0, 255))
	config.dab.rtlsdr.cachedDevice = ConfigText(default="", fixed_size=False)
	config.dab.rtlsdr.cachedTunerType = ConfigInteger(default=0, limits=(0, 255))
	config.dab.rtlsdr.cachedTuner = ConfigText(default="", fixed_size=False)
	config.dab.rtlsdr.cachedGains = ConfigText(default="", fixed_size=False)
	config.dab.rtlsdr.region = ConfigSelection(default="all", choices=getRTLSDRRegions())
	config.dab.rtlsdr.scanSource = ConfigSelection(default="all", choices=[
		("all", _("USB and satellite")),
		("rtlsdr", _("USB receiver only")),
		("dvb", _("Satellite only"))
	])
	config.dab.rtlsdr.slideshow = ConfigYesNo(default=True)
	config.dab.rtlsdr.automaticGain = ConfigYesNo(default=True)
	# The Welle backend maps this value onto the receiver's discrete gain table.  It
	# is a percentage, not a physical dB value.
	config.dab.rtlsdr.gain = ConfigSelectionNumber(min=0, max=100, stepwidth=1, default=35, units="%")
	config.dab.rtlsdr.ppm = ConfigInteger(default=0, limits=(-200, 200))
