from Components.ActionMap import NumberActionMap
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.RTLSDR import cacheRTLSDRTuner, enumerateRTLSDRDevices, getActiveRTLSDRTuner, hasAvailableSatelliteDAB, hasRTLSDRBackend, isRTLSDRInUse
from Components.Sources.StaticText import StaticText
from Components.config import ConfigNothing, ConfigText, NoSave, ReadOnly, config, configfile, getConfigListEntry
from Screens.Screen import Screen


def _readOnly(value):
	value = str(value) if value not in (None, "") else _("Not available")
	return ReadOnly(NoSave(ConfigText(default=value, fixed_size=False)))


class RTLSDRSetup(Screen, ConfigListScreen):
	def __init__(self, session):
		Screen.__init__(self, session, mandatoryWidgets=["config", "footnote", "description"], enableHelp=True)
		self.setImage("RTLSDRSetup", "setup")
		self.skinName = ["RTLSDRSetup", "Setup"]
		self.setTitle(_("DAB+ USB receiver"))
		self.devices = []
		self.deviceByKey = {}
		self.list = []
		ConfigListScreen.__init__(self, self.list, session=session, fullUI=True)
		self["footnote"] = Label()
		self["footnote"].hide()
		self["description"] = Label()
		self["key_yellow"] = StaticText("")
		self["key_blue"] = StaticText(_("Refresh"))
		self["refreshActions"] = NumberActionMap(["ColorActions"], {
			"blue": self.refreshDevices
		}, -2)
		self["config"].onSelectionChanged.append(self.selectionChanged)
		self.refreshDevices()
		self.selectionChanged()

	def selectionChanged(self):
		current = self["config"].getCurrent()
		self["description"].setText(current[2] if current and len(current) > 2 else "")

	def refreshDevices(self):
		self.devices = enumerateRTLSDRDevices(probe=True)
		self.deviceByKey = {device["key"]: device for device in self.devices}
		choices = [("auto", _("Automatic"))]
		for device in self.devices:
			label = device.get("name") or device.get("knownModel") or device.get("product") or _("RTL-SDR device")
			serial = device.get("serial")
			port = device.get("port")
			details = [value for value in (serial, "USB %s" % port if port else "") if value]
			choices.append((device["key"], "%s (%s)" % (label, ", ".join(details)) if details else label))
		selected = config.dab.rtlsdr.device.value
		keys = [choice[0] for choice in choices]
		if selected not in keys:
			selected = "auto"
		config.dab.rtlsdr.device.setChoices(choices, default=selected)
		config.dab.rtlsdr.device.value = selected
		self.createSetup()

	def selectedDevice(self):
		key = config.dab.rtlsdr.device.value
		if key == "auto":
			return self.devices[0] if self.devices else None
		return self.deviceByKey.get(key)

	def createSetup(self):
		settings = [
			getConfigListEntry(_("Enable DAB+ USB receiver"), config.dab.rtlsdr.enabled,
				_("Use the RTL-SDR device exclusively for DAB+ reception.")),
			getConfigListEntry(_("Receiver"), config.dab.rtlsdr.device,
				_("Select the RTL-SDR device. Generic devices are identified by their physical USB port."))
		]
		if config.dab.rtlsdr.enabled.value:
			settings.append(getConfigListEntry(_("Scan region"), config.dab.rtlsdr.region,
				_("Limit a DAB+ USB scan to the frequency blocks defined for this region in dab.xml.")))
			if hasAvailableSatelliteDAB():
				settings.append(getConfigListEntry(_("Reception sources to scan"), config.dab.rtlsdr.scanSource,
					_("Scan the USB receiver, available DAB+ satellite feeds, or both.")))
			settings.append(getConfigListEntry(_("Show DAB slideshow"), config.dab.rtlsdr.slideshow,
				_("Replace the static radio background with pictures transmitted by the current DAB+ station.")))
			settings.append(getConfigListEntry(_("Automatic gain"), config.dab.rtlsdr.automaticGain,
				_("Let the tuner select its RF gain automatically.")))
			if not config.dab.rtlsdr.automaticGain.value:
				settings.append(getConfigListEntry(_("RF gain"), config.dab.rtlsdr.gain,
					_("Position in the tuner's supported gain range. The backend selects the closest gain step.")))
			settings.append(getConfigListEntry(_("Frequency correction"), config.dab.rtlsdr.ppm,
				_("Correct the tuner oscillator in parts per million.")))
		settings.append(getConfigListEntry(_("Detected hardware"), NoSave(ConfigNothing())))
		device = self.selectedDevice()
		if device is None:
			settings.append(getConfigListEntry(_("Status"), _readOnly(_("No compatible RTL-SDR device detected"))))
		else:
			inUse = isRTLSDRInUse(device)
			if inUse:
				cacheRTLSDRTuner(device, getActiveRTLSDRTuner())
			status = _("In use by DAB+") if inUse else (_("Ready") if device.get("available") and hasRTLSDRBackend() else (
				_("DAB+ decoder backend is not installed") if device.get("available") else _("Unable to open receiver (%d)") % device.get("errorCode", -1)))
			tuner = device.get("tuner")
			if device.get("probeCached") and tuner:
				tuner = _("%s (cached)") % tuner
			settings.extend([
				getConfigListEntry(_("Status"), _readOnly(status)),
				getConfigListEntry(_("Model"), _readOnly(device.get("name") or device.get("knownModel") or device.get("product"))),
				getConfigListEntry(_("Manufacturer"), _readOnly(device.get("manufacturer"))),
				getConfigListEntry(_("Product"), _readOnly(device.get("product"))),
				getConfigListEntry(_("Serial number"), _readOnly(device.get("serial"))),
				getConfigListEntry(_("USB ID"), _readOnly("%s:%s" % (device.get("vendorId", ""), device.get("productId", "")))),
				getConfigListEntry(_("USB port"), _readOnly(device.get("port"))),
				getConfigListEntry(_("USB speed"), _readOnly("%s Mbit/s" % device.get("speed") if device.get("speed") else "")),
				getConfigListEntry(_("Tuner"), _readOnly(tuner)),
				getConfigListEntry(_("Gain steps"), _readOnly(len(device.get("gains", []))))
			])
		self.list = settings
		self["config"].setList(settings)

	def keyLeft(self):
		ConfigListScreen.keyLeft(self)
		self.createSetup()

	def keyRight(self):
		ConfigListScreen.keyRight(self)
		self.createSetup()

	def keyCancel(self):
		for entry in self["config"].list:
			entry[1].cancel()
		self.close()

	def keySave(self):
		device = self.selectedDevice()
		config.dab.rtlsdr.deviceIndex.value = device.get("index", 0) if device else 0
		config.dab.rtlsdr.save()
		configfile.save()
		self.close()
