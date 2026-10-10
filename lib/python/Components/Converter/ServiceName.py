from enigma import eEPGCache, eServiceCenter, eServiceReference, iPlayableService, iPlayableServicePtr, iServiceInformation

from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.NimManager import nimmanager
from Components.config import config
import Screens.InfoBar
from ServiceReference import ServiceReference, resolveAlternate
from Tools.Directories import fileExists
from Tools.Transponder import ConvertToHumanReadable, getChannelNumber


class ServiceName(Converter):
	NAME = 0
	NAME_ONLY = 1
	NAME_EVENT = 2
	PROVIDER = 3
	REFERENCE = 4
	EDITREFERENCE = 5
	TRANSPONDER = 6
	TUNERSYSTEM = 7
	ORB_POS = 8
	NUMBER = 9

	def __init__(self, tokens):
		Converter.__init__(self, tokens)
		self.epgQuery = eEPGCache.getInstance().lookupEventTime
		self.mode = ""
		if ";" in tokens:
			tokens, self.mode = tokens.split(";")
		self.type = {
			"EditReference": self.EDITREFERENCE,
			"NameAndEvent": self.NAME_EVENT,
			"NameOnly": self.NAME_ONLY,
			"Number": self.NUMBER,
			"OrbitalPosition": self.ORB_POS,
			"Provider": self.PROVIDER,
			"Reference": self.REFERENCE,
			"TransponderInfo": self.TRANSPONDER,
			"TunerSystem": self.TUNERSYSTEM
		}.get(tokens, self.NAME)

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] == iPlayableService.evStart or self.type == self.REFERENCE and what[1] == iPlayableService.evUpdatedInfo:
			Converter.changed(self, what)

	@cached
	def getText(self):
		def getChannelText(frequency):
			result = ""
			for nim in nimmanager.nim_slots:
				if nim.isCompatible("DVB-T"):
					channel = getChannelNumber(frequency, nim.slot)
					if channel:
						result = f"{_('CH')}{channel}"
						break
			return result

		def getOrbitalPosition(transponderInfo):
			position = transponderInfo["orbital_position"]
			if "(" in position:
				position = position.split("(")[1]
				result = f"{position[:-2]}\u00B0{position[-2:-1]}"
			else:
				position = position.split(" ")[0]
				result = f"{position[:-1]}\u00B0{position[-1:]}"
			return result

		def getTransponderInfo(service, info):
			if service:
				alternativeRef = resolveAlternate(service)
				if alternativeRef:
					service = alternativeRef
					info = eServiceCenter.getInstance().info(service)
				transponderData = info.getInfoObject(service, iServiceInformation.sTransponderData)
			else:
				transponderData = info.getInfoObject(iServiceInformation.sTransponderData)
			return service, ConvertToHumanReadable(transponderData) if transponderData else {}

		def isRootBouquet():
			serviceList = Screens.InfoBar.InfoBar.instance.servicelist
			epgBouquet = serviceList and serviceList.getRoot()
			return not ServiceReference(epgBouquet).getServiceName()

		text = ""
		service = self.source.service
		info = None
		if isinstance(service, eServiceReference):
			info = self.source.info
		elif isinstance(service, iPlayableServicePtr):
			info = service and service.info()
			service = None
		if info:
			match self.type:
				case self.EDITREFERENCE | self.REFERENCE:
					if self.type == self.REFERENCE or getattr(self.source, "editmode", False):
						if service:
							alternativeRef = resolveAlternate(service)
							if alternativeRef:
								service = alternativeRef
							text = service.toString()
						else:
							text = info.getInfoString(iServiceInformation.sServiceref)
							path = text and eServiceReference(text).getPath()
							if path and fileExists(f"{path}.meta"):
								with open(f"{path}.meta") as fd:
									text = fd.readline().strip()
				case self.NAME | self.NAME_EVENT | self.NAME_ONLY:
					name = service and info.getName(service)
					if name is None:
						name = info.getName()
					name = name.replace("\xc2\x86", "").replace("\xc2\x87", "").replace("_", " ")
					if self.type == self.NAME_EVENT:
						event = info and info.getEvent(0)
						if not event and info:
							event = self.epgQuery(eServiceReference(info.getInfoString(iServiceInformation.sServiceref)), -1, 0)
						text = f"{name} - " if event is None else f"{name} - {event.getEventName()}"
					elif self.type != self.NAME_ONLY and config.usage.show_infobar_channel_number.value and hasattr(self.source, "serviceref") and self.source.serviceref and "0:0:0:0:0:0:0:0:0" not in self.source.serviceref.toString():
						channelNum = self.source.serviceref.getChannelNum() or None
						text = name if channelNum is None else f"{channelNum}   {name}"
					else:
						text = name
				case self.NUMBER:
					serviceRef = getattr(self.source, "serviceref", None)
					channelNum = serviceRef and serviceRef.getChannelNum() or None
					text = "" if channelNum is None else str(channelNum)
				case self.ORB_POS:
					transponderInfo = getTransponderInfo(service, info)[1]
					if "orbital_position" in transponderInfo:
						text = getOrbitalPosition(transponderInfo)
				case self.PROVIDER:
					text = info.getInfoString(iServiceInformation.sProvider)
				case self.TRANSPONDER:
					service, transponderInfo = getTransponderInfo(service, info)
					if ("InRootOnly" in self.mode and not isRootBouquet()) or ("NoRoot" in self.mode and isRootBouquet()):
						text = ""
					elif transponderInfo:
						system = transponderInfo["system"]
						if system is None:  # Catch driver bug.
							text = ""
						elif "DVB-T" in system:
							text = f"{system} {getChannelText(transponderInfo['frequency'])} {transponderInfo['frequency']}/{transponderInfo['bandwidth']}"
						elif "DVB-C" in system:
							text = f"{system} {transponderInfo['frequency']} {transponderInfo['symbol_rate']} {transponderInfo['fec_inner']} {transponderInfo['modulation']}"
						else:
							text = f"{getOrbitalPosition(transponderInfo)} {system} {transponderInfo['frequency']} {transponderInfo['polarization_abbreviation']} {transponderInfo['symbol_rate']} {transponderInfo['fec_inner']} {transponderInfo['modulation']}"
					else:
						refString = service.toString() if service else info.getInfoString(iServiceInformation.sServiceref)
						if "%3a//" in refString:
							text = refString.rsplit("%3a//", 1)[1].split("/")[0]
				case self.TUNERSYSTEM:
					text = getTransponderInfo(service, info)[1].get("system") or ""
		return text

	text = property(getText)
