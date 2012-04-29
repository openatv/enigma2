# shamelessly copied from pliExpertInfo (Vali, Mirakels, Littlesat)

from enigma import iServiceInformation
from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.config import config
from Tools.Transponder import ConvertToHumanReadable
from Tools.GetEcmInfo import GetEcmInfo
from Poll import Poll

def addspace(text):
	if text:
		text += " "
	return text

class PliExtraInfo(Poll, Converter, object):
	def __init__(self, type):
		Converter.__init__(self, type)
		Poll.__init__(self)
		self.type = type
		self.poll_interval = 1000
		self.poll_enabled = True
		self.caid_data = (
			( "0x100",  "0x1ff", "Seca",    "S" ),
			( "0x500",  "0x5ff", "Via",     "V" ),
			( "0x600",  "0x6ff", "Irdeto",  "I" ),
			( "0x900",  "0x9ff", "NDS",     "Nd"),
			( "0xb00",  "0xbff", "Conax",   "Co"),
			( "0xd00",  "0xdff", "CryptoW", "Cw"),
			("0x1700", "0x17ff", "Beta",    "B" ),
			("0x1800", "0x18ff", "Nagra",   "N" ),
			("0x2600", "0x2600", "Biss",    "Bi"),
			("0x4ae0", "0x4ae1", "Dre",     "D" )
		)
		self.ecmdata = GetEcmInfo()

	def getCryptoInfo(self,info):
		if (info.getInfo(iServiceInformation.sIsCrypted) == 1):
			data = self.ecmdata.getEcmData()
			self.current_source = data[0]
			self.current_caid = data[1]
			self.current_provid = data[2]
			self.current_ecmpid = data[3]
		else:
			self.current_source = ""
			self.current_caid = "0"
			self.current_provid = "0"
			self.current_ecmpid = "0"

	def createCryptoBar(self,info):
		res = ""
		available_caids = info.getInfoObject(iServiceInformation.sCAIDs)

		for caid_entry in self.caid_data:
			if int(self.current_caid, 16) >= int(caid_entry[0], 16) and int(self.current_caid, 16) <= int(caid_entry[1], 16):
				color="\c0000??00"
			else:
				color = "\c007?7?7?"
				try:
					for caid in available_caids:
						if caid >= int(caid_entry[0], 16) and caid <= int(caid_entry[1], 16):
							color="\c00????00"
				except:
					pass

			if res: res += " "
			res += color + caid_entry[3]

		res += "\c00??????"
		return res

	def createCryptoSeca(self,info):
		available_caids = info.getInfoObject(iServiceInformation.sCAIDs)
		if int(self.current_caid, 16) >= int('0x100', 16) and int(self.current_caid, 16) <= int('0x1ff', 16):
			color="\c004c7d3f"
		else:
			color = "\c009?9?9?"
			try:
				for caid in available_caids:
					if caid >= int('0x100', 16) and caid <= int('0x1ff', 16):
						color="\c00eeee00"
			except:
				pass
		res = color + 'S'
		res += "\c00??????"
		return res

	def createCryptoVia(self,info):
		available_caids = info.getInfoObject(iServiceInformation.sCAIDs)
		if int(self.current_caid, 16) >= int('0x500', 16) and int(self.current_caid, 16) <= int('0x5ff', 16):
			color="\c004c7d3f"
		else:
			color = "\c009?9?9?"
			try:
				for caid in available_caids:
					if caid >= int('0x500', 16) and caid <= int('0x5ff', 16):
						color="\c00eeee00"
			except:
				pass
		res = color + 'V'
		res += "\c00??????"
		return res

	def createCryptoIrdeto(self,info):
		available_caids = info.getInfoObject(iServiceInformation.sCAIDs)
		if int(self.current_caid, 16) >= int('0x600', 16) and int(self.current_caid, 16) <= int('0x6ff', 16):
			color="\c004c7d3f"
		else:
			color = "\c009?9?9?"
			try:
				for caid in available_caids:
					if caid >= int('0x600', 16) and caid <= int('0x6ff', 16):
						color="\c00eeee00"
			except:
				pass
		res = color + 'I'
		res += "\c00??????"
		return res

	def createCryptoNDS(self,info):
		available_caids = info.getInfoObject(iServiceInformation.sCAIDs)
		if int(self.current_caid, 16) >= int('0x900', 16) and int(self.current_caid, 16) <= int('0x9ff', 16):
			color="\c004c7d3f"
		else:
			color = "\c009?9?9?"
			try:
				for caid in available_caids:
					if caid >= int('0x900', 16) and caid <= int('0x9ff', 16):
						color="\c00eeee00"
			except:
				pass
		res = color + 'NDS'
		res += "\c00??????"
		return res

	def createCryptoConax(self,info):
		available_caids = info.getInfoObject(iServiceInformation.sCAIDs)
		if int(self.current_caid, 16) >= int('0xb00', 16) and int(self.current_caid, 16) <= int('0xbff', 16):
			color="\c004c7d3f"
		else:
			color = "\c009?9?9?"
			try:
				for caid in available_caids:
					if caid >= int('0xb00', 16) and caid <= int('0xbff', 16):
						color="\c00eeee00"
			except:
				pass
		res = color + 'CO'
		res += "\c00??????"
		return res

	def createCryptoCryptoW(self,info):
		available_caids = info.getInfoObject(iServiceInformation.sCAIDs)
		if int(self.current_caid, 16) >= int('0xd00', 16) and int(self.current_caid, 16) <= int('0xdff', 16):
			color="\c004c7d3f"
		else:
			color = "\c009?9?9?"
			try:
				for caid in available_caids:
					if caid >= int('0xd00', 16) and caid <= int('0xdff', 16):
						color="\c00eeee00"
			except:
				pass
		res = color + 'CW'
		res += "\c00??????"
		return res

	def createCryptoBeta(self,info):
		available_caids = info.getInfoObject(iServiceInformation.sCAIDs)
		if int(self.current_caid, 16) >= int('0x1700', 16) and int(self.current_caid, 16) <= int('0x17ff', 16):
			color="\c004c7d3f"
		else:
			color = "\c009?9?9?"
			try:
				for caid in available_caids:
					if caid >= int('0x1700', 16) and caid <= int('0x17ff', 16):
						color="\c00eeee00"
			except:
				pass
		res = color + 'B'
		res += "\c00??????"
		return res

	def createCryptoNagra(self,info):
		available_caids = info.getInfoObject(iServiceInformation.sCAIDs)
		if int(self.current_caid, 16) >= int('0x1800', 16) and int(self.current_caid, 16) <= int('0x18ff', 16):
			color="\c004c7d3f"
		else:
			color = "\c009?9?9?"
			try:
				for caid in available_caids:
					if caid >= int('0x1800', 16) and caid <= int('0x18ff', 16):
						color="\c00eeee00"
			except:
				pass
		res = color + 'N'
		res += "\c00??????"
		return res

	def createCryptoBiss(self,info):
		available_caids = info.getInfoObject(iServiceInformation.sCAIDs)
		if int(self.current_caid, 16) >= int('0x2600', 16) and int(self.current_caid, 16) <= int('0x26ff', 16):
			color="\c004c7d3f"
		else:
			color = "\c009?9?9?"
			try:
				for caid in available_caids:
					if caid >= int('0x2600', 16) and caid <= int('0x26ff', 16):
						color="\c00eeee00"
			except:
				pass
		res = color + 'BI'
		res += "\c00??????"
		return res

	def createCryptoDre(self,info):
		available_caids = info.getInfoObject(iServiceInformation.sCAIDs)
		if int(self.current_caid, 16) >= int('0x4ae0', 16) and int(self.current_caid, 16) <= int('0x4ae1', 16):
			color="\c004c7d3f"
		else:
			color = "\c009?9?9?"
			try:
				for caid in available_caids:
					if caid >= int('0x4ae0', 16) and caid <= int('0x4ae1', 16):
						color="\c00eeee00"
			except:
				pass
		res = color + 'DC'
		res += "\c00??????"
		return res

	def createCryptoSpecial(self,info):
		caid_name = "FTA"
		try:
			for caid_entry in self.caid_data:
				if int(self.current_caid, 16) >= int(caid_entry[0], 16) and int(self.current_caid, 16) <= int(caid_entry[1], 16):
					caid_name = caid_entry[2]
					break
			return caid_name + ":%04x:%04x:%04x:%04x" % (int(self.current_caid,16),int(self.current_provid,16),info.getInfo(iServiceInformation.sSID),int(self.current_ecmpid,16))
		except:
			pass
		return ""

	def createResolution(self,info):
		xres = info.getInfo(iServiceInformation.sVideoWidth)
		if xres == -1:
			return ""
		yres = info.getInfo(iServiceInformation.sVideoHeight)
		mode = ("i", "p", "")[info.getInfo(iServiceInformation.sProgressive)]
		fps  = str((info.getInfo(iServiceInformation.sFrameRate) + 500) / 1000)
		return str(xres) + "x" + str(yres) + mode + fps

	def createVideoCodec(self,info):
		return ("MPEG2", "MPEG4", "MPEG1", "MPEG4-II", "VC1", "VC1-SM", "")[info.getInfo(iServiceInformation.sVideoType)]

	def createFrequency(self,fedata):
		frequency = fedata.get("frequency")
		if frequency:
			return str(frequency / 1000)
		return ""

	def createSymbolRate(self,fedata):
		symbolrate = fedata.get("symbol_rate")
		if symbolrate:
			return str(symbolrate / 1000)
		return ""

	def createPolarization(self,fedata):
		polarization = fedata.get("polarization_abbreviation")
		if polarization:
			return polarization
		return ""

	def createFEC(self,fedata):
		fec = fedata.get("fec_inner")
		if fec:
			return fec
		return ""

	def createModulation(self,fedata):
		modulation = fedata.get("modulation")
		if modulation:
			return modulation
		return ""

	def createTunerType(self,feraw):
		tunertype = feraw.get("tuner_type")
		if tunertype:
			return tunertype
		return ""

	def createTunerSystem(self,fedata):
		tunersystem = fedata.get("system")
		if tunersystem:
			return tunersystem
		return ""

	def createOrbPos(self,feraw):
		orbpos = feraw.get("orbital_position")
		if orbpos > 1800:
			return str((float(3600 - orbpos)) / 10.0) + "W"
		elif orbpos > 0:
			return str((float(orbpos)) / 10.0) + "E"
		return ""

	def createProviderName(self,info):
		return info.getInfoString(iServiceInformation.sProvider)

	@cached
	def getText(self):

		service = self.source.service
		if service is None:
			return ""
		info = service and service.info()

		if not info:
			return ""

		if self.type == "CryptoBar":
			self.getCryptoInfo(info)
			return self.createCryptoBar(info)

		if self.type == "CryptoSeca":
			self.getCryptoInfo(info)
			return self.createCryptoSeca(info)

		if self.type == "CryptoVia":
			self.getCryptoInfo(info)
			return self.createCryptoVia(info)

		if self.type == "CryptoIrdeto":
			self.getCryptoInfo(info)
			return self.createCryptoIrdeto(info)

		if self.type == "CryptoNDS":
			self.getCryptoInfo(info)
			return self.createCryptoNDS(info)

		if self.type == "CryptoConax":
			self.getCryptoInfo(info)
			return self.createCryptoConax(info)

		if self.type == "CryptoCryptoW":
			self.getCryptoInfo(info)
			return self.createCryptoCryptoW(info)

		if self.type == "CryptoBeta":
			self.getCryptoInfo(info)
			return self.createCryptoBeta(info)

		if self.type == "CryptoNagra":
			self.getCryptoInfo(info)
			return self.createCryptoNagra(info)

		if self.type == "CryptoBiss":
			self.getCryptoInfo(info)
			return self.createCryptoBiss(info)

		if self.type == "CryptoDre":
			self.getCryptoInfo(info)
			return self.createCryptoDre(info)

		if self.type == "CryptoSpecial":
			self.getCryptoInfo(info)
			return self.createCryptoSpecial(info)

		if self.type == "ResolutionString":
			return self.createResolution(info)

		if self.type == "VideoCodec":
			return self.createVideoCodec(info)

		feinfo = service.frontendInfo()
		if feinfo is None:
			return ""

		feraw = feinfo.getAll(True)
		if feraw is None:
			return ""

		fedata = ConvertToHumanReadable(feraw)
		if fedata is None:
			return ""

		if self.type == "TransponderFrequency":
			return self.createFrequency(fedata)

		if self.type == "TransponderSymbolRate":
			return self.createSymbolRate(fedata)

		if self.type == "TransponderPolarization":
			return self.createPolarization(fedata)

		if self.type == "TransponderFEC":
			return self.createFEC(fedata)

		if self.type == "TransponderModulation":
			return self.createModulation(fedata)

		if self.type == "OrbitalPosition":
			return self.createOrbPos(feraw)

		if self.type == "TunerType":
			return self.createTunerType(feraw)

		if self.type == "TunerSystem":
			return self.createTunerSystem(fedata)

		if self.type == "All":
			self.getCryptoInfo(info)
			if config.usage.show_cryptoinfo.value:
				return addspace(self.createProviderName(info)) + addspace(self.createTunerSystem(fedata)) + addspace(self.createFrequency(fedata)) + addspace(self.createPolarization(fedata))\
				+ addspace(self.createSymbolRate(fedata)) + addspace(self.createFEC(fedata)) + addspace(self.createModulation(fedata)) + self.createOrbPos(feraw) + "\n"\
				+ addspace(self.createCryptoBar(info)) + addspace(self.createCryptoSpecial(info)) + "\n"\
				+ addspace(self.createVideoCodec(info)) + self.createResolution(info)
			else:
				return addspace(self.createProviderName(info)) + addspace(self.createTunerSystem(fedata)) + addspace(self.createFrequency(fedata)) + addspace(self.createPolarization(fedata))\
				+ addspace(self.createSymbolRate(fedata)) + addspace(self.createFEC(fedata)) + addspace(self.createModulation(fedata)) + self.createOrbPos(feraw) + "\n"\
				+ addspace(self.createCryptoBar(info)) + self.current_source + "\n"\
				+ addspace(self.createCryptoSpecial(info)) + addspace(self.createVideoCodec(info)) + self.createResolution(info)

		return _("invalid type")

	text = property(getText)

	@cached
	def getBool(self):
		service = self.source.service
		info = service and service.info()

		if not info:
			return False

		if self.type == "CryptoCaidSecaAvailable":
			request_caid = "S"
			request_selected = False
		elif self.type == "CryptoCaidViaAvailable":
			request_caid = "V"
			request_selected = False
		elif self.type == "CryptoCaidIrdetoAvailable":
			request_caid = "I"
			request_selected = False
		elif self.type == "CryptoCaidNDSAvailable":
			request_caid = "Nd"
			request_selected = False
		elif self.type == "CryptoCaidConaxAvailable":
			request_caid = "Co"
			request_selected = False
		elif self.type == "CryptoCaidCryptoWAvailable":
			request_caid = "Cw"
			request_selected = False
		elif self.type == "CryptoCaidBetaAvailable":
			request_caid = "B"
			request_selected = False
		elif self.type == "CryptoCaidNagraAvailable":
			request_caid = "N"
			request_selected = False
		elif self.type == "CryptoCaidBissAvailable":
			request_caid = "Bi"
			request_selected = False
		elif self.type == "CryptoCaidDreAvailable":
			request_caid = "D"
			request_selected = False
		elif self.type == "CryptoCaidSecaSelected":
			request_caid = "S"
			request_selected = True
		elif self.type == "CryptoCaidViaSelected":
			request_caid = "V"
			request_selected = True
		elif self.type == "CryptoCaidIrdetoSelected":
			request_caid = "I"
			request_selected = True
		elif self.type == "CryptoCaidNDSSelected":
			request_caid = "Nd"
			request_selected = True
		elif self.type == "CryptoCaidConaxSelected":
			request_caid = "Co"
			request_selected = True
		elif self.type == "CryptoCaidCryptoWSelected":
			request_caid = "Cw"
			request_selected = True
		elif self.type == "CryptoCaidBetaSelected":
			request_caid = "B"
			request_selected = True
		elif self.type == "CryptoCaidNagraSelected":
			request_caid = "N"
			request_selected = True
		elif self.type == "CryptoCaidBissSelected":
			request_caid = "Bi"
			request_selected = True
		elif self.type == "CryptoCaidDreSelected":
			request_caid = "D"
			request_selected = True
		else:
			return False

		if info.getInfo(iServiceInformation.sIsCrypted) != 1:
			return False

		data = self.ecmdata.getEcmData()

		if data is None:
			return False

		current_caid	= data[1]
		#current_provid	= data[2]
		#current_ecmpid	= data[3]

		available_caids = info.getInfoObject(iServiceInformation.sCAIDs)

		for caid_entry in self.caid_data:
			if caid_entry[3] == request_caid:
				if(request_selected):
					if int(current_caid, 16) >= int(caid_entry[0], 16) and int(current_caid, 16) <= int(caid_entry[1], 16):
						return True
				else: # request available
					try:
						for caid in available_caids:
							if caid >= int(caid_entry[0], 16) and caid <= int(caid_entry[1], 16):
								return True
					except:
						pass

		return False

	boolean = property(getBool)

	def changed(self, what):
		Converter.changed(self, what)

