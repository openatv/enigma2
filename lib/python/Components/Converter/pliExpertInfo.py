#
#  Coded by Vali, updated by Mirakels for openpli
#

from enigma import iServiceInformation, eServiceCenter, iPlayableService, iPlayableServicePtr
from Components.Converter.Converter import Converter
from Components.Element import cached
from Components.config import config
from Tools.Transponder import ConvertToHumanReadable
from Tools.GetEcmInfo import GetEcmInfo
from Poll import Poll

class pliExpertInfo(Poll, Converter, object):
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
			( "0x100", "0x1FF","Seca"   ,"S" ),
			( "0x500", "0x5FF","Via"    ,"V" ),
			( "0x600", "0x6FF","Irdeto" ,"I" ),
			( "0x900", "0x9FF","NDS"    ,"Nd"),
			( "0xB00", "0xBFF","Conax"  ,"Co"),
			( "0xD00", "0xDFF","CryptoW","Cw"),
			("0x1700","0x17FF","Beta"   ,"B" ),
			("0x1800","0x18FF","Nagra"  ,"N" ),
			("0x2600","0x26FF","BISS"   ,"Bi"))
		self.ecmdata = GetEcmInfo()

	@cached
	def getText(self):
		service = self.source.service
		try:
			info = service and service.info()
		except:
			try:
				info = eServiceCenter.getInstance().info(service)
			except:
				pass
		if not info:
			return ""

		Ret_Text = ""
		Sec_Text = ""
		Res_Text = ""
		showCryptoInfo = False

		if (self.type == self.SMART_INFO_H or self.type == self.SERVICE_INFO or self.type == self.CRYPTO_INFO or self.type == self.FREQUENCY_INFO): # HORIZONTAL
			sep = "  "
			sep2 = " - "
		elif (self.type == self.SMART_INFO_V): # VERTIKAL
			sep = "\n"
			sep2 = "\n"
		else:
			return ""	# unsupported orientation

		if (self.type == self.FREQUENCY_INFO):
			try:
				feinfo = (service and service.frontendInfo())
				prvd = info.getInfoString(iServiceInformation.sProvider)
				Ret_Text = self.short(prvd)
				frontendDataOrg = (feinfo and feinfo.getAll(True))
			except:
				try:
					frontendDataOrg = info.getInfoObject(service, iServiceInformation.sTransponderData)
					prvd = info.getInfoString(service, iServiceInformation.sProvider)
				except:
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
						if orbital_pos > 1800:
							if orbital_pos == 3590:
								orb_pos = 'Thor/Intelsat'
							elif orbital_pos == 3560:
								orb_pos = 'Amos (4'
							elif orbital_pos == 3550:
								orb_pos = 'Atlantic Bird'
							elif orbital_pos == 3530:
								orb_pos = 'Nilesat/Atlantic Bird'
							elif orbital_pos == 3520:
								orb_pos = 'Atlantic Bird'
							elif orbital_pos == 3475:
								orb_pos = 'Atlantic Bird'
							elif orbital_pos == 3460:
								orb_pos = 'Express'
							elif orbital_pos == 3450:
								orb_pos = 'Telstar'
							elif orbital_pos == 3420:
								orb_pos = 'Intelsat'
							elif orbital_pos == 3380:
								orb_pos = 'Nss'
							elif orbital_pos == 3355:
								orb_pos = 'Intelsat'
							elif orbital_pos == 3325:
								orb_pos = 'Intelsat'
							elif orbital_pos == 3300:
								orb_pos = 'Hispasat'
							elif orbital_pos == 3285:
								orb_pos = 'Intelsat'
							elif orbital_pos == 3170:
								orb_pos = 'Intelsat'
							elif orbital_pos == 3150:
								orb_pos = 'Intelsat'
							elif orbital_pos == 3070:
								orb_pos = 'Intelsat'
							elif orbital_pos == 3045:
								orb_pos = 'Intelsat'
							elif orbital_pos == 3020:
								orb_pos = 'Intelsat 9'
							elif orbital_pos == 2990:
								orb_pos = 'Amazonas'
							elif orbital_pos == 2900:
								orb_pos = 'Star One'
							elif orbital_pos == 2880:
								orb_pos = 'AMC 6 (72'
							elif orbital_pos == 2875:
								orb_pos = 'Echostar 6'
							elif orbital_pos == 2860:
								orb_pos = 'Horizons'
							elif orbital_pos == 2810:
								orb_pos = 'AMC5'
							elif orbital_pos == 2780:
								orb_pos = 'NIMIQ 4'
							elif orbital_pos == 2690:
								orb_pos = 'NIMIQ 1'
							elif orbital_pos == 3592:
								orb_pos = 'Thor/Intelsat'
							elif orbital_pos == 2985:
								orb_pos = 'Echostar 3,12'
							elif orbital_pos == 2830:
								orb_pos = 'Echostar 8'
							elif orbital_pos == 2630:
								orb_pos = 'Galaxy 19'
							elif orbital_pos == 2500:
								orb_pos = 'Echostar 10,11'
							elif orbital_pos == 2502:
								orb_pos = 'DirectTV 5'
							elif orbital_pos == 2410:
								orb_pos = 'Echostar 7 Anik F3'
							elif orbital_pos == 2391:
								orb_pos = 'Galaxy 23'
							elif orbital_pos == 2390:
								orb_pos = 'Echostar 9'
							elif orbital_pos == 2412:
								orb_pos = 'DirectTV 7S'
							elif orbital_pos == 2310:
								orb_pos = 'Galaxy 27'
							elif orbital_pos == 2311:
								orb_pos = 'Ciel 2'
							elif orbital_pos == 2120:
								orb_pos = 'Echostar 2'
							else:
								orb_pos = str((float(3600 - orbital_pos))/10.0) + "W"
						elif orbital_pos > 0:
							if orbital_pos == 192:
								orb_pos = 'Astra 1F'
							elif orbital_pos == 130:
								orb_pos = 'Hot Bird 6,7A,8'
							elif orbital_pos == 235:
								orb_pos = 'Astra 1E'
							elif orbital_pos == 1100:
								orb_pos = 'BSat 1A,2A'
							elif orbital_pos == 1101:
								orb_pos = 'N-Sat 110'
							elif orbital_pos == 1131:
								orb_pos = 'KoreaSat 5'
							elif orbital_pos == 1440:
								orb_pos = 'SuperBird 7,C2'
							elif orbital_pos == 1006:
								orb_pos = 'AsiaSat 2'
							elif orbital_pos == 1030:
								orb_pos = 'Express A2'
							elif orbital_pos == 1056:
								orb_pos = 'Asiasat 3S'
							elif orbital_pos == 1082:
								orb_pos = 'NSS 11'
							elif orbital_pos == 881:
								orb_pos = 'ST1'
							elif orbital_pos == 900:
								orb_pos = 'Yamal 201'
							elif orbital_pos == 917:
								orb_pos = 'Mesat'
							elif orbital_pos == 950:
								orb_pos = 'Insat 4B'
							elif orbital_pos == 951:
								orb_pos = 'NSS 6'
							elif orbital_pos == 765:
								orb_pos = 'Telestar'
							elif orbital_pos == 785:
								orb_pos = 'ThaiCom 5'
							elif orbital_pos == 800:
								orb_pos = 'Express'
							elif orbital_pos == 830:
								orb_pos = 'Insat 4A'
							elif orbital_pos == 850:
								orb_pos = 'Intelsat 709'
							elif orbital_pos == 750:
								orb_pos = 'Abs'
							elif orbital_pos == 720:
								orb_pos = 'Intelsat'
							elif orbital_pos == 705:
								orb_pos = 'Eutelsat W5'
							elif orbital_pos == 685:
								orb_pos = 'Intelsat'
							elif orbital_pos == 620:
								orb_pos = 'Intelsat 902'
							elif orbital_pos == 600:
								orb_pos = 'Intelsat 904'
							elif orbital_pos == 570:
								orb_pos = 'Nss'
							elif orbital_pos == 530:
								orb_pos = 'Express AM22'
							elif orbital_pos == 480:
								orb_pos = 'Eutelsat 2F2'
							elif orbital_pos == 450:
								orb_pos = 'Intelsat'
							elif orbital_pos == 420:
								orb_pos = 'Turksat 2A'
							elif orbital_pos == 400:
								orb_pos = 'Express AM1'
							elif orbital_pos == 390:
								orb_pos = 'Hellas Sat 2'
							elif orbital_pos == 380:
								orb_pos = 'Paksat 1'
							elif orbital_pos == 360:
								orb_pos = 'Eutelsat Sesat'
							elif orbital_pos == 335:
								orb_pos = 'Astra 1M'
							elif orbital_pos == 330:
								orb_pos = 'Eurobird 3'
							elif orbital_pos == 328:
								orb_pos = 'Galaxy 11'
							elif orbital_pos == 315:
								orb_pos = 'Astra 5A'
							elif orbital_pos == 310:
								orb_pos = 'Turksat'
							elif orbital_pos == 305:
								orb_pos = 'Arabsat'
							elif orbital_pos == 285:
								orb_pos = 'Eurobird 1'
							elif orbital_pos == 284:
								orb_pos = 'Eurobird/Astra'
							elif orbital_pos == 282:
								orb_pos = 'Eurobird/Astra'
							elif orbital_pos == 1220:
								orb_pos = 'AsiaSat'
							elif orbital_pos == 1380:
								orb_pos = 'Telstar 18'
							elif orbital_pos == 260:
								orb_pos = 'Badr 3/4'
							elif orbital_pos == 255:
								orb_pos = 'Eurobird 2'
							elif orbital_pos == 215:
								orb_pos = 'Eutelsat'
							elif orbital_pos == 216:
								orb_pos = 'Eutelsat W6'
							elif orbital_pos == 210:
								orb_pos = 'AfriStar 1'
							elif orbital_pos == 160:
								orb_pos = 'Eutelsat W2'
							elif orbital_pos == 100:
								orb_pos = 'Eutelsat W1'
							elif orbital_pos == 90:
								orb_pos = 'Eurobird 9'
							elif orbital_pos == 70:
								orb_pos = 'Eutelsat W3A'
							elif orbital_pos == 50:
								orb_pos = 'Sirius 4'
							elif orbital_pos == 48:
								orb_pos = 'Sirius 4'
							elif orbital_pos == 30:
								orb_pos = 'Telecom 2'
							else:
								orb_pos = str((float(orbital_pos))/10.0) + "E"
						Ret_Text += sep + orb_pos + "\n"
						Ret_Text += frequency + sep + frontendData.get("polarization_abbreviation")
						Ret_Text += sep + symbolrate
						Ret_Text += sep + frontendData.get("modulation") + "-" + fec_inner
					else:
						Ret_Text += sep + "DVB-C " + frequency + " MHz" + sep + fec_inner + sep + symbolrate
				elif (frontendData.get("tuner_type") == "DVB-T"):
					frequency = (str((frontendData.get("frequency") / 1000)) + " MHz")
					Ret_Text = "Frequency: " + frequency

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
				Res_Text += ("MPEG2 ", "MPEG4 ", "MPEG1 ", "MPEG4-II ", "VC1 ", "VC1-SM ", "")[info.getInfo(iServiceInformation.sVideoType)]
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
						Sec_Text += ":%04x:%04x" % (info.getInfo(iServiceInformation.sSID),int(pid, 16))

			elif not config.usage.show_cryptoinfo.value:
				showCryptoInfo = True
				Sec_Text = "FTA"
			res = ""
			searchIDs = (info.getInfoObject(iServiceInformation.sCAIDs))
			for idline in self.idnames:
				if int(decCI, 16) >= int(idline[0], 16) and int(decCI, 16) <= int(idline[1], 16):
					color="\c0000??00"
				else:
					color = "\c007?7?7?"
					try:
						for oneID in searchIDs:
							if oneID >= int(idline[0], 16) and oneID <= int(idline[1], 16):
								color="\c00????00"
					except:
						pass
				res += color + idline[3] + " "

			if (self.type != self.CRYPTO_INFO):
				Ret_Text += "\n"
			Ret_Text += res + "\c00?????? " + Sec_Text

		if Res_Text != "":
			if showCryptoInfo:
				Ret_Text += sep + Res_Text
			else:
				Ret_Text += "\n" + Res_Text

		return Ret_Text

	text = property(getText)

	def changed(self, what):
		Converter.changed(self, what)

	def short(self, langTxt):
		if (self.type == self.SMART_INFO_V and len(langTxt)>23):
			retT = langTxt[:20] + "..."
			return retT
		else:
			return langTxt
