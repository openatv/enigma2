from xml.etree.ElementTree import parse

from enigma import eServiceCenter, eServiceReference, iServiceInformation

from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.config import config
from ServiceReference import isRadioServiceReference


class ExtendedServiceInfo(Converter):
	SERVICENAME = 0
	SERVICENUMBER = 1
	ORBITALPOSITION = 2
	SATNAME = 3
	PROVIDER = 4
	FROMCONFIG = 5
	ALL = 6

	def __init__(self, tokens):
		Converter.__init__(self, tokens)
		self.satNames = {}
		self.readSatXml()
		self.getLists()
		self.type = {
			"Config": self.FROMCONFIG,
			"OrbitalPosition": self.ORBITALPOSITION,
			"Provider": self.PROVIDER,
			"SatName": self.SATNAME,
			"ServiceName": self.SERVICENAME,
			"ServiceNumber": self.SERVICENUMBER
		}.get(tokens, self.ALL)

	def changed(self, what):
		Converter.changed(self, what)

	def getListFromRef(self, ref):
		channelList = []
		serviceHandler = eServiceCenter.getInstance()
		services = serviceHandler.list(ref)
		bouquets = services and services.getContent("SN", True)
		for bouquet in bouquets:
			services = serviceHandler.list(eServiceReference(bouquet[0]))
			channels = services and services.getContent("SN", True)
			channelList.extend(x[1].replace("\xc2\x86", "").replace("\xc2\x87", "") for x in channels if not x[0].startswith("1:64:"))
		return channelList

	def getLists(self):
		self.tv_list = self.getListFromRef(eServiceReference("1:7:1:0:0:0:0:0:0:0:(type == 1) || (type == 17) || (type == 195) || (type == 25) FROM BOUQUET \"bouquets.tv\" ORDER BY bouquet"))
		self.radio_list = self.getListFromRef(eServiceReference("1:7:2:0:0:0:0:0:0:0:(type == 2) FROM BOUQUET \"bouquets.radio\" ORDER BY bouquet"))

	def getOrbitalPosition(self, info):
		orbital = ""
		transponderData = info.getInfoObject(iServiceInformation.sTransponderData)
		if transponderData is not None and not isinstance(transponderData, float) and transponderData.get("tuner_type") in ("DVB-S", "DVB-S2"):
			position = int(transponderData["orbital_position"])
			orbital = f"{float(3600 - position) / 10.0}W" if position > 1800 else f"{float(position) / 10.0}E"
		return orbital

	def getServiceNumber(self, name, ref):
		number = ""
		serviceList = []
		if isRadioServiceReference(ref):
			serviceList = self.radio_list
		elif ref.startswith("1:0:1"):
			serviceList = self.tv_list
		if name in serviceList[:-1]:
			number = str(serviceList.index(name) + 1)
		return number

	@cached
	def getText(self):
		text = ""
		service = self.source.service
		info = service and service.info()
		if info:
			name = info.getName().replace("\xc2\x86", "").replace("\xc2\x87", "")
			number = self.getServiceNumber(name, info.getInfoString(iServiceInformation.sServiceref))
			orbital = self.getOrbitalPosition(info)
			satName = self.satNames.get(orbital, orbital)
			match self.type:
				case self.FROMCONFIG:
					text = f"{number}. {name}" if config.plugins.ExtendedServiceInfo.showServiceNumber.value is True and number != "" else name
					if config.plugins.ExtendedServiceInfo.showOrbitalPosition.value is True and orbital != "":
						text = f"{text} ({satName})" if config.plugins.ExtendedServiceInfo.orbitalPositionType.value == "name" else f"{text} ({orbital})"
				case self.ORBITALPOSITION:
					text = orbital
				case self.PROVIDER:
					text = info.getInfoString(iServiceInformation.sProvider)
				case self.SATNAME:
					text = satName
				case self.SERVICENAME:
					text = name
				case self.SERVICENUMBER:
					text = number
				case _:
					text = name if number == "" else f"{number}. {name}"
					if orbital != "":
						text = f"{text} ({orbital})"
		return text

	text = property(getText)

	def readSatXml(self):
		satXml = parse("/etc/tuxbox/satellites.xml").getroot()
		if satXml is not None:
			for sat in satXml.findall("sat"):
				name = sat.get("name") or None
				position = sat.get("position") or None
				if name is not None and position is not None:
					position = f"{position[:-1]}.{position[-1:]}"
					position = f"{position[1:]}W" if position.startswith("-") else f"{position}E"
					if position.startswith("."):
						position = f"0{position}"
					self.satNames[position] = name
