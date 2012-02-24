# shamelessly copied from pliExpertInfo (Vali, Mirakels, Littlesat)

from enigma import iServiceInformation
from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.config import config
from Tools.Transponder import ConvertToHumanReadable
from Tools.GetEcmInfo import GetEcmInfo
from Poll import Poll

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

	@cached
	def getText(self):

		service = self.source.service
		info = service and service.info()

		if not info:
			return ""

		if self.type == "CryptoBar":
			if not config.usage.show_cryptoinfo.value:
				return ""

			if (info.getInfo(iServiceInformation.sIsCrypted) == 1):
				data	= self.ecmdata.getEcmData()
				current_caid	= data[1]
				#current_provid	= data[2]
				#current_ecmpid	= data[3]
			else:
				current_caid	= "0"
				#current_provid	= "0"
				#current_ecmpid	= "0"

			res = ""
			available_caids = (info.getInfoObject(iServiceInformation.sCAIDs))

			for caid_entry in self.caid_data:
				if int(current_caid, 16) >= int(caid_entry[0], 16) and int(current_caid, 16) <= int(caid_entry[1], 16):
					color="\c0000??00"
				else:
					color = "\c007?7?7?"
					try:
						for caid in available_caids:
							if caid >= int(caid_entry[0], 16) and caid <= int(caid_entry[1], 16):
								color="\c00????00"
					except:
						pass

				res += color + caid_entry[3] + " "

			return res

		if self.type == "ResolutionString":
			xres = info.getInfo(iServiceInformation.sVideoWidth)
			yres = info.getInfo(iServiceInformation.sVideoHeight)
			mode = ("i", "p", "")[info.getInfo(iServiceInformation.sProgressive)]
			fps  = str((info.getInfo(iServiceInformation.sFrameRate) + 500) / 1000)
			return str(xres) + "x" + str(yres) + mode + fps

		if self.type == "VideoCodec":
			return ("MPEG2", "AVC", "MPEG1", "MPEG4", "VC1", "VC1SM", "")[info.getInfo(iServiceInformation.sVideoType)]

		if self.type == "TransponderFrequency" or \
				self.type == "TransponderSymbolRate" or \
				self.type == "TransponderPolarization" or \
				self.type == "TransponderFEC":
			if service is None:
				return ""

			feinfo = service.frontendInfo()
			if feinfo is None:
				return ""

			feraw = feinfo.getAll(False)
			if feraw is None:
				return ""

			fedata = ConvertToHumanReadable(feraw)
			if fedata is None:
				return ""

			if self.type == "TransponderFrequency":
				frequency = fedata.get("frequency")

				if frequency is None:
					return ""
				else:
					return str(frequency / 1000)

			if self.type == "TransponderSymbolRate":
				symbolrate = fedata.get("symbol_rate")

				if symbolrate is None:
					return ""
				else:
					return str(symbolrate / 1000)

			if self.type == "TransponderPolarization":
				polarization = fedata.get("polarization_abbreviation")

				if polarization is None:
					return ""
				else:
					return polarization

			if self.type == "TransponderFEC":
				fec = fedata.get("fec_inner")

				if fec is None:
					return ""
				else:
					return fec

		return "invalid type"

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

		available_caids = (info.getInfoObject(iServiceInformation.sCAIDs))

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

	def short(self, langTxt):
		return langTxt
