#
#  Coded by Vali, updated by Mirakels for openpli
#

from enigma import iServiceInformation, eServiceCenter
from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.config import config
from Tools.Transponder import ConvertToHumanReadable
from Tools.GetEcmInfo import GetEcmInfo
from Components.Converter.Poll import Poll


class pliExpertInfo(Poll, Converter):
	SMART_LABEL = 0
	SMART_INFO_H = 1
	SMART_INFO_V = 2
	SERVICE_INFO = 3
	CRYPTO_INFO = 4
	FREQUENCY_INFO = 5

	def __init__(self, type):
		Converter.__init__(self, type)
		Poll.__init__(self)
		self.type = {
				"ShowMe": self.SMART_LABEL,
				"ExpertInfo": self.SMART_INFO_H,
				"ExpertInfoVertical": self.SMART_INFO_V,
				"ServiceInfo": self.SERVICE_INFO,
				"CryptoInfo": self.CRYPTO_INFO,
				"FrequencyInfo": self.FREQUENCY_INFO
			}[type]

		self.poll_interval = 1000
		self.poll_enabled = True
		self.idnames = (
			("0x100", "0x1FF", "Seca", "S"),
			("0x500", "0x5FF", "Via", "V"),
			("0x600", "0x6FF", "Irdeto", "I"),
			("0x900", "0x9FF", "NDS", "Nd"),
			("0xB00", "0xBFF", "Conax", "Co"),
			("0xD00", "0xDFF", "CryptoW", "Cw"),
			("0x1700", "0x17FF", "Beta", "B"),
			("0x1800", "0x18FF", "Nagra", "N"),
			("0x2600", "0x26FF", "BISS", "Bi"))
		self.ecmdata = GetEcmInfo()

	@cached
	def getText(self):
		service = self.source.service
		try:
			info = service and service.info()
		except Exception:
			try:
				info = eServiceCenter.getInstance().info(service)
			except Exception:
				pass
		if not info:
			return ""

		Ret_Text = ""
		Sec_Text = ""
		Res_Text = ""
		showCryptoInfo = False

		if (self.type == self.SMART_INFO_H or self.type == self.SERVICE_INFO or self.type == self.CRYPTO_INFO or self.type == self.FREQUENCY_INFO):  # HORIZONTAL
			sep = "  "
			sep2 = " - "
		elif (self.type == self.SMART_INFO_V):  # VERTIKAL
			sep = "\n"
			sep2 = "\n"
		else:
			return ""  # unsupported orientation

		if (self.type == self.FREQUENCY_INFO):
			try:
				feinfo = (service and service.frontendInfo())
				prvd = info.getInfoString(iServiceInformation.sProvider)
				Ret_Text = self.short(prvd)
				frontendDataOrg = (feinfo and feinfo.getAll(True))
			except Exception:
				try:
					frontendDataOrg = info.getInfoObject(service, iServiceInformation.sTransponderData)
					prvd = info.getInfoString(service, iServiceInformation.sProvider)
				except Exception:
					pass

			if (frontendDataOrg is not None):
				frontendData = ConvertToHumanReadable(frontendDataOrg)
				if ((frontendDataOrg.get("tuner_type") == "DVB-S") or (frontendDataOrg.get("tuner_type") == "DVB-C")):
					frequency = (str((frontendData.get("frequency") / 1000)) + " MHz")
					symbolrate = (str((frontendData.get("symbol_rate") / 1000)))
					fec_inner = frontendData.get("fec_inner")
					if (frontendDataOrg.get("tuner_type") == "DVB-S"):
						Ret_Text += sep + frontendData.get("system")
						orbital_pos = int(frontendDataOrg["orbital_position"])
						orb_pos = {
							30: 'Rascom/Eutelsat 3E',
							48: 'SES 5',
							70: 'Eutelsat 7E',
							90: 'Eutelsat 9E',
							100: 'Eutelsat 10E',
							130: 'Hot Bird',
							160: 'Eutelsat 16E',
							192: 'Astra 1KR/1L/1M/1N',
							200: 'Arabsat 20E',
							216: 'Eutelsat 21.5E',
							235: 'Astra 3',
							255: 'Eutelsat 25.5E',
							260: 'Badr 4/5/6',
							282: 'Astra 2E/2F/2G',
							305: 'Arabsat 30.5E',
							315: 'Astra 5',
							330: 'Eutelsat 33E',
							360: 'Eutelsat 36E',
							380: 'Paksat',
							390: 'Hellas Sat',
							400: 'Express 40E',
							420: 'Turksat',
							450: 'Intelsat 45E',
							480: 'Afghansat',
							490: 'Yamal 49E',
							530: 'Express 53E',
							570: 'NSS 57E',
							600: 'Intelsat 60E',
							620: 'Intelsat 62E',
							685: 'Intelsat 68.5E',
							705: 'Eutelsat 70.5E',
							720: 'Intelsat 72E',
							750: 'ABS',
							765: 'Apstar',
							785: 'ThaiCom',
							800: 'Express 80E',
							830: 'Insat',
							851: 'Intelsat/Horizons',
							880: 'ST2',
							900: 'Yamal 90E',
							915: 'Mesat',
							950: 'NSS/SES 95E',
							1005: 'AsiaSat 100E',
							1030: 'Express 103E',
							1055: 'Asiasat 105E',
							1082: 'NSS/SES 108E',
							1100: 'BSat/NSAT',
							1105: 'ChinaSat',
							1130: 'KoreaSat',
							1222: 'AsiaSat 122E',
							1380: 'Telstar 18',
							1440: 'SuperBird',
							2310: 'Ciel',
							2390: 'Echostar/Galaxy 121W',
							2410: 'Echostar/DirectTV 119W',
							2500: 'Echostar/DirectTV 110W',
							2630: 'Galaxy 97W',
							2690: 'NIMIQ 91W',
							2780: 'NIMIQ 82W',
							2830: 'Echostar/QuetzSat',
							2880: 'AMC 72W',
							2900: 'Star One',
							2985: 'Echostar 61.5W',
							2990: 'Amazonas',
							3020: 'Intelsat 58W',
							3045: 'Intelsat 55.5W',
							3070: 'Intelsat 53W',
							3100: 'Intelsat 50W',
							3150: 'Intelsat 45W',
							3169: 'Intelsat 43.1W',
							3195: 'SES 40.5W',
							3225: 'NSS/Telstar 37W',
							3255: 'Intelsat 34.5W',
							3285: 'Intelsat 31.5W',
							3300: 'Hispasat',
							3325: 'Intelsat 27.5W',
							3355: 'Intelsat 24.5W',
							3380: 'SES 22W',
							3400: 'NSS 20W',
							3420: 'Intelsat 18W',
							3450: 'Telstar 15W',
							3460: 'Express 14W',
							3475: 'Eutelsat 12.5W',
							3490: 'Express 11W',
							3520: 'Eutelsat 8W',
							3530: 'Nilesat/Eutelsat 7W',
							3550: 'Eutelsat 5W',
							3560: "Amos",
							3592: 'Thor/Intelsat'
						}.get(orbital_pos, "")

						if not orb_pos:
							if orbital_pos > 1800:
								orb_pos = str((float(3600 - orbital_pos)) / 10.0) + "W"
							else:
								orb_pos = str((float(orbital_pos)) / 10.0) + "E"

						Ret_Text += sep + orb_pos + "\n"
						Ret_Text += frequency + sep + frontendData.get("polarization_abbreviation")
						Ret_Text += sep + symbolrate
						Ret_Text += sep + frontendData.get("modulation") + "-" + fec_inner
					else:
						Ret_Text += sep + "DVB-C " + frequency + " MHz" + sep + fec_inner + sep + symbolrate
				elif (frontendData.get("tuner_type") == "DVB-T"):
					frequency = (str((frontendData.get("frequency") / 1000)) + " MHz")
					Ret_Text = f"Frequency: {frequency}"

		if (self.type == self.SMART_INFO_H or self.type == self.SMART_INFO_V or self.type == self.SERVICE_INFO):

			xresol = info.getInfo(iServiceInformation.sVideoWidth)
			yresol = info.getInfo(iServiceInformation.sVideoHeight)
			feinfo = (service and service.frontendInfo())

			prvd = info.getInfoString(iServiceInformation.sProvider)
			Ret_Text = self.short(prvd)

			frontendDataOrg = (feinfo and feinfo.getAll(True))
			if (frontendDataOrg is not None):
				frontendData = ConvertToHumanReadable(frontendDataOrg)
				if ((frontendDataOrg.get("tuner_type") == "DVB-S") or (frontendDataOrg.get("tuner_type") == "DVB-C")):
					frequency = (str((frontendData.get("frequency") / 1000)))
					symbolrate = (str((frontendData.get("symbol_rate") / 1000)))
					fec_inner = frontendData.get("fec_inner")
					if (frontendDataOrg.get("tuner_type") == "DVB-S"):
						Ret_Text += sep + frontendData.get("system")
						Ret_Text += sep + frequency + frontendData.get("polarization_abbreviation")
						Ret_Text += sep + symbolrate
						Ret_Text += sep + fec_inner + " " + frontendData.get("modulation")
						orbital_pos = int(frontendDataOrg["orbital_position"])
						if orbital_pos > 1800:
							orb_pos = str((float(3600 - orbital_pos)) / 10.0) + "W"
						elif orbital_pos > 0:
							orb_pos = str((float(orbital_pos)) / 10.0) + "E"
						Ret_Text += sep + orb_pos
					else:
						Ret_Text += sep + "DVB-C " + frequency + " MHz" + sep + fec_inner + sep + symbolrate
				elif (frontendDataOrg.get("tuner_type") == "DVB-T"):
					frequency = (str((frontendData.get("frequency") / 1000)))
					Ret_Text += sep + "DVB-T" + sep + "Frequency:" + sep + frequency + " MHz"

			if (feinfo is not None) and (xresol > 0):
				from Components.Converter.PliExtraInfo import codec_data
				Res_Text += codec_data.get(self.info.getInfo(iServiceInformation.sVideoType), "N/A")
				Res_Text += str(xresol) + "x" + str(yresol)
				Res_Text += ("i", "p", "")[info.getInfo(iServiceInformation.sProgressive)]
				Res_Text += str((info.getInfo(iServiceInformation.sFrameRate) + 500) / 1000)

		if (self.type == self.SMART_INFO_H or self.type == self.SMART_INFO_V or self.type == self.CRYPTO_INFO):

			decCI = "0"
			Sec_Text = ""
			if (info.getInfo(iServiceInformation.sIsCrypted) == 1):
				data = self.ecmdata.getEcmData()
				if not config.usage.show_cryptoinfo.value:
					showCryptoInfo = True
					Sec_Text = data[0] + "\n"
				decCI = data[1]
				provid = data[2]
				pid = data[3]

				if decCI != '0':
					decCIfull = "%04x" % int(decCI, 16)
					for idline in self.idnames:
						if int(decCI, 16) >= int(idline[0], 16) and int(decCI, 16) <= int(idline[1], 16):
							decCIfull = idline[2] + ":" + decCIfull
							break
					Sec_Text += decCIfull
					if provid != '0':
						Sec_Text += ":%04x" % int(provid, 16)
					else:
						Sec_Text += ":"
					if pid != '0':
						Sec_Text += ":%04x:%04x" % (info.getInfo(iServiceInformation.sSID), int(pid, 16))

			elif not config.usage.show_cryptoinfo.value:
				showCryptoInfo = True
				Sec_Text = "FTA"
			res = ""
			searchIDs = (info.getInfoObject(iServiceInformation.sCAIDs))
			for idline in self.idnames:
				if int(decCI, 16) >= int(idline[0], 16) and int(decCI, 16) <= int(idline[1], 16):
					color = r"\c0000ff00"
				else:
					color = r"\c007f7f7f"
					try:
						for oneID in searchIDs:
							if oneID >= int(idline[0], 16) and oneID <= int(idline[1], 16):
								color = r"\c00ffff00"
					except Exception:
						pass
				res += color + idline[3] + " "

			if (self.type != self.CRYPTO_INFO):
				Ret_Text += "\n"
			Ret_Text += res + r"\c00ffffff " + Sec_Text

		if Res_Text != "":
			_sep = sep if showCryptoInfo else "\n"
			Ret_Text = f"{_sep}{Ret_Text}"

		return Ret_Text

	text = property(getText)

	def changed(self, what):
		Converter.changed(self, what)

	def short(self, langTxt):
		if (self.type == self.SMART_INFO_V and len(langTxt) > 23):
			retT = langTxt[:20] + "..."
			return retT
		else:
			return langTxt
