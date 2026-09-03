from Components.ActionMap import HelpableActionMap
from Components.config import ConfigNothing, ConfigText, NoSave, ReadOnly, config
from Components.RTLSDR import cacheRTLSDRTuner, enumerateRTLSDRDevices, getActiveRTLSDRTuner, hasAvailableSatelliteDAB, hasRTLSDRBackend, isRTLSDRInUse, updateDABBoxInfo
from Components.Sources.StaticText import StaticText
from Screens.Setup import Setup


class RTLSDRSetup(Setup):
	def __init__(self, session):
		self.devices = []
		self.deviceByKey = {}
		self.hasAvailableSatelliteDAB = hasAvailableSatelliteDAB  # Exposed for the "conditional" eval in 'setup.xml'.
		Setup.__init__(self, session, "RTLSDRSetup")
		self["key_blue"] = StaticText(_("Refresh"))
		self["refreshActions"] = HelpableActionMap(self, ["ColorActions"], {
			"blue": (self.keyRefreshDevices, _("Refresh list of RTL-SDR USB tuners"))
		}, prio=0, description=_("DAB+ USB Tuner Settings Actions"))
		self.keyRefreshDevices()

	def keyRefreshDevices(self):
		self.devices = enumerateRTLSDRDevices(probe=True)
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

	def createSetup(self, appendItems=None, prependItems=None):
		Setup.createSetup(self, appendItems=self.buildDiagnosticsItems())

	def buildDiagnosticsItems(self):
		def readOnly(value):
			value = str(value) if value not in (None, "") else _("Not available")
			return ReadOnly(NoSave(ConfigText(default=value, fixed_size=False)))

		items = [(_("Detected hardware"), NoSave(ConfigNothing()))]
		device = self.selectedDevice()
		if device is None:
			items.append((_("Status"), readOnly(_("No compatible RTL-SDR USB tuner detected"))))
		else:
			inUse = isRTLSDRInUse(device)
			if inUse:
				cacheRTLSDRTuner(device, getActiveRTLSDRTuner())
			status = _("In use by DAB+") if inUse else (_("Ready") if device.get("available") and hasRTLSDRBackend() else (
				_("DAB+ decoder back end not installed") if device.get("available") else _("Unable to open tuner (%d)") % device.get("errorCode", -1)))
			tuner = device.get("tuner")
			if device.get("probeCached") and tuner:
				tuner = _("%s (cached)") % tuner
			items.extend([
				(_("Status"), readOnly(status)),
				(_("Model"), readOnly(device.get("name") or device.get("knownModel") or device.get("product"))),
				(_("Manufacturer"), readOnly(device.get("manufacturer"))),
				(_("Product"), readOnly(device.get("product"))),
				(_("Serial number"), readOnly(device.get("serial"))),
				(_("USB ID"), readOnly(f"{device.get("vendorId", "")}:{device.get("productId", "")}")),
				(_("USB port"), readOnly(device.get("port"))),
				(_("USB speed"), readOnly(f"{device.get("speed")} Mbps" if device.get("speed") else "")),
				(_("Tuner"), readOnly(tuner)),
				(_("Gain steps"), readOnly(len(device.get("gains", []))))
			])
		return items

	def keySave(self):  # This modified the keySave() method in 'ConfigList.py'.
		device = self.selectedDevice()
		config.dab.rtlsdr.deviceIndex.value = device.get("index", 0) if device else 0
		config.dab.rtlsdr.deviceIndex.save()  # Not part of the visible list, so Setup.keySave wouldn't save it.
		Setup.keySave(self)

	def selectedDevice(self):
		key = config.dab.rtlsdr.device.value
		if key == "auto":
			device = self.devices[0] if self.devices else None
		else:
			device = self.deviceByKey.get(key)
		return device
