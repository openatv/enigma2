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
			dateTimes.updateDatesAndTimes()

		def removeNotifiers():
			date.layout.removeNotifier(updatePreviews)
			date.dayFormat.removeNotifier(updatePreviews)
			date.dateFormat.removeNotifier(updatePreviews)
			date.monthFormat.removeNotifier(updatePreviews)
			date.daySeparator.removeNotifier(updatePreviews)
			date.firstSeparator.removeNotifier(updatePreviews)
			date.secondSeparator.removeNotifier(updatePreviews)
			date.suffix.removeNotifier(updatePreviews)
			date.timeSeparator.removeNotifier(updatePreviews)
			time.layout.removeNotifier(updatePreviews)
			time.hourFormat.removeNotifier(updatePreviews)
			time.meridiemFormat.removeNotifier(updatePreviews)
			time.secondsFormat.removeNotifier(updatePreviews)
			time.separator.removeNotifier(updatePreviews)
			dateTimes.updateDatesAndTimes()

		Setup.__init__(self, session=session, setup="DateTime")
		self["key_yellow"] = StaticText()
		self["geolocationActions"] = HelpableActionMap(self, "ColorActions", {
			"yellow": (self.keyUseGeolocation, _("Use geolocation to set the current time zone location"))
		}, prio=0, description=_("Date and Time Setup Actions"))
		date = config.usage.date
		time = config.usage.time
		date.layout.addNotifier(updatePreviews, initial_call=False)
		date.dayFormat.addNotifier(updatePreviews, initial_call=False)
		date.dateFormat.addNotifier(updatePreviews, initial_call=False)
		date.monthFormat.addNotifier(updatePreviews, initial_call=False)
		date.daySeparator.addNotifier(updatePreviews, initial_call=False)
		date.firstSeparator.addNotifier(updatePreviews, initial_call=False)
		date.secondSeparator.addNotifier(updatePreviews, initial_call=False)
		date.suffix.addNotifier(updatePreviews, initial_call=False)
		date.timeSeparator.addNotifier(updatePreviews, initial_call=False)
		time.layout.addNotifier(updatePreviews, initial_call=False)
		time.hourFormat.addNotifier(updatePreviews, initial_call=False)
		time.meridiemFormat.addNotifier(updatePreviews, initial_call=False)
		time.secondsFormat.addNotifier(updatePreviews, initial_call=False)
		time.separator.addNotifier(updatePreviews, initial_call=False)
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
		date = config.usage.date
		time = config.usage.time
		if Setup.getCurrentItem(self) in (date.layout, date.dayFormat, date.dateFormat, date.monthFormat, date.daySeparator,
				date.firstSeparator, date.secondSeparator, date.suffix, date.timeSeparator, time.layout,
				time.hourFormat, time.meridiemFormat, time.secondsFormat, time.separator):
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
