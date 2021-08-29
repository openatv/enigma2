from Components.ActionMap import HelpableActionMap
from Components.config import config
from Components.Sources.StaticText import StaticText
from Screens.Setup import Setup
from Tools.Geolocation import geolocation


class Time(Setup):
	def __init__(self, session):
		Setup.__init__(self, session=session, setup="Time")
		self["key_yellow"] = StaticText("")
		self["geolocationActions"] = HelpableActionMap(self, "ColorActions", {
			"yellow": (self.useGeolocation, _("Use geolocation to set the current time zone location"))
		}, prio=0, description=_("Time Setup Actions"))
		self.selectionChanged()

	def selectionChanged(self):
		if Setup.getCurrentItem(self) in (config.timezone.area, config.timezone.val):
			self["key_yellow"].setText(_("Use Geolocation"))
			self["geolocationActions"].setEnabled(True)
		else:
			self["key_yellow"].setText("")
			self["geolocationActions"].setEnabled(False)
		Setup.selectionChanged(self)

	def useGeolocation(self):
		geolocationData = geolocation.getGeolocationData(fields="status,message,timezone,proxy")
		if geolocationData.get("proxy", True):
			self.setFootnote(_("Geolocation is not available."))
			return
		tz = geolocationData.get("timezone", None)
		if tz is None:
			self.setFootnote(_("Geolocation does not contain time zone information."))
		else:
			areaItem = None
			valItem = None
			for item in self["config"].list:
				if item[1] is config.timezone.area:
					areaItem = item
				if item[1] is config.timezone.val:
					valItem = item
			area, zone = tz.split("/", 1)
			config.timezone.area.value = area
			if areaItem is not None:
				areaItem[1].changed()
			self["config"].invalidate(areaItem)
			config.timezone.val.value = zone
			if valItem is not None:
				valItem[1].changed()
			self["config"].invalidate(valItem)
			self.setFootnote(_("Geolocation has been used to set the time zone."))

	def yellow(self):  # Invoked from the Wizard.
		self.useGeolocation()
