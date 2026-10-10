from xml.etree.ElementTree import parse

from enigma import iServiceInformation

from Components.Converter.Converter import Converter
from Components.Converter.Poll import Poll
from Components.Element import cached


class SmartInfo(Poll, Converter):
	EXPERTINFO = 0

	def __init__(self, tokens):
		Converter.__init__(self, tokens)
		Poll.__init__(self)
		self.type = self.EXPERTINFO
		self.poll_interval = 30000
		self.poll_enabled = True
		self.ar_fec = ("Auto", "1/2", "2/3", "3/4", "5/6", "7/8", "3/5", "4/5", "8/9", "9/10", "None", "None", "None", "None", "None")
		self.ar_pol = ("H", "V", "CL", "CR", "na", "na", "na", "na", "na", "na", "na", "na")
		self.satNames = {}
		self.readSatXml()

	def changed(self, what):
		Converter.changed(self, what)

	def getOrbitalPosition(self, info):
		orbital = ""
		transponderData = info.getInfoObject(iServiceInformation.sTransponderData)
		if transponderData is not None and not isinstance(transponderData, float) and transponderData.get("tuner_type") in ("DVB-S", "DVB-S2"):
			position = int(transponderData["orbital_position"])
			orbital = f"{float(3600 - position) / 10.0}W" if position > 1800 else f"{float(position) / 10.0}E"
		return orbital

	@cached
	def getText(self):
		text = ""
		service = self.source.service
		info = service and service.info()
		if info:
			if self.type == self.EXPERTINFO:
				orbital = self.getOrbitalPosition(info)
				satName = self.satNames.get(orbital, orbital)
				frontendInfo = service and service.frontendInfo()
				if frontendInfo is not None:
					frontendData = frontendInfo and frontendInfo.getAll(True)
					if frontendData is not None:
						tunerType = frontendData.get("tuner_type")
						if tunerType in ("DVB-C", "DVB-S"):
							frequency = f"{frontendData.get('frequency') / 1000} MHz"
							symbolRate = f"{frontendData.get('symbol_rate') / 1000}"
							try:
								polarization = frontendData.get("polarization") if tunerType == "DVB-S" else 0
								text = f"{frequency} {self.ar_pol[polarization]} {self.ar_fec[frontendData.get('fec_inner')]} {symbolRate} "
							except Exception:
								text = f"{frequency} {symbolRate} "
						elif tunerType == "DVB-T":
							text = f"{_('Frequency: ')}{frontendData.get('frequency') / 1000} MHz"
					text = f"{text} {satName}"
			else:
				text = "n/a"
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
