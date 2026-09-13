from ctypes import ArgumentError, CDLL, POINTER, byref, c_char, c_char_p, c_int, c_uint32, c_void_p, create_string_buffer
from glob import glob
from os import makedirs, replace, unlink, uname
from os.path import basename, exists, join, realpath
from re import fullmatch, split
from threading import Thread
from xml.etree.ElementTree import ParseError, parse

from enigma import eTimer

from Components.config import ConfigInteger, ConfigSelection, ConfigSelectionNumber, ConfigSubDict, ConfigSubsection, ConfigText, ConfigYesNo, config, configfile
from Components.Opkg import OpkgComponent
from Components.SystemInfo import BoxInfo
from Screens.Toast import Toast
from Tools.Directories import SCOPE_CONFIG, SCOPE_SKINS, resolveFilename


RTLSDR_LIBRARY_PATHS = (
	"/usr/lib/librtlsdr.so.0",
	"/usr/lib/librtlsdr.so.2",
	"/usr/lib/librtlsdr.so",
)

RTLSDR_DVB_BLACKLIST_PATH = "/etc/modprobe.d/enigma2-dab-rtlsdr.conf"
RTLSDR_DVB_KERNEL_MODULES = (
	"dvb_usb_rtl2832",
	"dvb_usb_rtl28xxu",
	"rtl2832",
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
			print(f"[RTLSDR] Unable to read DAB configuration '{path}': {err}")
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


def _enabled(value):
	return str(value or "true").lower() not in ("0", "false", "no", "off")


def _orbitalPositionName(position):
	position = int(position)
	direction = "W" if position > 1800 else "E"
	degrees = (3600 - position if position > 1800 else position) / 10.0
	return f"{degrees:.1f}°{direction}"


def getDABSatelliteDefinitions(availableOnly=False):
	"""Return DAB satellite positions which have at least one enabled feed.

	Availability is derived from the configured Enigma2 tuner topology.  This
	also covers USALS/positioner tuners because NimManager expands their
	configured satellite list before getNimListForSat() is queried.
	"""
	root = _dabXMLRoot()
	if root is None:
		return ()
	from Components.NimManager import nimmanager
	positions = {}
	for satellite in root.findall("satellite"):
		try:
			orbitalPosition = int(satellite.get("orbitalPosition", "-1"), 10)
		except ValueError:
			continue
		hasFeed = False
		for transponder in satellite.findall("transponder"):
			for feed in transponder.findall("feed"):
				enabled = feed.get("enabled", transponder.get("enabled", satellite.get("enabled", "true")))
				if _enabled(enabled):
					hasFeed = True
					break
			if hasFeed:
				break
		if not hasFeed:
			continue
		entry = positions.setdefault(orbitalPosition, {"position": orbitalPosition, "names": []})
		name = (satellite.get("name") or "").strip()
		if name and name not in entry["names"]:
			entry["names"].append(name)
	for feed in root.findall("feed"):
		try:
			orbitalPosition = int(feed.get("orbitalPosition", "-1"), 10)
		except ValueError:
			continue
		if not _enabled(feed.get("enabled", "true")):
			continue
		entry = positions.setdefault(orbitalPosition, {"position": orbitalPosition, "names": []})
		name = (feed.get("satellite") or "").strip()
		if name and name not in entry["names"]:
			entry["names"].append(name)
	definitions = []
	for entry in positions.values():
		nimSlots = nimmanager.getNimListForSat(entry["position"])
		entry["available"] = bool(nimSlots)
		entry["motorized"] = any(entry["position"] in (satellite[0] for satellite in nimmanager.getRotorSatListForNim(slot)) for slot in nimSlots)
		if availableOnly and not entry["available"]:
			continue
		positionName = _orbitalPositionName(entry["position"])
		entry["label"] = "%s - %s" % (positionName, " / ".join(entry["names"])) if entry["names"] else positionName
		definitions.append(entry)
	return tuple(definitions)


def ensureDABSatelliteConfig(definitions=None):
	definitions = definitions if definitions is not None else getDABSatelliteDefinitions(availableOnly=True)
	for definition in definitions:
		key = str(definition["position"])
		if key not in config.dab.satellites:
			selection = ConfigYesNo(default=True)
			selection.addNotifier(updateDABBoxInfo, initial_call=False)
			config.dab.satellites[key] = selection
	return config.dab.satellites


def hasAvailableSatelliteDAB():
	return bool(getDABSatelliteDefinitions(availableOnly=True))


def isDABSatelliteEnabled(position):
	position = int(position)
	definitions = getDABSatelliteDefinitions(availableOnly=True)
	if not any(item["position"] == position for item in definitions):
		return False
	settings = ensureDABSatelliteConfig(definitions)
	selection = settings.get(str(position))
	return bool(selection and selection.value)


def isDABSatelliteMotorized(position):
	position = int(position)
	return any(item["position"] == position and item["motorized"] for item in getDABSatelliteDefinitions(availableOnly=True))


def canScanSatelliteDAB(definitions=None):
	definitions = definitions if definitions is not None else getDABSatelliteDefinitions(availableOnly=True)
	settings = ensureDABSatelliteConfig(definitions)
	return any(settings[str(item["position"])].value for item in definitions)


def _read(path):
	try:
		with open(path, "r", encoding="utf-8", errors="replace") as fd:
			return fd.read().strip()
	except OSError:
		return ""


def _driverNames(path):
	drivers = []
	for interfacePath in sorted(glob(f"{path}:*")):
		driverPath = join(interfacePath, "driver")
		if exists(driverPath):
			driver = basename(realpath(driverPath))
			if driver and driver not in drivers:
				drivers.append(driver)
	return drivers


def _dvbFrontends(path):
	usbPath = realpath(path).rstrip("/")
	frontends = []
	for frontendPath in sorted(glob("/sys/class/dvb/dvb*.frontend*")):
		devicePath = realpath(join(frontendPath, "device"))
		if devicePath == usbPath or devicePath.startswith(f"{usbPath}/"):
			frontends.append(basename(frontendPath))
	return frontends


def usbDevices():
	devices = []
	for path in sorted(glob("/sys/bus/usb/devices/*")):
		vendor = _read(join(path, "idVendor"))
		productId = _read(join(path, "idProduct"))
		if not vendor or not productId:
			continue
		deviceId = (vendor.lower(), productId.lower())
		knownModel = RTLSDR_USB_DEVICES.get(deviceId, "")
		drivers = _driverNames(path) if knownModel else []
		devices.append({
			"port": basename(path),
			"vendorId": vendor.lower(),
			"productId": productId.lower(),
			"knownModel": knownModel,
			"manufacturer": _read(join(path, "manufacturer")),
			"product": _read(join(path, "product")),
			"serial": _read(join(path, "serial")),
			"speed": _read(join(path, "speed")),
			"driver": ", ".join(drivers),
			"frontends": _dvbFrontends(path) if knownModel else []
		})
	return devices


def enumerateRTLSDRSysfsDevices():
	"""Enumerate supported receivers without calling or opening librtlsdr.

	The setup screen runs this on the Enigma2 main thread, so it must only read
	the kernel's already available sysfs attributes.  Cached tuner details are
	added when a receiver has previously been opened by the DAB service.
	"""
	devices = [device for device in usbDevices() if (device["vendorId"], device["productId"]) in RTLSDR_USB_DEVICES]
	serialCounts = {}
	for device in devices:
		serial = device.get("serial", "")
		serialCounts[serial] = serialCounts.get(serial, 0) + 1
	for index, device in enumerate(devices):
		serial = device.get("serial", "")
		port = device.get("port", "")
		if serial not in GENERIC_SERIALS and serialCounts.get(serial) == 1:
			key = f"serial:{serial}"
		elif port:
			key = f"port:{port}"
		else:
			key = f"index:{index}"
		device.update({
			"index": index,
			"key": key,
			"name": device.get("knownModel") or device.get("product") or _("RTL-SDR USB tuner"),
			"available": True,
			"errorCode": 0,
			"error": "",
			"tunerType": 0,
			"tuner": "",
			"gains": []
		})
		if config.dab.rtlsdr.cachedDevice.value == key:
			device["tunerType"] = config.dab.rtlsdr.cachedTunerType.value
			device["tuner"] = config.dab.rtlsdr.cachedTuner.value or RTLSDR_TUNERS.get(device["tunerType"], "")
			try:
				device["gains"] = [int(value) for value in config.dab.rtlsdr.cachedGains.value.split(",") if value]
			except ValueError:
				device["gains"] = []
			device["probeCached"] = bool(device["tuner"])
	return devices


def hasRTLSDRUSBHardware():
	return any((device.get("vendorId"), device.get("productId")) in RTLSDR_USB_DEVICES for device in usbDevices())


def isRTLSDRDVBKernelDriverBlacklisted():
	return exists(RTLSDR_DVB_BLACKLIST_PATH)


def hasRTLSDRDVBKernelDriver(devices=None):
	"""Detect the DVB side of a dual-purpose RTL2832 receiver without opening it."""
	if isRTLSDRDVBKernelDriverBlacklisted():
		return True
	if any(exists(f"/sys/module/{module}") for module in RTLSDR_DVB_KERNEL_MODULES):
		return True
	devices = usbDevices() if devices is None else devices
	for device in devices:
		drivers = {driver.strip().replace("-", "_") for driver in device.get("driver", "").split(",") if driver.strip()}
		if drivers.intersection(RTLSDR_DVB_KERNEL_MODULES):
			return True
	# A connected stick normally causes the module to be loaded.  Checking the
	# dependency index additionally covers images where module auto-loading has
	# been disabled for another reason, without recursively scanning the module tree.
	modules = _read(f"/lib/modules/{uname().release}/modules.dep").replace("-", "_")
	return any(f"/{module}.ko" in modules for module in RTLSDR_DVB_KERNEL_MODULES)


def setRTLSDRDVBKernelDriverBlacklist(enabled):
	"""Persist the mutually exclusive choice between kernel DVB and RTL-SDR use."""
	if enabled:
		makedirs("/etc/modprobe.d", exist_ok=True)
		temporary = f"{RTLSDR_DVB_BLACKLIST_PATH}.tmp"
		with open(temporary, "w", encoding="utf-8") as fd:
			fd.write("# Managed by Enigma2 DAB+ settings.\n")
			fd.write("# Disable the RTL2832 DVB frontend so librtlsdr can claim the receiver.\n")
			for module in RTLSDR_DVB_KERNEL_MODULES:
				fd.write(f"blacklist {module}\n")
		replace(temporary, RTLSDR_DVB_BLACKLIST_PATH)
	elif exists(RTLSDR_DVB_BLACKLIST_PATH):
		unlink(RTLSDR_DVB_BLACKLIST_PATH)


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
		def decode(value):
			if not value:
				return ""
			if isinstance(value, bytes):
				return value.decode("utf-8", "replace").strip()
			return str(value).strip()

		manufacturer = create_string_buffer(256)
		product = create_string_buffer(256)
		serial = create_string_buffer(256)
		result = self.lib.rtlsdr_get_device_usb_strings(index, manufacturer, product, serial)
		info = {
			"index": index,
			"name": decode(self.lib.rtlsdr_get_device_name(index)),
			"manufacturer": decode(manufacturer.value),
			"product": decode(product.value),
			"serial": decode(serial.value),
			"tunerType": 0,
			"tuner": RTLSDR_TUNERS[0],
			"gains": [],
			"available": result == 0,
			"errorCode": result,
			"error": "" if result == 0 else f"USB string query failed ({result})"
		}
		if probe and info["available"]:
			device = c_void_p()
			result = self.lib.rtlsdr_open(byref(device), index)
			if result == 0 and device:
				try:
					tunerType = int(self.lib.rtlsdr_get_tuner_type(device))
					info["tunerType"] = tunerType
					info["tuner"] = RTLSDR_TUNERS.get(tunerType, f"Unknown ({tunerType})")
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
				info["error"] = f"Unable to open device ({result})"
		return info


def matchSysfs(devices):
	sysfsDevices = usbDevices()
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


RTLSDR_PROBE_TIMEOUT = 3  # Seconds. A stuck USB transfer inside librtlsdr can block indefinitely otherwise.


def _probeRTLSDRDevices(probe, result):
	try:
		library = RTLSDRLibrary()
		result.extend(library.device(index, probe=probe) for index in range(library.count()))
	except (ArgumentError, AttributeError, OSError, ValueError) as err:
		print(f"[RTLSDR] Device enumeration failed: {err}")


def enumerateRTLSDRDevices(probe=False):
	devices = []
	worker = Thread(target=_probeRTLSDRDevices, args=(probe, devices), daemon=True)
	worker.start()
	worker.join(RTLSDR_PROBE_TIMEOUT)
	if worker.is_alive():
		print(f"[RTLSDR] Device enumeration did not respond within {RTLSDR_PROBE_TIMEOUT}s; a USB transfer may be stuck.")
		return []
	matchSysfs(devices)
	serialCounts = {}
	for device in devices:
		serial = device.get("serial", "")
		serialCounts[serial] = serialCounts.get(serial, 0) + 1
	for device in devices:
		serial = device.get("serial", "")
		port = device.get("port", "")
		if serial not in GENERIC_SERIALS and serialCounts.get(serial) == 1:
			key = f"serial:{serial}"
		elif port:
			key = f"port:{port}"
		else:
			key = f"index:{device['index']}"
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
	return hasRTLSDRUSBHardware()


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
		config.dab.rtlsdr.cachedDevice.save()
		config.dab.rtlsdr.cachedTunerType.save()
		config.dab.rtlsdr.cachedTuner.save()
		configfile.save()
	return changed


def isRTLSDREnabled():
	return config.dab.rtlsdr.enabled.value and hasRTLSDRDevice()


def hasRTLSDRBackend():
	return exists("/usr/bin/dab-rtlsdr-welle-e2")


def canScanRTLSDR():
	return isRTLSDREnabled() and hasRTLSDRBackend()


def updateDABBoxInfo(configElement=None):
	hasUSB = hasRTLSDRUSBHardware()
	satellites = getDABSatelliteDefinitions(availableOnly=True)
	ensureDABSatelliteConfig(satellites)
	BoxInfo.setMutableItem("HasRTLSDR", hasUSB)
	BoxInfo.setMutableItem("HasDABSettings", hasUSB or bool(satellites))
	BoxInfo.setMutableItem("CanScanDAB", canScanRTLSDR() or canScanSatelliteDAB(satellites))


class DABUSBInstaller:
	def __init__(self):
		self.session = None
		self.opkg = None
		self.running = False

	def hasRTLSDRRuntime(self):
		return hasRTLSDRBackend() and any(exists(path) for path in RTLSDR_LIBRARY_PATHS)

	def requestInstall(self):
		updateDABBoxInfo()
		if self.running or self.hasRTLSDRRuntime() or not hasRTLSDRUSBHardware() or self.session is None:
			return
		self.running = True
		self.opkg = OpkgComponent()
		self.opkg.addCallback(self.opkgCallback)
		if Toast.instance:
			Toast.instance.showToast(
				_("An RTL-SDR receiver was detected. The optional DAB+ USB runtime is being installed from the feed."),
				Toast.TYPE_INFO, timeout=6)
		self.opkg.runCommand(self.opkg.CMD_REFRESH_INSTALL, {"arguments": ["enigma2-plugin-systemplugins-dabusb"]})

	def opkgCallback(self, event, parameter):
		if event == self.opkg.EVENT_ERROR:
			self.finish(False)
		elif event == self.opkg.EVENT_DONE:
			self.finish(self.hasRTLSDRRuntime())

	def finish(self, success):
		if not self.running:
			return
		self.running = False
		if self.opkg:
			self.opkg.removeCallback(self.opkgCallback)
			self.opkg = None
		if self.session and Toast.instance:
			Toast.instance.showToast(
				_("DAB+ USB support was installed. You can now enable the receiver in Reception settings.") if success else _("DAB+ USB support could not be installed from the feed."),
				Toast.TYPE_INFO if success else Toast.TYPE_ERROR, timeout=10)


dabUSBInstaller = None
dabHotplugNotifier = []


def dabUSBHotplug(device, action):
	if action in ("dab-sdr-add", "dab-sdr-remove") and dabUSBInstaller:
		dabUSBInstaller.requestInstall()


def initRTLSDR(session):
	global dabUSBInstaller
	dabUSBInstaller = DABUSBInstaller()
	dabUSBInstaller.session = session
	updateDABBoxInfo()
	if dabUSBHotplug not in dabHotplugNotifier:
		dabHotplugNotifier.append(dabUSBHotplug)
	# A receiver can already be present before Enigma2 opens the hotplug socket.
	bootProbe = eTimer()
	bootProbe.callback.append(dabUSBInstaller.requestInstall)
	bootProbe.start(2000, True)
	dabUSBInstaller.bootProbe = bootProbe


if not hasattr(config, "dab"):
	config.dab = ConfigSubsection()
if not hasattr(config.dab, "satellites"):
	config.dab.satellites = ConfigSubDict()
if not hasattr(config.dab, "scanSource"):
	config.dab.scanSource = ConfigSelection(default="all", choices=[
		("all", _("USB and satellite")),
		("rtlsdr", _("USB receiver only")),
		("dvb", _("Satellite only"))
	])
if not hasattr(config.dab, "slideshow"):
	config.dab.slideshow = ConfigYesNo(default=True)
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
	config.dab.rtlsdr.automaticGain = ConfigYesNo(default=True)
	# The Welle backend maps this value onto the receiver's discrete gain table.  It
	# is a percentage, not a physical dB value.
	config.dab.rtlsdr.gain = ConfigSelectionNumber(min=0, max=100, stepwidth=1, default=35, units="%")
	config.dab.rtlsdr.ppm = ConfigInteger(default=0, limits=(-200, 200))

ensureDABSatelliteConfig()
config.dab.rtlsdr.enabled.addNotifier(updateDABBoxInfo)
