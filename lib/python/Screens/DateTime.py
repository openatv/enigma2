from Components.ActionMap import HelpableActionMap
from Components.config import config
from Components.DateTimes import dateTimes
from Components.NetworkTime import ntpSyncPoller
from Components.Sources.StaticText import StaticText
from Screens.Setup import Setup
from Tools.Geolocation import geolocation


class DateTime(Setup):
	def __init__(self, session):
		def updatePreviews(configElement):
			dateTimes.updateDatesAndTimes()
			self.setFootnote(f"{_("Preview")}:  {dateTimes.getDateTime()}")

		def updateNetworkTime():
			if config.misc.SyncTimeUsing.isChanged() or config.misc.NTPserver.isChanged() or config.misc.useNTPminutes.isChanged():
				ntpSyncPoller.timeCheck()

		def removeNotifiers():
			for configElement in self.configElements:
				configElement.removeNotifier(updatePreviews)
			dateTimes.updateDatesAndTimes()

		Setup.__init__(self, session=session, setup="DateTime")
		self["key_yellow"] = StaticText()
		self["geolocationActions"] = HelpableActionMap(self, "ColorActions", {
			"yellow": (self.keyUseGeolocation, _("Use geolocation to set the current time zone location"))
		}, prio=0, description=_("Date and Time Setup Actions"))
		self.configElements = dateTimes.getConfigElements()
		for configElement in self.configElements:
			configElement.addNotifier(updatePreviews, initial_call=False)
		self.addSaveNotifier(updateNetworkTime)
		updatePreviews(None)
		self.selectionChanged()
		self.onClose.append(removeNotifiers)

	def selectionChanged(self):
		if Setup.getCurrentItem(self) in (config.timezone.area, config.timezone.val):
			self["key_yellow"].setText(_("Use Geolocation"))
			self["geolocationActions"].setEnabled(True)
		else:
			self["key_yellow"].setText("")
			self["geolocationActions"].setEnabled(False)
		Setup.selectionChanged(self)
		if Setup.getCurrentItem(self) in self.configElements:
			self.setFootnote(f"{_("Preview")}:  {dateTimes.getDateTime()}")

	def keyUseGeolocation(self):
		def keyUseGeolocationCallback(geolocationData):
			if geolocationData.get("proxy", True):
				self.setFootnote(_("Geolocation data is not available."))
			else:
				tz = geolocationData.get("timezone", None)
				if tz is None or "/" not in tz:
					self.setFootnote(_("Geolocation data does not contain time zone information."))
				else:
					areaItem = None
					valItem = None
					for item in self["config"].list:
						if len(item) > 1 and item[1] is config.timezone.area:
							areaItem = item
						if len(item) > 1 and item[1] is config.timezone.val:
							valItem = item
					area, zone = tz.split("/", 1)  # All timezones should be in IANA Time Zones format (Area/Location).
					config.timezone.area.value = area
					if areaItem is not None:
						areaItem[1].changed()
					self["config"].invalidate(areaItem)
					config.timezone.val.value = zone
					if valItem is not None:
						valItem[1].changed()
					self["config"].invalidate(valItem)
					self.setFootnote(_("Geolocation data has been used to set the time zone."))

		geolocation.getGeolocationData(fields="status,message,timezone,proxy", screen=self, callback=keyUseGeolocationCallback)

	def yellow(self):  # Invoked from the Wizard.
		self.keyUseGeolocation()
