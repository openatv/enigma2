from enigma import iServiceInformation

from Components.ActionMap import HelpableActionMap
from Components.config import ConfigText, ConfigYesNo, NoSave, ReadOnly, config
from Components.RTLSDR import cacheRTLSDRTuner, ensureDABSatelliteConfig, enumerateRTLSDRSysfsDevices, getDABSatelliteDefinitions, hasAvailableSatelliteDAB, hasRTLSDRBackend, hasRTLSDRDVBKernelDriver, hasRTLSDRUSBHardware, isRTLSDRDVBKernelDriverBlacklisted, isRTLSDRInUse, setRTLSDRDVBKernelDriverBlacklist, updateDABBoxInfo
from Components.Sources.StaticText import StaticText
from Screens.MessageBox import MessageBox
from Screens.Setup import Setup


class RTLSDRSetup(Setup):
	def __init__(self, session):
		self.devices = []
		self.deviceByKey = {}
		self.usbHardwarePresent = hasRTLSDRUSBHardware()
		self.dvbKernelDriverPresent = hasRTLSDRDVBKernelDriver()
		self.dvbKernelBlacklist = NoSave(ConfigYesNo(default=isRTLSDRDVBKernelDriverBlacklisted()))
		self.hasAvailableSatelliteDAB = hasAvailableSatelliteDAB  # Exposed for the "conditional" eval in 'setup.xml'.
		Setup.__init__(self, session, "RTLSDRSetup")
		self["key_blue"] = StaticText(_("Refresh") if self.hasRTLSDRHardware() else "")
		self["refreshActions"] = HelpableActionMap(self, ["ColorActions"], {
			"blue": (self.keyRefreshDevices, _("Refresh list of RTL-SDR USB tuners"))
		}, prio=0, description=_("DAB+ Settings Actions"))
		self.keyRefreshDevices()

	def keyRefreshDevices(self):
		# Never call rtlsdr_open() here. Apart from delaying Enigma2's main
		# loop, that would temporarily detach a receiver which is being used by
		# the DVB kernel driver. USB and driver identity are already in sysfs.
		self.devices = enumerateRTLSDRSysfsDevices()
		self.usbHardwarePresent = bool(self.devices)
		self.dvbKernelDriverPresent = hasRTLSDRDVBKernelDriver(self.devices)
		updateDABBoxInfo()
		self.deviceByKey = {device["key"]: device for device in self.devices}
		choices = [("auto", _("Automatic"))]
		for device in self.devices:
			label = device.get("name") or device.get("knownModel") or device.get("product") or _("RTL-SDR USB tuner")
			serial = device.get("serial")
			port = device.get("port")
			details = [value for value in (serial, f"USB {port}" if port else "") if value]
			choices.append((device["key"], f"{label} ({", ".join(details)})" if details else label))
		selected = config.dab.rtlsdr.device.value
		if selected not in [choice[0] for choice in choices]:
			selected = "auto"
		config.dab.rtlsdr.device.setChoices(default=selected, choices=choices)
		config.dab.rtlsdr.device.value = selected
		self.createSetup()

	def hasRTLSDRHardware(self):  # Exposed for the "conditional" eval in 'setup.xml'.
		return self.usbHardwarePresent

	def showDVBKernelBlacklist(self):  # Exposed for the "conditional" eval in 'setup.xml'.
		return self.hasRTLSDRHardware() and (self.dvbKernelDriverPresent or self.dvbKernelBlacklist.value)

	def createSetup(self, appendItems=None, prependItems=None):
		Setup.createSetup(self, prependItems=self.buildCommonItems() + self.buildSatelliteItems(), appendItems=self.buildDiagnosticsItems())

	def buildCommonItems(self):
		items = [
			(_("Common settings"),),
			((_("Show DAB+ slideshow"), 1), config.dab.slideshow,
				_("Replace the static radio background with pictures transmitted by the current DAB+ station."))
		]
		if self.hasRTLSDRHardware() and self.hasAvailableSatelliteDAB():
			items.append((
				(_("Reception sources to scan"), 1),
				config.dab.scanSource,
				_("Scan the USB tuner, available DAB+ satellite feeds, or both.")))
		return items

	def buildSatelliteItems(self):
		definitions = getDABSatelliteDefinitions(availableOnly=True)
		if len(definitions) < 2:
			return []
		settings = ensureDABSatelliteConfig(definitions)
		items = [(_("Satellite feeds to scan"),)]
		for definition in definitions:
			selection = settings.get(str(definition["position"]))
			if selection is not None:
				label = _("%s (motor)") % definition["label"] if definition["motorized"] else definition["label"]
				items.append((
					((_("Scan %s") % label), 1),
					selection,
					_("Include this configured satellite position in the DAB+ scan. Disable it to skip the position.")))
		return items

	def buildDiagnosticsItems(self):
		def readOnly(value):
			value = str(value) if value not in (None, "") else _("Not available")
			return ReadOnly(NoSave(ConfigText(default=value, fixed_size=False)))

		if not self.hasRTLSDRHardware():
			return []
		items = [(_("Detected USB hardware"),)]
		device = self.selectedDevice()
		if device is None:
			items.append(((_("Status"), 1), readOnly(_("No compatible RTL-SDR USB tuner detected"))))
		else:
			inUse = isRTLSDRInUse(device)
			if inUse:
				cacheRTLSDRTuner(device, self.getActiveRTLSDRTuner())
			if inUse:
				status = _("In use by DAB+")
			elif device.get("available"):
				status = _("Ready") if hasRTLSDRBackend() else _("DAB+ decoder back end not installed")
			else:
				status = _("Unable to open tuner (%d)") % device.get("errorCode", -1)
			tuner = device.get("tuner")
			if device.get("probeCached") and tuner:
				tuner = _("%s (cached)") % tuner
			items.extend([
				((_("Status"), 1), readOnly(status)),
				((_("Model"), 1), readOnly(device.get("name") or device.get("knownModel") or device.get("product"))),
				((_("Manufacturer"), 1), readOnly(device.get("manufacturer"))),
				((_("Product"), 1), readOnly(device.get("product"))),
				((_("Serial number"), 1), readOnly(device.get("serial"))),
				((_("USB ID"), 1), readOnly(f"{device.get("vendorId", "")}:{device.get("productId", "")}")),
				((_("USB port"), 1), readOnly(device.get("port"))),
				((_("USB speed"), 1), readOnly(f"{device.get("speed")} Mbps" if device.get("speed") else "")),
				((_("Kernel driver"), 1), readOnly(device.get("driver"))),
				((_("DVB frontend"), 1), readOnly(", ".join(device.get("frontends", ())))),
				((_("Tuner"), 1), readOnly(tuner)),
				((_("Gain steps"), 1), readOnly(len(device.get("gains", []))))
			])
		return items

	def keySave(self):  # This modified the keySave() method in 'ConfigList.py'.
		if self.dvbKernelBlacklist.isChanged():
			try:
				setRTLSDRDVBKernelDriverBlacklist(self.dvbKernelBlacklist.value)
			except OSError as err:
				self.session.open(
					MessageBox,
					_("The RTL2832 kernel driver blacklist could not be updated:\n%s") % err,
					type=MessageBox.TYPE_ERROR,
					timeout=10)
				return
		device = self.selectedDevice()
		config.dab.rtlsdr.deviceIndex.value = device.get("index", 0) if device else 0
		config.dab.rtlsdr.deviceIndex.save()  # Not part of the visible list, so Setup.keySave wouldn't save it.
		updateDABBoxInfo()
		Setup.keySave(self)

	def selectedDevice(self):
		key = config.dab.rtlsdr.device.value
		if key == "auto":
			device = self.devices[0] if self.devices else None
		else:
			device = self.deviceByKey.get(key)
		return device

	def getActiveRTLSDRTuner(self):
		try:
			reference = self.session.nav.getCurrentlyPlayingServiceReference()
			if reference and reference.getPath().startswith("dab://rtlsdr/"):
				service = self.session.nav.getCurrentService()
				info = service and service.info()
				field = getattr(iServiceInformation, "sDABReceiverName", None)
				return info.getInfoString(field).strip() if info and field is not None else ""
		except (AttributeError, TypeError, ValueError):
			pass
		return ""
