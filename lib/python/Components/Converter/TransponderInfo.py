from enigma import eServiceCenter, iPlayableService, iPlayableServicePtr, iServiceInformation

from Components.Converter.Converter import Converter
from Components.Element import cached
from ServiceReference import resolveAlternate
from Tools.Transponder import ConvertToHumanReadable


class TransponderInfo(Converter):
	def __init__(self, tokens):
		Converter.__init__(self, tokens)
		self.type = tokens.split(";")

	def changed(self, what):
		if what[0] != self.CHANGED_SPECIFIC or what[1] == iPlayableService.evStart:
			Converter.changed(self, what)

	@cached
	def getBoolean(self):
		# Finds "DVB-S", "DVB-S2", "DVB-T", "DVB-T2", "DVB-C", "ATSC", "Stream" or combinations of these,
		# e.g. <convert type="TransponderInfo">DVB-S;DVB-S2</convert> to return True for either.
		text = self.getText()
		system = text and text.strip().split() and text.strip().split()[0].lower()  # Get the first group of characters in lower case.
		systems = self.type and [x.lower() for x in self.type if x]  # Only populated entries in lower case.
		return bool(system and systems and system in systems)

	boolean = property(getBoolean)

	@cached
	def getText(self):
		text = ""
		service = self.source.service
		if isinstance(service, iPlayableServicePtr):
			info = service and service.info()
			ref = None
		else:  # Reference.
			info = service and self.source.info
			ref = service
		if info:
			if ref:
				alternativeRef = resolveAlternate(ref)
				if alternativeRef:
					ref = alternativeRef
					info = eServiceCenter.getInstance().info(ref)
				transponderRaw = info.getInfoObject(ref, iServiceInformation.sTransponderData)
				ref = ref.toString().replace("%3a", ":")
			else:
				transponderRaw = info.getInfoObject(iServiceInformation.sTransponderData)
				ref = info.getInfoString(iServiceInformation.sServiceref)
			if transponderRaw:
				transponderData = ConvertToHumanReadable(transponderRaw)
				onid, tsid = [int(x, 16) for x in ref.split(":")[4:6]]  # Retrieve onid and tsid from service reference.
				if not transponderData["system"]:
					transponderData["system"] = transponderRaw.get("tuner_type", "None")
				try:
					system = transponderData["system"]
					if "DVB-T" in system:
						text = f"{system} {tsid}-{onid} {transponderData['channel']} {int(transponderData['frequency'] / 1000000 + 0.5)} MHz {transponderData['bandwidth']}"
					elif "DVB-C" in system:
						text = f"{system} {tsid}-{onid} {int(transponderData['frequency'] / 1000 + 0.5)} MHz {int(transponderData['symbol_rate'] / 1000 + 0.5)} {transponderData['fec_inner']} {transponderData['modulation']}"
					elif "ATSC" in system:
						text = f"{system} {tsid}-{onid} {int(transponderData['frequency'] / 1000 + 0.5)} MHz {transponderData['modulation']}"
					else:
						position = transponderData["orbital_position" if "detailed_satpos" in self.type else "orb_pos"]
						text = f"{system} {tsid}-{onid} {int(transponderData['frequency'] / 1000 + 0.5)} {transponderData['polarization_abbreviation']} {int(transponderData['symbol_rate'] / 1000 + 0.5)} {transponderData['fec_inner']} {transponderData['modulation']} {position}"
				except Exception:
					text = ""
			elif "://" in ref:
				text = f"{_('Stream')} {ref.rsplit('://', 1)[1].split('/')[0]}"
		return text

	text = property(getText)
