# -*- coding: UTF-8 -*-
##
## Extended Service-Info Converter
##
## Example usage in the skin.xml:
##		<widget source="session.CurrentService" render="Label" position="164,435" size="390,28" font="Regular;26" transparent="1" >
##			<convert type="ExtServiceInfo">Config</convert>
##		</widget>
##
## Known issues with the ServiceNumber Converter:
## If you have one service in different bouquets the first index of the service will be taken
## If you rename, move, delete or add a channel the numbers will not be OK any more. You have to restart E2 then
##
from Components.config import config
from Components.Converter.Converter import Converter
from Components.Element import cached
from enigma import eServiceCenter, eServiceReference, iServiceInformation
from xml.etree.cElementTree import parse

##########################################################################

class ExtServiceInfo(Converter, object):
	SERVICENAME = 0
	SERVICENUMBER = 1
	SERVICENUMBERANDNAME = 2
	ORBITALPOSITION = 3
	SATNAME = 4
	PROVIDER = 5
	FROMCONFIG = 6
	ALL = 7

	def __init__(self, type):
		Converter.__init__(self, type)
		self.satNames = {}
		self.readSatXml()
		self.getLists()

		if type == "ServiceName":
			self.type = self.SERVICENAME
		elif type == "ServiceNumber":
			self.type = self.SERVICENUMBER
		elif type == "ServiceNumberAndName":
			self.type = self.SERVICENUMBERANDNAME
		elif type == "OrbitalPosition":
			self.type = self.ORBITALPOSITION
		elif type == "SatName":
			self.type = self.SATNAME
		elif type == "Provider":
			self.type = self.PROVIDER
		elif type == "Config":
			self.type = self.FROMCONFIG
		else:
			self.type = self.ALL

	@cached
	def getText(self):
		service = self.source.service
		info = service and service.info()
		if not info:
			return ""

		text = ""
		name = info.getName().replace('\xc2\x86', '').replace('\xc2\x87', '')
		number = self.getServiceNumber(name, info.getInfoString(iServiceInformation.sServiceref))
		orbital = self.getOrbitalPosition(info)
		satName = self.satNames.get(orbital, orbital)

		if self.type == self.SERVICENAME:
			text = name
		elif self.type == self.SERVICENUMBER:
			text = number
		elif self.type == self.SERVICENUMBERANDNAME:
			text = number + " " + name
		elif self.type == self.ORBITALPOSITION:
			text = orbital
		elif self.type == self.SATNAME:
			text = satName
		elif self.type == self.PROVIDER:
			text = info.getInfoString(iServiceInformation.sProvider)
		elif self.type == self.FROMCONFIG:
			if config.plugins.ExtendedServiceInfo.showServiceNumber.value == True and number != "":
				text = "%s. %s" % (number, name)
			else:
				text = name
			if config.plugins.ExtendedServiceInfo.showOrbitalPosition.value == True and orbital != "":
				if config.plugins.ExtendedServiceInfo.orbitalPositionType.value == "name":
					text = "%s (%s)" % (text, satName)
				else:
					text = "%s (%s)" % (text, orbital)
		else:
			if number == "":
				text = name
			else:
				text = "%s. %s" % (number, name)
			if orbital != "":
				text = "%s (%s)" % (text, orbital)

		return text

	text = property(getText)

	def changed(self, what):
		Converter.changed(self, what)

	def getListFromRef(self, ref):
		list = []

		serviceHandler = eServiceCenter.getInstance()
		services = serviceHandler.list(ref)
		bouquets = services and services.getContent("SN", True)

		for bouquet in bouquets:
			services = serviceHandler.list(eServiceReference(bouquet[0]))
			channels = services and services.getContent("SN", True)
			for channel in channels:
				if not channel[0].startswith("1:64:"): # Ignore marker
					list.append(channel[1].replace('\xc2\x86', '').replace('\xc2\x87', ''))

		return list

	def getLists(self):
		self.tv_list = self.getListFromRef(eServiceReference('1:7:1:0:0:0:0:0:0:0:(type == 1) || (type == 17) || (type == 195) || (type == 25) FROM BOUQUET "bouquets.tv" ORDER BY bouquet'))
		self.radio_list = self.getListFromRef(eServiceReference('1:7:2:0:0:0:0:0:0:0:(type == 2) FROM BOUQUET "bouquets.radio" ORDER BY bouquet'))

	def readSatXml(self):
		satXml = parse("/etc/tuxbox/satellites.xml").getroot()
		if satXml is not None:
			for sat in satXml.findall("sat"):
				name = sat.get("name") or None
				position = sat.get("position") or None
				if name is not None and position is not None:
					position = "%s.%s" % (position[:-1], position[-1:])
					if position.startswith("-"):
						position = "%sW" % position[1:]
					else:
						position = "%sE" % position
					if position.startswith("."):
						position = "0%s" % position
					self.satNames[position] = name

	def getServiceNumber(self, name, ref):
		list = []
		if ref.startswith("1:0:2"):
			list = self.radio_list
		elif ref.startswith("1:0:1"):
			list = self.tv_list
		number = ""
		if name in list:
			for idx in range(1, len(list)):
				if name == list[idx-1]:
					number = str(idx)
					break
		return number

	def getOrbitalPosition(self, info):
		transponderData = info.getInfoObject(iServiceInformation.sTransponderData)
		orbital = 0
		if transponderData is not None:
			if isinstance(transponderData, float):
				return ""
			if transponderData.has_key("tuner_type"):
				if (transponderData["tuner_type"] == "DVB-S") or (transponderData["tuner_type"] == "DVB-S2"):
					orbital = transponderData["orbital_position"]
					orbital = int(orbital)
					if orbital > 1800:
						orbital = str((float(3600 - orbital))/10.0) + "W"
					else:
						orbital = str((float(orbital))/10.0) + "E"
					return orbital
		return ""
